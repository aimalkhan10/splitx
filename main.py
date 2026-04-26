# main.py  — SplitX FastAPI Entry Point
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, check_db_connection

# Import all models so SQLAlchemy registers them before create_all()
import app.models  # noqa: F401

from app.routes import auth, users, groups, expenses, payments, balances


# ── Lifespan: runs on startup / shutdown ──────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    print("[INFO] Starting SplitX API...")

    if check_db_connection():
        print("[OK] Database connection successful")
        # Create all tables that don't exist yet
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables verified / created")
    else:
        print("[ERROR] Database connection FAILED -- check .env credentials")

    yield  # app is running

    # ── Shutdown ─────────────────────────────────────────────
    print("[INFO] SplitX API shutting down...")


# ── App instance ──────────────────────────────────────────────
app = FastAPI(
    title       = settings.APP_NAME,
    description = "Splitwise-clone REST API — split expenses with friends & groups",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # tighten in production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────
API_PREFIX = "/api"

app.include_router(auth.router,     prefix=API_PREFIX)
app.include_router(users.router,    prefix=API_PREFIX)
app.include_router(groups.router,   prefix=API_PREFIX)
app.include_router(expenses.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(balances.router, prefix=API_PREFIX)


# ── Root health-check endpoint ────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "app":     settings.APP_NAME,
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    db_ok = check_db_connection()
    return {
        "api":      "ok",
        "database": "ok" if db_ok else "unreachable",
    }
