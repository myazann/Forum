# Forum — Product & User Journey Strategy

> **Revision (2026-07-20) — back to fundamentals.** The main structure is now:
> **topic → share your opinion (instant, verbatim, no gate) → see where the
> room stands, especially the side opposed to you → the mediator OFFERS one
> concrete consensus solution → accept it, or object in your own words →
> objections drive the next revision → consensus or honest dissensus.**
> Consequences: the two-candidate election and three-verdict ballots are
> removed (one offer per round, accept/object); position-card confirmation is
> dropped (your words enter verbatim); **no login** — identity materializes
> silently when you act (generated pseudonym + cookie; /api/login remains to
> claim a preferred name); Home is the topic floor. The social layer (§2, §4)
> is to be reread with one change: **you follow topics people participate
> in, not people's opinions** — person-following and opinion-shares are out;
> topic-following and participation signals are the Phase C spine. Sections
> below describing elections, ballots, card confirmation, or person-follows
> are historical until rewritten.

*Companion to [STRATEGY.md](STRATEGY.md) (the engine) — this document is the citizen's side: where people enter, what they see, what they own, and why they come back. July 2026.*

## 1. Diagnosis: why the demo feels like an admin panel

The current app is the **mediator's console**. It renders the engine's state machine — landscape, candidates, ballots — and the human is a guest inside the machine room, clicking the machine's buttons ("Draft two rival proposals" is a mediator's verb, not a citizen's). There is one deliberation, it exists only while the server runs, nobody has a name, and when you leave, no trace of you remains.

A civic platform inverts this. The citizen's frame is:

> *Something I care about is being decided. I said my piece. Did anyone hear me? What happened next? What are the people I trust saying?*

Everything below serves that frame. The engine we built stays exactly as it is — it becomes one **room** in a building, rather than the whole building.

## 2. Design pillars — the social layer with different physics

Social structure (identity, follows, a feed) is what turns a tool you're summoned to into a place you live. But Forum cannot import social media's physics, because three of its core mechanics are the disease Forum treats (STRATEGY.md §5.2, §5.4; vTaiwan/Polis's deliberate no-reply design). So the social layer is rebuilt around four pillars:

**P1 — You reply to topics, never to people.** There are no comments, no reply chains, no quote-dunks. The only "reply" primitive in Forum is *taking your own position on the topic*. If someone you follow shares a position that outrages you, the button under it is not "Reply" — it is **"Take your position"**. Disagreement is routed into deliberation, not threads. This single constraint structurally removes dunking, pile-ons, and most harassment surface.

**P2 — The scoreboard is being heard, not being loud.** No follower counts on display, no like counters racing upward. The reputation that accrues on a profile is a **civic record**: deliberations joined, critiques that were addressed in a revision ("your objection shaped v3"), steelmen endorsed by the people they argue against, consensus texts your concerns are cited in (`draws_from` — the engine already tracks this). Status flows from bridging, because that's what the platform measures and shows.

**P3 — The feed is ranked by bridging, not engagement.** Chronological within your own deliberations (it's a to-do list of civic moments: elections open, ballots open, revisions landed). For discovery, ranking rewards what Community Notes rewards — content endorsed *across* clusters, not within them — plus deliberate cross-cluster injection: the feed regularly carries one well-argued position from outside your cluster (labeled as such). An echo chamber is a feed-ranking choice; so is its opposite.

**P4 — Your voice is yours.** The *process* is radically public (proposals, tallies, distributions, the audit trail). The *individual ballot* is private by default — coerced or performative voting is a real failure mode, and the freedom to accept a compromise your tribe hates requires a private booth. Sharing a ballot with reasons is a deliberate act, like publishing an op-ed. Position cards are pseudonymous-public by default (they feed the landscape) with real-name attachment opt-in. Nothing a user wrote is ever shown in a form they didn't confirm (the position card mechanic, now a platform-wide rule).

## 3. Actors

| Actor | Who they are | What they need |
|---|---|---|
| **Participant** | Has taken a position in ≥1 deliberation | To be heard, to see what their words did, to vote |
| **Observer** | Follows topics/people, hasn't spoken yet | A low-pressure on-ramp; watching is legitimate participation |
| **Initiator** | Raises a topic, invites others | Topic creation, invite links, quorum visibility |
| **Institution** *(later)* | Council, employer, municipality | Outcome reports, commitment tracking (STRATEGY.md §3.12) |

The Observer → Participant conversion is *the* funnel. Social media optimizes lurk→post with outrage; Forum's on-ramp is **"take a position" moments** placed where curiosity peaks (under a shared position, on a topic page approaching quorum, at a deliberation's election).

## 4. The user journey

### 4.1 Entry — three doors

1. **Invited to a deliberation** (the demo's world): a link — "Your neighborhood is deliberating parking. 14 have taken positions. Election opens at 20." Lands on the deliberation page in observer mode; the CTA is *Take your position*.
2. **Invited by a person**: a shared position card ("Rosa shared her position on school closures"). The card is the hook; the CTA is the topic, not the person (P1).
3. **Topic emergence** *(Phase C, STRATEGY.md §3.8)*: "312 people have raised housing costs this week. A deliberation opens at 500." Raising a topic is itself an entry action.

### 4.2 Onboarding = your first position

No profile-building wizard. You write what you think about the thing you came for; the Forum shows you its position card of you; you correct it and confirm. **The existing card-confirm mechanic is the onboarding** — the first 90 seconds teach the platform's core promise: *it listens, it doesn't distort you, nothing counts without your sign-off.* Identity asked at the moment it's needed, not before: display name at first position, email/magic-link only when you want to be findable across sessions. (Real identity/sybil resistance stays a Phase-4+ dependency — invite-graphs and per-deliberation membership until then; STRATEGY.md §5.6.)

### 4.3 Home — the feed

Not a timeline of content; a **civic surface** with three bands:

```
┌────────────────────────────────────────────────────┐
│ NEEDS YOU (your deliberations, action required)    │
│ ▸ Parking reform — election open · 2 candidates    │
│ ▸ AI gains — the mediator revised the proposal.    │
│   Your critique about board seats → addressed ✓    │
│   Ballot open until quorum.                        │
├────────────────────────────────────────────────────┤
│ PEOPLE & TOPICS YOU FOLLOW                         │
│ ▸ Marcus shared his ballot + reasons on AI gains   │
│   [Read] [Take your position]                      │
│ ▸ Housing costs: 312 raised · opens at 500 [Raise] │
│ ▸ From outside your cluster: Wei's position on …   │
├────────────────────────────────────────────────────┤
│ OUTCOMES                                           │
│ ▸ School closures reached consensus at 81% —       │
│   your concern is cited in the final text ¶3       │
└────────────────────────────────────────────────────┘
```

The single most important card type is the **closed loop**: *"the mediator revised the proposal — your critique was addressed in v3."* The engine already produces this data (critiques → revision rationale, `draws_from`); surfacing it per-user is the retention mechanic *and* the legitimacy claim in one. People return to places that prove they were heard.

### 4.4 The deliberation room

The current UI, reframed from console to room:

- **Observer mode is the default state** — landscape, candidates, tallies, trajectory visible read-only, with "Take your position to vote" gates. (The engine gains nothing here; this is presentation.)
- Mediator's verbs disappear behind the curtain: phases advance on **quorum + clock** ("Election closes in 2 days or when 80% have voted"), not on someone pressing "Draft proposals". The room shows *"The mediator is drafting two rival proposals from 41 positions…"* — the live-progress plumbing we built, recast as theater curtains.
- Your column: your position card, your election vote, your ballot, your critique — and what happened to each ("cited in v2's rationale").

### 4.5 Profile — the civic record

```
┌────────────────────────────────────────────┐
│ Rosa · Chihuahua · joined May 2036         │
│ "Programs die before they reach my town."  │
├────────────────────────────────────────────┤
│ CIVIC RECORD                               │
│ 7 deliberations · 3 reached consensus      │
│ 4 critiques addressed in revisions         │
│ 2 steelmen endorsed by the other side      │
│ Cited in 2 consensus texts                 │
├────────────────────────────────────────────┤
│ SHARED POSITIONS (what she chose to show)  │
│ ▸ School closures — position + journey:    │
│   "I moved from reject to accept because   │
│    v3 added per-town delivery accounts."   │
└────────────────────────────────────────────┘
```

No follower count on the page. The **journey post** ("what changed my mind") is the platform's prestige genre — the thing social media has no grammar for, and the thing deliberation is *made of*. Opinion movement is already measured for §5.8 metrics; here it becomes something a person can be proud of publicly.

### 4.6 What "share" means

Shareable objects, each a structured card (never free-text broadcast):
- **Position card** (default pseudonymous; name attach opt-in)
- **Ballot + reasons** (private by default; sharing is deliberate — P4)
- **Journey** ("I changed my verdict between rounds because…")
- **Steelman endorsement** ("this is the best argument against my side")
- **Outcome report** (the deliberation's own artifact)

Every share's CTA for the viewer is *Take your position* / *Follow this topic*. Nothing has a reply box.

## 5. Backend: from one deliberation in RAM to a platform

### 5.1 Data model — AS BUILT in Phase A (July 2026)

```
users          id, handle (pseudonym, unique), token, created_at
deliberations  id, topic, status, created_by, config{min_participants,
               include_personas, threshold, max_rounds}, state (JSON), timestamps
participants   delib_id, user_id, role, joined_at
events         id, delib_id, type, payload, ts        ← written at every phase
                                                        transition; Phase B's feed
                                                        reads from here
```

Design choice that stuck: **relational tables for what we query; each
deliberation's full engine state (positions, cards, steelmen, rounds,
candidates, elections, ballots, staged actions, audit log) is one JSON
document** — the engine serializes itself, and at pilot scale a document per
deliberation beats mapping every ballot into rows. Consequences the later
phases must respect:

- Anything the *feed or profile* needs across deliberations must be **derived
  into tables at write time** (via `events` payloads), not queried out of
  state JSONs at read time. Phase B's civic record depends on this.
- `positions` / `ballots` visibility flags live inside the state doc
  (`humans[uid]`), so sharing (Phase B/C) is a state-doc field plus a derived
  `shares` row — not a schema migration of the core.
- Personas are engine-internal, not `users` rows. The "personas populate the
  social layer" trick therefore needs a thin adapter in Phase C (persona
  profile pages rendered from cards + their deliberation history), not fake
  accounts.

Identity as shipped: pseudonym + session token, "knowing the pseudonym = owning
it" (pilot-grade). The upgrade path (email attach / magic link) is a Phase B/C
pre-pilot task, deliberately additive: `users` gains nullable `email`, nothing
else changes.

### 5.2 Architecture evolution

| | Phase A (shipped) | Phase B | Later |
|---|---|---|---|
| Storage | SQLite (stdlib, WAL), state-doc + relational index | + notifications, civic_events, shares tables | Postgres when a pilot outgrows one box |
| Identity | pseudonym + cookie token | + optional email attach (account recovery) | magic links / OAuth |
| Engine | untouched core; service layer queues actions per deliberation, advances on quorum, self-heals stalled phases on read | + machine-readable closed loop (see B-1) | phase clocks/deadlines |
| API | login/me, deliberations CRUD, join/position/confirm/vote/ballot, role-aware views | + `/api/me/feed`, `/api/users/{handle}`, notifications | + follows, topics, shares |
| Frontend | Floor (home.html) · Room (room.html), duplicated CSS | app shell + Feed + Profile, shared design-system files | + Topic pages, journey composer |

### 5.3 Feed assembly (v1, deliberately simple)

```
NEEDS YOU:   events where user is participant and phase awaits their action
FOLLOWING:   shares by followed users + milestones of followed topics
             + 1 injected cross-cluster share per session (labeled)
OUTCOMES:    closed deliberations user touched or follows
Ranking:     band order fixed; within bands: recency. No engagement signals
             exist to rank by — by design (P3). Bridging-weighted discovery
             ranking arrives Phase C with cross-cluster endorsement data.
```

## 6. Phased plan (revised after Phase A shipped)

Each phase now has two tracks. **Engineering** builds capability; **Experience**
turns it into the citizen's journey — screens, states, and copy are first-class
deliverables, not by-products. A phase isn't done until both tracks pass its
exit test.

### Phase A — Multi-user core ✅ shipped 2026-07-15

Pseudonymous users, SQLite persistence, concurrent deliberations, join links,
quorum-driven phases (no mediator buttons; initiator may lower quorum),
per-human position cards + steelmen, tallies-only-after-close, per-viewer
state shaping, action queue (nothing a user does is dropped mid-phase).
*Exit test passed: two users over HTTP, 10-voter election, server killed and
restarted mid-deliberation with everything intact, consensus + report.*

Known gaps, deliberately deferred: no phase deadlines (a vanished participant
stalls a round — see B-6); no joining once a deliberation has started; no
account recovery (pseudonym = token).

### Phase B — The loop closes (the platform remembers you)

**Engineering**
1. **Machine-readable closed loop** — the one engine change of the phase: the
   revision prompt's candidates gain an `addresses` field (which participants'
   critiques each candidate answers), so *"your critique was addressed in
   round 3"* becomes data, not inference. Consensus reports already carry
   `draws_from` for "cited in the final text".
2. **Civic-record derivation**: enrich `events` payloads at phase close
   (per-user: voted, balloted, critique-addressed, cited); roll them into a
   `civic_events(user_id, delib_id, kind, round, ts)` table. Profiles and
   feeds read tables, never state JSONs (§5.1).
3. `notifications(user_id, event_id, seen_at)` + unseen counts.
4. APIs: `/api/me/feed` (NEEDS YOU: my deliberations awaiting my action;
   OUTCOMES: closed deliberations I touched), `/api/users/{handle}` (civic
   record + shared positions).
5. Position sharing: `visibility` on the human's state entry + derived
   `shares` row (pseudonymous-public claim by default per §8 decision;
   ballots stay private, shared per-ballot only).
6. **Phase deadlines**: config gains `phase_hours`; a lightweight scheduler
   closes elections/ballots with whoever has acted when the clock expires —
   the anti-stall mechanic Phase A punted on.

**Experience**
1. **App shell** shared by every page: wordmark → Home (feed), "The floor"
   (all deliberations), notification badge, profile menu with your pseudonym.
   Prerequisite: extract the duplicated CSS/JS into `web/static/forum.css` +
   `forum.js` (design tokens, cards, meters, ballots) — one design system,
   three surfaces about to become five.
2. **Home becomes the feed**: NEEDS YOU and OUTCOMES bands (FOLLOWING waits
   for C); the closed-loop card is the hero — *"The mediator revised the
   proposal — your critique about board seats was addressed. Ballot open."*
   Empty state designed, not defaulted: "Nothing needs you. Go live your
   life."
3. **Your column in the room**: a persistent strip showing *your* journey in
   this deliberation — position → vote → ballot → what happened to each
   ("addressed in v3", "cited ¶2"). The room today shows the group; B makes
   your thread through it visible.
4. **Profile page**: civic record (auto-computed, uncurated), shared
   positions, join date. No follower counts — there is nothing to count.
5. **Onboarding moment**: first pseudonym pick gets the three-line contract
   (you're pseudonymous; nothing counts until you confirm it; you'll see the
   strongest case against you). One screen, no tour.
6. **Share controls**: per-position "share publicly" toggle at confirm time +
   per-ballot share action after a round closes, with copy that treats
   sharing as deliberate ("publishing your ballot is an op-ed, not a like").

*Exit test: a participant who left mid-deliberation returns via the
"your critique was addressed" notification and re-engages; their profile
shows a true civic record they didn't curate; a stalled election closes on
its deadline without anyone touching a mediator control.*

### Phase C — The social spine (the platform is a place)

**Engineering**: `follows(follower_id, kind, target)` (people + topics);
journey posts + steelman endorsements as share kinds; topic raising +
emergence thresholds (a topic page accumulates raisers, a deliberation opens
at N — STRATEGY.md §3.8); mid-flight joining (new positions land in a
between-rounds landscape refresh); persona adapter so simulated citizens have
profile pages and shares in dev mode; discovery ranking = bridging-weighted
(cross-cluster endorsements) with one labeled cross-cluster injection per
session.

**Experience**: FOLLOWING band; follow buttons on profiles/topics (never a
follower count); topic pages with "Raise this too" + emergence progress;
journey composer (guided: your before/after verdicts pre-filled, you write
the "because"); steelman endorsement action ("this is the best argument
against my side"); every share's viewer-CTA is *Take your position* — nothing
anywhere gets a reply box (§2 P1).

*Exit test: an observer discovers a deliberation through a followed person's
share, converts via "Take your position", and the entry is attributable to
the social graph.*

### Phase D — Institutions & scale

Unchanged (STRATEGY.md Phases 3–4): outcome commitment tracking, sampled
panels, real identity. Not before the B and C loops demonstrably work.

### Cross-cutting experience debt (schedule inside B and C, before the pilot)

| Item | When | Why it can't slip past the pilot |
|---|---|---|
| Shared design-system files (kill the CSS duplication) | B, first | Every B/C surface multiplies the divergence otherwise |
| Mobile pass (candidate cards, ballot, feed on a phone) | B | The pilot cohort will open invite links on phones |
| Accessibility audit (focus order, `aria-live` on phase changes, contrast re-run through the palette validator) | B | Civic platform; table stakes |
| Room updates via SSE (drop 2s polling) | C | Feeds + rooms polling at scale is self-inflicted load |
| Email attach for account recovery | B, pre-pilot | A lost cookie currently orphans a pseudonym and its record |
| Rate limits + input caps on LLM-backed endpoints | B, pre-pilot | Cost safety before strangers hold invite links |
| Observer→participant copy for started deliberations | C (with mid-flight joining) | Today's "watch until the next one" is honest but loses the convert |

Persona-powered development applies to every phase: simulated citizens
exercise feeds, profiles, and follows in dev mode the way they exercise
deliberations today — the whole social experience is testable with zero real
users.

## 7. Pressure points specific to the social layer

| Risk | Design answer |
|---|---|
| Engagement drift — feed slowly optimizes for time-on-site | No engagement metrics collected for ranking; band structure hard-coded; "NEEDS YOU empty" is a success state, shown as such ("Nothing needs you. Go live your life.") |
| Echo chambers via follows | Cross-cluster injection (P3); topic-follow weighted over people-follow in discovery |
| Harassment / dogpiles | No replies, no DMs, no quote-shares (P1); structured share objects only |
| Ballot performativity & coercion | Private ballots by default (P4); sharing is per-ballot, never blanket |
| Status games corrupt sincerity | Civic record counts only mediator-verified events (citations, addressed critiques — computed from engine data, not self-reported); no follower counts |
| Gaming the civic record | Records derive from the audit trail; the same transparency that legitimizes the mediator legitimizes the scoreboard |
| Sybil (amplified by social graph) | Unchanged from STRATEGY.md §5.6: invite-graphs + per-deliberation membership until real identity exists |

## 8. Open questions (your call, before Phase A)

1. **Pseudonymity default**: position cards public-but-pseudonymous (recommended) vs named-by-default? Affects onboarding copy and the follows model (following a pseudonym is fine; the civic record makes pseudonyms meaningful).
2. **Observer ballots**: can observers see live tallies before voting closes (transparency) or only after (anti-herding)? Recommended: distributions visible only after your own ballot is cast — the private-booth principle applied to information.
3. **Scope of the first real deployment**: one community (Existential Hope cohort) with a handful of live topics beats an open platform. Phase A's exit test doubles as the pilot's infrastructure.

## 9. What we deliberately do not build

Comments/replies of any kind; repost-with-commentary; trending lists ranked by volume; follower leaderboards; DMs; infinite scroll (the feed has an end: "Nothing else needs you"); engagement notifications ("people are talking about…"). Each is a load-bearing absence — removing one of these removals would quietly re-import the physics we're escaping.
