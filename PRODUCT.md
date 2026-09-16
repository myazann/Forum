# Forum — current product contract

Updated 16 September 2026. This document describes the current participant experience and supersedes the July product flows. The original strategy is preserved in [docs/PRODUCT-2026-07.md](docs/PRODUCT-2026-07.md); the assessment and broader rollout plan are in [UX_UPDATE_PLAN.md](UX_UPDATE_PLAN.md).

## The promise

I can say what matters to me, understand a different perspective, consider one concrete proposal, and see how concerns change it. The group may reach agreement; unresolved disagreement remains part of the result.

The journey is **share a view → understand others → shape a proposal → see the result**. A return visit tells me what needs my attention and what happened while I was away.

## Two clearly labeled modes

### Guided example

A five-minute, restartable walkthrough about car-free Saturdays on Market Street. The visitor selects one of three written perspectives: shop deliveries, disability access, or retaining customer parking. Four additional viewpoints, their votes, and two proposals are curated content. No model calls or persona generation occur.

The visitor sees common ground and an opposing perspective before opening the first proposal. Their own accept/object choices are counted exactly. Round one has two scripted acceptances, so either response leads to a revision. Round two has three scripted acceptances: accepting produces 4/5 agreement; objecting produces 3/5 and a disagreement result. The 75% rule requires four of five participants.

The revision adds morning deliveries and disability access while retaining the parking restriction. If the visitor objected, a private concern card quotes the applicable proposal clause and explains what changed or remains unresolved. First-round acceptance never earns a fabricated objection-attribution badge.

Every screen identifies the scenario as an example. No arbitrary free-text analysis is implied. Saved examples belong in the visitor's My discussions, not the public room list. Result links remain readable by observers.

### Group discussion

Requires a configured live mediator. The mock backend cannot create a custom-topic group discussion. Generated participants are disabled for newly created web discussions.

The host supplies a question, optional context, and a timing preset (10-minute windows together or 24-hour windows asynchronously). A room and invite link exist before the host speaks. Views remain open until the intake deadline, or until the host starts early with at least three contributors. Merely reaching three contributors does not shut the door on other invitees.

Participants submit and may edit their verbatim opinion during intake. When intake closes, membership is fixed. Late arrivals can read the current proposal and eventual result; the interface does not pretend they can still vote.

The mediator maps common ground, supplies a personal opposing perspective, and drafts one proposal. A participant passes through the perspective screen before the response controls. Reading it does not require agreeing with it.

A round ends when all eligible humans respond or its deadline passes. The saved current proposal remains readable after responding. A response can be changed while the window is open. Submissions carry a round number and immutable proposal ID; stale submissions are rejected.

## Decision and participation rules

- Agreement requires at least 75% of all eligible participants, rounded up.
- Missing responses remain in the denominator and are never treated as acceptance.
- Fewer than 75% responding produces **Not enough responses**, not manufactured agreement or disagreement. The round does not silently consume the remaining revisions.
- When enough people respond but fewer than 75% accept, the mediator revises, up to four rounds. The final alternative to agreement is an honest disagreement report.
- Fewer than three contributors at the intake deadline also produces **Not enough responses**. Starting a new discussion is the recovery path in this release.
- A background scheduler progresses rooms without open browser tabs. This implementation runs in one process with SQLite; use a single uvicorn worker.
- All outcomes are advisory. A supermajority is not unanimity, and an objection does not guarantee a further revision if the threshold is already reached.

## Evidence of being heard

Concerns have persistent IDs, original text, author, and originating round. They remain in revision input across rounds. A proposed assessment must identify a known concern and quote text actually present in the revised proposal. The participant sees addressed, partly addressed, not addressed, or no supported mapping yet.

This is the mediator's assessment, not proof that the person is satisfied. Their next response expresses their judgment. This release does not award public civic reputation from model-generated attribution or publish a separate resolved-concern leaderboard.

The example uses curated concern-to-clause mappings. Live assessments are model-generated and require further quality evaluation; exact-quote validation prevents nonexistent evidence but does not establish semantic correctness.

## Identity and visibility

Identity is a generated pseudonym and an HTTP-only cookie. No signup is needed. A person can rename their existing identity. A public pseudonym cannot be used to claim a session: the old name-only login endpoint returns 410.

Continuity is limited to the same browser and its cookies. Cross-device recovery is not implemented. The profile page explains this and no longer offers a destructive “switch” action.

| Information | Visibility |
|---|---|
| Topic, context, verbatim submitted opinions | Public under a pseudonym inside the room |
| Proposal, tradeoffs, common ground, aggregate closed-round results | Public |
| Individual acceptance choice and raw objection | Author and mediator; not returned in public responses |
| Objection-to-clause explanation | Author only |
| Objection themes | May be summarized without attribution in public proposals/reports |
| Raw model prompts/responses | Stored locally for development; excluded from public audit API |
| Model-call metadata and process explanation | Public |
| Personal participation history and name settings | Current browser identity only |

The language model is instructed not to reproduce private objections verbatim or identify their authors in public prose. Raw trace and response redaction is enforced in API shaping. The model's public summaries still require quality/privacy evaluation before an external pilot. Pseudonymity is not proof of personhood.

## Screens and recovery

Home explains the idea and offers the example as the primary first action. Returning participants see action-needed, in-progress, and completed discussions, plus actual recent updates. Group creation is a secondary path with defaults instead of exposed persona controls.

The room has a compact topic header, stage indicator, one primary task, and stable disclosure sections for personal contribution, other views, proposal history, and how the result was produced. Opinion and objection drafts are saved locally. Rerenders preserve active input and focus. Missing rooms, connection loss, mediation failure, late arrival, and insufficient participation have explicit copy and next steps.

Desktop and phone use the same flow. Mobile topic cards stack their title, status, and action. Focus indicators, textarea labels, status announcements, keyboard-operable controls, and reduced-motion styling are included.

## Validation and remaining work

The integration suite exercises all 12 example response/concern combinations, three-person participation, persistent concern mappings, privacy boundaries, identity takeover prevention, deadline advancement without reads, stale requests, and saved-state restoration. Browser walkthroughs cover desktop/mobile entry, perspective, objection, revision, result, and leaving/returning.

Still needed before an external pilot: live-model semantic/privacy quality checks, observation of unfamiliar users, delivery under realistic network/model delays, abuse/cost controls, a broader assistive-technology review, and a recovery mechanism if cross-device continuity is required. These are not prerequisites to trying the deterministic example locally.

Synthetic persona optimization, social feeds, follows, reputation, topic emergence, institutional integrations, and scale infrastructure remain deferred. The existing persona research runner is retained separately from the ordinary web journey.
