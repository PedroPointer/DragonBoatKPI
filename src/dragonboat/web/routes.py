"""Web routes — home, registros, informes, config."""

from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from dragonboat.analysis import (
    analizar_tramo,
    build_gps_data_json,
    build_gps_inicio_fin,
    calcular_sectores,
    cargar_csv,
    classify_gps_segments,
    detectar_tramos,
    detectar_paladas,
    extraer_metadata_date,
    format_duration,
    format_duration_short,
    generar_informe_str,
    generar_resumen_sesion,
    get_trajectory,
    imprimir_metricas,
    nombre_base,
    resumen_paladas,
)
from dragonboat.config import settings
from dragonboat.db_models import Boat, Sesion
from dragonboat.database import get_session as db_session
from dragonboat.models import Metricas
from dragonboat.repo import (
    crear_csv_upload,
    crear_distancia,
    crear_gps_data,
    crear_prueba,
    crear_prueba_manual,
    delete_csv_upload,
    delete_distancia,
    delete_prueba,
    delete_sesion_diaria,
    get_assignments,
    get_boat_stats,
    get_csv_upload,
    get_csv_upload_by_filename,
    get_default_selected_day,
    get_dias_con_competicion,
    get_dias_con_entrenamientos,
    get_distancia,
    get_distinct_names,
    get_gps_data_for_sesion,
    get_or_create_sesion_by_date,
    get_prueba,
    get_ranking,
    get_recent_uploads,
    get_sesion_by_date,
    get_sesion_diaria,
    get_setting,
    get_umbral_parado,
    list_categories,
    list_csv_uploads,
    list_distancias,
    list_pruebas,
    list_pruebas_by_csv,
    list_pruebas_by_sesion,
    list_sesiones_diarias,
    list_test_types,
    recalc_sesion_aggregates,
    set_setting,
    update_distancia,
    update_prueba,
    update_sesion_diaria,
)
from dragonboat.visualization.charts import graficar_200m
from dragonboat.analysis.metrics import calcular_pitch

router = APIRouter()

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


def _register_jinja_filters() -> None:
    def from_json(value):
        if not value:
            return {}
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}

    def fmt_decimal(value, decimals: int = 2):
        if value is None:
            return "-"
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)

    def fmt_comma_es(value, decimals: int = 2):
        if value is None:
            return "—"
        try:
            return f"{float(value):.{decimals}f}".replace(".", ",")
        except (ValueError, TypeError):
            return str(value)

    templates.env.filters["from_json"] = from_json
    templates.env.filters["duration"] = format_duration
    templates.env.filters["duration_short"] = format_duration_short
    templates.env.filters["comma"] = fmt_decimal
    templates.env.filters["comma_es"] = fmt_comma_es


_register_jinja_filters()


CATEGORIAS = [
    "Open Sénior", "Open Veterano",
    "Femenino Sénior", "Femenino Veterano",
    "Mixto Sénior", "Mixto Veterano",
    "ACS", "PD1", "PD2", "PD3",
]


def _parse_tiempo(s: str) -> float:
    s = s.strip()
    if not s:
        raise ValueError("tiempo vacío")
    s = s.replace(",", ".")
    parts = s.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(s)


def _default_boat_id() -> int | None:
    with db_session() as s:
        boat = s.query(Boat).filter(Boat.name == "DB12").first()
        return boat.id if boat else None


# ── Home ──

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    rankings = {
        d: get_ranking(distancia=d, limit=5)
        for d in settings.distancias_validas
    }
    sesiones = list_sesiones_diarias(50)

    incomplete = []
    for ses in sesiones:
        warns = []
        pruebas = list_pruebas_by_sesion(ses.id)
        # Aggregate over all pruebas of the day
        total_palistas = 0
        has_timonel = False
        for prueba in pruebas:
            assigned = sum(1 for a in prueba.crew_assignments if a.role == "remero")
            total_palistas += assigned
            if any(a.role == "timonel" for a in prueba.crew_assignments):
                has_timonel = True
        if total_palistas == 0:
            warns.append({"type": "crew", "label": "falta asignar tripulación"})
        if not has_timonel and pruebas:
            warns.append({"type": "timonel", "label": "falta timonel"})
        if warns:
            incomplete.append({"sesion": ses, "warnings": warns})

    return templates.TemplateResponse(
        name="home.html",
        request=request,
        context={
            "rankings": rankings,
            "distancias_validas": settings.distancias_validas,
            "incomplete": incomplete,
            "active_nav": "home",
        },
    )


# ── Registros (calendario + detalles del día seleccionado) ──

@router.get("/registros", response_class=HTMLResponse)
async def registros_list(
    request: Request,
    dia: int = None,
    mes: int = None,
    anio: int = None,
    tipo: str = None,
    barco: str = None,
):
    # 1. Determinar día seleccionado
    if dia and mes and anio:
        try:
            selected_date: date | None = date(anio, mes, dia)
        except ValueError:
            selected_date = get_default_selected_day()
    else:
        selected_date = get_default_selected_day()

    # 2. Cargar sesión del día seleccionado
    sesion = None
    pruebas: list = []
    csv_uploads: list = []
    gps_segments_json = "[]"
    test_segments_json = "[]"

    if selected_date:
        base_sesion = get_sesion_by_date(selected_date)
        if base_sesion:
            sesion = get_sesion_diaria(base_sesion.id)
            if sesion:
                pruebas = list_pruebas_by_sesion(sesion.id)
                csv_uploads = list(sesion.csv_uploads)
                threshold = get_umbral_parado()
                all_segments: list = []
                for gps in get_gps_data_for_sesion(sesion.id):
                    try:
                        data = json.loads(gps.data_json)
                    except (ValueError, TypeError):
                        continue
                    all_segments.extend(classify_gps_segments(data, threshold=threshold))
                gps_segments_json = json.dumps(all_segments)

                # ── Build test GPS segments (colored by distance) ──
                test_segments = []
                for p in pruebas:
                    if not p.gps_inicio or not p.gps_fin or not p.segment_gps_json:
                        continue
                    try:
                        seg_data = json.loads(p.segment_gps_json)
                    except (ValueError, TypeError):
                        continue
                    lats = seg_data.get("lat", [])
                    lons = seg_data.get("lon", [])
                    if not lats or not lons:
                        continue
                    step = 5
                    points = [
                        [lats[i], lons[i]]
                        for i in range(0, len(lats), step)
                        if lats[i] is not None and lons[i] is not None
                    ]
                    if len(points) < 2:
                        continue
                    dist = p.distancia.metros if p.distancia else 0
                    if dist == 200:
                        color = "#3b82f6"
                    elif dist == 500:
                        color = "#eab308"
                    elif dist == 1000:
                        color = "#f97316"
                    else:
                        color = "#3b82f6"
                    test_segments.append({
                        "points": points,
                        "color": color,
                        "id": p.id,
                        "name": p.custom_name or f"Test #{p.test_number}",
                        "distance": dist,
                    })
                test_segments_json = json.dumps(test_segments)

    with db_session() as s:
        boats = s.query(Boat).all()

    tipos = list_test_types()
    categories = list_categories()
    names = get_distinct_names()

    return templates.TemplateResponse(
        name="registros.html",
        request=request,
        context={
            "selected_date": selected_date,
            "sesion": sesion,
            "pruebas": pruebas,
            "csv_uploads": csv_uploads,
            "gps_segments_json": gps_segments_json,
            "test_segments_json": test_segments_json,
            "boats": boats,
            "categorias": [c.name for c in categories],
            "tipos": tipos,
            "names": names,
            "distancias_validas": settings.distancias_validas,
            "filter_tipo": tipo or "",
            "filter_barco": barco or "",
            "umbral": get_umbral_parado(),
            "active_nav": "registros",
        },
    )


@router.get("/registros/dias")
async def registros_dias(year: int = None, month: int = None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    dias = get_dias_con_entrenamientos(year, month)
    dias_competicion = get_dias_con_competicion(year, month)
    return JSONResponse({"dias": dias, "dias_competicion": dias_competicion})


# ── /sesion/{id} → redirect a /registros con el día ──

@router.get("/sesion/{sesion_id}")
async def sesion_detail_redirect(sesion_id: int):
    sesion = get_sesion_diaria(sesion_id)
    if not sesion or not sesion.fecha:
        return RedirectResponse(url="/registros", status_code=302)
    f = sesion.fecha
    return RedirectResponse(
        url=f"/registros?dia={f.day}&mes={f.month}&anio={f.year}",
        status_code=302,
    )


@router.post("/sesion/{sesion_id}/delete")
async def sesion_delete(sesion_id: int):
    delete_sesion_diaria(sesion_id)
    return RedirectResponse(url="/registros", status_code=302)


@router.post("/sesion/{sesion_id}/recalcular")
async def sesion_recalcular(sesion_id: int):
    recalc_sesion_aggregates(sesion_id)
    sesion = get_sesion_diaria(sesion_id)
    if sesion and sesion.fecha:
        f = sesion.fecha
        return RedirectResponse(
            url=f"/registros?dia={f.day}&mes={f.month}&anio={f.year}",
            status_code=302,
        )
    return RedirectResponse(url="/registros", status_code=302)


@router.post("/sesion/{sesion_id}")
async def sesion_update(
    request: Request,
    sesion_id: int,
    categoria: str = Form(None),
    tipo: str = Form(None),
):
    update_sesion_diaria(
        sesion_id,
        categoria=categoria or None,
        tipo=tipo or None,
    )
    sesion = get_sesion_diaria(sesion_id)
    if sesion and sesion.fecha:
        f = sesion.fecha
        return RedirectResponse(
            url=f"/registros?dia={f.day}&mes={f.month}&anio={f.year}",
            status_code=302,
        )
    return RedirectResponse(url="/registros", status_code=302)


# ── Registrar prueba manual ──

@router.post("/registros/new")
async def registro_nuevo(
    request: Request,
    custom_name: str = Form(""),
    fecha: str = Form(""),
    distancia: int = Form(...),
    boat_id: int = Form(None),
    tiempo: str = Form(...),
    categoria: str = Form(""),
    tipo: str = Form(""),
):
    try:
        tiempo_s = _parse_tiempo(tiempo)
    except (ValueError, TypeError):
        return RedirectResponse(url="/registros?error=Tiempo+inv%C3%A1lido", status_code=302)
    if tiempo_s <= 0:
        return RedirectResponse(url="/registros?error=El+tiempo+debe+ser+mayor+a+cero", status_code=302)

    velocidad_media = distancia / tiempo_s * 3.6

    fecha_hora = datetime.now()
    if fecha:
        try:
            fecha_hora = datetime.fromisoformat(fecha)
        except ValueError:
            pass

    sesion = get_or_create_sesion_by_date(fecha_hora.date())
    next_num = sesion.num_pruebas + 1

    crear_prueba_manual(
        sesion_id=sesion.id,
        distancia_metros=distancia,
        tiempo_total=tiempo_s,
        velocidad_media=velocidad_media,
        custom_name=custom_name.strip() or None,
        boat_id=boat_id if boat_id and boat_id > 0 else None,
        categoria=categoria.strip() or None,
        tipo=tipo.strip() or None,
        fecha_hora=fecha_hora,
        test_number=next_num,
    )
    recalc_sesion_aggregates(sesion.id)
    return RedirectResponse(url="/registros", status_code=302)


@router.post("/test/{prueba_id}/delete")
async def prueba_delete(prueba_id: int):
    delete_prueba(prueba_id)
    return RedirectResponse(url="/registros", status_code=302)


# ── Detalle de prueba ──

@router.get("/test/{prueba_id}", response_class=HTMLResponse)
async def test_page(request: Request, prueba_id: int):
    from dragonboat.repo import list_crew_by_frequency

    prueba = get_prueba(prueba_id)
    if not prueba:
        return RedirectResponse(url="/registros", status_code=302)

    chart_available = bool(
        prueba.chart_filename
        and (settings.resolved_output_dir / f"{prueba.chart_filename}.png").exists()
    )

    with db_session() as s:
        boats = s.query(Boat).all()

    names = get_distinct_names()
    tipos = list_test_types()
    categorias = list_categories()

    boat = prueba.boat
    if not boat:
        with db_session() as s:
            boat = s.query(Boat).filter(Boat.name == "DB12").first()

    crew_list = list_crew_by_frequency()
    crew_json = json.dumps([
        {"id": cm["id"], "nombre": cm["nombre"], "apellido": cm["apellido"],
         "categoria": cm["categoria"], "photo_path": cm["photo_path"], "freq": cm["freq"]}
        for cm in crew_list
    ])

    raw_assignments = get_assignments(prueba_id)
    assignments_json = json.dumps([
        {"crew_member_id": a.crew_member_id, "role": a.role,
         "side": a.side, "row_number": a.row_number}
        for a in raw_assignments
    ])

    has_gps = bool(prueba.segment_gps_json or prueba.gps_data_id)

    sectores: list[dict] = []
    if prueba.sectores_detalle:
        try:
            sectores = json.loads(prueba.sectores_detalle)
        except (ValueError, TypeError):
            sectores = []
    if not sectores and prueba.tiempos_por_distancia and prueba.distancia:
        try:
            tpd = json.loads(prueba.tiempos_por_distancia)
            sectores = calcular_sectores(tpd, prueba.distancia.metros)
        except (ValueError, TypeError):
            sectores = []

    paladas_detalle: list[float] = []
    if prueba.paladas_detalle:
        try:
            paladas_detalle = json.loads(prueba.paladas_detalle)
        except (ValueError, TypeError):
            paladas_detalle = []
    paladas_resumen = resumen_paladas(paladas_detalle)

    return templates.TemplateResponse(
        name="test.html",
        request=request,
        context={
            "test": prueba,
            "chart_available": chart_available,
            "has_gps": has_gps,
            "boat": boat,
            "boats": boats,
            "names": names,
            "categorias": [c.name for c in categorias],
            "tipos": tipos,
            "crew_json": crew_json,
            "assignments_json": assignments_json,
            "sectores": sectores,
            "paladas_resumen": paladas_resumen,
            "active_nav": "registros",
        },
    )


@router.post("/test/{prueba_id}")
async def test_update(
    request: Request,
    prueba_id: int,
    custom_name: str = Form(None),
    categoria: str = Form(None),
    boat_id: int = Form(None),
    tipo: str = Form(None),
    distancia: int = Form(None),
):
    update_prueba(
        prueba_id,
        custom_name=custom_name.strip() if custom_name else None,
        categoria=categoria or None,
        boat_id=boat_id,
        tipo=tipo or None,
        distancia_metros=distancia,
    )
    return RedirectResponse(url=f"/test/{prueba_id}", status_code=302)


@router.get("/test/{prueba_id}/trajectory")
async def test_trajectory(prueba_id: int):
    prueba = get_prueba(prueba_id)
    if not prueba:
        return JSONResponse({"points": [], "center": None})
    gps_json = None
    if prueba.segment_gps_json:
        gps_json = prueba.segment_gps_json
    elif prueba.gps_data:
        gps_json = prueba.gps_data.data_json
    if not gps_json:
        return JSONResponse({"points": [], "center": None})
    points = get_trajectory(gps_json)
    if not points:
        return JSONResponse({"points": [], "center": None})
    center = [
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    ]
    gps_inicio = None
    gps_fin = None
    if prueba.gps_inicio:
        try:
            gi = json.loads(prueba.gps_inicio)
            gps_inicio = {"lat": gi.get("lat"), "lon": gi.get("lon")}
        except (ValueError, TypeError):
            pass
    if prueba.gps_fin:
        try:
            gf = json.loads(prueba.gps_fin)
            gps_fin = {"lat": gf.get("lat"), "lon": gf.get("lon")}
        except (ValueError, TypeError):
            pass
    return JSONResponse({
        "points": points,
        "center": center,
        "gps_inicio": gps_inicio,
        "gps_fin": gps_fin,
    })


@router.get("/test/{prueba_id}/chart-data")
async def test_chart_data(prueba_id: int):
    """JSON para la gráfica ECharts interactiva (web /test/{id}).

    Devuelve series 25Hz desde ``start_t - 2s`` (vía ``gps_data.data_json``) +
    eventos del ``segment_gps_json`` (picos, valles, dist/palada) + marcadores
    y métricas de la prueba.
    """
    prueba = get_prueba(prueba_id)
    if not prueba:
        return JSONResponse({"error": "not found"}, status_code=404)
    if not prueba.segment_gps_json:
        return JSONResponse({"error": "no segment data"}, status_code=404)

    try:
        segment = json.loads(prueba.segment_gps_json)
    except (ValueError, TypeError):
        return JSONResponse({"error": "corrupt segment data"}, status_code=404)

    seg_speed = segment.get("speed", [])
    seg_time = segment.get("time", [])
    if not seg_speed or not seg_time:
        return JSONResponse({"error": "empty series"}, status_code=404)

    full_time: list[float] = []
    full_speed: list[float] = []
    full_lean: list[float] = []
    full_gx: list[float] = []
    full_gz: list[float] = []

    if prueba.gps_data and prueba.gps_data.data_json:
        try:
            full = json.loads(prueba.gps_data.data_json)
            full_time = full.get("time", []) or []
            full_speed = full.get("speed", []) or []
            full_lean = full.get("lean", []) or []
            full_gx = full.get("gforce_x", []) or []
            full_gz = full.get("gforce_z", []) or []
        except (ValueError, TypeError):
            pass

    seg_start_t = float(seg_time[0])
    seg_end_t = float(seg_time[-1])
    t_offset: float = 0.0
    series_lo = 0
    series_hi = len(full_time)

    if full_time and full_speed:
        target = float(seg_speed[0])
        idx = -1
        for i in range(len(full_speed)):
            if full_speed[i] == target:
                if i + len(seg_speed) <= len(full_speed) and all(
                    full_speed[i + k] == seg_speed[k] for k in range(min(5, len(seg_speed)))
                ):
                    idx = i
                    break
        if idx >= 0:
            t_offset = float(full_time[idx]) - seg_start_t
            pre_start_abs = t_offset - 2.0
            series_lo = 0
            for j in range(idx, -1, -1):
                if float(full_time[j]) <= pre_start_abs:
                    series_lo = j
                    break
            series_hi = idx + len(seg_time)

    if series_hi > len(full_time):
        series_hi = len(full_time)
    if series_lo < 0:
        series_lo = 0

    if full_time and full_speed and full_lean and full_gx and full_gz:
        rel_t = [float(full_time[k]) - t_offset for k in range(series_lo, series_hi)]
        spd = [float(full_speed[k]) for k in range(series_lo, series_hi)]
        ln = [float(full_lean[k]) for k in range(series_lo, series_hi)]
        gx = [float(full_gx[k]) for k in range(series_lo, series_hi)]
        gz = [float(full_gz[k]) for k in range(series_lo, series_hi)]
        pitch_vals = calcular_pitch(gx, gz).tolist()
    else:
        rel_t = list(seg_time)
        spd = list(seg_speed)
        ln = list(segment.get("lean", []))
        gx = list(segment.get("gforce_x", []))
        gz = list(segment.get("gforce_z", []))
        if gx and gz:
            pitch_vals = calcular_pitch(gx, gz).tolist()
        else:
            pitch_vals = [0.0] * len(rel_t)

    tpd: dict[str, float] = {}
    if prueba.tiempos_por_distancia:
        try:
            tpd = json.loads(prueba.tiempos_por_distancia)
        except (ValueError, TypeError):
            tpd = {}

    t0 = float(rel_t[0]) if rel_t else 0.0
    tN = float(rel_t[-1]) if rel_t else 0.0

    return JSONResponse({
        "time": rel_t,
        "speed": spd,
        "lean": ln,
        "pitch": pitch_vals,
        "time_start": t0,
        "time_end": tN,
        "tiempo_total": prueba.tiempo_total,
        "velocidad_media": prueba.velocidad_media,
        "velocidad_maxima": prueba.velocidad_maxima,
        "tiempo_12kmh": prueba.tiempo_12kmh,
        "peak_times": segment.get("peak_times", []),
        "peak_speeds": segment.get("peak_speeds", []),
        "valley_times": segment.get("valley_times", []),
        "dist_por_palada": segment.get("dist_por_palada", []),
        "tiempos_por_distancia": tpd,
        "dist_media_palada": prueba.dist_media_palada,
        "num_paladas": prueba.num_paladas,
    })


@router.get("/test/{prueba_id}/chart.png")
async def test_chart_png(prueba_id: int):
    prueba = get_prueba(prueba_id)
    if not prueba or not prueba.chart_filename:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = settings.resolved_output_dir / f"{prueba.chart_filename}.png"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(
        path,
        filename=f"prueba_{prueba_id}_{prueba.chart_filename}.png",
        media_type="image/png",
    )


# ── Informes ──

@router.get("/informes", response_class=HTMLResponse)
async def informes_page(request: Request, pagina: int = 1):
    page_data = get_recent_uploads(page=pagina)
    return templates.TemplateResponse(
        name="informes.html",
        request=request,
        context={
            "active_nav": "informes",
            "distancias_validas": settings.distancias_validas,
            "recent_uploads": page_data["uploads"],
            "page": page_data["page"],
            "total_pages": page_data["total_pages"],
            "total": page_data["total"],
        },
    )


@router.post("/informes/check-duplicates")
async def check_duplicates(request: Request):
    body = await request.json()
    filenames: list[str] = body.get("filenames", [])
    if not filenames:
        return JSONResponse({"ok": True, "duplicates": []})
    duplicates = [f for f in filenames if f and get_csv_upload_by_filename(f) is not None]
    return JSONResponse({"ok": True, "duplicates": duplicates})


@router.post("/informes/eliminar-upload/{sesion_id}")
async def eliminar_upload(sesion_id: int):
    with db_session() as s:
        ses = s.query(Sesion).filter(Sesion.id == sesion_id).first()
        if not ses:
            return JSONResponse({"error": "No se encontró la sesión"}, status_code=404)
        csv_ids = [c.id for c in list(ses.csv_uploads)]

    for cid in csv_ids:
        delete_csv_upload(cid)

    return JSONResponse({"ok": True})


def _process_single_csv(content: bytes, filename: str, overwrite: bool) -> dict:
    """Process a single CSV upload and return a resumen dict for the template.

    Never raises: errors are captured into the returned dict under ``estado``.
    """
    resumen: dict = {
        "csv_filename": filename,
        "estado": "ok",
        "conteo_distancias": {d: 0 for d in settings.distancias_validas},
        "total_pruebas": 0,
        "first_prueba_id": None,
        "report_filename": None,
        "sesion_id": None,
        "mensaje": None,
    }

    existing = get_csv_upload_by_filename(filename)
    if existing and not overwrite:
        resumen["estado"] = "duplicado"
        resumen["mensaje"] = "El archivo ya está registrado. Subilo otra vez con 'Reemplazar' para sobrescribirlo."
        return resumen
    if existing and overwrite:
        try:
            delete_csv_upload(existing.id)
        except Exception as exc:  # noqa: BLE001
            resumen["estado"] = "error"
            resumen["mensaje"] = f"No se pudo reemplazar el archivo previo: {exc}"
            return resumen

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = cargar_csv(tmp_path)
    except Exception as exc:  # noqa: BLE001
        resumen["estado"] = "error"
        resumen["mensaje"] = f"Error al leer el CSV: {exc}"
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return resumen

    try:
        metadata_date = extraer_metadata_date(tmp_path)
        if metadata_date is None:
            try:
                metadata_date = df["Time"].iloc[0].to_pydatetime()
            except Exception:
                metadata_date = datetime.now()

        tramos = detectar_tramos(df)
        if not tramos and df.empty:
            resumen["estado"] = "error"
            resumen["mensaje"] = "CSV vacío o no se pudo leer"
            return resumen

        sesion = get_or_create_sesion_by_date(metadata_date.date())

        input_dir = settings.resolved_input_dir
        input_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(input_dir / filename)
        (input_dir / filename).write_bytes(content)

        csv_upload = crear_csv_upload(
            filename=filename,
            file_path=file_path,
            sesion_id=sesion.id,
            metadata_date=metadata_date,
        )

        full_gps = {
            "time": [float(t) for t in (df["elapsed_time"].values - df["elapsed_time"].iloc[0])],
            "speed": [float(s) for s in df["speed_kmh"].values],
            "lat": [float(v) if pd.notna(v) else None for v in df["lat"].values],
            "lon": [float(v) if pd.notna(v) else None for v in df["lon"].values],
            "lean": [float(v) if pd.notna(v) else 0.0 for v in df["lean_angle"].values],
            "gforce_x": [float(v) if pd.notna(v) else 0.0 for v in df["gforce_x"].values],
            "gforce_z": [float(v) if pd.notna(v) else 0.0 for v in df["gforce_z"].values],
        }
        gps_data = crear_gps_data(
            csv_upload_id=csv_upload.id,
            sesion_id=sesion.id,
            data=full_gps,
        )

        default_boat_id = _default_boat_id()
        first_prueba_id = None
        pruebas_info: list[tuple] = []
        idx_valido = 0

        for tramo in tramos:
            paladas_info = detectar_paladas(df, tramo.start_idx, tramo.end_idx)
            m = analizar_tramo(
                df, tramo.start_idx, tramo.end_idx, paladas_info, distancia=tramo.distancia
            )
            if m is None:
                continue
            t11 = m.tiempo_11kmh if m.tiempo_11kmh is not None else 99
            limite = settings.limite_tiempo_max.get(tramo.distancia, 1500.0)
            media_check = (tramo.distancia == 2000) or (m.velocidad_media > 9.0)
            if not (m.tiempo_total < limite and t11 < 20.0 and media_check):
                continue

            m.calm_start = tramo.calm_start
            m.calm_end = tramo.calm_end
            idx_valido += 1

            if paladas_info.dist_por_palada and len(paladas_info.dist_por_palada) > 15:
                after_15 = paladas_info.dist_por_palada[15:]
                m.dist_max_palada = max(after_15)
                m.dist_min_palada = min(after_15)

            start_dt = df["Time"].iloc[tramo.start_idx] + pd.Timedelta(hours=2)
            nb = nombre_base(m, idx_valido, start_dt)
            imprimir_metricas(m, filename, idx_valido)

            segment_gps = build_gps_data_json(df, tramo.start_idx, tramo.end_idx, paladas_info, m)
            segment_gps_json = json.dumps(segment_gps, ensure_ascii=False)

            gps_inicio, gps_fin = build_gps_inicio_fin(
                df, tramo.start_idx, tramo.end_idx, time_offset=m.start_time
            )

            try:
                graficar_200m(df, m, paladas_info, settings.resolved_output_dir, nb)
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] No se pudo generar PNG chart: {exc}")

            prueba = crear_prueba(
                sesion_id=sesion.id,
                csv_upload_id=csv_upload.id,
                gps_data_id=gps_data.id,
                fecha_hora=start_dt,
                test_number=idx_valido,
                distancia_metros=tramo.distancia,
                metric=m,
                chart_filename=nb,
                boat_id=default_boat_id,
                tipo="entreno",
                gps_inicio=gps_inicio,
                gps_fin=gps_fin,
                tiempos_por_distancia=m.tiempos_por_distancia,
                segment_gps_json=segment_gps_json,
                sectores_detalle=calcular_sectores(m.tiempos_por_distancia, tramo.distancia),
                paladas_detalle=list(paladas_info.dist_por_palada),
            )

            if first_prueba_id is None:
                first_prueba_id = prueba.id
            pruebas_info.append((m, idx_valido, start_dt, paladas_info.dist_por_palada))

        recalc_sesion_aggregates(sesion.id)

        report_filename = None
        if pruebas_info:
            output_dir = settings.resolved_output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            base = filename.rsplit(".", 1)[0]
            report_filename = f"Informe_{base}.txt"
            report_path = output_dir / report_filename
            try:
                report_text = generar_resumen_sesion(filename, pruebas_info)
                report_path.write_text(report_text, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                report_filename = None
                print(f"[WARN] No se pudo escribir el informe .txt: {exc}")

        conteo = {d: 0 for d in settings.distancias_validas}
        for m, _, _, _ in pruebas_info:
            conteo[m.distancia] += 1

        resumen.update({
            "sesion_id": sesion.id,
            "report_filename": report_filename,
            "conteo_distancias": conteo,
            "total_pruebas": len(pruebas_info),
            "first_prueba_id": first_prueba_id,
        })

        if not pruebas_info:
            resumen["estado"] = "ok_sin_pruebas"
            resumen["mensaje"] = "No se detectaron pruebas de velocidad; se registró solo el GPS del entreno."

        return resumen
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.post("/informes/upload", response_class=HTMLResponse)
async def upload_csv(
    request: Request,
    files: list[UploadFile] = File(..., alias="files"),
):
    overwrite = request.query_params.get("overwrite") == "1"

    if not files:
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "error": "No se enviaron archivos",
                "active_nav": "informes",
                "distancias_validas": settings.distancias_validas,
            },
            status_code=400,
        )

    resumenes: list[dict] = []
    top_error: str | None = None

    for f in files:
        filename = f.filename or ""
        if not filename.lower().endswith(".csv"):
            resumenes.append({
                "csv_filename": filename or "(sin nombre)",
                "estado": "error",
                "conteo_distancias": {d: 0 for d in settings.distancias_validas},
                "total_pruebas": 0,
                "first_prueba_id": None,
                "report_filename": None,
                "sesion_id": None,
                "mensaje": "Solo se aceptan archivos CSV",
            })
            continue

        try:
            content = await f.read()
        except Exception as exc:  # noqa: BLE001
            resumenes.append({
                "csv_filename": filename,
                "estado": "error",
                "conteo_distancias": {d: 0 for d in settings.distancias_validas},
                "total_pruebas": 0,
                "first_prueba_id": None,
                "report_filename": None,
                "sesion_id": None,
                "mensaje": f"No se pudo leer el archivo: {exc}",
            })
            continue

        resumenes.append(_process_single_csv(content, filename, overwrite))

    if all(r["estado"] == "error" for r in resumenes):
        top_error = "Ninguno de los archivos pudo procesarse."

    page_data = get_recent_uploads(page=1)

    return templates.TemplateResponse(
        name="informes.html",
        request=request,
        context={
            "resumenes": resumenes,
            "error": top_error,
            "active_nav": "informes",
            "distancias_validas": settings.distancias_validas,
            "recent_uploads": page_data["uploads"],
            "page": page_data["page"],
            "total_pages": page_data["total_pages"],
            "total": page_data["total"],
        },
    )


@router.post("/informes/generate")
async def informes_generate(request: Request, sesion_id: int = Form(...)):
    pruebas = list_pruebas_by_sesion(sesion_id)
    if not pruebas:
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "message": "Sesión sin pruebas",
                "active_nav": "informes",
                "distancias_validas": settings.distancias_validas,
            },
        )
    # Build txt content from pruebas
    output_dir = settings.resolved_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report_filename = f"Informe_sesion_{sesion_id}.txt"
    report_path = output_dir / report_filename
    lines = [f"Sesión #{sesion_id} - {datetime.now().strftime('%d/%m/%Y %H:%M')}", ""]
    for p in pruebas:
        lines.append(f"Prueba #{p.test_number}: {p.distancia.metros if p.distancia else '?'}m - {p.tiempo_total:.2f}s")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return templates.TemplateResponse(
        name="informes.html",
        request=request,
        context={
            "message": f"Informe generado: {report_filename}",
            "active_nav": "informes",
            "distancias_validas": settings.distancias_validas,
        },
    )


@router.get("/informes/reporte/{filename}")
async def ver_reporte(filename: str):
    if ".." in filename or filename.startswith("/") or "/" in filename:
        return JSONResponse({"error": "Filename inválido"}, status_code=400)
    path = settings.resolved_output_dir / filename
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "Informe no encontrado"}, status_code=404)
    content = path.read_text(encoding="utf-8")
    return JSONResponse({"filename": filename, "content": content})


@router.get("/informes/reporte/{filename:path}/download")
async def descargar_reporte(filename: str):
    if ".." in filename or filename.startswith("/"):
        return JSONResponse({"error": "Filename inválido"}, status_code=400)
    path = settings.resolved_output_dir / filename
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(
        str(path),
        filename=filename,
        media_type="text/plain; charset=utf-8",
    )


@router.get("/informes/download-csvs")
async def descargar_todos_csvs():
    """Empaqueta todos los CSVs subidos en un ZIP y lo sirve para descarga."""
    uploads = list_csv_uploads(limit=10000)

    input_dir = settings.resolved_input_dir
    zip_buffer = io.BytesIO()
    used_names: set[str] = set()
    added = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for upload in uploads:
            file_path = Path(upload.file_path) if upload.file_path else None
            if not file_path or not file_path.is_file():
                file_path = input_dir / upload.filename
                if not file_path.is_file():
                    continue

            archive_name = upload.filename
            if archive_name in used_names:
                base = Path(upload.filename).stem
                suffix = Path(upload.filename).suffix
                archive_name = f"{base}_{upload.id}{suffix}"
            used_names.add(archive_name)

            zf.write(file_path, arcname=archive_name)
            added += 1

    zip_buffer.seek(0)

    if added == 0:
        return JSONResponse(
            {"error": "No hay archivos CSV disponibles para descargar"},
            status_code=404,
        )

    zip_name = f"dragonboat_csvs_{datetime.now().strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


# ── Configuración ──

@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={"active_nav": "config", "section": "main"},
    )


@router.get("/config/barcos", response_class=HTMLResponse)
async def config_barcos(request: Request):
    with db_session() as s:
        boats = s.query(Boat).order_by(Boat.name).all()
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={
            "active_nav": "config",
            "section": "barcos",
            "boats": boats,
        },
    )


@router.post("/config/barcos")
async def config_barcos_post(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(...),
    num_rows: int = Form(...),
    total_persons: int = Form(...),
):
    with db_session() as s:
        boat = Boat(name=name, display_name=display_name,
                    num_rows=num_rows, total_persons=total_persons)
        s.add(boat)
        s.commit()
    return RedirectResponse(url="/config/barcos", status_code=302)


@router.post("/config/barcos/{boat_id}/delete")
async def config_barcos_delete(boat_id: int):
    with db_session() as s:
        boat = s.query(Boat).filter(Boat.id == boat_id).first()
        if boat:
            s.delete(boat)
            s.commit()
    return RedirectResponse(url="/config/barcos", status_code=302)


@router.get("/config/categorias", response_class=HTMLResponse)
async def config_categorias(request: Request):
    categories = list_categories()
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={
            "active_nav": "config",
            "section": "categorias",
            "categories": categories,
        },
    )


@router.post("/config/categorias")
async def config_categorias_post(name: str = Form(...)):
    from dragonboat.repo import crear_category
    crear_category(name=name)
    return RedirectResponse(url="/config/categorias", status_code=302)


@router.post("/config/categorias/{cat_id}/edit")
async def config_categorias_edit(cat_id: int, name: str = Form(...)):
    from dragonboat.repo import update_category
    update_category(cat_id, name=name)
    return RedirectResponse(url="/config/categorias", status_code=302)


@router.post("/config/categorias/{cat_id}/delete")
async def config_categorias_delete(cat_id: int):
    from dragonboat.repo import delete_category
    delete_category(cat_id)
    return RedirectResponse(url="/config/categorias", status_code=302)


@router.get("/config/tipos", response_class=HTMLResponse)
async def config_tipos(request: Request):
    test_types = list_test_types()
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={
            "active_nav": "config",
            "section": "tipos",
            "test_types": test_types,
        },
    )


@router.post("/config/tipos")
async def config_tipos_post(name: str = Form(...)):
    from dragonboat.repo import crear_test_type
    crear_test_type(name=name)
    return RedirectResponse(url="/config/tipos", status_code=302)


@router.post("/config/tipos/{type_id}/edit")
async def config_tipos_edit(type_id: int, name: str = Form(...)):
    from dragonboat.repo import update_test_type
    update_test_type(type_id, name=name)
    return RedirectResponse(url="/config/tipos", status_code=302)


@router.post("/config/tipos/{type_id}/delete")
async def config_tipos_delete(type_id: int):
    from dragonboat.repo import delete_test_type
    delete_test_type(type_id)
    return RedirectResponse(url="/config/tipos", status_code=302)


@router.get("/config/distancias", response_class=HTMLResponse)
async def config_distancias(request: Request):
    distancias = list_distancias()
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={
            "active_nav": "config",
            "section": "distancias",
            "distancias": distancias,
        },
    )


@router.post("/config/distancias")
async def config_distancias_post(
    request: Request,
    metros: int = Form(...),
    descripcion: str = Form(...),
    orden: int = Form(...),
):
    crear_distancia(metros=metros, descripcion=descripcion, orden=orden)
    return RedirectResponse(url="/config/distancias", status_code=302)


@router.post("/config/distancias/{distancia_id}/edit")
async def config_distancias_edit(
    distancia_id: int,
    descripcion: str = Form(...),
    orden: int = Form(...),
):
    update_distancia(distancia_id, descripcion=descripcion, orden=orden)
    return RedirectResponse(url="/config/distancias", status_code=302)


@router.post("/config/distancias/{distancia_id}/delete")
async def config_distancias_delete(distancia_id: int):
    delete_distancia(distancia_id)
    return RedirectResponse(url="/config/distancias", status_code=302)


@router.get("/config/umbral", response_class=HTMLResponse)
async def config_umbral(request: Request):
    umbral = get_umbral_parado()
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={
            "active_nav": "config",
            "section": "umbral",
            "umbral_parado": umbral,
        },
    )


@router.post("/config/umbral")
async def config_umbral_post(umbral: float = Form(...)):
    if 0.5 <= umbral <= 20.0:
        set_setting("umbral_velocidad_parado", f"{umbral:.2f}")
    return RedirectResponse(url="/config/umbral", status_code=302)


@router.get("/config/telegram", response_class=HTMLResponse)
async def config_telegram(request: Request):
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={
            "active_nav": "config",
            "section": "telegram",
        },
    )


# ── API ──

@router.get("/api/ranking")
async def api_ranking():
    ranking = get_ranking(limit=20)
    for r in ranking:
        if r.get("fecha"):
            r["fecha"] = r["fecha"].isoformat()
    return JSONResponse(ranking)


@router.get("/api/boat-stats")
async def api_boat_stats():
    return JSONResponse(get_boat_stats())


@router.get("/api/sesiones")
async def api_sesiones():
    sesiones = list_sesiones_diarias(200)
    return JSONResponse([
        {
            "id": s.id,
            "fecha": s.fecha.isoformat() if s.fecha else None,
            "categoria": s.categoria,
            "tipo": s.tipo,
            "num_pruebas": s.num_pruebas,
            "num_archivos": s.num_archivos,
            "distancia_total_nominal": s.distancia_total_nominal,
            "tiempo_total_entreno": s.tiempo_total_entreno,
            "tiempo_parado": s.tiempo_parado,
            "tiempo_movimiento": s.tiempo_movimiento,
            "vel_media_movimiento": s.vel_media_movimiento,
            "vel_max_dia": s.vel_max_dia,
        }
        for s in sesiones
    ])


@router.get("/api/pruebas")
async def api_pruebas(sesion_id: int = None, limit: int = 100):
    if sesion_id:
        pruebas = list_pruebas_by_sesion(sesion_id)
    else:
        pruebas = list_pruebas(limit)
    return JSONResponse([
        {
            "id": p.id,
            "sesion_id": p.sesion_id,
            "fecha_hora": p.fecha_hora.isoformat() if p.fecha_hora else None,
            "custom_name": p.custom_name,
            "distancia": p.distancia.metros if p.distancia else None,
            "tiempo_total": p.tiempo_total,
            "velocidad_media": p.velocidad_media,
            "boat_name": p.boat.name if p.boat else None,
        }
        for p in pruebas
    ])
