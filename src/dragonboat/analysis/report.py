"""Report generation — adapted from dragonboat_analyzer.py lines 358-437.

Extended to support any of the standard distances (200/500/1000/2000m).
"""

from __future__ import annotations

import os
from datetime import datetime

from dragonboat.analysis._utils import fmt, format_duration
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


def generar_informe_str(
    m: Metricas,
    idx: int,
    start_dt: datetime,
    dist_por_palada: list[float],
) -> str:
    """Generate the text report block for a single training test."""
    d = m.distancia
    step = d / 4.0
    vel_media_ms = m.velocidad_media / 3.6
    acel_g = m.aceleracion_max / 9.81
    std_str = fmt(m.dist_std_palada, 2) if m.dist_std_palada > 0 else "N/A"
    test_time = m.tiempo_total

    # Build sector lines from tiempos_por_distancia
    sector_lines: list[str] = []
    keys = [str(int(step * i)) for i in range(1, 5)]
    for i, k in enumerate(keys):
        t = m.tiempos_por_distancia.get(k)
        if t is not None:
            if i == 0:
                v = (step / t) * 3.6
                sector_lines.append(
                    f"• 0 a {k}m: {format_duration(t)} ({fmt(v)}km/h)"
                )
            else:
                prev_key = keys[i - 1]
                prev_t = m.tiempos_por_distancia.get(prev_key)
                if prev_t is not None:
                    seg_t = t - prev_t
                    seg_d = step
                    v = (seg_d / seg_t) * 3.6
                    sector_lines.append(
                        f"• {prev_key} a {k}m: {format_duration(seg_t)} ({fmt(v)}km/h) {format_duration(t)}"
                    )
                else:
                    sector_lines.append(f"• {k}m: {format_duration(t)}")

    dist_max = max(dist_por_palada) if dist_por_palada else 0
    dist_min = min(dist_por_palada) if dist_por_palada else 0
    dist_min_sin10 = min(dist_por_palada[10:]) if len(dist_por_palada) > 10 else 0

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

