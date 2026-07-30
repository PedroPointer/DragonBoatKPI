"""SQLite database engine and session management."""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from dragonboat.config import settings

_db_path = settings.resolved_registro_file.parent / "dragonboat.db"
DB_URL = f"sqlite:///{_db_path}"

engine = create_engine(DB_URL, echo=False, future=True)


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


def _ensure_column(conn, table: str, column: str, ddl_type: str) -> None:
    """Idempotent column-add for SQLite.

    Inspects PRAGMA table_info and runs ALTER TABLE ADD COLUMN only if the
    column is missing. Safe to call repeatedly; does not touch existing rows.
    """
    existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def _run_migrations(engine) -> None:
    """Apply schema migrations idempotently after create_all.

    The project does not use alembic; this is the lightweight mechanism that
    keeps existing DBs up to date when the ORM gains new columns.
    """
    with engine.begin() as conn:
        _ensure_column(conn, "test_metrics", "sectores_detalle", "TEXT")
        _ensure_column(conn, "test_metrics", "paladas_detalle", "TEXT")


def init_db() -> None:
    """Create all tables, apply idempotent migrations, and seed reference data."""
    from dragonboat.db_models import (
        Base,
        AppSetting,
        Boat,
        Category,
        Distancia,
        TestType,
        CATEGORIAS_COMPETICION,
        DISTANCIAS_SEED,
    )

    Base.metadata.create_all(bind=engine)
    _run_migrations(engine)

    with get_session() as session:
        if session.query(Boat).count() == 0:
            session.add_all([
                Boat(name="DB12", display_name="Dragon Boat 12", num_rows=5, total_persons=12),
                Boat(name="DB22", display_name="Dragon Boat 22", num_rows=10, total_persons=22),
            ])
            session.commit()

        if session.query(Category).count() == 0:
            session.add_all([Category(name=name) for name in CATEGORIAS_COMPETICION])
            session.commit()

        if session.query(TestType).count() == 0:
            session.add_all([
                TestType(name="entreno"),
                TestType(name="competicion"),
            ])
            session.commit()

        if session.query(Distancia).count() == 0:
            session.add_all([
                Distancia(metros=m, descripcion=d, orden=o)
                for m, d, o in DISTANCIAS_SEED
            ])
            session.commit()

        if session.query(AppSetting).count() == 0:
            session.add_all([
                AppSetting(key="umbral_velocidad_parado", value="5.0"),
            ])
            session.commit()
