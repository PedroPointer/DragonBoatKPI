"""Shared utilities for the analysis package."""

from __future__ import annotations


def fmt(val: float | None, decimals: int = 2, suffix: str = "") -> str:
    """Format a numeric value for display, or 'N/A' if None."""
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"
