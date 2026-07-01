"""200m segment detection — adapted from dragonboat_analyzer.py lines 87-142."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dragonboat.config import settings
from dragonboat.analysis.calm import first_stroke_valley
from dragonboat.models import TramoDetectado


def _find_starts_gradient(
    speed: np.ndarray,
    min_speed: float | None = None,
):
    """Yield candidate start indices: local valley followed by strong acceleration."""
    if min_speed is None:
        min_speed = settings.min_speed_start
    n = len(speed)
    grad = np.gradient(speed)

    i = 1000  # skip first ~40s (warm-up / manoeuvres)
    while i < n - 200:
        if speed[i] < min_speed and speed[i] < speed[i - 5] and speed[i] < speed[i + 5]:
            if np.max(speed[max(0, i - 200) : i]) - speed[i] < 2.0:
                i += 1
                continue
            chunk = grad[i : i + 25]
            peak_grad = np.max(chunk)
            if peak_grad > 0.30:
                accel_rel = np.argmax(chunk > 0.15)
                accel_idx = i + accel_rel
                lo = max(0, i - 10)
                hi = min(accel_idx + 5, n)
                trough_rel = np.argmin(speed[lo:hi])
                start = lo + trough_rel
                if start < n:
                    yield start
                i = accel_idx + 150
                continue
        i += 1


def detectar_200m(df: pd.DataFrame) -> list[TramoDetectado]:
    """Detect all 200m segments in the dataframe.

    Returns a list of TramoDetectado with start/end indices and calm zone info.
    """
    speed = df["speed_kmh"].values
    dist = df["distance_m"].values
    n = len(df)

    raw_tramos: list[tuple[int, int, float, int, int]] = []

    for start_raw in _find_starts_gradient(speed):
        valley, c_s, c_e = first_stroke_valley(df, start_raw)
        target_dist = dist[valley] + settings.distancia_200m
        end_idx = int(np.searchsorted(dist, target_dist)) + 3
        if end_idx >= n:
            continue

        mean_sp = float(np.mean(speed[valley:end_idx]))
        if mean_sp > 10.0:
            raw_tramos.append((int(valley), end_idx, mean_sp, c_s, c_e))

    # Deduplicate: if two starts are < 200 samples apart, keep the one with higher mean_speed
    raw_tramos.sort(key=lambda t: t[0])
    unicos: list[tuple[int, int, float, int, int]] = []
    for t in raw_tramos:
        if unicos and abs(t[0] - unicos[-1][0]) < 200:
            if t[2] > unicos[-1][2]:
                unicos[-1] = t
        else:
            unicos.append(t)

    return [
        TramoDetectado(
            start_idx=t[0],
            end_idx=t[1],
            calm_start=t[3],
            calm_end=t[4],
        )
        for t in unicos
    ]
