from typing import TYPE_CHECKING

from osdagbridge.core.reports.report_utils import _fig_embed, _tex
from osdagbridge.core.reports.styles import (
    COMPACT_TABCOLSEP_PT,
    make_longtable,
    status_badge,
)
from osdagbridge.core.utils.common import (
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
)

if TYPE_CHECKING:
    from .report_generator import ReportDataBridge


def ch4_analysis(asum, fig_paths, bridge: "ReportDataBridge", span_m: float):
    fig_paths = fig_paths or {}
    lc_summary = (asum or {}).get('load_cases', {})
    rxn_summary = (asum or {}).get('reactions', {})

    def _is_moving(lc_name: str) -> bool:
        n = lc_name.lower()
        return "moving" in n or " pos_" in n

    lc_summary = {k: v for k, v in lc_summary.items() if not _is_moving(k)}
    rxn_summary = {k: v for k, v in rxn_summary.items() if not _is_moving(k)}

    def _fmt(val, nd=3):
        try:
            return f"{float(val):.{nd}f}"
        except (TypeError, ValueError):
            return r"---"

    def _merged_row(lc, bm_d, rxn_d):
        bm_d = bm_d or {}
        rxn_d = rxn_d or {}
        return (
            _tex(lc) + r" & "
            + _fmt(bm_d.get('max_bm')) + r" & "
            + _tex(bm_d.get('bm_girder', '---')) + r" & "
            + _fmt(bm_d.get('bm_location')) + r" & "
            + _fmt(bm_d.get('max_sf')) + r" & "
            + _tex(bm_d.get('sf_girder', '---')) + r" & "
            + _fmt(bm_d.get('sf_location')) + r" & "
            + _fmt(rxn_d.get('left_kN')) + r" & "
            + _fmt(rxn_d.get('right_kN')) + r" \\[4pt]"
        )

    all_lcs = list(lc_summary.keys()) + [k for k in rxn_summary if k not in lc_summary]

    merged_body = (
        ("\n\\hline\n").join(
            _merged_row(lc, lc_summary.get(lc), rxn_summary.get(lc))
            for lc in all_lcs
        )
        + "\n\\hline"
        if all_lcs
        else r"--- & --- & --- & --- & --- & --- & --- & --- & --- \\[4pt]" + "\n\\hline"
    )

    # 2-tier grouped header for Table 4.1 (includes Support Reactions)
    # Place \multirow{-2.5}{*} on Row 2 so colortbl's Row 2 tint never clips text.
    t41_hdr = (
        r"\hline" + "\n"
        r"\rowcolor{osdagGreenTint}" + "\n"
        r" & "
        r"\multicolumn{3}{c|}{\cellcolor{osdagGreenTint}\textcolor{osdagGreenDark}{\textbf{Bending Moment}}} & "
        r"\multicolumn{3}{c|}{\cellcolor{osdagGreenTint}\textcolor{osdagGreenDark}{\textbf{Shear Force}}} & "
        r"\multicolumn{2}{c|}{\cellcolor{osdagGreenTint}\textcolor{osdagGreenDark}{\textbf{Support Reactions}}} \\" + "\n"
        r"\cline{2-9}" + "\n"
        r"\rowcolor{osdagGreenTint}" + "\n"
        r"\multirow{-2.5}{*}{\makecell{\textcolor{osdagGreenDark}{\textbf{Load Case /}}\\\textcolor{osdagGreenDark}{\textbf{Combination}}}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Max}}\\\textcolor{osdagGreenDark}{\textbf{(kNm)}}} & "
        r"\textcolor{osdagGreenDark}{\textbf{Girder}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Loc.}}\\\textcolor{osdagGreenDark}{\textbf{(m)}}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Max}}\\\textcolor{osdagGreenDark}{\textbf{(kN)}}} & "
        r"\textcolor{osdagGreenDark}{\textbf{Girder}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Loc.}}\\\textcolor{osdagGreenDark}{\textbf{(m)}}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Left}}\\\textcolor{osdagGreenDark}{\textbf{(kN)}}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Right}}\\\textcolor{osdagGreenDark}{\textbf{(kN)}}} \\[4pt]" + "\n"
        r"\hline"
    )
    t41_first_head = r"\caption{\textbf{Summary of Maximum Demands and Support Reactions}}\\" + "\n" + t41_hdr
    t41_cont_head = (
        r"\multicolumn{9}{l}{\small\textit{Table \thetable\ (continued): Summary of Maximum Demands and Support Reactions}} \\"
        + "\n"
        + t41_hdr
    )

    demands_table = make_longtable(
        caption="Summary of Maximum Demands and Support Reactions",
        headers=None,
        body_tex=merged_body,
        col_alignments=["C", "C", "C", "C", "C", "C", "C", "C", "C"],
        col_widths_cm=[2.8, 1.6, 1.2, 1.2, 1.6, 1.2, 1.2, 1.5, 1.5],
        raw_first_head=t41_first_head,
        raw_head=t41_cont_head,
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        arraystretch=1.2,
        font_size=r"\footnotesize",
    )

    # Governing deflections across girders
    _span_m = float(bridge.input_dict.get(KEY_SPAN, 0) or 0)
    _allow_live_mm = _span_m * 1000.0 / 800.0
    _allow_total_mm = _span_m * 1000.0 / 600.0

    try:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1) or 1)
    except (TypeError, ValueError):
        n = 1

    _live_mm = None
    _total_mm = None
    for _gi in range(1, n + 1):
        _l = bridge.output_dict.get(f"{KEY_SD_DEFL_LIVE}.G{_gi}")
        _t = bridge.output_dict.get(f"{KEY_SD_DEFL_TOTAL}.G{_gi}")
        if _l is not None:
            _live_mm = max(_live_mm, float(_l)) if _live_mm is not None else float(_l)
        if _t is not None:
            _total_mm = max(_total_mm, float(_t)) if _total_mm is not None else float(_t)

    _live_str = f"{_live_mm:.3f} mm" if _live_mm is not None else "---"
    _total_str = f"{_total_mm:.3f} mm" if _total_mm is not None else "---"
    _allow_live_str = f"L/800 = {_allow_live_mm:.1f} mm"
    _allow_total_str = f"L/600 = {_allow_total_mm:.1f} mm"
    _live_status = (
        status_badge("PASS" if _live_mm <= _allow_live_mm else "FAIL")
        if _live_mm is not None
        else "---"
    )
    _total_status = (
        status_badge("PASS" if _total_mm <= _allow_total_mm else "FAIL")
        if _total_mm is not None
        else "---"
    )

    defl_rows = [
        (r"Deflection due to Live Load, $\delta_{LL}$", _live_str),
        (r"Allowable Live Load Deflection ($\Delta_{allow}$)", _allow_live_str),
        ("Live Load Deflection Check Status", _live_status),
        (r"Deflection due to Total Load, $\delta_{total}$", _total_str),
        (r"Allowable Total Deflection ($\Delta_{allow}$)", _allow_total_str),
        ("Total Load Deflection Check Status", _total_status),
    ]
    defl_table = make_longtable(
        caption=r"Deflection Summary (Live Load \& Total Load)",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in defl_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[7.0, 8.2],
    )

    return (
        r"""
\chapter{Analysis Results}

A grillage model was used for structural analysis. The deck is idealized as a grid of elastic beam elements --- longitudinal members represent the composite steel girders with effective slab, and transverse members represent the slab or cross frames. This section summarizes the critical output from that analysis.

"""
        + demands_table + "\n\n"
        + defl_table + "\n\n"
        + r"\vspace{0.8em}" + "\n"
        + r"\noindent" + "\n"
        + _fig_embed(
            fig_paths.get('bm_envelope'),
            'Bending Moment Envelope (Envelope ULS): Max/min BM along span. X-axis: distance from left support (m). Y-axis: Bending Moment (kN-m).',
            width=r'0.75\textwidth',
        )
        + "\n\n" + r"\vspace{0.5em}" + "\n"
        + _fig_embed(
            fig_paths.get('sf_envelope'),
            'Shear Force Envelope (Envelope ULS): Max/min SF along span. X-axis: distance from left support (m). Y-axis: Shear Force (kN).',
            width=r'0.75\textwidth',
        )
        + "\n\n" + r"\vspace{0.5em}" + "\n"
        + _fig_embed(
            fig_paths.get('defl_ll'),
            'Vertical Deflection D$_y$ (1.0 LL): Maximum deflection along span. Load Case: 1.0 LL, Combination: $D_y$. Nodes shown. Isometric view.',
            width=r'0.75\textwidth',
        )
        + "\n"
    )
