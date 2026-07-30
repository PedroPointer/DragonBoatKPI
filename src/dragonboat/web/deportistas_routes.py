"""Deportistas routes — CRUD, import CSV, photo upload, boat assignment."""

from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from PIL import Image

from dragonboat.config import settings
from dragonboat.repo import (
    list_crew,
    get_crew_member,
    crear_crew_member,
    update_crew_member,
    delete_crew_member,
    get_assignments,
    save_assignments,
    list_categories,
)
from dragonboat.db_models import CrewMember
from dragonboat.database import get_session as db_session
from dragonboat.visualization.boat_svg import render_boat_svg
import json

router = APIRouter()

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

PHOTOS_DIR = settings.resolved_output_dir.parent / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def _save_photo(member_id: int, file_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")
    img.thumbnail((40, 40), Image.LANCZOS)

    w, h = img.size
    left = (w - 40) // 2
    top = (h - 40) // 2
    img = img.crop((left, top, left + 40, top + 40))

    filename = f"{member_id}.webp"
    path = PHOTOS_DIR / filename
    img.save(path, "WEBP", quality=85)
    return filename


@router.get("/deportistas", response_class=HTMLResponse)
async def deportistas_list(request: Request):
    crew = list_crew()
    categories = list_categories()
    return templates.TemplateResponse(
        name="deportistas.html",
        request=request,
        context={
            "crew": crew,
            "categories": categories,
            "active_nav": "deportistas",
        },
    )


@router.post("/deportistas/add")
async def deportistas_add(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(...),
    categoria: str = Form(None),
    photo: UploadFile = File(None),
):
    cm = crear_crew_member(
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        categoria=categoria or None,
    )

    if photo and photo.filename:
        content = await photo.read()
        filename = _save_photo(cm.id, content)
        with db_session() as s:
            db_cm = s.query(CrewMember).filter(CrewMember.id == cm.id).first()
            if db_cm:
                db_cm.photo_path = filename
                s.commit()

    return RedirectResponse(url="/deportistas", status_code=302)


@router.post("/deportistas/{member_id}/edit")
async def deportistas_edit(
    member_id: int,
    nombre: str = Form(...),
    apellido: str = Form(...),
    categoria: str = Form(None),
    photo: UploadFile = File(None),
):
    update_crew_member(
        member_id,
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        categoria=categoria or None,
    )
    if photo and photo.filename:
        content = await photo.read()
        filename = _save_photo(member_id, content)
        with db_session() as s:
            db_cm = s.query(CrewMember).filter(CrewMember.id == member_id).first()
            if db_cm:
                db_cm.photo_path = filename
                s.commit()
    return RedirectResponse(url="/deportistas", status_code=302)


@router.post("/deportistas/{member_id}/delete")
async def deportistas_delete(member_id: int):
    for ext in ("webp", "jpg", "png"):
        p = PHOTOS_DIR / f"{member_id}.{ext}"
        if p.exists():
            p.unlink()

    delete_crew_member(member_id)
    return RedirectResponse(url="/deportistas", status_code=302)


@router.post("/deportistas/import")
async def deportistas_import(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        return RedirectResponse(url="/deportistas", status_code=302)

    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    for row in reader:
        nombre = (row.get("nombre") or row.get("Nombre") or "").strip()
        apellido = (row.get("apellido") or row.get("Apellido") or "").strip()
        categoria = (row.get("categoria") or row.get("Categoria") or "").strip() or None
        if nombre and apellido:
            crear_crew_member(nombre=nombre, apellido=apellido, categoria=categoria)
            count += 1

    print(f"[DEPORTISTAS] Imported {count} crew members from CSV")
    return RedirectResponse(url="/deportistas", status_code=302)


@router.get("/test/{test_id}/crew", response_class=HTMLResponse)
async def boat_page(request: Request, test_id: int):
    return RedirectResponse(url=f"/test/{test_id}#tripulacion", status_code=302)


@router.post("/test/{test_id}/crew")
async def boat_save(request: Request, test_id: int):
    form = await request.form()
    assignments = []

    for key, value in form.items():
        if key.startswith("slot_") and value:
            parts = key.split("_")
            role = parts[1]
            side = parts[2] if parts[2] != "None" else None
            row_num = int(parts[3]) if parts[3] != "None" else None
            crew_member_id = int(value)

            assignments.append({
                "crew_member_id": crew_member_id,
                "role": role,
                "side": side,
                "row_number": row_num,
            })

    save_assignments(test_id, assignments)
    return RedirectResponse(url=f"/test/{test_id}#tripulacion", status_code=302)


@router.post("/test/{test_id}/crew/json")
async def boat_save_json(request: Request, test_id: int):
    import json
    body = await request.json()
    raw = body.get("assignments", [])
    assignments = []
    for a in raw:
        assignments.append({
            "crew_member_id": int(a["crew_member_id"]),
            "role": a["role"],
            "side": a.get("side"),
            "row_number": a.get("row_number"),
        })
    save_assignments(test_id, assignments)
    return JSONResponse({"ok": True})
