"""Report generation — adapted from dragonboat_analyzer.py lines 358-437.

Extended to support any of the standard distances (200/500/1000/2000m).
"""

from __future__ import annotations

import os
from datetime import datetime

from dragonboat.analysis._utils import (
    calcular_sectores,
    fmt,
    format_duration,
    resumen_paladas,
)
from dragonboat.config import settings
from dragonboat.models import Metricas, PaladasInfo


def imprimir_metricas(m: Metricas, filename: str, idx: int) -> None:
    """Print a summary of one training test to stdout."""
    d = m.distancia
    print()
    print("=" * 65)
    print(f"  PRUEBA {d}m #{idx} - {os.path.basename(filename)}")
    print(f"  Barco dragon de {settings.bote_personas} personas")
    print("=" * 65)
    print(f"  Tiempo total {d}m:            {format_duration(m.tiempo_total)}")
    print(
        f"  Velocidad media:            {fmt(m.velocidad_media)} km/h"
        f"  ({fmt(m.velocidad_media / 3.6)} m/s)"
    )
    print(f"  Velocidad maxima:           {fmt(m.velocidad_maxima)} km/h")
    print(
        f"  Aceleracion maxima:         {fmt(m.aceleracion_max, 3)} m/s2"
        f"  ({fmt(m.aceleracion_max / 9.81, 4)} G)"
    )
    print("=" * 65)
    print()


def nombre_base(m: Metricas, idx: int, start_dt: datetime) -> str:
    """Generate the base filename for outputs of one test."""
    d = m.distancia
    return (
        f"{d}metros_{start_dt.strftime('%m%d')}_{idx}_"
        f"{start_dt.strftime('%H-%M')}_{m.tiempo_total:.2f}"
    )


def _format_sector_line(s: dict, is_first: bool) -> str:
    """Render one sector dict as a bullet line, matching the report layout."""
    t_sector = format_duration(s["t_sector"]) if s["t_sector"] is not None else "—"
    t_acum = format_duration(s["t_acum"])
    vel = fmt(s["vel"]) if s["vel"] is not None else "—"
    if is_first:
        return f"• 0 a {s['to']}m: {t_sector} ({vel}km/h)"
    return f"• {s['from']} a {s['to']}m: {t_sector} ({vel}km/h) {t_acum}"


def generar_informe_str(
    m: Metricas,
    idx: int,
    start_dt: datetime,
    dist_por_palada: list[float] | None = None,
) -> str:
    """Generate the text report block for a single training test.

    `dist_por_palada` is optional; the values needed from it are derived here
    via `resumen_paladas()`. The same helper is used to populate the web view
    from the persisted `paladas_detalle` column.
    """
    d = m.distancia
    vel_media_ms = m.velocidad_media / 3.6
    acel_g = m.aceleracion_max / 9.81
    std_str = fmt(m.dist_std_palada, 2) if m.dist_std_palada > 0 else "N/A"
    test_time = m.tiempo_total

    sectores = calcular_sectores(m.tiempos_por_distancia, d)
    sector_lines: list[str] = []
    for i, s in enumerate(sectores):
        sector_lines.append(_format_sector_line(s, is_first=(i == 0)))

    resumen = resumen_paladas(dist_por_palada)
    dist_max = resumen["max_all"] or 0
    dist_min = resumen["min_salida"] or 0
    dist_min_sin10 = resumen["min_sin10"] or 0

    lines = [
        f"*Dragon Boat - {d}m *",
        f'{start_dt.strftime("%d/%m/%Y %H:%M")} Prueba #{idx}',
        "",
        f"⏱️ *Tiempo total: {format_duration(test_time)}*",
        "",
        "📍 *Tiempos por sector*",
        f"• Aceleracion 0 a 12 km/h: {format_duration(m.tiempo_12kmh)}",
        *sector_lines,
        "",
        "📊 *Velocidad*",
        f"• Media: {fmt(m.velocidad_media)}km/h ({fmt(vel_media_ms)} m/s)",
        f"• Maxima: {fmt(m.velocidad_maxima)}km/h",
        f"• Minima: {fmt(m.velocidad_min_post10)}km/h (sin 15 primeras)",
        f"• Acel maxima: {fmt(m.aceleracion_max, 3)}m/s2 ({fmt(acel_g, 3)} G)",
        "",
        "🔄 *Paladas*",
        f"• Total: {m.num_paladas}",
        f"• Distancia por palada: {fmt(m.dist_media_palada)} m",
        f"• Maxima: {fmt(dist_max)} m",
        f"• Minima: {fmt(dist_min)} m (salida)",
        f"• Minima: {fmt(dist_min_sin10)} m (sin 10 primeras)",
        f"• Consistencia: {std_str} m",
    ]
    return "\n".join(lines)


def generar_resumen_sesion(
    csv_filename: str,
    pruebas: list[tuple],
) -> str:
    """Build the combined .txt report for an entire CSV upload.

    Each entry in `pruebas` is a tuple (m, idx, start_dt, dist_por_palada)
    matching the signature of generar_informe_str.
    """
    sep = "-" * 40
    header = (
        f"📋 RESUMEN DE SESION: {csv_filename}\n"
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        f"=============================================\n"
    )

    body_blocks: list[str] = []
    for m, idx, start_dt, dist_por_palada in pruebas:
        block = generar_informe_str(m, idx, start_dt, dist_por_palada)
        body_blocks.append(block)

    if not body_blocks:
        return header + "\n(Sin pruebas válidas detectadas)\n"

    return header + "\n\n" + ("\n\n" + sep + "\n\n").join(body_blocks) + "\n"


