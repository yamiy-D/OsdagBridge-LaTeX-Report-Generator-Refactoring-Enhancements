# =============================================================================
# EXECUTIVE SUMMARY
# =============================================================================

from osdagbridge.core.reports.report_utils import (
    _fig_or_placeholder,
    _render_value,
    _tex,
    get_girder_entries,
)
from osdagbridge.core.reports.styles import (
    chapter_title_format_tex,
    make_simple_table,
    section_note,
    status_badge,
    ur_cell,
)
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_SD_SECTION_DESIGNATION,
    KEY_SPAN,
    KEY_STRUCTURE_TYPE,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS,
)


def _format_outcome_line(component_label: str, status_text: str) -> str:
    return rf"{component_label} design: {status_badge(status_text)}"


def executive_summary(input_dict, output_dict, fig_paths, ur_summary=None) -> str:
    fig_paths = fig_paths or {}
    plan_fig = _fig_or_placeholder(fig_paths.get('girder_top'), 'Figure 1 -- Overall Bridge Plan')
    cs_fig = _fig_or_placeholder(
        fig_paths.get('cross_section'),
        'Figure 2 -- Typical Cross-Section (with girder, deck, barriers, footpath)',
    )
    geom_fig = _fig_or_placeholder(
        fig_paths.get('final_geometry'),
        'Figure 3 -- 3D View of Bridge Superstructure',
    )

    sec = _render_value(output_dict or {}, KEY_SD_SECTION_DESIGNATION)

    if ur_summary is None:
        from osdagbridge.core.reports.report_generator import ReportDataBridge
        ur_summary = ReportDataBridge(output_dict or {}, input_dict or {}).extract_component_ur_summary()

    overall_design_status = str(ur_summary.get("overall_design_status") or "")
    gov_name = str(ur_summary.get("governing_check") or "")
    overall_ur_str = str(ur_summary.get("overall_utilization_ratio") or "")
    statuses = ur_summary.get("statuses") or {}
    per_girder_ur = ur_summary.get("per_girder_ur") or {}
    per_girder_gov = ur_summary.get("per_girder_gov_check") or {}

    gov = _tex(gov_name) if gov_name not in (None, '', 'None') else ''
    ur = _tex(overall_ur_str) if overall_ur_str else ''

    # --- Dynamic Table 1: per-girder summary scaled safely within textwidth ---
    labels = get_girder_entries(input_dict)
    if not labels:
        labels = [("", "")]
    n_cols = len(labels)

    label_col_cm = 3.2
    girder_col_cm = max(1.6, round((12.4 / max(1, n_cols)), 2))
    t1_aligns = ["L"] + ["C"] * n_cols
    t1_widths = [label_col_cm] + [girder_col_cm] * n_cols
    t1_headers = ["Parameter"] + [_tex(lbl) for lbl, _ in labels]

    mid_cells = ' & '.join([_tex(mid) for _, mid in labels])
    sec_cells = ' & '.join([sec] * n_cols)

    # Per-girder governing check and UR (never stamping Deck Slab UR onto girders)
    gov_list = []
    ur_list = []
    for gi, (lbl, _) in enumerate(labels, start=1):
        gkey = lbl if lbl in per_girder_ur else f"G{gi}"
        g_gov = per_girder_gov.get(gkey) or gov_name
        g_ur = per_girder_ur.get(gkey)
        gov_list.append(_tex(g_gov) if g_gov else "---")
        ur_list.append(ur_cell(g_ur) if g_ur is not None else "---")

    t1_body = (
        f"Member ID & {mid_cells} " + r"\\[4pt]" + "\n\\hline\n"
        f"Section Designation & {sec_cells} " + r"\\[4pt]" + "\n\\hline\n"
        f"Governing Check & {' & '.join(gov_list)} " + r"\\[4pt]" + "\n\\hline\n"
        f"Utilization Ratio & {' & '.join(ur_list)} " + r"\\[4pt]" + "\n\\hline"
    )

    table1 = (
        r'\noindent\textbf{Table 1 -- Final Bridge Geometry (after optimization)}' + '\n\n'
        + make_simple_table(
            headers=t1_headers,
            body_tex=t1_body,
            col_alignments=t1_aligns,
            col_widths_cm=t1_widths,
            floating=False,
            font_size=r"\small" if n_cols >= 6 else None,
        )
    )

    # --- Project Overview Table ---
    ov_rows = [
        ("Bridge Type", _render_value(input_dict, KEY_STRUCTURE_TYPE)),
        ("Design Standard", "IRC 5, IRC 6, IRC 22, IRC 24, IS 800"),
        ("Span", _render_value(input_dict, KEY_SPAN, ' m')),
        ("Carriageway Width", _render_value(input_dict, KEY_CARRIAGEWAY_WIDTH, ' m')),
        ("No. of Girders", _render_value(input_dict, KEY_TS_NO_OF_GIRDERS)),
        ("Girder Spacing", _render_value(input_dict, KEY_TS_GIRDER_SPACING, ' m')),
        ("Deck Thickness", _render_value(input_dict, KEY_TS_DECK_THICKNESS, ' mm')),
        ("Overall Design Status", status_badge(_tex(overall_design_status)) if overall_design_status else "---"),
        ("Governing Check", gov or "---"),
        ("Overall Utilization Ratio (max)", ur or "---"),
    ]
    ov_body = "\n".join(
        rf"\textbf{{{k}}} & {v} \\[4pt]" + "\n" + r"\hline"
        for k, v in ov_rows
    )
    overview_table = make_simple_table(
        headers=["Parameter", "Value"],
        body_tex=ov_body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.6, 9.6],
        floating=False,
    )

    outcomes_lines = (
        r"\noindent " + _format_outcome_line("Girder", statuses.get("girder", "N/A")) + r" \\" + "\n"
        + _format_outcome_line("Cross bracing", statuses.get("cross_bracing", "N/A")) + r" \\" + "\n"
        + _format_outcome_line("End diaphragm", statuses.get("end_diaphragm", "N/A")) + r" \\" + "\n"
        + _format_outcome_line("Deck slab", statuses.get("deck", "N/A"))
    )

    return (
        r"""
\newpage
{\centering\Large\bfseries\color{osdagGreenDark} Executive Summary\par}
\addcontentsline{toc}{chapter}{Executive Summary}
\vspace{0.8em}

This section provides a concise summary of the bridge design, key inputs, governing loads, and final design outcomes.

\section*{Project Overview}
\addcontentsline{toc}{section}{Project Overview}
\label{sec:project-overview}

"""
        + overview_table
        + "\n\n"
        + plan_fig
        + "\n\n\\newpage\n\n"
        + cs_fig + "\n\n" + geom_fig + "\n\n" + table1 + "\n\n"
        + r"\vspace{0.4em}" + "\n"
        + section_note(r"Note: Utilization ratio (UR) = demand / capacity. A value $\leq 1.0$ indicates a passing check.")
        + r"""

\vspace{1em}

\section*{Key Design Outcomes Summary}
\addcontentsline{toc}{section}{Key Design Outcomes Summary}
\label{sec:key-outcomes}

"""
        + outcomes_lines
        + r"""

\section*{Design Assumptions and Limitations}
\addcontentsline{toc}{section}{Design Assumptions and Limitations}
\label{sec:exec-assumptions}

\begin{itemize}
\item Additional inputs not provided by the user were assumed by software per IRC/IS code defaults or practical consideration.
\item Grillage analysis was performed using OSPGrillage assuming simply supported I-girders.
\item Substructure and foundation design are not included in this report.
\item Splice connections and bearings are not designed in this version.
\end{itemize}

% Restore numbered chapter format
"""
        + chapter_title_format_tex()
        + "\n"
    )
