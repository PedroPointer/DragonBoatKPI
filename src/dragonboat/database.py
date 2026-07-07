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
    from dragonboat.db_models import Base, Boat, Category, TestType

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

    # Seed test types if empty
    with get_session() as session:
        existing = session.query(TestType).count()
        if existing == 0:
            session.add_all([
                TestType(name="entreno"),
                TestType(name="competicion"),
            ])
            session.commit()

    # Migrate: add new columns to test_metrics if missing
    _migrate_add_column(engine, "test_metrics", "dist_max_palada", "FLOAT")
    _migrate_add_column(engine, "test_metrics", "dist_min_palada", "FLOAT")
    _migrate_add_column(engine, "sesiones", "distancia", "INTEGER")
    _migrate_add_column(engine, "test_metrics", "tiempos_por_distancia", "TEXT")

    # Backfill: legacy rows get distancia=200 and tiempos_por_distancia computed
    _backfill_distance_metadata()


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


def _backfill_distance_metadata() -> None:
    """For legacy rows: set distancia=200 and compute tiempos_por_distancia from GPS data."""
    import json as _json
    from dragonboat.db_models import Sesion, TestMetric, TestGpsData

    with get_session() as sess:
        sesiones = sess.query(Sesion).all()
        changed = False
        for s in sesiones:
            if s.distancia is None:
                s.distancia = 200
                changed = True
            tm = s.metric
            if tm and not tm.tiempos_por_distancia:
                gps = sess.query(TestGpsData).filter(TestGpsData.sesion_id == s.id).first()
                if gps:
                    data = _json.loads(gps.data_json)
                    time = data.get("time", [])
                    markers = _compute_markers(time, distancia=200)
                    if markers:
                        tm.tiempos_por_distancia = _json.dumps(markers)
                        changed = True
        if changed:
            sess.commit()


def _compute_markers(time: list[float], distancia: int) -> dict[str, float]:
    """Compute tiempo for D/4 markers from a time array of length > distancia*4 / sample rate.

    The input time array is expected to be the segment's elapsed_time values
    sampled at 25Hz, with time[0] ~= 0. Returns markers every distancia/4 meters.
    Distance is approximated by index assuming 25Hz @ speed >10km/h.
    For legacy backfill, we use the test's full time array (sampled at 25Hz)
    and map index -> approximate distance via time.
    """
    if not time or len(time) < 2:
        return {}
    sample_rate = 25.0
    total_time = float(time[-1])
    if total_time <= 0:
        return {}
    step = distancia / 4.0
    markers: dict[str, float] = {}
    for i in range(1, 5):
        target = step * i
        # Approximate distance by time fraction (good enough for legacy backfill
        # where exact distance_m is not stored; tests were nominally 200m at 10-12 km/h).
        target_time = (target / distancia) * total_time
        # find first index where time >= target_time
        for j, t in enumerate(time):
            if t >= target_time:
                markers[str(int(target))] = round(float(t), 2)
                break
    return markers
