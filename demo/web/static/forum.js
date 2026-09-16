const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const pct = (x) => Math.round((x || 0) * 100);
const STATUS = {
  gathering: "Sharing views",
  landscape: "Understanding the room",
  offered: "Proposal open",
  evaluated: "A revision is next",
  consensus: "Agreement reached",
  dissensus: "Disagreement recorded",
  insufficient: "Not enough responses",
};
let SHELL_ME = null;
let LIVE_AVAILABLE = false;

async function api(path, body) {
  if (location.protocol === "file:") {
    throw new Error(
      "Open the running Forum demo at http://127.0.0.1:8710. This HTML file alone cannot save views or complete a discussion.",
    );
  }
  let res;
  try {
    res = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(30000),
    });
  } catch {
    throw new Error(
      "Connection interrupted. Your writing is saved in this browser. Please try again.",
    );
  }
  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(
      "The server could not complete that request. Please try again.",
    );
  }
  if (!res.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((x) => x.msg).join(". ")
      : data.detail;
    const error = new Error(detail || "That request could not be completed.");
    error.status = res.status;
    throw error;
  }
  return data;
}

async function shell() {
  const data = await api("/api/me");
  SHELL_ME = data.user;
  LIVE_AVAILABLE = data.live_available;
  $("shellBar").innerHTML =
    `<a class="brand" href="/" aria-label="Forum home"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>forum</a>
    <nav class="nav" aria-label="Main navigation"><a href="/${SHELL_ME ? "#my-discussions" : "#how-it-works"}">${SHELL_ME ? "My discussions" : "How it works"}</a><a href="/#start-group">Start a discussion</a></nav>
    ${SHELL_ME ? `<a class="session-link" href="/u/${encodeURIComponent(SHELL_ME.handle)}" title="Your name and browser session">${esc(SHELL_ME.handle)}</a>` : ""}`;
  return data;
}

function notice(message, error = false) {
  if (location.protocol === "file:") {
    return '<div class="notice">This is a preview of the page file. <a href="http://127.0.0.1:8710/">Open the running Forum demo →</a> to try the complete journey.</div>';
  }
  return `<div class="notice ${error ? "error" : ""}">${esc(message)}</div>`;
}
function pill(status) {
  return `<span class="pill ${["dissensus", "insufficient"].includes(status) ? "amber" : ""}">${esc(STATUS[status] || status)}</span>`;
}
function when(ts) {
  return new Date(ts * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function deadline(ts) {
  const minutes = Math.max(0, Math.ceil((ts * 1000 - Date.now()) / 60000));
  return minutes === 0 ? "Closing now" : `Closes ${when(ts)}`;
}
function storeDraft(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {}
}
function removeDraft(key) {
  try {
    localStorage.removeItem(key);
  } catch {}
}
function readDraft(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 5000);
}
async function copyLink() {
  try {
    await navigator.clipboard.writeText(location.href);
    toast("Link copied");
  } catch {
    toast("Copy the link from your browser’s address bar.");
  }
}
async function startExample(button) {
  button.disabled = true;
  try {
    const result = await api("/api/examples", {});
    location.href = "/d/" + result.id;
  } catch (e) {
    button.disabled = false;
    toast(e.message);
  }
}
function discussionCard(d) {
  return `<a class="discussion" href="/d/${d.id}"><div class="discussion-main"><h3>${esc(d.topic)}</h3>
    <p>${d.mode === "example" ? "Guided example · " : ""}${esc(d.action || STATUS[d.status] || "Read discussion")}</p></div>${pill(d.status)}<span class="go">${["consensus", "dissensus", "insufficient"].includes(d.status) ? "Read result" : "Open discussion"} <span aria-hidden="true">↗</span></span></a>`;
}
