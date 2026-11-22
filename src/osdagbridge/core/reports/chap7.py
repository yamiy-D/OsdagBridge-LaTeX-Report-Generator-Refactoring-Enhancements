from osdagbridge.core.reports.report_utils import _fig_numbered, _tex
from osdagbridge.core.reports.styles import (
    COMPACT_TABCOLSEP_PT,
    make_longtable,
    na_cell,
)
from osdagbridge.core.utils.common import (
    KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_DS_REINF_MATERIAL,
    KEY_GIRDER,
)


def _boq_cell(input_dict: dict, key: str) -> str:
    val = input_dict.get(key, "N.A.")
    if val in (None, "", "N.A.", "N/A"):
        return na_cell("N.A.")
    return str(val)


def ch7_quantities(input_dict, fig_paths=None):
    """Chapter 7 -- Material Take-off & Quantity Summary."""
    input_dict = input_dict or {}
    fig_paths = fig_paths or {}

    girder_grade = _tex(input_dict.get(KEY_GIRDER) or "IS 2062")
    concrete_grade = _tex(input_dict.get(KEY_DECK_CONCRETE_GRADE_BASIC) or "M40")
    rebar_grade = _tex(input_dict.get(KEY_DS_REINF_MATERIAL) or "Fe 500")

    rows = [
        (
            "1",
            f"Structural Steel ({girder_grade}) for Girders",
            "steel_girders",
        ),
        ("2(a)", "Cross Bracing -- Top Chord", "bracing_top"),
        ("2(b)", "Cross Bracing -- Bottom Chord", "bracing_bot"),
        ("2(c)", "Cross Bracing -- Diagonal Chord", "bracing_diag"),
        ("3", "End Diaphragms (Structural Steel)", "ed_steel"),
        ("4", f"Concrete ({concrete_grade}) for Deck Slab", "concrete_deck"),
        ("5", f"Reinforcement Steel ({rebar_grade})", "rebar_deck"),
        ("6", "Shear Stud Connectors", "shear_studs"),
        ("7", "Crash Barrier", "crash_barrier"),
    ]

    body_lines = []
    for sn, desc, prefix in rows:
        body_lines.append(
            f"{sn} & {desc} & "
            + _boq_cell(input_dict, f"{prefix}_vol_formula") + " & "
            + _boq_cell(input_dict, f"{prefix}_qty") + " & "
            + _boq_cell(input_dict, f"{prefix}_vol_total") + " & "
            + _boq_cell(input_dict, f"{prefix}_wt_single") + " & "
            + _boq_cell(input_dict, f"{prefix}_wt_total")
            + r" \\[4pt]" + "\n\\hline"
        )

    bom_table = make_longtable(
        caption=r"Bill of Materials (Steel, Concrete, and Reinforcement Quantities)",
        headers=[
            "S.N.",
            "Item Description",
            r"Unit Volume (m\textsuperscript{3})",
            "Quantity",
            r"Total Volume (m\textsuperscript{3})",
            "Unit Weight (MT)",
            "Total Weight (MT)",
        ],
        body_tex="\n".join(body_lines),
        col_alignments=["C", "L", "C", "C", "C", "C", "C"],
        col_widths_cm=[1.0, 3.55, 3.0, 1.85, 1.8, 1.8, 1.8],
        label="tab:bill-of-materials",
        note=(
            r"Note: Reinforcement steel mass uses the standard preliminary take-off rate of "
            r"120 kg/m\textsuperscript{3} of deck concrete. End diaphragm steel tonnage is derived for "
            r"cross-bracing configurations and marked N.A. for rolled/welded sections."
        ),
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\small",
    )

    charts_block = ""
    steel_fig = fig_paths.get("mto_steel_chart")
    conc_fig = fig_paths.get("mto_concrete_rebar_chart")
    if steel_fig or conc_fig:
        parts = [
            r"\section{Material Quantity Visualizations}",
            r"\label{sec:material-quantity-charts}",
        ]
        if steel_fig:
            parts.append(
                _fig_numbered(
                    steel_fig,
                    "Structural Steel Tonnage Breakdown (Girders, Cross Bracing, End Diaphragms)",
                    label="fig:mto-steel-tonnage",
                    width=r"0.86\textwidth",
                )
            )
        if conc_fig:
            parts.append(
                _fig_numbered(
                    conc_fig,
                    r"Deck Slab Concrete Volume (m\textsuperscript{3}) vs. Reinforcement Steel Weight (MT)",
                    label="fig:mto-concrete-rebar",
                    width=r"0.88\textwidth",
                )
            )
        charts_block = "\n\n".join(parts)

    return (
        r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

This chapter summarizes the estimated structural steel, deck concrete, reinforcement, shear connector, and crash barrier quantities for the designed superstructure.

"""
        + bom_table
        + "\n\n"
        + charts_block
        + "\n"
    )
