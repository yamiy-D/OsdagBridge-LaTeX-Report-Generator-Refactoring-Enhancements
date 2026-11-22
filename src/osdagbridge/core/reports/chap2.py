# =============================================================================
# Chapter 2: Input Parameters (Consuming Centralized styles.py)
# =============================================================================

from osdagbridge.core.reports.report_utils import _render_value, _tex, get_girder_entries
from osdagbridge.core.reports.styles import (
    COMPACT_TABCOLSEP_PT,
    make_longtable,
    make_simple_table,
)
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CB_LOAD,
    KEY_CB_TYPE,
    KEY_CROSS_BRACING,
    KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_DESIGN_MODE,
    KEY_DO_GAMMA_C_BASIC,
    KEY_DO_GAMMA_FLT,
    KEY_DO_GAMMA_M0,
    KEY_DO_GAMMA_M1,
    KEY_DO_GAMMA_MF,
    KEY_DO_GAMMA_S,
    KEY_DO_GAMMA_V,
    KEY_END_DIAPHRAGM,
    KEY_FOOTPATH,
    KEY_GIRDER,
    KEY_INCLUDE_MEDIAN,
    KEY_MD_TYPE,
    KEY_MP_CB_BRACING_SECTION_DESIGNATION,
    KEY_MP_CB_MEMBER_ID,
    KEY_MP_CB_SELECT_GIRDERS,
    KEY_MP_CB_SPACING,
    KEY_MP_CB_TYPE,
    KEY_MP_ED_BRACING_SECTION_DESIGNATION,
    KEY_MP_ED_MEMBER_ID,
    KEY_MP_ED_SELECT_GIRDERS,
    KEY_MP_ED_TYPE,
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS,
    KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH,
    KEY_MP_GIRDER_DEPTH,
    KEY_MP_GIRDER_SYMMETRY,
    KEY_MP_GIRDER_TOP_FLANGE_THICKNESS,
    KEY_MP_GIRDER_TOP_FLANGE_WIDTH,
    KEY_MP_GIRDER_TORSIONAL_RESTRAINT,
    KEY_MP_GIRDER_TYPE,
    KEY_MP_GIRDER_WARPING_RESTRAINT,
    KEY_MP_GIRDER_WEB_THICKNESS,
    KEY_MP_GIRDER_WEB_TYPE,
    KEY_MP_STIFFENER_BEARING_THICKNESS,
    KEY_MP_STIFFENER_INTERMEDIATE,
    KEY_MP_STIFFENER_INTERMEDIATE_SPACING,
    KEY_MP_STIFFENER_INTERMEDIATE_THICKNESS,
    KEY_MP_STIFFENER_LONGITUDINAL,
    KEY_MP_STIFFENER_NO_BEARING_STIFFENERS,
    KEY_MP_STIFFENER_SPACING,
    KEY_RL_LOAD_VALUE,
    KEY_RL_TYPE,
    KEY_SD_BOTTOM_FLANGE_THICKNESS,
    KEY_SD_BOTTOM_FLANGE_WIDTH,
    KEY_SD_SHEAR_DIAMETER,
    KEY_SD_SHEAR_HEIGHT,
    KEY_SD_SHEAR_STUDS_PER_SECTION,
    KEY_SD_SHEAR_ULTIMATE_STRENGTH,
    KEY_SD_SHEAR_YIELD_STRENGTH,
    KEY_SD_TOP_FLANGE_THICKNESS,
    KEY_SD_TOP_FLANGE_WIDTH,
    KEY_SD_TOTAL_DEPTH,
    KEY_SD_WEB_THICKNESS,
    KEY_SKEW_ANGLE,
    KEY_SPAN,
    KEY_STRUCTURE_TYPE,
    KEY_TS_DECK_OVERHANG,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_OVERALL_WIDTH,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
)


def _format_dim_mm(input_dict, in_key, output_dict=None, out_key=None, is_thickness=False):
    """Render a girder section dimension in mm.

    Prefers guaranteed-mm keys from ``output_dict`` when present; otherwise
    uses dimension-specific bounds (``< 0.5`` m for plate thicknesses, ``< 10.0``
    m for depths/flange widths) so unconverted mm inputs (e.g. 8 mm web plate)
    are never mis-multiplied while post-design metre-mutated values convert back
    accurately to mm.
    """
    if output_dict and out_key and output_dict.get(out_key) not in (None, ""):
        raw = output_dict.get(out_key)
    else:
        raw = input_dict.get(in_key)
    if raw in (None, ""):
        return ""
    try:
        val = float(raw)
        threshold = 0.5 if is_thickness else 10.0
        mm_val = val * 1000.0 if 0.0 < val < threshold else val
        if abs(mm_val - round(mm_val)) < 1e-6:
            return f"{int(round(mm_val))} mm"
        return f"{mm_val:.1f} mm"
    except (TypeError, ValueError):
        return _tex(raw) + " mm"


def _resolve_lane_count(input_dict):
    val = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    if val not in (None, ""):
        return _tex(val)
    cw = input_dict.get(KEY_CARRIAGEWAY_WIDTH)
    if cw not in (None, ""):
        try:
            lanes = IRC6_2017.table_6(float(cw))
            if lanes is not None:
                return str(int(lanes))
        except Exception:
            pass
    return ""


def ch2_input_parameters(m, input_dict, output_dict=None):
    input_dict = input_dict or {}
    output_dict = output_dict or {}
    girder_entries = get_girder_entries(input_dict)
    n_girders = len(girder_entries)

    # --- Basic Input Tables ---
    loc_rows = [
        ("Project Location", _tex(m.project_location)),
        (
            "Latitude / Longitude",
            _render_value(input_dict, 'latitude') + ', ' + _render_value(input_dict, 'longitude'),
        ),
        ("Seismic Zone (IRC 6)", _render_value(input_dict, 'seismic_zone')),
        ("Basic Wind Speed (IRC 6)", _render_value(input_dict, 'wind_speed', ' m/s')),
        (
            "Shade Temp. Max / Min (IRC 6)",
            _render_value(input_dict, 'shade_temp_max')
            + r" \textdegree{}C / "
            + _render_value(input_dict, 'shade_temp_min')
            + r" \textdegree{}C",
        ),
    ]
    loc_body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in loc_rows)
    loc_table = make_simple_table(
        headers=["Parameter", "Value"],
        body_tex=loc_body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.4],
        caption="Project Location",
        label="subsec:project-location",
    )

    geom_rows = [
        ("Type of Structure", _render_value(input_dict, KEY_STRUCTURE_TYPE)),
        ("Span (m)", _render_value(input_dict, KEY_SPAN, ' m')),
        ("Carriageway Width (m)", _render_value(input_dict, KEY_CARRIAGEWAY_WIDTH, ' m')),
        ("Include Median", _render_value(input_dict, KEY_INCLUDE_MEDIAN)),
        ("Footpath", _render_value(input_dict, KEY_FOOTPATH)),
        (
            "Skew Angle (degrees)",
            _render_value(input_dict, KEY_SKEW_ANGLE, r'\textdegree{}')
            + r" (IRC 24 Cl. 504.8 limit: $\pm$15\textdegree{})",
        ),
    ]
    geom_body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in geom_rows)
    geom_table = make_simple_table(
        headers=["Parameter", "Value"],
        body_tex=geom_body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.4],
        caption="Bridge Geometry",
        label="subsec:bridge-geometry",
    )

    mat_rows = [
        ("Girder Steel Grade (IS 2062)", _render_value(input_dict, KEY_GIRDER)),
        ("Cross Bracing Steel Grade", _render_value(input_dict, KEY_CROSS_BRACING)),
        ("End Diaphragm Steel Grade", _render_value(input_dict, KEY_END_DIAPHRAGM)),
        ("Concrete Deck Grade (IRC 22)", _render_value(input_dict, KEY_DECK_CONCRETE_GRADE_BASIC)),
    ]
    mat_body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in mat_rows)
    mat_table = make_simple_table(
        headers=["Parameter", "Value"],
        body_tex=mat_body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.4],
        caption="Material Selection",
        label="subsec:material",
    )

    # --- Additional Input LongTables ---
    ts_rows = [
        ("Overall Bridge Width (m)", _render_value(input_dict, KEY_TS_OVERALL_WIDTH, ' m')),
        ("No. of Girders", _render_value(input_dict, KEY_TS_NO_OF_GIRDERS)),
        ("Girder Spacing (m)", _render_value(input_dict, KEY_TS_GIRDER_SPACING, ' m')),
        ("Deck Overhang Width (m)", _render_value(input_dict, KEY_TS_DECK_OVERHANG, ' m')),
        ("Deck Thickness (mm)", _render_value(input_dict, KEY_TS_DECK_THICKNESS, ' mm')),
        (
            "Footpath Width (m)",
            _render_value(input_dict, KEY_TS_FOOTPATH_WIDTH, ' m') + " (IRC 5 Cl. 104.3.6 min: 1.5 m)",
        ),
        (
            "No. of Traffic Lanes",
            _resolve_lane_count(input_dict) + " (per IRC 5 Cl. 104.3.1)",
        ),
    ]
    ts_body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in ts_rows)
    ts_table = make_longtable(
        caption="Typical Section Details",
        headers=["Parameter", "Value"],
        body_tex=ts_body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    comp_rows = [
        ("Crash Barrier Type", _render_value(input_dict, KEY_CB_TYPE)),
        ("Crash Barrier Load (kN/m)", _render_value(input_dict, KEY_CB_LOAD)),
    ]
    if str(input_dict.get(KEY_INCLUDE_MEDIAN, "")).strip().lower() in ("yes", "true", "1"):
        comp_rows.append(("Median Type", _render_value(input_dict, KEY_MD_TYPE)))
    comp_rows.extend([
        ("Railing Type", _render_value(input_dict, KEY_RL_TYPE)),
        ("Railing Load (kN/m)", _render_value(input_dict, KEY_RL_LOAD_VALUE)),
        ("Wearing Course Material", _render_value(input_dict, KEY_WC_MATERIAL)),
        ("Wearing Course Thickness (mm)", _render_value(input_dict, KEY_WC_THICKNESS, ' mm')),
    ])
    comp_body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in comp_rows)
    comp_table = make_longtable(
        caption="Components Details",
        headers=["Parameter", "Value"],
        body_tex=comp_body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    return (
        r"""
\chapter{Input Parameters}

This section documents all inputs provided to OsdagBridge. User-provided inputs are clearly distinguished from software-assumed defaults. Where the user did not supply a value, the software has applied the IRC/IS code default or an empirical guideline; these are annotated with an asterisk (\sdstar{}).

\section{Basic Inputs (User-Defined)}
\label{sec:basic-inputs}

\noindent\textit{Note: These inputs are mandatory and were provided by the user.}

"""
        + loc_table + "\n\n"
        + geom_table + "\n\n"
        + mat_table + r"""

\newpage
\section{Additional Inputs}
\label{sec:additional-inputs}

Where the user has modified additional inputs, those values are reported here. Where no modification was made, the software default is shown.

"""
        + ts_table + "\n\n"
        + comp_table + "\n\n"
        + _girder_tables(input_dict, n_girders, output_dict) + "\n\n"
        + _bracing_tables(input_dict, n_girders) + "\n\n"
        + _shear_connector_table(input_dict, output_dict) + "\n\n"
        + _safety_factors_table(input_dict)
    )


def _girder_tables(input_dict, n_girders, output_dict=None):
    n = n_girders if n_girders >= 1 else 1
    girder_entries = get_girder_entries(input_dict)
    if not girder_entries:
        girder_entries = [(f"Girder {i}", "M1") for i in range(1, n + 1)]

    entries_for_table = [(lbl, mid, i) for i, (lbl, mid) in enumerate(girder_entries, start=1)]

    gen_lines = []
    dim_lines = []
    rst_lines = []

    for g_lbl, m_id, i in entries_for_table:
        gen_lines.append(
            _tex(g_lbl) + " & " + _tex(m_id) + " & "
            + _render_value(input_dict, KEY_DESIGN_MODE) + " & "
            + _render_value(input_dict, f"{KEY_MP_GIRDER_TYPE}.G{i}.M1") + " & "
            + _render_value(input_dict, f"{KEY_MP_GIRDER_SYMMETRY}.G{i}.M1")
            + r" \\[4pt]" + "\n\\hline"
        )

        d_mm = _format_dim_mm(input_dict, f"{KEY_MP_GIRDER_DEPTH}.G{i}.M1", output_dict, KEY_SD_TOTAL_DEPTH, False)
        tw_mm = _format_dim_mm(input_dict, f"{KEY_MP_GIRDER_WEB_THICKNESS}.G{i}.M1", output_dict, KEY_SD_WEB_THICKNESS, True)
        bft_mm = _format_dim_mm(input_dict, f"{KEY_MP_GIRDER_TOP_FLANGE_WIDTH}.G{i}.M1", output_dict, KEY_SD_TOP_FLANGE_WIDTH, False)
        tft_mm = _format_dim_mm(input_dict, f"{KEY_MP_GIRDER_TOP_FLANGE_THICKNESS}.G{i}.M1", output_dict, KEY_SD_TOP_FLANGE_THICKNESS, True)
        bfb_mm = _format_dim_mm(input_dict, f"{KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH}.G{i}.M1", output_dict, KEY_SD_BOTTOM_FLANGE_WIDTH, False)
        tfb_mm = _format_dim_mm(input_dict, f"{KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS}.G{i}.M1", output_dict, KEY_SD_BOTTOM_FLANGE_THICKNESS, True)

        dim_lines.append(
            _tex(g_lbl) + " & " + d_mm + " & " + tw_mm + " & "
            + f"{bft_mm}, {tft_mm}" + " & "
            + f"{bfb_mm}, {tfb_mm}"
            + r" \\[4pt]" + "\n\\hline"
        )

        rst_lines.append(
            _tex(g_lbl) + " & "
            + _render_value(input_dict, f"{KEY_MP_GIRDER_TORSIONAL_RESTRAINT}.G{i}.M1")
            + ", "
            + _render_value(input_dict, f"{KEY_MP_GIRDER_WARPING_RESTRAINT}.G{i}.M1")
            + " & "
            + _render_value(input_dict, f"{KEY_MP_GIRDER_WEB_TYPE}.G{i}.M1")
            + " & "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_INTERMEDIATE}.G{i}.M1")
            + "; Spacing: "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_INTERMEDIATE_SPACING}.G{i}.M1", " mm")
            + "; Thickness: "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_INTERMEDIATE_THICKNESS}.G{i}.M1", " mm")
            + " & "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_LONGITUDINAL}.G{i}.M1")
            + " & No.: "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_NO_BEARING_STIFFENERS}.G{i}.M1")
            + "; Spacing: "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_SPACING}.G{i}.M1", " mm")
            + "; Thickness: "
            + _render_value(input_dict, f"{KEY_MP_STIFFENER_BEARING_THICKNESS}.G{i}.M1", " mm")
            + r" \\[4pt]" + "\n\\hline"
        )

    gen_table = make_longtable(
        caption="Girder General Information",
        headers=["Girder", "Member ID", "Design Mode", "Girder Type", "Girder Symmetry"],
        body_tex="\n".join(gen_lines),
        col_alignments=["L", "L", "L", "L", "L"],
        col_widths_cm=[1.8, 2.0, 3.2, 3.6, 3.6],
    )

    dim_table = make_longtable(
        caption="Girder Section Dimensions",
        headers=[
            "Girder",
            "Total Depth, D (mm)",
            r"Web, $t_w$ (mm)",
            r"Top Flange ($b_{tf}$, $t_{tf}$) mm",
            r"Bottom Flange ($b_{bf}$, $t_{bf}$) mm",
        ],
        body_tex="\n".join(dim_lines),
        col_alignments=["L", "C", "C", "L", "L"],
        col_widths_cm=[1.6, 2.4, 2.0, 4.1, 4.1],
    )

    rst_table = make_longtable(
        caption="Girder Restraint and Stiffener Details",
        headers=[
            "Girder",
            "Torsional / Warping Restraint",
            "Web Philosophy",
            "Intermediate Stiffeners",
            "Longitudinal Stiffeners",
            "Bearing Stiffener",
        ],
        body_tex="\n".join(rst_lines),
        col_alignments=["L", "L", "L", "L", "L", "L"],
        col_widths_cm=[1.3, 2.5, 2.2, 3.2, 2.5, 2.7],
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\small",
    )

    return "\\newpage\n\n" + gen_table + "\n\n" + dim_table + "\n\n" + rst_table


def _bracing_tables(input_dict, n_girders):
    n = n_girders if n_girders >= 2 else 2
    cb_lines = []
    ed_lines = []

    for i in range(1, n):
        cb_loc = _render_value(input_dict, f"{KEY_MP_CB_SELECT_GIRDERS}.G{i}G{i+1}.B{i}M1")
        cb_ids = _render_value(input_dict, f"{KEY_MP_CB_MEMBER_ID}.G{i}G{i+1}.B{i}M1")
        cb_lines.append(
            cb_loc + " & " + cb_ids + " & "
            + _render_value(input_dict, f"{KEY_MP_CB_TYPE}.G{i}G{i+1}.B{i}M1") + " & "
            + _render_value(input_dict, f"{KEY_MP_CB_BRACING_SECTION_DESIGNATION}.G{i}G{i+1}.B{i}M1") + " & "
            + _render_value(input_dict, f"{KEY_MP_CB_SPACING}.G{i}G{i+1}.B{i}M1", " m")
            + r" \\[4pt]" + "\n\\hline"
        )

        ed_loc = _render_value(input_dict, f"{KEY_MP_ED_SELECT_GIRDERS}.G{i}G{i+1}.E{i}M1")
        ed_ids = _render_value(input_dict, f"{KEY_MP_ED_MEMBER_ID}.G{i}G{i+1}.E{i}M1")
        ed_lines.append(
            ed_loc + " & " + ed_ids + " & "
            + _render_value(input_dict, f"{KEY_MP_ED_TYPE}.G{i}G{i+1}.E{i}M1") + " & "
            + _render_value(input_dict, f"{KEY_MP_ED_BRACING_SECTION_DESIGNATION}.G{i}G{i+1}.E{i}M1")
            + r" \\[4pt]" + "\n\\hline"
        )

    # Exact 5 columns for Cross Bracing and exact 4 columns for End Diaphragm (no ghost columns)
    cb_table = make_longtable(
        caption="Member Properties: Cross Bracing Details",
        headers=["Location", "Member IDs", "Type of Bracing", "Bracing Section", "Spacing (m)"],
        body_tex="\n".join(cb_lines),
        col_alignments=["L", "L", "L", "L", "C"],
        col_widths_cm=[2.4, 2.4, 3.6, 3.6, 2.2],
    )

    ed_table = make_longtable(
        caption="Member Properties: End Diaphragm Details",
        headers=["Location", "Member IDs", "Type of End Diaphragm", "Section Designation"],
        body_tex="\n".join(ed_lines),
        col_alignments=["L", "L", "L", "L"],
        col_widths_cm=[2.6, 2.6, 4.4, 4.8],
    )

    return "\\newpage\n\n" + cb_table + "\n\n" + ed_table


def _shear_connector_table(input_dict, output_dict=None):
    od = output_dict or {}
    rows = [
        ("Stud Diameter (mm)", _render_value(od, KEY_SD_SHEAR_DIAMETER, " mm")),
        ("Stud Height (mm)", _render_value(od, KEY_SD_SHEAR_HEIGHT, " mm")),
        (r"Stud $f_y$ (MPa)", _render_value(od, KEY_SD_SHEAR_YIELD_STRENGTH, " MPa")),
        (r"Stud $f_u$ (MPa)", _render_value(od, KEY_SD_SHEAR_ULTIMATE_STRENGTH, " MPa")),
        ("No. of Studs per Section", _render_value(od, KEY_SD_SHEAR_STUDS_PER_SECTION)),
    ]
    body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in rows)
    return make_longtable(
        caption="Shear Connector Details",
        headers=["Parameter", "Value"],
        body_tex=body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
        label="subsec:shear-connectors",
    )


def _safety_factors_table(input_dict):
    rows = [
        (r"$\gamma_{M0}$ (Yielding / Buckling)", _render_value(input_dict, KEY_DO_GAMMA_M0)),
        (r"$\gamma_{M1}$ (Ultimate Stress)", _render_value(input_dict, KEY_DO_GAMMA_M1)),
        (r"$\gamma_C$ (Concrete, Basic)", _render_value(input_dict, KEY_DO_GAMMA_C_BASIC)),
        (r"$\gamma_s$ (Reinforcement)", _render_value(input_dict, KEY_DO_GAMMA_S)),
        (r"$\gamma_v$ (Shear Connectors)", _render_value(input_dict, KEY_DO_GAMMA_V)),
        (r"$\gamma_{fft}$ (Fatigue Load)", _render_value(input_dict, KEY_DO_GAMMA_FLT)),
        (r"$\gamma_{Mft}$ (Fatigue Strength)", _render_value(input_dict, KEY_DO_GAMMA_MF)),
    ]
    body = "\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in rows)
    return make_longtable(
        caption="Partial Safety Factors",
        headers=["Parameter", "Value"],
        body_tex=body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
        label="subsec:safety-factors",
        note="Note: All values are per IRC 22 Table 1 unless user-modified.",
    )
