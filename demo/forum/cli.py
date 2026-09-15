"""Headless runner: a persona-only deliberation in the terminal.

    python -m forum.cli                      # auto-detected backend
    FORUM_BACKEND=mock python -m forum.cli   # instant, no LLM
    python -m forum.cli "Your topic here"

Useful for testing a backend without the web platform.
"""

import json
import sys

from .engine import Deliberation


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else None
    d = Deliberation(topic=topic)
    print(f"backend: {d.backend.name}")
    print(f"topic:   {d.topic}\n")

    print("[gathering] collecting opinions + reading the room…")
    d.gen_persona_opinions()
    d.begin()
    for c in d.landscape.get("clusters", []):
        print(f"  camp: {c['label']} ({len(c.get('member_ids', []))}) — {c['summary']}")

    while d.status not in ("consensus", "dissensus"):
        print(f"\n[round {len(d.rounds) + 1}] mediator drafting the offer…")
        d.make_offer()
        r = d.rounds[-1]
        o = r["offer"]
        print(f"  «{o['title']}»\n  {o['text']}")
        print("  collecting responses…")
        d.respond_with({})
        print(f"  accepted: {r['approval']:.0%} (threshold {d.threshold:.0%}) -> {r['outcome']}")
        for x in r["responses"]:
            print(f"    {x['id']:<8} {x['response']:<8} {x['objection'][:90]}")

    print(f"\n=== {d.status.upper()} after {len(d.rounds)} round(s) ===")
    print(json.dumps(d.report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
