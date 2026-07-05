"""Repository layer — all database operations for the application.

Model: csv_uploads (provenance) ──< sesiones (pruebas) ──< test_metrics
                                                    └──< crew_assignments >── crew_members
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import func, desc, cast, Integer
from sqlalchemy.orm import selectinload

from dragonboat.database import get_session, init_db
from dragonboat.db_models import (
    Boat,
    Category,
    CsvUpload,
    Sesion,
    TestMetric,
    TestGpsData,
    TestType,
    CrewMember,
    CrewAssignment,
)
from dragonboat.models import Metricas


# ── CsvUpload CRUD ──

def crear_csv_upload(filename: str, file_path: Optional[str] = None) -> CsvUpload:
    csv = CsvUpload(filename=filename, file_path=file_path, kept=True)
    with get_session() as s:
        s.add(csv)
        s.commit()
        s.refresh(csv)
        return csv


def get_csv_upload(csv_id: int) -> Optional[CsvUpload]:
    with get_session() as s:
        return (
            s.query(CsvUpload)
            .options(selectinload(CsvUpload.sesiones).selectinload(Sesion.metric))
            .filter(CsvUpload.id == csv_id)
            .first()
        )


def get_csv_upload_by_filename(filename: str) -> Optional[CsvUpload]:
    with get_session() as s:
        return (
            s.query(CsvUpload)
            .filter(CsvUpload.filename == filename)
            .first()
        )


def list_csv_uploads(limit: int = 50) -> list[CsvUpload]:
    with get_session() as s:
        return (
            s.query(CsvUpload)
            .options(
                selectinload(CsvUpload.sesiones).selectinload(Sesion.metric),
                selectinload(CsvUpload.sesiones).selectinload(Sesion.boat),
                selectinload(CsvUpload.sesiones).selectinload(Sesion.crew_assignments).selectinload(CrewAssignment.crew_member),
            )
            .order_by(desc(CsvUpload.uploaded_at))
            .limit(limit)
            .all()
        )


def update_csv_upload_kept(csv_id: int, kept: bool) -> Optional[CsvUpload]:
    with get_session() as s:
        csv = s.query(CsvUpload).filter(CsvUpload.id == csv_id).first()
        if not csv:
            return None
        csv.kept = kept
        s.commit()
        s.refresh(csv)
        return csv


def delete_csv_upload(csv_id: int) -> bool:
    """Delete a CsvUpload and all its sesiones (cascade). Deletes file on disk if kept."""
    with get_session() as s:
        csv = s.query(CsvUpload).filter(CsvUpload.id == csv_id).first()
        if not csv:
            return False
        if csv.file_path and csv.kept:
            try:
                os.unlink(csv.file_path)
            except OSError:
                pass
        s.delete(csv)
        s.commit()
        return True


# ── Sesion CRUD (one 200m tramo = one prueba) ──

def crear_sesion(
    csv_upload_id: int,
    test_number: int,
    metric: Metricas,
    fecha_hora: datetime,
    tipo: Optional[str] = "entreno",
    chart_filename: Optional[str] = None,
    boat_id: Optional[int] = None,
) -> Sesion:
    with get_session() as s:
        sesion = Sesion(
            csv_upload_id=csv_upload_id,
            test_number=test_number,
            fecha_hora=fecha_hora,
            tipo=tipo,
            boat_id=boat_id,
        )
        s.add(sesion)
        s.flush()

        tm = TestMetric(
            sesion_id=sesion.id,
            tiempo_total=metric.tiempo_total,
            velocidad_media=metric.velocidad_media,
            velocidad_maxima=metric.velocidad_maxima,
            velocidad_min_post10=metric.velocidad_min_post10,
            aceleracion_max=metric.aceleracion_max,
            tiempo_11kmh=metric.tiempo_11kmh,
            tiempo_12kmh=metric.tiempo_12kmh,
            tiempo_50m=metric.tiempo_50m,
            tiempo_100m=metric.tiempo_100m,
            tiempo_150m=metric.tiempo_150m,
            num_paladas=metric.num_paladas,
            dist_media_palada=metric.dist_media_palada,
            dist_std_palada=metric.dist_std_palada,
            dist_max_palada=metric.dist_max_palada,
            dist_min_palada=metric.dist_min_palada,
            chart_filename=chart_filename,
        )
        s.add(tm)
        s.commit()
        s.refresh(sesion)
        return sesion


def get_sesion(prueba_id: int) -> Optional[Sesion]:
    with get_session() as s:
        return (
            s.query(Sesion)
            .options(
                selectinload(Sesion.metric),
                selectinload(Sesion.boat),
                selectinload(Sesion.csv_upload),
                selectinload(Sesion.crew_assignments).selectinload(CrewAssignment.crew_member),
            )
            .filter(Sesion.id == prueba_id)
            .first()
        )


def get_sesiones(limit: int = 20) -> list[Sesion]:
    with get_session() as s:
        return (
            s.query(Sesion)
            .options(
                selectinload(Sesion.metric),
                selectinload(Sesion.boat),
                selectinload(Sesion.csv_upload),
                selectinload(Sesion.crew_assignments).selectinload(CrewAssignment.crew_member),
            )
            .order_by(desc(Sesion.fecha_hora))
            .limit(limit)
            .all()
        )


def get_csv_sesiones(csv_upload_id: int) -> list[Sesion]:
    with get_session() as s:
        return (
            s.query(Sesion)
            .options(selectinload(Sesion.metric), selectinload(Sesion.boat))
            .filter(Sesion.csv_upload_id == csv_upload_id)
            .order_by(Sesion.test_number)
            .all()
        )


def update_sesion(
    prueba_id: int,
    custom_name: Optional[str] = None,
    categoria: Optional[str] = None,
    boat_id: Optional[int] = None,
    tipo: Optional[str] = None,
) -> Optional[Sesion]:
    with get_session() as s:
        sesion = s.query(Sesion).filter(Sesion.id == prueba_id).first()
        if not sesion:
            return None
        if custom_name is not None:
            sesion.custom_name = custom_name
        if categoria is not None:
            sesion.categoria = categoria if categoria else None
        if boat_id is not None:
            sesion.boat_id = boat_id
        if tipo is not None:
            sesion.tipo = tipo
        s.commit()
        s.refresh(sesion)
        return sesion


def delete_sesion(prueba_id: int) -> bool:
    """Delete a sesion (prueba). If parent csv_upload becomes empty, delete it too."""
    with get_session() as s:
        sesion = s.query(Sesion).filter(Sesion.id == prueba_id).first()
        if not sesion:
            return False
        csv_id = sesion.csv_upload_id
        s.delete(sesion)
        s.flush()

        if csv_id is not None:
            remaining = s.query(Sesion).filter(Sesion.csv_upload_id == csv_id).count()
            if remaining == 0:
                csv = s.query(CsvUpload).filter(CsvUpload.id == csv_id).first()
                if csv:
                    if csv.file_path and csv.kept:
                        try:
                            os.unlink(csv.file_path)
                        except OSError:
                            pass
                    s.delete(csv)

        s.commit()
        return True


def get_distinct_names() -> list[str]:
    """Return distinct custom_names for autocomplete."""
    with get_session() as s:
        results = (
            s.query(Sesion.custom_name)
            .filter(Sesion.custom_name.isnot(None))
            .filter(Sesion.custom_name != "")
            .distinct()
            .order_by(Sesion.custom_name)
            .all()
        )
        return [r[0] for r in results]


# ── Ranking & Stats ──

def get_ranking(
    boat_name: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Top N fastest 200m pruebas."""
    with get_session() as s:
        q = (
            s.query(
                Sesion.id.label("sesion_id"),
                TestMetric.tiempo_total,
                TestMetric.velocidad_media,
                TestMetric.velocidad_maxima,
                TestMetric.num_paladas,
                TestMetric.dist_media_palada,
                Sesion.custom_name,
                Sesion.categoria,
                Boat.name.label("boat_name"),
                Sesion.fecha_hora,
            )
            .join(Sesion, TestMetric.sesion_id == Sesion.id)
            .outerjoin(Boat, Sesion.boat_id == Boat.id)
            .order_by(TestMetric.tiempo_total)
            .limit(limit)
        )
        if boat_name:
            q = q.filter(Boat.name == boat_name)
        return [
            {
                "sesion_id": r.sesion_id,
                "tiempo_total": r.tiempo_total,
                "velocidad_media": r.velocidad_media,
                "velocidad_maxima": r.velocidad_maxima,
                "num_paladas": r.num_paladas,
                "dist_media_palada": r.dist_media_palada,
                "custom_name": r.custom_name,
                "categoria": r.categoria,
                "boat_name": r.boat_name,
                "fecha": r.fecha_hora,
            }
            for r in q.all()
        ]


def get_boat_stats() -> list[dict]:
    """Aggregate stats per boat type."""
    with get_session() as s:
        results = (
            s.query(
                Boat.name,
                Boat.display_name,
                func.count(TestMetric.id).label("num_tests"),
                func.avg(TestMetric.tiempo_total).label("avg_tiempo"),
                func.min(TestMetric.tiempo_total).label("best_tiempo"),
                func.max(TestMetric.tiempo_total).label("worst_tiempo"),
                func.avg(TestMetric.velocidad_media).label("avg_velocidad"),
                func.avg(TestMetric.num_paladas).label("avg_paladas"),
                func.avg(TestMetric.dist_media_palada).label("avg_dist_palada"),
            )
            .join(Sesion, TestMetric.sesion_id == Sesion.id)
            .join(Boat, Sesion.boat_id == Boat.id)
            .group_by(Boat.name)
            .all()
        )
        return [
            {
                "name": r.name,
                "display_name": r.display_name,
                "num_tests": r.num_tests,
                "avg_tiempo": round(r.avg_tiempo, 2) if r.avg_tiempo else 0,
                "best_tiempo": round(r.best_tiempo, 2) if r.best_tiempo else 0,
                "worst_tiempo": round(r.worst_tiempo, 2) if r.worst_tiempo else 0,
                "avg_velocidad": round(r.avg_velocidad, 2) if r.avg_velocidad else 0,
                "avg_paladas": round(r.avg_paladas, 1) if r.avg_paladas else 0,
                "avg_dist_palada": round(r.avg_dist_palada, 2) if r.avg_dist_palada else 0,
            }
            for r in results
        ]


# ── TestGpsData ──

def crear_test_gps_data(sesion_id: int, data: dict) -> None:
    """Store the full 25Hz sensor data dict as JSON."""
    with get_session() as s:
        existing = s.query(TestGpsData).filter(TestGpsData.sesion_id == sesion_id).first()
        if existing:
            existing.data_json = json.dumps(data, ensure_ascii=False)
        else:
            s.add(TestGpsData(
                sesion_id=sesion_id,
                data_json=json.dumps(data, ensure_ascii=False),
            ))
        s.commit()


def get_test_gps_data(sesion_id: int) -> dict | None:
    """Load the full 25Hz sensor data dict. Returns None if not found."""
    with get_session() as s:
        row = s.query(TestGpsData).filter(TestGpsData.sesion_id == sesion_id).first()
        if not row:
            return None
        return json.loads(row.data_json)


def get_trajectory(sesion_id: int) -> list[list[float]]:
    """Return decimated [[lat, lon], ...] at ~5Hz from the 25Hz JSON.

    Decimates to avoid sending 25Hz data for the leaflet map.
    """
    data = get_test_gps_data(sesion_id)
    if not data:
        return []
    lats = data.get("lat", [])
    lons = data.get("lon", [])
    if not lats or not lons:
        return []
    # Decimate from 25Hz to ~5Hz: sample every 5th point
    step = 5
    return [[lats[i], lons[i]] for i in range(0, len(lats), step)]


# ── CrewMember CRUD ──

def list_crew() -> list[CrewMember]:
    with get_session() as s:
        return s.query(CrewMember).order_by(CrewMember.nombre, CrewMember.apellido).all()


def list_crew_by_frequency() -> list[dict]:
    """Return crew members ordered by assignment frequency (most used first)."""
    with get_session() as s:
        results = (
            s.query(
                CrewMember.id,
                CrewMember.nombre,
                CrewMember.apellido,
                CrewMember.categoria,
                CrewMember.photo_path,
                func.count(CrewAssignment.id).label("freq"),
            )
            .outerjoin(CrewAssignment, CrewAssignment.crew_member_id == CrewMember.id)
            .group_by(CrewMember.id)
            .order_by(func.count(CrewAssignment.id).desc(), CrewMember.nombre)
            .all()
        )
        return [
            {
                "id": r.id,
                "nombre": r.nombre,
                "apellido": r.apellido,
                "categoria": r.categoria,
                "photo_path": r.photo_path,
                "freq": r.freq,
            }
            for r in results
        ]


def get_crew_member(member_id: int) -> Optional[CrewMember]:
    with get_session() as s:
        return s.query(CrewMember).filter(CrewMember.id == member_id).first()


def crear_crew_member(
    nombre: str,
    apellido: str,
    categoria: Optional[str] = None,
    photo_path: Optional[str] = None,
) -> CrewMember:
    with get_session() as s:
        cm = CrewMember(
            nombre=nombre,
            apellido=apellido,
            categoria=categoria,
            photo_path=photo_path,
        )
        s.add(cm)
        s.commit()
        s.refresh(cm)
        return cm


def update_crew_member(
    member_id: int,
    nombre: Optional[str] = None,
    apellido: Optional[str] = None,
    categoria: Optional[str] = None,
) -> Optional[CrewMember]:
    with get_session() as s:
        cm = s.query(CrewMember).filter(CrewMember.id == member_id).first()
        if not cm:
            return None
        if nombre is not None:
            cm.nombre = nombre
        if apellido is not None:
            cm.apellido = apellido
        if categoria is not None:
            cm.categoria = categoria if categoria else None
        s.commit()
        s.refresh(cm)
        return cm


def delete_crew_member(member_id: int) -> bool:
    with get_session() as s:
        cm = s.query(CrewMember).filter(CrewMember.id == member_id).first()
        if not cm:
            return False
        s.delete(cm)
        s.commit()
        return True


# ── CrewAssignment ──

def get_assignments(prueba_id: int) -> list[CrewAssignment]:
    with get_session() as s:
        return (
            s.query(CrewAssignment)
            .options(selectinload(CrewAssignment.crew_member))
            .filter(CrewAssignment.sesion_id == prueba_id)
            .all()
        )


def save_assignments(prueba_id: int, assignments: list[dict]) -> None:
    """Replace all crew assignments for a prueba.

    Each dict: {crew_member_id, role, side, row_number}
    """
    with get_session() as s:
        s.query(CrewAssignment).filter(CrewAssignment.sesion_id == prueba_id).delete()
        for a in assignments:
            s.add(CrewAssignment(
                sesion_id=prueba_id,
                crew_member_id=a["crew_member_id"],
                role=a["role"],
                side=a.get("side"),
                row_number=a.get("row_number"),
            ))
        s.commit()


# ── Category CRUD ──

def list_categories() -> list[Category]:
    with get_session() as s:
        return s.query(Category).order_by(Category.name).all()


def get_category(category_id: int) -> Optional[Category]:
    with get_session() as s:
        return s.query(Category).filter(Category.id == category_id).first()


def crear_category(name: str) -> Category:
    with get_session() as s:
        cat = Category(name=name)
        s.add(cat)
        s.commit()
        s.refresh(cat)
        return cat


def update_category(category_id: int, name: str) -> Optional[Category]:
    with get_session() as s:
        cat = s.query(Category).filter(Category.id == category_id).first()
        if not cat:
            return None
        cat.name = name
        s.commit()
        s.refresh(cat)
        return cat


def delete_category(category_id: int) -> bool:
    with get_session() as s:
        cat = s.query(Category).filter(Category.id == category_id).first()
        if not cat:
            return False
        s.delete(cat)
        s.commit()
        return True


# ── TestType CRUD ──

def list_test_types() -> list[TestType]:
    with get_session() as s:
        return s.query(TestType).order_by(TestType.name).all()


def get_test_type(type_id: int) -> Optional[TestType]:
    with get_session() as s:
        return s.query(TestType).filter(TestType.id == type_id).first()


def crear_test_type(name: str) -> TestType:
    with get_session() as s:
        tt = TestType(name=name)
        s.add(tt)
        s.commit()
        s.refresh(tt)
        return tt


def update_test_type(type_id: int, name: str) -> Optional[TestType]:
    with get_session() as s:
        tt = s.query(TestType).filter(TestType.id == type_id).first()
        if not tt:
            return None
        tt.name = name
        s.commit()
        s.refresh(tt)
        return tt


def delete_test_type(type_id: int) -> bool:
    with get_session() as s:
        tt = s.query(TestType).filter(TestType.id == type_id).first()
        if not tt:
            return False
        s.delete(tt)
        s.commit()
        return True


# ── Calendario ──

def get_dias_con_entrenamientos(year: int, month: int) -> list[int]:
    """Return list of days in the given month that have sesiones with metrics."""
    with get_session() as s:
        results = (
            s.query(
                cast(func.strftime("%d", Sesion.fecha_hora), Integer).label("dia")
            )
            .filter(
                cast(func.strftime("%Y", Sesion.fecha_hora), Integer) == year,
                cast(func.strftime("%m", Sesion.fecha_hora), Integer) == month,
                Sesion.metric != None,
            )
            .distinct()
            .order_by("dia")
            .all()
        )
        return [r.dia for r in results]
