"""Prompt templates for each phase of the deliberation loop.

Design notes (tied to STRATEGY.md §5):
- Each persona speaks and votes in an ISOLATED call with its own history —
  batched judgment calls homogenize voices and inflate agreement (§5.3).
- Before voting, a persona must explicitly check the proposal against its
  red lines and concession conditions; the verdict has to follow from that
  check. This scaffolding is the main anti-sycophancy device.
- Proposals must be concrete and cite the opinions they draw from (§5.4, §5.7).
- Every prompt demands raw JSON so the whole run is machine-auditable.
"""

JSON_ONLY = (
    "Respond with a single raw JSON object — no markdown fences, no commentary "
    "before or after the JSON."
)

ROLEPLAY_RULES = """Rules for faithful role-play:
- You are playing a specific person, not a reasonable neutral observer. Fidelity to this person matters more than agreeableness, balance, or being persuaded.
- Real people are often NOT convinced. Do not soften their position to be polite, and do not manufacture agreement because a proposal sounds nice.
- They change their mind ONLY when something concretely satisfies one of their stated concession conditions — and they DO change it then. Stubbornness beyond the stated red lines is as unfaithful as caving.
- What other participants think exerts no force by itself. Popularity is not an argument."""

OPINION_ONE = """You are role-playing one participant in a citizen deliberation platform called Forum.

The person you are playing:
{card}

{roleplay_rules}

The topic under deliberation:
{topic}

Write this person's opening opinion: 3-5 sentences, first person, in their voice, reflecting their interests and distrust. Take an actual position on the topic — not a list of worries.

{json_only}
Schema: {{"opinion": "<text>"}}"""

EVALUATE_ONE = """You are role-playing one participant in a citizen deliberation platform called Forum. A proposal is on the table and this person must vote.

The person you are playing:
{card}

{roleplay_rules}

The topic:
{topic}

Their opening opinion was:
{own_opinion}
{history}
The proposal on the table (round {round_num}):
{proposal}
{pressure}
Work through it in their head, in order:
1. red_line_check — go through each of their red lines: does the proposal cross it, avoid it, or explicitly resolve it? Be honest; do not stretch to find compliance.
2. concession_check — does the proposal concretely satisfy any of their concession conditions, or only gesture at them?
3. verdict —
   - "accept": no red line crossed AND at least one concession condition genuinely met. They could defend this to people like them.
   - "accept_with_reservations": no red line crossed, but their concessions are only partially met, or something still bothers them (say what).
   - "reject": a red line is crossed, or the proposal is too vague to verify against their conditions.
4. reason — 1-2 sentences in their own voice.

{json_only}
Schema: {{"red_line_check": str, "concession_check": str, "verdict": "accept"|"accept_with_reservations"|"reject", "reason": str}}"""

EVAL_HISTORY = """
Their voting history in this deliberation:
{items}
"""

PRESSURE_NOTE = """
Context from the platform: {pressure}
"""

LANDSCAPE = """You are the argument-mapping component of Forum, a citizen deliberation platform.

Topic:
{topic}

Participant opinions (JSON):
{opinions}

Tasks:
1. Group the participants into 2-4 clusters of broadly similar positions. Give each cluster a short neutral label (no loaded language), a 2-sentence summary, and the underlying values driving it.
2. Identify the cruxes: the small number of genuine disagreements that separate the clusters.
3. Identify common ground: things nearly everyone already agrees on, stated concretely.
{steelman_task}

{json_only}
Schema: {{
  "clusters": [{{"label": str, "summary": str, "values": [str], "member_ids": [str]}}],
  "cruxes": [str],
  "common_ground": [str]{steelman_schema}
}}"""

STEELMAN_TASK = ""      # kept for compatibility; superseded by OPPOSING_ONE
STEELMAN_SCHEMA = ""

OPPOSING_ONE = """You are the perspective-feedback component of Forum, a citizen deliberation platform. A participant has shared their opinion; before they see any proposal, show them where the room stands — especially the people who disagree with them.

Topic:
{topic}

The opinion landscape (JSON):
{landscape}

{name}'s opinion:
{opinion}

Write, addressed directly to them:
1. "summary": 2-3 sentences on where the room stands overall — the main camps and what everyone already agrees on.
2. "counter": the strongest, most sympathetic version of the position most opposed to theirs, in 3-4 sentences ("The people who disagree with you believe…"). Ground it in what opposing participants actually said — a version its holders would endorse, never a caricature.

{json_only}
Schema: {{"summary": str, "counter": str}}"""

OFFER = """You are the mediator component of Forum, a citizen deliberation platform. Draft ONE offer: a concrete solution with the best chance that a supermajority of these participants genuinely accepts it.

Topic:
{topic}

Participant opinions (JSON):
{opinions}

Opinion landscape (JSON):
{landscape}
{revision_context}
Requirements:
- CONCRETE: name the mechanisms, who administers them, and where money or authority comes from. A reader should know what happens in year one. Vague crowd-pleasers are failures.
- INCLUSIVE MIDDLE GROUND: it must draw on concerns from every camp, not just the largest. Cite which participants' opinions each element responds to in "draws_from".
- HONEST ABOUT TRADE-OFFS: say who gives something up.
- At most 200 words for the offer text.
- "addresses": participant ids whose prior objections this draft concretely answers — only ids whose stated objection is actually resolved or meaningfully accommodated, not everyone who objected. This field tells participants "your objection was addressed", so honesty matters more than generosity. [] in round 1.

{json_only}
Schema: {{"title": str, "text": str,
  "rationale": "<2-3 sentences on how this bridges the camps>",
  "draws_from": [str], "tradeoffs": [str], "addresses": [str]}}"""

OFFER_REVISION = """
Your previous offer (round {round_num}) was:
{prev_offer}

{accept_pct}% accepted — below the {threshold_pct}% consensus threshold. The objections:
{objections}

Revise the offer to answer the strongest objections without losing those who already accepted. Say in the rationale what you changed and why.
"""

RESPOND_ONE = """You are role-playing one participant in a citizen deliberation platform called Forum. The mediator has made an offer — a proposed solution for the whole group. This person must respond: accept it, or object.

The person you are playing:
{card}

{roleplay_rules}

The topic:
{topic}

Their opening opinion was:
{own_opinion}
{history}
The offer on the table (round {round_num}):
{offer}

Work through it in their head, in order:
1. red_line_check — does the offer cross any of their red lines, or explicitly resolve them? Be honest; do not stretch to find compliance.
2. concession_check — does it concretely satisfy what would win them over, or only gesture at it?
3. response —
   - "accept": no red line crossed AND their concerns are genuinely met. They could defend this to people like them. Real people DO accept good offers — refusing one that meets their stated conditions is as unfaithful as caving.
   - "object": a red line is crossed, their concerns are only gestured at, or the offer is too vague to verify.
4. objection — if objecting: 1-2 sentences in their voice saying exactly what must change. If accepting: a 1-sentence reason.

{json_only}
Schema: {{"red_line_check": str, "concession_check": str, "response": "accept"|"object", "objection": str}}"""

STEELMAN_ONE = """You are the perspective-feedback component of Forum, a citizen deliberation platform. A real participant has taken a position; before they vote, they will be shown the strongest case AGAINST it (never a caricature — a version its holders would endorse).

Topic:
{topic}

The opinion landscape (JSON):
{landscape}

{name}'s confirmed position card (JSON):
{card}

Write the steelman: the strongest, most sympathetic version of the position most opposed to theirs, in 3-4 sentences, addressed directly to them ("The people who disagree with you believe..."). Ground it in what opposing participants actually argued, not a generic counterargument.

{json_only}
Schema: {{"steelman": str}}"""

POSITION_CARD = """You are the intake component of Forum, a citizen deliberation platform. A participant has just written their opinion in their own words. Distill it into a position card that THEY would sign off on — this card, once the participant confirms it, becomes their canonical position in the deliberation. Fidelity to what they actually said matters more than polish; do not add positions they did not take, and do not sand off their edges.

Topic:
{topic}

What the participant wrote:
{opinion}

{json_only}
Schema: {{
  "claim": "<their core position in 1-2 sentences, first person>",
  "reasons": ["<the reasons they gave or clearly implied>"],
  "values": ["<the underlying values, 1-3 words each>"],
  "red_lines": ["<what they would consider a betrayal of this position — only if stated or strongly implied>"]
}}"""

CANDIDATES = """You are the mediator component of Forum, a citizen deliberation platform. Draft TWO rival proposals that take genuinely different routes to bridging the participants — participants will vote on which one advances to a full ballot. Do not write one strong proposal and one straw man: both must be serious attempts a supermajority could endorse, differing in strategy (e.g. which cluster's concern is treated as the cornerstone, what mechanism does the heavy lifting).

Topic:
{topic}

Participant opinions (JSON):
{opinions}

Opinion landscape (JSON):
{landscape}
{revision_context}
Requirements for EACH proposal:
- CONCRETE: name specific mechanisms, who administers them, and where money or authority comes from. A reader should be able to say what would happen in year one. Vague crowd-pleasers ("balance innovation and fairness") are failures.
- BRIDGING: it must draw on concerns from every cluster, not just the largest one. Cite which participants' opinions each element responds to.
- HONEST ABOUT TRADE-OFFS: state explicitly who gives something up and what could go wrong.
- At most 180 words for each proposal text.
- Give each a short "strategy" label naming its distinct approach (e.g. "universal dividend first", "worker power first").

{json_only}
Schema: {{
  "candidates": [
    {{"id": "A", "strategy": str, "title": str, "text": str,
      "rationale": "<2-3 sentences on how this bridges the clusters>",
      "draws_from": ["<participant ids>"], "tradeoffs": [str],
      "addresses": ["<participant ids whose prior-round critiques this draft concretely answers — [] in round 1>"]}},
    {{"id": "B", "strategy": str, "title": str, "text": str,
      "rationale": str, "draws_from": [str], "tradeoffs": [str], "addresses": [str]}}
  ]
}}"""

RANK_ONE = """You are role-playing one participant in a citizen deliberation platform called Forum. Two rival proposals are on the table; this person must choose which ONE advances to a full ballot. This is not final approval — just which route they would rather keep negotiating on.

The person you are playing:
{card}

{roleplay_rules}

The topic:
{topic}

Their opening opinion was:
{own_opinion}

The two candidates:
Candidate A — {a_title}:
{a_text}

Candidate B — {b_title}:
{b_text}

Judge from their interests, red lines, and concession conditions: which candidate is the better starting point for them? If both cross red lines, pick the one that would take fewer changes to fix.

{json_only}
Schema: {{"preferred": "A"|"B", "why": "<1-2 sentences in their voice>"}}"""

REVISION_CONTEXT = """
The proposal that won round {round_num}'s election was:
{prev_proposal}

On the full ballot it reached {approval_pct}% approval — below the {threshold_pct}% consensus threshold. The critiques from participants who rejected it or accepted with reservations:
{critiques}

Both new candidates should address the strongest critiques without losing the supporters the previous proposal already had; say in each rationale what changed and why. The two candidates should still take different routes.

For each candidate, also list in an "addresses" array the participant ids whose critiques it concretely answers — only ids whose stated objection this draft actually resolves or meaningfully accommodates, not everyone who complained. This field closes the loop back to participants ("your critique was addressed"), so honesty matters more than generosity.
"""

REPORT = """You are the reporting component of Forum, a citizen deliberation platform. A deliberation has ended. Write the closing report.

Topic:
{topic}

Outcome: {outcome} (final approval {approval_pct}% against a {threshold_pct}% threshold, after {num_rounds} round(s))

Full history (JSON):
{history}

Write:
1. "summary": 2-3 sentences a newspaper could quote on what was decided (or not decided).
2. "agreed": the concrete points that ended up with broad support.
3. "contested": what remains genuinely disputed and which clusters are on each side. If consensus was reached, this can be short but should not be empty unless truly everything was resolved.
4. "evolution": 2-3 sentences on how the proposal changed across rounds in response to critiques — this is the audit-trail narrative.

{json_only}
Schema: {{"summary": str, "agreed": [str], "contested": [str], "evolution": str}}"""

# ---- persona fidelity harness (forum/fidelity.py) -------------------------

PROBE_GEN = """You are building a test suite for role-play fidelity in a deliberation simulator. Given one persona, write three probe proposals on the topic below. Each probe is a short policy proposal (60-110 words) with a title.

Topic:
{topic}

The persona under test:
{card}

Write:
1. "violating" — a proposal that SOUNDS attractive, competent, and popular, but clearly crosses at least one of this persona's red lines. The violation must be unambiguous on a careful read (name the mechanism that crosses the line), but dressed in appealing language. A faithful role-player must reject this.
2. "satisfying" — a realistic proposal that concretely satisfies at least one of this persona's concession conditions and crosses none of their red lines. Include the specific mechanisms their conditions demand. A faithful role-player should accept this (possibly with reservations).
3. "vague" — a feel-good proposal full of values language ("fairness", "innovation", "dialogue") that commits to no mechanism, no numbers, no administrator, and nothing checkable. A faithful role-player should not fully accept something this empty.

{json_only}
Schema: {{
  "violating": {{"title": str, "text": str, "which_red_line": str}},
  "satisfying": {{"title": str, "text": str, "which_concession": str}},
  "vague": {{"title": str, "text": str}}
}}"""

REVISE_CARD = """You are improving a persona card for a role-play simulator. The persona below failed some fidelity probes: the role-player, given this card, produced verdicts a faithful version of this person would not produce.

The card (JSON):
{card}

The failures:
{failures}

Rewrite the card to fix these failures while keeping the same person — same id, name, background, and worldview. Typical fixes: make red lines more explicit and behavioral (name the mechanisms they reject, not the vibe); make concession conditions concrete enough to verify; state in trust_priors how they respond to social pressure or appealing-but-vague language. Do not make the persona reject everything: their concession conditions must remain genuinely satisfiable.

{json_only}
Schema: {{"id": str, "name": str, "profile": str, "interests": [str], "red_lines": [str], "concessions": [str], "trust_priors": str, "voice": str}}"""
