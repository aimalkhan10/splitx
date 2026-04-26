# app/core/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # test connection before using it from pool
    pool_recycle=3600,        # recycle connections every 1 hour
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,      # log SQL in debug mode
)

# ── Session factory ───────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ── Base class for all ORM models ─────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency — one DB session per request ───────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Health check helper ───────────────────────────────────────
def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
