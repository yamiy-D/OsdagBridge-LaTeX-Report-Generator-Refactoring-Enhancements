# =============================================================================
# OsdagBridge — Thread-Safe Matplotlib Chart Generators for Reports
# =============================================================================
"""Programmatic Matplotlib chart generators for Section 5.5 (Utilization Ratio)
and Chapter 7 (Material Take-off & Quantity Summary).

Design invariants:
- Pure object-oriented Matplotlib (``Figure`` + ``FigureCanvasAgg``) with ZERO
  ``matplotlib.pyplot`` imports so rendering is safe inside desktop Qt worker
  threads (``_ReportWorker``) and headless CI environments.
- Uses ``matplotlib.rc_context`` locally so global ``rcParams`` are never
  mutated (preventing races with ``MplPlotWidget`` on the GUI thread).
- Consumes all colors exclusively from ``styles.CHART_PALETTE``.
"""

from __future__ import annotations

import io
import logging
from typing import Dict, Mapping, Optional

from matplotlib import rc_context
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from osdagbridge.core.reports.styles import CHART_PALETTE

logger = logging.getLogger(__name__)

_LOCAL_RC = {
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "xtick.color": CHART_PALETTE["text"],
    "ytick.color": CHART_PALETTE["text"],
    "text.color": CHART_PALETTE["text"],
}


def _render_png_bytes(fig: Figure, dpi: int = 300) -> bytes:
    """Render a Matplotlib Figure to PNG bytes via Agg and release its memory."""
    buf = io.BytesIO()
    try:
        canvas = FigureCanvasAgg(fig)
        canvas.print_png(buf)
        return buf.getvalue()
    finally:
        fig.clear()


def generate_ur_summary_chart(
    component_urs: Mapping[str, Optional[float]],
    dpi: int = 300,
) -> Optional[bytes]:
    """Generate the Section 5.5 Utilization Ratio (UR = Demand / Capacity) bar chart.

    Parameters
    ----------
    component_urs : Mapping[str, Optional[float]]
        Dictionary with keys ``'girder'``, ``'deck'``, ``'cross_bracing'``, and
        ``'end_diaphragm'`` mapped to numeric UR values (or ``None`` when N/A).
    dpi : int
        Output resolution in dots per inch (default 300).

    Returns
    -------
    Optional[bytes]
        PNG image bytes, or ``None`` if no component has a numeric UR.
    """
    if not component_urs:
        return None

    ordered_specs = [
        ("girder", "Steel Plate\nGirders"),
        ("deck", "Concrete\nDeck Slab"),
        ("cross_bracing", "Cross\nBracing"),
        ("end_diaphragm", "End\nDiaphragms"),
    ]

    raw_vals = []
    for key, _ in ordered_specs:
        v = component_urs.get(key)
        try:
            raw_vals.append(float(v) if v is not None else None)
        except (TypeError, ValueError):
            raw_vals.append(None)

    numeric_vals = [v for v in raw_vals if v is not None and v >= 0.0]
    if not numeric_vals:
        return None

    # Cap extreme sentinel failure values (e.g., 9.999) so passing bars stay legible
    non_sentinel = [v for v in numeric_vals if v < 9.5]
    cap_ceiling = max(2.2, (max(non_sentinel) * 1.4) if non_sentinel else 2.2)

    plot_heights = []
    bar_colors = []
    bar_labels = []
    is_na_flags = []
    has_na = False

    for v in raw_vals:
        if v is None:
            has_na = True
            is_na_flags.append(True)
            plot_heights.append(0.08)
            bar_colors.append("#E5E7EB")
            bar_labels.append("N/A")
        else:
            is_na_flags.append(False)
            if v >= 9.5:
                plot_heights.append(cap_ceiling)
                bar_colors.append(CHART_PALETTE["fail"])
                bar_labels.append(f">{v:.1f} (FAIL)")
            else:
                plot_heights.append(v)
                if v > 1.0:
                    bar_colors.append(CHART_PALETTE["fail"])
                    bar_labels.append(f"{v:.2f} (FAIL)")
                elif v >= 0.90:
                    bar_colors.append(CHART_PALETTE["warn"])
                    bar_labels.append(f"{v:.2f}")
                else:
                    bar_colors.append(CHART_PALETTE["primary"])
                    bar_labels.append(f"{v:.2f}")

    y_max = max(1.25, max(plot_heights) * 1.22)

    with rc_context(_LOCAL_RC):
        fig = Figure(figsize=(7.2, 4.0), dpi=dpi, facecolor="white")
        ax = fig.add_subplot(111)
        ax.set_facecolor("white")

        x_pos = list(range(len(ordered_specs)))
        labels = [lbl for _, lbl in ordered_specs]

        bars = ax.bar(
            x_pos,
            plot_heights,
            width=0.52,
            color=bar_colors,
            edgecolor=CHART_PALETTE["primary_dark"],
            linewidth=0.8,
            zorder=3,
        )

        # Apply dashed muted styling to N/A placeholder bars
        for bar, is_na in zip(bars, is_na_flags):
            if is_na:
                bar.set_edgecolor(CHART_PALETTE["muted"])
                bar.set_linestyle("--")
                bar.set_hatch("//")

        # Horizontal threshold line at UR = 1.0 (Red dashed line)
        ax.axhline(
            1.0,
            color=CHART_PALETTE["fail"],
            linestyle="--",
            linewidth=1.6,
            zorder=4,
            label="Design Limit (UR = 1.0)",
        )

        # Annotate bar values with a subtle white halo so text near UR=1.0 never
        # collides with the red dashed threshold line.
        for bar, text, is_na in zip(bars, bar_labels, is_na_flags):
            h = bar.get_height()
            color = CHART_PALETTE["muted"] if is_na else CHART_PALETTE["text"]
            weight = "normal" if is_na else "bold"
            label_y = h + (y_max * 0.025)
            # If the text sits just below UR=1.0 (e.g., 0.80 <= h <= 0.96), nudge it
            # neatly above the 1.0 threshold or give it a crisp opaque white pill.
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                label_y,
                text,
                ha="center",
                va="bottom",
                fontsize=8.8,
                fontweight=weight,
                color=color,
                bbox=dict(boxstyle="round,pad=0.16", facecolor="white", edgecolor="none", alpha=0.92),
                zorder=6,
            )

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=9.2)
        ax.set_ylabel("Utilization Ratio", fontweight="bold")
        ax.set_ylim(0.0, y_max)
        ax.set_title("Overall Design Check Summary — Utilization Ratio (Demand / Capacity)", pad=12)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4, color="#94A3B8", zorder=0)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        legend_handles = [
            Patch(facecolor=CHART_PALETTE["primary"], edgecolor=CHART_PALETTE["primary_dark"], label="Pass (UR <= 0.90)"),
            Patch(facecolor=CHART_PALETTE["warn"], edgecolor=CHART_PALETTE["primary_dark"], label="Near Limit (0.90 < UR <= 1.0)"),
            Patch(facecolor=CHART_PALETTE["fail"], edgecolor=CHART_PALETTE["primary_dark"], label="Fail (UR > 1.0)"),
        ]
        line_handles, line_labels = ax.get_legend_handles_labels()
        ax.legend(
            handles=legend_handles + line_handles,
            loc="upper right",
            fontsize=7.8,
            frameon=True,
            facecolor="white",
            edgecolor="#E2E8F0",
        )

        if has_na:
            fig.text(
                0.5,
                0.01,
                "Note: N/A indicates component design check not applicable or not yet implemented for selected section type.",
                ha="center",
                fontsize=7.6,
                style="italic",
                color=CHART_PALETTE["muted"],
            )
            fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.20)
        else:
            fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.15)

        return _render_png_bytes(fig, dpi=dpi)


def generate_material_quantity_charts(
    boq_numeric: Mapping[str, Optional[float]],
    dpi: int = 300,
) -> Dict[str, bytes]:
    """Generate Chapter 7 Material Take-off bar charts as PNG bytes.

    Produces up to two charts keyed by asset stem:
    - ``'mto_steel_chart'``: Structural steel tonnage (MT) across Girders,
      Cross Bracing, and End Diaphragms.
    - ``'mto_concrete_rebar_chart'``: Two side-by-side single-axis subplots for
      Deck Slab Concrete Volume (m^3) and Deck Reinforcement Steel Weight (MT).
    """
    out: Dict[str, bytes] = {}
    if not boq_numeric:
        return out

    def _flt(key: str) -> Optional[float]:
        v = boq_numeric.get(key)
        if v is None:
            return None
        try:
            f = float(v)
            return f if f >= 0.0 else None
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Chart 1: Structural Steel Tonnage Breakdown (Girders, CB, ED)
    # ------------------------------------------------------------------
    steel_specs = [
        ("steel_girders_mt", "Steel Plate\nGirders"),
        ("steel_cross_bracing_mt", "Cross\nBracing"),
        ("steel_end_diaphragms_mt", "End\nDiaphragms"),
    ]
    steel_vals = [_flt(k) for k, _ in steel_specs]
    valid_steel = [v for v in steel_vals if v is not None and v > 0.0]

    if valid_steel:
        total_steel = sum(valid_steel)
        max_steel = max(valid_steel)
        y_max = max_steel * 1.25
        has_na_steel = any(v is None for v in steel_vals)

        with rc_context(_LOCAL_RC):
            fig = Figure(figsize=(6.8, 3.8), dpi=dpi, facecolor="white")
            ax = fig.add_subplot(111)
            ax.set_facecolor("white")

            x_pos = list(range(len(steel_specs)))
            labels = [lbl for _, lbl in steel_specs]
            palette_seq = [
                CHART_PALETTE["primary"],
                CHART_PALETTE["primary_dark"],
                CHART_PALETTE["concrete"],
            ]

            heights = []
            colors = []
            na_flags = []
            annotations = []
            for idx, v in enumerate(steel_vals):
                if v is None:
                    na_flags.append(True)
                    heights.append(max_steel * 0.06)
                    colors.append("#E5E7EB")
                    annotations.append("N/A")
                else:
                    na_flags.append(False)
                    heights.append(v)
                    colors.append(palette_seq[idx])
                    pct = (v / total_steel * 100.0) if total_steel > 0 else 0.0
                    annotations.append(f"{v:.2f} MT ({pct:.1f}%)")

            bars = ax.bar(
                x_pos,
                heights,
                width=0.48,
                color=colors,
                edgecolor=CHART_PALETTE["primary_dark"],
                linewidth=0.8,
                zorder=3,
            )
            for bar, is_na in zip(bars, na_flags):
                if is_na:
                    bar.set_edgecolor(CHART_PALETTE["muted"])
                    bar.set_linestyle("--")
                    bar.set_hatch("//")

            for bar, ann, is_na in zip(bars, annotations, na_flags):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bar.get_height() + (y_max * 0.025),
                    ann,
                    ha="center",
                    va="bottom",
                    fontsize=8.8,
                    fontweight="normal" if is_na else "bold",
                    color=CHART_PALETTE["muted"] if is_na else CHART_PALETTE["text"],
                )

            ax.set_xticks(x_pos)
            ax.set_xticklabels(labels, fontsize=9.2)
            ax.set_ylabel("Structural Steel Tonnage (MT)", fontweight="bold")
            ax.set_ylim(0.0, y_max)
            ax.set_title(
                f"Structural Steel Tonnage Summary (Total: {total_steel:.2f} MT)",
                pad=12,
            )
            ax.yaxis.grid(True, linestyle="--", alpha=0.4, color="#94A3B8", zorder=0)
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            if has_na_steel:
                fig.text(
                    0.5,
                    0.01,
                    "Note: N/A indicates End Diaphragm steel quantity is not derived for non-bracing section types.",
                    ha="center",
                    fontsize=7.6,
                    style="italic",
                    color=CHART_PALETTE["muted"],
                )
                fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.20)
            else:
                fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.15)

            out["mto_steel_chart"] = _render_png_bytes(fig, dpi=dpi)

    # ------------------------------------------------------------------
    # Chart 2: Deck Slab Concrete Volume (m^3) vs. Rebar Weight (MT)
    # Two independent single-axis subplots so units are never conflated.
    # ------------------------------------------------------------------
    conc_m3 = _flt("concrete_deck_m3")
    rebar_mt = _flt("rebar_deck_mt")

    if conc_m3 is not None or rebar_mt is not None:
        with rc_context(_LOCAL_RC):
            fig = Figure(figsize=(7.0, 3.6), dpi=dpi, facecolor="white")
            ax1 = fig.add_subplot(121)
            ax2 = fig.add_subplot(122)

            # Left panel: Concrete Volume (m^3)
            ax1.set_facecolor("white")
            if conc_m3 is not None and conc_m3 > 0:
                b1 = ax1.bar(
                    [0],
                    [conc_m3],
                    width=0.42,
                    color=CHART_PALETTE["concrete"],
                    edgecolor="#1E3A5F",
                    linewidth=0.8,
                    zorder=3,
                )
                ax1.set_ylim(0.0, conc_m3 * 1.28)
                ax1.text(
                    0,
                    conc_m3 + conc_m3 * 0.04,
                    f"{conc_m3:.2f} m³",
                    ha="center",
                    va="bottom",
                    fontsize=9.2,
                    fontweight="bold",
                )
            else:
                ax1.text(0, 0.5, "N/A", ha="center", va="center", color=CHART_PALETTE["muted"])
                ax1.set_ylim(0.0, 1.0)
            ax1.set_xticks([0])
            ax1.set_xticklabels(["Deck Slab\nConcrete"])
            ax1.set_xlim(-0.6, 0.6)
            ax1.set_ylabel("Concrete Volume (m³)", fontweight="bold")
            ax1.set_title("Concrete Volume", pad=10)
            ax1.yaxis.grid(True, linestyle="--", alpha=0.4, color="#94A3B8", zorder=0)
            ax1.set_axisbelow(True)
            ax1.spines["top"].set_visible(False)
            ax1.spines["right"].set_visible(False)

            # Right panel: Reinforcement Steel Weight (MT)
            ax2.set_facecolor("white")
            if rebar_mt is not None and rebar_mt > 0:
                ax2.bar(
                    [0],
                    [rebar_mt],
                    width=0.42,
                    color=CHART_PALETTE["rebar"],
                    edgecolor="#1E293B",
                    linewidth=0.8,
                    zorder=3,
                )
                ax2.set_ylim(0.0, rebar_mt * 1.28)
                ax2.text(
                    0,
                    rebar_mt + rebar_mt * 0.04,
                    f"{rebar_mt:.2f} MT",
                    ha="center",
                    va="bottom",
                    fontsize=9.2,
                    fontweight="bold",
                )
            else:
                ax2.text(0, 0.5, "N/A", ha="center", va="center", color=CHART_PALETTE["muted"])
                ax2.set_ylim(0.0, 1.0)
            ax2.set_xticks([0])
            ax2.set_xticklabels(["Deck\nReinforcement"])
            ax2.set_xlim(-0.6, 0.6)
            ax2.set_ylabel("Reinforcement Steel Weight (MT)", fontweight="bold")
            ax2.set_title("Reinforcement Steel", pad=10)
            ax2.yaxis.grid(True, linestyle="--", alpha=0.4, color="#94A3B8", zorder=0)
            ax2.set_axisbelow(True)
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_visible(False)

            fig.suptitle(
                "Concrete Volume (m³) vs. Reinforcement Steel Weight (MT)",
                fontsize=11,
                fontweight="bold",
                y=0.98,
            )
            fig.subplots_adjust(left=0.13, right=0.96, top=0.82, bottom=0.16, wspace=0.38)
            out["mto_concrete_rebar_chart"] = _render_png_bytes(fig, dpi=dpi)

    return out
