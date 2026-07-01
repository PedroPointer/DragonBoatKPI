"""Chart generation — adapted from dragonboat_analyzer.py graficar_200m()."""

from __future__ import annotations

import os
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

from dragonboat.analysis._utils import fmt
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
        f"200 Metros - {hora_str} - {fecha_str} - {m.tiempo_total:.2f}s",
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
            f"150m\n{m.tiempo_150m:.1f}s",
            xy=(m.tiempo_150m, np.interp(m.tiempo_150m, rel_time, speed)),
            xytext=(m.tiempo_150m - 2, m.velocidad_maxima * 0.60),
            fontsize=8,
            ha="center",
            va="bottom",
            color="#f39c12",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f39c12", alpha=0.85),
        )

    if m.tiempo_50m is not None:
        ax1.annotate(
            f"50m\n{m.tiempo_50m:.1f}s",
            xy=(m.tiempo_50m, np.interp(m.tiempo_50m, rel_time, speed)),
            xytext=(m.tiempo_50m, m.velocidad_maxima * 0.45),
            fontsize=7,
            ha="center",
            color="#555",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#888", alpha=0.85),
        )
    if m.tiempo_100m is not None:
        ax1.annotate(
            f"100m\n{m.tiempo_100m:.1f}s",
            xy=(m.tiempo_100m, np.interp(m.tiempo_100m, rel_time, speed)),
            xytext=(m.tiempo_100m, m.velocidad_maxima * 0.55),
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
            f"0-12 km/h: {m.tiempo_12kmh:.2f}s",
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
        "Distancia Palada: {:.2f} m/pal\n"
        "Consistencia(std): {} m     "
    ).format(
        fmt(m.velocidad_maxima, 1),
        fmt(m.velocidad_media, 2),
        fmt(m.tiempo_12kmh),
        m.num_paladas,
        m.dist_media_palada,
        std_str,
    )

    props = dict(boxstyle="round,pad=0.6", facecolor="#f8f8f8", edgecolor="#333", alpha=0.92)
    ax1.text(
        0.60,
        0.43,
        f"Tiempo 200m:  {fmt(m.tiempo_total)} s",
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

    dist_times = [
        (m.tiempo_50m, "#888"),
        (m.tiempo_100m, "#888"),
        (m.tiempo_150m, "#f39c12"),
        (test_time, "#e74c3c"),
    ]
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


# ── Plotly interactive chart ──

def graficar_200m_plotly(
    data: dict,
    m: Metricas,
    output_dir: str | Path,
    sesion_id: int,
    panels: set[str] | None = None,
) -> str:
    """Generate a Plotly interactive chart from full 25Hz data.

    panels: subset of {"speed", "roll", "pitch", "dist"} to display.
           None or empty → all 4 panels.

    Caches HTML to ``output_dir/charts/{sesion_id}_{panels_key}.html``.
    Returns the path to the cached file.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    ALL_PANELS = ["speed", "roll", "pitch", "dist"]
    PANEL_TITLES = {
        "speed": "Velocidad",
        "roll": "Balanceo (Roll)",
        "pitch": "Cabeceo (Pitch)",
        "dist": "Distancia por palada",
    }

    if not panels:
        panels = set(ALL_PANELS)
    active = [p for p in ALL_PANELS if p in panels]
    if not active:
        active = list(ALL_PANELS)
    n = len(active)

    time = data["time"]
    speed = data["speed"]
    lean = data["lean"]
    gf_x = data["gforce_x"]
    gf_z = data["gforce_z"]
    peak_t = data["peak_times"]
    peak_s = data["peak_speeds"]
    valley_t = data["valley_times"]
    dist_pp = data.get("dist_por_palada", [])

    from dragonboat.analysis.metrics import calcular_pitch
    pitch = calcular_pitch(np.array(gf_x), np.array(gf_z)).tolist()
    prefix_t = -0.5
    test_time = m.tiempo_total

    # Speed panel gets triple height
    rh = [3 if p == "speed" else 1 for p in active]
    fig = make_subplots(
        rows=n, cols=1, shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=rh,
        subplot_titles=[PANEL_TITLES[p] for p in active],
    )

    # ── Helper: row index for a panel (1-based) ──
    def row(panel_name: str) -> int:
        return active.index(panel_name) + 1

    # ── Panel: Speed ──
    if "speed" in active:
        r = row("speed")

        fig.add_trace(go.Scatter(
            x=time, y=speed,
            mode="lines", line=dict(color="#27ae60", width=2.2),
            showlegend=False, hovertemplate="%{y:.1f} km/h<extra></extra>",
        ), row=r, col=1)

        fig.add_hline(
            y=m.velocidad_media, line=dict(color="#3498db", dash="dash", width=1.5),
            row=r, col=1,
        )
        fig.add_annotation(
            x=test_time * 0.02, y=m.velocidad_media,
            text=f"{m.velocidad_media:.2f} km/h",
            showarrow=False, font=dict(color="#3498db", size=11),
            xanchor="left", yanchor="bottom",
            row=r, col=1,
        )

        if m.tiempo_12kmh is not None:
            fig.add_vrect(
                x0=0, x1=m.tiempo_12kmh,
                fillcolor="#f39c12", opacity=0.08, line_width=0,
                row=r, col=1,
            )
            fig.add_annotation(
                x=m.tiempo_12kmh / 2, y=m.velocidad_maxima * 0.92,
                text=f"0-12 km/h: {m.tiempo_12kmh:.2f}s",
                showarrow=False, font=dict(color="#7a5c00", size=11),
                row=r, col=1,
            )

        if m.tiempo_150m is not None:
            fig.add_vrect(
                x0=m.tiempo_150m, x1=test_time,
                fillcolor="#e74c3c", opacity=0.05, line_width=0,
                row=r, col=1,
            )

        for t_m, label in [(m.tiempo_50m, "50m"), (m.tiempo_100m, "100m"), (m.tiempo_150m, "150m")]:
            if t_m is not None and 0 < t_m < test_time:
                fig.add_vline(x=t_m, line=dict(color="#888", dash="dash", width=1), row=r, col=1)
                fig.add_annotation(
                    x=t_m, y=m.velocidad_maxima * 0.45,
                    text=label, showarrow=False,
                    font=dict(color="#555", size=10),
                    row=r, col=1,
                )

        for vt in valley_t:
            fig.add_trace(go.Scatter(
                x=[vt],
                y=[float(np.interp(vt, time, speed))],
                mode="markers", marker=dict(color="#2980b9", size=4, opacity=0.45),
                showlegend=False, hovertemplate="Catch %{x:.2f}s<extra></extra>",
            ), row=r, col=1)

        for i, (pt, ps) in enumerate(zip(peak_t, peak_s)):
            fig.add_annotation(
                x=pt, y=ps,
                text=str(i + 1),
                showarrow=False,
                yshift=12,
                font=dict(color="#1a1a1a", size=9),
                bgcolor="white", borderpad=2,
                opacity=0.9,
                row=r, col=1,
            )

    # ── Panel: Roll ──
    if "roll" in active:
        r = row("roll")
        num_bars = min(80, len(time))
        step = max(1, len(time) // num_bars)
        t_bins = time[::step]
        roll_bins = lean[::step]
        roll_colors = ["#c0392b" if abs(v) > settings.roll_alert_deg
                       else "#D2691E" if v >= 0 else "#FFB347"
                       for v in roll_bins]
        fig.add_trace(go.Bar(
            x=t_bins, y=roll_bins,
            marker_color=roll_colors, opacity=0.85,
            showlegend=False, hovertemplate="%{y:.1f}°<extra></extra>",
        ), row=r, col=1)

    # ── Panel: Pitch ──
    if "pitch" in active:
        r = row("pitch")
        num_bars = min(80, len(time))
        step = max(1, len(time) // num_bars)
        t_bins = time[::step]
        pitch_bins = np.array(pitch)[::step].tolist()
        pitch_colors = ["#6a9ad8" if v >= 0 else "#1a3a8a" for v in pitch_bins]
        fig.add_trace(go.Bar(
            x=t_bins, y=pitch_bins,
            marker_color=pitch_colors, opacity=0.85,
            showlegend=False, hovertemplate="%{y:.1f}°<extra></extra>",
        ), row=r, col=1)

    # ── Panel: Dist per stroke ──
    if "dist" in active:
        r = row("dist")
        if dist_pp and len(peak_t) >= 2:
            n_bars = min(len(dist_pp), len(peak_t) - 1)
            mid_times = [(peak_t[i] + peak_t[i + 1]) / 2 for i in range(n_bars)]
            bar_heights = [dist_pp[i] for i in range(n_bars)]
            mean_d = m.dist_media_palada
            bar_colors = ["#2ecc71" if d >= mean_d else "#e74c3c" for d in bar_heights]

            fig.add_trace(go.Bar(
                x=mid_times, y=bar_heights,
                marker_color=bar_colors, opacity=0.85,
                showlegend=False,
                text=[f"{d:.2f}" for d in bar_heights],
                textposition="outside",
                hovertemplate="%{y:.2f}m<extra></extra>",
            ), row=r, col=1)

            fig.add_hline(
                y=mean_d, line=dict(color="#c0392b", dash="dash", width=1.5),
                row=r, col=1,
            )
            fig.add_annotation(
                x=0, y=mean_d,
                text=f"{mean_d:.2f} m",
                showarrow=False, font=dict(color="#c0392b", size=12),
                xanchor="left", yanchor="bottom",
                row=r, col=1,
            )

            i_best = int(np.argmax(bar_heights))
            fig.add_annotation(
                x=mid_times[i_best], y=bar_heights[i_best],
                text="★", showarrow=False,
                font=dict(color="#f1c40f", size=20),
                row=r, col=1,
            )
        else:
            fig.add_annotation(
                x=0.5, y=0.5, xref="paper", yref="paper",
                text="No detectadas",
                showarrow=False, font=dict(color="gray", size=14),
                row=r, col=1,
            )

    # ── Layout ──
    height_per_unit = 180
    fig.update_layout(
        height=sum(rh) * height_per_unit + 100,
        margin=dict(l=50, r=50, t=50, b=30),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Segoe UI, Arial, sans-serif"),
        showlegend=False,
    )

    last_row = row(active[-1])
    fig.update_xaxes(title_text="Tiempo (s)", row=last_row, col=1)
    for r in range(1, n + 1):
        fig.update_yaxes(gridcolor="#e0e0e0", row=r, col=1)
        fig.update_xaxes(gridcolor="#e0e0e0", row=r, col=1)
    fig.update_xaxes(range=[prefix_t, test_time + 0.5], row=1, col=1)
    for r in range(2, n + 1):
        fig.update_xaxes(matches="x", row=r, col=1)

    # ── Save ──
    charts_dir = Path(output_dir) / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    panels_key = "_".join(sorted(active))
    out_path = charts_dir / f"{sesion_id}_{panels_key}.html"
    fig.write_html(
        str(out_path),
        include_plotlyjs="cdn",
        div_id=f"chart-{sesion_id}",
        config={"responsive": True, "displaylogo": False},
    )
    print(f"  Chart HTML guardado: {out_path}")
    return str(out_path)
