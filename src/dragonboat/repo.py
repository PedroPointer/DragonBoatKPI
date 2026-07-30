"""Repository layer — all database operations for the application.

Jerarquía (sin ciclos, FKs en el hijo):
  sesiones (día)
    ├─ csv_uploads (1:N)
    │    └─ gps_data (1:1)
    │         └─ test_metrics (0:N, derivados)
    ├─ test_metrics (1:N)
    │    ├─ crew_assignments (1:N)
    │    └─ gps_data (0..1 FK)
    └─ gps_data (1:N)
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import selectinload

from dragonboat.database import get_session
from dragonboat.db_models import (
    AppSetting,
    Boat,
    Category,
    CsvUpload,
    Distancia,
    GpsData,
    Sesion,
    TestMetric,
    TestType,
    CrewMember,
    CrewAssignment,
)
from dragonboat.models import Metricas
from dragonboat.config import settings
from dragonboat.analysis._utils import format_duration


# ════════════════════════════════════════════════════════════════════
#  Distancias (catálogo)
# ════════════════════════════════════════════════════════════════════

def get_or_create_distancia(metros: int) -> Distancia:
    with get_session() as s:
        d = s.query(Distancia).filter(Distancia.metros == metros).first()
        if d:
            return d
        d = Distancia(metros=metros, descripcion=f"{metros} metros", orden=metros)
        s.add(d)
        s.commit()
        s.refresh(d)
        return d


def get_distancia_by_metros(metros: int) -> Optional[Distancia]:
    with get_session() as s:
        return s.query(Distancia).filter(Distancia.metros == metros).first()


def get_distancia(distancia_id: int) -> Optional[Distancia]:
    with get_session() as s:
        return s.query(Distancia).filter(Distancia.id == distancia_id).first()


def list_distancias() -> list[Distancia]:
    with get_session() as s:
        return s.query(Distancia).order_by(Distancia.orden).all()


def crear_distancia(metros: int, descripcion: str, orden: int) -> Distancia:
    with get_session() as s:
        d = Distancia(metros=metros, descripcion=descripcion, orden=orden)
        s.add(d)
        s.commit()
        s.refresh(d)
        return d


def update_distancia(distancia_id: int, descripcion: str, orden: int) -> Optional[Distancia]:
    with get_session() as s:
        d = s.query(Distancia).filter(Distancia.id == distancia_id).first()
        if not d:
            return None
        d.descripcion = descripcion
        d.orden = orden
        s.commit()
        s.refresh(d)
        return d


def delete_distancia(distancia_id: int) -> bool:
    with get_session() as s:
        d = s.query(Distancia).filter(Distancia.id == distancia_id).first()
        if not d:
            return False
        if s.query(TestMetric).filter(TestMetric.distancia_id == distancia_id).count() > 0:
            return False
        s.delete(d)
        s.commit()
        return True


# ════════════════════════════════════════════════════════════════════
#  Sesiones (día = un entreno)
# ════════════════════════════════════════════════════════════════════

def get_or_create_sesion_by_date(fecha: date) -> Sesion:
    """Devuelve la sesión del día o crea una nueva."""
    with get_session() as s:
        ses = s.query(Sesion).filter(Sesion.fecha == fecha).first()
        if ses:
            return ses
        ses = Sesion(fecha=fecha)
        s.add(ses)
        s.commit()
        s.refresh(ses)
        return ses


def get_sesion_diaria(sesion_id: int) -> Optional[Sesion]:
    with get_session() as s:
        return (
            s.query(Sesion)
            .options(
                selectinload(Sesion.test_metrics).selectinload(TestMetric.boat),
                selectinload(Sesion.test_metrics).selectinload(TestMetric.distancia),
                selectinload(Sesion.test_metrics).selectinload(TestMetric.tipo),
                selectinload(Sesion.test_metrics).selectinload(TestMetric.categoria),
                selectinload(Sesion.csv_uploads).selectinload(CsvUpload.gps_data),
                selectinload(Sesion.gps_data),
            )
            .filter(Sesion.id == sesion_id)
            .first()
        )


def get_sesion_by_date(fecha: date) -> Optional[Sesion]:
    """Devuelve la sesión cuyo `fecha` coincide con el día exacto."""
    with get_session() as s:
        return s.query(Sesion).filter(Sesion.fecha == fecha).first()


def get_default_selected_day() -> Optional[date]:
    """Día con entrenamientos más cercano a hoy.

    - Si hoy tiene entrenamientos → hoy.
    - Si no → el día más reciente con entrenamientos (≤ hoy).
    - Si no hay ninguno → None.
    """
    today = date.today()
    with get_session() as s:
        today_ses = (
            s.query(Sesion)
            .filter(Sesion.fecha == today, Sesion.num_archivos > 0)
            .first()
        )
        if today_ses:
            return today
        last = (
            s.query(Sesion.fecha)
            .filter(Sesion.num_archivos > 0, Sesion.fecha <= today)
            .order_by(desc(Sesion.fecha))
            .first()
        )
        return last[0] if last else None


# ── App settings (key-value) ──

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_session() as s:
        row = s.query(AppSetting).filter(AppSetting.key == key).first()
        return row.value if row else default


def set_setting(key: str, value: str) -> None:
    with get_session() as s:
        row = s.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = value
            row.updated_at = datetime.now()
        else:
            s.add(AppSetting(key=key, value=value))
        s.commit()


def get_umbral_parado() -> float:
    """Devuelve el umbral (km/h) por debajo del cual un sample se considera parado."""
    try:
        return float(get_setting("umbral_velocidad_parado", "5.0"))
    except (ValueError, TypeError):
        return 5.0


def list_sesiones_diarias(limit: int = 50) -> list[Sesion]:
    with get_session() as s:
        return (
            s.query(Sesion)
            .options(
                selectinload(Sesion.test_metrics),
                selectinload(Sesion.csv_uploads),
            )
            .order_by(desc(Sesion.fecha))
            .limit(limit)
            .all()
        )


def list_sesiones_by_date_range(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> list[Sesion]:
    with get_session() as s:
        q = s.query(Sesion).options(selectinload(Sesion.test_metrics))
        if fecha_desde:
            q = q.filter(Sesion.fecha >= fecha_desde)
        if fecha_hasta:
            q = q.filter(Sesion.fecha <= fecha_hasta)
        return q.order_by(desc(Sesion.fecha)).all()


def update_sesion_diaria(
    sesion_id: int,
    fecha: Optional[date] = None,
    categoria: Optional[str] = None,
    tipo: Optional[str] = None,
) -> Optional[Sesion]:
    with get_session() as s:
        ses = s.query(Sesion).filter(Sesion.id == sesion_id).first()
        if not ses:
            return None
        if fecha is not None:
            ses.fecha = fecha
        if categoria is not None:
            ses.categoria = categoria or None
        if tipo is not None:
            ses.tipo = tipo or None
        s.commit()
        s.refresh(ses)
        return ses


def delete_sesion_diaria(sesion_id: int) -> bool:
    """Borra una sesión: cascade a CSVs, GPS, pruebas, crew, archivos."""
    with get_session() as s:
        ses = s.query(Sesion).filter(Sesion.id == sesion_id).first()
        if not ses:
            return False
        csvs = list(ses.csv_uploads)
        s.delete(ses)
        s.commit()

    for c in csvs:
        if c.file_path and c.kept:
            try:
                os.unlink(c.file_path)
            except OSError:
                pass

    return True


# ════════════════════════════════════════════════════════════════════
#  CSV uploads
# ════════════════════════════════════════════════════════════════════

def crear_csv_upload(
    filename: str,
    file_path: Optional[str],
    sesion_id: int,
    metadata_date: Optional[datetime] = None,
) -> CsvUpload:
    with get_session() as s:
        csv = CsvUpload(
            filename=filename,
            file_path=file_path,
            sesion_id=sesion_id,
            metadata_date=metadata_date,
            kept=True,
        )
        s.add(csv)
        s.commit()
        s.refresh(csv)
        return csv


def get_csv_upload(csv_id: int) -> Optional[CsvUpload]:
    with get_session() as s:
        return (
            s.query(CsvUpload)
            .options(
                selectinload(CsvUpload.sesion),
                selectinload(CsvUpload.gps_data),
                selectinload(CsvUpload.test_metrics),
            )
            .filter(CsvUpload.id == csv_id)
            .first()
        )


def get_csv_upload_by_filename(filename: str) -> Optional[CsvUpload]:
    with get_session() as s:
        return s.query(CsvUpload).filter(CsvUpload.filename == filename).first()


def list_csv_uploads(limit: int = 50) -> list[CsvUpload]:
    with get_session() as s:
        return (
            s.query(CsvUpload)
            .options(
                selectinload(CsvUpload.sesion),
                selectinload(CsvUpload.gps_data),
                selectinload(CsvUpload.test_metrics),
            )
            .order_by(desc(CsvUpload.metadata_date), desc(CsvUpload.uploaded_at))
            .limit(limit)
            .all()
        )


def delete_csv_upload(csv_id: int) -> bool:
    """Borra un CSV: cascade a gps_data (1:1) y test_metrics. Borra archivo si kept."""
    with get_session() as s:
        csv = s.query(CsvUpload).filter(CsvUpload.id == csv_id).first()
        if not csv:
            return False
        sesion_id = csv.sesion_id
        file_path = csv.file_path
        kept = csv.kept
        s.delete(csv)
        s.commit()

    if file_path and kept:
        try:
            os.unlink(file_path)
        except OSError:
            pass

    recalc_sesion_aggregates(sesion_id)
    return True


# ════════════════════════════════════════════════════════════════════
#  GPS data
# ════════════════════════════════════════════════════════════════════

def crear_gps_data(
    csv_upload_id: int,
    sesion_id: int,
    data: dict,
) -> GpsData:
    with get_session() as s:
        existing = (
            s.query(GpsData)
            .filter(GpsData.csv_upload_id == csv_upload_id)
            .first()
        )
        if existing:
            existing.data_json = json.dumps(data, ensure_ascii=False)
            existing.sesion_id = sesion_id
            s.commit()
            s.refresh(existing)
            return existing
        gps = GpsData(
            csv_upload_id=csv_upload_id,
            sesion_id=sesion_id,
            data_json=json.dumps(data, ensure_ascii=False),
        )
        s.add(gps)
        s.commit()
        s.refresh(gps)
        return gps


def get_gps_data_by_csv(csv_upload_id: int) -> Optional[GpsData]:
    with get_session() as s:
        row = s.query(GpsData).filter(GpsData.csv_upload_id == csv_upload_id).first()
        if not row:
            return None
        return row


def get_gps_data(gps_data_id: int) -> Optional[GpsData]:
    with get_session() as s:
        return s.query(GpsData).filter(GpsData.id == gps_data_id).first()


def get_gps_data_for_sesion(sesion_id: int) -> list[GpsData]:
    with get_session() as s:
        return (
            s.query(GpsData)
            .filter(GpsData.sesion_id == sesion_id)
            .order_by(GpsData.created_at)
            .all()
        )


def get_gps_data_for_prueba(test_metric_id: int) -> Optional[GpsData]:
    """Devuelve el GPS de la prueba (via FK directa o via sesion)."""
    with get_session() as s:
        tm = s.query(TestMetric).filter(TestMetric.id == test_metric_id).first()
        if not tm:
            return None
        if tm.gps_data_id:
            return s.query(GpsData).filter(GpsData.id == tm.gps_data_id).first()
        return None


def parse_gps_data_json(gps: GpsData) -> dict:
    return json.loads(gps.data_json)


# ════════════════════════════════════════════════════════════════════
#  Pruebas (TestMetric)
# ════════════════════════════════════════════════════════════════════

def _get_tipo_id(tipo_name: str | None) -> int | None:
    if not tipo_name:
        return None
    with get_session() as s:
        t = s.query(TestType).filter(TestType.name == tipo_name).first()
        return t.id if t else None


def _get_categoria_id(categoria_name: str | None) -> int | None:
    if not categoria_name:
        return None
    with get_session() as s:
        c = s.query(Category).filter(Category.name == categoria_name).first()
        return c.id if c else None


def crear_prueba(
    sesion_id: int,
    csv_upload_id: int,
    gps_data_id: int,
    fecha_hora: datetime,
    test_number: int,
    distancia_metros: int,
    metric: Metricas,
    chart_filename: Optional[str] = None,
    boat_id: Optional[int] = None,
    custom_name: Optional[str] = None,
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    gps_inicio: Optional[dict] = None,
    gps_fin: Optional[dict] = None,
    tiempos_por_distancia: Optional[dict] = None,
    segment_gps_json: Optional[str] = None,
    sectores_detalle: Optional[list] = None,
    paladas_detalle: Optional[list] = None,
) -> TestMetric:
    distancia = get_or_create_distancia(distancia_metros)
    tipo_id = _get_tipo_id(tipo or "entreno")
    categoria_id = _get_categoria_id(categoria)

    tpd_json = None
    if tiempos_por_distancia is not None:
        tpd_json = json.dumps(tiempos_por_distancia, ensure_ascii=False)
    elif metric.tiempos_por_distancia:
        tpd_json = json.dumps(metric.tiempos_por_distancia, ensure_ascii=False)

    sectores_json = (
        json.dumps(sectores_detalle, ensure_ascii=False) if sectores_detalle is not None else None
    )
    paladas_json = (
        json.dumps(paladas_detalle, ensure_ascii=False) if paladas_detalle is not None else None
    )

    with get_session() as s:
        tm = TestMetric(
            sesion_id=sesion_id,
            csv_upload_id=csv_upload_id,
            gps_data_id=gps_data_id,
            fecha_hora=fecha_hora,
            test_number=test_number,
            custom_name=custom_name,
            distancia_id=distancia.id,
            boat_id=boat_id,
            tipo_id=tipo_id,
            categoria_id=categoria_id,
            chart_filename=chart_filename,
            gps_inicio=json.dumps(gps_inicio, ensure_ascii=False) if gps_inicio else None,
            gps_fin=json.dumps(gps_fin, ensure_ascii=False) if gps_fin else None,
            tiempos_por_distancia=tpd_json,
            segment_gps_json=segment_gps_json,
            sectores_detalle=sectores_json,
            paladas_detalle=paladas_json,
            tiempo_total=metric.tiempo_total,
            velocidad_media=metric.velocidad_media,
            velocidad_maxima=metric.velocidad_maxima,
            velocidad_min_post10=metric.velocidad_min_post10,
            aceleracion_max=metric.aceleracion_max,
            tiempo_12kmh=metric.tiempo_12kmh,
            num_paladas=metric.num_paladas,
            dist_media_palada=metric.dist_media_palada,
            dist_std_palada=metric.dist_std_palada,
            dist_max_palada=metric.dist_max_palada,
            dist_min_palada=metric.dist_min_palada,
        )
        s.add(tm)
        s.commit()
        s.refresh(tm)
        return tm


def crear_prueba_manual(
    sesion_id: int,
    distancia_metros: int,
    tiempo_total: float,
    velocidad_media: float,
    custom_name: str | None = None,
    boat_id: int | None = None,
    categoria: str | None = None,
    tipo: str | None = None,
    fecha_hora: datetime | None = None,
    test_number: int | None = None,
) -> TestMetric:
    distancia = get_or_create_distancia(distancia_metros)
    tipo_id = _get_tipo_id(tipo or "entreno")
    categoria_id = _get_categoria_id(categoria)
    with get_session() as s:
        tm = TestMetric(
            sesion_id=sesion_id,
            csv_upload_id=None,
            gps_data_id=None,
            fecha_hora=fecha_hora or datetime.now(),
            test_number=test_number,
            custom_name=custom_name,
            distancia_id=distancia.id,
            boat_id=boat_id,
            tipo_id=tipo_id,
            categoria_id=categoria_id,
            chart_filename=None,
            gps_inicio=None,
            gps_fin=None,
            tiempos_por_distancia=None,
            segment_gps_json=None,
            sectores_detalle=None,
            paladas_detalle=None,
            tiempo_total=tiempo_total,
            velocidad_media=velocidad_media,
            velocidad_maxima=0.0,
            velocidad_min_post10=None,
            aceleracion_max=0.0,
            tiempo_12kmh=None,
            num_paladas=0,
            dist_media_palada=0.0,
            dist_std_palada=0.0,
            dist_max_palada=None,
            dist_min_palada=None,
        )
        s.add(tm)
        s.commit()
        s.refresh(tm)
        return tm


def get_prueba(test_metric_id: int) -> Optional[TestMetric]:
    with get_session() as s:
        return (
            s.query(TestMetric)
            .options(
                selectinload(TestMetric.sesion),
                selectinload(TestMetric.boat),
                selectinload(TestMetric.distancia),
                selectinload(TestMetric.tipo),
                selectinload(TestMetric.categoria),
                selectinload(TestMetric.gps_data),
                selectinload(TestMetric.csv_upload),
                selectinload(TestMetric.crew_assignments).selectinload(
                    CrewAssignment.crew_member
                ),
            )
            .filter(TestMetric.id == test_metric_id)
            .first()
        )


def list_pruebas(limit: int = 50) -> list[TestMetric]:
    with get_session() as s:
        return (
            s.query(TestMetric)
            .options(
                selectinload(TestMetric.boat),
                selectinload(TestMetric.distancia),
                selectinload(TestMetric.sesion),
            )
            .order_by(desc(TestMetric.fecha_hora))
            .limit(limit)
            .all()
        )


def list_pruebas_by_sesion(sesion_id: int) -> list[TestMetric]:
    with get_session() as s:
        return (
            s.query(TestMetric)
            .options(
                selectinload(TestMetric.boat),
                selectinload(TestMetric.distancia),
                selectinload(TestMetric.gps_data),
                selectinload(TestMetric.crew_assignments),
            )
            .filter(TestMetric.sesion_id == sesion_id)
            .order_by(TestMetric.fecha_hora)
            .all()
        )


def list_pruebas_by_csv(csv_upload_id: int) -> list[TestMetric]:
    with get_session() as s:
        return (
            s.query(TestMetric)
            .options(
                selectinload(TestMetric.distancia),
                selectinload(TestMetric.boat),
            )
            .filter(TestMetric.csv_upload_id == csv_upload_id)
            .order_by(TestMetric.fecha_hora)
            .all()
        )


def list_pruebas_by_distance(metros: int, limit: int = 50) -> list[TestMetric]:
    with get_session() as s:
        return (
            s.query(TestMetric)
            .options(
                selectinload(TestMetric.boat),
                selectinload(TestMetric.distancia),
            )
            .join(Distancia, TestMetric.distancia_id == Distancia.id)
            .filter(Distancia.metros == metros)
            .order_by(TestMetric.tiempo_total)
            .limit(limit)
            .all()
        )


def update_prueba(
    test_metric_id: int,
    custom_name: Optional[str] = None,
    categoria: Optional[str] = None,
    boat_id: Optional[int] = None,
    tipo: Optional[str] = None,
    distancia_metros: Optional[int] = None,
    test_number: Optional[int] = None,
) -> Optional[TestMetric]:
    with get_session() as s:
        tm = s.query(TestMetric).filter(TestMetric.id == test_metric_id).first()
        if not tm:
            return None
        if custom_name is not None:
            tm.custom_name = custom_name or None
        if categoria is not None:
            tm.categoria_id = _get_categoria_id(categoria) if categoria else None
        if boat_id is not None:
            tm.boat_id = boat_id or None
        if tipo is not None:
            tm.tipo_id = _get_tipo_id(tipo) if tipo else None
        if distancia_metros is not None:
            d = get_or_create_distancia(distancia_metros)
            tm.distancia_id = d.id
        if test_number is not None:
            tm.test_number = test_number
        s.commit()
        s.refresh(tm)
        return tm


def delete_prueba(test_metric_id: int) -> bool:
    """Borra una prueba: cascade a crew_assignments. Recalcula agregados de la sesión."""
    with get_session() as s:
        tm = s.query(TestMetric).filter(TestMetric.id == test_metric_id).first()
        if not tm:
            return False
        sesion_id = tm.sesion_id
        chart_filename = tm.chart_filename
        s.delete(tm)
        s.commit()

    if chart_filename:
        from pathlib import Path
        charts_dir = settings.resolved_output_dir / "charts"
        for ext in (".html", ".png"):
            p = charts_dir / f"{chart_filename}{ext}"
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        p = settings.resolved_output_dir / f"{chart_filename}.png"
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    recalc_sesion_aggregates(sesion_id)
    return True


def get_distinct_names() -> list[str]:
    with get_session() as s:
        rows = (
            s.query(TestMetric.custom_name)
            .filter(TestMetric.custom_name.isnot(None))
            .filter(TestMetric.custom_name != "")
            .distinct()
            .order_by(TestMetric.custom_name)
            .all()
        )
        return [r[0] for r in rows]


# ════════════════════════════════════════════════════════════════════
#  Recalcular agregados y métricas generales de la sesión
# ════════════════════════════════════════════════════════════════════

THRESHOLD_STOPPED_KMH = 4.0


def recalc_sesion_aggregates(sesion_id: int) -> None:
    """Recalcula num_pruebas, distancia_total_*, num_archivos y métricas generales."""
    with get_session() as s:
        ses = s.query(Sesion).filter(Sesion.id == sesion_id).first()
        if not ses:
            return

        pruebas = (
            s.query(TestMetric)
            .options(selectinload(TestMetric.distancia))
            .filter(TestMetric.sesion_id == sesion_id)
            .all()
        )
        csvs = s.query(CsvUpload).filter(CsvUpload.sesion_id == sesion_id).all()

        pruebas_ordenadas = sorted(pruebas, key=lambda t: t.fecha_hora)
        for i, tm in enumerate(pruebas_ordenadas, start=1):
            tm.test_number = i

        ses.num_pruebas = len(pruebas)
        ses.num_archivos = len(csvs)
        nominal = 0
        for tm in pruebas:
            if tm.distancia:
                nominal += tm.distancia.metros
        ses.distancia_total_nominal = nominal

        compute_sesion_general_metrics_internal(s, ses)
        if not ses.distancia_total_real:
            ses.distancia_total_real = round(float(nominal), 1)
        s.commit()


def compute_sesion_general_metrics(sesion_id: int) -> None:
    with get_session() as s:
        ses = s.query(Sesion).filter(Sesion.id == sesion_id).first()
        if not ses:
            return
        compute_sesion_general_metrics_internal(s, ses)
        s.commit()


def compute_sesion_general_metrics_internal(s, ses: Sesion) -> None:
    """Calcula tiempo_total, tiempo_parado, tiempo_movimiento, vel_media_mov,
    vel_max_dia, ritmo_medio y distancia_total_real a partir de TODOS los
    gps_data de la sesión.

    Cada GpsData tiene su propio `time` que arranca en 0 (ver __main__.py),
    así que las métricas se calculan POR gps y luego se suman — concatenar
    los arrays subestimaba la distancia cuando se subían varios CSVs en el
    mismo día (t_total=max-min daba la duración de UN solo CSV, pero n era
    la suma de samples de todos).
    """
    gps_rows = (
        s.query(GpsData)
        .filter(GpsData.sesion_id == ses.id)
        .order_by(GpsData.created_at)
        .all()
    )
    if not gps_rows:
        ses.tiempo_total_entreno = None
        ses.tiempo_parado = None
        ses.tiempo_movimiento = None
        ses.vel_media_movimiento = None
        ses.vel_max_dia = None
        ses.ritmo_medio = None
        return

    t_total_sum = 0.0
    t_stopped_sum = 0.0
    t_moving_sum = 0.0
    dist_m_sum = 0.0
    max_speed_seen: float | None = None
    any_valid = False

    for g in gps_rows:
        try:
            d = json.loads(g.data_json)
        except (ValueError, TypeError):
            continue
        times = d.get("time", [])
        speeds = d.get("speed", [])
        if not times or not speeds:
            continue
        t_local = max(times) - min(times)
        n_local = len(speeds)
        if t_local <= 0 or n_local <= 0:
            continue
        any_valid = True
        sp_local = t_local / n_local
        n_stopped_local = sum(1 for s_ in speeds if s_ < THRESHOLD_STOPPED_KMH)
        t_stopped_local = n_stopped_local * sp_local
        t_moving_local = max(0.0, t_local - t_stopped_local)
        dist_m_local = sum(speeds) * sp_local / 3600.0 * 1000.0

        t_total_sum += t_local
        t_stopped_sum += t_stopped_local
        t_moving_sum += t_moving_local
        dist_m_sum += dist_m_local
        local_max = max(speeds)
        if max_speed_seen is None or local_max > max_speed_seen:
            max_speed_seen = local_max

    if not any_valid:
        ses.tiempo_total_entreno = None
        ses.tiempo_parado = None
        ses.tiempo_movimiento = None
        ses.vel_media_movimiento = None
        ses.vel_max_dia = None
        ses.ritmo_medio = None
        return

    ses.tiempo_total_entreno = round(t_total_sum, 2)
    ses.tiempo_parado = round(t_stopped_sum, 2)
    ses.tiempo_movimiento = round(t_moving_sum, 2)
    ses.distancia_total_real = round(dist_m_sum, 1)
    ses.vel_media_movimiento = round(
        (dist_m_sum / t_moving_sum) * 3.6 if t_moving_sum > 0 else 0.0, 2
    )
    ses.vel_max_dia = round(max_speed_seen, 2) if max_speed_seen is not None else 0.0
    ses.ritmo_medio = (
        round((t_moving_sum / 60.0) / (dist_m_sum / 1000.0), 2)
        if dist_m_sum > 0 and t_moving_sum > 0
        else None
    )


# ════════════════════════════════════════════════════════════════════
#  Rankings y estadísticas
# ════════════════════════════════════════════════════════════════════

def get_ranking(
    boat_name: Optional[str] = None,
    limit: int = 5,
    distancia: Optional[int] = None,
) -> list[dict]:
    with get_session() as s:
        q = (
            s.query(
                TestMetric.id.label("prueba_id"),
                TestMetric.custom_name,
                TestMetric.fecha_hora,
                TestMetric.categoria_id,
                TestMetric.tiempo_total,
                TestMetric.velocidad_media,
                TestMetric.velocidad_maxima,
                TestMetric.num_paladas,
                TestMetric.dist_media_palada,
                Distancia.metros.label("distancia"),
                Boat.name.label("boat_name"),
                Sesion.fecha,
            )
            .join(Distancia, TestMetric.distancia_id == Distancia.id)
            .join(Sesion, TestMetric.sesion_id == Sesion.id)
            .outerjoin(Boat, TestMetric.boat_id == Boat.id)
        )
        if boat_name:
            q = q.filter(Boat.name == boat_name)
        if distancia is not None:
            q = q.filter(Distancia.metros == distancia)
        q = q.order_by(TestMetric.tiempo_total).limit(limit)
        out = []
        for r in q.all():
            cat_name = None
            if r.categoria_id:
                cat = s.query(Category).filter(Category.id == r.categoria_id).first()
                cat_name = cat.name if cat else None
            out.append({
                "prueba_id": r.prueba_id,
                "tiempo_total": r.tiempo_total,
                "tiempo_total_formatted": format_duration(r.tiempo_total),
                "velocidad_media": r.velocidad_media,
                "velocidad_maxima": r.velocidad_maxima,
                "num_paladas": r.num_paladas,
                "dist_media_palada": r.dist_media_palada,
                "custom_name": r.custom_name,
                "categoria": cat_name,
                "distancia": r.distancia,
                "boat_name": r.boat_name,
                "fecha": r.fecha_hora,
            })
        return out


def get_boat_stats() -> list[dict]:
    with get_session() as s:
        results = (
            s.query(
                Boat.id.label("boat_id"),
                Boat.name,
                Boat.display_name,
                func.count(TestMetric.id).label("num_tests"),
                func.min(TestMetric.tiempo_total).label("best_tiempo"),
                func.avg(TestMetric.dist_media_palada).label("avg_dist_palada"),
            )
            .join(TestMetric, TestMetric.boat_id == Boat.id)
            .group_by(Boat.id, Boat.name, Boat.display_name)
            .all()
        )

        best_metrics = _get_boat_best_metrics(s)
        return [
            {
                "name": r.name,
                "display_name": r.display_name,
                "num_tests": r.num_tests,
                "best_tiempo": round(r.best_tiempo, 2) if r.best_tiempo else 0,
                "avg_dist_palada": round(r.avg_dist_palada, 2) if r.avg_dist_palada else 0,
                "best_tiempo_paladas": best_metrics.get(r.boat_id, {}).get("paladas"),
                "best_tiempo_vel_max": best_metrics.get(r.boat_id, {}).get("vel_max"),
                "best_tiempo_t12": best_metrics.get(r.boat_id, {}).get("t12"),
            }
            for r in results
        ]


def _get_boat_best_metrics(s) -> dict[int, dict]:
    rows = (
        s.query(
            TestMetric.boat_id,
            TestMetric.num_paladas,
            TestMetric.velocidad_maxima,
            TestMetric.tiempo_12kmh,
            TestMetric.tiempo_total,
        )
        .filter(TestMetric.boat_id.isnot(None))
        .order_by(TestMetric.boat_id, TestMetric.tiempo_total)
        .all()
    )
    out: dict[int, dict] = {}
    for boat_id, paladas, vel_max, t12, _t in rows:
        if boat_id not in out:
            out[boat_id] = {"paladas": paladas, "vel_max": vel_max, "t12": t12}
    return out


PAGE_FIRST = 5
PAGE_REST = 10


def get_recent_uploads(page: int = 1) -> dict:
    """Return uploads grouped by session, ordered by latest upload date.

    Page 1 returns ``PAGE_FIRST`` items; subsequent pages ``PAGE_REST``.
    """
    from math import ceil

    per_page = PAGE_FIRST if page == 1 else PAGE_REST

    with get_session() as s:
        total = s.query(Sesion).filter(Sesion.num_archivos > 0).count()
        offset = (page - 1) * PAGE_FIRST if page == 1 else PAGE_FIRST + (page - 2) * PAGE_REST
        sesiones = (
            s.query(Sesion)
            .options(
                selectinload(Sesion.csv_uploads),
                selectinload(Sesion.test_metrics).selectinload(TestMetric.distancia),
            )
            .filter(Sesion.num_archivos > 0)
            .order_by(desc(Sesion.fecha))
            .offset(offset)
            .limit(per_page)
            .all()
        )

        upload_list: list[dict] = []
        for ses in sesiones:
            conteo: dict[int, int] = {d: 0 for d in settings.distancias_validas}
            first_prueba = None
            for tm in ses.test_metrics:
                metros = tm.distancia.metros if tm.distancia else 200
                if metros in conteo:
                    conteo[metros] += 1
                if first_prueba is None or tm.test_number and (
                    first_prueba.test_number or 9999
                ) > (tm.test_number or 9999):
                    first_prueba = tm

            first_csv = ses.csv_uploads[0] if ses.csv_uploads else None
            if first_csv and first_csv.filename:
                report_base = first_csv.filename.rsplit(".", 1)[0]
            elif ses.fecha:
                report_base = ses.fecha.isoformat()
            else:
                report_base = f"sesion-{ses.id}"
            report_filename = f"Informe_{report_base}.txt"
            report_path = settings.resolved_output_dir / report_filename
            upload_list.append({
                "id": ses.id,
                "filename": ses.csv_uploads[0].filename if ses.csv_uploads else f"sesion_{ses.id}.csv",
                "fecha_datos": ses.fecha,
                "num_pruebas": ses.num_pruebas,
                "num_archivos": ses.num_archivos,
                "conteo_distancias": conteo,
                "first_sesion_id": first_prueba.id if first_prueba else None,
                "report_filename": report_filename,
                "report_exists": report_path.is_file(),
                "csv_uploads": [
                    {
                        "id": c.id,
                        "filename": c.filename,
                        "uploaded_at": c.uploaded_at,
                        "metadata_date": c.metadata_date,
                    }
                    for c in ses.csv_uploads
                ],
            })

        if total <= PAGE_FIRST:
            total_pages = 1
        else:
            total_pages = 1 + ceil((total - PAGE_FIRST) / PAGE_REST)

        return {
            "uploads": upload_list,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        }


# ════════════════════════════════════════════════════════════════════
#  Calendario y filtros
# ════════════════════════════════════════════════════════════════════

def get_dias_con_entrenamientos(year: int, month: int) -> list[int]:
    from sqlalchemy import cast, Integer
    with get_session() as s:
        results = (
            s.query(
                cast(func.strftime("%d", Sesion.fecha), Integer).label("dia")
            )
            .filter(
                cast(func.strftime("%Y", Sesion.fecha), Integer) == year,
                cast(func.strftime("%m", Sesion.fecha), Integer) == month,
                Sesion.num_archivos > 0,
            )
            .distinct()
            .order_by("dia")
            .all()
        )
        return [r.dia for r in results]


def get_dias_con_competicion(year: int, month: int) -> list[int]:
    from sqlalchemy import cast, Integer
    with get_session() as s:
        results = (
            s.query(
                cast(func.strftime("%d", Sesion.fecha), Integer).label("dia")
            )
            .filter(
                cast(func.strftime("%Y", Sesion.fecha), Integer) == year,
                cast(func.strftime("%m", Sesion.fecha), Integer) == month,
                Sesion.tipo == "competicion",
            )
            .distinct()
            .order_by("dia")
            .all()
        )
        return [r.dia for r in results]


# ════════════════════════════════════════════════════════════════════
#  Tripulación (sin cambios)
# ════════════════════════════════════════════════════════════════════

def list_crew() -> list[CrewMember]:
    with get_session() as s:
        return s.query(CrewMember).order_by(CrewMember.nombre, CrewMember.apellido).all()


def list_crew_by_frequency() -> list[dict]:
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
            cm.categoria = categoria or None
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


def get_assignments(test_metric_id: int) -> list[CrewAssignment]:
    with get_session() as s:
        return (
            s.query(CrewAssignment)
            .options(selectinload(CrewAssignment.crew_member))
            .filter(CrewAssignment.test_metric_id == test_metric_id)
            .all()
        )


def save_assignments(test_metric_id: int, assignments: list[dict]) -> None:
    with get_session() as s:
        s.query(CrewAssignment).filter(
            CrewAssignment.test_metric_id == test_metric_id
        ).delete()
        for a in assignments:
            s.add(CrewAssignment(
                test_metric_id=test_metric_id,
                crew_member_id=a["crew_member_id"],
                role=a["role"],
                side=a.get("side"),
                row_number=a.get("row_number"),
            ))
        s.commit()


# ════════════════════════════════════════════════════════════════════
#  Catálogo: Categorías y tipos
# ════════════════════════════════════════════════════════════════════

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


def list_test_types() -> list[TestType]:
    with get_session() as s:
        return s.query(TestType).order_by(TestType.name).all()


def get_test_type(type_id: int) -> Optional[TestType]:
    with get_session() as s:
        return s.query(TestType).filter(TestType.id == type_id).first()


def get_test_type_by_name(name: str) -> Optional[TestType]:
    with get_session() as s:
        return s.query(TestType).filter(TestType.name == name).first()


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
