"""CSV data loading — RaceBox Drag.

Funciones:
  - cargar_csv()        → DataFrame procesado
  - extraer_metadata_date() → fecha del header del CSV
  - build_gps_data_json()   → JSON 25Hz completo de un tramo
  - build_gps_inicio_fin()  → {lat, lon, t} del primer y último punto
  - downsample_5hz()        → puntos decimados para mapa
"""

from __future__ import annotations

import re
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from dragonboat.analysis.strokes import detectar_picos
from dragonboat.config import settings


# ── Metadata extraction ──

_METADATA_PATTERNS = [
    re.compile(r"date\s*[:=]\s*([0-9/: \-T]+)", re.IGNORECASE),
    re.compile(r"fecha\s*[:=]\s*([0-9/: \-T]+)", re.IGNORECASE),
    re.compile(r"start time\s*[:=]\s*([0-9/: \-T]+)", re.IGNORECASE),
    re.compile(r"recorded\s*[:=]\s*([0-9/: \-T]+)", re.IGNORECASE),
]


def extraer_metadata_date(path: str) -> datetime | None:
    """Lee las primeras líneas del CSV buscando una fecha en los metadatos.

    RaceBox Drag guarda algo como 'Date: 2026-07-20 10:30:15' antes de la
    cabecera de datos. Si no se encuentra, devuelve None.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                if line.startswith("Record,") or line.startswith("timestamp,"):
                    break
                for pat in _METADATA_PATTERNS:
                    m = pat.search(line)
                    if m:
                        raw = m.group(1).strip()
                        for fmt in (
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%d",
                            "%d/%m/%Y %H:%M:%S",
                            "%d/%m/%Y",
                            "%d-%m-%Y %H:%M:%S",
                        ):
                            try:
                                return datetime.strptime(raw, fmt)
                            except ValueError:
                                continue
    except OSError:
        return None
    return None


# ── CSV loading ──

def cargar_csv(path: str) -> pd.DataFrame:
    """Carga un CSV de RaceBox Drag, normaliza columnas y deriva velocidad/distancia."""
    with open(path, "r", encoding="utf-8") as f:
        header_line = ""
        skip_rows = 0
        for i, line in enumerate(f):
            if line.startswith("Record,Time") or line.startswith("timestamp,"):
                header_line = line
                skip_rows = i
                break

    df = pd.read_csv(path, skiprows=skip_rows)
    df["Time"] = pd.to_datetime(df["Time"])
    df["elapsed_time"] = (df["Time"] - df["Time"].iloc[0]).dt.total_seconds()
    df["speed_kmh"] = pd.to_numeric(df["Speed"], errors="coerce")
    df["lean_angle"] = pd.to_numeric(df["LeanAngle"], errors="coerce")
    df["gforce_x"] = pd.to_numeric(df["GForceX"], errors="coerce")
    df["gforce_z"] = pd.to_numeric(df["GForceZ"], errors="coerce")
    df["lat"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["lon"] = pd.to_numeric(df["Longitude"], errors="coerce")

    dt = df["elapsed_time"].diff().fillna(0)
    df["distance_m"] = ((df["speed_kmh"] / 3.6) * dt).cumsum()

    return df.dropna(subset=["speed_kmh", "elapsed_time"]).reset_index(drop=True)


# ── GPS segment JSON ──

def build_gps_data_json(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    paladas_info,
    m,
) -> dict:
    """JSON 25Hz completo de un tramo: time, speed, lean, gforce, lat, lon, peaks, valleys."""
    time_offset = m.start_time
    segment = df.iloc[start_idx : end_idx + 1]
    rel_time = (segment["elapsed_time"].values - time_offset)

    peaks_abs = detectar_picos(df, start_idx, end_idx)
    peak_times: list[float] = []
    peak_speeds: list[float] = []
    for p in peaks_abs:
        t_p = float(df["elapsed_time"].iloc[p] - time_offset)
        if 0 < t_p < m.tiempo_total:
            peak_times.append(t_p)
            peak_speeds.append(float(df["speed_kmh"].iloc[p]))

    speed = segment["speed_kmh"].values
    smoothed = pd.Series(speed).rolling(3, center=True, min_periods=1).mean().values
    valleys_idx, _ = find_peaks(
        -smoothed,
        distance=settings.stroke_min_dist,
        prominence=settings.stroke_prominence,
    )
    valley_times: list[float] = [
        float(rel_time[v])
        for v in valleys_idx
        if 0 < float(rel_time[v]) < m.tiempo_total
    ]

    return {
        "time": [float(t) for t in rel_time],
        "speed": [float(s) for s in segment["speed_kmh"].values],
        "lean": [float(l) for l in segment["lean_angle"].values],
        "gforce_x": [float(g) for g in segment["gforce_x"].values],
        "gforce_z": [float(g) for g in segment["gforce_z"].values],
        "lat": [float(l) for l in segment["lat"].values],
        "lon": [float(l) for l in segment["lon"].values],
        "peak_times": peak_times,
        "peak_speeds": peak_speeds,
        "valley_times": valley_times,
        "dist_por_palada": paladas_info.dist_por_palada,
    }


def build_gps_inicio_fin(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    time_offset: float = 0.0,
) -> tuple[dict, dict]:
    """Devuelve (gps_inicio, gps_fin) como dicts {lat, lon, t}.

    Útil para mostrar puntos de inicio/fin en el mapa sin cargar el GPS completo.
    """
    segment = df.iloc[start_idx : end_idx + 1]
    if segment.empty or "lat" not in segment.columns:
        return ({"lat": None, "lon": None, "t": 0.0}, {"lat": None, "lon": None, "t": 0.0})

    t0 = float(segment["elapsed_time"].iloc[0])
    t_end = float(segment["elapsed_time"].iloc[-1])

    lat_first = float(segment["lat"].iloc[0]) if pd.notna(segment["lat"].iloc[0]) else None
    lon_first = float(segment["lon"].iloc[0]) if pd.notna(segment["lon"].iloc[0]) else None
    lat_last = float(segment["lat"].iloc[-1]) if pd.notna(segment["lat"].iloc[-1]) else None
    lon_last = float(segment["lon"].iloc[-1]) if pd.notna(segment["lon"].iloc[-1]) else None

    return (
        {"lat": lat_first, "lon": lon_first, "t": round(t0 - time_offset, 3)},
        {"lat": lat_last, "lon": lon_last, "t": round(t_end - time_offset, 3)},
    )


# ── Decimation for map ──

def downsample_5hz(
    df_segment: pd.DataFrame,
    start_time: float | None = None,
) -> list[tuple[float, float, float]]:
    if df_segment.empty or "lat" not in df_segment.columns:
        return []
    lat_clean = df_segment.dropna(subset=["lat", "lon"])
    if lat_clean.empty:
        return []

    t0 = lat_clean["elapsed_time"].iloc[0]
    t_end = lat_clean["elapsed_time"].iloc[-1]
    targets = np.arange(t0, t_end + 0.001, 0.2)

    out: list[tuple[float, float, float]] = []
    for tg in targets:
        idx = (lat_clean["elapsed_time"] - tg).abs().idxmin()
        row = lat_clean.loc[idx]
        out.append((
            float(row["elapsed_time"] - t0),
            float(row["lat"]),
            float(row["lon"]),
        ))
    return out


def get_trajectory(gps_data_json: str) -> list[list[float]]:
    """Decimate GPS points to ~5Hz. Returns [[lat, lon, speed], ...]."""
    import json
    try:
        data = json.loads(gps_data_json)
    except (ValueError, TypeError):
        return []
    lats = data.get("lat", [])
    lons = data.get("lon", [])
    speeds = data.get("speed", [])
    if not lats or not lons:
        return []
    step = 5
    n = min(len(lats), len(lons))
    if speeds:
        n = min(n, len(speeds))
    out: list[list[float]] = []
    for i in range(0, n, step):
        lat = lats[i]
        lon = lons[i]
        spd = float(speeds[i]) if speeds and i < len(speeds) else 0.0
        if lat is not None and lon is not None:
            out.append([float(lat), float(lon), spd])
    return out


def classify_gps_segments(
    gps_data: dict,
    threshold: float = 5.0,
    decimate_step: int = 5,
) -> list[dict]:
    """Decima a 5Hz y agrupa samples consecutivos en segmentos por estado.

    Devuelve [{points: [[lat, lon], ...], status: "moving"|"stopped"}, ...]

    - speed >= threshold → "moving" (verde en UI)
    - speed < threshold  → "stopped" (rojo en UI)
    - Samples sin lat/lon se descartan.
    """
    lats = gps_data.get("lat", [])
    lons = gps_data.get("lon", [])
    speeds = gps_data.get("speed", [])
    if not lats or not lons:
        return []

    segments: list[dict] = []
    current_status: str | None = None
    current_points: list[list[float]] = []

    for i in range(0, len(lats), decimate_step):
        lat = lats[i]
        lon = lons[i]
        if lat is None or lon is None:
            continue
        s_kmh = speeds[i] if i < len(speeds) else 0.0
        status = "moving" if s_kmh >= threshold else "stopped"
        if status != current_status and current_points:
            segments.append({"points": current_points, "status": current_status})
            current_points = []
        current_status = status
        current_points.append([float(lat), float(lon)])

    if current_points:
        segments.append({"points": current_points, "status": current_status})

    return segments
