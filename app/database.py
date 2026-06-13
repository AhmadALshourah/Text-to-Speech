"""Database setup: SQLAlchemy engine, session factory, and declarative base."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# SQLite needs `check_same_thread=False` to be used across FastAPI's threads.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables and apply lightweight column migrations for SQLite."""
    from app.models import conversion, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Add any columns that exist in the model but not yet in the live DB."""
    _ensure_columns("users", [
        ("failed_login_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("lockout_until",         "DATETIME"),
        ("monthly_chars_used",    "INTEGER NOT NULL DEFAULT 0"),
        ("monthly_chars_reset",   "DATETIME"),
    ])


def _ensure_columns(table: str, cols: list[tuple[str, str]]) -> None:
    with engine.connect() as conn:
        result = conn.execute(__import__("sqlalchemy").text(f"PRAGMA table_info({table})"))
        existing = {row[1] for row in result}
        for col_name, col_def in cols:
            if col_name not in existing:
                conn.execute(__import__("sqlalchemy").text(
                    f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"
                ))
        conn.commit()
