"""Calm zone detection and first-stroke valley finding.

Adapted from dragonboat_analyzer.py lines 174-268.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from dragonboat.config import settings


def _fit_line_ssr(seg: np.ndarray) -> tuple[float, float]:
    """Fit y = a*x + b to *seg*. Return (slope, ssr)."""
    x = np.arange(len(seg), dtype=float)
    coeffs = np.polyfit(x, seg, 1)
    fitted = np.polyval(coeffs, x)
    ssr = float(np.sum((seg - fitted) ** 2))
    return float(coeffs[0]), ssr


def first_stroke_valley(
    df: pd.DataFrame,
    start_idx: int,
) -> tuple[int, int, int]:
    """Find the calm zone before *start_idx* and the valley of the first stroke.

    Returns (valley_idx, calm_start, calm_end).
    """
    speed = df["speed_kmh"].values
    n = len(speed)
    w = settings.calm_window

    calm_start, calm_end = start_idx, start_idx

    # ── Step 1: scan backwards for a calm window ──
    lo = max(w, start_idx - settings.calm_scan_back)
    for i in range(start_idx, lo, -1):
        if i - w < 0:
            break
        seg = speed[i - w : i]
        slope, ssr = _fit_line_ssr(seg)
        if abs(slope) < settings.calm_max_slope and ssr < settings.calm_max_ssr:
            calm_start = i - w
            calm_end = i
            break

    # ── Step 2: find where speed departs from calm baseline ──
    if calm_end <= calm_start:
        print(f"    [CALMA] start={start_idx} NO calm found")
        return start_idx, start_idx, start_idx

    calm_len = calm_end - calm_start
    half = calm_len // 2
    baseline = float(np.mean(speed[calm_start : calm_start + half]))
    calm_noise = float(np.std(speed[calm_start : calm_start + half]))

    departure_threshold = max(
        0.5 if baseline < 3.0 else 1.0,
        4.0 * calm_noise,
    )

    catch_idx = None
    search_end = min(calm_end + 100, n)
    for j in range(calm_start, search_end):
        if speed[j] - baseline > departure_threshold:
            peak_rel = int(np.argmax(speed[j : min(j + 30, n)]))
            peak_idx = j + peak_rel
            if (
                peak_idx + 10 < n
                and speed[peak_idx] - speed[peak_idx + 10] > settings.stroke_decel_drop
            ):
                catch_idx = j
                break

    # ── Step 3: valley = min in 5 samples before catch ──
    if catch_idx is not None:
        lookback = max(calm_start, catch_idx - 5)
        valley = lookback + int(np.argmin(speed[lookback : catch_idx + 1]))
    else:
        valley = calm_end

    # ── Step 4: skip GPS gaps ──
    dt_arr = np.diff(df["elapsed_time"].values)
    for g in range(valley, min(valley + 5, len(dt_arr))):
        if dt_arr[g] > 0.5:
            post_gap = g + 1
            post_end = min(post_gap + 5, n)
            valley = post_gap + int(np.argmin(speed[post_gap : post_end]))
            break

    slope_str = f"{slope:.4f}" if calm_end > calm_start else "N/A"
    # print(
    #     f"    [CALMA] start={start_idx} calm=[{calm_start},{calm_end}] "
    #     f"len={calm_end - calm_start} pend={slope_str} ssr={ssr:.3f} "
    #     f"baseline={baseline:.2f} noise={calm_noise:.3f} dep_thr={departure_threshold:.2f} "
    #     f"catch={catch_idx} valley={valley}"
    # )

    return valley, calm_start, calm_end
