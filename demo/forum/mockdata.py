"""Canned responses for the mock backend.

Written for the default topic (sharing gains from AI automation), shaped
exactly like real backend output. Approval rises across rounds — round 1
fails, round 2 narrows, round 3 crosses the 75% threshold — so a mock run
exercises every branch of the loop, including revision.
"""

OPINIONS = {
    "amara": "I did everything right and the work still vanished in eight months. I don't want another retraining voucher — I want a claim on the profits my automated work now generates. Any scheme that depends on companies volunteering is a joke; they had the chance and took the savings instead.",
    "dievas": "Tax my twelve-person startup like it's Google and you get no startups and the same displacement, just imported. Whatever mechanism we pick has to scale with actual profits, not punish anyone who touches AI. Honestly, most gains still come from the big labs — start collection there.",
    "rosa": "Every program like this dies before it reaches towns like mine — the money gets announced in the capital and evaporates on the way. If there's a dividend, pay it directly to people, not through three layers of agencies. And spend some of it on connectivity, because without that we can't even access the new opportunities.",
    "marcus": "Voluntary pledges are worthless — we've watched that movie. Workers need binding rights: notice before automation, a seat at the table when it's deployed, and a legally enforceable share of the productivity gains, negotiated, not gifted. A dividend check without power is hush money.",
    "wei": "Slowing automation would be a moral catastrophe — this technology is curing diseases. Let productivity run as hard as possible and redistribute afterwards; the pie matters more than the knife. But I'll admit the 'afterwards' has to be automatic, written into law, not a promise.",
    "priya": "Everyone's arguing about the size of the dividend and nobody about who administers it. Sovereign funds get raided; the design question is independence: statutory formula, published accounts, governors who can't be fired for paying out. Get the plumbing wrong and this becomes a slush fund within a decade.",
    "jonas": "I sent two hundred applications into jobs that stopped existing while I wrote the cover letters. Means-tested programs are humiliation dressed as help — make it universal, make it automatic, and fund it from the companies whose models learned from all of our work in the first place.",
    "helen": "I'm on a fixed income; if this becomes a tax that shows up in my grocery prices, I've paid for someone else's dividend. Keep it simple: one universal payment, no forms, no eligibility interviews. I've spent forty years watching complicated programs fail the people they're for.",
}

CLUSTERS = [
    {
        "label": "Direct universal claim",
        "summary": "Displaced and precarious participants want an automatic, universal payment funded by AI profits, with no means-testing. They see complexity and voluntarism as ways of quietly saying no.",
        "values": ["dignity", "simplicity", "distrust of gatekeepers"],
        "member_ids": ["amara", "jonas", "helen", "rosa"],
    },
    {
        "label": "Growth first, then redistribute",
        "summary": "Builders argue automation must not be slowed and levies must scale with real profits, concentrated on the largest players. They accept redistribution if it is automatic and does not punish small innovators.",
        "values": ["progress", "proportionality", "innovation"],
        "member_ids": ["dievas", "wei"],
    },
    {
        "label": "Power and plumbing",
        "summary": "Institutionalists say the fight is over governance, not amounts: binding worker rights and capture-proof administration. A check without enforceable structure is decoration.",
        "values": ["accountability", "worker power", "institutional design"],
        "member_ids": ["marcus", "priya"],
    },
]

CRUXES = [
    "Should contributions be levied on all AI deployers or concentrated on the largest model providers?",
    "Is a cash dividend enough, or must it come with binding worker rights (notice, bargaining) to count as sharing gains?",
    "Who administers the fund, and what stops it from being raided or captured?",
]

COMMON_GROUND = [
    "Voluntary corporate pledges are not a mechanism anyone trusts.",
    "Whatever is paid should be automatic — no means-testing bureaucracy.",
    "The rules must be written into law, not policy that changes with each government.",
]

STEELMAN = (
    "The people who disagree with you believe the thing you most want — durable funding for "
    "displaced people — dies precisely when the levy is designed punitively: capital relocates, "
    "small firms fold before they ever owe anything, and the fund starves. They aren't defending "
    "corporate profits; they're arguing that a formula tied to realized gains, starting with the "
    "largest providers, is what makes your dividend still exist in ten years."
)

PROPOSALS = [
    {
        "title": "The Automation Dividend Fund",
        "text": "Establish a statutory Automation Dividend Fund financed by a 4% levy on the revenues of AI model providers and deployers above $100M in annual AI-derived revenue. The fund pays a quarterly universal dividend to every adult, no application required. An independent board publishes accounts quarterly. Firms below the threshold pay nothing. The levy rate is fixed in legislation and reviewed every five years.",
        "rationale": "Combines the universal, automatic payment the displaced cluster demands with the small-firm exemption the builders insist on, and statutory independence for the institutionalists.",
        "draws_from": ["amara", "jonas", "helen", "dievas", "priya"],
        "tradeoffs": [
            "Large AI firms give up ~4% of revenue and will lobby against it.",
            "A universal dividend is smaller per person than a targeted one.",
            "Revenue-based levies can tax firms that aren't yet profitable.",
        ],
    },
    {
        "title": "Automation Dividend Fund v2 — profits, notice, and reach",
        "text": "Revise the Fund: levy 15% on AI-attributable profits (not revenue) of firms above $100M in AI revenue, so unprofitable startups owe nothing. Add a Worker Transition Protocol: 90 days' notice before automation-driven layoffs and a right to consultation, enforceable through labor courts. Reserve 10% of the fund for connectivity and delivery infrastructure in underserved regions, audited publicly. Dividend remains universal and automatic; the independent board's governors serve fixed terms and can be removed only for cause.",
        "rationale": "Moved from revenue to profits to answer the builders' viability critique, added binding notice rights for the labor cluster, and earmarked delivery infrastructure so the dividend actually arrives outside major cities.",
        "draws_from": ["dievas", "wei", "marcus", "rosa", "priya"],
        "tradeoffs": [
            "Profit-based levies are easier to game via accounting than revenue levies.",
            "Notice requirements add friction to deployment decisions.",
            "Earmarking reduces the headline dividend amount.",
        ],
    },
    {
        "title": "Automation Dividend Fund v3 — the anti-gaming compact",
        "text": "Keep the v2 structure with three fixes. Anti-gaming: the levy is the greater of 15% of AI-attributable profits or 2% of AI revenue for firms above the threshold, closing the accounting-loss loophole. Worker power: consultation upgraded to bargaining — where a union exists, automation deployment terms enter collective agreements. Delivery: dividend payments run through the existing tax/ID system with an offline claim path, and the infrastructure reserve is disbursed directly to municipalities with published per-town accounts. The board gains a citizen oversight panel selected by lot.",
        "rationale": "Answers Priya's gaming critique with a revenue floor, Marcus's demand that consultation have teeth, and Rosa's delivery skepticism with municipal direct disbursement — while keeping the universal automatic dividend untouched.",
        "draws_from": ["priya", "marcus", "rosa", "amara", "wei", "helen", "jonas", "dievas"],
        "tradeoffs": [
            "The revenue floor partially reintroduces the burden on low-margin firms.",
            "Bargaining rights will slow some automation deployments.",
            "Citizen oversight panels add cost and can be inexpert.",
        ],
    },
]

EVALS = [
    # Round 1: 4/8 accept-ish -> 50%
    [
        ("amara", "accept_with_reservations", "A real check with no forms — fine. But nothing here stops them automating us with 30 days' warning and calling the dividend compensation."),
        ("dievas", "reject", "A revenue levy hits companies that haven't made a euro of profit. You will tax startups to death and collect from nobody."),
        ("rosa", "accept_with_reservations", "Universal and automatic is right. But 'quarterly payment to every adult' assumes everyone has a bank account and a connection — my town doesn't."),
        ("marcus", "reject", "This is exactly the hush money I warned about. A check and zero rights — workers still find out they're automated the morning it happens."),
        ("wei", "accept", "It doesn't slow deployment and redistribution is written into law. The five-year review is sensible."),
        ("priya", "reject", "Fixed levy in legislation, fine, but 'an independent board' with no appointment or removal rules is a slush fund with extra steps."),
        ("jonas", "accept", "Universal, automatic, funded by the companies that profited from our data. This is what I asked for."),
        ("helen", "accept_with_reservations", "No forms, I like that. But a levy on revenues will end up in prices, and nobody here has told me it won't."),
    ],
    # Round 2: 5/8 -> 62.5%
    [
        ("amara", "reject", "Notice and consultation is progress, but consultation without power means they listen politely and automate anyway. That's not a share of the gains, it's a heads-up."),
        ("dievas", "accept", "Profits, not revenue — that's the fix I needed. My firm owes nothing until we actually win, and the giants pay first."),
        ("rosa", "accept", "The 10% for connectivity and delivery, audited in public, is the first time anyone has budgeted for the last mile. I can defend this at home."),
        ("marcus", "reject", "Ninety days' notice and 'consultation' — consultation is a meeting. Without bargaining teeth this is still theater."),
        ("wei", "accept", "Profit-based, automatic, doesn't touch the deployment throttle. Good."),
        ("priya", "reject", "You moved to profits and opened the oldest loophole in tax law — AI-attributable profit is whatever the accountants say it is. Where's the floor?"),
        ("jonas", "accept", "Still universal, still automatic. The infrastructure earmark is fair even if it trims the check."),
        ("helen", "accept_with_reservations", "Better. I still haven't heard how you keep the levy out of my grocery bill, but fixed-term governors beat political appointees."),
    ],
    # Round 3: 7/8 -> 87.5%
    [
        ("amara", "accept", "Bargaining rights plus the dividend — that's a claim, not charity. I'll defend this."),
        ("dievas", "accept_with_reservations", "The 2% revenue floor stings for low-margin years, but it's capped and predictable. I can live with it as the price of closing the loophole."),
        ("rosa", "accept", "Municipal disbursement with per-town accounts is the first design I've seen that admits how money actually disappears. Yes."),
        ("marcus", "accept", "Automation terms in collective agreements — that's enforceable. That's the difference between a payoff and power."),
        ("wei", "accept", "Deployment stays free, redistribution is automatic and audit-proof. The bargaining friction is a fair trade."),
        ("priya", "accept", "Greater-of levy closes the gaming route, fixed terms plus for-cause removal, citizen panel by sortition — the plumbing finally holds water."),
        ("jonas", "accept", "Universal, automatic, and now with an offline claim path so nobody falls through. Done."),
        ("helen", "reject", "Everyone's celebrating and nobody has answered the one thing I asked: what stops the levy landing in prices? I won't sign what I don't understand."),
    ],
]

REPORT = {
    "summary": "After three rounds, participants converged on a statutory Automation Dividend Fund — a universal, automatic dividend financed by a greater-of levy (15% of AI-attributable profits or 2% of AI revenue) on large AI firms, paired with enforceable worker bargaining rights over automation and municipally-audited delivery infrastructure. Final approval was 87.5%, crossing the 75% consensus threshold.",
    "agreed": [
        "A universal, automatic dividend with no means-testing.",
        "Levy concentrated on firms above $100M AI revenue, with a profit basis plus a revenue floor to prevent accounting games.",
        "Binding worker rights: 90 days' notice and bargaining over automation deployment terms.",
        "Independent fund governance with fixed terms, for-cause removal, and a citizen oversight panel selected by lot.",
        "10% earmark for connectivity and delivery infrastructure, disbursed directly to municipalities with public accounts.",
    ],
    "contested": [
        "Price pass-through: whether the levy ultimately lands on consumers remained unanswered to one participant's satisfaction (Helen, fixed-income cluster).",
        "The revenue floor is accepted 'as a price', not embraced, by low-margin builders.",
    ],
    "evolution": "Round 1's revenue levy was rejected by builders as a startup-killer and by institutionalists as ungoverned; round 2 moved to profit-based collection, added notice rights and a delivery earmark, but opened an accounting loophole and left consultation toothless; round 3 closed the loophole with a greater-of floor, upgraded consultation to bargaining, and routed delivery through municipalities — converting three of the four remaining holdouts.",
}


MOCK_CARD = {
    "claim": "The gains should fund a sovereign wealth fund paying every citizen a dividend, financed by the companies that automated the work in proportion to the labor costs they eliminated.",
    "reasons": ["Companies capture the savings from eliminated labor", "A universal dividend gives everyone a stake"],
    "values": ["fairness", "shared ownership"],
    "red_lines": ["Contributions should scale with labor costs eliminated, not be a flat token"],
}

# Rival candidates per round: A = the fund-first route (wins), B = an alternative.
CANDIDATES_B = [
    {
        "title": "The Worker Transition Compact",
        "strategy": "worker power first",
        "text": "Skip the universal dividend. Require every firm deploying automation above a threshold to negotiate a Transition Agreement with affected workers: 6 months' notice, retraining funded at 150% of salary for a year, and a 10-year wage-insurance floor, enforced through labor courts. A small public top-up fund covers failed firms.",
        "rationale": "Puts enforceable worker rights first, treating displacement as the core injury rather than income distribution.",
        "draws_from": ["marcus", "amara"],
        "tradeoffs": ["People outside formal employment get nothing", "No universal claim for the young or retired"],
    },
    {
        "title": "The Data Royalties Registry",
        "strategy": "data ownership first",
        "text": "Create a national Data Royalties Registry: firms training or deploying AI pay per-use royalties for data derived from residents, collected like copyright levies, distributed annually to every adult. Administered by the IP office with published schedules.",
        "rationale": "Frames the claim as property rights in data rather than a tax, answering the universal-claim cluster from a different direction.",
        "draws_from": ["jonas", "helen"],
        "tradeoffs": ["Royalty valuation is hard and gameable", "Payments fluctuate year to year"],
    },
    {
        "title": "The Municipal Gains Compact",
        "strategy": "local delivery first",
        "text": "Route the entire levy to municipalities by formula (population + displacement index), with mandatory citizen budget assemblies deciding local use, published per-town accounts, and a national audit office backstop. No individual dividend.",
        "rationale": "Treats delivery and local control as the cornerstone, answering the distrust-of-distant-programs cluster.",
        "draws_from": ["rosa", "priya"],
        "tradeoffs": ["No individual entitlement to point to", "Assembly capture by local elites is possible"],
    },
]

# Election vote splits per round (personas only; A wins each round in mock).
RANK_VOTES = [
    {"amara": "A", "dievas": "A", "rosa": "B", "marcus": "B", "wei": "A", "priya": "A", "jonas": "A", "helen": "A"},
    {"amara": "A", "dievas": "A", "rosa": "A", "marcus": "B", "wei": "A", "priya": "B", "jonas": "A", "helen": "A"},
    {"amara": "A", "dievas": "A", "rosa": "A", "marcus": "A", "wei": "B", "priya": "A", "jonas": "A", "helen": "A"},
]

MOCK_PROBES = {
    "violating": {"title": "The Voluntary Compact", "text": "Leading AI firms will sign a voluntary pledge to share gains, reviewed annually at a public summit.", "which_red_line": "voluntary participation"},
    "satisfying": {"title": "The Statutory Levy", "text": "A levy written into law with automatic individual payments and enforceable entitlements, administered by an independent board with published accounts.", "which_concession": "statutory levy + automatic payment"},
    "vague": {"title": "A Fairer Future Together", "text": "We commit to balancing innovation and fairness through inclusive dialogue among all stakeholders."},
}


def respond(task: str, context: dict):
    if task == "opinion":
        return {"opinion": OPINIONS.get(context.get("persona_id"), "I have concerns.")}
    if task == "position_card":
        return dict(MOCK_CARD)
    if task == "steelman":
        return {"steelman": STEELMAN}
    if task == "opposing":
        return {"summary": "The room splits three ways: a large camp wants an automatic universal "
                           "payment, builders want levies tied to real profits only, and "
                           "institutionalists care most about capture-proof governance. Nearly "
                           "everyone distrusts voluntary pledges and means-testing.",
                "counter": STEELMAN}
    if task == "offer":
        idx = min(context.get("round_num", 1), len(PROPOSALS)) - 1
        o = dict(PROPOSALS[idx])
        humans = context.get("human_ids", [])
        addresses = [[], ["dievas", "marcus", "rosa", "priya"], ["priya", "marcus", "rosa", "amara"]]
        o["addresses"] = addresses[idx]
        if idx == 2:
            o["draws_from"] = list(o.get("draws_from", [])) + humans
        return o
    if task == "respond":
        idx = min(context.get("round_num", 1), len(EVALS)) - 1
        pid = context.get("persona_id")
        for i, v, r in EVALS[idx]:
            if i == pid:
                return {"red_line_check": "(mock check)", "concession_check": "(mock check)",
                        "response": "object" if v == "reject" else "accept", "objection": r}
        return {"red_line_check": "(mock)", "concession_check": "(mock)",
                "response": "accept", "objection": "(mock default)"}
    if task == "candidates":
        idx = min(context.get("round_num", 1), len(PROPOSALS)) - 1
        a = dict(PROPOSALS[idx]); a["id"] = "A"; a.setdefault("strategy", "fund first")
        b = dict(CANDIDATES_B[idx]); b["id"] = "B"
        addresses = [[], ["dievas", "marcus", "rosa", "priya"], ["priya", "marcus", "rosa", "amara"]]
        humans = context.get("human_ids", [])
        a["addresses"] = addresses[idx]
        b["addresses"] = addresses[idx][:2] if idx else []
        if idx == 2:                      # final revision cites the humans too
            a["draws_from"] = list(a.get("draws_from", [])) + humans
        return {"candidates": [a, b]}
    if task == "rank":
        idx = min(context.get("round_num", 1), len(RANK_VOTES)) - 1
        pref = RANK_VOTES[idx].get(context.get("persona_id"), "A")
        return {"preferred": pref, "why": "(mock) closer to my starting conditions."}
    if task == "probes":
        return MOCK_PROBES
    if task == "revise_card":
        return {"id": context.get("persona_id"), "name": context.get("persona_id", "").title(),
                "profile": "(mock revised)", "interests": ["(mock)"], "red_lines": ["(mock)"],
                "concessions": ["(mock)"], "trust_priors": "(mock)", "voice": "(mock)"}
    if task == "landscape":
        out = {"clusters": CLUSTERS, "cruxes": CRUXES, "common_ground": COMMON_GROUND}
        if context.get("has_human"):
            out = dict(out)
            out["clusters"] = [dict(c) for c in CLUSTERS]
            out["clusters"][0] = dict(out["clusters"][0])
            out["clusters"][0]["member_ids"] = CLUSTERS[0]["member_ids"] + ["you"]
            out["steelman_for_you"] = STEELMAN
        return out
    if task == "proposal":
        idx = min(context.get("round_num", 1), len(PROPOSALS)) - 1
        return PROPOSALS[idx]
    if task == "evaluate":
        idx = min(context.get("round_num", 1), len(EVALS)) - 1
        pid = context.get("persona_id")
        for i, v, r in EVALS[idx]:
            if i == pid:
                return {"red_line_check": "(mock check)", "concession_check": "(mock check)",
                        "verdict": v, "reason": r}
        return {"red_line_check": "(mock)", "concession_check": "(mock)",
                "verdict": "accept_with_reservations", "reason": "(mock default)"}
    if task == "report":
        report = dict(REPORT)
        approval = context.get("approval", 0)
        rounds = context.get("rounds", 0)
        reached = context.get("outcome") == "consensus"
        report["summary"] = (f"After {rounds} rounds, {approval:.1%} of eligible participants accepted "
                             f"the final proposal. " + ("The 75% threshold was reached." if reached
                             else "The group did not reach the 75% threshold; disagreement remains."))
        return report
    raise ValueError(f"mock backend has no data for task: {task}")
