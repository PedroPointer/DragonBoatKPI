"""Shared utilities for the analysis package."""

from __future__ import annotations

from typing import Optional


def fmt(val: float | None, decimals: int = 2, suffix: str = "") -> str:
    """Format a numeric value with comma as decimal separator (Spanish style).

    Returns "N/A" for None. Examples:
        fmt(59.93)        -> "59,93"
        fmt(12.0123, 3)   -> "12,012"
        fmt(None)         -> "N/A"
    """
    if val is None:
        return "N/A"
    s = f"{val:.{decimals}f}{suffix}"
    return s.replace(".", ",")


def format_duration_short(seconds: float | None) -> str:
    """Format a time in seconds as MM:SS,CS (Spanish style, centésimas, sin horas).

    Útil para mostrar tiempos de sesión donde horas no son relevantes.
    Edge case: si rounding lleva cs a 100, carry-over correcto.

    Examples:
        format_duration_short(11.82)  -> "00:11,82"
        format_duration_short(60.0)   -> "01:00,00"
        format_duration_short(3723.0) -> "62:03,00"
        format_duration_short(None)   -> "—"
    """
    if seconds is None or seconds < 0:
        return "—"
    total_cs = int(round(seconds * 100))
    total_minutes = total_cs // (60 * 100)
    remaining_cs = total_cs % (60 * 100)
    s, cs = divmod(remaining_cs, 100)
    return f"{total_minutes:02d}:{s:02d},{cs:02d}"


def format_duration(seconds: float | None) -> str:
    """Format a time in seconds as HH:MM:SS,MM (Spanish style, 2 centésimas).

    Returns "—" for None / negative. Edge case: if rounding pushes cs to 100
    (e.g., 59.996s), it correctly carries over to seconds/minutes/hours.

    Examples:
        format_duration(59.93)    -> "00:00:59,93"
        format_duration(60.0)     -> "00:01:00,00"
        format_duration(1500.0)   -> "00:25:00,00"
        format_duration(None)     -> "—"
    """
    if seconds is None or seconds < 0:
        return "—"
    total_cs = int(round(seconds * 100))
    h, rem = divmod(total_cs, 3600 * 100)
    m, rem = divmod(rem, 60 * 100)
    s, cs = divmod(rem, 100)
    return f"{h:02d}:{m:02d}:{s:02d},{cs:02d}"


def calcular_sectores(
    tiempos_por_distancia: dict[str, float],
    distancia: int,
) -> list[dict]:
    """Build the per-sector breakdown from cumulative marker times.

    Given accumulated times at D/4 markers (e.g. {"125": 44.25, "250": 84.87,
    "375": 126.64, "500": 168.39} for 500m), returns one dict per sector with
    segment time, accumulated time, and segment velocity in km/h.

    The first sector reports only t_sector and t_acum (equal). Each subsequent
    sector also shows velocity. Matches the layout used by `generar_informe_str`
    and the new test.html "Datos generales" view.

    Returns an empty list if markers are missing.
    """
    if not tiempos_por_distancia:
        return []
    step = distancia / 4.0
    keys: list[str] = [str(int(step * i)) for i in range(1, 5)]
    out: list[dict] = []
    for i, k in enumerate(keys):
        t = tiempos_por_distancia.get(k)
        if t is None:
            continue
        if i == 0:
            seg_t = t
            v = (step / seg_t) * 3.6 if seg_t > 0 else 0.0
            out.append({
                "from": 0,
                "to": int(step),
                "t_sector": round(seg_t, 2),
                "t_acum": round(t, 2),
                "vel": round(v, 2),
            })
        else:
            prev_key = keys[i - 1]
            prev_t = tiempos_por_distancia.get(prev_key)
            if prev_t is None:
                out.append({
                    "from": int((i) * step),
                    "to": int((i + 1) * step),
                    "t_sector": None,
                    "t_acum": round(t, 2),
                    "vel": None,
                })
                continue
            seg_t = t - prev_t
            v = (step / seg_t) * 3.6 if seg_t > 0 else 0.0
            out.append({
                "from": int(i * step),
                "to": int((i + 1) * step),
                "t_sector": round(seg_t, 2),
                "t_acum": round(t, 2),
                "vel": round(v, 2),
            })
    return out


def resumen_paladas(dist_por_palada: list[float] | None) -> dict:
    """Aggregate stroke distances for the report view.

    `dist_por_palada` is the per-gap distance list (len = num_paladas - 1,
    because it comes from np.diff). Returns the three values the report needs:
    - max_all: longest stroke overall
    - min_salida: shortest stroke overall (start, may be very low)
    - min_sin10: shortest stroke excluding the first 10
    Returns None/0 if input is empty.
    """
    if not dist_por_palada:
        return {
            "max_all": None,
            "min_salida": None,
            "min_sin10": None,
        }
    return {
        "max_all": max(dist_por_palada),
        "min_salida": min(dist_por_palada),
        "min_sin10": min(dist_por_palada[10:]) if len(dist_por_palada) > 10 else min(dist_por_palada),
    }


