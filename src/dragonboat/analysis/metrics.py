"""Metric computation — adapted from dragonboat_analyzer.py lines 270-356."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from dragonboat.config import settings
from dragonboat.models import Metricas, PaladasInfo


def calcular_pitch(
    gforce_x: np.ndarray,
    gforce_z: np.ndarray,
    window: int = 25,
) -> np.ndarray:
    """Compute pitch angle from G-force data."""
    lp_x = pd.Series(gforce_x).rolling(window, center=True, min_periods=1).mean().values
    lp_z = pd.Series(gforce_z).rolling(window, center=True, min_periods=1).mean().values
    lp_z = np.clip(lp_z, 0.1, None)
    return np.degrees(np.arctan2(lp_x, lp_z))


def analizar_200m(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    paladas_info: PaladasInfo,
) -> Metricas | None:
    """Compute all metrics for a 200m segment.

    Returns Metricas or None if the segment is invalid.
    """
    segment = df.iloc[start_idx : end_idx + 1]
    speed = segment["speed_kmh"].values
    time = segment["elapsed_time"].values
    dist = segment["distance_m"].values

    start_dist = dist[0]
    start_time = time[0]

    target_dist = start_dist + settings.distancia_200m
    exact_idx = None
    for i in range(len(dist)):
        if dist[i] >= target_dist:
            exact_idx = i
            break

    if exact_idx is None or exact_idx < 1:
        return None

    d_prev, d_curr = dist[exact_idx - 1], dist[exact_idx]
    t_prev, t_curr = time[exact_idx - 1], time[exact_idx]
    frac = (target_dist - d_prev) / (d_curr - d_prev) if d_curr > d_prev else 0
    exact_time = t_prev + frac * (t_curr - t_prev)
    test_time = exact_time - start_time

    avg_speed_kmh = (settings.distancia_200m / test_time) * 3.6
    max_speed = float(np.max(speed))
    deriv = np.gradient(speed, time) / 3.6
    max_acc = float(np.max(deriv))

    # ── Helper: time to reach a speed ──
    def tiempo_hasta(valor, arr_t, arr_v, offset_v=0):
        for i in range(len(arr_v)):
            if arr_v[i] >= valor:
                if i > 0 and arr_v[i] > arr_v[i - 1]:
                    f = (valor - arr_v[i - 1]) / (arr_v[i] - arr_v[i - 1])
                    return arr_t[i - 1] + f * (arr_t[i] - arr_t[i - 1]) - offset_v
                return arr_t[i] - offset_v
        return None

    # ── Helper: time to reach a distance ──
    def tiempo_distancia(d_target, arr_t, arr_d, offset_t=0):
        for i in range(len(arr_d)):
            if arr_d[i] >= d_target:
                if i > 0 and arr_d[i] > arr_d[i - 1]:
                    f = (d_target - arr_d[i - 1]) / (arr_d[i] - arr_d[i - 1])
                    return arr_t[i - 1] + f * (arr_t[i] - arr_t[i - 1]) - offset_t
                return arr_t[i] - offset_t
        return None

    t_11 = tiempo_hasta(11.0, time, speed, start_time)
    t_12 = tiempo_hasta(12.0, time, speed, start_time)
    t_50 = tiempo_distancia(start_dist + 50.0, time, dist, start_time)
    t_100 = tiempo_distancia(start_dist + 100.0, time, dist, start_time)
    t_150 = tiempo_distancia(start_dist + 150.0, time, dist, start_time)
    last_50_time = test_time - t_150 if t_150 is not None else None

    avg_last_50 = None
    if t_150 is not None and test_time > t_150:
        avg_last_50 = (50.0 / (test_time - t_150)) * 3.6

    dist_media = float(np.mean(paladas_info.dist_por_palada)) if paladas_info.dist_por_palada else 0.0
    dist_std = float(np.std(paladas_info.dist_por_palada)) if len(paladas_info.dist_por_palada) > 1 else 0.0
    dist_max = float(np.max(paladas_info.dist_por_palada)) if paladas_info.dist_por_palada else None
    dist_min = float(np.min(paladas_info.dist_por_palada)) if paladas_info.dist_por_palada else None

    # Min speed after first 15 strokes
    smoothed = (
        pd.Series(speed)
        .rolling(2, center=True, min_periods=1)
        .mean()
        .values
    )
    valleys, _ = find_peaks(
        -smoothed,
        distance=settings.stroke_min_dist,
        prominence=settings.stroke_prominence,
    )
    if len(valleys) >= 15:
        speed_min_post10 = float(np.min(speed[valleys[9] :]))
    else:
        speed_min_post10 = max_speed

    return Metricas(
        tiempo_total=test_time,
        velocidad_media=avg_speed_kmh,
        velocidad_maxima=max_speed,
        velocidad_min_post10=speed_min_post10,
        aceleracion_max=max_acc,
        tiempo_11kmh=t_11,
        tiempo_12kmh=t_12,
        tiempo_150m=t_150,
        tiempo_50m=t_50,
        tiempo_100m=t_100,
        tiempo_ultimos_50m=last_50_time,
        vel_media_ultimos_50m=avg_last_50,
        num_paladas=paladas_info.num_paladas,
        dist_media_palada=dist_media,
        dist_std_palada=dist_std,
        dist_max_palada=dist_max,
        dist_min_palada=dist_min,
        start_idx=int(start_idx),
        end_idx=int(end_idx),
        start_time=start_time,
        exact_time=exact_time,
    )
