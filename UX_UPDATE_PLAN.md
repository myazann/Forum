# Forum: assessment and user experience update plan

Assessment and proposed scope prepared 16 September 2026. See the implementation update below for current status.

**Implementation update, 16 September 2026:** The first complete example journey
and shared participant UI are implemented, along with the small-group lifecycle,
private response shaping, identity corrections, round-bound submissions,
background deadlines, and return feed. [PRODUCT.md](PRODUCT.md) now records the
current contract. The assessment below describes the pre-update baseline.
The example is deterministic; live-group integration checks use a local mediator
fixture. Live model quality, unfamiliar-user observation, broad assistive-technology
testing, cross-device recovery, and external-pilot hardening remain outstanding.

Validation: 15 automated tests pass, including all 12 guided-example branches,
missing responses, stale submissions, private views, supported concern evidence,
and restart/failure recovery. Browser walkthroughs cover the example on desktop
and phone, plus a three-person group with a local test mediator: setup, invitations,
draft recovery, perspective, response editing, revision, and final result. No paid
model calls were made. Python compilation, JavaScript syntax, and whitespace
checks pass.

## 1. Assessment

Forum's idea is clear: help people who disagree develop a concrete proposal they can live with, while preserving an honest record of unresolved disagreement. The distinctive experience is seeing how people's concerns change the proposal.

The repository contains a working deliberation prototype with useful platform foundations. It is ready for a focused product iteration, but the ordinary participant journey is incomplete. Screens largely expose the current engine state; they do not yet consistently explain what happened, what the participant should do, and why their contribution mattered.

### What is already useful

- A compact FastAPI, SQLite, and vanilla JavaScript application with Home, Room, and Profile pages.
- Persistent rooms and cookie-based pseudonymous participation without a signup form.
- Verbatim opinion intake, a common-ground/disagreement model, and personal opposing-perspective summaries.
- One proposal per round, accept/object responses, revision, and consensus or disagreement outcomes.
- Results withheld from the normal room response until the round closes.
- Proposal provenance fields, notifications, civic events, and an inspectable model-call log.
- Swappable model backends and a cost-free mock backend.
- A calm visual direction worth retaining: restrained colors, readable typography, and no reply threads or popularity mechanics.

Keep this foundation. A framework migration, new database, or larger social layer would not resolve the present experience gaps.

### Findings that affect the user story

| Priority | Current behavior | User consequence | Evidence |
|---|---|---|---|
| P0 | First visit emphasizes room creation, simulated citizens, a participant threshold, and numeric phase hours. | A newcomer must configure a process before experiencing its value. | `demo/web/home.html:27–47`; browser walkthrough. |
| P0 | Default threshold is one human; opinion submission starts the room and later opinions are rejected. | “Share the link with friends” breaks as soon as the initiator speaks. Turning off personas alone can produce a one-person “consensus.” | `demo/forum/service.py:86–96,141–169`; late-join HTTP request returned 409. |
| P0 | Proposal and voting controls precede the opposing perspective. The group landscape's common ground and cruxes are not rendered as their own experience. | People can vote without understanding the disagreement, despite the stated product sequence. | `demo/web/room.html:51–58,200–269`; desktop walkthrough. |
| P0 | Mock responses ignore custom topics, mark every human as addressed after round one, and always return the same consensus report. | The cost-free demo can make false claims about listening and outcomes. | `demo/forum/mockdata.py:199–274`; reproduced with unrelated objections and a four-round disagreement outcome. |
| P0 | Revision attribution is a list of participant IDs and a badge, without an objection-to-clause explanation. | “You were heard” is asserted without evidence the participant can assess. | `demo/forum/engine.py:157–181`; `demo/web/room.html:235–246`. |
| P0 before real invitations | Closed responses are public with participant IDs; public audit prompts contain objections. Profiles say publication was chosen, although all opinions are listed. | Privacy expectations conflict with actual behavior. Sealing a tally until close is not ballot privacy. | `demo/forum/service.py:308–380`; `demo/web/profile.html:44`; anonymous API reads reproduced disclosure. |
| P0 before real invitations | A public handle alone can reclaim an existing identity through `/api/login`. | Someone can act as another participant. The “switch” link also logs out without a recovery flow. | `demo/server.py:59–70`; fresh-client identity claim reproduced. |
| P1 | Deadline evaluation happens during advancement/read requests; no independent scheduler exists. Approval uses only submitted responses. | A room can remain open while everyone is away, then report “100%” from one of two eligible people. | `demo/forum/service.py:141–173,325–326`; `demo/forum/engine.py:233–238`; reproduced after a deadline. |
| P1 | Current proposal rendering is inside the unresponded participant branch. Observers and people who have responded cannot read it there. | Waiting and observing become dead ends rather than useful participation states. | `demo/web/room.html:219–257`; source inspection. |
| P1 | Home consumes `needs_you`, but does not display returned outcomes or notifications; only the general room list refreshes periodically. | Leaving and returning loses the personal thread through the deliberation. | `demo/web/home.html:53–76,115`; completed-room return visit. |
| P1 | At 390 px, topic/status/action share one horizontal row; room cards nest substantial padding. | Titles wrap into a narrow stack and proposals require excessive scrolling. | Phone-width browser review of Home and Room. |
| P1 | Drafts survive some rerenders only; actions lack round/version binding and pending-state protection. | Refresh can lose writing; a stale response can target a later round. | `demo/web/room.html:72–75,167–179`; `demo/server.py:150–152`; `demo/forum/service.py:114–128`. |

The documents also disagree. `PRODUCT.md` starts with the newer one-proposal, no-login direction, but retains old elections, confirmation screens, and person-following plans below it. `STRATEGY.md` still treats those earlier mechanics as current. Establish one current product contract before implementation; keep the research vision as background.

## 2. The user story to build

> I arrive at a question I care about. I understand what this group can decide and when. I say what matters to me. I see what other people need and where we already agree. I consider one concrete proposal. If I object, I can see exactly how the next version responds—or why my concern remains unresolved. I can leave and return without losing my place. The final result tells me what the group accepted, who participated, and what remains disputed.

The emotional sequence is: **I understand → I contribute → I understand others → I can influence the proposal → I can judge the result.**

Acceptance should mean “I could live with this,” not enthusiasm for every clause. A supermajority does not mean unanimity. An objection may remain unresolved even when the room reaches its threshold; the product must preserve that concern rather than promise every objection another revision.

### Canonical first demonstration

Use one familiar, bounded question, for example: **“Should our town centre be car-free on Saturdays?”** Give it a short title and a separate context paragraph. Keep the existing AI-gains topic available later as another example.

Build two clearly distinguished ways to use the same participant screens:

- **Try a five-minute example:** a labeled, restartable, guided scenario with fixed example viewpoints and deterministic branches. No generated persona research is required. Let the visitor choose an example concern and see the matching proposal change. Label all example contributions and outcomes. Do not claim that arbitrary free text influenced a prerecorded revision.
- **Start a discussion with your group:** actual participants contribute in their own words and the mediator works from those contributions. Generated personas are off by default. This requires a configured live mediator; the canned backend must not silently present arbitrary-topic output as live deliberation.

An invitation should open the topic directly, with the group's scope, stage, deadline, and current action. It should not route through example selection or setup.

The example should contain both a meaningful revision and an unresolved concern. A second branch should end in a clear disagreement report. This demonstrates the mechanism without presenting agreement as inevitable.

### End-to-end sequence

| Moment | What the participant sees | Main action | Completion signal |
|---|---|---|---|
| Arrive | The question, why the group is discussing it, who is involved, whether this is an example, and what the result means. | Join the discussion / Try the example. | I understand the purpose and scope. |
| Contribute | “What matters most to you?” with a short optional example and a plain explanation of visibility. | Share my view. | My exact words are saved; I know the next step. |
| Understand | What we agree on, the main tradeoff, and a fair explanation of another perspective, linked to source opinions. | Read the proposal. | I can explain a concern other than my own. |
| Respond | One proposal with a brief summary, concrete measures, and explicit tradeoffs. | I could live with this / Something needs to change. | My response is recorded for a named version. |
| Wait | Saved response, readable proposal, how many people have responded, and a closing time. | Return later, or revise my response while open. | I know I can safely leave. |
| Review revision | What changed, why it changed, and what happened to my concern. Previous version remains accessible. | Respond to this version. | I can point to a specific change or an honest unresolved status. |
| Finish | Final proposal, exact participation and support counts, remaining disagreement, and advisory status. | Copy result link / Read how we got here. | I understand both the result and its limits. |
| Return | My discussions: action needed, waiting, and completed results, with a concise explanation of changes since my last visit. | Resume where needed. | No searching through a public room list. |

The perspective step is a reading checkpoint in the interface, not a test of belief. It must never require endorsing another person's view.

## 3. Experience and behavior decisions

### A room needs a stable structure

Use a compact topic header and a stage indicator: **Share views → Understand the room → Consider a proposal → Result**. Show revision numbers inside the proposal stage so the experience does not appear to jump backward through unrelated steps.

Keep one primary task prominent. Under it, provide stable access to **Your contribution**, **Other views**, **Previous versions**, and **How this was produced**. Observers see the same current proposal in read-only form. After submitting, the proposal remains visible alongside the saved response.

Use progressive disclosure for long source opinions and technical audit details. Surface the essential rationale and tradeoffs without making people open a drawer. Keep the current calm identity; reduce nested borders and mobile padding. Move the floating audit button out of the phone's reading area.

### Make revision evidence the centerpiece

Replace the blanket badge with an explanation such as:

> You asked for delivery access. Version 2 allows deliveries before 10 a.m. This adds an exception to the restriction; afternoon deliveries remain unresolved.

Store a stable objection ID, relevant proposal clause, explanation, and mediator assessment: addressed, partly addressed, or not addressed. Preserve unresolved concerns across rounds, including when their author does not respond again. The existing revision prompt uses the immediately preceding round's objections; that is insufficient for a durable concern history.

Let participants indicate whether the change meets their concern. Clearly separate the mediator's assessment from the participant's judgment. Generated attribution must cite a real concern and actual proposal text; the example branch can supply curated mappings. Do not treat a model-generated ID match as verified impact or automatically award public reputation for it.

### Make live room timing understandable

Proposed first group flow: creator supplies a question and short context, selects a simple session preset, and receives an invite link immediately. Participants join while intake is open; the creator may edit their opinion during intake. Explain when intake closes and who counts in each response round.

Use explicit intake and response deadlines plus a background scheduler. Freeze the eligible participant set at round start. For the initial small-group version, recommend acceptance by at least **75% of eligible participants**, rounded up, with nonresponses shown separately and never counted as acceptance. Show both counts: “6 of 8 eligible participants accepted; 7 responded.” Finalize this rule in the product contract before building tally UI.

If participation is too low to support a useful result, show **Not enough responses** rather than interpreting silence as disagreement or generating an artificial consensus. Empty rounds must not automatically consume all revisions. A creator must not accidentally launch a real group deliberation with only themselves.

Defer mid-round admission for this release. Late visitors should see the proposal, a clear explanation that this discussion is closed to new participants, and useful options to observe or start a related discussion. Do not offer “Take your position” on a room that cannot accept it.

### Align trust promises with behavior

Keep anonymous entry, but explain: the opinion is visible under a pseudonym; the acceptance choice is private; objections inform the mediator and may be summarized for the group. Choose and disclose the exact objection-publication policy before implementation.

Remove handle-only identity takeover before inviting real participants. Preserve the current cookie identity and use an explicit recovery mechanism if cross-device access is needed; choosing a display name must not switch accounts. Explain same-browser continuity and provide a real display-name edit action.

Separate the public process explanation from private raw traces. Public provenance can show source opinions, proposal changes, aggregate results, model information, and suitably redacted explanations. Protect raw prompts and individual responses across every API and audit surface, not just the rendered page. Public profile aggregation should require an explicit choice, or be deferred in favor of a private “My discussions” page.

Bind submissions to a round and proposal version, reject stale requests clearly, and prevent duplicate submissions. Save writing locally with appropriate clearing after submission; preserve input and focus during background updates. Distinguish missing rooms, lost connectivity, and failed mediation in human language. End-user error states should not display server commands.

## 4. Implementation sequence

These are ordered milestones, not separate projects. The first delivery should be a complete example journey through a revised result; a redesigned Home page alone does not meet the goal.

| Order | Deliverable | Main files/areas | Exit condition |
|---|---|---|---|
| 1 | Current product contract, scenario, screen sequence, and all participant/observer/waiting/error states. Retire conflicting product instructions. | `PRODUCT.md`, `STRATEGY.md`, this plan. | One agreed story and explicit visibility, timing, and outcome rules. |
| 2 | Trustworthy, restartable example: scoped topic, fixed viewpoints, meaningful concern branches, accurate result calculations, consensus and disagreement paths. | `forum/mockdata.py`, `forum/engine.py`, `forum/service.py`, `server.py`. | No unrelated-topic output, fabricated attribution, or report/tally mismatch. No persona generation needed. |
| 3 | Complete participant interface from entry through perspective, proposal, objection, revision evidence, and result. Build phone layouts as part of this work. | `web/home.html`, `web/room.html`, `web/static/forum.js`, `web/static/forum.css`; attribution fields in engine/prompts. | A first-time visitor completes the example unaided and explains what their selected concern changed. |
| 4 | Small-group session flow and return journey: invites, intake, deadlines, eligible-participant accounting, saved drafts, response versioning, My discussions, and surfaced outcomes. Close identity/privacy gaps before real invitations. | `server.py`, `forum/service.py`, `forum/db.py`, `forum/engine.py`, shared shell, Home/Profile. | Real participants can join, leave, return, object, and reach an accurate result with no generated participants or facilitator console. |
| 5 | End-to-end hardening and usability review across both modes. Update run/demo instructions. | Focused integration/browser checks, responsive/accessibility pass, `README.md`. | Both happy and failure paths pass; unfamiliar users understand the story without narration. |

Reuse the current service/engine split. Introduce explicit scenario mode, round identifiers, lifecycle timestamps, participation counts, and structured concern/change mappings as needed. Extract reusable rendering only where it prevents divergence between demo and group use. Keep polling initially if it is stable; SSE is not a prerequisite for this experience.

### Proposed acceptance checks

- Three unfamiliar people independently complete the guided example in roughly five minutes and can explain the other side, a proposal change, and the meaning of the outcome. This is a target to validate, not a measured result.
- Example branches include acceptance, a concern accommodated by revision, a concern still unresolved, and a disagreement outcome. All text and counts match the selected path.
- A group of at least three distinct browser identities completes the real-participant flow with personas disabled; one person leaves and returns during a round.
- The same proposal is readable before and after responding, and by an observer. No individual acceptance tally is exposed while a round is open.
- Refresh and reconnect preserve unsent writing and saved responses. Double-clicks and submissions from an older version cannot vote on a new proposal.
- A deadline advances without a page being open, survives a server restart, and cannot turn absent participants into supporters.
- Closed results agree across the report, room, Home, and shared result. Remaining concerns stay visible even when their authors are in the minority.
- Identity and privacy checks cover anonymous room/audit/profile reads and attempted reuse of another person's public handle.
- At phone widths, topic cards stack naturally and primary controls remain usable. Keyboard navigation, textarea labels, focus after updates, screen-reader status announcements, contrast, and reduced motion are checked.
- Empty rooms, insufficient participation, unknown URLs, mediator failures, and late arrivals all have understandable next steps.

## 5. Defer

Synthetic persona generation and optimization; persona profiles and fidelity improvements; people-following and social feeds; topic emergence; reputation expansion; institutional dashboards; large-scale identity and sybil systems; new model vendors; a frontend framework migration; elaborate landscape graphics; and streaming infrastructure.

Keep existing persona code available for later research. It is not on the critical path for this iteration. The relevant evaluation now is whether real people understand the process and can see faithful treatment of their concerns.

## 6. Inspection scope and limitations

Reviewed all three project documents, the server, service, persistence, engine, relevant prompts/mock data, and all frontend pages/styles/helpers. Inspected the persona/evaluation structure to understand its role; did not rerun persona research.

Ran the application with `FORUM_BACKEND=mock` and an isolated database at `/tmp/forum-ux-review-20260916.db`; the project's deliberation data was not used. Completed a three-round browser journey, reviewed desktop and 390 px layouts, and exercised two-participant/observer HTTP flows, four-round disagreement, sealed responses, deadline behavior, and handle-only login.

The mock consensus journey reported 87.5% in prose while the actual room showed 8/9 acceptance. The disagreement test ended with 0% acceptance after four rounds but received the same consensus prose. A custom town-centre question produced the AI-dividend proposal. These findings apply to the mock backend; live mediator quality and real-network latency remain unassessed.

No application code was changed. No existing automated application test suite was found; the checked-in evaluation results focus on persona fidelity. The local virtual environment's `uvicorn` executable references a previous folder path; launching through `./demo-venv/bin/python -m uvicorn` worked. This is a local setup issue to clarify in run instructions, not a reason to change the stack.
