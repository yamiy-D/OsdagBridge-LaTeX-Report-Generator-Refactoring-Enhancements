# =============================================================================
# Chapter 5: Design Checks (Consuming Centralized styles.py & charts.py)
# =============================================================================
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from osdagbridge.core.reports.report_utils import (
    _fig_numbered,
    _render_value,
    _tex,
    get_girder_entries,
)
from osdagbridge.core.reports.styles import (
    COMPACT_TABCOLSEP_PT,
    girder_banner_row,
    make_longtable,
    na_cell,
    status_badge,
    ur_cell,
)
from osdagbridge.core.utils.common import (
    KEY_DD_AS_BOT,
    KEY_DD_AS_LONG,
    KEY_DD_AS_MIN,
    KEY_DD_AS_REQ_BOT,
    KEY_DD_AS_REQ_TOP,
    KEY_DD_AS_TOP,
    KEY_DD_COVER_OK,
    KEY_DD_DIA_BOT,
    KEY_DD_D_BOT,
    KEY_DD_FY,
    KEY_DD_GAMMA_DL,
    KEY_DD_GAMMA_LL,
    KEY_DD_HAS_OVERHANG,
    KEY_DD_IMPACT_FACTOR,
    KEY_DD_MIN_COVER,
    KEY_DD_MU_BOT,
    KEY_DD_MU_OH,
    KEY_DD_MU_TOP,
    KEY_DD_M_BARRIER,
    KEY_DD_M_DL,
    KEY_DD_M_DL_OH,
    KEY_DD_M_LL,
    KEY_DD_M_LL_OH,
    KEY_DD_M_ULS_HOG,
    KEY_DD_M_ULS_OH,
    KEY_DD_M_ULS_SAG,
    KEY_DD_PUNCH_C1,
    KEY_DD_PUNCH_C2,
    KEY_DD_PUNCH_OK,
    KEY_DD_PUNCH_U1,
    KEY_DD_PUNCH_VED,
    KEY_DD_PUNCH_VED_KN,
    KEY_DD_SHEAR_OK,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_SPACING_MAX,
    KEY_DD_SPAN,
    KEY_DD_SPC_BOT,
    KEY_DD_TYRE_LENGTH,
    KEY_DD_TYRE_WIDTH,
    KEY_DD_VEHICLE,
    KEY_DD_VRD_C_MPA,
    KEY_DD_WDL,
    KEY_DD_WHEEL_LOAD,
    KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_OH,
    KEY_DD_WK_TOP,
    KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_DESIGN_MODE,
    KEY_DS_BOTTOM_CLEAR_COVER,
    KEY_DS_REINF_MATERIAL,
    KEY_DS_STUD_DIAMETER,
    KEY_DS_TOP_CLEAR_COVER,
    KEY_MATERIAL_DECK_FCK,
    KEY_MATERIAL_DECK_FCTM,
    KEY_SD_BOTTOM_FLANGE_THICKNESS,
    KEY_SD_BOTTOM_FLANGE_WIDTH,
    KEY_SD_BS_FCD,
    KEY_SD_BS_FCDW_LC,
    KEY_SD_BS_FCDW_WB,
    KEY_SD_BS_FPSD,
    KEY_SD_BS_R,
    KEY_SD_CLASS_FLANGE,
    KEY_SD_CLASS_WEB,
    KEY_SD_COMPOSITE_IZ,
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
    KEY_SD_EFFECTIVE_SLAB_WIDTH,
    KEY_SD_FLANGE_CLASS_LIMIT,
    KEY_SD_FLANGE_SLENDERNESS,
    KEY_SD_HIGH_SHEAR,
    KEY_SD_IS_FQ,
    KEY_SD_IS_FQD,
    KEY_SD_IS_IYS_MIN,
    KEY_SD_IS_IYS_PROV,
    KEY_SD_LTB_CHI,
    KEY_SD_LTB_LAMBDA,
    KEY_SD_LTB_MB,
    KEY_SD_LTB_MCR,
    KEY_SD_MDV,
    KEY_SD_MD_CAPACITY,
    KEY_SD_MN_AXIAL,
    KEY_SD_MN_MOMENT,
    KEY_SD_MN_RATIO,
    KEY_SD_MU_APPLIED,
    KEY_SD_PANEL_CD,
    KEY_SD_PNA_DEPTH,
    KEY_SD_SC_D_LIMIT,
    KEY_SD_SC_EDGE_DIST,
    KEY_SD_SC_Qr_kN,
    KEY_SD_SC_Qu_kN,
    KEY_SD_SC_REQ_EDGE_DIST,
    KEY_SD_SC_SL1,
    KEY_SD_SC_SL2,
    KEY_SD_SC_SR,
    KEY_SD_SECTION_CLASS,
    KEY_SD_SECTION_PROP_AREA,
    KEY_SD_SECTION_PROP_IZ,
    KEY_SD_SECTION_PROP_ZUZ,
    KEY_SD_SECTION_PROP_ZZ,
    KEY_SD_SHEAR_AV,
    KEY_SD_SHEAR_KV,
    KEY_SD_SHEAR_LAMBDA_W,
    KEY_SD_SHEAR_TAU_B,
    KEY_SD_SHEAR_VCR,
    KEY_SD_SHEAR_VU,
    KEY_SD_STIFF_END_COUNT,
    KEY_SD_STIFF_END_THICK,
    KEY_SD_STIFF_INT_SPACING,
    KEY_SD_STIFF_INT_THICK,
    KEY_SD_STIFF_LONG,
    KEY_SD_STIFF_METHOD,
    KEY_SD_STRESS_STEEL,
    KEY_SD_STRESS_STEEL_ALLOWABLE,
    KEY_SD_TOP_FLANGE_THICKNESS,
    KEY_SD_TOP_FLANGE_WIDTH,
    KEY_SD_TOTAL_DEPTH,
    KEY_SD_TS_VL,
    KEY_SD_TS_VRD,
    KEY_SD_ULS_PER_GIRDER,
    KEY_SD_WEB_CLASS_LIMIT,
    KEY_SD_WEB_SLENDERNESS,
    KEY_SD_WEB_THICKNESS,
    KEY_SPAN,
    KEY_TS_DECK_OVERHANG,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_NO_OF_GIRDERS,
    KEY_UTIL_FLEXURE,
    KEY_UTIL_INTERACTION,
    KEY_UTIL_LTB,
    KEY_UTIL_SHEAR,
)

if TYPE_CHECKING:
    from .report_generator import ReportDataBridge


def _build_transverse_member_tables(bridge: "ReportDataBridge", kind: str, title_prefix: str) -> str:
    """Build Connection/Properties, Slenderness, and Capacity tables for Cross Bracing ('cb')
    or End Diaphragm ('ed'). Fixes the duplicated \\multirow{2} bug and uses real ED data.
    """
    pairs = bridge.get_tm_pairs(kind)
    prop_prefix = "cb" if kind == "cb" else "ed"
    chord_flag_pfx = (
        "member_properties.cross_bracing_details"
        if kind == "cb"
        else "member_properties.end_diaphragm_details"
    )

    # --- Table (a): Connection and Section Properties ---
    forces_rows = []
    if not pairs:
        forces_rows.append(
            r"Between Girders & Diagonal & --- & --- & --- & --- \\[4pt]" + "\n\\hline"
        )
    else:
        for pair in pairs:
            pair_id = pair.replace("-", "")
            pair_subrows = []
            for member, label in [("diagonal", "Diagonal"), ("chord", "Top / Bottom chord")]:
                _, ftype = bridge.get_tm_governing_force(kind, pair, member)
                conn_type = bridge.get_tm_connection(kind, pair, member, ftype) or "---"
                section = bridge.get_tm_section(kind, pair, member, ftype) or "---"

                if member == "diagonal":
                    pfx = f"transverse_member_design.{prop_prefix}.section_properties.bracing.{pair_id}"
                else:
                    pfx = f"transverse_member_design.{prop_prefix}.section_properties.bottom_chord.{pair_id}"
                    if bridge.output_dict.get(f"{pfx}.A") is None:
                        pfx = f"transverse_member_design.{prop_prefix}.section_properties.top_chord.{pair_id}"

                area_cm2 = bridge.output_dict.get(f"{pfx}.A")
                rv_cm = bridge.output_dict.get(f"{pfx}.rv")
                area_str = f"{float(area_cm2) * 100:.1f}" if area_cm2 is not None else "---"
                rmin_str = f"{float(rv_cm) * 10:.1f}" if rv_cm is not None else "---"
                pair_subrows.append((label, conn_type, section, area_str, rmin_str))

            # Emit \multirow{2} ONLY on the first row of each pair (fixes duplicate-label bug)
            lbl0, c0, s0, a0, r0 = pair_subrows[0]
            lbl1, c1, s1, a1, r1 = pair_subrows[1]
            forces_rows.append(
                rf"\multirow{{2}}{{*}}{{\makecell{{{_tex(pair)}}}}} & {lbl0} & {c0} & {s0} & {a0} & {r0} \\*" + "\n"
                r"\cline{2-6}" + "\n"
                rf" & {lbl1} & {c1} & {s1} & {a1} & {r1} \\[4pt]" + "\n"
                r"\hline"
            )

    t_props = make_longtable(
        caption=f"{title_prefix} --- Connection and Section Properties",
        headers=[
            "Panel",
            "Member",
            "Connection",
            "Section",
            r"$A_g$ (mm\textsuperscript{2})",
            r"$r_{min}$ (mm)",
        ],
        body_tex="\n".join(forces_rows),
        col_alignments=["C", "L", "L", "C", "C", "C"],
        col_widths_cm=[1.7, 2.5, 2.2, 2.8, 2.1, 2.0],
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\small",
        note=r"Note: $A_g$ = gross cross-sectional area; $r_{min}$ = minimum radius of gyration.",
    )

    # --- Table (b): Slenderness Ratio Check ---
    def _slnd_status(slnd_str, limit):
        try:
            v = float(slnd_str)
            return status_badge("PASS" if v <= limit else "FAIL")
        except (ValueError, TypeError):
            return "---"

    slenderness_rows = []
    if not pairs:
        slenderness_rows.append(
            r"Between Girders & Diagonal & C & --- & --- & --- \\[4pt]" + "\n\\hline"
        )
    else:
        for pair in pairs:
            kl_diag = bridge.get_tm_effective_length(kind, "diagonal") or "---"
            slnd_diag = bridge.get_tm_slenderness(kind, pair, "diagonal")
            st_diag = _slnd_status(slnd_diag, 250)

            kl_ch = bridge.get_tm_effective_length(kind, "chord") or "---"
            slnd_ch = bridge.get_tm_slenderness(kind, pair, "chord")
            st_tc = _slnd_status(slnd_ch, 250)
            st_bc = _slnd_status(slnd_ch, 400)

            top_on = bool(bridge.output_dict.get(f"{chord_flag_pfx}.top_chord", True))
            bot_on = bool(bridge.output_dict.get(f"{chord_flag_pfx}.bottom_chord", True))
            sub_entries = [
                ("Diagonal", "C", kl_diag, slnd_diag or "---", f"250 --- {st_diag}"),
            ]
            if top_on:
                sub_entries.append(("Top chord", "C", kl_ch, slnd_ch or "---", f"250 --- {st_tc}"))
            if bot_on:
                sub_entries.append(("Bottom chord", "T", kl_ch, slnd_ch or "---", f"400 --- {st_bc}"))

            n_sub = len(sub_entries)
            lines = []
            for idx, (m_lbl, nat, kl, sl, lim_st) in enumerate(sub_entries):
                lead = rf"\multirow{{{n_sub}}}{{*}}{{\makecell{{{_tex(pair)}}}}}" if idx == 0 else ""
                is_last = idx == n_sub - 1
                row_end = r" \\[4pt]" + "\n\\hline" if is_last else r" \\*" + "\n\\cline{2-6}"
                lines.append(f"{lead} & {m_lbl} & {nat} & {kl} & {sl} & {lim_st}{row_end}")
            slenderness_rows.append("\n".join(lines))

    t_slnd = make_longtable(
        caption=f"{title_prefix} --- Slenderness Ratio Check (IS~800 Cl.~3.8)",
        headers=["Panel", "Member", "Nature", r"Eff.\ Length $KL$ (mm)", r"$KL/r$", "Limit / Status"],
        body_tex="\n".join(slenderness_rows),
        col_alignments=["C", "L", "C", "C", "C", "C"],
        col_widths_cm=[1.9, 2.3, 1.4, 2.6, 1.8, 3.4],
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\small",
        note=r"Note: Limit = 250 for compression members, 400 for tension members. $K = 1.0$ for pinned ends.",
    )

    # --- Table (c): Capacity Summary ---
    cap_rows = []
    if not pairs:
        cap_rows.append(
            r"Between Girders & Diagonal & --- & --- & --- & --- & --- & --- \\[4pt]" + "\n\\hline"
        )
    else:
        for pair in pairs:
            sub_lines = []
            for idx, (member, label) in enumerate([("diagonal", "Diagonal"), ("chord", "Chord")]):
                force_str, ftype = bridge.get_tm_governing_force(kind, pair, member)
                section = bridge.get_tm_section(kind, pair, member, ftype) or "---"
                gov_lc = bridge.get_tm_gov_lc(kind, pair, member, ftype) or "---"
                capacity = bridge.get_tm_capacity(kind, pair, member, ftype) or "---"
                ur_s = bridge.get_tm_efficiency(kind, pair, member, ftype)
                ur_disp = ur_cell(float(ur_s), decimals=3) if ur_s else "---"
                status = bridge.get_tm_status(kind, pair, member, ftype) or "---"

                lead = rf"\multirow{{2}}{{*}}{{\makecell{{{_tex(pair)}}}}}" if idx == 0 else ""
                row_end = r" \\[4pt]" + "\n\\hline" if idx == 1 else r" \\*" + "\n\\cline{2-8}"
                sub_lines.append(
                    f"{lead} & {label} & {section} & {gov_lc} & {force_str or '---'} & {capacity} & {ur_disp} & {status}{row_end}"
                )
            cap_rows.append("\n".join(sub_lines))

    t_cap = make_longtable(
        caption=f"{title_prefix} Design --- Capacity Summary",
        headers=["Panel", "Member", "Section", "Governing LC", "Demand (kN)", "Capacity (kN)", "UR", "Status"],
        body_tex="\n".join(cap_rows),
        col_alignments=["C", "L", "C", "L", "C", "C", "C", "C"],
        col_widths_cm=[1.6, 1.5, 2.2, 3.0, 1.6, 1.6, 1.1, 1.5],
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\footnotesize",
        note=r"Note: Designed per IS 800 Cl. 7 (compression) and Cl. 6 (tension).",
    )

    return t_props + "\n\n" + t_slnd + "\n\n" + t_cap


def ch5_design_checks(checks_data, bridge: "ReportDataBridge", fig_paths: Optional[dict] = None) -> str:
    """Chapter 5 -- Design Checks."""
    fig_paths = fig_paths or {}
    girder_entries = get_girder_entries(bridge.input_dict)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1) or 1)
        girder_entries = [(f"Girder {i}", "M1") for i in range(1, n + 1)]

    deck_rpt = bridge.output_dict.get("deck_report_values", {}) or {}

    def _dfmt(v, nd=2):
        try:
            return f"{float(v):.{nd}f}"
        except (TypeError, ValueError):
            return ""

    def _interaction_status(ratio):
        if ratio < 0.90:
            return status_badge("PASS")
        if ratio < 1.00:
            return status_badge("WARN")
        return status_badge("FAIL")

    def _defl_status(actual, allowable):
        try:
            return status_badge("PASS" if float(actual) <= float(allowable) else "FAIL")
        except (TypeError, ValueError):
            return "---"

    def _ge_status(provided, required):
        try:
            return status_badge("PASS" if float(provided) >= float(required) else "FAIL")
        except (TypeError, ValueError):
            return "---"

    # --- Table 5.1: Girder Section Properties (uses banner rows — no tall \multirow{13}) ---
    t51_rows = []
    for lbl, _ in girder_entries:
        t51_rows.append(girder_banner_row(f"Girder {_tex(lbl)}", 2))
        props = [
            (r"Depth, D (mm)", _render_value(bridge.output_dict, KEY_SD_TOTAL_DEPTH)),
            (r"Top Flange Width, $b_f$ (mm)", _render_value(bridge.output_dict, KEY_SD_TOP_FLANGE_WIDTH)),
            (r"Bottom Flange Width, $b_f$ (mm)", _render_value(bridge.output_dict, KEY_SD_BOTTOM_FLANGE_WIDTH)),
            (r"Top Flange Thickness, $t_f$ (mm)", _render_value(bridge.output_dict, KEY_SD_TOP_FLANGE_THICKNESS)),
            (r"Bottom Flange Thickness, $t_f$ (mm)", _render_value(bridge.output_dict, KEY_SD_BOTTOM_FLANGE_THICKNESS)),
            (r"Web Thickness, $t_w$ (mm)", _render_value(bridge.output_dict, KEY_SD_WEB_THICKNESS)),
            (r"Gross Area, A (cm$^2$)", _render_value(bridge.output_dict, KEY_SD_SECTION_PROP_AREA)),
            (r"Moment of Inertia, $I_z$ (cm$^4$)", _render_value(bridge.output_dict, KEY_SD_SECTION_PROP_IZ)),
            (r"Elastic Section Modulus, $Z_{ez}$ (cm$^3$)", _render_value(bridge.output_dict, KEY_SD_SECTION_PROP_ZZ)),
            (r"Plastic Section Modulus, $Z_{pz}$ (cm$^3$)", _render_value(bridge.output_dict, KEY_SD_SECTION_PROP_ZUZ)),
            (r"Effective Slab Width, $b_{eff}$ (mm)", _render_value(bridge.output_dict, KEY_SD_EFFECTIVE_SLAB_WIDTH)),
            (r"Transformed Composite $I_z$ (cm$^4$)", _render_value(bridge.output_dict, KEY_SD_COMPOSITE_IZ)),
            (r"Depth to Plastic Neutral Axis (mm)", _render_value(bridge.output_dict, KEY_SD_PNA_DEPTH)),
        ]
        for k, v in props:
            t51_rows.append(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline")

    table_5_1 = make_longtable(
        caption="Girder Section Properties (Final Optimized / User-selected)",
        headers=["Property", "Value"],
        body_tex="\n".join(t51_rows),
        col_alignments=["L", "C"],
        col_widths_cm=[9.4, 5.6],
    )

    # --- Table 5.2: Section Classification (compact 3-row \multirow with \\*) ---
    t52_rows = []
    for lbl, _ in girder_entries:
        t52_rows.append(
            rf"\multirow{{3}}{{*}}{{\makecell{{{_tex(lbl)}}}}} & Top Flange & "
            + _render_value(bridge.output_dict, KEY_SD_FLANGE_SLENDERNESS) + " & "
            + _render_value(bridge.output_dict, KEY_SD_FLANGE_CLASS_LIMIT) + " & "
            + _render_value(bridge.output_dict, KEY_SD_CLASS_FLANGE) + r" \\*" + "\n\\cline{2-5}\n"
            + " & Web & "
            + _render_value(bridge.output_dict, KEY_SD_WEB_SLENDERNESS) + " & "
            + _render_value(bridge.output_dict, KEY_SD_WEB_CLASS_LIMIT) + " & "
            + _render_value(bridge.output_dict, KEY_SD_CLASS_WEB) + r" \\*" + "\n\\cline{2-5}\n"
            + " & Overall Section & --- & --- & "
            + _render_value(bridge.output_dict, KEY_SD_SECTION_CLASS) + r" \\[4pt]" + "\n\\hline"
        )
    table_5_2 = make_longtable(
        caption="Girder Section Classification",
        headers=["Girder", "Element", "Slenderness Ratio", "Class Limit", "Classification"],
        body_tex="\n".join(t52_rows),
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[2.0, 3.0, 3.2, 2.4, 3.8],
        note="Note: IS 800:2007 Table 2.",
    )

    # --- Table 5.3: Moment Capacity Check ---
    try:
        _flex_ur = float(bridge.output_dict.get(KEY_UTIL_FLEXURE)) / 100.0
        _flex_ur_str = ur_cell(_flex_ur)
        _flex_status = status_badge("PASS" if _flex_ur <= 1.0 else "FAIL")
    except (TypeError, ValueError):
        _flex_ur_str = "---"
        _flex_status = "---"
    t53_rows = []
    for lbl, _ in girder_entries:
        t53_rows.append(
            rf"\multirow{{3}}{{*}}{{\makecell{{{_tex(lbl)}}}}} & Applied Moment, $M_u$ & Governing LC (ULS) & "
            + _render_value(bridge.output_dict, KEY_SD_MU_APPLIED, " kN-m") + r" & --- \\*" + "\n\\cline{2-5}\n"
            + r" & Design Moment Capacity, $M_d$ & IRC 22 Cl. 603.3.1 & "
            + _render_value(bridge.output_dict, KEY_SD_MD_CAPACITY, " kN-m") + r" & --- \\*" + "\n\\cline{2-5}\n"
            + r" & Utilization Ratio, $M_u / M_d$ & $M_u / M_d$ & "
            + _flex_ur_str + " & " + _flex_status + r" \\[4pt]" + "\n\\hline"
        )
    table_5_3 = make_longtable(
        caption="Moment Capacity Check",
        headers=["Girder", "Parameter", "Formula", "Value", "Status"],
        body_tex="\n".join(t53_rows),
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[1.8, 3.6, 3.2, 3.8, 1.8],
        note="Note: IRC 22 Cl. 603.3.1, IS 800 Cl. 8.2.1.",
    )

    # --- Table 5.4: Shear Capacity Check (banner rows replace tall \multirow{8}) ---
    try:
        _shear_ur = float(bridge.output_dict.get(KEY_UTIL_SHEAR)) / 100.0
        _shear_ur_str = ur_cell(_shear_ur)
        _shear_status = status_badge("PASS" if _shear_ur <= 1.0 else "FAIL")
    except (TypeError, ValueError):
        _shear_ur_str = "---"
        _shear_status = "---"
    t54_rows = []
    for lbl, _ in girder_entries:
        t54_rows.append(girder_banner_row(f"Girder {_tex(lbl)}", 4))
        s_items = [
            (r"Applied Shear, $V_u$", "Governing LC (ULS)", _render_value(bridge.output_dict, KEY_SD_SHEAR_VU, " kN"), "---"),
            (r"Shear Area, $A_v$", r"$d_w \times t_w$", _render_value(bridge.output_dict, KEY_SD_SHEAR_AV, r" mm$^2$"), "---"),
            (r"Panel Aspect Ratio, $c/d$", "---", _render_value(bridge.output_dict, KEY_SD_PANEL_CD), "---"),
            (r"Shear Buckling Coefficient, $k_v$", "IS 800 Cl. 8.4.2.2", _render_value(bridge.output_dict, KEY_SD_SHEAR_KV), "---"),
            (r"Web Slenderness, $\lambda_w$", r"$\sqrt{f_{yw}/(\sqrt{3}\,\tau_{cr})}$", _render_value(bridge.output_dict, KEY_SD_SHEAR_LAMBDA_W), "---"),
            (r"Design Shear Stress, $\tau_b$", "IRC 22 Cl. 603.3.3.2", _render_value(bridge.output_dict, KEY_SD_SHEAR_TAU_B, " MPa"), "---"),
            (r"Shear Buckling Resistance, $V_{cr}$", r"$A_v \times \tau_b$", _render_value(bridge.output_dict, KEY_SD_SHEAR_VCR, " kN"), "---"),
            (r"Utilization Ratio, $V_u / V_d$", r"$V_u / V_d$", _shear_ur_str, _shear_status),
        ]
        for p, fml, val, st in s_items:
            t54_rows.append(f"{p} & {fml} & {val} & {st} " + r"\\[4pt]" + "\n\\hline")
    table_5_4 = make_longtable(
        caption="Shear Capacity Check",
        headers=["Parameter", "Formula", "Value", "Status"],
        body_tex="\n".join(t54_rows),
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[4.8, 3.8, 3.8, 2.0],
        note="Note: IS 800 Cl. 8.4, IRC 22 Cl. 603.3.3.2.",
    )

    # --- Table 5.5: Interaction Checks ---
    try:
        _mv_ur = float(bridge.output_dict.get(KEY_UTIL_INTERACTION)) / 100.0
        _mv_ur_str = ur_cell(_mv_ur)
        _mv_status = _interaction_status(_mv_ur)
    except (TypeError, ValueError):
        _mv_ur_str = "---"
        _mv_status = "---"
    _mn_r = bridge.output_dict.get(KEY_SD_MN_RATIO)
    _mn_ax = bridge.output_dict.get(KEY_SD_MN_AXIAL)
    _mn_mo = bridge.output_dict.get(KEY_SD_MN_MOMENT)
    if _mn_r is None or _mn_ax is None or _mn_mo is None:
        _mn_cond = _mn_val = _mn_status = na_cell("N/A")
    else:
        _mn_cond = f"{_mn_ax:.2f} + {_mn_mo:.2f} = {_mn_r:.3f}"
        _mn_val = ur_cell(_mn_r, decimals=3)
        _mn_status = _interaction_status(_mn_r)
    t55_rows = []
    for lbl, _ in girder_entries:
        t55_rows.append(
            rf"\multirow{{4}}{{*}}{{\makecell{{{_tex(lbl)}}}}} & High Shear Condition? & $V_u > 0.6\,V_d$ & "
            + _render_value(bridge.output_dict, KEY_SD_HIGH_SHEAR) + r" & --- \\*" + "\n\\cline{2-5}\n"
            + r" & Reduced Moment Capacity, $M_{dv}$ & IRC 22 Cl. 603.3.3.3 & "
            + _render_value(bridge.output_dict, KEY_SD_MDV, " kN-m") + r" & --- \\*" + "\n\\cline{2-5}\n"
            + r" & Interaction Check: $M_u \leq M_{dv}$ & --- & "
            + _mv_ur_str + " & " + _mv_status + r" \\*" + "\n\\cline{2-5}\n"
            + r" & Interaction Check: $N_u/N_{Rd} + M_u/M_{dv} \leq 1.0$ & "
            + _mn_cond + " & " + _mn_val + " & " + _mn_status + r" \\[4pt]" + "\n\\hline"
        )
    table_5_5 = make_longtable(
        caption="Interaction Checks (M-V and M-N)",
        headers=["Girder", "Check", "Condition", "Value", "Status"],
        body_tex="\n".join(t55_rows),
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[1.8, 4.0, 3.2, 3.4, 1.8],
        note="Note: IRC 22 Cl. 603.3.3.3.",
    )

    # --- Table 5.6: LTB Check (banner rows replace \multirow{5}) ---
    try:
        _ltb_ur = float(bridge.output_dict.get(KEY_UTIL_LTB)) / 100.0
        _ltb_ur_str = ur_cell(_ltb_ur)
        _ltb_status = _interaction_status(_ltb_ur)
    except (TypeError, ValueError):
        _ltb_ur_str = "---"
        _ltb_status = "---"
    t56_rows = []
    for lbl, _ in girder_entries:
        t56_rows.append(girder_banner_row(f"Girder {_tex(lbl)}", 4))
        l_items = [
            (r"Elastic Critical Moment, $M_{cr}$", "IRC 22 Cl. 603.3.3.1", _render_value(bridge.output_dict, KEY_SD_LTB_MCR, " kN-m"), "---"),
            (r"Non-dim. Slenderness, $\bar{\lambda}_{LT}$", r"$\sqrt{M_p / M_{cr}}$", _render_value(bridge.output_dict, KEY_SD_LTB_LAMBDA), "---"),
            (r"LTB Reduction Factor, $\chi_{LT}$", "IS 800 Cl. 8.2.2", _render_value(bridge.output_dict, KEY_SD_LTB_CHI), "---"),
            (r"LTB Resistance, $M_b$", r"$\chi_{LT}\,M_p / \gamma_{m0}$", _render_value(bridge.output_dict, KEY_SD_LTB_MB, " kN-m"), "---"),
            (r"$M_u \leq M_b$", r"$M_u / M_b$", _ltb_ur_str, _ltb_status),
        ]
        for p, fml, val, st in l_items:
            t56_rows.append(f"{p} & {fml} & {val} & {st} " + r"\\[4pt]" + "\n\\hline")
    table_5_6 = make_longtable(
        caption="Lateral Torsional Buckling Check -- Construction Stage",
        headers=["Parameter", "Formula", "Value", "Status"],
        body_tex="\n".join(t56_rows),
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[4.8, 3.8, 3.8, 2.0],
        note="Note: IRC 22 Cl. 603.3.3.1, IS 800 Cl. 8.2.2.",
    )

    # --- Table 5.7: Stiffener Design Summary (adds explicit header + banner rows) ---
    t57_rows = []
    for lbl, _ in girder_entries:
        t57_rows.append(girder_banner_row(f"Girder {_tex(lbl)}", 2))
        st_items = [
            ("Shear Buckling Design Method", _render_value(bridge.output_dict, KEY_SD_STIFF_METHOD)),
            ("Intermediate Stiffener Thickness (mm)", _render_value(bridge.output_dict, KEY_SD_STIFF_INT_THICK)),
            ("Intermediate Stiffener Spacing (mm)", _render_value(bridge.output_dict, KEY_SD_STIFF_INT_SPACING)),
            ("End Panel Stiffener Thickness (mm)", _render_value(bridge.output_dict, KEY_SD_STIFF_END_THICK)),
            ("No. of End Panel Stiffeners", _render_value(bridge.output_dict, KEY_SD_STIFF_END_COUNT)),
            ("Longitudinal Stiffeners", _render_value(bridge.output_dict, KEY_SD_STIFF_LONG)),
        ]
        for k, v in st_items:
            t57_rows.append(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline")
    table_5_7 = make_longtable(
        caption="Stiffener Design Summary",
        headers=["Parameter", "Value"],
        body_tex="\n".join(t57_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[7.5, 7.5],
    )

    # --- Table 5.8: Intermediate Stiffener Checks (Custom Mode only) ---
    _is_custom = str(bridge.input_dict.get(KEY_DESIGN_MODE, "Optimized")).strip().lower() in {"custom", "customized"}
    if _is_custom:
        _iys_status = _ge_status(bridge.output_dict.get(KEY_SD_IS_IYS_PROV), bridge.output_dict.get(KEY_SD_IS_IYS_MIN))
        _fqd_status = _ge_status(bridge.output_dict.get(KEY_SD_IS_FQD), bridge.output_dict.get(KEY_SD_IS_FQ))
        t58_rows = []
        for lbl, _ in girder_entries:
            t58_rows.append(
                rf"\multirow{{2}}{{*}}{{\makecell{{{_tex(lbl)}}}}} & Min. Moment of Inertia, $I_s$ & "
                + _render_value(bridge.output_dict, KEY_SD_IS_IYS_MIN, r" mm$^4$") + " & "
                + _render_value(bridge.output_dict, KEY_SD_IS_IYS_PROV, r" mm$^4$") + " & "
                + _iys_status + r" \\*" + "\n\\cline{2-5}\n"
                + r" & Buckling Resistance, $F_{qd} \geq F_q$ & "
                + _render_value(bridge.output_dict, KEY_SD_IS_FQ, " kN") + " & "
                + _render_value(bridge.output_dict, KEY_SD_IS_FQD, " kN") + " & "
                + _fqd_status + r" \\[4pt]" + "\n\\hline"
            )
        t58_block = "\n\n" + make_longtable(
            caption="Intermediate Stiffener Checks",
            headers=["Girder", "Check", "Required", "Provided", "Status"],
            body_tex="\n".join(t58_rows),
            col_alignments=["C", "L", "C", "C", "C"],
            col_widths_cm=[1.8, 4.0, 3.2, 3.4, 1.8],
            note="Note: IS 800 Cl. 8.7.1.2.",
        )
    else:
        t58_block = ""

    # --- Table 5.9: End Panel (Bearing) Stiffener Checks ---
    _bs_r = bridge.output_dict.get(KEY_SD_BS_R)

    def _bs_check(resist_key):
        prov = bridge.output_dict.get(resist_key)
        if prov is None or float(prov) <= 0.0 or _bs_r is None:
            return (na_cell("N/A"), na_cell("N/A"), na_cell("N/A"))
        return (f"{_bs_r} kN", f"{prov} kN", status_badge("PASS" if float(prov) >= float(_bs_r) else "FAIL"))

    _wb_req, _wb_prov, _wb_st = _bs_check(KEY_SD_BS_FCDW_WB)
    _lc_req, _lc_prov, _lc_st = _bs_check(KEY_SD_BS_FCDW_LC)
    _ps_req, _ps_prov, _ps_st = _bs_check(KEY_SD_BS_FPSD)
    _cb_req, _cb_prov, _cb_st = _bs_check(KEY_SD_BS_FCD)
    t59_rows = []
    for lbl, _ in girder_entries:
        t59_rows.append(
            rf"\multirow{{4}}{{*}}{{\makecell{{{_tex(lbl)}}}}} & Web Buckling Resistance & {_wb_req} & {_wb_prov} & {_wb_st} \\*" + "\n\\cline{2-5}\n"
            + f" & Local Crushing Resistance & {_lc_req} & {_lc_prov} & {_lc_st} " + r"\\*" + "\n\\cline{2-5}\n"
            + f" & Bearing Capacity & {_ps_req} & {_ps_prov} & {_ps_st} " + r"\\*" + "\n\\cline{2-5}\n"
            + f" & Column Buckling Resistance & {_cb_req} & {_cb_prov} & {_cb_st} " + r"\\[4pt]" + "\n\\hline"
        )
    table_5_9 = make_longtable(
        caption="End Panel Stiffener Checks",
        headers=["Girder", "Check", "Required", "Provided", "Status"],
        body_tex="\n".join(t59_rows),
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[1.8, 4.2, 3.2, 3.2, 1.8],
        note="Note: IS 800 Cl. 8.4.2.2.",
    )

    # --- Table 5.10: Serviceability Deflection Checks ---
    try:
        _span_m = float(bridge.input_dict.get(KEY_SPAN))
        _allow_live_mm = _span_m * 1000.0 / 800.0
        _allow_total_mm = _span_m * 1000.0 / 600.0
    except (TypeError, ValueError):
        _allow_live_mm = _allow_total_mm = None
    _allow_live_str = f"L/800 = {_allow_live_mm:.1f} mm" if _allow_live_mm is not None else "---"
    _allow_total_str = f"L/600 = {_allow_total_mm:.1f} mm" if _allow_total_mm is not None else "---"
    t510_rows = []
    for _gi, (lbl, _) in enumerate(girder_entries, start=1):
        _live_mm = bridge.output_dict.get(f"{KEY_SD_DEFL_LIVE}.G{_gi}")
        _total_mm = bridge.output_dict.get(f"{KEY_SD_DEFL_TOTAL}.G{_gi}")
        t510_rows.append(
            rf"\multirow{{2}}{{*}}{{\makecell{{{_tex(lbl)}}}}} & Live Load Deflection, $\delta_{{LL}}$ (mm) & "
            + _allow_live_str + " & " + (_dfmt(_live_mm, 3) or "---") + " & "
            + _defl_status(_live_mm, _allow_live_mm) + r" \\*" + "\n\\cline{2-5}\n"
            + r" & Total Load Deflection, $\delta_{total}$ (mm) & "
            + _allow_total_str + " & " + (_dfmt(_total_mm, 3) or "---") + " & "
            + _defl_status(_total_mm, _allow_total_mm) + r" \\[4pt]" + "\n\\hline"
        )
    table_5_10 = make_longtable(
        caption="Serviceability -- Deflection Checks",
        headers=["Girder", "Check", "Allowable", "Actual", "Status"],
        body_tex="\n".join(t510_rows),
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[1.8, 4.2, 3.4, 3.0, 1.8],
        note="Note: IRC 22 Cl. 604.3.2.",
    )

    # --- Table 5.11: SLS Steel Stress Limitation ---
    def _mpa(v):
        s = _dfmt(v, nd=2)
        return (s + " MPa") if s else "---"

    _dr_511 = bridge.output_dict.get("design_results", {}) or {}
    _steel_sigma = _dr_511.get(KEY_SD_STRESS_STEEL)
    _steel_allow = _dr_511.get(KEY_SD_STRESS_STEEL_ALLOWABLE)
    _steel_status = _defl_status(_steel_sigma, _steel_allow)
    t511_rows = [
        rf"\makecell{{{_tex(lbl)}}} & Structural Steel ($0.9\,f_y$) & {_mpa(_steel_allow)} & {_mpa(_steel_sigma)} & {_steel_status} \\[4pt]" + "\n\\hline"
        for lbl, _ in girder_entries
    ]
    table_5_11 = make_longtable(
        caption="Serviceability -- Maximum Stress Limitation",
        headers=["Girder", "Element", "Allowable Stress", "Actual Stress", "Status"],
        body_tex="\n".join(t511_rows),
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[1.8, 4.2, 3.2, 3.2, 1.8],
    )

    # --- Table 5.12: Fatigue Assessment ---
    _fat_cat = ((bridge.output_dict.get("design_results", {}) or {}).get(KEY_SD_ULS_PER_GIRDER, {}) or {}).get("fatigue", {}) or {}
    t512_rows = []
    for _gi, (lbl, _) in enumerate(girder_entries, start=1):
        _g = _fat_cat.get(f"G{_gi}", {}) or {}
        t512_rows.append(
            rf"\makecell{{{_tex(lbl)}}} & {_mpa(_g.get('demand'))} & {_mpa(_g.get('capacity'))} & "
            + ur_cell(_g.get("ur")) + " & " + status_badge(_g.get("status")) + r" \\[4pt]" + "\n\\hline"
        )
    table_5_12 = make_longtable(
        caption="Serviceability -- Fatigue Assessment",
        headers=["Girder", r"Stress Range, $\Delta\sigma$ (MPa)", r"Fatigue Limit, $f_{fd}$ (MPa)", "Utilization Ratio", "Status"],
        body_tex="\n".join(t512_rows),
        col_alignments=["C", "C", "C", "C", "C"],
        col_widths_cm=[1.8, 3.4, 3.4, 3.0, 2.4],
        note=r"Note: IRC 22 Cl. 605 --- governing of normal and shear fatigue (worst by DCR). Capacity reduction factor $\mu_r$ applied where plate thickness $>$ 25 mm.",
    )

    # --- Table 5.13: Girder Design Summary ---
    _pg_summary = (bridge.output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}

    def _with_unit(value, unit):
        s = _dfmt(value, nd=2)
        if not s:
            return "---"
        return (s + " " + _tex(unit)) if unit and str(unit) not in ("-", "\u2013") else s

    g_summary_rows = []
    for _gi, (lbl, _) in enumerate(girder_entries, start=1):
        g_data = _pg_summary.get(f"G{_gi}", {}) or {}
        checks = g_data.get("checks") or []
        if not checks:
            g_summary_rows.append(rf"{_tex(lbl)} & --- & --- & --- & --- & --- & --- \\[4pt]" + "\n\\hline")
            continue
        ctrl = max(checks, key=lambda c: c.get("dcr") or 0.0)
        ctrl_lc, best_dcr = None, None
        for lc_name, lc_data in (g_data.get("per_lc") or {}).items():
            if str(lc_name).lower().startswith("envelope"):
                continue
            for chk in lc_data.get("checks") or []:
                if chk.get("id") == ctrl.get("check_id"):
                    d = chk.get("dcr") or 0.0
                    if best_dcr is None or d > best_dcr:
                        best_dcr, ctrl_lc = d, lc_name
        if ctrl_lc is None:
            ctrl_lc = (g_data.get("demand") or {}).get("governing_combination") or ""
        g_summary_rows.append(
            f"{_tex(lbl)} & {_tex(str(ctrl_lc))} & {_tex(str(ctrl.get('name', '')))} & "
            f"{_with_unit(ctrl.get('demand'), ctrl.get('demand_unit'))} & "
            f"{_with_unit(ctrl.get('capacity'), ctrl.get('capacity_unit'))} & "
            f"{ur_cell(ctrl.get('dcr'), decimals=3)} & {status_badge(ctrl.get('status'))} "
            + r"\\[4pt]" + "\n\\hline"
        )
    table_5_13 = make_longtable(
        caption="Girder Design Summary (DCR / Utilization Ratio)",
        headers=["Girder", "Controlling LC / Combination", "Controlling Check", "Demand", "Capacity", "UR", "Status"],
        body_tex="\n".join(g_summary_rows),
        col_alignments=["C", "L", "C", "C", "C", "C", "C"],
        col_widths_cm=[1.3, 3.6, 2.3, 1.9, 1.9, 1.4, 1.5],
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\footnotesize",
        note=r"Note: UR = Demand / Capacity. A value $\leq 1.0$ indicates a passing check.",
    )

    # --- Tables 5.14, 5.15, 5.16: Shear Connectors ---
    _dr_sc = bridge.output_dict.get("design_results", {}) or {}

    def _kn(v):
        s = _dfmt(v, nd=2)
        return (s + " kN") if s else "---"

    def _mm(v):
        s = _dfmt(v, nd=1)
        return (s + " mm") if s else "---"

    def _cm2m(v):
        s = _dfmt(v, nd=2)
        return (s + r" cm$^2$/m") if s else "---"

    def _knm(v):
        s = _dfmt(v, nd=2)
        return (s + " kN/m") if s else "---"

    t514_body = (
        r"Design Resistance, $Q_u$ & \footnotesize\makecell{$Q_u=\min(Q_{u,s},\,Q_{u,c})$\\[3pt]$Q_{u,s}=\dfrac{0.8\,f_u\,(\pi d^2/4)}{\gamma_v}$\\[3pt]$Q_{u,c}=\dfrac{0.29\,\alpha\,d^2\sqrt{f_{ck}\,E_{cm}}}{\gamma_v}$} & "
        + _kn(_dr_sc.get(KEY_SD_SC_Qu_kN)) + r" & IRC 22 Cl. 606.3.1 (Eq. 6.1) \\[4pt]" + "\n\\hline\n"
        + r"Fatigue Shear Resistance, $Q_r$ & IRC 22 Table 8 ($\phi d$, $N_{sc}$) & "
        + _kn(_dr_sc.get(KEY_SD_SC_Qr_kN)) + r" & IRC 22 Cl. 606.3.2 (Table 8) \\[4pt]" + "\n\\hline"
    )
    table_5_14 = make_longtable(
        caption="Shear Connector Capacity",
        headers=["Parameter", "Formula", "Value", "Reference"],
        body_tex=t514_body,
        col_alignments=["L", "C", "C", "L"],
        col_widths_cm=[3.5, 5.4, 2.4, 3.0],
    )

    _sc_prov = _dr_sc.get("stud_spacing_provided_mm")
    _sc_prov_str = _mm(_sc_prov)
    t515_rows = [
        ("ULS Shear (SL1)", _dr_sc.get(KEY_SD_SC_SL1)),
        ("Full Composite (SL2)", _dr_sc.get(KEY_SD_SC_SL2)),
        ("SLS Fatigue (SR)", _dr_sc.get(KEY_SD_SC_SR)),
        ("Max Spacing Limit (IRC 22)", _dr_sc.get("stud_spacing_max_mm")),
    ]
    t515_body = "\n".join(
        f"{c} & {_mm(r)} & {_sc_prov_str} & {_defl_status(_sc_prov, r)} " + r"\\[4pt]" + "\n\\hline"
        for c, r in t515_rows
    )
    table_5_15 = make_longtable(
        caption="Shear Connector Spacing",
        headers=["Criterion", "Governing Spacing", "Actual Spacing Provided", "Status"],
        body_tex=t515_body,
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[3.8, 4.0, 4.0, 2.2],
        note=r"Note: IRC 22 Cl. 606.4, 606.9. Governing spacing $= \min(S_{L1}, S_{L2}, S_R)$.",
    )

    _ts_vl = _dr_sc.get(KEY_SD_TS_VL)
    _ts_vrd = _dr_sc.get(KEY_SD_TS_VRD)
    _ts_ur_str = "---"
    if _ts_vl is not None and _ts_vrd is not None:
        try:
            if float(_ts_vrd) > 0.0:
                _ts_ur_str = ur_cell(float(_ts_vl) / float(_ts_vrd))
        except (TypeError, ValueError):
            pass
    _ts_ok = _dr_sc.get("transverse_shear_ok")
    _ts_status = status_badge("FAIL" if _ts_ok is False else "PASS") if _ts_ok is not None else "---"

    _ast_req = _dr_sc.get("Ast_required_cm2_per_m")
    _dd_516 = bridge.output_dict.get("deck_design_results", {}) or {}
    try:
        _ast_prov = (float(_dd_516.get("rebar_bottom_area") or 0) + float(_dd_516.get("rebar_top_area") or 0)) / 100.0
    except (TypeError, ValueError):
        _ast_prov = None
    _stud_d = bridge.input_dict.get(KEY_DS_STUD_DIAMETER)
    _d_lim = _dr_sc.get(KEY_SD_SC_D_LIMIT)
    _edge = _dr_sc.get(KEY_SD_SC_EDGE_DIST)
    _edge_req = _dr_sc.get(KEY_SD_SC_REQ_EDGE_DIST)

    t516_items = [
        (r"Longitudinal Shear per unit length, $V_L$", _knm(_ts_vl), "---"),
        (r"Transverse Shear Capacity of Slab, $V_{Rd}$", _knm(_ts_vrd), "---"),
        ("Transverse Shear Check", r"$V_L/V_{Rd}$ = " + _ts_ur_str, _ts_status),
        (r"Min. Transverse Reinforcement, $A_{st,min}$", r"Required " + _cm2m(_ast_req) + ", Provided " + _cm2m(_ast_prov), _defl_status(_ast_req, _ast_prov)),
        (r"Stud Diameter $\leq 2\,t_f$", r"$d$ = " + _mm(_stud_d) + r" $\leq 2t_f$ = " + _mm(_d_lim), _defl_status(_stud_d, _d_lim)),
        ("Stud Edge Distance", r"Provided " + _mm(_edge) + r" (req. $\geq$ " + _mm(_edge_req) + ")", _defl_status(_edge_req, _edge)),
    ]
    t516_body = "\n".join(rf"\textnormal{{{c}}} & {v} & {s} \\[4pt]" + "\n\\hline" for c, v, s in t516_items)
    table_5_16 = make_longtable(
        caption="Transverse Shear and Detailing Checks",
        headers=["Check", "Value", "Status"],
        body_tex=t516_body,
        col_alignments=["L", "L", "C"],
        col_widths_cm=[5.2, 7.2, 2.0],
        note="Note: IRC 22 Cl. 606.6, 606.10.",
    )

    # --- Section 5.2: Deck Slab Design Tables 5.17(a)-(g) ---
    _dk_has = bool(deck_rpt)
    _dk_oh = bool(deck_rpt.get(KEY_DD_HAS_OVERHANG))
    _DKPH = r"\placeholder{---}"

    def _dkv(key, default=0.0):
        v = deck_rpt.get(key)
        if v is None or v == "":
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _dkf(key, nd=2, scale=1.0):
        if not _dk_has:
            return _DKPH
        v = deck_rpt.get(key)
        if v is None or v == "":
            return _DKPH
        try:
            return f"{float(v) * scale:.{nd}f}"
        except (TypeError, ValueError):
            return _tex(v)

    def _dks(ok):
        return status_badge("PASS" if ok else "FAIL") if _dk_has else "---"

    def _dkoh(key, nd=2, scale=1.0, unit=""):
        if not _dk_has:
            return _DKPH
        if not _dk_oh:
            return na_cell("N/A")
        return _dkf(key, nd=nd, scale=scale) + unit

    _dk_wks = [_dkv(KEY_DD_WK_BOT), _dkv(KEY_DD_WK_TOP)]
    if _dk_oh:
        _dk_wks.append(_dkv(KEY_DD_WK_OH))
    _dk_gov_wk = max(_dk_wks)
    _dk_gov_wk_str = f"{_dk_gov_wk:.4f}" if _dk_has else _DKPH
    _dk_crack_ok = _dk_has and _dk_gov_wk <= _dkv(KEY_DD_WK_LIMIT)

    # Table 5.17(a): Deck Slab Loading & Geometry (now has explicit header row + LaTeX superscripts)
    dk_geom_items = [
        (r"Effective Span of Deck Slab, $l_{eff}$", _dkf(KEY_DD_SPAN, 0, 1000.0) + " mm (girder spacing, c/c)"),
        (r"Deck Thickness, $t_s$", _render_value(bridge.input_dict, KEY_TS_DECK_THICKNESS, " mm")),
        ("Clear Cover (IRC 112 Cl. 15.2)", "Top " + _render_value(bridge.input_dict, KEY_DS_TOP_CLEAR_COVER) + " / Bottom " + _render_value(bridge.input_dict, KEY_DS_BOTTOM_CLEAR_COVER) + " mm"),
        ("Concrete Grade (IRC 112 Cl. 6.4)", _render_value(bridge.input_dict, KEY_DECK_CONCRETE_GRADE_BASIC) + r" ($f_{ck}$ = " + _render_value(bridge.input_dict, KEY_MATERIAL_DECK_FCK) + r" MPa, $f_{ctm}$ = " + _render_value(bridge.input_dict, KEY_MATERIAL_DECK_FCTM) + " MPa)"),
        ("Reinforcement Grade (IRC 112 Cl. 6.2)", _render_value(bridge.input_dict, KEY_DS_REINF_MATERIAL) + r" ($f_y$ = " + _dkf(KEY_DD_FY, 0) + " MPa)"),
        (r"Dead Load per Unit Area, $w_{DL}$", _dkf(KEY_DD_WDL, 2) + r" kN/m\textsuperscript{2} (slab self-weight)"),
        ("IRC 6 Wheel Load (Class A / 70R)", _dkf(KEY_DD_WHEEL_LOAD, 1) + " kN"),
        ("Tyre Contact Width (IRC 6 Annex~A)", _dkf(KEY_DD_TYRE_WIDTH, 0, 1000.0) + " mm (transverse)"),
        ("Impact Factor (IRC 6 Cl. 208.2)", _dkf(KEY_DD_IMPACT_FACTOR, 3)),
        ("Governing Live Load Case", _dkf(KEY_DD_VEHICLE)),
    ]
    table_5_17a = make_longtable(
        caption="Deck Slab --- Loading and Geometry",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in dk_geom_items),
        col_alignments=["L", "L"],
        col_widths_cm=[5.6, 9.6],
    )

    # Table 5.17(b): Flexure Interior Panel
    t517b_body = (
        rf"\multirow{{5}}{{*}}{{\makecell{{At Midspan\\(Sagging)}}}} & Transverse BM (DL), $M_{{T,DL}}$ & $w_{{DL}}\,l_{{eff}}^2/10$ & {_dkf(KEY_DD_M_DL, 2)} kN-m/m & --- \\*" + "\n\\cline{2-5}\n"
        + rf" & Transverse BM (LL), $M_{{T,LL}}$ & Effective width (IRC 112 B3.1) & {_dkf(KEY_DD_M_LL, 2)} kN-m/m & --- \\*" + "\n\\cline{2-5}\n"
        + rf" & Total Design BM, $M_{{u,sag}}$ & {_dkf(KEY_DD_GAMMA_DL, 2)} DL + {_dkf(KEY_DD_GAMMA_LL, 2)} LL & {_dkf(KEY_DD_M_ULS_SAG, 2)} kN-m/m & --- \\*" + "\n\\cline{2-5}\n"
        + rf" & Effective depth, $d$ & $t_s - c_{{nom}} - \phi/2$ & {_dkf(KEY_DD_D_BOT, 1)} mm & --- \\*" + "\n\\cline{2-5}\n"
        + rf" & Moment Capacity, $M_{{Rd}}$ & IRC 112 Cl. 12.2 & {_dkf(KEY_DD_MU_BOT, 2)} kN-m/m & {_dks(_dkv(KEY_DD_MU_BOT) >= _dkv(KEY_DD_M_ULS_SAG))} \\[4pt]" + "\n\\hline\n"
        + rf"\multirow{{3}}{{*}}{{\makecell{{At Support\\(Hogging)}}}} & Total Design BM, $M_{{u,hog}}$ & {_dkf(KEY_DD_GAMMA_DL, 2)} DL + {_dkf(KEY_DD_GAMMA_LL, 2)} LL (at support) & {_dkf(KEY_DD_M_ULS_HOG, 2)} kN-m/m & --- \\*" + "\n\\cline{2-5}\n"
        + rf" & Required Top Steel, $A_{{st,top}}$ & $M_u / (0.87\,f_y\,d)$ & {_dkf(KEY_DD_AS_REQ_TOP, 0)} mm\textsuperscript{{2}}/m & --- \\*" + "\n\\cline{2-5}\n"
        + rf" & Moment Capacity, $M_{{Rd}}$ & IRC 112 Cl. 12.2 & {_dkf(KEY_DD_MU_TOP, 2)} kN-m/m & {_dks(_dkv(KEY_DD_MU_TOP) >= _dkv(KEY_DD_M_ULS_HOG))} \\[4pt]" + "\n\\hline"
    )
    table_5_17b = make_longtable(
        caption="Deck Slab --- Flexure Check: Interior Panel (Pigeaud's Method)",
        headers=["Location", "Parameter", "Formula / Reference", "Value", "Status"],
        body_tex=t517b_body,
        col_alignments=["C", "L", "C", "C", "C"],
        col_widths_cm=[2.6, 3.4, 3.0, 3.6, 1.8],
        note=r"Note: IRC 112 Cl. 12.2. Distribution (longitudinal) reinforcement designed for 20\% of main steel moment (IRC 21 Cl. 305.18).",
    )

    # Table 5.17(c): Cantilever Overhang Flexure
    oh_cap_st = _dks(_dkv(KEY_DD_MU_OH) >= _dkv(KEY_DD_M_ULS_OH)) if _dk_oh else (na_cell("N/A") if _dk_has else "---")
    t517c_items = [
        (r"Overhang Length, $l_{oh}$", "---", _render_value(bridge.input_dict, KEY_TS_DECK_OVERHANG, " m"), "---"),
        ("Crash Barrier Load Moment", "IRC 6 Cl. 206.4", _dkoh(KEY_DD_M_BARRIER, 2, unit=" kN-m/m"), "---"),
        ("Dead Load Moment", r"$w_{DL}\,l_{oh}^2/2$ + railing", _dkoh(KEY_DD_M_DL_OH, 2, unit=" kN-m/m"), "---"),
        ("Live Load Moment (eccentric wheel)", r"Wheel load $\times$ arm", _dkoh(KEY_DD_M_LL_OH, 2, unit=" kN-m/m"), "---"),
        (r"Total Hogging Moment, $M_{u,oh}$", f"{_dkf(KEY_DD_GAMMA_DL, 2)} DL + {_dkf(KEY_DD_GAMMA_LL, 2)} (LL + CB)", _dkoh(KEY_DD_M_ULS_OH, 2, unit=" kN-m/m"), "---"),
        (r"Moment Capacity (top steel), $M_{Rd,oh}$", "IRC 112 Cl. 12.2", _dkoh(KEY_DD_MU_OH, 2, unit=" kN-m/m"), oh_cap_st),
    ]
    table_5_17c = make_longtable(
        caption="Deck Slab --- Cantilever Overhang Flexure Check",
        headers=["Parameter", "Formula", "Value", "Status"],
        body_tex="\n".join(f"{p} & {f} & {v} & {s} " + r"\\[4pt]" + "\n\\hline" for p, f, v, s in t517c_items),
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[5.2, 3.4, 4.0, 2.0],
        note="Note: IRC 6 Cl. 206.4 crash barrier loads applied at kerb face; IRC 112 Cl. 12.2 flexure.",
    )

    # Table 5.17(d): Punching Shear
    punch_ur = ur_cell(_dkv(KEY_DD_PUNCH_VED) / _dkv(KEY_DD_VRD_C_MPA)) if (_dk_has and _dkv(KEY_DD_VRD_C_MPA) > 0) else _DKPH
    t517d_items = [
        (r"Design Wheel Load (ULS), $V_{Ed}$", r"$\gamma_Q\,(1+IF)\,P_w$", _dkf(KEY_DD_PUNCH_VED_KN, 1) + " kN", "---"),
        ("Tyre Contact Area", r"$a \times b$ (IRC 6 Annex~A)", _dkf(KEY_DD_TYRE_WIDTH, 0, 1000.0) + r" $\times$ " + _dkf(KEY_DD_TYRE_LENGTH, 0) + " mm", "---"),
        (r"Loaded Area at mid-depth, $b_0$", r"$c_1 \times c_2$ (incl.\ WC dispersion)", _dkf(KEY_DD_PUNCH_C1, 0) + r" $\times$ " + _dkf(KEY_DD_PUNCH_C2, 0) + " mm", "---"),
        (r"Control Perimeter, $u_1$", r"$2(c_1+c_2) + 4\pi d$", _dkf(KEY_DD_PUNCH_U1, 0) + " mm", "---"),
        (r"Punching Shear Stress, $v_{Ed}$", r"$V_{Ed} / (u_1\,d)$", _dkf(KEY_DD_PUNCH_VED, 3) + " MPa", "---"),
        (r"Punching Resistance, $v_{Rd,c}$", r"IRC 112 Eq.\ 10.1", _dkf(KEY_DD_VRD_C_MPA, 3) + " MPa", "---"),
        ("Punching Shear Check", r"$v_{Ed} \leq v_{Rd,c}$", punch_ur, _dks(bool(deck_rpt.get(KEY_DD_PUNCH_OK)))),
    ]
    table_5_17d = make_longtable(
        caption=r"Deck Slab --- Punching Shear Check (IRC~112 Cl.~10.4.6)",
        headers=["Parameter", "Formula / Reference", "Value", "Status"],
        body_tex="\n".join(f"{p} & {f} & {v} & {s} " + r"\\[4pt]" + "\n\\hline" for p, f, v, s in t517d_items),
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[5.2, 3.4, 4.0, 2.0],
        note=r"Note: Punching shear reinforcement not typically required for deck slabs with $d \geq 200$ mm and adequate longitudinal reinforcement.",
    )

    # Table 5.17(e): Crack Width
    t517e_items = [
        (r"Min. Reinforcement for Crack Control, $A_{s,min}$", _dkf(KEY_DD_AS_MIN, 0) + r" mm\textsuperscript{2}/m [IRC 112 Cl. 16.5.1]"),
        ("Provided Reinforcement (bottom)", r"$\phi$" + _dkf(KEY_DD_DIA_BOT, 0) + " @ " + _dkf(KEY_DD_SPC_BOT, 0) + " mm c/c (" + _dkf(KEY_DD_AS_BOT, 0) + r" mm\textsuperscript{2}/m)"),
        ("Max. Permissible Crack Width", _dkf(KEY_DD_WK_LIMIT, 2) + " mm"),
        (r"Calculated Crack Width, $w_k$ (governing)", _dk_gov_wk_str + " mm"),
        ("Crack Width Check", _dks(_dk_crack_ok)),
    ]
    table_5_17e = make_longtable(
        caption="Crack Width Check (Deck Slab)",
        headers=["Parameter", "Value / Reference"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in t517e_items),
        col_alignments=["L", "L"],
        col_widths_cm=[6.8, 8.4],
    )

    # Table 5.17(f): One-Way Shear
    k_sz = f"{min(1.0 + (200.0 / _dkv(KEY_DD_D_BOT)) ** 0.5, 2.0):.3f}" if (_dk_has and _dkv(KEY_DD_D_BOT) > 0) else _DKPH
    rho_l = f"{min(_dkv(KEY_DD_AS_BOT) / (1000.0 * _dkv(KEY_DD_D_BOT)), 0.02):.4f}" if (_dk_has and _dkv(KEY_DD_D_BOT) > 0) else _DKPH
    ow_ur = ur_cell(_dkv(KEY_DD_SHEAR_VED) / _dkv(KEY_DD_SHEAR_VRDC)) if (_dk_has and _dkv(KEY_DD_SHEAR_VRDC) > 0) else _DKPH
    t517f_items = [
        (r"Design Shear per unit width, $V_{Ed}$", r"$\gamma_{DL} V_{DL} + \gamma_{LL}(1{+}IF)V_{LL}$", _dkf(KEY_DD_SHEAR_VED, 2) + " kN/m", "---"),
        (r"Effective depth, $d$", r"$t_s - c_{nom} - \phi/2$", _dkf(KEY_DD_D_BOT, 1) + " mm", "---"),
        (r"Size factor, $k$", r"$1 + \sqrt{200/d} \leq 2.0$", k_sz, "---"),
        (r"Long.\ reinforcement ratio, $\rho_l$", r"$A_{sl}/(b_w\,d) \leq 0.02$", rho_l, "---"),
        (r"Shear resistance (no stirrups), $V_{Rd,c}$", r"$v_{Rd,c}\,b_w\,d$ (Cl.\ 10.3.2)", _dkf(KEY_DD_SHEAR_VRDC, 2) + " kN/m", "---"),
        ("One-Way Shear Check", r"$V_{Ed} \leq V_{Rd,c}$", ow_ur, _dks(bool(deck_rpt.get(KEY_DD_SHEAR_OK)))),
    ]
    table_5_17f = make_longtable(
        caption="One-Way (Beam) Shear Check (Deck Slab)",
        headers=["Parameter", "Formula / Reference", "Value", "Status"],
        body_tex="\n".join(f"{p} & {f} & {v} & {s} " + r"\\[4pt]" + "\n\\hline" for p, f, v, s in t517f_items),
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[5.2, 3.4, 4.0, 2.0],
        note="Note: IRC 112 Cl. 10.3.2. Shear reinforcement not provided in deck slabs; capacity relies on concrete and main reinforcement.",
    )

    # Table 5.17(g): Reinforcement Detailing Summary
    t517g_body = "\n".join([
        girder_banner_row("Main Reinforcement --- Bottom (Transverse)", 4),
        rf"Required Area, $A_{{st,req}}$ (mm\textsuperscript{{2}}/m) & {_dkf(KEY_DD_AS_REQ_BOT, 0)} mm\textsuperscript{{2}}/m & {_dkf(KEY_DD_AS_BOT, 0)} mm\textsuperscript{{2}}/m & {_dks(_dkv(KEY_DD_AS_BOT) >= _dkv(KEY_DD_AS_REQ_BOT))} \\[4pt]" + "\n\\hline",
        rf"Bar Diameter $\times$ Spacing & $\phi \geq 10$ mm (IRC 112) & $\phi${_dkf(KEY_DD_DIA_BOT, 0)} @ {_dkf(KEY_DD_SPC_BOT, 0)} mm c/c & --- \\[4pt]" + "\n\\hline",
        rf"Min.\ Reinforcement $A_{{s,min}}$ (IRC 112 Cl. 16.3.1) & {_dkf(KEY_DD_AS_MIN, 0)} mm\textsuperscript{{2}}/m & {_dkf(KEY_DD_AS_BOT, 0)} mm\textsuperscript{{2}}/m & {_dks(_dkv(KEY_DD_AS_BOT) >= _dkv(KEY_DD_AS_MIN))} \\[4pt]" + "\n\\hline",
        rf"Max.\ Bar Spacing (IRC 112 Cl. 16.3.2) & {_dkf(KEY_DD_SPACING_MAX, 0)} mm & {_dkf(KEY_DD_SPC_BOT, 0)} mm & {_dks(0.0 < _dkv(KEY_DD_SPC_BOT) <= _dkv(KEY_DD_SPACING_MAX))} \\[4pt]" + "\n\\hline",
        girder_banner_row("Distribution Reinforcement --- Longitudinal", 4),
        rf"Required Area, $A_{{st,dist}}$ (mm\textsuperscript{{2}}/m) & $\geq 20\%$ of main steel & {_dkf(KEY_DD_AS_LONG, 0)} mm\textsuperscript{{2}}/m & {_dks(_dkv(KEY_DD_AS_LONG) >= max(0.20 * _dkv(KEY_DD_AS_BOT), _dkv(KEY_DD_AS_MIN)))} \\[4pt]" + "\n\\hline",
        girder_banner_row("Top Reinforcement (Support / Cantilever Overhang)", 4),
        rf"Required Area, $A_{{st,top}}$ (mm\textsuperscript{{2}}/m) & {_dkf(KEY_DD_AS_REQ_TOP, 0)} mm\textsuperscript{{2}}/m & {_dkf(KEY_DD_AS_TOP, 0)} mm\textsuperscript{{2}}/m & {_dks(_dkv(KEY_DD_AS_TOP) >= _dkv(KEY_DD_AS_REQ_TOP))} \\[4pt]" + "\n\\hline",
        girder_banner_row("Cover and Detailing", 4),
        rf"Clear Cover (IRC 112 Cl. 15.2) & $\geq$ {_dkf(KEY_DD_MIN_COVER, 0)} mm (Table 14.2) & Top {_render_value(bridge.input_dict, KEY_DS_TOP_CLEAR_COVER)} / Bottom {_render_value(bridge.input_dict, KEY_DS_BOTTOM_CLEAR_COVER)} mm & {_dks(bool(deck_rpt.get(KEY_DD_COVER_OK)))} \\[4pt]" + "\n\\hline",
    ])
    table_5_17g = make_longtable(
        caption="Reinforcement Detailing Summary (Deck Slab)",
        headers=["Parameter", "Required / Limit", "Provided", "Status"],
        body_tex=t517g_body,
        col_alignments=["L", "C", "C", "C"],
        col_widths_cm=[5.2, 3.8, 3.8, 1.8],
        note="Note: IRC 112 Cl. 16.3, IS 456 Cl. 26.5.",
    )

    # --- Section 5.3: Cross Bracing & Section 5.4: End Diaphragm (real data!) ---
    cb_tables_tex = _build_transverse_member_tables(bridge, "cb", "Cross Bracing")
    ed_is_bracing = bridge.is_ed_bracing()
    if ed_is_bracing:
        ed_tables_tex = _build_transverse_member_tables(bridge, "ed", "End Diaphragm")
    else:
        ed_tables_tex = (
            r"\noindent " + na_cell("Rolled / Welded beam end diaphragm design checks are not yet implemented in this version.")
        )

    # --- Section 5.5: Overall Design Check Summary (Table 5.22 + UR Summary Chart) ---
    _pg_522 = (bridge.output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}

    def _vu_522(v, unit):
        s = _dfmt(v, nd=2)
        if not s:
            return ""
        u = (unit or "").strip()
        return (s + " " + _tex(u)) if u else s

    def _lc_short(lc):
        return _tex(str(lc).strip())

    def _gov_lc_in_522(g, check_ids):
        gd = _pg_522.get(g) or {}
        best = None
        for _lc, _ld in (gd.get("per_lc") or {}).items():
            if str(_lc).lower().startswith("envelope"):
                continue
            for _chk in (_ld.get("checks") or []):
                if _chk.get("id") in check_ids:
                    _d = _chk.get("dcr") or 0.0
                    if best is None or _d > best[0]:
                        best = (_d, _lc)
        return _lc_short(best[1]) if best else "---"

    def _dcr_row(check_ids, fallback_unit=""):
        best = None
        for g, gd in _pg_522.items():
            if str(g).startswith("EB"):
                continue
            for chk in (gd.get("checks") or []):
                if chk.get("check_id") in check_ids:
                    d = chk.get("dcr") or 0.0
                    if best is None or d > best[0]:
                        best = (
                            d,
                            chk.get("demand"),
                            chk.get("capacity"),
                            chk.get("demand_unit") or "",
                            chk.get("capacity_unit") or "",
                            g,
                        )
        if best is not None:
            d, dem, cap, du, cu, g = best
            return (_gov_lc_in_522(g, check_ids), _vu_522(dem, du) or "---", _vu_522(cap, cu) or "---", ur_cell(d))
        best = None
        for g, gd in _pg_522.items():
            if str(g).startswith("EB"):
                continue
            for _lc, _ld in (gd.get("per_lc") or {}).items():
                if str(_lc).lower().startswith("envelope"):
                    continue
                for chk in (_ld.get("checks") or []):
                    if chk.get("id") in check_ids:
                        d = chk.get("dcr") or 0.0
                        if best is None or d > best[0]:
                            best = (d, chk.get("demand"), chk.get("capacity"), _lc)
        if best is None:
            return ("---", "---", "---", "---")
        d, dem, cap, _lc = best
        return (_lc_short(_lc), _vu_522(dem, fallback_unit) or "---", _vu_522(cap, fallback_unit) or "---", ur_cell(d))

    def _tm_row(kind, force_type):
        pairs = bridge.get_tm_pairs(kind)
        best = None
        for pair in pairs:
            for member in ("diagonal", "chord"):
                cap = bridge.get_tm_capacity(kind, pair, member, force_type)
                eff = bridge.get_tm_efficiency(kind, pair, member, force_type)
                try:
                    ur = float(eff)
                except (TypeError, ValueError):
                    continue
                if best is None or ur > best[0]:
                    best = (ur, pair, member, cap)
        if best is None:
            return ("---", "---", "---", "---")
        ur, pair, member, cap = best
        gov = bridge.get_tm_gov_lc(kind, pair, member, force_type) or "---"
        dem = f"{float(cap) * ur:.2f} kN" if cap else "---"
        cap_s = (cap + " kN") if cap else "---"
        return (gov, dem, cap_s, ur_cell(ur))

    def _tm_slender_row(kind):
        pairs = bridge.get_tm_pairs(kind)
        best = None
        for pair in pairs:
            for member in ("diagonal", "chord"):
                s = bridge.get_tm_slenderness(kind, pair, member)
                try:
                    sf = float(s)
                except (TypeError, ValueError):
                    continue
                lim = 400.0 if member == "chord" else 250.0
                ratio = sf / lim
                if best is None or ratio > best[0]:
                    best = (ratio, sf, lim)
        if best is None:
            return ("---", "---", "---", "---")
        ratio, sf, lim = best
        return ("---", f"{sf:.1f}", f"{lim:.0f}", ur_cell(ratio))

    def _row522(label, cells):
        c = [x if x else "---" for x in cells]
        return label + " & " + " & ".join(c) + r" \\[4pt]" + "\n\\hline"

    def _row522_msg(label, msg):
        return label + r" & \multicolumn{4}{c|}{" + msg + r"} \\[4pt]" + "\n\\hline"

    _deck_combo = (
        r"Basic ULS: " + _tex(f"{_dkv(KEY_DD_GAMMA_DL):g}DL + {_dkv(KEY_DD_GAMMA_LL):g}LL")
    ) if _dk_has else "---"

    def _deck_row(dem_key, cap_key, unit, is_oh=False):
        if not _dk_has:
            return ("---", "---", "---", "---")
        if is_oh and not _dk_oh:
            return (_deck_combo, na_cell("N/A"), na_cell("N/A"), na_cell("N/A"))
        dem = _dkv(dem_key)
        cap = _dkv(cap_key)
        ur = (dem / cap) if cap > 0 else None
        return (_deck_combo, f"{dem:.2f} {unit}", f"{cap:.2f} {unit}", ur_cell(ur))

    def _gov_sls_frequent():
        best = None
        for _g, _gd in _pg_522.items():
            if str(_g).startswith("EB"):
                continue
            for _lc, _ld in (_gd.get("per_lc") or {}).items():
                if "frequent" not in str(_lc).lower():
                    continue
                _d = _ld.get("max_dcr") or 0.0
                if best is None or _d > best[0]:
                    best = (_d, _lc)
        return _tex(str(best[1]).strip()) if best else "Frequent SLS"

    _wk_lim = _dkv(KEY_DD_WK_LIMIT)
    _crack_cells = (
        (_gov_sls_frequent() if _dk_has else "---"),
        (f"{_dk_gov_wk:.3f} mm" if _dk_has else "---"),
        (f"{_wk_lim:.3f} mm" if _dk_has else "---"),
        (ur_cell(_dk_gov_wk / _wk_lim) if (_dk_has and _wk_lim > 0) else "---"),
    )

    if ed_is_bracing:
        _ed_comp_row = _row522(r"End Diaphragm --- Compression", _tm_row("ed", "compression"))
        _ed_tens_row = _row522(r"End Diaphragm --- Tension", _tm_row("ed", "tension"))
    else:
        _ed_msg = na_cell("N/A (Rolled / Welded section design not yet implemented)")
        _ed_comp_row = _row522_msg(r"End Diaphragm --- Moment", _ed_msg)
        _ed_tens_row = _row522_msg(r"End Diaphragm --- Shear", _ed_msg)

    _t522 = [
        _row522(r"Girder --- Moment", _dcr_row({1})),
        _row522(r"Girder --- Shear", _dcr_row({2})),
        _row522(r"Girder --- LTB (constr.)", _dcr_row({5})),
        _row522(r"Girder --- Deflection", _dcr_row({13, 14}, fallback_unit="mm")),
        _row522(r"Girder --- Stress", _dcr_row({11}, fallback_unit="MPa")),
        _row522(r"Girder --- Fatigue", _dcr_row({8, 9}, fallback_unit="MPa")),
        _row522(r"Transverse Shear (slab)", _dcr_row({16})),
        _row522(r"Crack Width (slab)", _crack_cells),
        _row522(r"Deck --- Flexure (sagging)", _deck_row(KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT, "kN-m/m")),
        _row522(r"Deck --- Flexure (hogging)", _deck_row(KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP, "kN-m/m")),
        _row522(r"Deck --- Cantilever Overhang", _deck_row(KEY_DD_M_ULS_OH, KEY_DD_MU_OH, "kN-m/m", is_oh=True)),
        _row522(r"Deck --- Punching Shear", _deck_row(KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA, "MPa")),
        _row522(r"Deck --- One-Way Shear", _deck_row(KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC, "kN/m")),
        _row522(r"Cross Bracing --- Compression", _tm_row("cb", "compression")),
        _row522(r"Cross Bracing --- Tension", _tm_row("cb", "tension")),
        _row522(r"Cross Bracing --- Slenderness", _tm_slender_row("cb")),
        _ed_comp_row,
        _ed_tens_row,
    ]
    table_5_22 = make_longtable(
        caption="Overall Design Check Summary --- All Members",
        headers=["Member / Check", "Governing Load Combo", "Demand", "Capacity", "UR"],
        body_tex="\n".join(_t522),
        col_alignments=["L", "L", "C", "C", "C"],
        col_widths_cm=[3.4, 4.6, 2.3, 2.3, 1.5],
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\small",
        note=r"Note: UR = Demand / Capacity. All values $\leq 1.0$ indicate passing checks.",
    )

    ur_chart_path = fig_paths.get("ur_summary_chart")
    ur_chart_block = ""
    if ur_chart_path:
        ur_chart_block = "\n\n" + _fig_numbered(
            ur_chart_path,
            r"Overall Utilization Ratio ($UR = \text{Demand}/\text{Capacity}$) Summary Across Primary Bridge Components (Threshold $UR = 1.0$)",
            label="fig:overall-ur-summary",
            width=r"0.90\textwidth",
        )

    return (
        r"""
\chapter{Design Checks}

This section presents all structural design checks performed by OsdagBridge. For each member, the demand from the governing load combination, the code-based capacity, and the utilization ratio are tabulated. All checks reference IS 800:2007 and IRC 22:2014 unless stated otherwise.

\section{Plate Girder Design}
\label{sec:plate-girder}

"""
        + table_5_1 + "\n\n"
        + table_5_2 + "\n\n"
        + table_5_3 + "\n\n"
        + table_5_4 + "\n\n"
        + table_5_5 + "\n\n"
        + table_5_6 + "\n\n"
        + table_5_7
        + t58_block + "\n\n"
        + table_5_9 + "\n\n"
        + table_5_10 + "\n\n"
        + table_5_11 + "\n\n"
        + table_5_12 + "\n\n"
        + table_5_13 + "\n\n"
        + table_5_14 + "\n\n"
        + table_5_15 + "\n\n"
        + table_5_16
        + r"""

\section{Deck Slab Design}
\label{sec:deck-design}

The reinforced concrete deck slab is designed per IRC~112:2011 (flexure, shear, crack width) and IRC~22:2014 (composite construction). Wheel loads are distributed using Pigeaud's method. The deck is checked for flexure in the transverse and longitudinal directions, punching shear, one-way (beam) shear, crack width, and reinforcement detailing.

"""
        + table_5_17a + "\n\n"
        + table_5_17b + "\n\n"
        + table_5_17c + "\n\n"
        + table_5_17d + "\n\n"
        + table_5_17e + "\n\n"
        + table_5_17f + "\n\n"
        + table_5_17g
        + r"""

\section{Cross Bracing Design}
\label{sec:cross-bracing}

Cross bracing between adjacent plate girders provides lateral stability during construction, resists transverse loads (wind, seismic, braking) in service, and prevents lateral torsional buckling of the girders. Members are designed per IS~800:2007 Cl.~7 (compression) and Cl.~6 (tension).

"""
        + cb_tables_tex
        + r"""

\section{End Diaphragm Design}
\label{sec:end-diaphragm}

End diaphragms at the supports transfer transverse loads to the bearings, restrain the bottom flanges against lateral displacement, and maintain the girder cross-section geometry during construction and in service. They are designed per IS~800:2007 and IRC~24:2010 Cl.~507.

"""
        + ed_tables_tex
        + r"""

\section{Overall Design Check Summary}
\label{sec:overall-summary}

"""
        + table_5_22
        + ur_chart_block
        + "\n"
    )
