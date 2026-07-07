"""Multi-distance segment detection.

Adapted from dragonboat_analyzer.py lines 87-142. Detects training runs
at any of the standard distances (200/500/1000/2000m).

Algorithm:
1. Find start (acceleration peak → calm zone → first-stroke valley).
2. For each candidate D in [2000, 1000, 500, 200] (longest first):
   a. Compute target_idx at dist[valley] + D.
   b. Validate speed in [valley, target_idx+1]:
      - 200/500/1000: mean speed > 10 km/h
      - 2000:         min speed > 8 km/h (instantaneous, since mean may dip)
   c. The first D that passes is the test distance.
3. If no D passes, discard the start.
4. Deduplicate nearby starts.

The "decel" is implicit: if the boat decelerated before D, the mean speed
over [valley, valley+D] would drop below the threshold. So the speed check
is equivalent to "decel happened after D".
"""

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


def _classify_distance(
    speed: np.ndarray,
    dist: np.ndarray,
    valley_idx: int,
    n: int,
) -> int | None:
    """Pick the largest valid distance D such that the test segment
    [valley, valley+D] passes the speed validation.

    Returns None if no D qualifies.
    """
    for D in sorted(settings.distancias_validas, reverse=True):
        target_dist = dist[valley_idx] + D
        target_idx = int(np.searchsorted(dist, target_dist))
        if target_idx >= n or target_idx <= valley_idx + 50:
            continue
        seg = speed[valley_idx : target_idx + 1]
        if D == 2000:
            if float(np.min(seg)) > settings.umbral_velocidad_instantanea_2000:
                return D
        else:
            if float(np.mean(seg)) > 10.0:
                return D
    return None


def detectar_tramos(df: pd.DataFrame) -> list[TramoDetectado]:
    """Detect all training segments (200/500/1000/2000m) in the dataframe."""
    speed = df["speed_kmh"].values
    dist = df["distance_m"].values
    n = len(df)

    raw_tramos: list[tuple[int, int, int, int, int]] = []

    for start_raw in _find_starts_gradient(speed):
        valley, c_s, c_e = first_stroke_valley(df, start_raw)
        if valley is None or valley >= n - 200:
            continue

        distancia = _classify_distance(speed, dist, valley, n)
        if distancia is None:
            continue

        target_idx = int(np.searchsorted(dist, dist[valley] + distancia))
        raw_tramos.append((int(valley), target_idx, distancia, c_s, c_e))

    # Deduplicate: if two starts are < 200 samples apart, keep the longer distancia
    raw_tramos.sort(key=lambda t: t[0])
    unicos: list[tuple[int, int, int, int, int]] = []
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
            distancia=t[2],
        )
        for t in unicos
    ]


# ── Back-compat alias (legacy callers) ──
def detectar_200m(df: pd.DataFrame) -> list[TramoDetectado]:
    """Legacy entrypoint. Equivalent to detectar_tramos(); kept for back-compat."""
    return detectar_tramos(df)
