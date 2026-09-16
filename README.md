# The Forum

**The future of democracy: An AI-mediator that unites people.**

Voting transmits about one bit of information every few years. Social media
amplifies whoever is loudest. Forum is an attempt at a third thing: an AI that
mediates at a scale no human facilitator could reach, looking for the
inclusive middle rather than the winning side.

You share your opinion on a topic. The Forum shows you where everyone else
stands, especially the people who disagree with you. Then it offers one
concrete solution built to be acceptable to the whole room. You accept it, or
you object in your own words. Your objection goes into the next revision.
Round after round, until a supermajority accepts, or the disagreement is
mapped honestly and published as the result.

No accounts, no replies, no comment threads. You respond to a proposal, never
to a person.

---

## The loop

```
   topic
     ↓
   everyone shares an opinion        ← your words, verbatim, instantly
     ↓
   the Forum reads the room          ← camps, common ground, real disagreements
     ↓
   you see the strongest case        ← the opposing view, steelmanned, for you
   against your own position
     ↓
   ONE offer, for everyone           ← concrete: mechanisms, money, who administers
     ↓
   accept  —or—  object in text      ← objections are the fuel of revision
     ↓
   revised offer answers objections  ← marked "this revision answers your objection"
     ↓
   consensus (75% accept)  |  dissensus (honest map of what divides you)
```

---

## Run it

Requires Python 3.11+. SQLite comes with Python, so there is nothing else to install.

```bash
git clone https://github.com/myazann/Forum.git
cd Forum
python3 -m venv demo-venv
./demo-venv/bin/pip install -r demo/requirements.txt
```

**Try it with no API key and no cost** — canned responses, full loop, instant:

```bash
FORUM_BACKEND=mock ./demo-venv/bin/uvicorn server:app --port 8710 --app-dir demo
```

**Run it for real** — set a key, then start the server:

```bash
export OPENAI_API_KEY=sk-...
./demo-venv/bin/uvicorn server:app --port 8710 --app-dir demo
```

Open <http://localhost:8710>, raise a topic, and say what you think. Share the
room's URL to bring someone else in. A phase takes 15–60 seconds on a real
backend, since every simulated citizen reasons in a separate call.

### Watch a deliberation in the terminal

```bash
cd demo
FORUM_BACKEND=mock ../demo-venv/bin/python -m forum.cli
../demo-venv/bin/python -m forum.cli "Should our city ban cars from the centre?"
```

---

## Technical details

### Backends

Chosen with `FORUM_BACKEND`, or detected automatically in this order:
`ANTHROPIC_API_KEY` → `OPENAI_API_KEY` → a logged-in `claude` CLI → `mock`.

| `FORUM_BACKEND` | Needs | Default model (`FORUM_MODEL` overrides) |
|---|---|---|
| `mock` | nothing | — canned responses for UI and plumbing work |
| `openai-api` | `OPENAI_API_KEY` | `gpt-5-mini` |
| `anthropic-api` | `ANTHROPIC_API_KEY` | `claude-opus-4-8` |
| `claude-cli` | a logged-in `claude` CLI | `sonnet` |

### Layout

```
demo/
  server.py            FastAPI app: pages + JSON API
  forum/
    engine.py          the loop — opinions, offers, responses, outcomes
    service.py         persistence, phase queue, quorum, per-viewer state
    db.py              SQLite schema and queries (stdlib sqlite3)
    llm.py             swappable backends
    prompts.py         one prompt per step of the loop
    personas.py        the 8 simulated citizens
    fidelity.py        measures how faithfully personas role-play
    mockdata.py        canned responses for FORUM_BACKEND=mock
    cli.py             terminal runner
  web/                 home.html (floor) · room.html · profile.html · static/
```

### How it behaves

- **Identity** is a cookie and a generated pseudonym, created the moment you
  act. There is no signup screen. `POST /api/login` claims a pseudonym you pick.
- **Rounds close** when every participant who has spoken has responded. Set
  `phase_hours` when raising a topic to close on a clock instead.
- **Results stay sealed** until a round closes, so nobody can follow the crowd.
- **Consensus** is 75% acceptance; a deliberation runs at most 4 rounds before
  publishing a dissensus report.
- **Storage** is one SQLite file (`demo/forum.db`, override with `FORUM_DB`).
  Relational tables hold users and participation; each deliberation's full
  state is a JSON document.
- **Every mediator call** — prompt and response — is recorded and readable
  from the "Audit trail" drawer inside a room.

### Persona fidelity

Simulated citizens are only useful if they behave like stubborn, self-interested
people. `forum/fidelity.py` measures that with five probes each: an appealing
offer that crosses a red line (must object), the same offer under "8 of 9
already accepted" pressure (must still object), an offer that genuinely meets
their conditions (must accept), a vague crowd-pleaser (must not accept), and a
repeat for consistency.

```bash
cd demo
FORUM_BACKEND=openai-api ../demo-venv/bin/python -m forum.fidelity --variant v2
```

---
