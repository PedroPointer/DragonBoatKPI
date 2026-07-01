"""SQLite database engine and session management."""

from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from dragonboat.config import settings

# Engine — sync (for CLI) and shared with web via thread pool
_db_path = settings.resolved_registro_file.parent / "dragonboat.db"
DB_URL = f"sqlite:///{_db_path}"

engine = create_engine(DB_URL, echo=False, future=True)

# Enable WAL mode for better concurrent access
@event.listens_for(engine, "connect")
def _set_wal(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Get a new sync session. Use as:
    with get_session() as session:
        ...
    """
    return SessionLocal()


def init_db() -> None:
    """Create all tables and seed reference data."""
    from dragonboat.db_models import Base, Boat, Category

    Base.metadata.create_all(bind=engine)

    # Seed boats if empty
    with get_session() as session:
        existing = session.query(Boat).count()
        if existing == 0:
            session.add_all([
                Boat(name="DB12", display_name="Dragon Boat 12", num_rows=5, total_persons=12),
                Boat(name="DB22", display_name="Dragon Boat 22", num_rows=10, total_persons=22),
            ])
            session.commit()

    # Seed categories if empty
    with get_session() as session:
        existing = session.query(Category).count()
        if existing == 0:
            from dragonboat.db_models import CATEGORIAS_COMPETICION
            session.add_all([
                Category(name=name) for name in CATEGORIAS_COMPETICION
            ])
            session.commit()

    # Migrate: add new columns to test_metrics if missing
    _migrate_add_column(engine, "test_metrics", "dist_max_palada", "FLOAT")
    _migrate_add_column(engine, "test_metrics", "dist_min_palada", "FLOAT")


def _migrate_add_column(engine, table: str, column: str, coltype: str) -> None:
    """Add column to table if it doesn't exist (SQLite)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        results = conn.execute(
            text(f"PRAGMA table_info({table})")
        ).all()
        col_names = [r[1] for r in results]
        if column not in col_names:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
            conn.commit()
