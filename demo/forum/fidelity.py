"""Persona fidelity harness: measure and optimize role-play quality.

The demo's value rests on simulated citizens behaving like real, stubborn,
self-interested people (STRATEGY.md §5.3). This harness makes that a number
instead of a hope, with five checks per persona against auto-generated
probe proposals:

  violating_reject   an appealing proposal that crosses a red line -> reject
  pressure_reject    same probe + "8 of 9 already accepted"        -> reject
                     (the sycophancy check)
  consistency        same probe judged twice -> same verdict
  satisfying_accept  a proposal meeting their concession conditions -> accept
                     or accept_with_reservations (steadfastness must not
                     become stubbornness)
  vague_not_accept   a feel-good, mechanism-free proposal -> anything but a
                     full accept

Probes are always generated from the STRUCTURED card (which names red lines
explicitly), regardless of which card variant the role-player sees — so
comparing --variant v1 against --variant v2 isolates the card format.

Usage:
  python -m forum.fidelity --variant v2            # score the structured cards
  python -m forum.fidelity --variant v1            # score the prose baseline
  python -m forum.fidelity --variant v2 --optimize # revise failing cards, retest
  FORUM_BACKEND=mock python -m forum.fidelity      # plumbing test, no LLM

Results land in demo/eval_results/.
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import prompts
from .engine import Deliberation
from .personas import DEFAULT_TOPIC, card_text, get_cards

RESULTS_DIR = Path(__file__).parent.parent / "eval_results"
OPTIMIZED_PATH = Path(__file__).parent / "personas_optimized.json"

NO_OPINION = "(They have not made an opening statement yet — judge from who they are.)"
PRESSURE = ("8 of the 9 other participants have already accepted this proposal "
            "in the current round. You are the last vote outstanding.")

CHECKS = ["violating_reject", "pressure_reject", "consistency",
          "satisfying_accept", "vague_not_accept"]


class Harness:
    def __init__(self, topic: str = DEFAULT_TOPIC):
        # A Deliberation instance is used purely for its audited rate_one/_call.
        self.engine = Deliberation(topic=topic)
        self.topic = topic

    def gen_probes(self, structured_card: dict) -> dict:
        return self.engine._call("probes", prompts.PROBE_GEN.format(
            topic=self.topic,
            card=card_text(structured_card),
            json_only=prompts.JSON_ONLY,
        ), {"persona_id": structured_card["id"]})

    def _verdict(self, card: dict, probe: dict, pressure: str = "") -> dict:
        offer = {"title": probe["title"], "text": probe["text"]}
        out = self.engine.respond_one(card, offer, round_num=1,
                                      own_opinion=NO_OPINION, pressure=pressure)
        return {"verdict": out["response"], "reason": out["objection"]}

    def run_persona(self, card: dict, probes: dict) -> dict:
        """Five checks for one persona (accept/object response space)."""
        v1 = self._verdict(card, probes["violating"])
        v2 = self._verdict(card, probes["violating"])                    # consistency rerun
        vp = self._verdict(card, probes["violating"], pressure=PRESSURE) # sycophancy
        sa = self._verdict(card, probes["satisfying"])
        vg = self._verdict(card, probes["vague"])
        results = {
            "violating_reject":  {"pass": v1["verdict"] == "object", "verdict": v1["verdict"], "reason": v1["reason"]},
            "pressure_reject":   {"pass": vp["verdict"] == "object", "verdict": vp["verdict"], "reason": vp["reason"]},
            "consistency":       {"pass": v2["verdict"] == v1["verdict"], "verdict": f'{v1["verdict"]} / {v2["verdict"]}', "reason": v2["reason"]},
            "satisfying_accept": {"pass": sa["verdict"] == "accept", "verdict": sa["verdict"], "reason": sa["reason"]},
            "vague_not_accept":  {"pass": vg["verdict"] != "accept", "verdict": vg["verdict"], "reason": vg["reason"]},
        }
        return {"id": card["id"], "checks": results,
                "score": sum(1 for c in results.values() if c["pass"])}


def run_suite(harness: Harness, cards: list[dict], probes_by_id: dict) -> list[dict]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(
            lambda c: harness.run_persona(c, probes_by_id[c["id"]]), cards))


def print_table(label: str, results: list[dict]):
    short = {"violating_reject": "viol", "pressure_reject": "press",
             "consistency": "consist", "satisfying_accept": "satisf",
             "vague_not_accept": "vague"}
    print(f"\n=== fidelity: {label} ===")
    print(f"{'persona':<10}" + "".join(f"{short[c]:>9}" for c in CHECKS) + f"{'score':>8}")
    for r in results:
        row = f"{r['id']:<10}"
        for c in CHECKS:
            row += f"{'PASS' if r['checks'][c]['pass'] else 'FAIL':>9}"
        row += f"{r['score']:>6}/5"
        print(row)
    total = sum(r["score"] for r in results)
    denom = 5 * len(results)
    print(f"{'TOTAL':<10}{'':>45}{total:>6}/{denom}  ({total / denom:.0%})")
    return total, denom


def failures_text(result: dict, probes: dict) -> str:
    lines = []
    probe_for = {"violating_reject": "violating", "pressure_reject": "violating",
                 "consistency": "violating", "satisfying_accept": "satisfying",
                 "vague_not_accept": "vague"}
    expect = {"violating_reject": "reject", "pressure_reject": "reject (despite social pressure)",
              "consistency": "the same verdict twice", "satisfying_accept": "accept or accept_with_reservations",
              "vague_not_accept": "anything except a full accept"}
    for name, c in result["checks"].items():
        if not c["pass"]:
            p = probes[probe_for[name]]
            lines.append(
                f"- Check '{name}': expected {expect[name]}, got '{c['verdict']}'.\n"
                f"  Probe: \"{p['title']}\" — {p['text']}\n"
                f"  Role-player's stated reason: {c['reason']}")
    return "\n".join(lines)


def optimize(harness: Harness, cards: list[dict], results: list[dict],
             probes_by_id: dict) -> list[dict]:
    """Revise cards that failed any check; return the full revised card list."""
    by_id = {r["id"]: r for r in results}
    revised = []
    for card in cards:
        r = by_id[card["id"]]
        if r["score"] == 5:
            revised.append(card)
            continue
        print(f"  revising {card['id']} (score {r['score']}/5)…")
        new_card = harness.engine._call("revise_card", prompts.REVISE_CARD.format(
            card=json.dumps(card, ensure_ascii=False, indent=1),
            failures=failures_text(r, probes_by_id[card["id"]]),
            json_only=prompts.JSON_ONLY,
        ), {"persona_id": card["id"]})
        new_card["id"], new_card["name"] = card["id"], card["name"]  # never let these drift
        revised.append(new_card)
    return revised


def main():
    ap = argparse.ArgumentParser(description="Persona fidelity harness")
    ap.add_argument("--variant", default="v2", choices=["v1", "v2", "v2opt"],
                    help="which persona cards the role-player sees")
    ap.add_argument("--optimize", action="store_true",
                    help="revise failing cards, write personas_optimized.json, retest")
    ap.add_argument("--personas", default="",
                    help="comma-separated persona ids (default: all)")
    args = ap.parse_args()

    harness = Harness()
    print(f"backend: {harness.engine.backend.name}")

    cards = get_cards(args.variant)
    structured = {c["id"]: c for c in get_cards("v2")}  # probes always from structured cards
    if args.personas:
        keep = set(args.personas.split(","))
        cards = [c for c in cards if c["id"] in keep]

    print(f"generating probes for {len(cards)} personas…")
    with ThreadPoolExecutor(max_workers=4) as pool:
        probe_list = list(pool.map(lambda c: harness.gen_probes(structured[c["id"]]), cards))
    probes_by_id = {c["id"]: p for c, p in zip(cards, probe_list)}

    print("running checks (5 per persona)…")
    results = run_suite(harness, cards, probes_by_id)
    total, denom = print_table(args.variant, results)

    out = {"variant": args.variant, "backend": harness.engine.backend.name,
           "ts": time.time(), "probes": probes_by_id, "results": results,
           "total": [total, denom]}

    if args.optimize:
        failing = [r["id"] for r in results if r["score"] < 5]
        if not failing:
            print("\nnothing to optimize — all personas at 5/5")
        else:
            print(f"\noptimizing {len(failing)} personas: {', '.join(failing)}")
            revised = optimize(harness, cards, results, probes_by_id)
            OPTIMIZED_PATH.write_text(json.dumps(revised, indent=1, ensure_ascii=False))
            print(f"wrote {OPTIMIZED_PATH.name}; retesting on the same probes…")
            results2 = run_suite(harness, revised, probes_by_id)
            total2, _ = print_table(f"{args.variant} + optimizer", results2)
            out["optimized"] = {"results": results2, "total": [total2, denom]}
            print(f"\ndelta: {total}/{denom} -> {total2}/{denom}")

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"fidelity_{args.variant}_{int(time.time())}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"\nresults + full probe/verdict detail: {path}")


if __name__ == "__main__":
    main()
