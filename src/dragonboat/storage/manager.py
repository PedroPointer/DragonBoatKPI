"""Storage manager — file operations, registry, session listing."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from dragonboat.config import settings


def ensure_dirs() -> None:
    """Create data directories if they don't exist."""
    settings.resolved_input_dir.mkdir(parents=True, exist_ok=True)
    settings.resolved_output_dir.mkdir(parents=True, exist_ok=True)


def cargar_registro() -> dict:
    """Load the analysis registry JSON, creating it if missing."""
    path = settings.resolved_registro_file
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        registro = {"archivos": {}}
        path.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
        return registro
    return json.loads(path.read_text(encoding="utf-8"))


def guardar_registro(registro: dict) -> None:
    """Write the registry JSON to disk."""
    path = settings.resolved_registro_file
    path.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")


def guardar_csv_subido(source_path: str, filename: str) -> Path:
    """Copy an uploaded CSV to the input directory.

    Returns the destination path.
    """
    ensure_dirs()
    dest = settings.resolved_input_dir / filename
    shutil.copy2(source_path, dest)
    return dest


def listar_sesiones() -> list[dict]:
    """List all registered sessions with their tramos."""
    registro = cargar_registro()
    sesiones = []
    for fname, info in registro.get("archivos", {}).items():
        sesiones.append(
            {
                "filename": fname,
                "fecha": info.get("fecha", ""),
                "formato": info.get("formato", ""),
                "tramos": info.get("tramos", []),
            }
        )
    return sesiones


def registrar_sesion(
    filename: str,
    formato: str,
    tramos_data: list[dict],
) -> None:
    """Register a processed session in the registry."""
    registro = cargar_registro()
    registro["archivos"][filename] = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "formato": formato,
        "tramos": tramos_data,
    }
    guardar_registro(registro)
