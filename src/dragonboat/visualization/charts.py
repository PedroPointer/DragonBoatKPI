"""Chart generation — adapted from dragonboat_analyzer.py graficar_200m()."""

from __future__ import annotations

import os  # noqa: F401  (kept for future use)
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.signal import find_peaks

from dragonboat.analysis._utils import fmt, format_duration
from dragonboat.analysis.strokes import detectar_picos
from dragonboat.config import settings
from dragonboat.models import Metricas, PaladasInfo


def graficar_200m(
    df: pd.DataFrame,
    m: Metricas,
    paladas_info: PaladasInfo,
    output_dir: str | Path,
    nombre: str,
) -> str:
    """Generate the 4-panel chart for a 200m test.

    Returns the full path to the saved PNG.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    num_paladas = paladas_info.num_paladas
    dist_por_palada = paladas_info.dist_por_palada

    PADDING_L = 1.0
    PADDING_R = 1.0
    pad_samples = int(PADDING_L * 25)
    pad_start = max(m.start_idx - pad_samples, 0)

    segment = df.iloc[pad_start : m.end_idx + 1].copy()
    time = segment["elapsed_time"].values
    speed = segment["speed_kmh"].values
    lean = segment["lean_angle"].values
    gf_x = segment["gforce_x"].values
    gf_z = segment["gforce_z"].values
    rel_time = time - m.start_time
    test_time = m.tiempo_total

    from datetime import datetime, timedelta

    start_dt = datetime.fromtimestamp(m.start_time) if m.start_time > 1e9 else datetime.now()
    hora_str = start_dt.strftime("%H:%M:%S")
    fecha_str = start_dt.strftime("%d/%m/%Y")

    plt.rcParams["font.family"] = "Segoe UI"
    plt.rcParams["font.size"] = 10

    fig = plt.figure(figsize=(14, 12), constrained_layout=True)
    gs = fig.add_gridspec(4, 1, height_ratios=[2, 1, 1, 1], hspace=0.12)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax4 = fig.add_subplot(gs[3], sharex=ax1)

    fig.suptitle(
        f"{m.distancia} Metros - {hora_str} - {fecha_str} - {format_duration(m.tiempo_total)}",
        fontsize=14,
        fontweight="bold",
    )

    # ── Panel 1: Speed ──
    _pts = np.array([rel_time, speed]).T.reshape(-1, 1, 2)
    _segs = np.concatenate([_pts[:-1], _pts[1:]], axis=1)
    _accel = np.gradient(speed, rel_time)
    _seg_accel = (_accel[:-1] + _accel[1:]) / 2.0
    _seg_colors = ["#27ae60" if a > 0 else "#e74c3c" for a in _seg_accel]
    ax1.add_collection(
        LineCollection(_segs, colors=_seg_colors, linewidths=2.2, alpha=0.9)
    )
    ax1.set_xlim(-PADDING_L, test_time + PADDING_R)
    ax1.set_ylim(max(0, speed.min() - 1.5), speed.max() + 2.5)
    ax1.set_ylabel("Velocidad (km/h)", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.set_title("Velocidad", fontsize=12, fontweight="bold")

    # Calm zone debug
    if m.calm_start is not None and m.calm_end is not None:
        cs = max(0, m.calm_start - pad_start)
        ce = max(0, m.calm_end - pad_start)
        ce = min(ce, len(time) - 1)
        if cs < len(time):
            cs_rel = time[cs] - m.start_time
            ce_rel = time[ce] - m.start_time
            ax1.axvspan(cs_rel, ce_rel, alpha=0.2, color="red", zorder=1)

    ax1.axvline(x=0, color="#999", ls="-", lw=1.5, alpha=0.6, zorder=5)
    ax1.axhline(y=m.velocidad_media, color="#3498db", ls="--", lw=1.5, alpha=0.7)
    ax1.annotate(
        f"{m.velocidad_media:.2f} km/h",
        xy=(0, m.velocidad_media),
        xytext=(6, 6),
        textcoords="offset points",
        fontsize=9,
        color="#3498db",
        fontweight="bold",
        ha="left",
        va="bottom",
    )

    if m.tiempo_150m is not None:
        ax1.annotate(
            f"150m\n{format_duration(m.tiempo_150m)}",
            xy=(m.tiempo_150m, np.interp(m.tiempo_150m, rel_time, speed)),
            xytext=(m.tiempo_150m - 2, m.velocidad_maxima * 0.60),
            fontsize=8,
            ha="center",
            va="bottom",
            color="#f39c12",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f39c12", alpha=0.85),
        )

    # Intermediate markers (D/4, 2D/4, 3D/4) — secondary, in grey
    keys = sorted(m.tiempos_por_distancia.keys(), key=lambda k: int(k))
    if len(keys) >= 2:
        # Show the second-to-last (penultimate) marker in orange
        if m.distancia != 200 and len(keys) >= 2:
            penult_key = keys[-2]
            t_penult = m.tiempos_por_distancia[penult_key]
            ax1.annotate(
                f"{penult_key}m\n{format_duration(t_penult)}",
                xy=(t_penult, np.interp(t_penult, rel_time, speed)),
                xytext=(t_penult, m.velocidad_maxima * 0.60),
                fontsize=8,
                ha="center",
                va="bottom",
                color="#f39c12",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f39c12", alpha=0.85),
            )
        # First marker (D/4) in grey
        first_key = keys[0]
        t_first = m.tiempos_por_distancia[first_key]
        ax1.annotate(
            f"{first_key}m\n{format_duration(t_first)}",
            xy=(t_first, np.interp(t_first, rel_time, speed)),
            xytext=(t_first, m.velocidad_maxima * 0.45),
            fontsize=7,
            ha="center",
            color="#555",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888", alpha=0.85),
        )
        # Second marker (D/2) in grey, only if distance >= 500
        if len(keys) >= 3 and m.distancia >= 500:
            mid_key = keys[1]
            t_mid = m.tiempos_por_distancia[mid_key]
            ax1.annotate(
                f"{mid_key}m\n{format_duration(t_mid)}",
                xy=(t_mid, np.interp(t_mid, rel_time, speed)),
                xytext=(t_mid, m.velocidad_maxima * 0.55),
                fontsize=7,
                ha="center",
                color="#555",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888", alpha=0.85),
            )

    if m.tiempo_12kmh is not None:
        ax1.axvspan(0, m.tiempo_12kmh, alpha=0.08, color="#f39c12", zorder=0)
        ax1.text(
            m.tiempo_12kmh / 2,
            m.velocidad_maxima * 0.92,
            f"0-12 km/h: {format_duration(m.tiempo_12kmh)}",
            fontsize=9,
            ha="center",
            va="bottom",
            color="#7a5c00",
            fontweight="bold",
            alpha=0.75,
        )

    if m.tiempo_150m is not None:
        ax1.axvspan(m.tiempo_150m, test_time, alpha=0.06, color="#e74c3c", zorder=0)

    std_str = fmt(m.dist_std_palada, 2) if m.dist_std_palada > 0 else "N/A"
    stats = (
        "Vel. max:         {} km/h   \n"
        "Vel. media:       {} km/h   \n"
        "0-12 km/h:        {}        \n"
        "Paladas totales:  {}        \n"
        "Distancia Palada: {} m/pal\n"
        "Consistencia(std): {} m     "
    ).format(
        fmt(m.velocidad_maxima, 1),
        fmt(m.velocidad_media, 2),
        format_duration(m.tiempo_12kmh),
        m.num_paladas,
        fmt(m.dist_media_palada),
        std_str,
    )

    props = dict(boxstyle="round,pad=0.6", facecolor="#f8f8f8", edgecolor="#333", alpha=0.92)
    ax1.text(
        0.60,
        0.43,
        f"Tiempo {m.distancia}m:  {format_duration(m.tiempo_total)}",
        transform=ax1.transAxes,
        fontsize=14,
        fontweight="bold",
        ha="right",
        va="top",
        color="#c0392b",
    )
    ax1.text(
        0.95,
        0.41,
        stats,
        transform=ax1.transAxes,
        fontsize=12,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=props,
        fontfamily="Consolas",
    )

    # Peaks and valleys
    peaks_abs = detectar_picos(df, m.start_idx, m.end_idx)
    peak_times = []
    peak_speeds = []
    for p in peaks_abs:
        t_p = df["elapsed_time"].iloc[p] - m.start_time
        if 0 < t_p < test_time:
            peak_times.append(t_p)
            peak_speeds.append(df["speed_kmh"].iloc[p])

    for i, (t_p, s_p) in enumerate(zip(peak_times, peak_speeds)):
        ax1.annotate(
            str(i + 1),
            (t_p, s_p),
            xytext=(0, 7),
            textcoords="offset points",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#1a1a1a",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#666", alpha=0.9),
        )

    _sm = pd.Series(speed).rolling(3, center=True, min_periods=1).mean().values
    _valleys, _ = find_peaks(
        -_sm, distance=settings.stroke_min_dist, prominence=settings.stroke_prominence
    )
    for v in _valleys:
        t_v = rel_time[v]
        if 0 < t_v < test_time:
            ax1.plot(
                t_v, speed[v], "o", color="#2980b9", markersize=3.0, alpha=0.45, zorder=6
            )

    ax1.legend(
        handles=[
            Line2D([0], [0], color="#27ae60", lw=2.4, label="Acelera"),
            Line2D([0], [0], color="#e74c3c", lw=2.4, label="Frena"),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="#2980b9",
                markersize=6,
                label="Catch (valle)",
            ),
        ],
        loc="lower center",
        fontsize=9,
        framealpha=0.85,
    )

    # Vertical lines for peaks across all panels
    for t in peak_times:
        for ax in (ax2, ax3, ax4):
            ax.axvline(x=t, color="gray", ls=":", alpha=0.28, lw=0.6)

    dist_times: list[tuple[float, str]] = []
    keys = sorted(m.tiempos_por_distancia.keys(), key=lambda k: int(k))
    for i, k in enumerate(keys):
        t = m.tiempos_por_distancia.get(k)
        if t is None:
            continue
        if i == len(keys) - 1:
            color = "#e74c3c"
        elif i == len(keys) - 2:
            color = "#f39c12"
        else:
            color = "#888"
        dist_times.append((t, color))
    for ax in (ax1, ax2, ax3, ax4):
        for t_val, c in dist_times:
            if t_val is not None and 0 < t_val < test_time:
                ax.axvline(x=t_val, color=c, ls="--", alpha=0.4, lw=1.0)

    # ── Panel 2: Roll ──
    num_bars = min(80, len(rel_time))
    step = max(1, len(rel_time) // num_bars)
    t_bins = rel_time[::step]
    roll_bins = lean[::step]
    colors_roll = []
    for v in roll_bins:
        if abs(v) > settings.roll_alert_deg:
            colors_roll.append("#c0392b")
        elif v >= 0:
            colors_roll.append("#D2691E")
        else:
            colors_roll.append("#FFB347")

    ax2.bar(
        t_bins,
        roll_bins,
        width=step * np.mean(np.diff(rel_time)) * 0.8,
        color=colors_roll,
        alpha=0.85,
        edgecolor="none",
    )
    ax2.axhline(y=0, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax2.axvline(x=0, color="#999", ls="-", lw=1.5, alpha=0.6, zorder=5)
    ax2.set_ylabel("Roll (Balanceo) (deg)", fontsize=12)
    ax2.set_xlim(-PADDING_L, test_time + PADDING_R)
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.set_title("Balanceo (Roll)", fontsize=12, fontweight="bold")
    ax2.legend(
        handles=[
            Patch(color="#D2691E", label="Estribor"),
            Patch(color="#FFB347", label="Babor"),
            Patch(color="#c0392b", label=f"Inestable (>{settings.roll_alert_deg:.0f} deg)"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        fontsize=9,
    )

    # ── Panel 3: Pitch ──
    from dragonboat.analysis.metrics import calcular_pitch

    pitch = calcular_pitch(gf_x, gf_z)
    pitch_bins = pitch[::step]
    colors_pitch = ["#6a9ad8" if v > 0 else "#1a3a8a" for v in pitch_bins]

    ax3.bar(
        t_bins,
        pitch_bins,
        width=step * np.mean(np.diff(rel_time)) * 0.8,
        color=colors_pitch,
        alpha=0.85,
        edgecolor="none",
    )
    ax3.axhline(y=0, color="gray", ls="--", lw=0.8, alpha=0.5)
    ax3.axvline(x=0, color="#999", ls="-", lw=1.5, alpha=0.6, zorder=5)
    ax3.set_ylabel("Cabeceo (deg)", fontsize=12)
    ax3.set_xlim(-PADDING_L, test_time + PADDING_R)
    ax3.grid(True, alpha=0.3, axis="y")
    ax3.set_title("Cabeceo (Pitch)", fontsize=12, fontweight="bold")
    ax3.legend(
        handles=[
            Patch(color="#1a3a8a", label="Popa"),
            Patch(color="#6a9ad8", label="Proa"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
        fontsize=10,
    )

    # ── Panel 4: Distance per stroke ──
    if dist_por_palada and len(peak_times) >= 2:
        n_bars = min(len(dist_por_palada), len(peak_times) - 1)
        mid_times = [(peak_times[i] + peak_times[i + 1]) / 2 for i in range(n_bars)]
        bar_heights = [dist_por_palada[i] for i in range(n_bars)]
        mean_d = m.dist_media_palada
        bar_colors = ["#2ecc71" if d >= mean_d else "#e74c3c" for d in bar_heights]
        mean_stroke_dur = (
            float(np.mean(np.diff(peak_times))) if len(peak_times) > 1 else 0.7
        )
        bar_w = mean_stroke_dur * 0.7
        ax4.bar(
            mid_times,
            bar_heights,
            width=bar_w,
            color=bar_colors,
            alpha=0.85,
            edgecolor="white",
            linewidth=0.5,
        )
        ax4.axhline(y=mean_d, color="#c0392b", ls="--", lw=1.5, alpha=0.85)
        ax4.annotate(
            f"{mean_d:.2f} m",
            xy=(0, mean_d),
            xytext=(6, 12),
            textcoords="offset points",
            fontsize=12,
            color="#c0392b",
            fontweight="bold",
            ha="left",
            va="top",
        )
        ax4.axvline(x=0, color="#999", ls="-", lw=1.5, alpha=0.6, zorder=5)
        ax4.set_ylabel("Dist. palada (m)", fontsize=12)
        ax4.set_xlabel("Tiempo (s)", fontsize=12)
        ax4.grid(True, alpha=0.3, axis="y")
        ax4.set_title("Distancia por palada", fontsize=11, fontweight="bold")
        for k, (xt, h) in enumerate(zip(mid_times, bar_heights)):
            ax4.annotate(
                str(k + 1),
                (xt, h),
                xytext=(0, 3),
                textcoords="offset points",
                fontsize=7,
                ha="center",
                va="bottom",
                color="#222",
                fontweight="bold",
            )
        i_best = int(np.argmax(bar_heights))
        ax4.plot(
            mid_times[i_best],
            bar_heights[i_best],
            marker="*",
            color="#f1c40f",
            markersize=14,
            zorder=7,
            markeredgecolor="#b8860b",
            markeredgewidth=0.8,
        )
    else:
        ax4.text(
            0.5,
            0.5,
            "No detectadas",
            transform=ax4.transAxes,
            ha="center",
            va="center",
            fontsize=11,
            color="gray",
        )
        ax4.set_xlabel("Tiempo (s)", fontsize=12)

    out_path = output_dir / f"{nombre}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Grafica guardada: {out_path}")
    return str(out_path)



