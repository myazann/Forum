"""Forum server — zero-prior entry.

Run:  uvicorn server:app --port 8710   (from demo/, with the venv active)

No login, no signup: the first time someone acts, they silently become a
citizen with a generated pseudonym (cookie session). They can pick a nicer
pseudonym any time via /api/login. Two citizen verbs per deliberation:
share an opinion, respond to the offer (accept / object).
"""

import random

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from forum import db, service
from forum.personas import DEFAULT_TOPIC

app = FastAPI(title="Forum")
WEB_DIR = Path(__file__).parent / "web"
COOKIE = "forum_token"

db.init()

ADJ = ["quiet", "amber", "cedar", "bright", "steady", "plain", "keen", "mellow"]
NOUN = ["harbor", "meadow", "signal", "lantern", "bridge", "orchard", "compass", "commons"]


def _fresh_handle() -> str:
    for _ in range(50):
        h = f"{random.choice(ADJ)}-{random.choice(NOUN)}-{random.randint(10, 99)}"
        if not db.user_by_handle(h):
            return h
    return f"citizen-{random.randint(1000, 9999)}"


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    return db.user_by_token(token) if token else None


def citizen(request: Request, response: Response) -> dict:
    """The zero-prior identity: acting makes you a citizen, silently."""
    u = current_user(request)
    if not u:
        u = db.create_user(_fresh_handle())
        response.set_cookie(COOKIE, u["token"], httponly=True, samesite="lax",
                            max_age=60 * 60 * 24 * 365)
    return u


class LoginBody(BaseModel):
    handle: str


@app.post("/api/login")
def login(body: LoginBody, response: Response):
    """Optional: claim a pseudonym you prefer (also how you return on a new
    device, pilot-grade trust model)."""
    handle = body.handle.strip()[:40]
    if len(handle) < 2:
        raise HTTPException(400, "Pseudonym must be at least 2 characters")
    user = db.user_by_handle(handle) or db.create_user(handle)
    response.set_cookie(COOKIE, user["token"], httponly=True, samesite="lax",
                        max_age=60 * 60 * 24 * 365)
    return {"id": user["id"], "handle": user["handle"]}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    u = current_user(request)
    return {"user": {"id": u["id"], "handle": u["handle"]} if u else None,
            "default_topic": DEFAULT_TOPIC}


# ---- deliberations --------------------------------------------------------

class CreateBody(BaseModel):
    topic: str = ""
    include_personas: bool = True
    min_participants: int = 1
    phase_hours: float = 0


@app.get("/api/deliberations")
def list_deliberations():
    return {"deliberations": db.list_deliberations()}


@app.post("/api/deliberations")
def create_deliberation(body: CreateBody, request: Request, response: Response):
    user = citizen(request, response)
    delib_id = service.create(user, body.topic, body.include_personas,
                              body.min_participants, body.phase_hours)
    return {"id": delib_id}


@app.get("/api/d/{delib_id}")
def get_state(delib_id: str, request: Request):
    v = service.view(delib_id, current_user(request))
    if v is None:
        raise HTTPException(404, "No such deliberation")
    return v


@app.get("/api/d/{delib_id}/audit")
def get_audit(delib_id: str):
    return {"audit": service.audit(delib_id)}


@app.get("/api/me/feed")
def my_feed(request: Request):
    u = current_user(request)
    if not u:
        return {"needs_you": [], "outcomes": [], "notifications": [], "unseen": 0}
    return service.feed(u)


@app.post("/api/me/seen")
def mark_seen(request: Request):
    u = current_user(request)
    if u:
        db.mark_seen(u["id"])
    return {"ok": True}


@app.get("/api/users/{handle}")
def user_profile(handle: str):
    p = service.profile(handle)
    if p is None:
        raise HTTPException(404, "No such pseudonym")
    return p


# ---- the two citizen verbs ------------------------------------------------

class PositionBody(BaseModel):
    text: str


class RespondBody(BaseModel):
    response: str            # accept | object
    objection: str = ""


def _wrap(fn):
    try:
        fn()
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@app.post("/api/d/{delib_id}/position")
def position(delib_id: str, body: PositionBody, request: Request, response: Response):
    user = citizen(request, response)
    if not body.text.strip():
        raise HTTPException(400, "Say what you think first")
    return _wrap(lambda: service.take_position(delib_id, user, body.text.strip()))


@app.post("/api/d/{delib_id}/respond")
def respond(delib_id: str, body: RespondBody, request: Request, response: Response):
    user = citizen(request, response)
    return _wrap(lambda: service.respond(delib_id, user, body.response, body.objection))


@app.post("/api/d/{delib_id}/begin")
def begin(delib_id: str, request: Request, response: Response):
    user = citizen(request, response)
    return _wrap(lambda: service.begin_now(delib_id, user))


@app.post("/api/d/{delib_id}/retry")
def retry(delib_id: str):
    service.retry(delib_id)
    return {"ok": True}


# ---- pages ----------------------------------------------------------------

app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def _page(name: str):
    return FileResponse(WEB_DIR / name, headers={"Cache-Control": "no-cache"})


@app.get("/")
def home():
    return _page("home.html")


@app.get("/floor")
def floor():
    return _page("home.html")            # merged: home IS the floor of topics


@app.get("/u/{handle}")
def profile_page(handle: str):
    return _page("profile.html")


@app.get("/d/{delib_id}")
def room(delib_id: str):
    return _page("room.html")
