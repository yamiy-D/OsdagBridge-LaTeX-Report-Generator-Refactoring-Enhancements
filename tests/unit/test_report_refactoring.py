"""Unit and integration tests for OsdagBridge LaTeX report refactoring (R1-R6)."""

from __future__ import annotations

import inspect
import os
import re
import sys
from unittest.mock import patch

import pytest

# Ensure local src/ is importable even without editable pip install
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from osdagbridge.core.boq.boq_generator import calculate_material_quantities
from osdagbridge.core.reports import charts, styles
from osdagbridge.core.reports.chap1 import ch1_project_info
from osdagbridge.core.reports.chap2 import ch2_input_parameters
from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.reports.chap4 import ch4_analysis
from osdagbridge.core.reports.chap5 import ch5_design_checks
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.reports.chap8 import ch8_design_log
from osdagbridge.core.reports.executive_summary import executive_summary
from osdagbridge.core.reports.report_generator import (
    ReportDataBridge,
    ReportMetadata,
    ReportOptions,
    ReportPayload,
    ReportRequest,
    build_report_payload,
    generate_report,
)
from osdagbridge.core.reports.report_utils import _tex
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV,
    KEY_CARRIAGEWAY_WIDTH,
    KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_DESIGN_MODE,
    KEY_DS_REINF_MATERIAL,
    KEY_FOOTPATH,
    KEY_GIRDER,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MP_ED_BRACING_TYPE,
    KEY_MP_ED_TYPE,
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS,
    KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH,
    KEY_MP_GIRDER_DEPTH,
    KEY_MP_GIRDER_TOP_FLANGE_THICKNESS,
    KEY_MP_GIRDER_TOP_FLANGE_WIDTH,
    KEY_MP_GIRDER_WEB_THICKNESS,
    KEY_SD_TOTAL_DEPTH,
    KEY_SL_SEISMIC_ZONE,
    KEY_SPAN,
    KEY_STRUCTURE_TYPE,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS,
    KEY_TS_OVERALL_WIDTH,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_TERRAIN_TYPE,
)


def _sample_4_girder_inputs_and_outputs(ed_type="Cross Bracing", failing_girder=False):
    inputs = {
        KEY_STRUCTURE_TYPE: "Composite Steel Plate Girder",
        KEY_DESIGN_MODE: "Optimized",
        KEY_SPAN: 30.0,
        KEY_CARRIAGEWAY_WIDTH: 10.5,
        KEY_FOOTPATH: "Both Sides",
        KEY_TS_FOOTPATH_WIDTH: 1.5,
        KEY_TS_OVERALL_WIDTH: 14.5,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_GIRDER_SPACING: 3.6,
        KEY_TS_DECK_THICKNESS: 250.0,
        KEY_GIRDER: "E 350 (Fe 490)",
        KEY_DECK_CONCRETE_GRADE_BASIC: "M35",
        KEY_DS_REINF_MATERIAL: "Fe 550",
        f"{KEY_MP_ED_TYPE}.G1G2.E1M1": ed_type,
        f"{KEY_MP_ED_BRACING_TYPE}.G1G2.E1M1": "X-Bracing",
        KEY_LL_IRC_CLASS_A: True,
        KEY_LL_IRC_70R_WHEELED: True,
        KEY_LL_IRC_70R_TRACKED: False,
        KEY_LL_IRC_CLASS_SV: True,
        KEY_BL_IRC_CLASS_SV: False,
        KEY_LL_IRC_CLASS_FATIGUE: False,
        KEY_LL_ECCENTRICITY: "1.2",
        KEY_LL_FOOTPATH_PRESSURE_MODE: "As per IRC 6",
        KEY_LL_FOOTPATH_PRESSURE_VALUE: "",
        KEY_WL_BASIC_WIND_SPEED: "44",
        KEY_WL_AVG_EXPOSED_HEIGHT: "10",
        KEY_WL_TERRAIN_TYPE: "Plain Terrain",
        KEY_SL_SEISMIC_ZONE: "III",
        KEY_TL_HIGHEST_MAX_TEMP: "42",
        KEY_TL_LOWEST_MIN_TEMP: "10",
        "typical_section.crash_barrier.area": 300000.0,
    }
    for i in range(1, 5):
        inputs[f"{KEY_MP_GD_SELECT_GIRDER}.G{i}"] = f"G{i}"
        inputs[f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1"] = f"G{i}M1"
        # Post-design metre-mutated values
        inputs[f"{KEY_MP_GIRDER_DEPTH}.G{i}.M1"] = 1.6
        inputs[f"{KEY_MP_GIRDER_WEB_THICKNESS}.G{i}.M1"] = 0.012
        inputs[f"{KEY_MP_GIRDER_TOP_FLANGE_WIDTH}.G{i}.M1"] = 0.45
        inputs[f"{KEY_MP_GIRDER_TOP_FLANGE_THICKNESS}.G{i}.M1"] = 0.025
        inputs[f"{KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH}.G{i}.M1"] = 0.55
        inputs[f"{KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS}.G{i}.M1"] = 0.032

    g1_dcr = 1.18 if failing_girder else 0.78
    g1_st = "FAIL" if failing_girder else "PASS"

    per_girder = {}
    for i in range(1, 5):
        dcr = g1_dcr if i == 1 else 0.65
        st = g1_st if i == 1 else "PASS"
        per_girder[f"G{i}"] = {
            "checks": [
                {
                    "check_id": 1,
                    "name": "Flexure",
                    "demand": 4200.0,
                    "capacity": 4200.0 / dcr,
                    "demand_unit": "kN-m",
                    "capacity_unit": "kN-m",
                    "dcr": dcr,
                    "status": st,
                },
                {
                    "check_id": 2,
                    "name": "Shear",
                    "demand": 950.0,
                    "capacity": 1800.0,
                    "demand_unit": "kN",
                    "capacity_unit": "kN",
                    "dcr": 0.53,
                    "status": "PASS",
                },
            ],
            "per_lc": {
                "ULS-01": {"checks": [{"id": 1, "dcr": dcr, "demand": 4200.0, "capacity": 4200.0 / dcr}]}
            },
        }

    cb_raw = {
        "section_size.designation": "ISA 100x100x10",
        "Design.Strength": 320.0,
        "Optimum.UR": 0.48,
        "Member.Slenderness": 118.0,
        "Weld.Type": "Fillet",
    }
    ed_raw = {
        "section_size.designation": "ISA 90x90x8",
        "Design.Strength": 250.0,
        "Optimum.UR": 0.62,
        "Member.Slenderness": 132.0,
    }

    outputs = {
        KEY_SD_TOTAL_DEPTH: 1600.0,
        "design_results": {
            "A_steel_mm2": 48000.0,
            "per_girder": per_girder,
        },
        "deck_design_results": {"ur_flexure": 0.71, "ur_shear": 0.44},
        "crossbracing_forces_dict": {
            "geometry": {"diagonal_length_m": 3.85, "horiz_proj_m": 3.60, "cb_spacing_m": 6.0, "alpha_deg": 20.5},
            "pairs": {
                "G1-G2": {"diag_compression_kN": 140.0, "chord_tension_kN": 95.0, "diag_compression_gov_lc": "ULS-01"},
                "G2-G3": {"diag_compression_kN": 120.0, "chord_tension_kN": 80.0, "diag_compression_gov_lc": "ULS-01"},
                "G3-G4": {"diag_compression_kN": 135.0, "chord_tension_kN": 90.0, "diag_compression_gov_lc": "ULS-01"},
            },
        },
        "crossbracing_design_results": {
            p: {"diagonal": {"compression": cb_raw}, "chord": {"tension": cb_raw}}
            for p in ("G1-G2", "G2-G3", "G3-G4")
        },
        "end_diaphragm_forces_dict": {
            # Deliberately omits "geometry" to mirror plategirderbridge.py:2672
            "pairs": {
                "G1-G2": {"diag_compression_kN": 155.0, "chord_tension_kN": 100.0, "diag_compression_gov_lc": "ULS-02"},
                "G2-G3": {"diag_compression_kN": 150.0, "chord_tension_kN": 98.0, "diag_compression_gov_lc": "ULS-02"},
                "G3-G4": {"diag_compression_kN": 155.0, "chord_tension_kN": 100.0, "diag_compression_gov_lc": "ULS-02"},
            },
        },
        "end_diaphragm_design_results": {
            p: {"diagonal": {"compression": ed_raw}, "chord": {"tension": ed_raw}}
            for p in ("G1-G2", "G2-G3", "G3-G4")
        },
        "transverse_member_design.cb.section_properties.bracing.G1G2.A": 19.03,
        "transverse_member_design.cb.section_properties.bracing.G1G2.rv": 1.94,
        "transverse_member_design.cb.section_properties.top_chord.G1G2.A": 15.39,
        "transverse_member_design.cb.section_properties.bottom_chord.G1G2.A": 15.39,
        "transverse_member_design.ed.section_properties.bracing.G1G2.A": 13.79,
        "transverse_member_design.ed.section_properties.bracing.G1G2.rv": 1.75,
        "transverse_member_design.ed.section_properties.top_chord.G1G2.A": 13.79,
        "transverse_member_design.ed.section_properties.bottom_chord.G1G2.A": 13.79,
    }
    return inputs, outputs


# -----------------------------------------------------------------------------
# 1. styles.py & report_utils.py tests
# -----------------------------------------------------------------------------
def test_styles_preamble_and_no_negative_footrule_vspace():
    pre = styles.build_preamble("Test Bridge", "JOB-01", "2026-11-21", "Rev 1")
    assert r"\usepackage[T1]{fontenc}" in pre
    assert r"\usepackage{textcomp}" in pre
    assert r"\definecolor{osdagGreen}{HTML}{91B014}" in pre
    assert r"\sd@markpage" in pre
    assert "footskip=42pt" in pre
    assert r"\vspace{-20pt}" not in pre
    assert r"\vspace{-8pt}" not in pre


def test_styles_width_fitting_never_overflows():
    oversized = [2.5, 3.5, 3.5, 4.2, 1.8, 3.0]
    fitted = styles.fit_column_widths(oversized, tabcolsep_pt=4.5)
    total = styles.compute_table_total_width_cm(fitted, tabcolsep_pt=4.5)
    assert total <= styles.SAFE_TABLE_WIDTH_CM + 1e-6


def test_styles_make_longtable_balanced_and_repeating_headers():
    tex = styles.make_longtable(
        caption="Sample Table",
        headers=["Col A", "Col B"],
        body_tex="1 & 2 \\\\\n\\hline",
        col_alignments=["L", "C"],
        col_widths_cm=[8.0, 6.0],
    )
    assert tex.count(r"\begingroup") == tex.count(r"\endgroup") == 1
    assert r"\caption{\textbf{Sample Table}}\\" in tex
    assert r"\endfirsthead" in tex
    assert r"\endhead" in tex
    assert r"\endfoot" in tex
    assert r"\endlastfoot" in tex
    assert r"\rowcolor{osdagGreenTint}" in tex


def test_styles_girder_banner_uses_starred_break():
    banner = styles.girder_banner_row("Girder G1", 4)
    assert r"\\*" in banner
    assert r"\nopagebreak" not in banner


def test_tex_unicode_sanitization():
    raw = "Temp 42°C, ±15°, 120 mm², 10 m³, Type I – Rock, a ≤ b ≥ c, ∠ 100 ⅹ 100"
    escaped = _tex(raw)
    for bad in ("°", "²", "³", "±", "–", "≤", "≥", "∠", "ⅹ"):
        assert bad not in escaped
    assert r"\textdegree{}" in escaped
    assert r"\textsuperscript{2}" in escaped
    assert r"\textpm{}" in escaped


# -----------------------------------------------------------------------------
# 2. IRC 6:2017 braking & impact factor fixes
# -----------------------------------------------------------------------------
def test_irc6_impact_factor_backward_compat_and_wheeled():
    assert IRC6_2017.cl_208_3_impact_factor(30.0) == 0.10
    assert IRC6_2017.cl_208_3_impact_factor(50.0, "tracked") == 0.10
    assert IRC6_2017.cl_208_3_impact_factor(15.0, "wheeled") == 0.25
    assert IRC6_2017.cl_208_3_impact_factor(30.0, "wheeled") == round(9.0 / (13.5 + 30.0), 3)


def test_irc6_braking_force_all_lane_counts():
    bf1 = IRC6_2017.cl_211_2_braking_force(1)
    bf2 = IRC6_2017.cl_211_2_braking_force(2)
    bf3 = IRC6_2017.cl_211_2_braking_force(3)
    bf4 = IRC6_2017.cl_211_2_braking_force(4)
    assert 10.0 < bf1 < 12.0   # 20% of 55.4 t = 11.08 t
    assert bf1 < bf2 < bf3 < bf4
    assert pytest.approx(bf2 - bf1, abs=0.05) == 5.54
    assert pytest.approx(bf3 - bf2, abs=0.05) == 5.00


def test_irc6_vehicle_catalog_covers_all_ui_keys():
    cat = IRC6_2017.get_live_load_vehicle_catalog()
    expected = {
        "class_a", "70r_wheeled", "70r_tracked", "70r_bogie",
        "aa_wheeled", "aa_tracked", "class_sv", "class_fatigue",
    }
    assert expected.issubset(cat.keys())
    for k in expected:
        assert cat[k]["total_load_kN"] > 0


# -----------------------------------------------------------------------------
# 3. BOQ Generator (End Diaphragm, optimized A_steel_mm2, numeric dict)
# -----------------------------------------------------------------------------
def test_boq_generator_bracing_ed_and_numeric():
    inputs, outputs = _sample_4_girder_inputs_and_outputs(ed_type="Cross Bracing")
    q = calculate_material_quantities(inputs, outputs)
    num = q["_numeric"]
    # 4 girders * 0.048 m^2 * 30 m * 7.85 MT/m^3 = 45.216 MT
    assert pytest.approx(num["steel_girders_mt"], abs=0.05) == 45.216
    assert num["steel_cross_bracing_mt"] > 0.0
    assert num["steel_end_diaphragms_mt"] > 0.0
    assert num["ed_is_bracing"] is True
    assert num["concrete_deck_m3"] == pytest.approx(30.0 * 14.5 * 0.25, abs=0.01)
    assert num["rebar_deck_mt"] > 0.0
    assert q["ed_steel_wt_total"] != "N.A."


def test_boq_generator_rolled_ed_returns_na():
    inputs, outputs = _sample_4_girder_inputs_and_outputs(ed_type="Rolled Beam")
    q = calculate_material_quantities(inputs, outputs)
    assert q["_numeric"]["ed_is_bracing"] is False
    assert q["_numeric"]["steel_end_diaphragms_mt"] is None
    assert q["ed_steel_wt_total"] == "N.A."


# -----------------------------------------------------------------------------
# 4. Thread-safe Matplotlib Charts
# -----------------------------------------------------------------------------
def test_charts_module_forbids_pyplot_import():
    src = inspect.getsource(charts)
    assert "import matplotlib.pyplot" not in src
    assert "from matplotlib import pyplot" not in src


def test_ur_chart_generation_edge_cases():
    # Normal + N/A end diaphragm
    png = charts.generate_ur_summary_chart(
        {"girder": 0.78, "deck": 0.94, "cross_bracing": 0.45, "end_diaphragm": None}
    )
    assert png is not None and png.startswith(b"\x89PNG")

    # Failing + sentinel 9.999
    png_fail = charts.generate_ur_summary_chart(
        {"girder": 1.25, "deck": 9.999, "cross_bracing": 0.35, "end_diaphragm": 0.60}
    )
    assert png_fail is not None and png_fail.startswith(b"\x89PNG")

    # All None -> returns None
    assert charts.generate_ur_summary_chart(
        {"girder": None, "deck": None, "cross_bracing": None, "end_diaphragm": None}
    ) is None


def test_mto_charts_generation():
    res = charts.generate_material_quantity_charts(
        {
            "steel_girders_mt": 45.2,
            "steel_cross_bracing_mt": 4.8,
            "steel_end_diaphragms_mt": 1.6,
            "concrete_deck_m3": 108.75,
            "rebar_deck_mt": 13.05,
        }
    )
    assert "mto_steel_chart" in res and res["mto_steel_chart"].startswith(b"\x89PNG")
    assert "mto_concrete_rebar_chart" in res and res["mto_concrete_rebar_chart"].startswith(b"\x89PNG")


# -----------------------------------------------------------------------------
# 5. Chapter-Level Refactoring & Bugfix Verification
# -----------------------------------------------------------------------------
def test_chap2_mm_vs_m_disambiguation_and_no_ghost_columns():
    meta = ReportMetadata("Bridge", "Mumbai", "Eng", "Client", "Org")
    # Pre-design mm dict including 8 mm web thickness (must NOT become 8000 mm!)
    pre_inputs = {
        KEY_TS_NO_OF_GIRDERS: 2,
        f"{KEY_MP_GD_SELECT_GIRDER}.G1": "G1",
        f"{KEY_MP_GD_MEMBER_ID}.G1.M1": "G1M1",
        f"{KEY_MP_GIRDER_DEPTH}.G1.M1": 1500.0,
        f"{KEY_MP_GIRDER_WEB_THICKNESS}.G1.M1": 8.0,
        f"{KEY_MP_GIRDER_TOP_FLANGE_WIDTH}.G1.M1": 400.0,
        f"{KEY_MP_GIRDER_TOP_FLANGE_THICKNESS}.G1.M1": 20.0,
        f"{KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH}.G1.M1": 500.0,
        f"{KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS}.G1.M1": 25.0,
    }
    tex_pre = ch2_input_parameters(meta, pre_inputs, {})
    assert "1500 mm" in tex_pre
    assert "8 mm" in tex_pre
    assert "8000 mm" not in tex_pre

    # Post-design metre-mutated dict
    post_inputs, _ = _sample_4_girder_inputs_and_outputs()
    tex_post = ch2_input_parameters(meta, post_inputs, {})
    assert "1600 mm" in tex_post
    assert "12 mm" in tex_post
    assert "°" not in tex_post
    assert "±" not in tex_post
    assert tex_post.count(r"\begingroup") == tex_post.count(r"\endgroup")


def test_chap3_separates_vehicular_and_footpath_and_matches_ui_vehicles():
    inputs, _ = _sample_4_girder_inputs_and_outputs()
    tex = ch3_loads(inputs)
    assert r"\label{tab:vehicular-live-load}" in tex
    assert r"\label{tab:footpath-live-load}" in tex
    assert "Class A" in tex
    assert "Class 70R (Wheeled)" in tex
    assert "Class SV" in tex
    assert "Class 70R (Tracked)" not in tex
    assert "Class Fatigue" not in tex
    # Class SV braking is False -> row shows No
    sv_line = [ln for ln in tex.splitlines() if "Class SV &" in ln][0]
    assert "& No &" in sv_line
    # Footpath present -> 4.905 kN/m^2
    assert "4.905" in tex

    # Now disable footpath and enable Class SV braking
    inputs[KEY_FOOTPATH] = "None"
    inputs[KEY_BL_IRC_CLASS_SV] = True
    tex2 = ch3_loads(inputs)
    assert "No footpath provided" in tex2
    sv_line2 = [ln for ln in tex2.splitlines() if "Class SV &" in ln][0]
    assert "& Yes &" in sv_line2


def test_chap5_repeating_headers_ed_wiring_and_ur_chart():
    inputs, outputs = _sample_4_girder_inputs_and_outputs(ed_type="Cross Bracing")
    bridge = ReportDataBridge(outputs, inputs)
    tex = ch5_design_checks([], bridge, fig_paths={"ur_summary_chart": "images/ur_summary_chart.png"})

    n_lt = tex.count(r"\begin{longtable}")
    assert n_lt >= 15
    assert tex.count(r"\endfirsthead") == n_lt
    assert tex.count(r"\endhead") == n_lt
    assert tex.count(r"\begingroup") == tex.count(r"\endgroup")
    assert "ISA 90x90x8" in tex  # Real ED section, not CB copy!
    assert "images/ur_summary_chart.png" in tex
    assert "²" not in tex


def test_executive_summary_real_fail_status_and_unique_label():
    inputs, outputs = _sample_4_girder_inputs_and_outputs(failing_girder=True)
    tex = executive_summary(inputs, outputs, {})
    assert "Fail" in tex
    assert "Girder design pass" not in tex
    assert r"\label{sec:exec-assumptions}" in tex
    assert r"\label{sec:assumptions}" not in tex


# -----------------------------------------------------------------------------
# 6. Full Pipeline Assembly & LaTeX Integrity Check
# -----------------------------------------------------------------------------
def test_full_generate_report_tex_integrity_and_immutability(tmp_path):
    inputs, outputs = _sample_4_girder_inputs_and_outputs()
    original_input_keys = set(inputs.keys())

    meta = ReportMetadata(
        project_name="4-Girder Composite Bridge",
        project_location="Mumbai, Maharashtra",
        designer="Test Engineer",
        client="NHAI",
        company="Osdag",
        job_number="JOB-2026-01",
        report_date="2026-11-21",
        subtitle="Rev 1",
    )
    opts = ReportOptions(
        sections=["loads", "analysis", "design_checks", "drawings"],
        include_figures=True,
        include_toc=True,
        include_pdf=True,
    )
    req = ReportRequest(metadata=meta, options=opts, output_dir=str(tmp_path), file_stem="Report_Test")
    payload = build_report_payload(req, inputs, outputs)

    with patch("osdagbridge.core.reports.report_generator.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = b""
        mock_run.return_value.stderr = b""
        result = generate_report(payload, req, keep_assets=True)

    # Caller inputs dict was never mutated
    assert set(inputs.keys()) == original_input_keys
    assert result.tex_path and os.path.exists(result.tex_path)

    with open(result.tex_path, "r", encoding="utf-8") as fh:
        tex = fh.read()

    # Balanced TeX groups across entire document
    assert tex.count(r"\begingroup") == tex.count(r"\endgroup")

    # Every longtable has \endfirsthead and \endhead
    n_lt = tex.count(r"\begin{longtable}")
    assert n_lt > 20
    assert tex.count(r"\endfirsthead") == n_lt
    assert tex.count(r"\endhead") == n_lt

    # Zero duplicate \label{...} definitions
    labels = re.findall(r"\\label\{([^}]+)\}", tex)
    assert len(labels) == len(set(labels)), f"Duplicate labels: {[l for l in labels if labels.count(l) > 1]}"

    # Zero raw problematic Unicode glyphs in compiled .tex
    assert "°" not in tex
    assert "²" not in tex

    # Relative asset paths & generated chart PNGs copied cleanly with keep_assets=True
    for chart_name in ("ur_summary_chart.png", "mto_steel_chart.png", "mto_concrete_rebar_chart.png"):
        assert f"images/{chart_name}" in tex
        assert os.path.exists(os.path.join(str(tmp_path), "images", chart_name))
