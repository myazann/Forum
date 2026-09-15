"""Service layer: persistence + phase orchestration for the offer loop.

- load/save deliberations (engine state JSON + staged responses) in SQLite
- quorum rules: the response phase closes when every participant with an
  opinion has responded, or the phase deadline passes
- one background drainer per deliberation works a phase queue; user actions
  are never dropped, stalled phases self-heal on the next read
- per-viewer shaping: your opinion, your opposing-views summary, your
  response state; results don't exist until the round closes
- the closed loop: offers carry `addresses` -> notifications + civic events
"""

import threading
import time

from . import db
from .engine import RESPONSES, Deliberation
from .llm import make_backend

_locks: dict[str, threading.Lock] = {}
_workers: dict[str, threading.Thread] = {}
_backend = None
_global = threading.Lock()
_PHASES = {}
_pending: dict[str, list] = {}


def _lock(delib_id: str) -> threading.Lock:
    with _global:
        return _locks.setdefault(delib_id, threading.Lock())


def backend():
    global _backend
    if _backend is None:
        _backend = make_backend()
    return _backend


def busy(delib_id: str) -> bool:
    w = _workers.get(delib_id)
    return w is not None and w.is_alive()


# ---- load/save ------------------------------------------------------------

def _load(delib_id: str):
    row = db.load_deliberation(delib_id)
    if not row:
        return None, None, None
    state = row["state"]
    staged = state.get("staged", {"responses": {}})
    staged.setdefault("responses", {})
    d = Deliberation.from_dict(state, backend=backend())
    return d, staged, row["config"]


def _save(delib_id: str, d: Deliberation, staged: dict):
    state = d.to_dict()
    state["staged"] = staged
    db.save_state(delib_id, d.status, state)


# ---- creation & membership ------------------------------------------------

def create(user: dict, topic: str, include_personas: bool = True,
           min_participants: int = 1, phase_hours: float = 0) -> str:
    d = Deliberation(topic=topic, backend=backend(), include_personas=include_personas)
    config = {"include_personas": include_personas,
              "min_participants": max(0, int(min_participants)),
              "phase_hours": max(0.0, float(phase_hours))}
    db.create_deliberation(d.id, d.topic, d.status, user["id"], config, d.to_dict())
    db.join(d.id, user["id"])
    db.add_event(d.id, "created", {"by": user["handle"]})
    if include_personas:
        _spawn(d.id, "persona opinions")
    return d.id


def join(delib_id: str, user: dict):
    db.join(delib_id, user["id"])


# ---- citizen actions ------------------------------------------------------

def take_position(delib_id: str, user: dict, raw_text: str):
    """Instant: the citizen's own words enter the room verbatim."""
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        if d.status != "gathering":
            raise ValueError("this deliberation has already started — watch, or join the next one")
        d.add_position(user["id"], user["handle"], raw_text)
        _save(delib_id, d, staged)
    db.join(delib_id, user["id"])
    db.add_event(delib_id, "position", {"by": user["handle"]})
    advance(delib_id)


def begin_now(delib_id: str, user: dict):
    """Initiator lowers the quorum to whoever has spoken."""
    import json as _json
    row = db.load_deliberation(delib_id)
    if row["created_by"] != user["id"]:
        raise PermissionError("only the initiator can begin early")
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        config["min_participants"] = max(1, len(d.humans)) if d.humans else 0
        db.conn().execute("UPDATE deliberations SET config = ? WHERE id = ?",
                          (_json.dumps(config), delib_id))
        db.conn().commit()
    advance(delib_id)


def respond(delib_id: str, user: dict, response: str, objection: str = ""):
    if response not in RESPONSES:
        raise ValueError("response must be accept or object")
    if response == "object" and not objection.strip():
        raise ValueError("say what must change — your objection drives the next offer")
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        if d.status != "offered":
            raise ValueError("no offer is open right now")
        if user["id"] not in d.humans:
            raise ValueError("share your opinion before responding")
        staged["responses"][user["id"]] = {"response": response, "objection": objection.strip()}
        _save(delib_id, d, staged)
    db.add_event(delib_id, "response", {"by": user["handle"], "response": response})
    advance(delib_id)


def retry(delib_id: str):
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        d.error = None
        _save(delib_id, d, staged)
    advance(delib_id)


# ---- advancement ----------------------------------------------------------

def advance(delib_id: str):
    if busy(delib_id):
        return
    d, staged, config = _load(delib_id)
    if d is None or d.error:
        return
    speakers = list(d.humans)

    def deadline_passed():
        hours = config.get("phase_hours", 0)
        opened = staged.get("phase_opened_at")
        return bool(hours and opened and time.time() > opened + hours * 3600)

    if d.status == "gathering":
        need = config.get("min_participants", 1)
        if d.include_personas and not d.opinions:
            _spawn(delib_id, "persona opinions")
        elif len(speakers) >= need and (speakers or d.include_personas):
            _spawn(delib_id, "landscape")
    elif d.status == "landscape":
        _spawn(delib_id, "offer")
    elif d.status == "offered":
        if (not speakers or all(uid in staged["responses"] for uid in speakers)
                or deadline_passed()):
            _spawn(delib_id, "responses")
    elif d.status == "evaluated":
        _spawn(delib_id, "offer")


def _spawn(delib_id: str, phase_name: str, custom=None):
    with _global:
        q = _pending.setdefault(delib_id, [])
        duplicate = custom is None and any(p == phase_name and c is None for p, c in q)
        if not duplicate:
            q.append((phase_name, custom))
        if q and not busy(delib_id):
            t = threading.Thread(target=_drain, args=(delib_id,), daemon=True)
            _workers[delib_id] = t
            t.start()


def _drain(delib_id: str):
    while True:
        with _global:
            q = _pending.get(delib_id, [])
            if not q:
                _PHASES.pop(delib_id, None)
                return
            phase_name, custom = q.pop(0)
            _PHASES[delib_id] = phase_name
        _run_one(delib_id, phase_name, custom)


def _run_one(delib_id: str, phase_name: str, custom):
    try:
        with _lock(delib_id):
            d, staged, config = _load(delib_id)
            if custom is not None:
                custom(d, staged)
            elif phase_name == "persona opinions":
                if d.opinions:
                    return
                d.gen_persona_opinions()
            elif phase_name == "landscape":
                if d.status != "gathering":
                    return
                d.begin()
            elif phase_name == "offer":
                if d.status not in ("landscape", "evaluated"):
                    return
                d.make_offer()
                staged["responses"] = {}
                staged["phase_opened_at"] = time.time()
            elif phase_name == "responses":
                if d.status != "offered":
                    return
                d.respond_with(staged["responses"])
            d.progress = {}
            _save(delib_id, d, staged)
            db.add_event(delib_id, "phase", {"phase": phase_name, "status": d.status})
            _after_phase(delib_id, phase_name, d)
    except Exception as e:
        with _lock(delib_id):
            d, staged, config = _load(delib_id)
            d.error = f"{phase_name} failed: {e}"
            _save(delib_id, d, staged)
    finally:
        advance(delib_id)


# ---- the closed loop: notifications + civic record ------------------------

def _after_phase(delib_id: str, phase_name: str, d):
    humans = list(d.humans.keys())
    if not humans or not d.rounds:
        return
    rnd = d.rounds[-1]

    if phase_name == "offer":
        addressed = set(rnd["offer"].get("addresses", []))
        for uid in humans:
            was_addressed = uid in addressed and rnd["number"] > 1
            if was_addressed:
                db.add_civic_event(uid, delib_id, "critique_addressed", rnd["number"])
            db.notify(uid, delib_id, "offer_open",
                      {"round": rnd["number"], "title": rnd["offer"]["title"],
                       "addressed": was_addressed})

    elif phase_name == "responses":
        if d.status in ("consensus", "dissensus"):
            cited = set(rnd["offer"].get("draws_from", [])) if d.status == "consensus" else set()
            for uid in humans:
                if uid in cited:
                    db.add_civic_event(uid, delib_id, "cited_in_consensus", rnd["number"])
                db.notify(uid, delib_id, "outcome",
                          {"status": d.status, "approval": rnd["approval"],
                           "cited": uid in cited})
        else:
            for uid in humans:
                db.notify(uid, delib_id, "round_result",
                          {"round": rnd["number"], "approval": rnd["approval"],
                           "outcome": rnd["outcome"]})


def live_progress(delib_id: str) -> dict:
    return {"phase": _PHASES.get(delib_id, ""),
            "note": {
                "persona opinions": "The simulated citizens are writing their opening opinions",
                "landscape": "Reading the room and summarizing the other side for each participant",
                "offer": "The mediator is drafting an offer for the whole room",
                "responses": "The simulated citizens are weighing the offer",
            }.get(_PHASES.get(delib_id, ""), "Working")}


# ---- feed & profile -------------------------------------------------------

def feed(user: dict) -> dict:
    needs_you, outcomes = [], []
    for row in db.deliberations_for(user["id"]):
        entry = {"id": row["id"], "topic": row["topic"], "status": row["status"]}
        if row["status"] in ("consensus", "dissensus"):
            outcomes.append(entry)
            continue
        d, staged, config = _load(row["id"])
        action = None
        if row["status"] == "gathering" and user["id"] not in d.humans:
            action = "share your opinion"
        elif (row["status"] == "offered" and user["id"] in d.humans
              and user["id"] not in staged["responses"]):
            action = "respond to the offer"
        if action:
            entry["action"] = action
            hours = config.get("phase_hours", 0)
            opened = staged.get("phase_opened_at")
            if hours and opened and row["status"] == "offered":
                entry["closes_at"] = opened + hours * 3600
            needs_you.append(entry)
    cited_ids = {r["delib_id"] for r in db.conn().execute(
        "SELECT delib_id FROM civic_events WHERE user_id=? AND kind='cited_in_consensus'",
        (user["id"],)).fetchall()} if outcomes else set()
    for o in outcomes:
        o["cited"] = o["id"] in cited_ids
    return {"needs_you": needs_you, "outcomes": outcomes,
            "notifications": db.notifications_for(user["id"]),
            "unseen": db.unseen_count(user["id"])}


def profile(handle: str) -> dict | None:
    u = db.user_by_handle(handle)
    if not u:
        return None
    shared = []
    for row in db.deliberations_for(u["id"]):
        d, _, _ = _load(row["id"])
        h = d.humans.get(u["id"])
        if h:
            shared.append({"delib_id": row["id"], "topic": row["topic"],
                           "status": row["status"], "claim": h["opinion"]})
    return {"handle": u["handle"], "joined": u["created_at"],
            "record": db.civic_record(u["id"]), "shared_positions": shared}


# ---- per-viewer state shaping ---------------------------------------------

def view(delib_id: str, user: dict | None) -> dict | None:
    advance(delib_id)
    d, staged, config = _load(delib_id)
    if d is None:
        return None
    uid = user["id"] if user else None
    parts = db.participants(delib_id)
    row = db.load_deliberation(delib_id)

    me = None
    if uid:
        h = d.humans.get(uid)
        me = {
            "user_id": uid, "handle": user["handle"],
            "is_creator": row["created_by"] == uid,
            "has_position": h is not None,
            "opinion": h["opinion"] if h else None,
            "opposing": h["opposing"] if h else None,
            "responded": uid in staged["responses"],
            "my_response": staged["responses"].get(uid),
        }

    rounds = []
    for r in d.rounds:
        rr = {"number": r["number"], "offer": r["offer"], "outcome": r["outcome"]}
        if r["responses"]:
            rr.update({k: r[k] for k in ("responses", "approval", "approval_by_cluster")})
        if r is d.rounds[-1] and d.status == "offered":
            rr["waiting_on"] = {"responded": len(staged["responses"]),
                                "needed": len(d.humans)}
        rounds.append(rr)

    return {
        "id": d.id, "topic": d.topic, "status": d.status,
        "threshold": d.threshold, "max_rounds": d.max_rounds,
        "backend": d.backend.name, "include_personas": d.include_personas,
        "min_participants": config.get("min_participants", 1),
        "speaker_count": len(d.humans),
        "participants": [{"handle": p["handle"],
                          "spoke": any(o["is_human"] and o["name"] == p["handle"]
                                       for o in d.opinions)} for p in parts],
        "opinions": d.opinions,
        "landscape": d.landscape, "rounds": rounds, "report": d.report,
        "error": d.error, "busy": busy(delib_id),
        "progress": live_progress(delib_id) if busy(delib_id) else {},
        "me": me,
        "audit_count": len(d.audit),
        "closes_at": (staged.get("phase_opened_at", 0) + config.get("phase_hours", 0) * 3600
                      if config.get("phase_hours", 0) and staged.get("phase_opened_at")
                      and d.status == "offered" else None),
    }


def audit(delib_id: str) -> list:
    d, _, _ = _load(delib_id)
    return d.audit if d else []
