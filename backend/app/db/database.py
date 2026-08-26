"""
SentinelRisk — Database Engine & Session Management

Provides SQLAlchemy engine, session factory, and declarative Base.
Designed for SQLite in Stage 1; the engine URL can be swapped to
PostgreSQL or another backend in later stages without changing models.
"""

import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all SentinelRisk ORM models."""
    pass


def _get_engine(database_url: str | None = None):
    """Create a SQLAlchemy engine from the given or configured URL."""
    url = database_url or get_settings().database_url
    connect_args = {}

    # SQLite-specific: allow multi-thread access
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args, echo=False)

    # Enable SQLite foreign key enforcement
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Default engine and session factory
engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite_schema(target_engine):
    """Safely apply schema additions for SQLite tables if they exist with older schemas."""
    try:
        with target_engine.connect() as conn:
            # Check cases table
            cursor = conn.connection.cursor()
            existing_tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "cases" in existing_tables:
                existing_cols = [c[1] for c in cursor.execute("PRAGMA table_info(cases)").fetchall()]
                cols_to_add = [
                    ("case_id", "VARCHAR(50)"),
                    ("customer_id", "VARCHAR(100)"),
                    ("merchant_id", "VARCHAR(100)"),
                    ("amount", "FLOAT DEFAULT 0.0"),
                    ("decision", "VARCHAR(30) DEFAULT 'REVIEW'"),
                    ("risk_score", "FLOAT DEFAULT 0.0"),
                    ("priority", "VARCHAR(20) DEFAULT 'MEDIUM'"),
                    ("priority_reason", "TEXT"),
                    ("assigned_to", "VARCHAR(100)"),
                    ("resolution", "VARCHAR(50)"),
                    ("resolution_reason", "TEXT"),
                    ("report_payload", "TEXT"),
                ]
                for col_name, col_def in cols_to_add:
                    if col_name not in existing_cols:
                        cursor.execute(f"ALTER TABLE cases ADD COLUMN {col_name} {col_def}")
                conn.connection.commit()
    except Exception as e:
        logger.warning(f"SQLite schema auto-migration notice: {e}")


def init_database(database_url: str | None = None):
    """
    Create all tables defined by ORM models.

    Safe to call multiple times — CREATE IF NOT EXISTS semantics.
    """
    # Import models so they register with Base.metadata
    import backend.app.db.models  # noqa: F401

    target_engine = _get_engine(database_url) if database_url else engine
    Base.metadata.create_all(bind=target_engine)
    _migrate_sqlite_schema(target_engine)
    logger.info("Database tables initialized successfully.")
    return target_engine
