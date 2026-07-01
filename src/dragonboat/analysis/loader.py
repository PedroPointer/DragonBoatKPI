"""CSV data loading — adapted from dragonboat_analyzer.py cargar_csv()."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from dragonboat.analysis.strokes import detectar_picos
from dragonboat.config import settings


def build_gps_data_json(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    paladas_info,
    m,
) -> dict:
    """Build the full 25Hz sensor JSON dict for a 200m segment.

    Returns dict with keys: time, speed, lean, gforce_x, gforce_z,
    lat, lon, peak_times, peak_speeds, valley_times, dist_por_palada.
    """
    time_offset = m.start_time
    segment = df.iloc[start_idx : end_idx + 1]
    rel_time = (segment["elapsed_time"].values - time_offset)

    # Peaks (from the full df/indices, original API)
    peaks_abs = detectar_picos(df, start_idx, end_idx)
    peak_times: list[float] = []
    peak_speeds: list[float] = []
    for p in peaks_abs:
        t_p = float(df["elapsed_time"].iloc[p] - time_offset)
        if 0 < t_p < m.tiempo_total:
            peak_times.append(t_p)
            peak_speeds.append(float(df["speed_kmh"].iloc[p]))

    # Valleys (from the segment)
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


def downsample_5hz(
    df_segment: pd.DataFrame,
    start_time: float | None = None,
) -> list[tuple[float, float, float]]:
    """Decimate GPS points to ~5Hz for map visualization.

    Returns list of (t_offset, lat, lon) — one sample every 0.2 s.
    If the segment has no valid lat/lon, returns empty list.
    """
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


def cargar_csv(path: str) -> pd.DataFrame:
    """Load a RaceBox Drag CSV and compute derived columns.

    Scans the file for the header line starting with 'Record,Time' or 'timestamp,',
    then loads from that row. Computes elapsed_time, speed_kmh, lean_angle,
    gforce_x, gforce_z, and cumulative distance_m.
    """
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
