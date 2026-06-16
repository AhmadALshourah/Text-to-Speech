"""FastAPI application entry point.

Improvements applied:
- IDEA-04  : GZipMiddleware compresses responses
- IDEA-16  : Security headers middleware (CSP, X-Frame-Options, …)
- IDEA-30  : Structured logging configuration
- IDEA-31  : Enhanced /health endpoint (DB liveness check)
- IDEA-32  : Background periodic cleanup of stale audio files
- IDEA-13  : SlowAPI rate-limit error handler wired up

Run with:
    uvicorn main:app --reload
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db
from app.dependencies import get_db
from app.limiter import limiter
from app.routers import auth, history, share, tts

# ── Logging — IDEA-30 ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

_INSECURE_KEY = "dev-only-insecure-secret-change-me"


# ── Periodic audio cleanup — IDEA-32 ─────────────────────────────────────────

async def _audio_cleanup_loop() -> None:
    """Delete MP3 files older than 10 minutes every 10 minutes."""
    audio_dir = Path(settings.audio_output_dir)
    while True:
        await asyncio.sleep(600)
        try:
            cutoff = time.time() - 600
            for f in audio_dir.glob("*.mp3"):
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink(missing_ok=True)
                except OSError:
                    pass
        except Exception:
            pass  # never let cleanup crash the server


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key == _INSECURE_KEY:
        logger.warning(
            "⚠️  SECRET_KEY is the insecure default — "
            "set a strong random value in .env before deploying."
        )
    init_db()
    task = asyncio.create_task(_audio_cleanup_loop())
    logger.info("VoiceForge started.")
    yield
    task.cancel()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="VoiceForge — Text-to-Speech", version="1.0.0", lifespan=lifespan)

# Rate-limit error handler — IDEA-13
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Compression — IDEA-04
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers — IDEA-16
@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "media-src 'self' blob:; "
        "connect-src 'self'"
    )
    return response


# Request timing log — IDEA-30
@app.middleware("http")
async def _log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    logger.info("%s %s → %d  (%.0fms)", request.method, request.url.path, response.status_code, ms)
    return response


# ── API routes ────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(tts.router)
app.include_router(history.router)
app.include_router(share.router)

# Static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── HTML pages ────────────────────────────────────────────────────────────────

def _page(name: str) -> FileResponse:
    return FileResponse(TEMPLATES_DIR / name)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return _page("index.html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    return _page("login.html")


@app.get("/register", include_in_schema=False)
def register_page() -> FileResponse:
    return _page("register.html")


@app.get("/history", include_in_schema=False)
def history_page() -> FileResponse:
    return _page("history.html")


@app.get("/profile", include_in_schema=False)
def profile_page() -> FileResponse:
    return _page("profile.html")


@app.get("/s/{uuid}", include_in_schema=False)
def share_page(uuid: str) -> FileResponse:
    return _page("share.html")


# ── Health check — IDEA-31 ────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)) -> JSONResponse:
    """Liveness probe: checks DB connectivity."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    payload = {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "version": "1.0.0",
    }
    code = 200 if db_ok else 503
    return JSONResponse(content=payload, status_code=code)
