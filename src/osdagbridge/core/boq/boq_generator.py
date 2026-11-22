# =============================================================================
# OsdagBridge — BOQ (Bill of Quantities) Generator
# =============================================================================

import logging
import math
from typing import Any, Optional

from osdagbridge.core.utils.common import (
    KEY_MP_ED_BRACING_TYPE,
    KEY_MP_ED_TYPE,
    KEY_MP_GIRDER_DEPTH,
    KEY_SD_TOTAL_DEPTH,
    KEY_SPAN,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS,
)

logger = logging.getLogger("osdagbridge.core.boq_generator")

STEEL_DENSITY_KG_M3 = 7850.0
STEEL_DENSITY_MT_M3 = 7.85
CONCRETE_DENSITY_MT_M3 = 2.5


def resolve_girder_value(source: dict, base_key: str, i: int = 0) -> Any:
    """Resolve a girder property from an input/output dict, tolerating both the
    per-girder dynamic key scheme and the legacy scalar key.
    """
    candidates = [
        f"{base_key}.G{i + 1}.M1",
        base_key,
        f"{base_key}.G1.M1",
    ]
    for key in candidates:
        if key in source:
            return source[key]
    raise KeyError(base_key)


def _to_meters(val: Any, is_thickness: bool = False) -> Optional[float]:
    """Convert a dimension that may be in mm or already mutated to m into metres.

    Uses dimension-specific thresholds so plate thicknesses in mm (e.g. 8 mm)
    are never confused with values in metres (< 0.5 m).
    """
    if val in (None, ""):
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if f <= 0:
        return None
    threshold = 0.5 if is_thickness else 10.0
    return f if f < threshold else (f / 1000.0)


def _find_prefixed_value(source: dict, prefix: str) -> Any:
    """Return the first non-empty value in ``source`` whose key matches or starts with ``prefix``."""
    if not isinstance(source, dict):
        return None
    if source.get(prefix) not in (None, ""):
        return source[prefix]
    dot_prefix = prefix + "."
    for k, v in source.items():
        if str(k).startswith(dot_prefix) and v not in (None, ""):
            return v
    return None


def _bool_flag(inputs: dict, outputs: dict, key: str, default: bool = True) -> bool:
    """Read a boolean toggle from outputs or inputs (tolerating per-pair suffix keys)."""
    for src in (outputs, inputs):
        val = _find_prefixed_value(src, key)
        if val is not None:
            if isinstance(val, bool):
                return val
            s = str(val).strip().lower()
            if s in ("false", "0", "no", "none", "off"):
                return False
            if s in ("true", "1", "yes", "on"):
                return True
    return default


def _section_multiplier(design_results: dict, pair_key: str, member: str) -> float:
    """Return 2.0 when a designed section is a double-angle/channel ('2-...'), else 1.0."""
    try:
        from osdagbridge.core.reports.report_utils import extract_osdag_member_summary
        pair_map = (design_results or {}).get(pair_key, {}) or {}
        member_map = pair_map.get(member, {}) or {}
        for ft in ("compression", "tension"):
            sec = str(extract_osdag_member_summary(member_map.get(ft) or {}).get("section") or "").strip()
            if sec.startswith("2-") or sec.lower().startswith("2 "):
                return 2.0
    except Exception:
        pass
    return 1.0


def _resolve_girder_depth_m(inputs: dict, outputs: dict) -> Optional[float]:
    """Return girder total depth in metres (preferring guaranteed-mm output_dict)."""
    d_out = (outputs or {}).get(KEY_SD_TOTAL_DEPTH)
    if d_out not in (None, ""):
        try:
            f = float(d_out)
            if f > 0:
                return f / 1000.0 if f >= 10.0 else f
        except (TypeError, ValueError):
            pass
    try:
        return _to_meters(resolve_girder_value(inputs, KEY_MP_GIRDER_DEPTH, 0), is_thickness=False)
    except KeyError:
        return None


def calculate_material_quantities(inputs: dict, outputs: dict) -> dict:
    """Calculate quantities (steel tonnage, concrete volume, rebar, studs,
    cross bracing, and end diaphragms) for Chapter 7 and MTO charts.

    Returns formatted display strings plus a ``_numeric`` dict with raw floats
    (or ``None`` when unavailable/not applicable) so chart modules never parse
    LaTeX strings.
    """
    inputs = inputs or {}
    outputs = outputs or {}

    numeric = {
        "steel_girders_mt": None,
        "steel_cross_bracing_mt": None,
        "steel_end_diaphragms_mt": None,
        "concrete_deck_m3": None,
        "rebar_deck_mt": None,
        "ed_is_bracing": False,
    }

    quantities = {
        "steel_girders_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_girders_qty": "N.A.",
        "steel_girders_vol_total": "N.A.",
        "steel_girders_wt_single": "N.A.",
        "steel_girders_wt_total": "N.A.",

        "steel_bracing_vol_formula": r"\placeholder{Area $\times$ Length}",
        "steel_bracing_qty": "N.A.",
        "steel_bracing_vol_total": "N.A.",
        "steel_bracing_wt_single": "N.A.",
        "steel_bracing_wt_total": "N.A.",

        "bracing_top_vol_formula": "N.A.",
        "bracing_top_qty": "N.A.",
        "bracing_top_vol_total": "N.A.",
        "bracing_top_wt_single": "N.A.",
        "bracing_top_wt_total": "N.A.",

        "bracing_bot_vol_formula": "N.A.",
        "bracing_bot_qty": "N.A.",
        "bracing_bot_vol_total": "N.A.",
        "bracing_bot_wt_single": "N.A.",
        "bracing_bot_wt_total": "N.A.",

        "bracing_diag_vol_formula": "N.A.",
        "bracing_diag_qty": "N.A.",
        "bracing_diag_vol_total": "N.A.",
        "bracing_diag_wt_single": "N.A.",
        "bracing_diag_wt_total": "N.A.",

        "ed_steel_vol_formula": "N.A.",
        "ed_steel_qty": "N.A.",
        "ed_steel_vol_total": "N.A.",
        "ed_steel_wt_single": "N.A.",
        "ed_steel_wt_total": "N.A.",

        "concrete_deck_vol_formula": r"\placeholder{Width $\times$ Thickness $\times$ Length}",
        "concrete_deck_qty": "N.A.",
        "concrete_deck_vol_total": "N.A.",
        "concrete_deck_wt_single": "N.A.",
        "concrete_deck_wt_total": "N.A.",

        "rebar_deck_vol_formula": r"\placeholder{Area $\times$ Length}",
        "rebar_deck_qty": "N.A.",
        "rebar_deck_vol_total": "N.A.",
        "rebar_deck_wt_single": "N.A.",
        "rebar_deck_wt_total": "N.A.",

        "shear_studs_vol_formula": "N.A.",
        "shear_studs_qty": "N.A.",
        "shear_studs_vol_total": "N.A.",
        "shear_studs_wt_single": "N.A.",
        "shear_studs_wt_total": "N.A.",

        "crash_barrier_vol_formula": "N.A.",
        "crash_barrier_qty": "N.A.",
        "crash_barrier_vol_total": "N.A.",
        "crash_barrier_wt_single": "N.A.",
        "crash_barrier_wt_total": "N.A.",

        "_numeric": numeric,
    }

    try:
        span_val = inputs.get(KEY_SPAN)
        n_girders_val = inputs.get(KEY_TS_NO_OF_GIRDERS)
        if span_val is None or n_girders_val is None:
            return quantities

        try:
            span = float(span_val)
            n_girders = int(n_girders_val)
        except Exception:
            return quantities

        if span <= 0 or n_girders <= 0:
            return quantities

        # ------------------------------------------------------------------
        # 1. Concrete Deck Slab Volume (m^3) & Weight (MT) + Reinforcement
        # ------------------------------------------------------------------
        overall_width_val = inputs.get("typical_section.overall_bridge_width")
        deck_thickness_val = inputs.get(KEY_TS_DECK_THICKNESS)

        if overall_width_val is not None and deck_thickness_val is not None:
            try:
                overall_width = float(overall_width_val)
                deck_thickness = float(deck_thickness_val)
                if deck_thickness > 2.0:  # mm -> m
                    deck_thickness /= 1000.0
                if overall_width > 0 and deck_thickness > 0:
                    concrete_vol = span * overall_width * deck_thickness
                    quantities["concrete_deck_vol_formula"] = (
                        f"${overall_width:.2f}\\text{{ m}} \\times {deck_thickness:.2f}\\text{{ m}} "
                        f"\\times {span:.2f}\\text{{ m}} = {concrete_vol:.2f}\\text{{ m}}^3$"
                    )
                    quantities["concrete_deck_qty"] = "1"
                    quantities["concrete_deck_vol_total"] = f"{concrete_vol:.2f}"
                    quantities["concrete_deck_wt_single"] = f"{(concrete_vol * CONCRETE_DENSITY_MT_M3):.2f}"
                    quantities["concrete_deck_wt_total"] = f"{(concrete_vol * CONCRETE_DENSITY_MT_M3):.2f}"
                    numeric["concrete_deck_m3"] = round(concrete_vol, 3)

                    # 2. Reinforcement Steel (preliminary 120 kg/m^3 estimate)
                    rebar_wt_kg = concrete_vol * 120.0
                    rebar_vol = rebar_wt_kg / STEEL_DENSITY_KG_M3
                    rebar_area = rebar_vol / span if span > 0 else 0.0
                    quantities["rebar_deck_vol_formula"] = (
                        f"${rebar_area:.6f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {rebar_vol:.5f}\\text{{ m}}^3$"
                    )
                    quantities["rebar_deck_qty"] = "1"
                    quantities["rebar_deck_vol_total"] = f"{rebar_vol:.2f}"

                    rebar_wt_mt = rebar_wt_kg / 1000.0
                    quantities["rebar_deck_wt_single"] = f"{rebar_wt_mt:.2f}"
                    quantities["rebar_deck_wt_total"] = f"{rebar_wt_mt:.2f}"
                    numeric["rebar_deck_mt"] = round(rebar_wt_mt, 3)
            except Exception:
                pass

        # ------------------------------------------------------------------
        # 3. Structural Steel Girders (prefer final optimized A_steel_mm2)
        # ------------------------------------------------------------------
        girder_area = 0.0
        used_optimized_area = False
        dr = outputs.get("design_results", {}) or {}
        opt_a_mm2 = dr.get("A_steel_mm2")
        if opt_a_mm2 not in (None, ""):
            try:
                f_a = float(opt_a_mm2)
                if f_a > 0:
                    girder_area = f_a / 1e6  # mm^2 -> m^2
                    used_optimized_area = True
            except (TypeError, ValueError):
                pass

        if girder_area <= 0:
            try:
                a_in = float(resolve_girder_value(inputs, "member_properties.girder_details.section_properties.area", 0))
                if a_in > 0:
                    # Handle m^2 (< 2) vs cm^2 (2..5000) vs mm^2 (> 5000)
                    if a_in < 2.0:
                        girder_area = a_in
                    elif a_in < 5000.0:
                        girder_area = a_in / 1e4
                    else:
                        girder_area = a_in / 1e6
            except Exception:
                pass

        if girder_area <= 0:
            try:
                dw = _to_meters(resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_depth", 0), False)
                tw = _to_meters(resolve_girder_value(inputs, "member_properties.girder_details.section_input.web_thickness", 0), True)
                bft = _to_meters(resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_width", 0), False)
                tft = _to_meters(resolve_girder_value(inputs, "member_properties.girder_details.section_input.top_flange_thickness", 0), True)
                bfb = _to_meters(resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_width", 0), False)
                tfb = _to_meters(resolve_girder_value(inputs, "member_properties.girder_details.section_input.bottom_flange_thickness", 0), True)
                if all(v is not None for v in (dw, tw, bft, tft, bfb, tfb)):
                    girder_area = (dw * tw) + (bft * tft) + (bfb * tfb)
            except Exception:
                pass

        if girder_area > 0:
            girder_vol = girder_area * span
            girder_total_vol = n_girders * girder_vol
            quantities["steel_girders_vol_formula"] = (
                f"${girder_area:.5f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {girder_vol:.5f}\\text{{ m}}^3$"
            )
            quantities["steel_girders_qty"] = str(n_girders)
            quantities["steel_girders_vol_total"] = f"{girder_total_vol:.2f}"

            if used_optimized_area:
                total_girder_mass = girder_total_vol * STEEL_DENSITY_KG_M3
            else:
                total_girder_mass = 0.0
                for gi in range(n_girders):
                    try:
                        mass_per_m = float(
                            resolve_girder_value(inputs, "member_properties.girder_details.section_properties.mass", gi)
                        )
                        total_girder_mass += mass_per_m * span
                    except Exception:
                        total_girder_mass += girder_vol * STEEL_DENSITY_KG_M3

            single_girder_wt = (total_girder_mass / n_girders) / 1000.0
            total_girder_wt = total_girder_mass / 1000.0
            quantities["steel_girders_wt_single"] = f"{single_girder_wt:.2f}"
            quantities["steel_girders_wt_total"] = f"{total_girder_wt:.2f}"
            numeric["steel_girders_mt"] = round(total_girder_wt, 3)

        # ------------------------------------------------------------------
        # 4. Shear Stud Connectors
        # ------------------------------------------------------------------
        spacing_mm = 0.0
        studs_per_sec = 0
        stud_d = 0.0
        stud_h_mm = 0.0

        spacing_val = outputs.get("steeldesign.details.shear.longitudinal_spacing")
        studs_val = outputs.get("steeldesign.details.shear.studs_per_section")
        stud_d_val = outputs.get("steeldesign.details.shear.diameter") or inputs.get("design_options.shear_studs.diameter")
        stud_h_val = outputs.get("steeldesign.details.shear.height") or inputs.get("design_options.shear_studs.height")

        if spacing_val is not None and studs_val is not None and stud_d_val is not None and stud_h_val is not None:
            try:
                spacing_mm = float(spacing_val)
                studs_per_sec = int(studs_val)
                stud_d = float(stud_d_val)
                stud_h_mm = float(stud_h_val)
            except Exception:
                pass

        if spacing_mm > 0.0 and studs_per_sec > 0 and stud_d > 0.0 and stud_h_mm > 0.0:
            stud_h = stud_h_mm / 1000.0
            n_sections = int(span * 1000.0 / spacing_mm) + 1
            total_studs = n_girders * studs_per_sec * n_sections

            stud_area = (math.pi * (stud_d / 1000.0) ** 2) / 4.0
            stud_vol = stud_area * stud_h
            quantities["shear_studs_vol_formula"] = (
                f"${stud_area:.6f}\\text{{ m}}^2 \\times {stud_h:.3f}\\text{{ m}} = {stud_vol:.6f}\\text{{ m}}^3$"
            )
            quantities["shear_studs_qty"] = str(total_studs)

            studs_total_vol = total_studs * stud_vol
            quantities["shear_studs_vol_total"] = f"{studs_total_vol:.2f}"

            single_stud_wt = stud_vol * STEEL_DENSITY_MT_M3
            total_studs_wt = studs_total_vol * STEEL_DENSITY_MT_M3
            quantities["shear_studs_wt_single"] = f"{single_stud_wt:.6f}"
            quantities["shear_studs_wt_total"] = f"{total_studs_wt:.3f}"

        # ------------------------------------------------------------------
        # 5. Cross Bracing Steel (per-pair areas, actual chord areas & flags)
        # ------------------------------------------------------------------
        spacing_val = inputs.get(KEY_TS_GIRDER_SPACING)
        spacing = 0.0
        if spacing_val is not None:
            try:
                spacing = float(spacing_val)
            except Exception:
                pass

        cb_forces = outputs.get("crossbracing_forces_dict") or {}
        cb_geom = cb_forces.get("geometry") or {}
        cb_designs = outputs.get("crossbracing_design_results") or {}

        bracing_len = 0.0
        if cb_geom.get("diagonal_length_m") is not None:
            try:
                bracing_len = float(cb_geom["diagonal_length_m"])
            except Exception:
                pass

        n_bays = max(0, n_girders - 1)
        top_chord_enabled = _bool_flag(inputs, outputs, "member_properties.cross_bracing_details.top_chord", default=True)
        bot_chord_enabled = _bool_flag(inputs, outputs, "member_properties.cross_bracing_details.bottom_chord", default=True)

        cb_spacing_val = cb_geom.get("cb_spacing_m")
        cb_spacing = 0.0
        if cb_spacing_val is not None:
            try:
                cb_spacing = float(cb_spacing_val)
            except Exception:
                pass
        n_panels = max(1, round(span / cb_spacing) - 1) if cb_spacing > 0.0 else max(3, int(span / 5.0))

        def _pair_area_m2(kind: str, member_slot: str, pair_id: str, fallback_pair_id: str = "G1G2") -> float:
            raw = outputs.get(f"transverse_member_design.{kind}.section_properties.{member_slot}.{pair_id}.A")
            if raw is None and pair_id != fallback_pair_id:
                raw = outputs.get(f"transverse_member_design.{kind}.section_properties.{member_slot}.{fallback_pair_id}.A")
            if raw is None:
                return 0.0
            try:
                return float(raw) / 10000.0  # cm^2 -> m^2
            except (TypeError, ValueError):
                return 0.0

        if n_bays > 0 and bracing_len > 0.0 and spacing > 0.0:
            diag_vol_total = 0.0
            top_vol_total = 0.0
            bot_vol_total = 0.0
            rep_diag_area = 0.0
            rep_top_area = 0.0
            rep_bot_area = 0.0

            for bay_i in range(1, n_bays + 1):
                pair_id = f"G{bay_i}G{bay_i + 1}"
                pair_dash = f"G{bay_i}-G{bay_i + 1}"
                d_area = _pair_area_m2("cb", "bracing", pair_id) * _section_multiplier(cb_designs, pair_dash, "diagonal")
                if d_area <= 0.0:
                    continue
                if rep_diag_area <= 0.0:
                    rep_diag_area = d_area
                diag_vol_total += (n_panels * 2) * d_area * bracing_len

                if top_chord_enabled:
                    t_base = _pair_area_m2("cb", "top_chord", pair_id)
                    if t_base <= 0.0:
                        t_base = _pair_area_m2("cb", "bracing", pair_id)
                    t_area = t_base * _section_multiplier(cb_designs, pair_dash, "chord")
                    if rep_top_area <= 0.0:
                        rep_top_area = t_area
                    top_vol_total += n_panels * t_area * spacing

                if bot_chord_enabled:
                    b_base = _pair_area_m2("cb", "bottom_chord", pair_id)
                    if b_base <= 0.0:
                        b_base = _pair_area_m2("cb", "bracing", pair_id)
                    b_area = b_base * _section_multiplier(cb_designs, pair_dash, "chord")
                    if rep_bot_area <= 0.0:
                        rep_bot_area = b_area
                    bot_vol_total += n_panels * b_area * spacing

            if rep_diag_area > 0.0:
                # 5a. Top Chord
                top_qty = n_bays * n_panels if top_chord_enabled else 0
                top_wt_total = top_vol_total * STEEL_DENSITY_MT_M3
                if top_chord_enabled and top_qty > 0:
                    top_vol_single = top_vol_total / top_qty
                    quantities["bracing_top_vol_formula"] = (
                        f"${rep_top_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {top_vol_single:.5f}\\text{{ m}}^3$"
                    )
                    quantities["bracing_top_qty"] = str(top_qty)
                    quantities["bracing_top_vol_total"] = f"{top_vol_total:.2f}"
                    quantities["bracing_top_wt_single"] = f"{(top_vol_single * STEEL_DENSITY_MT_M3):.4f}"
                    quantities["bracing_top_wt_total"] = f"{top_wt_total:.2f}"
                else:
                    quantities["bracing_top_qty"] = "0"
                    quantities["bracing_top_vol_total"] = "0.00"
                    quantities["bracing_top_wt_total"] = "0.00"

                # 5b. Bottom Chord
                bot_qty = n_bays * n_panels if bot_chord_enabled else 0
                bot_wt_total = bot_vol_total * STEEL_DENSITY_MT_M3
                if bot_chord_enabled and bot_qty > 0:
                    bot_vol_single = bot_vol_total / bot_qty
                    quantities["bracing_bot_vol_formula"] = (
                        f"${rep_bot_area:.5f}\\text{{ m}}^2 \\times {spacing:.2f}\\text{{ m}} = {bot_vol_single:.5f}\\text{{ m}}^3$"
                    )
                    quantities["bracing_bot_qty"] = str(bot_qty)
                    quantities["bracing_bot_vol_total"] = f"{bot_vol_total:.2f}"
                    quantities["bracing_bot_wt_single"] = f"{(bot_vol_single * STEEL_DENSITY_MT_M3):.4f}"
                    quantities["bracing_bot_wt_total"] = f"{bot_wt_total:.2f}"
                else:
                    quantities["bracing_bot_qty"] = "0"
                    quantities["bracing_bot_vol_total"] = "0.00"
                    quantities["bracing_bot_wt_total"] = "0.00"

                # 5c. Diagonal
                diags_qty = n_bays * n_panels * 2
                diag_vol_single = diag_vol_total / diags_qty
                diag_wt_total = diag_vol_total * STEEL_DENSITY_MT_M3
                quantities["bracing_diag_vol_formula"] = (
                    f"${rep_diag_area:.5f}\\text{{ m}}^2 \\times {bracing_len:.2f}\\text{{ m}} = {diag_vol_single:.5f}\\text{{ m}}^3$"
                )
                quantities["bracing_diag_qty"] = str(diags_qty)
                quantities["bracing_diag_vol_total"] = f"{diag_vol_total:.2f}"
                quantities["bracing_diag_wt_single"] = f"{(diag_vol_single * STEEL_DENSITY_MT_M3):.4f}"
                quantities["bracing_diag_wt_total"] = f"{diag_wt_total:.2f}"

                cb_total_mt = top_wt_total + bot_wt_total + diag_wt_total
                numeric["steel_cross_bracing_mt"] = round(cb_total_mt, 3)

        # ------------------------------------------------------------------
        # 6. End Diaphragm Steel (strictly gated on Cross Bracing ED type)
        # ------------------------------------------------------------------
        ed_type_str = str(_find_prefixed_value(inputs, KEY_MP_ED_TYPE) or "").strip()
        ed_is_bracing = "brac" in ed_type_str.lower()
        numeric["ed_is_bracing"] = ed_is_bracing

        if ed_is_bracing and n_bays > 0 and spacing > 0.0:
            ed_designs = outputs.get("end_diaphragm_design_results") or {}
            d_m = _resolve_girder_depth_m(inputs, outputs)
            ed_btype = str(_find_prefixed_value(inputs, KEY_MP_ED_BRACING_TYPE) or "X").strip().upper()
            ed_top_on = _bool_flag(inputs, outputs, "member_properties.end_diaphragm_details.top_chord", default=True)
            ed_bot_on = _bool_flag(inputs, outputs, "member_properties.end_diaphragm_details.bottom_chord", default=True)

            if d_m and d_m > 0.0:
                h_m = 0.85 * d_m
                horiz_proj = (spacing / 2.0) if ed_btype.startswith("K") else spacing
                ed_diag_len = math.hypot(horiz_proj, h_m)
                n_ends = 2  # Left and right support frames

                ed_total_vol = 0.0
                ed_total_members = 0
                rep_ed_area = 0.0

                for bay_i in range(1, n_bays + 1):
                    pair_id = f"G{bay_i}G{bay_i + 1}"
                    pair_dash = f"G{bay_i}-G{bay_i + 1}"
                    d_area = _pair_area_m2("ed", "bracing", pair_id) * _section_multiplier(ed_designs, pair_dash, "diagonal")
                    if d_area <= 0.0:
                        continue
                    if rep_ed_area <= 0.0:
                        rep_ed_area = d_area
                    # 2 diagonals per bay per end
                    ed_total_vol += (n_ends * 2) * d_area * ed_diag_len
                    ed_total_members += n_ends * 2

                    if ed_top_on:
                        t_base = _pair_area_m2("ed", "top_chord", pair_id) or _pair_area_m2("ed", "bracing", pair_id)
                        t_area = t_base * _section_multiplier(ed_designs, pair_dash, "chord")
                        ed_total_vol += n_ends * t_area * spacing
                        ed_total_members += n_ends

                    if ed_bot_on:
                        b_base = _pair_area_m2("ed", "bottom_chord", pair_id) or _pair_area_m2("ed", "bracing", pair_id)
                        b_area = b_base * _section_multiplier(ed_designs, pair_dash, "chord")
                        ed_total_vol += n_ends * b_area * spacing
                        ed_total_members += n_ends

                if ed_total_vol > 0.0 and ed_total_members > 0:
                    ed_total_wt = ed_total_vol * STEEL_DENSITY_MT_M3
                    ed_vol_per_end = ed_total_vol / float(n_ends)
                    ed_wt_per_end = ed_total_wt / float(n_ends)
                    quantities["ed_steel_vol_formula"] = (
                        f"${n_bays}\\text{{ bays}} \\times {ed_vol_per_end / n_bays:.4f}\\text{{ m}}^3/\\text{{end}}$"
                    )
                    quantities["ed_steel_qty"] = f"{n_ends} ends ({ed_total_members} pcs)"
                    quantities["ed_steel_vol_total"] = f"{ed_total_vol:.2f}"
                    quantities["ed_steel_wt_single"] = f"{ed_wt_per_end:.2f}"
                    quantities["ed_steel_wt_total"] = f"{ed_total_wt:.2f}"
                    numeric["steel_end_diaphragms_mt"] = round(ed_total_wt, 3)

        # ------------------------------------------------------------------
        # 7. Crash Barrier (m^3 and MT)
        # ------------------------------------------------------------------
        cb_area_val = inputs.get("typical_section.crash_barrier.area")
        cb_area = 0.0
        if cb_area_val is not None:
            try:
                cb_area = float(cb_area_val) / 1e6
            except Exception:
                pass

        if cb_area > 0.0:
            cb_vol = cb_area * span
            quantities["crash_barrier_vol_formula"] = (
                f"${cb_area:.5f}\\text{{ m}}^2 \\times {span:.2f}\\text{{ m}} = {cb_vol:.5f}\\text{{ m}}^3$"
            )
            quantities["crash_barrier_qty"] = "2"

            cb_total_vol = 2 * cb_vol
            quantities["crash_barrier_vol_total"] = f"{cb_total_vol:.2f}"

            single_cb_wt = cb_vol * CONCRETE_DENSITY_MT_M3
            total_cb_wt = cb_total_vol * CONCRETE_DENSITY_MT_M3
            quantities["crash_barrier_wt_single"] = f"{single_cb_wt:.2f}"
            quantities["crash_barrier_wt_total"] = f"{total_cb_wt:.2f}"

    except Exception as exc:
        logger.warning(f"Error calculating material quantities: {exc}")

    return quantities
