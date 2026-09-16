"""Forum's participant web app. Run one uvicorn worker with SQLite."""

from contextlib import asynccontextmanager
from pathlib import Path
import random
import re
import threading

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from forum import db, service


@asynccontextmanager
async def lifespan(app):
    db.init()
    stop = threading.Event()

    def scheduler():
        while not stop.is_set():
            service.tick()
            stop.wait(1)
    worker = threading.Thread(target=scheduler, daemon=True)
    worker.start()
    yield
    stop.set()
    worker.join(timeout=2)


app = FastAPI(title="Forum", lifespan=lifespan)
WEB_DIR = Path(__file__).parent / "web"
COOKIE = "forum_token"
ADJ = ["quiet", "amber", "cedar", "bright", "steady", "keen", "mellow"]
NOUN = ["harbor", "meadow", "lantern", "bridge", "orchard", "compass", "commons"]


def current_user(request):
    token = request.cookies.get(COOKIE)
    return db.user_by_token(token) if token else None


def citizen(request, response):
    user = current_user(request)
    if not user:
        import uuid
        handle = f"{random.choice(ADJ)}-{random.choice(NOUN)}-{uuid.uuid4().hex[:5]}"
        user = db.create_user(handle)
        response.set_cookie(COOKIE, user["token"], httponly=True, samesite="lax",
                            secure=request.url.scheme == "https", max_age=60 * 60 * 24 * 365)
    return user


def required_user(request):
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Your session is not available in this browser. Open your discussion in the browser you used before.")
    return user


def call(fn):
    try:
        result = fn()
        return result if result is not None else {"ok": True}
    except LookupError as e:
        raise HTTPException(404, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.middleware("http")
async def private_state(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/api/me")
def me(request: Request):
    u = current_user(request)
    return {"user": {"id": u["id"], "handle": u["handle"]} if u else None,
            "live_available": service.live_available()}


class NameBody(BaseModel):
    handle: str = Field(min_length=2, max_length=40)


@app.post("/api/me/name")
def rename(body: NameBody, request: Request):
    user = required_user(request)
    handle = body.handle.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,39}", handle):
        raise HTTPException(400, "Use 2–40 letters, numbers, hyphens or underscores.")
    call(lambda: db.rename_user(user["id"], handle))
    return {"id": user["id"], "handle": handle}


@app.post("/api/login")
def login():
    raise HTTPException(410, "A public name cannot be used to sign in. Your identity is saved in the browser where you participated.")


@app.post("/api/examples")
def create_example(request: Request, response: Response):
    user = citizen(request, response)
    return {"id": service.create_example(user)}


class CreateBody(BaseModel):
    topic: str = Field(min_length=10, max_length=240)
    context: str = Field(default="", max_length=1600)
    intake_hours: float = Field(default=24, ge=1/60, le=168)
    phase_hours: float = Field(default=24, ge=1/60, le=168)


@app.post("/api/deliberations")
def create(body: CreateBody, request: Request, response: Response):
    user = citizen(request, response)
    return {"id": call(lambda: service.create(user, body.topic, body.context,
                                             body.intake_hours, body.phase_hours))}


@app.get("/api/deliberations")
def discussions():
    # Examples belong to the visitor who started them, not a global demo feed.
    return {"deliberations": [d for d in db.list_deliberations() if d["config"].get("mode") == "live"]}


@app.get("/api/d/{delib_id}")
def state(delib_id: str, request: Request):
    return call(lambda: service.view(delib_id, current_user(request)))


@app.get("/api/d/{delib_id}/audit")
def audit(delib_id: str):
    return {"audit": call(lambda: service.audit(delib_id))}


@app.get("/api/me/feed")
def feed(request: Request):
    user = current_user(request)
    return service.feed(user) if user else {"needs_you": [], "waiting": [], "outcomes": [], "notifications": [], "unseen": 0}


@app.post("/api/me/seen")
def seen(request: Request):
    user = required_user(request)
    db.mark_seen(user["id"])
    return {"ok": True}


@app.get("/api/users/{handle}")
def profile(handle: str, request: Request):
    return call(lambda: service.profile(handle, current_user(request)))


class PositionBody(BaseModel):
    text: str = Field(default="", max_length=5000)
    choice: str | None = None


class RespondBody(BaseModel):
    response: str
    objection: str = Field(default="", max_length=3000)
    round_number: int = Field(ge=1)
    proposal_id: str = Field(min_length=1, max_length=100)


@app.post("/api/d/{delib_id}/position")
def position(delib_id: str, body: PositionBody, request: Request, response: Response):
    user = citizen(request, response)
    return call(lambda: service.take_position(delib_id, user, body.text, body.choice))


@app.post("/api/d/{delib_id}/continue")
def next_step(delib_id: str, request: Request):
    return call(lambda: service.continue_journey(delib_id, required_user(request)))


@app.post("/api/d/{delib_id}/respond")
def respond(delib_id: str, body: RespondBody, request: Request):
    return call(lambda: service.respond(delib_id, required_user(request), body.response,
                                        body.objection, body.round_number, body.proposal_id))


@app.post("/api/d/{delib_id}/begin")
def begin(delib_id: str, request: Request):
    return call(lambda: service.begin_now(delib_id, required_user(request)))


@app.post("/api/d/{delib_id}/retry")
def retry(delib_id: str, request: Request):
    return call(lambda: service.retry(delib_id, required_user(request)))


app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def page(name):
    return FileResponse(WEB_DIR / name, headers={"Cache-Control": "no-cache"})


@app.get("/")
@app.get("/floor")
def home():
    return page("home.html")


@app.get("/u/{handle}")
def profile_page(handle: str):
    return page("profile.html")


@app.get("/d/{delib_id}")
def room(delib_id: str):
    return page("room.html")
