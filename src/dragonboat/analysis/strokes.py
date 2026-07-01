"""Stroke (palada) detection — adapted from dragonboat_analyzer.py lines 144-171."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from dragonboat.config import settings
from dragonboat.models import PaladasInfo


def detectar_picos(df: pd.DataFrame, start_idx: int, end_idx: int) -> np.ndarray:
    """Return ABSOLUTE indices of speed peaks detected in the segment."""
    segment = df.iloc[start_idx : end_idx + 1]
    speed = segment["speed_kmh"].values
    smoothed = (
        pd.Series(speed)
        .rolling(3, center=True, min_periods=1)
        .mean()
        .values
    )
    peaks, _ = find_peaks(
        smoothed,
        distance=settings.stroke_min_dist,
        prominence=settings.stroke_prominence,
    )
    valid = [start_idx + p for p in peaks if 0 < p < len(speed) - 1]
    return np.array(valid, dtype=int)


def detectar_paladas(df: pd.DataFrame, start_idx: int, end_idx: int) -> PaladasInfo:
    """Detect strokes in the 200m segment.

    Returns PaladasInfo with count and per-stroke distances.
    """
    segment = df.iloc[start_idx : end_idx + 1]
    speed = segment["speed_kmh"].values
    dist = segment["distance_m"].values

    smoothed = (
        pd.Series(speed)
        .rolling(3, center=True, min_periods=1)
        .mean()
        .values
    )
    peaks, _ = find_peaks(
        smoothed,
        distance=settings.stroke_min_dist,
        prominence=settings.stroke_prominence,
    )

    valid_peaks = [start_idx + p for p in peaks if 0 < p < len(speed) - 1]

    if len(valid_peaks) < 2:
        return PaladasInfo(num_paladas=len(valid_peaks), dist_por_palada=[])

    abs_positions = np.array([dist[p - start_idx] for p in valid_peaks])
    dist_entre_paladas = np.diff(abs_positions)
    return PaladasInfo(
        num_paladas=len(valid_peaks),
        dist_por_palada=dist_entre_paladas.tolist(),
    )
