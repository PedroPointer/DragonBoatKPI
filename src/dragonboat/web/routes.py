"""Web routes — dashboard, registros, informes, config."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from dragonboat.analysis import (
    analizar_200m,
    build_gps_data_json,
    cargar_csv,
    detectar_200m,
    detectar_paladas,
    generar_informe_str,
    imprimir_metricas,
    nombre_base,
)
from dragonboat.config import settings
from dragonboat.repo import (
    crear_csv_upload,
    crear_sesion,
    crear_test_gps_data,
    get_csv_upload,
    get_csv_upload_by_filename,
    delete_csv_upload,
    get_sesion,
    get_sesiones,
    get_csv_sesiones,
    get_ranking,
    get_boat_stats,
    get_distinct_names,
    update_sesion,
    delete_sesion,
    get_test_gps_data,
    get_trajectory,
    list_categories,
    get_category,
    crear_category,
    update_category,
    delete_category,
    list_test_types,
    crear_test_type,
    update_test_type,
    delete_test_type,
    get_dias_con_entrenamientos,
    list_crew,
    get_assignments,
)
from dragonboat.db_models import Boat, Sesion as SesionModel
from dragonboat.database import get_session as db_session
from dragonboat.visualization.charts import graficar_200m, graficar_200m_plotly

router = APIRouter()

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

CATEGORIAS = [
    "Open Sénior", "Open Veterano",
    "Femenino Sénior", "Femenino Veterano",
    "Mixto Sénior", "Mixto Veterano",
    "ACS", "PD1", "PD2", "PD3",
]


# ── Dashboard (Home) ──

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    ranking = get_ranking(limit=20)
    boat_stats = get_boat_stats()
    sesiones = get_sesiones(50)

    incomplete = []
    for s in sesiones:
        warns = []
        boat = s.boat
        if not boat:
            with db_session() as sess:
                boat = sess.query(Boat).filter(Boat.name == "DB12").first()
        num_rows = boat.num_rows if boat else 5
        assigned = sum(1 for a in s.crew_assignments if a.role == "remero")
        if assigned < num_rows * 2:
            warns.append({"type": "crew", "label": "falta asignar tripulación"})
        has_timonel = any(a.role == "timonel" for a in s.crew_assignments)
        if not has_timonel:
            warns.append({"type": "timonel", "label": "falta timonel"})
        if warns:
            incomplete.append({"sesion": s, "warnings": warns})

    return templates.TemplateResponse(
        name="dashboard.html",
        request=request,
        context={
            "ranking": ranking,
            "boat_stats": boat_stats,
            "incomplete": incomplete,
            "active_nav": "dashboard",
        },
    )


# ── Registros ──

@router.get("/registros", response_class=HTMLResponse)
async def registros_list(
    request: Request,
    tipo: str = None,
    barco: str = None,
):
    sesiones = get_sesiones(200)
    if tipo:
        sesiones = [s for s in sesiones if s.tipo == tipo]
    if barco:
        sesiones = [s for s in sesiones if s.boat and s.boat.name == barco]

    rows = []
    for s in sesiones:
        rows.append({
            "prueba_id": s.id,
            "numero": s.test_number,
            "nombre": s.custom_name or "",
            "tipo": s.tipo or "",
            "barco": s.boat.name if s.boat else "",
            "tiempo": s.metric.tiempo_total if s.metric else None,
            "categoria": s.categoria or "",
            "fecha": s.fecha_hora,
            "hora": s.fecha_hora.strftime("%H:%M") if s.fecha_hora else "",
        })

    boats = []
    with db_session() as s:
        boats = s.query(Boat).all()

    return templates.TemplateResponse(
        name="registros.html",
        request=request,
        context={
            "rows": rows,
            "boats": boats,
            "filter_tipo": tipo or "",
            "filter_barco": barco or "",
            "active_nav": "registros",
        },
    )


@router.get("/registros/dias")
async def registros_dias(year: int = None, month: int = None):
    from datetime import datetime
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    dias = get_dias_con_entrenamientos(year, month)
    return JSONResponse({"dias": dias})


@router.get("/registros/{prueba_id}", response_class=HTMLResponse)
async def sesion_detail(request: Request, prueba_id: int):
    """Detail view of a single prueba (sesion). Redirect to test page."""
    return RedirectResponse(url=f"/test/{prueba_id}", status_code=302)


@router.post("/registros/{prueba_id}")
async def sesion_update(
    request: Request,
    prueba_id: int,
    tipo: str = Form(None),
    boat_id: int = Form(None),
):
    update_sesion(prueba_id, tipo=tipo, boat_id=boat_id)
    return RedirectResponse(url=f"/test/{prueba_id}", status_code=302)


@router.post("/registros/{prueba_id}/delete")
async def sesion_delete(prueba_id: int):
    delete_sesion(prueba_id)
    return RedirectResponse(url="/registros", status_code=302)


# ── Test / Prueba detail routes ──

@router.get("/test/{test_id}", response_class=HTMLResponse)
async def test_page(request: Request, test_id: int):
    import json as _json
    from dragonboat.repo import list_crew_by_frequency, get_assignments

    test = get_sesion(test_id)
    if not test:
        return RedirectResponse(url="/registros", status_code=302)

    chart_available = bool(
        test.metric and test.metric.chart_filename
        and (settings.resolved_output_dir / f"{test.metric.chart_filename}.png").exists()
    )

    with db_session() as s:
        boats = s.query(Boat).all()

    names = get_distinct_names()
    tipos = list_test_types()

    # Boat for crew section
    boat = test.boat
    if not boat:
        with db_session() as s:
            boat = s.query(Boat).filter(Boat.name == "DB12").first()

    # Crew data for interactive SVG (ordered by frequency)
    crew_list = list_crew_by_frequency()
    crew_json = _json.dumps([
        {"id": cm["id"], "nombre": cm["nombre"], "apellido": cm["apellido"],
         "categoria": cm["categoria"], "photo_path": cm["photo_path"], "freq": cm["freq"]}
        for cm in crew_list
    ])

    raw_assignments = get_assignments(test_id)
    assignments_json = _json.dumps([
        {"crew_member_id": a.crew_member_id, "role": a.role,
         "side": a.side, "row_number": a.row_number}
        for a in raw_assignments
    ])

    return templates.TemplateResponse(
        name="test.html",
        request=request,
        context={
            "test": test,
            "chart_available": chart_available,
            "boat": boat,
            "boats": boats,
            "names": names,
            "categorias": CATEGORIAS,
            "tipos": tipos,
            "crew_json": crew_json,
            "assignments_json": assignments_json,
            "active_nav": "registros",
        },
    )


@router.post("/test/{test_id}")
async def test_update(
    request: Request,
    test_id: int,
    custom_name: str = Form(None),
    categoria: str = Form(None),
    boat_id: int = Form(None),
    tipo: str = Form(None),
):
    update_sesion(
        test_id,
        custom_name=custom_name.strip() if custom_name else None,
        categoria=categoria or None,
        boat_id=boat_id,
        tipo=tipo or None,
    )
    return RedirectResponse(url=f"/test/{test_id}", status_code=302)


@router.get("/test/{test_id}/trajectory")
async def test_trajectory(test_id: int):
    """Return GPS trajectory points for the test map."""
    points = get_trajectory(test_id)
    if not points:
        return JSONResponse({"points": [], "center": None})
    center = [
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    ]
    return JSONResponse({"points": points, "center": center})


@router.get("/test/{test_id}/chart-html")
async def test_chart_html(test_id: int, panels: str = ""):
    """Return Plotly HTML for the interactive viewer.

    panels: comma-separated panel names, e.g. "speed,roll". Empty = all.
    """
    ALL_PANELS = {"speed", "roll", "pitch", "dist"}

    if panels.strip():
        panel_set = {p.strip() for p in panels.split(",") if p.strip()} & ALL_PANELS
    else:
        panel_set = ALL_PANELS
    if not panel_set:
        panel_set = ALL_PANELS

    panels_key = "_".join(sorted(panel_set))
    charts_dir = settings.resolved_output_dir / "charts"
    path = charts_dir / f"{test_id}_{panels_key}.html"

    if not path.exists():
        # Need to generate: load data + metric
        gps_data = get_test_gps_data(test_id)
        if not gps_data:
            return HTMLResponse("<p>Gráfica no disponible — subir el CSV nuevamente</p>", status_code=404)
        test_obj = get_sesion(test_id)
        if not test_obj or not test_obj.metric:
            return HTMLResponse("<p>Gráfica no disponible</p>", status_code=404)
        tm = test_obj.metric
        from dragonboat.models import Metricas
        m = Metricas(
            tiempo_total=tm.tiempo_total,
            velocidad_media=tm.velocidad_media,
            velocidad_maxima=tm.velocidad_maxima,
            velocidad_min_post10=tm.velocidad_min_post10,
            aceleracion_max=tm.aceleracion_max,
            tiempo_11kmh=tm.tiempo_11kmh,
            tiempo_12kmh=tm.tiempo_12kmh,
            tiempo_150m=tm.tiempo_150m,
            tiempo_50m=tm.tiempo_50m,
            tiempo_100m=tm.tiempo_100m,
            tiempo_ultimos_50m=None,
            vel_media_ultimos_50m=None,
            num_paladas=tm.num_paladas,
            dist_media_palada=tm.dist_media_palada,
            dist_std_palada=tm.dist_std_palada,
            start_idx=0, end_idx=0, start_time=0, exact_time=0,
            dist_max_palada=tm.dist_max_palada,
            dist_min_palada=tm.dist_min_palada,
        )
        graficar_200m_plotly(gps_data, m, settings.resolved_output_dir, test_id, panels=panel_set)

    return HTMLResponse(path.read_text(encoding="utf-8"))


@router.get("/test/{test_id}/chart.png")
async def test_chart_png(test_id: int):
    """Serve/download the matplotlib PNG chart."""
    test_obj = get_sesion(test_id)
    if not test_obj or not test_obj.metric or not test_obj.metric.chart_filename:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = settings.resolved_output_dir / f"{test_obj.metric.chart_filename}.png"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(
        path,
        filename=f"prueba_{test_id}_{test_obj.metric.chart_filename}.png",
        media_type="image/png",
    )


# ── Informes ──

@router.get("/informes", response_class=HTMLResponse)
async def informes_page(request: Request):
    return templates.TemplateResponse(
        name="informes.html",
        request=request,
        context={"active_nav": "informes"},
    )


@router.post("/informes/upload", response_class=HTMLResponse)
async def upload_csv(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "error": "Solo se aceptan archivos CSV",
                "active_nav": "informes",
            },
            status_code=400,
        )

    content = await file.read()

    # Dedupe check
    overwrite = request.query_params.get("overwrite") == "1"
    existing = get_csv_upload_by_filename(file.filename)
    if existing and not overwrite:
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "duplicate_filename": file.filename,
                "active_nav": "informes",
            },
        )

    if existing and overwrite:
        delete_csv_upload(existing.id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = cargar_csv(tmp_path)
    except Exception:
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "error": "Error al leer el CSV",
                "active_nav": "informes",
            },
            status_code=400,
        )

    tramos = detectar_200m(df)
    if not tramos:
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "error": "No se detectaron tramos de 200m",
                "active_nav": "informes",
            },
            status_code=400,
        )

    input_dir = settings.resolved_input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(input_dir / file.filename)
    (input_dir / file.filename).write_bytes(content)

    csv_upload = crear_csv_upload(file.filename, file_path=file_path)
    idx_valido = 0
    first_sesion_id = None

    for tramo in tramos:
        paladas_info = detectar_paladas(df, tramo.start_idx, tramo.end_idx)
        m = analizar_200m(df, tramo.start_idx, tramo.end_idx, paladas_info)
        if m is None:
            continue

        t11 = m.tiempo_11kmh if m.tiempo_11kmh is not None else 99
        if not (m.tiempo_total < 85.0 and t11 < 20.0 and m.velocidad_media > 9.0):
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
        imprimir_metricas(m, file.filename, idx_valido)

        chart_path = graficar_200m(df, m, paladas_info, settings.resolved_output_dir, nb)
        sesion = crear_sesion(
            csv_upload.id, idx_valido, m,
            fecha_hora=start_dt,
            tipo="entreno",
            chart_filename=nb,
        )
        gps_data = build_gps_data_json(df, tramo.start_idx, tramo.end_idx, paladas_info, m)
        crear_test_gps_data(sesion.id, gps_data)
        graficar_200m_plotly(gps_data, m, settings.resolved_output_dir, sesion.id)
        if first_sesion_id is None:
            first_sesion_id = sesion.id

    os.unlink(tmp_path)

    if idx_valido == 0:
        return templates.TemplateResponse(
            name="informes.html",
            request=request,
            context={
                "error": "No se detectaron tramos validos",
                "active_nav": "informes",
            },
            status_code=400,
        )

    return RedirectResponse(url=f"/test/{first_sesion_id}", status_code=302)


@router.post("/informes/generate")
async def informes_generate(request: Request, session_id: int = Form(...)):
    return templates.TemplateResponse(
        name="informes.html",
        request=request,
        context={
            "message": "Generación de PDF próximamente",
            "active_nav": "informes",
        },
    )


# ── Config ──

@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse(
        name="config.html",
        request=request,
        context={"active_nav": "config", "section": "main"},
    )


# ── Config: Barcos ──

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


# ── Config: Categorías ──

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
    crear_category(name=name)
    return RedirectResponse(url="/config/categorias", status_code=302)


@router.post("/config/categorias/{cat_id}/edit")
async def config_categorias_edit(cat_id: int, name: str = Form(...)):
    update_category(cat_id, name=name)
    return RedirectResponse(url="/config/categorias", status_code=302)


@router.post("/config/categorias/{cat_id}/delete")
async def config_categorias_delete(cat_id: int):
    delete_category(cat_id)
    return RedirectResponse(url="/config/categorias", status_code=302)


# ── Config: Tipos ──

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
    crear_test_type(name=name)
    return RedirectResponse(url="/config/tipos", status_code=302)


@router.post("/config/tipos/{type_id}/edit")
async def config_tipos_edit(type_id: int, name: str = Form(...)):
    update_test_type(type_id, name=name)
    return RedirectResponse(url="/config/tipos", status_code=302)


@router.post("/config/tipos/{type_id}/delete")
async def config_tipos_delete(type_id: int):
    delete_test_type(type_id)
    return RedirectResponse(url="/config/tipos", status_code=302)


# ── Config: Telegram ──

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


@router.get("/api/sessions")
async def api_sessions():
    sesiones = get_sesiones(200)
    return JSONResponse([
        {
            "id": s.id,
            "csv_filename": s.csv_upload.filename if s.csv_upload else None,
            "fecha_hora": s.fecha_hora.isoformat() if s.fecha_hora else None,
            "tipo": s.tipo,
            "boat_name": s.boat.name if s.boat else None,
            "custom_name": s.custom_name,
        }
        for s in sesiones
    ])
