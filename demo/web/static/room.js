const ROOM = location.pathname.split("/").pop();
let S = null,
  stateKey = "",
  inFlight = null,
  actionPending = false;
const terminal = (s) => ["consensus", "dissensus", "insufficient"].includes(s);
const latest = () => S.rounds.at(-1);
const draftKey = (kind) =>
  `forum:${S?.me?.user_id || "guest"}:${ROOM}:${kind}:${kind === "objection" ? latest()?.offer.id || "" : ""}`;
const bullets = (items) =>
  `<ul>${(items || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
const title = (kicker, heading, description = "") =>
  `<div class="step-kicker">${esc(kicker)}</div><h2 class="stage-title" tabindex="-1">${esc(heading)}</h2>${description ? `<p class="stage-intro">${esc(description)}</p>` : ""}`;

async function poll(force = false) {
  if (inFlight) {
    await inFlight;
    if (!force) return;
  }
  inFlight = (async () => {
    try {
      const next = await api(`/api/d/${ROOM}`);
      const key = JSON.stringify(next);
      S = next;
      if (force || key !== stateKey) {
        stateKey = key;
        render();
      }
      if ($("message").dataset.connection) {
        $("message").innerHTML = "";
        delete $("message").dataset.connection;
      }
    } catch (e) {
      if (e.status === 404) {
        $("stage").innerHTML =
          `<div class="card">${title("Discussion unavailable", "We couldn’t find that discussion.", "The link may be incomplete. You can return home or start a new example.")}<div class="actions"><a class="btn" href="/">Back to Forum</a></div></div>`;
      } else {
        $("message").innerHTML = notice(e.message, true);
        $("message").dataset.connection = "yes";
      }
    }
  })();
  await inFlight;
  inFlight = null;
}

async function act(path, body = {}, clearDraft = null) {
  if (actionPending) return;
  actionPending = true;
  if (inFlight) await inFlight;
  document
    .querySelectorAll("#stage button")
    .forEach((b) => (b.disabled = true));
  $("message").innerHTML = "";
  try {
    await api(`/api/d/${ROOM}/${path}`, body);
    if (clearDraft) removeDraft(clearDraft);
    if (path === "respond") {
      if ($("responseForm")) $("responseForm").hidden = true;
      if ($("objectForm")) $("objectForm").hidden = true;
    }
    actionPending = false;
    await poll(true);
    const heading = document.querySelector(".stage-title");
    if (heading) heading.focus({ preventScroll: true });
    $("stage").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    actionPending = false;
    await poll(true);
    $("message").innerHTML = notice(e.message, true);
    $("message").scrollIntoView({ block: "center" });
  }
}

function shareView(event) {
  event.preventDefault();
  if (S.mode === "example") {
    const choice = document.querySelector('input[name="perspective"]:checked');
    if (choice) act("position", { choice: choice.value });
  } else act("position", { text: $("opinionText").value }, draftKey("opinion"));
}
function sendResponse(response) {
  const rnd = latest();
  act(
    "respond",
    {
      response,
      objection:
        response === "object" && S.mode !== "example"
          ? $("objectionText").value
          : "",
      round_number: rnd.number,
      proposal_id: rnd.offer.id,
    },
    draftKey("objection"),
  );
}
function openObjection() {
  $("objectForm").hidden = false;
  const input = $("objectionText");
  if (input) input.focus();
  else $("sendObjection").focus();
}
function editResponse() {
  $("responseForm").hidden = false;
  document.querySelector("#responseForm button")?.focus();
}

function render() {
  // Preserve focus/caret, open disclosures and unsent input when a background update arrives.
  const active = document.activeElement;
  const focus = active?.id
    ? { id: active.id, start: active.selectionStart, end: active.selectionEnd }
    : null;
  const opened = new Set(
    [...document.querySelectorAll("details[id][open]")].map((d) => d.id),
  );
  const objectOpen = $("objectForm") && !$("objectForm").hidden;
  const responseOpen = $("responseForm") && !$("responseForm").hidden;
  const oldProposal =
    document.querySelector("[data-proposal]")?.dataset.proposal;
  const checked = document.querySelector(
    'input[name="perspective"]:checked',
  )?.value;
  const me = S.me,
    isExample = S.mode === "example";
  if (me && SHELL_ME?.id !== me.user_id) shell().catch(() => {});
  $("roomHeader").innerHTML =
    `<header class="room-header"><div class="room-topline"><a class="back" href="/">← All discussions</a><span class="pill neutral">${isExample ? "Guided example · about 5 minutes" : "Group discussion · advisory"}</span></div><h1>${esc(S.topic)}</h1><p class="room-context">${esc(S.context)}</p><div class="room-meta"><span>${isExample ? (me?.is_creator ? "You + 4 example viewpoints" : "Saved guided example") : `${S.speaker_count} ${S.speaker_count === 1 ? "person has" : "people have"} shared a view`}</span><span>${esc(STATUS[S.status] || "In progress")}</span>${S.closes_at ? `<span data-deadline="${S.closes_at}">${deadline(S.closes_at)}</span>` : ""}</div></header>`;
  document.title = `${S.topic} — Forum`;
  const step = terminal(S.status)
    ? 3
    : S.status === "gathering"
      ? 0
      : me?.has_position && !me.perspective_seen
        ? 1
        : 2;
  $("steps").innerHTML =
    `<ol class="steps" aria-label="Discussion stages">${["Share a view", "Understand others", "Shape a proposal", "See the result"].map((n, i) => `<li class="${i === step ? "current" : i < step ? "done" : ""}" ${i === step ? 'aria-current="step"' : ""}><span class="step-n" aria-hidden="true">${i < step ? "✓" : i + 1}</span>${n}</li>`).join("")}</ol>`;
  $("progress").innerHTML = S.busy
    ? `<div class="notice"><span class="spinner" aria-hidden="true"></span>${esc(S.progress)}. You can leave this page; your place is saved.</div>`
    : S.error
      ? `<div class="notice error">${esc(S.error)}${me?.is_creator ? '<div class="actions"><button class="btn small secondary" onclick="act(\'retry\')">Try mediation again</button></div>' : ""}</div>`
      : "";
  $("stage").innerHTML = stageHTML();
  $("support").innerHTML = supportHTML();
  for (const id of opened) {
    const el = $(id);
    if (el) el.open = true;
  }
  if (checked) {
    const input = document.querySelector(
      `input[name="perspective"][value="${checked}"]`,
    );
    if (input) input.checked = true;
  }
  if (objectOpen && oldProposal === latest()?.offer.id && $("objectForm"))
    $("objectForm").hidden = false;
  if (responseOpen && oldProposal === latest()?.offer.id && $("responseForm"))
    $("responseForm").hidden = false;
  for (const [id, kind] of [
    ["opinionText", "opinion"],
    ["objectionText", "objection"],
  ]) {
    const input = $(id);
    if (!input) continue;
    input.value =
      readDraft(draftKey(kind)) ??
      (kind === "opinion"
        ? me?.opinion || ""
        : me?.my_response?.objection || "");
    input.addEventListener("input", () =>
      storeDraft(draftKey(kind), input.value),
    );
  }
  if (focus && $(focus.id)) {
    $(focus.id).focus({ preventScroll: true });
    if (focus.start != null && $(focus.id).setSelectionRange)
      $(focus.id).setSelectionRange(focus.start, focus.end);
  }
}

function stageHTML() {
  const me = S.me,
    ex = S.mode === "example";
  if (terminal(S.status)) return outcomeHTML();
  if (ex && !me?.is_creator)
    return `<div class="card">${title("An example someone else started", "Explore it from your own perspective.", "This is a saved guided example. Start your own to choose a concern and shape its outcome.")}<div class="actions"><button class="btn" onclick="startExample(this)">Start my own example ↗</button></div>${latest() ? proposalHTML(latest()) : ""}</div>`;
  if (S.status === "gathering") return intakeHTML();
  if (me?.has_position && !me.perspective_seen && me.opposing)
    return perspectiveHTML();
  if (S.status === "evaluated" && ex) return roundResultHTML();
  if (S.status === "offered")
    return `<div class="card" data-proposal="${esc(latest().offer.id)}">${title(`Proposal ${latest().number} of up to ${S.max_rounds}`, latest().number > 1 ? "What changed, and why." : "Could you live with this?", latest().number > 1 ? "Read the revision and decide for yourself whether it goes far enough." : "You can accept a compromise without agreeing with every part of it.")}${concernsHTML()}${proposalHTML(latest())}${responseHTML()}</div>`;
  return `<div class="card">${title("Your view is saved", "The group’s next step is taking shape.", "The mediator is reading the views and preparing a proposal. You can safely leave and return from My discussions.")}<div class="actions"><a class="btn secondary" href="/">Back to my discussions</a></div></div>`;
}

function intakeHTML() {
  const me = S.me;
  if (S.mode === "example")
    return `<div class="card">${title("01 · Share a view", "What matters most to you?", "Choose a perspective to explore. These are written examples, so you can follow exactly how a concern affects the next proposal.")}<form onsubmit="shareView(event)"><div class="choice-list">${S.example_choices.map((c) => `<label class="choice"><input type="radio" name="perspective" value="${c.id}" required><span><strong>${esc(c.title)}</strong><span class="choice-copy">${esc(c.opinion)}</span></span></label>`).join("")}</div><button class="btn" type="submit">Share this view <span aria-hidden="true">→</span></button><p class="help">This walkthrough uses curated viewpoints and example votes. No AI is called and no real town decision is being made.</p></form></div>`;
  const invite = me?.is_creator
    ? `<div class="notice"><strong>Bring your group into the room.</strong><p>Share the link with at least two other people. Everyone can contribute until intake closes.</p><div class="actions" style="margin-top:12px"><button class="btn small secondary" onclick="copyLink()">Copy invite link</button>${S.speaker_count >= 3 ? '<button class="btn small" onclick="act(\'begin\')">Everyone is here · Begin now</button>' : ""}</div></div>`
    : "";
  const form = `<form onsubmit="shareView(event)"><div class="field"><label for="opinionText">What matters to you about this question?</label><textarea id="opinionText" rows="5" maxlength="5000" required placeholder="Share your view, what you need, and anything you would find hard to accept."></textarea><p class="help">Saved in this browser as you write. Your submitted view is visible in this room under your pseudonym.</p></div><div class="actions"><button class="btn" type="submit">${me?.has_position ? "Save updated view" : "Share my view"} →</button></div></form>`;
  return `${invite}<div class="card">${me?.has_position ? `${title("Your contribution", "Your view is in the room.", "You can edit it until intake closes. Everyone gets a chance to speak before the proposal is prepared.")}<p class="quote" style="margin-top:20px">“${esc(me.opinion)}”</p><details id="editView" style="margin-top:24px"><summary>Edit my view</summary>${form}</details>` : `${title("01 · Share a view", "Start with what matters to you.", "You do not need an account or a polished argument. Your own words are enough.")}${form}`}</div>`;
}

function perspectiveHTML() {
  const me = S.me;
  return `<div class="card">${title("02 · Understand others", "There’s more common ground than it seems.", me.opposing.summary)}<div class="two-col"><div class="inset"><h3>What the room shares</h3>${bullets(S.landscape.common_ground)}</div><div class="inset warm"><h3>The real disagreements</h3>${bullets(S.landscape.cruxes)}</div></div><div class="perspective"><h3>A fair case for another perspective</h3><p>${esc(me.opposing.counter)}</p></div><p class="help" style="margin-top:18px">This is a summary of the views below. Reading it does not mean you have to agree.</p><div class="actions"><button class="btn" onclick="act('continue')">Read the first proposal <span aria-hidden="true">→</span></button></div></div>`;
}

function proposalHTML(round) {
  const offer = round.offer;
  return `<article class="proposal"><h3>${esc(offer.title)}</h3>${offer.summary ? `<p class="intro" style="margin-top:10px">${esc(offer.summary)}</p>` : ""}<p class="proposal-text">${esc(offer.text)}</p><div class="tradeoffs"><h3>The tradeoffs</h3>${bullets(offer.tradeoffs)}</div><p class="proposal-rationale"><strong>Why this proposal:</strong> ${esc(offer.rationale || "")}</p></article>`;
}

function concernsHTML() {
  if (!S.me?.concerns?.length) return "";
  return S.me.concerns
    .map((c) => {
      const a = c.assessment;
      const resolved = a?.status === "addressed";
      return `<section class="concern ${resolved ? "" : "unresolved"}"><div class="label">${a ? { addressed: "Your concern · a concrete change", partly_addressed: "Your concern · partly addressed", not_addressed: "Your concern · still unresolved" }[a.status] : terminal(S.status) ? "Your concern · recorded in the result" : "Your concern · awaiting a response"}</div><p class="source">You asked: “${esc(c.text)}”</p>${a ? `<p class="quote">“${esc(a.proposal_quote)}”</p><p class="explanation">${esc(a.explanation)}</p><p class="help">${S.mode === "example" ? "Curated example explanation" : "The mediator’s assessment"} · ${terminal(S.status) ? "Your final response is recorded separately from this assessment." : "Your response decides whether this is enough for you."}</p>` : `<p class="explanation">${terminal(S.status) ? "This discussion has ended. Your concern remains recorded; no further revision is scheduled." : "This concern is saved. No supported change has been linked to it yet."}</p>`}</section>`;
    })
    .join("");
}

function responseHTML() {
  const me = S.me;
  if (!me?.has_position)
    return `<div class="your-response"><strong>You’re observing this discussion.</strong><p>New views closed before you arrived. You can read the current proposal and see aggregate results when the round closes.</p><a href="/#start-group">Start a related discussion →</a></div>`;
  const waiting = latest().waiting_on;
  const saved = me.responded
    ? `<div class="your-response"><strong>Your response to version ${latest().number} is saved: ${me.my_response.response === "accept" ? "you could live with it." : "something needs to change."}</strong>${me.my_response.objection ? `<p>“${esc(me.my_response.objection)}”</p>` : ""}<p>${waiting ? `${waiting.responded} of ${waiting.needed} people have responded. ` : ""}You can leave and come back. Choices stay private.</p><button class="btn small text" onclick="editResponse()">Change my response while this round is open</button></div>`
    : "";
  const choice = S.example_choices.find((c) => c.id === S.selected_choice);
  return (
    saved +
    `<div class="response-area" id="responseForm" ${me.responded ? "hidden" : ""}><h3>Can you live with this proposal?</h3><p class="help">${S.mode === "example" ? "Your response is your choice. The other four example votes are scripted." : "Your choice stays private. Objections inform the mediator and may be summarized without your name."}</p><div class="actions"><button class="btn" onclick="sendResponse('accept')">I could live with this <span aria-hidden="true">✓</span></button><button class="btn secondary" onclick="openObjection()">Something needs to change</button></div><form id="objectForm" class="object-form" hidden onsubmit="event.preventDefault();sendResponse('object')">${S.mode === "example" ? `<div class="inset warm"><h3>The concern you’re exploring</h3><p>${esc(choice?.objection)}</p></div><p class="help">${latest().number === 1 ? "Send this example objection to see how the revision responds." : "The final response records whether this proposal works for you. It may end in disagreement."}</p>` : '<label for="objectionText">What would need to change?</label><textarea id="objectionText" rows="3" maxlength="3000" required placeholder="Be specific about what would make this proposal workable for you."></textarea><p class="help">Your writing is saved as you go. An objection remains recorded even if the group reaches agreement.</p>'}<div class="actions"><button class="btn" id="sendObjection" type="submit">${latest().number === S.max_rounds ? "Record my objection" : "Send my objection"} →</button><button class="btn text" type="button" onclick="$('objectForm').hidden=true">Cancel</button></div></form></div>`
  );
}

function tallyHTML(rnd) {
  if (!rnd || !rnd.outcome) return "";
  return `<div class="tally"><strong>${rnd.accepting} / ${rnd.eligible}</strong><span>accepted version ${rnd.number}</span></div><div class="meter" aria-hidden="true"><span style="width:${pct(rnd.approval)}%"></span></div><p class="tally-note">${pct(rnd.approval)}% accepted · ${rnd.required} of ${rnd.eligible} needed for agreement · ${rnd.responded} responded${rnd.responded < rnd.eligible ? ` · ${rnd.eligible - rnd.responded} did not respond` : ""}</p>`;
}

function roundResultHTML() {
  const rnd = latest();
  const my = rnd.my_response;
  return `<div class="card">${title("The first round is complete", "The proposal needs another look.", my?.response === "object" ? "Your objection is saved. The room did not reach the acceptance threshold, so there will be a revision." : "Your acceptance is saved. Other concerns keep this version below the threshold, so there will be a revision.")}${tallyHTML(rnd)}<div class="inset warm" style="margin-top:24px"><h3>What still needs work</h3><p>Jo needs door-to-door disability access. Leo wants customer parking to stay all day.${my?.response === "object" ? " Your selected concern is part of the next review, too." : ""}</p></div><div class="actions"><button class="btn" onclick="act('continue')">See the revised proposal <span aria-hidden="true">→</span></button><a class="btn text" href="/">Come back later</a></div><details id="previousProposal" style="margin-top:24px"><summary>Read version 1 again</summary>${proposalHTML(rnd)}</details></div>`;
}

function outcomeHTML() {
  const r = S.report || {};
  const rnd = latest();
  const heading =
    S.status === "consensus"
      ? "A way forward, with differences recorded."
      : S.status === "dissensus"
        ? "Some common ground. No shared proposal yet."
        : "The group needs more voices.";
  return `<div class="card">${title(S.mode === "example" ? "Example complete · The result" : "04 · The result", heading, r.summary || "")}${S.mode === "example" ? '<p class="help" style="margin-top:14px">Guided example result · four scripted votes and the visitor’s chosen response.</p>' : ""}${tallyHTML(rnd)}${S.me?.has_position ? `<div class="your-response">${rnd?.my_response ? `You ${rnd.my_response.response === "accept" ? "accepted" : "objected to"} the final version. ` : ""}Your contribution remains part of this discussion.</div>` : ""}${concernsHTML()}<div class="two-col"><div class="inset"><h3>Common ground</h3>${r.agreed?.length ? bullets(r.agreed) : "<p>No group agreement has been inferred.</p>"}</div><div class="inset warm"><h3>What remains unresolved</h3>${r.contested?.length ? bullets(r.contested) : "<p>No unresolved concerns were recorded in the closing report.</p>"}</div></div><p class="small muted">${esc(r.evolution || "")}</p>${rnd ? `<details id="finalProposal" open style="margin-top:24px"><summary>${S.status === "consensus" ? "Read the accepted proposal" : "Read the final proposal"}</summary>${proposalHTML(rnd)}</details>` : ""}<p class="result-note">${S.mode === "example" ? "This illustrates a process; no real group or council made this decision." : "This is a recommendation from this group, not a binding decision. Acceptance is measured against everyone eligible for the round, including people who did not respond."}</p>${S.mode === "example" ? `<section class="inset" style="margin-top:24px"><h3>You’ve completed the example.</h3><p>${S.status === "consensus" ? "The group found a proposal four people could live with. The remaining objection stays in the record." : "The group did not reach agreement. That is a complete result, too: the final proposal and unresolved concerns are preserved."}</p><p>Your result is saved in My discussions. Try another perspective to see how a different concern changes the journey.</p><div class="actions"><a class="btn" href="/">Finish & return to my discussions</a><button class="btn secondary" onclick="startExample(this)">Try another perspective</button>${LIVE_AVAILABLE ? '<a class="btn text" href="/#start-group">Bring your own question →</a>' : ""}</div></section><div class="actions"><button class="btn text" onclick="copyLink()">Copy result link ↗</button></div>` : '<div class="actions"><button class="btn" onclick="copyLink()">Copy result link ↗</button><a class="btn secondary" href="/">My discussions</a></div>'}</div>`;
}

function supportHTML() {
  const me = S.me;
  const previousDrafts = S.rounds
    .filter((r) => r.outcome)
    .map((r) => ({
      number: r.number,
      text: readDraft(
        `forum:${me?.user_id || "guest"}:${ROOM}:objection:${r.offer.id}`,
      ),
    }))
    .filter((d) => d.text);
  return `<div class="details-list">${
    me?.has_position
      ? `<details id="yourContribution"><summary>Your contribution</summary><div class="details-body"><p class="quote">“${esc(me.opinion)}”</p>${S.rounds
          .filter((r) => r.my_response)
          .map(
            (r) =>
              `<div class="history"><span class="pill neutral">Version ${r.number}</span><p>You ${r.my_response.response === "accept" ? "could live with this proposal." : "asked for a change."}</p>${r.my_response.objection ? `<p>${esc(r.my_response.objection)}</p>` : ""}</div>`,
          )
          .join(
            "",
          )}<p class="help">Your views and responses are saved. Return using this browser to keep your identity.</p></div></details>`
      : ""
  }
    <details id="otherViews"><summary>Other views in the room · ${S.opinions.length}</summary><div class="details-body">${S.opinions.map((o) => `<div class="opinion"><strong>${esc(o.name)}${!o.is_human ? " · example viewpoint" : ""}</strong><p>${esc(o.opinion)}</p></div>`).join("") || '<p class="small muted">No views shared yet.</p>'}</div></details>
    ${S.landscape.common_ground?.length && S.me?.perspective_seen ? `<details id="commonGround"><summary>Common ground and disagreements</summary><div class="details-body"><h3>Common ground</h3>${bullets(S.landscape.common_ground)}<h3>Main disagreements</h3>${bullets(S.landscape.cruxes)}</div></details>` : ""}
    ${
      S.rounds.some((r) => r.outcome)
        ? `<details id="previousVersions"><summary>How the proposal evolved · ${S.rounds.length} ${S.rounds.length === 1 ? "version" : "versions"}</summary><div class="details-body">${S.rounds
            .filter((r) => r.outcome)
            .map(
              (r) =>
                `<article class="history"><span class="pill neutral">Version ${r.number} · ${r.accepting}/${r.eligible} accepted</span>${proposalHTML(r)}</article>`,
            )
            .join("")}</div></details>`
        : ""
    }
    ${previousDrafts.length ? `<details id="previousDrafts"><summary>Your unsent drafts from closed rounds</summary><div class="details-body"><p class="help">These were saved only in this browser and were not submitted.</p>${previousDrafts.map((d) => `<div class="history"><strong>Version ${d.number}</strong><p>${esc(d.text)}</p></div>`).join("")}</div></details>` : ""}
    <details id="process"><summary>How this was produced</summary><div class="details-body"><p class="small">${esc(S.process.description)}</p><p class="help">${S.mode === "example" ? "Example content is written in advance. Selecting another concern never generates a new person." : `${S.process.calls} model calls recorded. Model backend: ${esc(S.process.backend)}. Private raw traces are not published.`}</p><p class="small muted" style="margin-top:12px">One proposal at a time. At least 75% acceptance to reach agreement. Up to ${S.max_rounds} rounds; unresolved differences stay in the result.</p></div></details></div>`;
}

shell()
  .catch(() => {})
  .then(() => poll(true));
setInterval(() => {
  if (!actionPending && !document.hidden) poll();
  document
    .querySelectorAll("[data-deadline]")
    .forEach((el) => (el.textContent = deadline(Number(el.dataset.deadline))));
}, 3000);
