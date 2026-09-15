/* Forum shared helpers + app shell (Phase B).
   Every page includes this after a <div class="topbar"><div class="topbar-in"
   id="shellBar"> skeleton; call shell("home"|"floor"|"room"|"profile"). */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => Math.round(x * 100);
const VLABEL = { accept: "accept", accept_with_reservations: "reservations", reject: "reject" };
const VCOLOR = { accept: "var(--ok)", accept_with_reservations: "var(--warn)", reject: "var(--bad)" };

async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function timeago(ts) {
  const s = Math.max(1, (Date.now() / 1000) - ts);
  if (s < 90) return "just now";
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

function closesIn(ts) {
  const s = ts - Date.now() / 1000;
  if (s <= 0) return "closing";
  if (s < 3600) return `closes in ${Math.round(s / 60)}m`;
  if (s < 86400) return `closes in ${Math.round(s / 3600)}h`;
  return `closes in ${Math.round(s / 86400)}d`;
}

let SHELL_ME = null;

/* Renders the top bar and resolves the current user. NEVER rejects: a dead
   server must degrade to a visible message, not a blank page. */
async function shell(active) {
  let me = null;
  try {
    me = await api("/api/me");
    window.SERVER_DOWN = false;
  } catch {
    window.SERVER_DOWN = true;
  }
  SHELL_ME = me && me.user;
  window.DEFAULT_TOPIC = me && me.default_topic;
  let unseen = 0;
  if (SHELL_ME && active !== "home") {
    try { unseen = (await api("/api/me/feed")).unseen; } catch {}
  }
  $("shellBar").innerHTML = `
    <div class="wordmark"><a href="/">The <span>Forum</span></a></div>
    <nav class="nav">
      <a href="/" class="${["home", "floor"].includes(active) ? "active" : ""}">The floor${unseen ? '<span class="ndot"></span>' : ""}</a>
    </nav>
    <div class="spacer"></div>
    <span class="menu">${SHELL_ME
      ? `<a href="/u/${esc(SHELL_ME.handle)}">${esc(SHELL_ME.handle)}</a> ·
         <a href="#" onclick="api('/api/logout', {}).then(() => location.href = '/'); return false"
            style="color:var(--muted)">switch</a>`
      : ""}</span>`;
  return SHELL_ME;
}

function serverDownCard() {
  return `<div class="card" style="border-color:var(--bad)">
    <h2 style="font-size:17px">Can't reach the Forum server</h2>
    <p class="sub" style="margin:0">The page loaded, but the server isn't answering. Start it with
    <code>./demo-venv/bin/uvicorn server:app --port 8710 --app-dir demo</code> from the Forum
    directory — this page retries automatically.</p></div>`;
}
