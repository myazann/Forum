"""Persistent participant journeys and single-process background orchestration."""

from copy import deepcopy
import logging
import math
import threading
import time
import uuid

from . import db, example
from .engine import RESPONSES, Deliberation
from .llm import make_backend

log = logging.getLogger(__name__)
_locks = {}
_workers = {}
_global = threading.Lock()
_backend = None
TERMINAL = {"consensus", "dissensus", "insufficient"}


class UnavailableBackend:
    """Keep saved discussions readable when the configured mediator cannot load."""
    name = "unavailable"

    def complete_json(self, *args, **kwargs):
        raise RuntimeError("The configured mediator is unavailable.")


def _lock(delib_id):
    with _global:
        return _locks.setdefault(delib_id, threading.RLock())


def backend():
    global _backend
    if _backend is None:
        _backend = make_backend()
    return _backend


def live_available():
    try:
        return backend().name != "mock"
    except Exception:
        return False


def busy(delib_id):
    with _global:
        return delib_id in _workers


def _load(delib_id):
    row = db.load_deliberation(delib_id)
    if not row:
        raise LookupError("This discussion could not be found.")
    state = row["state"]
    staged = state.get("staged", {})
    staged.setdefault("responses", {})
    staged.setdefault("perspective_seen", [])
    try:
        reader_backend = example.ExampleBackend() if state.get("mode") == "example" else backend()
    except Exception:
        reader_backend = UnavailableBackend()
    d = Deliberation.from_dict(state, backend=reader_backend)
    # Older persisted rooms had no proposal identifiers or explicit electorate.
    # A deterministic ID permits safe version binding without rewriting history.
    for rnd in d.rounds:
        rnd["offer"].setdefault("id", uuid.uuid5(uuid.NAMESPACE_URL,
                                               f"forum:{d.id}:round:{rnd['number']}").hex)
        rnd.setdefault("eligible_ids", list(d.humans) + [c["id"] for c in d.cards])
    hours = row["config"].get("phase_hours", 0)
    if "closes_at" not in staged and hours and staged.get("phase_opened_at"):
        staged["closes_at"] = staged["phase_opened_at"] + hours * 3600
    return d, staged, row["config"]


def _save(delib_id, d, staged):
    state = d.to_dict()
    state["staged"] = staged
    db.save_state(delib_id, d.status, state)


def create_example(user):
    d = example.new()
    config = {"mode": "example", "include_personas": False, "min_participants": 1}
    db.create_deliberation(d.id, d.topic, d.status, user["id"], config, d.to_dict())
    db.join(d.id, user["id"])
    return d.id


def create(user, topic, context="", intake_hours=24, phase_hours=24):
    if not live_available():
        raise ValueError("Live discussions are not available on this instance. Try the guided example.")
    if len(topic.strip()) < 10:
        raise ValueError("Give the group a clear question of at least 10 characters.")
    d = Deliberation(topic.strip(), backend=backend(), include_personas=False)
    d.context = context.strip()
    config = {"mode": "live", "include_personas": False, "min_participants": 3,
              "intake_closes_at": time.time() + intake_hours * 3600, "phase_hours": phase_hours}
    db.create_deliberation(d.id, d.topic, d.status, user["id"], config, d.to_dict())
    db.join(d.id, user["id"])
    return d.id


def _available(delib_id):
    if busy(delib_id):
        raise ValueError("The mediator is working. Your writing is safe; try again when this step finishes.")


def take_position(delib_id, user, raw_text="", choice=None):
    _available(delib_id)
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        if d.status != "gathering":
            raise ValueError("This discussion has closed to new views. You can still read the proposal and result.")
        if d.mode == "example":
            if db.load_deliberation(delib_id)["created_by"] != user["id"]:
                raise PermissionError("Start your own example to try a perspective.")
            example.choose(d, user, choice)
        else:
            if time.time() >= config.get("intake_closes_at", float("inf")):
                raise ValueError("The time for sharing views has ended. Refresh to see the next step.")
            if not raw_text.strip():
                raise ValueError("Write what matters to you before sharing.")
            d.add_position(user["id"], user["handle"], raw_text.strip())
        _save(delib_id, d, staged)
        db.join(delib_id, user["id"])


def begin_now(delib_id, user):
    _available(delib_id)
    with _lock(delib_id):
        d, staged, _ = _load(delib_id)
        row = db.load_deliberation(delib_id)
        if row["created_by"] != user["id"]:
            raise PermissionError("Only the person who started this discussion can close intake early.")
        if d.mode == "example" or d.status != "gathering":
            raise ValueError("This discussion is not gathering views.")
        if len(d.humans) < 3:
            raise ValueError("At least three people need to share a view before the group can begin.")
        staged["intake_closed"] = True
        _save(delib_id, d, staged)
    advance(delib_id)


def continue_journey(delib_id, user):
    with _lock(delib_id):
        d, staged, _ = _load(delib_id)
        if user["id"] not in d.humans:
            raise PermissionError("Share a view before continuing.")
        if d.status not in ("landscape", "evaluated", "offered"):
            raise ValueError("There is no proposal to open at this stage.")
        if user["id"] not in staged["perspective_seen"]:
            staged["perspective_seen"].append(user["id"])
        if d.mode == "example":
            if d.status != "offered":
                example.make_offer(d)
                staged["responses"] = {}
                _notify_offer(delib_id, d)
        _save(delib_id, d, staged)


def respond(delib_id, user, response, objection, round_number, proposal_id):
    if response not in RESPONSES:
        raise ValueError("Choose whether you could live with the proposal or need a change.")
    _available(delib_id)
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        if d.status != "offered":
            raise ValueError("That response window has closed. Review the latest version before responding.")
        rnd = d.rounds[-1]
        if rnd["number"] != round_number or rnd["offer"].get("id") != proposal_id:
            raise ValueError("The proposal has changed. Review the new version before responding.")
        if user["id"] not in d.humans:
            raise PermissionError("Only people who shared a view during intake can respond.")
        if user["id"] not in staged["perspective_seen"]:
            raise ValueError("Read where the room stands before responding to the proposal.")
        if d.mode == "example":
            example.respond(d, response)
            staged["responses"] = {user["id"]: d.rounds[-1]["responses"][-1]}
        else:
            if time.time() >= staged.get("closes_at", float("inf")):
                raise ValueError("This response window has closed. Your draft is still saved.")
            if response == "object" and not objection.strip():
                raise ValueError("Say what would need to change for you to accept.")
            staged["responses"][user["id"]] = {"response": response,
                                                  "objection": objection.strip() if response == "object" else ""}
        _save(delib_id, d, staged)
        if d.status in TERMINAL:
            _notify_outcome(delib_id, d)
    advance(delib_id)


def retry(delib_id, user):
    with _lock(delib_id):
        d, staged, _ = _load(delib_id)
        if db.load_deliberation(delib_id)["created_by"] != user["id"]:
            raise PermissionError("Only the discussion host can retry mediation.")
        d.error = None
        _save(delib_id, d, staged)
    advance(delib_id)


def advance(delib_id):
    if busy(delib_id):
        return
    with _lock(delib_id):
        d, staged, config = _load(delib_id)
        if d.mode == "example" or d.error or d.status in TERMINAL:
            return
        if config.get("mode") == "live" and not live_available():
            d.error = "The live mediator is unavailable. Saved views and responses are safe; the host can retry after service is restored."
            _save(delib_id, d, staged)
            return
        phase = None
        if d.status == "gathering":
            closes = config.get("intake_closes_at")
            ready = staged.get("intake_closed") or (closes and time.time() >= closes)
            # Existing research rooms retain their original quorum behavior.
            if not closes:
                ready = len(d.humans) >= config.get("min_participants", 1)
            if ready:
                if not d.include_personas and len(d.humans) < 3:
                    d.status = "insufficient"
                    d.report = {"summary": "Fewer than three people shared a view before intake closed. No group result was declared.",
                                "agreed": [], "contested": [], "evolution": "Start a new discussion when your group is ready."}
                    _save(delib_id, d, staged)
                    _notify_outcome(delib_id, d)
                    return
                phase = "landscape"
        elif d.status in ("landscape", "evaluated"):
            phase = "offer"
        elif d.status == "offered":
            eligible = [u for u in d.rounds[-1].get("eligible_ids", list(d.humans)) if u in d.humans]
            if all(u in staged["responses"] for u in eligible) or time.time() >= staged.get("closes_at", float("inf")):
                phase = "responses"
        if phase:
            _launch(delib_id, phase)


def _launch(delib_id, phase):
    with _global:
        if delib_id in _workers:
            return
        _workers[delib_id] = phase
    threading.Thread(target=_run_phase, args=(delib_id, phase), daemon=True).start()


def _run_phase(delib_id, phase):
    try:
        with _lock(delib_id):
            d, staged, config = _load(delib_id)
            if phase == "landscape":
                d.begin()
            elif phase == "offer":
                d.make_offer()
                staged["responses"] = {}
                staged["closes_at"] = time.time() + config.get("phase_hours", 24) * 3600
            elif phase == "responses":
                d.respond_with(staged["responses"])
            _save(delib_id, d, staged)
            if phase == "offer":
                _notify_offer(delib_id, d)
            elif d.status in TERMINAL:
                _notify_outcome(delib_id, d)
    except Exception:
        log.exception("Mediation failed in %s for %s", phase, delib_id)
        with _lock(delib_id):
            d, staged, _ = _load(delib_id)
            d.error = "The mediator couldn't finish this step. Saved views and responses are safe."
            _save(delib_id, d, staged)
    finally:
        with _global:
            _workers.pop(delib_id, None)
    # Continue only after releasing the worker reservation. No browser polling needed.
    advance(delib_id)


def tick():
    rows = db.conn().execute("SELECT id FROM deliberations WHERE status NOT IN ('consensus','dissensus','insufficient')").fetchall()
    for row in rows:
        try:
            advance(row["id"])
        except Exception:
            log.exception("Could not advance discussion %s", row["id"])


def _notify_offer(delib_id, d):
    rnd = d.rounds[-1]
    for uid in d.humans:
        db.notify(uid, delib_id, "offer_open", {"round": rnd["number"], "title": rnd["offer"]["title"]})


def _notify_outcome(delib_id, d):
    for uid in set(d.humans) | {db.load_deliberation(delib_id)["created_by"]}:
        db.notify(uid, delib_id, "outcome", {"status": d.status})


def feed(user):
    groups = {"needs_you": [], "waiting": [], "outcomes": []}
    for row in db.deliberations_for(user["id"]):
        d, staged, config = _load(row["id"])
        entry = {"id": d.id, "topic": d.topic, "status": d.status, "mode": d.mode,
                 "updated_at": row["updated_at"], "action": "Read discussion"}
        uid = user["id"]
        if d.status in TERMINAL:
            entry["action"] = "Read result"
            groups["outcomes"].append(entry)
        elif d.status == "gathering" and uid not in d.humans:
            entry["action"] = "Share your view"
            groups["needs_you"].append(entry)
        elif d.mode == "example" and d.status in ("landscape", "evaluated"):
            entry["action"] = "Understand the room" if d.status == "landscape" else "See what changed"
            groups["needs_you"].append(entry)
        elif d.status == "offered" and uid in d.humans and uid not in staged["responses"]:
            entry["action"] = "Consider the revised proposal" if len(d.rounds) > 1 else "Consider the proposal"
            groups["needs_you"].append(entry)
        else:
            entry["action"] = "Waiting for the group" if not busy(d.id) else "Mediator at work"
            groups["waiting"].append(entry)
    return {**groups, "notifications": db.notifications_for(user["id"]), "unseen": db.unseen_count(user["id"])}


def _my_concerns(d, uid, offer):
    changes = {c["concern_id"]: c for c in offer.get("changes", [])}
    return [{**c, "assessment": changes.get(c["id"])} for c in d.concerns if c["user_id"] == uid]


def view(delib_id, user):
    d, staged, config = _load(delib_id)
    uid = user["id"] if user else None
    row = db.load_deliberation(delib_id)
    current_offer = d.rounds[-1]["offer"] if d.rounds else {}
    names = {p["user_id"]: p["handle"] for p in db.participants(delib_id)}
    opinions = [{**o, "name": names.get(o["id"], o["name"])} for o in d.opinions]
    me = None
    if user:
        h = d.humans.get(uid)
        me = {"user_id": uid, "handle": user["handle"], "is_creator": row["created_by"] == uid,
              "has_position": bool(h), "opinion": h["opinion"] if h else None,
              "opposing": h["opposing"] if h else None,
              "perspective_seen": uid in staged["perspective_seen"],
              "responded": uid in staged["responses"], "my_response": staged["responses"].get(uid),
              "concerns": _my_concerns(d, uid, current_offer)}
    rounds = []
    for r in d.rounds:
        offer = {k: deepcopy(v) for k, v in r["offer"].items() if k not in ("changes", "addresses")}
        eligible = len(r.get("eligible_ids", [])) or len(d.humans) + len(d.cards)
        rr = {"number": r["number"], "offer": offer, "outcome": r["outcome"], "eligible": eligible,
              "required": math.ceil(eligible * d.threshold),
              "my_response": next((x for x in r["responses"] if x["id"] == uid), None)}
        if r["outcome"]:
            rr.update(approval=r["approval"], responded=len(r["responses"]),
                      accepting=sum(x["response"] == "accept" for x in r["responses"]),
                      objecting=sum(x["response"] == "object" for x in r["responses"]))
        elif r is d.rounds[-1]:
            rr["waiting_on"] = {"responded": len(staged["responses"]), "needed": len(d.humans)}
        rounds.append(rr)
    phase = _workers.get(delib_id)
    note = {"landscape": "Finding common ground and understanding the different views",
            "offer": "Preparing a concrete proposal for the group", "responses": "Reviewing the responses and recording the result"}.get(phase, "")
    return {"id": d.id, "topic": d.topic, "context": d.context, "mode": d.mode,
            "status": d.status, "threshold": d.threshold, "max_rounds": d.max_rounds,
            "speaker_count": len(d.humans), "min_participants": config.get("min_participants", 3),
            "opinions": opinions, "landscape": d.landscape, "rounds": rounds,
            "report": d.report, "me": me, "busy": bool(phase), "progress": note, "error": d.error,
            "closes_at": config.get("intake_closes_at") if d.status == "gathering" else
                         staged.get("closes_at") if d.status == "offered" else None,
            "example_choices": [{k: v for k, v in c.items() if k != "counter"} for c in example.CHOICES] if d.mode == "example" else [],
            "selected_choice": d.scenario.get("choice") if uid == row["created_by"] else None,
            "process": {"backend": d.backend.name, "calls": len(d.audit),
                        "description": "Curated viewpoints, proposals and example votes. Your response is counted exactly as you choose it. No AI is called." if d.mode == "example" else
                        "The mediator reads public views and private responses. Public results show aggregate counts. Individual acceptance choices and raw model traces are not published."}}


def audit(delib_id):
    """Public call metadata only: prompts and responses can contain private votes."""
    d, _, _ = _load(delib_id)
    return [{k: a[k] for k in ("task", "backend", "duration_s", "ts")} for a in d.audit]


def profile(handle, viewer):
    u = db.user_by_handle(handle)
    if not u:
        raise LookupError("This profile could not be found.")
    if not viewer or u["id"] != viewer["id"]:
        raise PermissionError("Participation history is private. Public views remain visible inside each discussion.")
    return {"handle": u["handle"], "joined": u["created_at"]}
