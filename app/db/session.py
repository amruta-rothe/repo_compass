"""Database session management for RepoCompass."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "get_db",
    "init_db",
    "ensure_db_initialized",
    "get_db_info",
]


_db_initialized = False


def _build_engine():
    settings = get_settings()
    db_url = settings.database_url or "sqlite:///./repo_compass_dev.db"

    # Normalize postgres:// to postgresql:// for SQLAlchemy 2.0+
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )
    else:
        # PostgreSQL (Supabase / Neon / Direct)
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return engine


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
        ensure_db_initialized()
    return _SessionLocal


def ensure_db_initialized():
    """Ensure all database tables exist on startup."""
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Database table initialization warning: {e}")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create all tables (for SQLite dev mode or Supabase PostgreSQL bootstrap)."""
    from app.db import models  # noqa: F401 – registers models with Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    # Safe SQLite dev migration for new Profile columns
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN ml_survey JSON"))
            conn.commit()
    except Exception:
        pass
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN ml_features JSON"))
            conn.commit()
    except Exception:
        pass


def get_db_info() -> dict:
    """Return current database connection details for diagnostics."""
    settings = get_settings()
    is_postgres = bool(settings.database_url and not settings.database_url.startswith("sqlite"))
    return {
        "is_postgres": is_postgres,
        "type": "PostgreSQL (Supabase)" if is_postgres else "SQLite (Local Dev)",
        "url_masked": (
            settings.database_url.split("@")[-1] if "@" in (settings.database_url or "")
            else "repo_compass_dev.db"
        )
    }
