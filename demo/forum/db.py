"""SQLite persistence for Forum (Phase A — PRODUCT.md §5).

Zero-dependency: Python's stdlib sqlite3. Relational tables hold what we
query (users, deliberations index, participants); each deliberation's full
engine state is a JSON document — the engine serializes itself, and at
pilot scale a document per deliberation beats mapping every round/ballot
into rows. WAL mode so reads don't block the single writer.
"""

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DB_PATH = Path(os.environ.get("FORUM_DB", Path(__file__).parent.parent / "forum.db"))

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id         TEXT PRIMARY KEY,
  handle     TEXT UNIQUE NOT NULL,          -- pseudonym (PRODUCT.md §8: pseudonymous by default)
  token      TEXT UNIQUE NOT NULL,          -- session token (name-only login, Phase A)
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS deliberations (
  id         TEXT PRIMARY KEY,
  topic      TEXT NOT NULL,
  status     TEXT NOT NULL,
  created_by TEXT NOT NULL REFERENCES users(id),
  config     TEXT NOT NULL,                 -- JSON: {min_participants, include_personas, threshold, max_rounds}
  state      TEXT NOT NULL,                 -- JSON: full engine state (Deliberation.to_dict)
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS participants (
  delib_id  TEXT NOT NULL REFERENCES deliberations(id),
  user_id   TEXT NOT NULL REFERENCES users(id),
  role      TEXT NOT NULL DEFAULT 'participant',
  joined_at REAL NOT NULL,
  PRIMARY KEY (delib_id, user_id)
);
CREATE TABLE IF NOT EXISTS events (                     -- feed source (Phase B reads this)
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  delib_id TEXT NOT NULL,
  type     TEXT NOT NULL,
  payload  TEXT NOT NULL,
  ts       REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS civic_events (               -- the uncurated civic record
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id  TEXT NOT NULL,
  delib_id TEXT NOT NULL,
  kind     TEXT NOT NULL,                               -- critique_addressed | cited_in_consensus
  round    INTEGER,
  ts       REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id  TEXT NOT NULL,
  delib_id TEXT NOT NULL,
  kind     TEXT NOT NULL,          -- election_open | ballot_open | round_result | outcome
  payload  TEXT NOT NULL,
  ts       REAL NOT NULL,
  seen_at  REAL
);
"""


def conn() -> sqlite3.Connection:
    c = getattr(_local, "conn", None)
    if c is None:
        c = sqlite3.connect(DB_PATH, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        _local.conn = c
    return c


def init():
    conn().executescript(SCHEMA)
    conn().commit()


# ---- users ----------------------------------------------------------------

def create_user(handle: str) -> dict:
    u = {"id": "u_" + uuid.uuid4().hex[:10], "handle": handle.strip(),
         "token": uuid.uuid4().hex, "created_at": time.time()}
    conn().execute("INSERT INTO users (id, handle, token, created_at) VALUES (?,?,?,?)",
                   (u["id"], u["handle"], u["token"], u["created_at"]))
    conn().commit()
    return u


def user_by_handle(handle: str) -> dict | None:
    r = conn().execute("SELECT * FROM users WHERE handle = ?", (handle.strip(),)).fetchone()
    return dict(r) if r else None


def user_by_token(token: str) -> dict | None:
    r = conn().execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    return dict(r) if r else None


def rename_user(user_id: str, handle: str):
    try:
        conn().execute("UPDATE users SET handle=? WHERE id=?", (handle, user_id))
        conn().commit()
    except sqlite3.IntegrityError:
        conn().rollback()
        raise ValueError("That name is already in use. Choose another name.")


# ---- deliberations --------------------------------------------------------

def create_deliberation(delib_id: str, topic: str, status: str, created_by: str,
                        config: dict, state: dict):
    now = time.time()
    conn().execute(
        "INSERT INTO deliberations (id, topic, status, created_by, config, state, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (delib_id, topic, status, created_by, json.dumps(config),
         json.dumps(state, ensure_ascii=False), now, now))
    conn().commit()


def save_state(delib_id: str, status: str, state: dict):
    conn().execute("UPDATE deliberations SET status = ?, state = ?, updated_at = ? WHERE id = ?",
                   (status, json.dumps(state, ensure_ascii=False), time.time(), delib_id))
    conn().commit()


def load_deliberation(delib_id: str) -> dict | None:
    r = conn().execute("SELECT * FROM deliberations WHERE id = ?", (delib_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["config"] = json.loads(d["config"])
    d["state"] = json.loads(d["state"])
    return d


def list_deliberations() -> list[dict]:
    rows = conn().execute(
        "SELECT d.id, d.topic, d.status, d.created_by, d.config, d.created_at, d.updated_at,"
        "       u.handle AS creator_handle,"
        "       (SELECT COUNT(*) FROM participants p WHERE p.delib_id = d.id) AS participant_count,"
        "       json_array_length(d.state, '$.rounds') AS rounds,"
        "       json_extract(d.state, '$.rounds[#-1].approval') AS last_approval"
        " FROM deliberations d JOIN users u ON u.id = d.created_by"
        " ORDER BY d.updated_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d["config"])
        out.append(d)
    return out


# ---- participants ---------------------------------------------------------

def join(delib_id: str, user_id: str, role: str = "participant"):
    conn().execute(
        "INSERT OR IGNORE INTO participants (delib_id, user_id, role, joined_at) VALUES (?,?,?,?)",
        (delib_id, user_id, role, time.time()))
    conn().commit()


def participants(delib_id: str) -> list[dict]:
    rows = conn().execute(
        "SELECT p.user_id, p.role, p.joined_at, u.handle FROM participants p"
        " JOIN users u ON u.id = p.user_id WHERE p.delib_id = ? ORDER BY p.joined_at",
        (delib_id,)).fetchall()
    return [dict(r) for r in rows]


# ---- events ---------------------------------------------------------------

def add_event(delib_id: str, type_: str, payload: dict):
    conn().execute("INSERT INTO events (delib_id, type, payload, ts) VALUES (?,?,?,?)",
                   (delib_id, type_, json.dumps(payload, ensure_ascii=False), time.time()))
    conn().commit()


# ---- civic record ---------------------------------------------------------

def add_civic_event(user_id: str, delib_id: str, kind: str, round_: int | None = None):
    # one row per (user, delib, kind, round) — re-runs of a phase must not double-credit
    row = conn().execute(
        "SELECT 1 FROM civic_events WHERE user_id=? AND delib_id=? AND kind=? AND round IS ?",
        (user_id, delib_id, kind, round_)).fetchone()
    if row:
        return
    conn().execute("INSERT INTO civic_events (user_id, delib_id, kind, round, ts) VALUES (?,?,?,?,?)",
                   (user_id, delib_id, kind, round_, time.time()))
    conn().commit()


def civic_record(user_id: str) -> dict:
    c = conn()
    joined = c.execute("SELECT COUNT(*) FROM participants WHERE user_id=?", (user_id,)).fetchone()[0]
    consensus = c.execute(
        "SELECT COUNT(*) FROM participants p JOIN deliberations d ON d.id=p.delib_id"
        " WHERE p.user_id=? AND d.status='consensus'", (user_id,)).fetchone()[0]
    counts = dict(c.execute(
        "SELECT kind, COUNT(*) FROM civic_events WHERE user_id=? GROUP BY kind",
        (user_id,)).fetchall())
    return {"deliberations": joined, "consensus_reached": consensus,
            "critiques_addressed": counts.get("critique_addressed", 0),
            "cited_in_consensus": counts.get("cited_in_consensus", 0)}


# ---- notifications --------------------------------------------------------

def notify(user_id: str, delib_id: str, kind: str, payload: dict):
    conn().execute("INSERT INTO notifications (user_id, delib_id, kind, payload, ts) VALUES (?,?,?,?,?)",
                   (user_id, delib_id, kind, json.dumps(payload, ensure_ascii=False), time.time()))
    conn().commit()


def notifications_for(user_id: str, limit: int = 30) -> list[dict]:
    rows = conn().execute(
        "SELECT n.*, d.topic FROM notifications n JOIN deliberations d ON d.id=n.delib_id"
        " WHERE n.user_id=? ORDER BY n.ts DESC LIMIT ?", (user_id, limit)).fetchall()
    out = []
    for r in rows:
        n = dict(r)
        n["payload"] = json.loads(n["payload"])
        out.append(n)
    return out


def unseen_count(user_id: str) -> int:
    return conn().execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND seen_at IS NULL",
                          (user_id,)).fetchone()[0]


def mark_seen(user_id: str):
    conn().execute("UPDATE notifications SET seen_at=? WHERE user_id=? AND seen_at IS NULL",
                   (time.time(), user_id))
    conn().commit()


def deliberations_for(user_id: str) -> list[dict]:
    rows = conn().execute(
        "SELECT d.id, d.topic, d.status, d.config, d.updated_at FROM participants p"
        " JOIN deliberations d ON d.id=p.delib_id WHERE p.user_id=? ORDER BY d.updated_at DESC",
        (user_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d["config"])
        out.append(d)
    return out
