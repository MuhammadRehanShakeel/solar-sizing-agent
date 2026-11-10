"""
main.py - Starts the SolarSaathi API.

Run:  venv\\Scripts\\python.exe main.py      (or double-click start_project.bat)
API docs (try every endpoint): http://localhost:5002/docs
"""
import logging
import os
import sys
from contextlib import asynccontextmanager

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app import config  # noqa: E402
from app.core.security import enforce_rate_limit  # noqa: E402

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("logs/backend.log", encoding="utf-8")],
)
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app):
    """Runs once when the server starts: check the database and the AI keys."""
    from app.agent.llm import available_models
    from app.database import execute_query
    try:
        execute_query("SELECT 1 AS ok", fetch_one=True)
        log.info("[OK] Connected to SQL Server (%s / %s)", config.DB_SERVER, config.DB_NAME)
    except Exception as e:
        log.error("[ERROR] Database problem: %s  ->  run scripts\\init_db.py first", e)
    models = available_models()
    if models:
        log.info("[OK] AI models: %s", ", ".join(models))
        from app.services import gemini
        gemini.warm_up_in_background()                   # find a Gemini model the key may use
    else:
        log.warning("[!] No GROQ_API_KEY / GEMINI_API_KEY in backend/.env - only the quick calculator works")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="SolarSaathi API",
    description="AI solar sizing agent for Pakistan: LangGraph + Groq / Gemini, bill reading, voice, PDF quotes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,          # only our own frontend, never "*"
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],          # (no DELETE route exists)
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_layer(request: Request, call_next):
    """General rate limit + safe browser headers on every response."""
    try:
        enforce_rate_limit(request, "all", config.RATE_LIMIT_DEFAULT)
    except HTTPException as e:
        return JSONResponse({"detail": e.detail}, status_code=429)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
    return response


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    """Never show Python errors to users; the details go to logs/backend.log."""
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)


from app.routes import admin_routes, auth_routes, chat_routes, planner_routes, quote_routes  # noqa: E402

for module in (chat_routes, quote_routes, planner_routes, auth_routes, admin_routes):
    app.include_router(module.router)


@app.get("/")
def root():
    return {"api": "SolarSaathi", "status": "online", "version": app.version, "docs": "/docs"}


@app.get("/health")
def health():
    from app.agent.llm import available_models
    from app.database import execute_query
    try:
        execute_query("SELECT 1 AS ok", fetch_one=True)
        db = "ok"
    except Exception:
        db = "down"
    models = available_models()
    return {"status": "healthy" if db == "ok" and models else "degraded", "database": db, "ai_models": models,
            "bill_reading": bool(config.GEMINI_API_KEY), "voice": bool(config.GROQ_API_KEY)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, reload=False)
