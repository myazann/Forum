# Forum — Strategy & Build Plan

*Working document, July 2026. Companion to the "Idea" page from the Worldbuilding AI Futures course and the Existential Hope competition submission. The product/user-journey side — entry points, feed, follows, data model, phased platform plan — lives in [PRODUCT.md](PRODUCT.md).*

## 1. What we are building

**Forum is an AI-mediated deliberation and consensus engine.** Citizens submit opinions on a topic in free form. The system maps the argument landscape, generates a middle-ground proposal, shows each participant the strongest version of the other side, collects critiques and ratings, and iterates the proposal until a supermajority approves — or until it can honestly report where agreement is impossible. Topics can emerge bottom-up when enough people raise them. The process is transparent, replayable, and bounded by human-rights guardrails.

The 2035 vision (Global Forum Council, billions of participants) is the north star, not the spec. What we build now is the smallest system that demonstrates the core claim: **an AI mediator can take a group of disagreeing people from raw opinions to a concrete proposal that a supermajority genuinely endorses — and can show its work.**

## 2. Prior art — what exists and where Forum differs

We are not starting from zero. The single most important reference is DeepMind's **Habermas Machine** ([paper](https://www.science.org/doi/10.1126/science.adq2852), [code + data](https://github.com/google-deepmind/habermas_machine)), which validated the core mechanic with 5,700+ UK participants:

- Participants write opinions on a policy question.
- An LLM generates **multiple candidate group statements**; a **reward model predicts each participant's ranking** of the candidates; a social-choice rule (Schulze method) picks the winner.
- Participants critique the winning statement; the LLM generates revised candidates from opinions + critiques; a second election picks the final statement.
- Result: participants preferred the AI mediator's statements to those of human mediators, group agreement measurably increased, and minority views were not steamrolled — critiques demonstrably shaped revisions.

DeepMind released the prompted pipeline (works with any modern LLM) and ~450 MB of human preference data. **We should treat this as our reference implementation and eval set**, not reinvent it.

Other systems worth borrowing from:

| System | What it does | What we take |
|---|---|---|
| [Polis](https://pol.is) (used by vTaiwan) | Vote agree/disagree on short statements; PCA clustering reveals opinion groups and cross-group consensus statements | Opinion-landscape visualization; "notice what all clusters agree on"; no-reply-button design that avoids outrage dynamics |
| [Talk to the City](https://ai.objectives.institute/talk-to-the-city) (AI Objectives Institute) | LLM clustering + reports over large-scale freeform public input | Intake and argument-mapping patterns at scale |
| Community Notes (X) | Bridging-based ranking: a note surfaces only if people who usually disagree both endorse it | The **bridging principle** as an anti-polarization scoring rule for proposals |
| Stanford Online Deliberation Platform | Structured small-group video deliberation with automated moderation | Process structure for a later "humans actually talk" layer |
| Decidim / Consul | Municipal participation platforms | Governance/institution interface patterns, not tech |

**Forum's differentiation** is the combination: (1) a *full consensus loop* that iterates proposals over multiple rounds against an explicit approval threshold rather than producing a one-shot statement; (2) *personalized perspective feedback* — every participant sees a steelman of the other side, not just the group output; (3) *bottom-up topic emergence*; (4) *transparency as a first-class feature* (every synthesis step logged and replayable); (5) an eventual *institution interface*. Nobody has shipped that combination.

## 3. Core components

Roughly in dependency order. Components 1–6 are the demo; 7–12 are the platform.

1. **Opinion intake & position cards.** Freeform input (text first; voice later). An LLM condenses each opinion into a canonical "position card" (claim, reasons, underlying values, red lines) that **the participant must confirm** before it counts. This confirmation step is a legitimacy requirement, not UX polish — the system must never misrepresent what someone said.

2. **Argument mapping.** Embed position cards, cluster them (k-means/HDBSCAN), have an LLM label each cluster and extract the shared values and crux disagreements between clusters. Output: the *opinion landscape* — the map both the mediator and the participants see.

3. **Mediator (synthesis engine).** Generates k candidate proposals from the landscape. Each candidate must be concrete (someone could act on it), must cite which clusters/opinions it draws from, and must state its trade-offs explicitly. Vague crowd-pleasers are a failure mode to engineer against, not a success.

4. **Election & preference aggregation.** Participants rate/rank candidates. Start with simple approval ratings; adopt Habermas-Machine-style predicted rankings + Schulze as we scale; add a bridging bonus (Community-Notes-style) so proposals endorsed *across* clusters beat proposals loved by one side.

5. **Critique → revision loop.** Collect critiques of the leading proposal, feed them with the landscape back into the mediator, produce revised candidates, re-elect. Stopping rules: approval ≥ threshold (75% target) with engagement quorum, or max rounds reached — in which case the output is a **dissensus report**: what everyone agreed on, what remains contested and why. An honest map of disagreement is a valid product, not a failure.

6. **Consensus metrics.** Per round: approval rate, participation rate, approval-by-cluster (minority representation), opinion movement (are positions converging or just the proposal mutating?), plateau/deadlock detection.

7. **Perspective feedback.** For each participant: "here is where your position sits, here is the strongest case for the people who disagree with you, here is what you both actually want." This is the feature that answers the strongest critique of AI-mediated consensus (see §5.2).

8. **Topic emergence.** Continuously cluster raised topics; when a critical mass of distinct participants raise the same theme, a deliberation opens automatically.

9. **Guardrails / constitution.** A published rule set (UDHR-derived) applied by an auditable classifier. Excluded opinions get an explanation and an appeal path. The filter itself must be deliberated eventually — a constitution nobody consented to is a pressure point (§5.7).

10. **Transparency & audit layer.** Every prompt, every candidate, every ranking, every revision stored and publicly replayable. Bias evals run continuously (does the mediator systematically favor certain framings/demographics?). This is the main defense against "who controls the mediator."

11. **Identity & participation integrity.** One person, one voice; sybil resistance. Unsolved in general and *the* hard dependency for anything beyond invited pilots. Punt early (invite-only), design for it later.

12. **Institution interface.** Reports for policymakers, commitment tracking, the transparency-enforcement agent from the blueprint. Phase 4 territory.

## 4. Architecture sketch

```
                    ┌─────────────────────────────────────────┐
                    │            Deliberation Engine           │
                    │  (state machine: INTAKE → MAPPING →     │
                    │   SYNTHESIS → ELECTION → CRITIQUE →      │
                    │   REVISION → …  → CONSENSUS/DISSENSUS)   │
                    └───────┬─────────────────────┬───────────┘
   Participants ──────► Intake API           LLM Service Layer ──► Claude API /
   (humans + simulated  Position cards       (synthesis, steelman,   claude CLI /
    personas)           Ratings, critiques    clustering labels,     mock backend
                                              persona simulation)
                    ┌───────┴─────────────────────┴───────────┐
                    │   Store: opinions, cards, clusters,      │
                    │   proposals, ratings, critiques, rounds  │
                    │   (SQLite → Postgres)  + full audit log  │
                    └──────────────────┬───────────────────────┘
                                       │
                              Web UI: landscape map, proposal
                              cards, approval meters, round
                              timeline, replay/audit view
```

Two design decisions that matter early:

- **The simulation harness is a core component, not a testing hack.** LLM-persona participants let us run hundreds of deliberations during development, stress-test mechanism design (holdout coalitions, trolls, sycophantic convergence), and evaluate mediator quality cheaply before any human sees the system. It is also how the demo is compelling on day one.
- **Swappable LLM backends** (API / CLI / mock / multi-model ensemble). Independence from any single model vendor is a legitimacy requirement long-term (§5.1), and a practical one now.

## 5. Pressure points

These are the places where the idea can break. Each gets a design answer, not just acknowledgment.

**5.1 Who controls the mediator?** (the risk you flagged in the blueprint). The mediator's prompts, model choice, and clustering decisions all encode power. *Answers:* radical transparency (open prompts, replayable runs), multi-model ensembles with disagreement surfaced, published bias evals, and eventually third-party audit access. Note this is also the GFC's institutional job in your world — the tech and the institution answer the same threat.

**5.2 Consensus without deliberation — the "hollow consensus" critique.** [Rob Horning's essay](https://robhorning.substack.com/p/habermas-machines) argues systems like this let people *avoid* engaging each other: positions go in, a statement comes out, and the mutual-understanding work that makes people able to live with outcomes never happens; the result is an illusion of collective action over atomized individuals. This is the strongest intellectual attack on Forum and it deserves a real answer. *Answers:* perspective feedback is mandatory in the loop (you rate a proposal only after seeing the other side's steelman); measure opinion *movement*, not just approval; surface disagreement prominently (dissensus reports are a first-class output); and long-term, use the AI to *scaffold* human-to-human deliberation (structured small groups feeding the global loop) rather than replace it. Forum should market itself as a disagreement-mapping machine that sometimes finds consensus, not a consensus vending machine.

**5.3 Deadlock and strategic holdouts** (also flagged in your blueprint). A 75% threshold invites bloc veto: reject until you get concessions. *Answers:* bounded rounds with a published dissensus report as the fallback (removes the holdout's leverage — blocking no longer buys silence, it buys a public record that "group X blocked on Y"); per-round rejection rationales required to count as rejection; possibly a threshold that decays slightly per round. This needs simulation before pilots — it's exactly what the persona harness is for.

**5.4 Lowest-common-denominator proposals.** Optimizing for approval yields mush ("we should balance innovation and safety"). *Answers:* concreteness requirements enforced at generation (proposals must be actionable and falsifiable); rate with "could you live with it / would you defend it" rather than "do you like it"; bridging bonus rewards specific proposals that cross clusters.

**5.5 Representation and scale.** Everyone-rates-everything dies beyond ~10³ participants, and self-selection skews who shows up. *Answers:* hierarchical aggregation (cluster-level synthesis feeding global synthesis); stratified sampled panels for rating duty (sortition — with the legitimacy trade-offs acknowledged); participation-gap reporting as a standing metric.

**5.6 Sybils and astroturf.** LLMs make fake grassroots nearly free; topic emergence (§3.8) is especially attackable. *Answers for now:* invite-only pilots, rate limits, provenance on every opinion. *Real answer later:* identity infrastructure (national eID, proof-of-personhood) — acknowledged as an external dependency the GFC would own in-world.

**5.7 Preference laundering and guardrail legitimacy.** Summarization can subtly shift what people said; the human-rights filter can become unaccountable censorship. *Answers:* user-confirmed position cards (§3.1); citations from every proposal back to the opinions it drew from; published filter rules with explanations and appeals; the filter's rule set itself eventually goes through Forum.

**5.8 The evaluation problem.** "It works" must be defined before scaling. *Metrics:* approval and approval-by-cluster; perceived fairness and perceived being-heard (survey); informed opinion shift (with a control for conformity pressure); minority-representation score; statement quality vs. human mediators (the Habermas Machine dataset gives us a benchmark to compare against directly).

**5.9 Legitimacy gap.** Advisory tools get ignored; binding tools get captured. *Answer:* start explicitly advisory with a commitment-tracking layer ("the council responded to this consensus by X") and grow authority with track record — this mirrors the vTaiwan trajectory.

## 6. Tools & stack

- **LLM:** Claude API — Sonnet-class for synthesis/steelman/persona work, Haiku-class for high-volume per-participant operations; Batch API for mass rating simulation; structured outputs for position cards and proposals. For local development without an API key, the `claude` CLI works as a backend on a subscription. Mock backend for deterministic tests.
- **Embeddings & clustering:** voyage or open sentence-transformers embeddings; k-means/HDBSCAN; 2-D projection (UMAP/PCA) for the landscape map. (Demo can start with LLM-only clustering at small n.)
- **Reference code/data:** `google-deepmind/habermas_machine` (prompted pipeline + preference data — our eval benchmark), `compdemocracy/polis`, Talk to the City reports pipeline, Community Notes scoring code (open source).
- **App stack:** Python + FastAPI, SQLite (→ Postgres), server-rendered HTML + vanilla JS for the demo (React only when the UI earns it). Everything replayable from the audit log.

## 7. Roadmap

**Phase 0 — Working demo (now).** One topic, ~8–12 simulated diverse personas plus the human user, full loop: opinions → landscape → candidate proposals → election → critiques → revision → consensus/dissensus, with a dashboard showing rounds, clusters, approval-by-cluster, and an audit trail. *Exit criterion: a stranger can watch a deliberation converge in under five minutes and inspect why the proposal changed between rounds.*

**Phase 1 — Mediator quality (2–4 weeks).** Adopt the Habermas Machine candidate-generation + election structure; build the eval harness against their released human-preference data; add user-confirmed position cards and steelman perspective feedback; run mechanism-design experiments in simulation (holdout coalitions, threshold schedules, bridging bonus on/off).

*Update (mid-July 2026): three Phase 1 items shipped in the demo — user-confirmed position cards (§3.1), the Habermas-Machine two-candidate election structure (§3.3–3.4), and steelman-before-ballot (§5.2) — plus a redesigned interface with live phase progress, approval trajectory, and a replayable audit drawer.*

*Update (2026-07-15): the demo became a platform. [PRODUCT.md](PRODUCT.md) §6 now owns the product/platform roadmap (Phases A–D); this document's phases below remain the engine/research roadmap, and the two interleave: platform Phase A (multi-user core — pseudonymous users, SQLite persistence, quorum-driven phases, N-human deliberations) shipped and passed its exit test, which means the Phase 2 pilot below now has its infrastructure. Remaining engine work unchanged: the Habermas Machine dataset eval harness, probe validation in the fidelity harness, and the §5.8 metrics instrumented for a real cohort.*

*Status (July 2026): the simulation-credibility prerequisite is in place. Personas are structured cards (interests, explicit red lines, concession conditions) judged in isolated calls with a mandatory red-line check before each verdict, and their fidelity is measured by a probe harness (`demo/forum/fidelity.py`): red-line violation → reject, violation under social pressure → still reject, genuine concession → accept, vague crowd-pleaser → not accept, plus consistency. On gpt-5-mini: 39/40 for structured cards vs 38/40 for prose bios, with the residual failure adjudicated as a probe-generation error. A real-backend 4-round run produced non-monotonic approval (67→67→44→78%) and persistent faithful holdouts — the loop is not converging by sycophancy.*

**Phase 2 — First real pilot (1–2 months).** 10–50 real participants — the Existential Hope / worldbuilding course community is the natural first cohort, and the competition context is a story asset. One genuinely contested topic. Measure §5.8 metrics. Publish the run (transparency as marketing).

**Phase 3 — Scale mechanics (months 3–6).** Hierarchical aggregation, sampled rating panels, topic emergence, deadlock handling hardened by simulation; identity design document.

**Phase 4 — Institution layer.** Government/organization interface, commitment tracking, third-party audit access, multi-language.

## 8. What we deliberately punt on

Proof-of-personhood at scale, binding authority, voice/multimodal intake, the transparency-enforcement agent, and anything requiring the GFC to exist. They stay in the worldbuild until the core loop has earned real users.

---
*Next artifact: `demo/` — Phase 0 implementation.*
