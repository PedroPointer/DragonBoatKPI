"""Report generation — adapted from dragonboat_analyzer.py lines 358-437."""

from __future__ import annotations

import os
from datetime import datetime

from dragonboat.analysis._utils import fmt
from dragonboat.config import settings
from dragonboat.models import Metricas, PaladasInfo


def imprimir_metricas(m: Metricas, filename: str, idx: int) -> None:
    """Print a summary of one 200m test to stdout."""
    print()
    print("=" * 65)
    print(f"  PRUEBA 200m #{idx} - {os.path.basename(filename)}")
    print(f"  Barco dragon de {settings.bote_personas} personas")
    print("=" * 65)
    print(f"  Tiempo total 200m:          {fmt(m.tiempo_total)} s")
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
    return (
        f"200metros_{start_dt.strftime('%m%d')}_{idx}_"
        f"{start_dt.strftime('%H-%M')}_{m.tiempo_total:.2f}"
    )


def generar_informe_str(
    m: Metricas,
    idx: int,
    start_dt: datetime,
    dist_por_palada: list[float],
) -> str:
    """Generate the text report block for a single 200m test."""
    vel_media_ms = m.velocidad_media / 3.6
    acel_g = m.aceleracion_max / 9.81
    std_str = fmt(m.dist_std_palada, 2) if m.dist_std_palada > 0 else "N/A"
    t11 = fmt(m.tiempo_11kmh)
    t12 = fmt(m.tiempo_12kmh)
    t50 = m.tiempo_50m
    t100 = m.tiempo_100m
    t150 = m.tiempo_150m
    test_time = m.tiempo_total

    def _seg(t_a, t_b):
        if t_a is not None and t_b is not None and t_b > t_a:
            dt = t_b - t_a
            v = (50.0 / dt) * 3.6
            return fmt(dt), fmt(v)
        return "N/A", "N/A"

    if t50 is not None:
        t_0_50 = fmt(t50)
        v_0_50 = fmt(50.0 / t50 * 3.6)
    else:
        t_0_50 = v_0_50 = "N/A"
    t_50_100, v_50_100 = _seg(t50, t100)
    t_100_150, v_100_150 = _seg(t100, t150)
    t_150_200, v_150_200 = _seg(t150, test_time)

    dist_max = max(dist_por_palada) if dist_por_palada else 0
    dist_min = min(dist_por_palada) if dist_por_palada else 0
    dist_min_sin10 = min(dist_por_palada[10:]) if len(dist_por_palada) > 10 else 0

    lines = [
        f"*Dragon Boat - 200m *",
        f'{start_dt.strftime("%d/%m/%Y %H:%M")} Prueba #{idx}',
        "",
        f"⏱️ *Tiempo total: {fmt(test_time)}s*",
        "",
        "📍 *Tiempos por sector*",
        f"• Aceleracion 0 a 12 km/h: {t12}s",
        f"• 0 a 50m: {t_0_50}s ({v_0_50}km/h)",
        f"• 50 a 100m: {t_50_100}s ({v_50_100}km/h) {fmt(t100)}s",
        f"• 100 a 150m: {t_100_150}s ({v_100_150}km/h) {fmt(t150)}s",
        f"• 150 a 200m: {t_150_200}s ({v_150_200}km/h) {fmt(test_time)}s",
        "",
        "📊 *Velocidad*",
        f"• Media: {fmt(m.velocidad_media)}km/h ({vel_media_ms:.2f} m/s)",
        f"• Maxima: {fmt(m.velocidad_maxima)}km/h",
        f"• Minima: {fmt(m.velocidad_min_post10)}km/h (sin 15 primeras)",
        f"• Acel maxima: {fmt(m.aceleracion_max, 3)}m/s2 ({acel_g:.3f} G)",
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
