"""The Forum deliberation engine — the fundamentals (July 2026 refocus).

The loop, per participant (the original blueprint):

    share your opinion
      -> see where the room stands, especially the side opposed to you
      -> the AI mediator OFFERS one concrete solution built for consensus
      -> accept it, or object in your own words
      -> objections drive a revised offer, round after round
      -> until a supermajority accepts, or the disagreement is honestly mapped

State machine:

    GATHERING -> (landscape, internal) -> OFFERED -> EVALUATED -> OFFERED …
              -> CONSENSUS | DISSENSUS

Design rules that survive every iteration:
- Opinions are instant: a participant's own words enter the room verbatim,
  no gate. The landscape and offers must answer the room, not a paraphrase.
- Every human gets a personal opposing-views summary before any offer.
- One offer per round; responses are binary + text: accept, or object with
  the words that must change. Objections are the fuel of revision.
- Offers carry `addresses` — whose objections this revision answers — so
  "your objection was addressed" is data, not inference.
- Every LLM call goes through `_call` into a replayable audit log.
- Dissensus after max_rounds is a valid product, not a failure.

The engine is pure compute + state: the service layer decides when phases
advance and persists via to_dict()/from_dict().
"""

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from . import prompts
from .llm import make_backend
from .personas import DEFAULT_TOPIC, card_text, get_cards

RESPONSES = ("accept", "object")
MAX_PARALLEL = 4


class Deliberation:
    def __init__(self, topic: str | None = None, threshold: float = 0.75,
                 max_rounds: int = 4, backend=None, persona_variant: str = "v2opt",
                 include_personas: bool = True):
        self.id = uuid.uuid4().hex[:8]
        self.topic = (topic or "").strip() or DEFAULT_TOPIC
        self.threshold = threshold
        self.max_rounds = max_rounds
        self.backend = backend or make_backend()
        self.persona_variant = persona_variant
        self.include_personas = include_personas
        self.cards = get_cards(persona_variant) if include_personas else []
        self.status = "gathering"
        self.humans: dict[str, dict] = {}   # uid -> {name, opinion, opposing}
        self.opinions: list[dict] = []      # {id, name, opinion, is_human}
        self.landscape: dict = {}
        self.rounds: list[dict] = []        # {number, offer, responses, approval, outcome}
        self.report: dict | None = None
        self.audit: list[dict] = []
        self.error: str | None = None
        self.progress: dict = {}
        self._audit_lock = threading.Lock()

    # ---- plumbing -------------------------------------------------------

    def _call(self, task: str, prompt: str, context: dict):
        t0 = time.time()
        response = self.backend.complete_json(task, prompt, context)
        with self._audit_lock:
            self.audit.append({
                "ts": time.time(), "task": task, "backend": self.backend.name,
                "prompt": prompt, "response": response,
                "duration_s": round(time.time() - t0, 2),
            })
        return response

    def _parallel(self, fn, items, phase: str, note_fmt: str):
        done = 0
        lock = threading.Lock()
        self._progress(phase, note_fmt.format(name="…"), 0, len(items))

        def wrapped(item):
            nonlocal done
            out = fn(item)
            with lock:
                done += 1
                self._progress(phase, note_fmt.format(name=item.get("name", "")),
                               done, len(items))
            return out

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
            return list(pool.map(wrapped, items))

    def _progress(self, phase: str, note: str, done: int = 0, total: int = 0):
        self.progress = {"phase": phase, "note": note, "done": done, "total": total}

    def _opinions_json(self) -> str:
        return json.dumps(
            [{"id": o["id"], "opinion": o["opinion"]} for o in self.opinions],
            ensure_ascii=False, indent=1)

    # ---- GATHERING ------------------------------------------------------

    def gen_persona_opinions(self):
        def one(card):
            out = self._call("opinion", prompts.OPINION_ONE.format(
                card=card_text(card), roleplay_rules=prompts.ROLEPLAY_RULES,
                topic=self.topic, json_only=prompts.JSON_ONLY,
            ), {"persona_id": card["id"]})
            return {"id": card["id"], "name": card["name"],
                    "opinion": out["opinion"], "is_human": False}

        self.opinions = self._parallel(one, self.cards,
                                       "gathering", "{name} is writing their opening opinion")

    def add_position(self, uid: str, name: str, raw_text: str):
        """Instant — a citizen's own words enter the room verbatim, no gate."""
        self.humans[uid] = {"name": name, "opinion": raw_text, "opposing": None}
        self.opinions = [o for o in self.opinions if o["id"] != uid]
        self.opinions.append({"id": uid, "name": name, "opinion": raw_text,
                              "is_human": True})

    # ---- LANDSCAPE + per-human opposing summaries (internal step) -------

    def begin(self):
        self._progress("landscape", "Reading the room — mapping every opinion")
        self.landscape = self._call("landscape", prompts.LANDSCAPE.format(
            topic=self.topic, opinions=self._opinions_json(),
            steelman_task="", steelman_schema="", json_only=prompts.JSON_ONLY,
        ), {})

        def one_opposing(item):
            uid, h = item["uid"], item["h"]
            out = self._call("opposing", prompts.OPPOSING_ONE.format(
                topic=self.topic,
                landscape=json.dumps(self.landscape, ensure_ascii=False),
                name=h["name"], opinion=h["opinion"],
                json_only=prompts.JSON_ONLY), {"uid": uid})
            h["opposing"] = {"summary": out.get("summary", ""),
                             "counter": out.get("counter", "")}
            return None

        if self.humans:
            self._parallel(one_opposing,
                           [{"uid": u, "h": h, "name": h["name"]}
                            for u, h in self.humans.items()],
                           "landscape", "Summarizing the other side for {name}")
        self.status = "landscape"

    # ---- THE OFFER ------------------------------------------------------

    def make_offer(self):
        round_num = len(self.rounds) + 1
        revision = ""
        if self.rounds:
            prev = self.rounds[-1]
            objections = [f"- {r['id']}: {r['objection']}"
                          for r in prev["responses"] if r["response"] == "object"]
            revision = prompts.OFFER_REVISION.format(
                round_num=prev["number"],
                prev_offer=json.dumps(prev["offer"], ensure_ascii=False),
                accept_pct=round(prev["approval"] * 100),
                threshold_pct=round(self.threshold * 100),
                objections="\n".join(objections) or "(none recorded)")
        self._progress("offer", "The mediator is drafting an offer for the whole room")
        offer = self._call("offer", prompts.OFFER.format(
            topic=self.topic, opinions=self._opinions_json(),
            landscape=json.dumps(self.landscape, ensure_ascii=False),
            revision_context=revision, json_only=prompts.JSON_ONLY,
        ), {"round_num": round_num, "human_ids": list(self.humans)})
        offer["addresses"] = [x for x in offer.get("addresses", []) if isinstance(x, str)]
        self.rounds.append({"number": round_num, "offer": offer, "responses": [],
                            "approval": None, "approval_by_cluster": {}, "outcome": None})
        self.status = "offered"

    # ---- RESPONSES ------------------------------------------------------

    def _history_block(self, persona_id: str) -> str:
        items = []
        for r in self.rounds[:-1]:
            mine = next((x for x in r["responses"] if x["id"] == persona_id), None)
            if mine:
                items.append(f'- Round {r["number"]} ("{r["offer"]["title"]}"): '
                             f'{mine["response"]}ed — "{mine["objection"]}"')
        return prompts.EVAL_HISTORY.format(items="\n".join(items)) if items else ""

    def respond_one(self, card: dict, offer: dict, round_num: int,
                    own_opinion: str, history: str = "", pressure: str = "") -> dict:
        """One persona responds to one offer in an isolated call.
        Also used directly by the fidelity harness."""
        out = self._call("respond", prompts.RESPOND_ONE.format(
            card=card_text(card), roleplay_rules=prompts.ROLEPLAY_RULES,
            topic=self.topic, own_opinion=own_opinion, history=history,
            round_num=round_num, offer=json.dumps(offer, ensure_ascii=False),
            pressure=prompts.PRESSURE_NOTE.format(pressure=pressure) if pressure else "",
            json_only=prompts.JSON_ONLY,
        ), {"persona_id": card["id"], "round_num": round_num})
        response = out.get("response")
        if response not in RESPONSES:
            raise ValueError(f"invalid response from {card['id']}: {response!r}")
        return {"id": card["id"], "response": response,
                "objection": out.get("objection", ""),
                "red_line_check": out.get("red_line_check", ""),
                "concession_check": out.get("concession_check", "")}

    def respond_with(self, human_responses: dict[str, dict]):
        """human_responses: uid -> {response: accept|object, objection: str}."""
        rnd = self.rounds[-1]
        opinion_by_id = {o["id"]: o["opinion"] for o in self.opinions}

        def one(card):
            return self.respond_one(card, rnd["offer"], rnd["number"],
                                    own_opinion=opinion_by_id.get(card["id"], ""),
                                    history=self._history_block(card["id"]))

        responses = self._parallel(one, self.cards,
                                   "responses", "{name} is weighing the offer")
        for uid, r in human_responses.items():
            if r.get("response") in RESPONSES:
                responses.append({"id": uid, "response": r["response"],
                                  "objection": (r.get("objection") or "").strip()
                                  or ("(accepted)" if r["response"] == "accept" else "(no reason given)")})
        rnd["responses"] = responses

        n = len(responses)
        accepts = sum(1 for r in responses if r["response"] == "accept")
        rnd["approval"] = accepts / n if n else 0.0
        rnd["approval_by_cluster"] = self._approval_by_cluster(responses)

        if rnd["approval"] >= self.threshold:
            rnd["outcome"] = "consensus"
            self._finish("consensus")
        elif rnd["number"] >= self.max_rounds:
            rnd["outcome"] = "dissensus"
            self._finish("dissensus")
        else:
            rnd["outcome"] = "revise"
            self.status = "evaluated"

    def _approval_by_cluster(self, responses):
        by_id = {r["id"]: r["response"] for r in responses}
        out = {}
        for cluster in self.landscape.get("clusters", []):
            members = [m for m in cluster.get("member_ids", []) if m in by_id]
            if members:
                acc = sum(1 for m in members if by_id[m] == "accept")
                out[cluster["label"]] = {"accepting": acc, "total": len(members)}
        return out

    # ---- CLOSING REPORT -------------------------------------------------

    def _finish(self, outcome: str):
        final = self.rounds[-1]
        self._progress("report", "Writing the closing report")
        history = [{"round": r["number"], "proposal": r["offer"],
                    "approval": r["approval"],
                    "ratings": [{"id": x["id"],
                                 "verdict": x["response"],
                                 "reason": x["objection"]} for x in r["responses"]]}
                   for r in self.rounds]
        self.report = self._call("report", prompts.REPORT.format(
            topic=self.topic, outcome=outcome,
            approval_pct=round(final["approval"] * 100),
            threshold_pct=round(self.threshold * 100),
            num_rounds=len(self.rounds),
            history=json.dumps(history, ensure_ascii=False),
            json_only=prompts.JSON_ONLY), {"outcome": outcome})
        self.status = outcome

    # ---- serialization --------------------------------------------------

    _FIELDS = ("id", "topic", "threshold", "max_rounds", "persona_variant",
               "include_personas", "status", "humans", "opinions", "landscape",
               "rounds", "report", "audit", "error")

    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self._FIELDS}
        d["backend"] = self.backend.name
        d["progress"] = self.progress
        return d

    @classmethod
    def from_dict(cls, d: dict, backend=None) -> "Deliberation":
        obj = cls(topic=d["topic"], threshold=d["threshold"], max_rounds=d["max_rounds"],
                  backend=backend, persona_variant=d.get("persona_variant", "v2opt"),
                  include_personas=d.get("include_personas", True))
        for k in cls._FIELDS:
            if k in d:
                setattr(obj, k, d[k])
        return obj
