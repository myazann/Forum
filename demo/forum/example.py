"""A curated, deterministic walkthrough. No generated people or model calls.

The visitor chooses a published example view; peer contributions and votes are
fixed. Only the visitor's own response determines their ballot. All outputs
are labeled as examples by the shared room UI.
"""

from copy import deepcopy
import uuid

from .engine import Deliberation

TOPIC = "Should our town centre be car-free on Saturdays?"
CONTEXT = ("Imagine a six-week trial on Market Street. Residents want quieter, safer streets; "
           "shops and people who depend on cars need access. The group is preparing a "
           "recommendation for the town council, not making a binding decision.")

CHOICES = [
    {"id": "deliveries", "title": "Keep local shops working",
     "opinion": "I'd support a quieter street if shops can still receive their Saturday deliveries.",
     "objection": "Allow morning deliveries before the street closes to general traffic.",
     "counter": "Families need a predictable stretch of the day when children can move safely. An exemption that lasts all day would leave the street just as busy. A short delivery window could protect both needs."},
    {"id": "access", "title": "Make room for people who need a car",
     "opinion": "A quieter centre sounds good, but people with limited mobility must be able to reach the shops by car.",
     "objection": "Keep door-to-door vehicle access for disabled visitors throughout the day.",
     "counter": "People walking and using mobility aids also benefit from fewer moving vehicles. They want a safe street without excluding anyone who needs a car. A specific access exception could serve both groups."},
    {"id": "parking", "title": "Keep parking close to the shops",
     "opinion": "I want the existing customer parking to stay on Market Street all day. Nearby streets are too far away for some customers.",
     "objection": "Keep all existing customer parking on Market Street throughout Saturday.",
     "counter": "Neighbours want to use that same road space for walking, seating and play. Keeping every parking space would leave little room for the trial. This is a real conflict over a limited space, not a misunderstanding."},
]

PEERS = [
    {"id": "ex_aya", "name": "Aya · resident", "opinion": "I'd like a safe place for children to walk and play. A short trial would help us find out whether it works."},
    {"id": "ex_sam", "name": "Sam · café owner", "opinion": "More people walking could help my café. I can arrange deliveries earlier if the hours are predictable."},
    {"id": "ex_jo", "name": "Jo · access advocate", "opinion": "Please keep door-to-door access for disabled visitors. A pedestrian street should be accessible to everyone."},
    {"id": "ex_leo", "name": "Leo · shopkeeper", "opinion": "I want customer parking outside my shop all day. I'm not convinced a trial makes the loss of passing trade acceptable."},
]

class ExampleBackend:
    name = "guided-example"

    def complete_json(self, *args, **kwargs):
        raise RuntimeError("The guided example uses curated content, not a model.")


def new():
    d = Deliberation(TOPIC, max_rounds=2, include_personas=False, backend=ExampleBackend())
    d.mode = "example"
    d.context = CONTEXT
    d.opinions = [{**p, "is_human": False} for p in deepcopy(PEERS)]
    return d


def choose(d, user, choice_id):
    choice = next((c for c in CHOICES if c["id"] == choice_id), None)
    if not choice:
        raise ValueError("Choose one of the three example perspectives.")
    d.scenario = {"choice": choice_id, "owner": user["id"]}
    d.add_position(user["id"], user["handle"], choice["opinion"])
    d.humans[user["id"]]["opposing"] = {
        "summary": "Everyone wants a thriving, accessible town centre. They disagree about how much road space should stay available for cars.",
        "counter": choice["counter"],
    }
    d.landscape = {
        "common_ground": ["Keep the town centre welcoming and accessible.", "Support local shops.", "Evaluate a time-limited trial before making a permanent change."],
        "cruxes": ["How much vehicle access can remain without losing a safe, quiet street?", "Can delivery and access exceptions work without keeping all-day customer parking?"],
        "clusters": [],
    }
    d.status = "landscape"


def make_offer(d):
    number = len(d.rounds) + 1
    uid = d.scenario["owner"]
    if number == 1:
        offer = {
            "title": "A six-week Saturday trial",
            "summary": "Try a quieter Market Street, then decide together whether to keep it.",
            "text": "Close Market Street to general traffic from 9 a.m. to 6 p.m. on Saturdays for six weeks. Remove on-street customer parking during those hours. Keep emergency access open. The council will use its existing trial budget for signs and removable barriers, collect feedback from residents and shops, and publish a review before any permanent decision.",
            "rationale": "A short, reversible trial gives the town evidence. This first version leaves practical access questions unanswered.",
            "tradeoffs": ["People driving to the shops would need to park elsewhere.", "The first version has no delivery window or disability-access exception."],
            "changes": [], "addresses": [], "draws_from": ["ex_aya", "ex_sam"],
        }
    else:
        text = ("Trial a quieter Market Street for six Saturdays, closing it to general traffic from 10 a.m. to 6 p.m. "
                "Allow shop deliveries before 10 a.m. Keep door-to-door vehicle access for disabled visitors throughout the day. "
                "Keep emergency access open. Remove general customer parking during the closure; signpost spaces on adjoining streets. "
                "The council will fund signs and removable barriers from its existing trial budget, collect access and shop-trade feedback, "
                "and publish a review before deciding whether to continue.")
        offer = {
            "title": "A quieter street, with practical access",
            "summary": "Keep the six-week trial, add access exceptions, and review the effect on shops.",
            "text": text,
            "rationale": "The delivery window and disability-access exception respond to concerns from the room. General customer parking remains a real disagreement.",
            "tradeoffs": ["The car-free part of the day starts an hour later.", "Some vehicles still enter for disability and emergency access.", "General customer parking moves to adjoining streets; Leo still objects."],
            "changes": [], "addresses": [], "draws_from": [p["id"] for p in PEERS],
        }
        quotes = {
            "deliveries": ("addressed", "Allow shop deliveries before 10 a.m.", "Version 2 adds the morning delivery window you requested. Afternoon deliveries are still restricted."),
            "access": ("addressed", "Keep door-to-door vehicle access for disabled visitors throughout the day.", "Version 2 explicitly preserves all-day door-to-door access for disabled visitors."),
            "parking": ("not_addressed", "Remove general customer parking during the closure; signpost spaces on adjoining streets.", "The proposal still removes general parking from Market Street. Nearby spaces do not meet your request to keep the existing spaces."),
        }
        for concern in d.concerns:
            status, quote, explanation = quotes[d.scenario["choice"]]
            offer["changes"].append({"concern_id": concern["id"], "status": status,
                                     "proposal_quote": quote, "explanation": explanation})
            if status == "addressed":
                offer["addresses"].append(uid)
    offer["id"] = uuid.uuid4().hex
    d.rounds.append({"number": number, "offer": offer, "responses": [], "approval": None,
                     "approval_by_cluster": {}, "outcome": None,
                     "eligible_ids": [p["id"] for p in PEERS] + [uid]})
    d.status = "offered"


def respond(d, response):
    rnd = d.rounds[-1]
    uid = d.scenario["owner"]
    choice = next(c for c in CHOICES if c["id"] == d.scenario["choice"])
    objection = choice["objection"] if response == "object" else ""
    if response == "object":
        # Repeated rejection preserves one concern, rather than claiming new impact.
        if not d.concerns:
            d.concerns.append({"id": uuid.uuid4().hex, "user_id": uid,
                               "round": rnd["number"], "text": objection})
    accepting = {"ex_aya", "ex_sam"} if rnd["number"] == 1 else {"ex_aya", "ex_sam", "ex_jo"}
    rnd["responses"] = [{"id": p["id"], "response": "accept" if p["id"] in accepting else "object",
                         "objection": ""} for p in PEERS]
    rnd["responses"].append({"id": uid, "response": response, "objection": objection})
    rnd["approval"] = sum(r["response"] == "accept" for r in rnd["responses"]) / 5
    if rnd["number"] == 1:
        rnd["outcome"] = "revise"
        d.status = "evaluated"
        return
    outcome = "consensus" if rnd["approval"] >= d.threshold else "dissensus"
    rnd["outcome"] = outcome
    d.status = outcome
    accepts = sum(r["response"] == "accept" for r in rnd["responses"])
    contested = ["Leo still wants all-day customer parking on Market Street; this proposal does not retain it."]
    if response == "object":
        contested.append("The visitor in this example did not accept the final proposal; their concern remains recorded.")
    d.report = {
        "summary": (f"{accepts} of 5 participants in this example accepted version 2. " +
                    ("That meets the 75% threshold, with disagreement about parking still recorded."
                     if outcome == "consensus" else "That falls short of the 75% threshold. The group has common ground, but no agreed proposal.")),
        "agreed": ["A welcoming, accessible town centre matters to everyone.", "Local shops need to remain viable.", "Any trial should be reviewed before a permanent decision."],
        "contested": contested,
        "evolution": "The first proposal closed the street from 9 a.m. The second added a morning delivery window and all-day disability access. General customer parking remained outside the trial area.",
    }
