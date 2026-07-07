"""Shared utilities for the analysis package."""

from __future__ import annotations


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
