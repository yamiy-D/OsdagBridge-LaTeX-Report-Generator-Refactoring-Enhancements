# =============================================================================
# OsdagBridge — Report Generator
# =============================================================================

import ast
import datetime
import importlib
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from osdagbridge.core.boq.boq_generator import (
    _find_prefixed_value,
    _resolve_girder_depth_m,
    calculate_material_quantities,
)
from osdagbridge.core.reports.charts import (
    generate_material_quantity_charts,
    generate_ur_summary_chart,
)
from osdagbridge.core.reports.report_utils import _tex, extract_osdag_member_summary
from osdagbridge.core.reports.styles import (
    build_preamble,
    chapter_title_format_tex,
    make_simple_table,
    status_badge,
)
from osdagbridge.core.utils.common import (
    KEY_DD_HAS_OVERHANG,
    KEY_DD_MU_BOT,
    KEY_DD_MU_OH,
    KEY_DD_MU_TOP,
    KEY_DD_M_ULS_HOG,
    KEY_DD_M_ULS_OH,
    KEY_DD_M_ULS_SAG,
    KEY_DD_PUNCH_VED,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_VRD_C_MPA,
    KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_OH,
    KEY_DD_WK_TOP,
    KEY_DESIGN_MODE,
    KEY_MP_ED_BRACING_TYPE,
    KEY_MP_ED_TYPE,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TS_GIRDER_SPACING,
)

from .chap1 import ch1_project_info
from .chap2 import ch2_input_parameters
from .chap3 import ch3_loads
from .chap4 import ch4_analysis
from .chap5 import ch5_design_checks
from .chap6 import ch6_drawings
from .chap7 import ch7_quantities
from .chap8 import ch8_design_log
from .chap9 import references
from .executive_summary import executive_summary

logger = logging.getLogger(__name__)


# =============================================================================
# PREAMBLE / TITLE PAGE / TOC (Consuming Centralized styles.py)
# =============================================================================

def preamble(project_name, job_number, report_date, report_version='Rev 0'):
    return build_preamble(
        _tex(project_name),
        _tex(job_number),
        _tex(report_date),
        _tex(report_version),
    )


def title_page(m, osdag_logo, org_logo):
    if osdag_logo:
        lhs = r'\includegraphics[width=\linewidth,keepaspectratio]{' + osdag_logo.replace('\\', '/') + r'}'
    else:
        lhs = r'\textit{(Osdag Logo)}'

    if org_logo:
        rhs = r'\includegraphics[width=\linewidth,height=2.2cm,keepaspectratio]{' + org_logo.replace('\\', '/') + r'}'
    else:
        rhs = r''

    logos_tex = (
        r"\noindent" + "\n"
        r"\begin{minipage}[c]{0.6\textwidth}" + "\n"
        r"\raggedright" + "\n"
        + lhs + "\n"
        r"\end{minipage}%" + "\n"
        r"\hfill" + "\n"
        r"\begin{minipage}[c]{0.35\textwidth}" + "\n"
        r"\raggedleft" + "\n"
        + rhs + "\n"
        r"\end{minipage}" + "\n"
        r"\\[1cm]" + "\n"
    )

    meta_rows = [
        ("Project Name", _tex(m.project_name)),
        ("Project Location", _tex(m.project_location)),
        ("Author / Designer", _tex(m.designer)),
        ("Reviewer", _tex(m.reviewer)),
        ("Organization", _tex(m.company)),
        ("Client Name and Organization", _tex(m.client)),
        ("Job Number", _tex(m.job_number)),
        ("Date", _tex(m.report_date)),
        ("Report Version", _tex(m.subtitle) if m.subtitle else ""),
    ]
    meta_body = "\n".join(
        rf"\textbf{{{k}}} & {v} \\[4pt]" + "\n" + r"\hline"
        for k, v in meta_rows
    )
    meta_table = make_simple_table(
        headers=None,
        body_tex=meta_body,
        col_alignments=["L", "L"],
        col_widths_cm=[4.8, 9.8],
        floating=False,
    )

    return (
        r"\begin{titlepage}" + "\n"
        r"\thispagestyle{firstpage}" + "\n"
        r"\centering" + "\n"
        r"\vspace*{1.2cm}" + "\n"
        + logos_tex
        + r"{\Huge \textbf{\textcolor{osdagGreenDark}{OsdagBridge}}}\\[0.3cm]" + "\n"
        r"{\large Open Source Software for Steel Girder Bridge Design}\\[1.2cm]" + "\n"
        r"{\Large \textbf{Design Report}}\\[1.2cm]" + "\n"
        + meta_table + "\n"
        r"\end{titlepage}" + "\n"
    )


def toc_section():
    return (
        "\n% Chapter / TOC Formatting\n"
        + chapter_title_format_tex()
        + r"""
\setcounter{tocdepth}{2}

% TOC styling using titletoc
\titlecontents{chapter}[1.5em]
  {\normalfont\vspace{2pt}}
  {\contentslabel{1.5em}}
  {\hspace*{-1.5em}}
  {\hfill\contentspage}

\titlecontents{section}[3.8em]
  {\normalfont}
  {\contentslabel{2.3em}}
  {\hspace*{-2.3em}}
  {\hfill\contentspage}

\titlecontents{subsection}[7.0em]
  {\normalfont}
  {\contentslabel{3.2em}}
  {\hspace*{-3.2em}}
  {\hfill\contentspage}

\newpage
\renewcommand{\contentsname}{\centering\Large\bfseries Table of Contents}
\tableofcontents
"""
    )


# ---------------------------------------------------------------------------
# Public data-classes
# ---------------------------------------------------------------------------

@dataclass
class ReportMetadata:
    project_name: str
    project_location: str
    designer: str
    client: str
    company: str
    group_name: str = ''
    subtitle: str = ''
    job_number: str = ''
    additional_comments: str = ''
    logo_path: Optional[str] = None
    report_date: str = ''
    reviewer: str = ''


@dataclass
class ReportOptions:
    sections: List[str]
    include_figures: bool
    include_toc: bool
    include_pdf: bool


@dataclass
class ReportRequest:
    metadata: ReportMetadata
    options: ReportOptions
    output_dir: str
    file_stem: str


@dataclass
class ReportFigures:
    plan: Optional[str] = None
    cross_section: Optional[str] = None
    final_geometry: Optional[str] = None
    longitudinal_elevation: Optional[str] = None
    girder_3d: Optional[str] = None
    girder_front: Optional[str] = None
    girder_top: Optional[str] = None
    girder_end: Optional[str] = None
    bm_envelope: Optional[str] = None
    sf_envelope: Optional[str] = None
    defl_ll: Optional[str] = None
    shear_connector: Optional[str] = None
    cross_bracing: Optional[str] = None


@dataclass
class ReportPayload:
    metadata: ReportMetadata
    options: ReportOptions
    inputs: dict
    analysis_summary: dict
    design_checks: list
    figures: ReportFigures
    log_entries: List[str] = field(default_factory=list)
    output_dict: dict = field(default_factory=dict)
    figure_data: dict = field(default_factory=dict)


@dataclass
class ReportResult:
    pdf_path: Optional[str]
    tex_path: Optional[str]
    warnings: List[str] = field(default_factory=list)
    log_path: Optional[str] = None
    passes: int = 0


# ---------------------------------------------------------------------------
# Centralized Data Extraction Bridge
# ---------------------------------------------------------------------------

class ReportDataBridge:
    """Centralized data extraction for the OsdagBridge report.

    Provides parameterized transverse-member accessors for both Cross Bracing
    (``kind='cb'``) and End Diaphragms (``kind='ed'``), plus a canonical
    component UR summary consumed by Executive Summary, Section 5.5, and charts.
    """

    def __init__(self, output_dict: dict, input_dict: dict, payload: Optional["ReportPayload"] = None):
        self.output_dict = output_dict or {}
        self.input_dict = input_dict or {}
        self.payload = payload

    # =====================================================================
    # TRANSVERSE MEMBERS (Cross Bracing 'cb' & End Diaphragm 'ed')
    # =====================================================================

    def is_ed_bracing(self) -> bool:
        """Return True when End Diaphragm is configured as Cross Bracing."""
        ed_type = str(_find_prefixed_value(self.input_dict, KEY_MP_ED_TYPE) or "").strip()
        return "brac" in ed_type.lower()

    def _tm_forces_dict(self, kind: str) -> dict:
        key = "crossbracing_forces_dict" if kind == "cb" else "end_diaphragm_forces_dict"
        return self.output_dict.get(key, {}) or {}

    def _tm_pair_designs(self, kind: str) -> dict:
        key = "crossbracing_design_results" if kind == "cb" else "end_diaphragm_design_results"
        return self.output_dict.get(key, {}) or {}

    def _tm_osdag(self, kind: str, pair: str, member: str, force_type: str) -> dict:
        try:
            raw = self._tm_pair_designs(kind)[pair][member][force_type]
            return extract_osdag_member_summary(raw or {})
        except (KeyError, TypeError):
            return {}

    def get_tm_pairs(self, kind: str) -> list:
        try:
            pairs = self._tm_forces_dict(kind).get("pairs", {})
            if pairs:
                return sorted(pairs.keys())
            # Fall back to design results keys if forces_dict omitted pairs
            designs = self._tm_pair_designs(kind)
            if designs:
                return sorted(designs.keys())
        except Exception:
            pass
        return []

    def get_tm_geometry(self, kind: str) -> dict:
        geom = self._tm_forces_dict(kind).get("geometry", {}) or {}
        if geom or kind != "ed":
            return geom
        # Deterministic geometry derivation for bracing-type End Diaphragms
        # because _design_end_diaphragm_members() does not persist 'geometry'.
        try:
            spacing = float(self.input_dict.get(KEY_TS_GIRDER_SPACING) or 0.0)
        except (TypeError, ValueError):
            spacing = 0.0
        d_m = _resolve_girder_depth_m(self.input_dict, self.output_dict) or 0.0
        if spacing > 0.0 and d_m > 0.0:
            btype = str(_find_prefixed_value(self.input_dict, KEY_MP_ED_BRACING_TYPE) or "X").strip().upper()
            h_m = 0.85 * d_m
            horiz_proj = (spacing / 2.0) if btype.startswith("K") else spacing
            diag_len = math.hypot(horiz_proj, h_m)
            alpha_deg = math.degrees(math.atan2(h_m, horiz_proj)) if horiz_proj > 0 else 0.0
            return {
                "diagonal_length_m": diag_len,
                "horiz_proj_m": spacing,
                "alpha_deg": alpha_deg,
                "brace_type": "K" if btype.startswith("K") else "X",
            }
        return {}

    def get_tm_brace_type(self, kind: str) -> str:
        try:
            val = self._tm_forces_dict(kind).get("brace_type")
            if val:
                return str(val)
            geom = self.get_tm_geometry(kind)
            return str(geom.get("brace_type", "X"))
        except Exception:
            return "X"

    def get_tm_force(self, kind: str, pair: str, member: str, force_type: str) -> str:
        try:
            pairs = self._tm_forces_dict(kind)["pairs"][pair]
            key = f"diag_{force_type}_kN" if member == "diagonal" else f"chord_{force_type}_kN"
            val = pairs.get(key)
            if val is not None:
                return f"{float(val):.3f}"
        except (KeyError, TypeError, ValueError):
            pass
        return ""

    def get_tm_nature(self, kind: str, pair: str, member: str) -> str:
        try:
            pairs = self._tm_forces_dict(kind)["pairs"][pair]
            t_key = "diag_tension_kN" if member == "diagonal" else "chord_tension_kN"
            c_key = "diag_compression_kN" if member == "diagonal" else "chord_compression_kN"
            has_t = pairs.get(t_key) is not None
            has_c = pairs.get(c_key) is not None
            if has_t and has_c:
                return "T / C"
            if has_t:
                return "T"
            if has_c:
                return "C"
        except (KeyError, TypeError):
            pass
        return ""

    def get_tm_governing_force(self, kind: str, pair: str, member: str) -> tuple:
        try:
            pairs = self._tm_forces_dict(kind)["pairs"][pair]
            t_key = "diag_tension_kN" if member == "diagonal" else "chord_tension_kN"
            c_key = "diag_compression_kN" if member == "diagonal" else "chord_compression_kN"
            t_val = pairs.get(t_key)
            c_val = pairs.get(c_key)
            if t_val is not None and c_val is not None:
                if abs(c_val) >= abs(t_val):
                    return (f"{float(c_val):.3f}", "compression")
                return (f"{float(t_val):.3f}", "tension")
            if c_val is not None:
                return (f"{float(c_val):.3f}", "compression")
            if t_val is not None:
                return (f"{float(t_val):.3f}", "tension")
        except (KeyError, TypeError, ValueError):
            pass
        return ("", "compression")

    def get_tm_section(self, kind: str, pair: str, member: str, force_type: str) -> str:
        val = self._tm_osdag(kind, pair, member, force_type).get("section")
        return _tex(val) if val else ""

    def get_tm_capacity(self, kind: str, pair: str, member: str, force_type: str) -> str:
        val = self._tm_osdag(kind, pair, member, force_type).get("capacity_kN")
        return f"{float(val):.3f}" if val is not None else ""

    def get_tm_efficiency(self, kind: str, pair: str, member: str, force_type: str) -> str:
        val = self._tm_osdag(kind, pair, member, force_type).get("efficiency")
        return f"{float(val):.3f}" if val is not None else ""

    def get_tm_slenderness(self, kind: str, pair: str, member: str) -> str:
        for ft in ("compression", "tension"):
            val = self._tm_osdag(kind, pair, member, ft).get("slenderness")
            if val is not None:
                return f"{float(val):.1f}"
        return ""

    def get_tm_status(self, kind: str, pair: str, member: str, force_type: str) -> str:
        try:
            val = self._tm_osdag(kind, pair, member, force_type).get("efficiency")
            if val is not None:
                ur = float(val)
                return status_badge("PASS" if ur <= 1.0 else "FAIL")
        except (TypeError, ValueError):
            pass
        return ""

    def get_tm_gov_lc(self, kind: str, pair: str, member: str, force_type: str) -> str:
        try:
            pfx = "diag" if member == "diagonal" else "chord"
            key = f"{pfx}_{force_type}_gov_lc"
            val = self._tm_forces_dict(kind)["pairs"][pair].get(key)
            return _tex(val) if val else ""
        except (KeyError, TypeError):
            return ""

    def get_tm_connection(self, kind: str, pair: str, member: str, force_type: str) -> str:
        val = self._tm_osdag(kind, pair, member, force_type).get("connection")
        return str(val) if val else ""

    def get_tm_effective_length(self, kind: str, member: str) -> str:
        try:
            geom = self.get_tm_geometry(kind)
            L_m = geom.get("diagonal_length_m", 0) if member == "diagonal" else geom.get("horiz_proj_m", 0)
            return f"{float(L_m) * 1000:.0f}" if L_m else ""
        except (TypeError, ValueError):
            return ""

    def get_tm_alpha_deg(self, kind: str) -> str:
        try:
            return f"{float(self.get_tm_geometry(kind).get('alpha_deg', 0)):.2f}"
        except Exception:
            return ""

    # Backward-compatible Cross Bracing wrappers
    def _cb_forces_dict(self) -> dict:
        return self._tm_forces_dict("cb")

    def _cb_pair_designs(self) -> dict:
        return self._tm_pair_designs("cb")

    def _cb_osdag(self, pair: str, member: str, force_type: str) -> dict:
        return self._tm_osdag("cb", pair, member, force_type)

    def get_cb_pairs(self) -> list:
        return self.get_tm_pairs("cb")

    def get_cb_geometry(self) -> dict:
        return self.get_tm_geometry("cb")

    def get_cb_brace_type(self) -> str:
        return self.get_tm_brace_type("cb")

    def get_cb_force(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_force("cb", pair, member, force_type)

    def get_cb_nature(self, pair: str, member: str) -> str:
        return self.get_tm_nature("cb", pair, member)

    def get_cb_governing_force(self, pair: str, member: str) -> tuple:
        return self.get_tm_governing_force("cb", pair, member)

    def get_cb_section(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_section("cb", pair, member, force_type)

    def get_cb_capacity(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_capacity("cb", pair, member, force_type)

    def get_cb_efficiency(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_efficiency("cb", pair, member, force_type)

    def get_cb_slenderness(self, pair: str, member: str) -> str:
        return self.get_tm_slenderness("cb", pair, member)

    def get_cb_status(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_status("cb", pair, member, force_type)

    def get_cb_gov_lc(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_gov_lc("cb", pair, member, force_type)

    def get_cb_connection(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_connection("cb", pair, member, force_type)

    def get_cb_effective_length(self, member: str) -> str:
        return self.get_tm_effective_length("cb", member)

    def get_cb_alpha_deg(self) -> str:
        return self.get_tm_alpha_deg("cb")

    # End Diaphragm wrappers
    def get_ed_pairs(self) -> list:
        return self.get_tm_pairs("ed")

    def get_ed_governing_force(self, pair: str, member: str) -> tuple:
        return self.get_tm_governing_force("ed", pair, member)

    def get_ed_section(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_section("ed", pair, member, force_type)

    def get_ed_capacity(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_capacity("ed", pair, member, force_type)

    def get_ed_efficiency(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_efficiency("ed", pair, member, force_type)

    def get_ed_slenderness(self, pair: str, member: str) -> str:
        return self.get_tm_slenderness("ed", pair, member)

    def get_ed_status(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_status("ed", pair, member, force_type)

    def get_ed_gov_lc(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_gov_lc("ed", pair, member, force_type)

    def get_ed_connection(self, pair: str, member: str, force_type: str) -> str:
        return self.get_tm_connection("ed", pair, member, force_type)

    def get_ed_effective_length(self, member: str) -> str:
        return self.get_tm_effective_length("ed", member)

    # =====================================================================
    # CANONICAL COMPONENT UR & STATUS SUMMARY (Single Source of Truth)
    # =====================================================================

    def _max_tm_ur(self, kind: str) -> Optional[float]:
        """Maximum UR across axial efficiency and slenderness ratio for CB or ED."""
        best = None
        pairs = self.get_tm_pairs(kind)
        for pair in pairs:
            for member in ("diagonal", "chord"):
                for ft in ("compression", "tension"):
                    eff = self.get_tm_efficiency(kind, pair, member, ft)
                    try:
                        f = float(eff)
                        best = f if best is None else max(best, f)
                    except (TypeError, ValueError):
                        pass
                slnd = self.get_tm_slenderness(kind, pair, member)
                try:
                    sf = float(slnd)
                    lim = 400.0 if member == "chord" else 250.0
                    ratio = sf / lim
                    best = ratio if best is None else max(best, ratio)
                except (TypeError, ValueError):
                    pass
        return best

    def _max_deck_ur(self) -> Optional[float]:
        """Maximum Deck Slab UR reconciling deck_report_values and deck_design_results."""
        candidates = []
        deck_rpt = self.output_dict.get("deck_report_values", {}) or {}
        if deck_rpt:
            def _f(k):
                try:
                    v = deck_rpt.get(k)
                    return float(v) if v not in (None, "") else None
                except (TypeError, ValueError):
                    return None

            ratio_pairs = [
                (KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT),
                (KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP),
                (KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA),
                (KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC),
            ]
            if deck_rpt.get(KEY_DD_HAS_OVERHANG):
                ratio_pairs.append((KEY_DD_M_ULS_OH, KEY_DD_MU_OH))
            for dem_k, cap_k in ratio_pairs:
                d, c = _f(dem_k), _f(cap_k)
                if d is not None and c is not None and c > 0.0:
                    candidates.append(d / c)

            wk_lim = _f(KEY_DD_WK_LIMIT)
            if wk_lim and wk_lim > 0.0:
                wks = [_f(KEY_DD_WK_BOT), _f(KEY_DD_WK_TOP)]
                if deck_rpt.get(KEY_DD_HAS_OVERHANG):
                    wks.append(_f(KEY_DD_WK_OH))
                valid_wks = [w for w in wks if w is not None]
                if valid_wks:
                    candidates.append(max(valid_wks) / wk_lim)

        deck_res = self.output_dict.get("deck_design_results", {}) or {}
        for k, v in deck_res.items():
            if str(k).startswith("ur_"):
                try:
                    candidates.append(float(v))
                except (TypeError, ValueError):
                    pass

        return max(candidates) if candidates else None

    def extract_component_ur_summary(self) -> Dict[str, object]:
        """Compute canonical UR and pass/fail/N/A statuses once for all consumers
        (Executive Summary, Section 5.5 Table 5.22, and Section 5.5 UR chart).
        """
        design_results = self.output_dict.get("design_results", {}) or {}
        per_girder = design_results.get("per_girder", {}) or {}

        failing_checks: List[str] = []
        gov_name, gov_dcr = "", None
        girder_max_ur: Optional[float] = None
        per_girder_ur: Dict[str, Optional[float]] = {}
        per_girder_gov_check: Dict[str, str] = {}

        for g, gd in per_girder.items():
            if str(g).startswith("EB"):
                continue
            g_best_dcr = None
            g_best_name = ""
            for chk in (gd.get("checks") or []):
                try:
                    raw_dcr = chk.get("dcr")
                    dcr = float(raw_dcr) if raw_dcr is not None else None
                except (TypeError, ValueError):
                    dcr = None
                name = str(chk.get("name", "")).strip()
                is_fail = ("FAIL" in str(chk.get("status", "")).upper()) or (dcr is not None and dcr > 1.0)
                if is_fail and name and name not in failing_checks:
                    failing_checks.append(name)
                if dcr is not None:
                    if g_best_dcr is None or dcr > g_best_dcr:
                        g_best_dcr, g_best_name = dcr, name
                    if gov_dcr is None or dcr > gov_dcr:
                        gov_dcr, gov_name = dcr, name
                    if girder_max_ur is None or dcr > girder_max_ur:
                        girder_max_ur = dcr
            per_girder_ur[str(g)] = g_best_dcr
            per_girder_gov_check[str(g)] = g_best_name

        deck_max_ur = self._max_deck_ur()
        cb_max_ur = self._max_tm_ur("cb")
        ed_is_bracing = self.is_ed_bracing()
        ed_max_ur = self._max_tm_ur("ed") if ed_is_bracing else None

        components = {
            "girder": girder_max_ur,
            "deck": deck_max_ur,
            "cross_bracing": cb_max_ur,
            "end_diaphragm": ed_max_ur,
        }

        def _comp_status(val: Optional[float], force_fail: bool = False) -> str:
            if val is None:
                return "N/A"
            if force_fail or val > 1.0:
                return "Fail"
            return "Pass"

        statuses = {
            "girder": _comp_status(girder_max_ur, force_fail=bool(failing_checks)),
            "deck": _comp_status(deck_max_ur),
            "cross_bracing": _comp_status(cb_max_ur),
            "end_diaphragm": _comp_status(ed_max_ur),
        }

        if not per_girder and deck_max_ur is None and cb_max_ur is None:
            overall_design_status = ""
        elif failing_checks:
            overall_design_status = "Fail (" + ", ".join(failing_checks) + ")"
        elif any(st == "Fail" for st in statuses.values()):
            failed_comps = [
                lbl for k, lbl in (
                    ("girder", "Girder"),
                    ("deck", "Deck slab"),
                    ("cross_bracing", "Cross bracing"),
                    ("end_diaphragm", "End diaphragm"),
                )
                if statuses[k] == "Fail"
            ]
            overall_design_status = "Fail (" + ", ".join(failed_comps) + ")"
        else:
            overall_design_status = "Pass"

        comp_pairs = [
            (girder_max_ur, "Girder"),
            (deck_max_ur, "Deck slab"),
            (cb_max_ur, "Cross bracing"),
            (ed_max_ur, "End diaphragm"),
        ]
        valid_pairs = [(u, lbl) for u, lbl in comp_pairs if u is not None]
        if valid_pairs:
            max_ur, max_label = max(valid_pairs, key=lambda item: item[0])
            overall_ur_str = f"{max_ur:.2f} ({max_label})"
        else:
            overall_ur_str = ""

        return {
            "components": components,
            "statuses": statuses,
            "per_girder_ur": per_girder_ur,
            "per_girder_gov_check": per_girder_gov_check,
            "overall_design_status": overall_design_status,
            "governing_check": gov_name,
            "overall_utilization_ratio": overall_ur_str,
            "ed_is_bracing": ed_is_bracing,
        }


# ---------------------------------------------------------------------------
# Location formatter & Payload builder (preserved public signatures)
# ---------------------------------------------------------------------------

def _format_project_location(pl_data):
    if not pl_data:
        return ''
    if isinstance(pl_data, str):
        try:
            pl_dict = ast.literal_eval(pl_data)
        except Exception:
            return pl_data
    elif isinstance(pl_data, dict):
        pl_dict = pl_data
    else:
        return str(pl_data)

    method = pl_dict.get('method')
    data = pl_dict.get('data', {})

    if method == 'location_name':
        dist = data.get('district', '')
        state = data.get('state', '')
        if dist and state:
            return f"{dist}, {state}"
        return dist or state or r''
    elif method == 'map':
        lat = data.get('latitude', '')
        lon = data.get('longitude', '')
        if lat and lon:
            try:
                from osdagbridge.core.bridge_types.plate_girder.ui_fields_project_location import DB_PATH
                from osdagbridge.core.data.project_location.database import Database
                db = Database(DB_PATH)
                db.connect()
                nearest = db.get_nearest_station_temperature(float(lat), float(lon))
                db.close()
                if nearest:
                    return f"{nearest['station']}, {nearest['state']}"
            except Exception as e:
                logger.warning(f"Reverse geocode error: {e}")
            return f"Lat: {lat} deg, Lon: {lon} deg"
        return 'Map Location'
    elif method == 'custom_data':
        return 'Custom Location Data'

    return str(pl_data)


def build_report_payload(request, input_dict, output_dict):
    try:
        local_inputs = dict(input_dict or {})
        rd = request.metadata.report_date or datetime.date.today().isoformat()
        lp = request.metadata.logo_path
        raw_pl = request.metadata.project_location or local_inputs.get('project.location') or ''
        pl = _format_project_location(raw_pl)

        md = ReportMetadata(
            project_name=request.metadata.project_name,
            project_location=pl,
            designer=request.metadata.designer,
            client=request.metadata.client,
            company=request.metadata.company,
            group_name=request.metadata.group_name,
            subtitle=request.metadata.subtitle,
            job_number=request.metadata.job_number,
            additional_comments=request.metadata.additional_comments,
            logo_path=lp,
            report_date=rd,
            reviewer=getattr(request.metadata, 'reviewer', ''),
        )

        try:
            if isinstance(raw_pl, str) and '{' in raw_pl:
                pl_dict = ast.literal_eval(raw_pl)
            elif isinstance(raw_pl, dict):
                pl_dict = raw_pl
            else:
                pl_dict = {}

            if pl_dict and isinstance(pl_dict, dict):
                data = pl_dict.get('data', {})
                weather = pl_dict.get('weather_data', {})
                lat_val = data.get('latitude') or weather.get('latitude')
                lon_val = data.get('longitude') or weather.get('longitude')

                if 'latitude' not in local_inputs and lat_val:
                    local_inputs['latitude'] = lat_val
                if 'longitude' not in local_inputs and lon_val:
                    local_inputs['longitude'] = lon_val
                if 'seismic_zone' not in local_inputs and weather.get('zone'):
                    local_inputs['seismic_zone'] = weather.get('zone')
                if 'wind_speed' not in local_inputs and weather.get('wind_speed'):
                    local_inputs['wind_speed'] = weather.get('wind_speed')
                if 'shade_temp_max' not in local_inputs and weather.get('max_temp'):
                    local_inputs['shade_temp_max'] = weather.get('max_temp')
                if 'shade_temp_min' not in local_inputs and weather.get('min_temp'):
                    local_inputs['shade_temp_min'] = weather.get('min_temp')
        except Exception as e:
            logger.warning(f"Failed to parse project location data: {e}")

        for _tkey in (
            KEY_TL_BRIDGE_TEMP_MIN,
            KEY_TL_BRIDGE_TEMP_MAX,
            KEY_TL_TEMP_RISE,
            KEY_TL_TEMP_FALL,
        ):
            if not local_inputs.get(_tkey) and (output_dict or {}).get(_tkey):
                local_inputs[_tkey] = output_dict[_tkey]

        if not local_inputs.get(KEY_TL_BRIDGE_TEMP_MIN):
            try:
                max_str = local_inputs.get(KEY_TL_HIGHEST_MAX_TEMP) or local_inputs.get('shade_temp_max')
                min_str = local_inputs.get(KEY_TL_LOWEST_MIN_TEMP) or local_inputs.get('shade_temp_min')
                if max_str and min_str:
                    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
                    res = IRC6_2017.cl_215_2_effective_bridge_temperature(
                        float(max_str), float(min_str), 'metallic', False
                    )
                    t_min = res.get('T_min', 0)
                    t_max = res.get('T_max', 0)
                    mean = (t_max + t_min) / 2.0
                    local_inputs[KEY_TL_BRIDGE_TEMP_MIN] = f"{t_min:.2f}"
                    local_inputs[KEY_TL_BRIDGE_TEMP_MAX] = f"{t_max:.2f}"
                    local_inputs[KEY_TL_TEMP_RISE] = f"{t_max - mean:.2f}"
                    local_inputs[KEY_TL_TEMP_FALL] = f"{mean - t_min:.2f}"
            except Exception as _te:
                logger.warning(f"Could not compute temperature values for report: {_te}")

        asum = (output_dict or {}).get('analysis_summary', {})
        dc = (output_dict or {}).get('design_checks', [])
        le = (output_dict or {}).get('design_log', [])

        if not le:
            try:
                from osdagbridge.core.utils.logger import bridge_logger
                le = bridge_logger.get_success_log()
            except Exception as _le:
                logger.warning("Could not read design log from logger: %s", _le)

        return ReportPayload(
            metadata=md,
            options=request.options,
            inputs=local_inputs,
            analysis_summary=asum,
            design_checks=dc,
            figures=ReportFigures(),
            log_entries=le,
            output_dict=output_dict or {},
        )

    except Exception as exc:
        logger.warning("build_report_payload error: %s", exc)
        return ReportPayload(
            metadata=request.metadata,
            options=request.options,
            inputs={},
            analysis_summary={},
            design_checks=[],
            figures=ReportFigures(),
            log_entries=[],
            output_dict={},
        )


# ===========================================================================
# LaTeX Log Parser & Convergence Helpers
# ===========================================================================

_RERUN_PATTERNS = (
    "Table widths have changed",
    "Rerun to get",
    "Label(s) may have changed",
    "Please rerun LaTeX",
)

_WARNING_REGEX = re.compile(
    r"(Overfull \\hbox.*|Package fancyhdr Warning:.*|LaTeX Warning:.*multiply-defined.*"
    r"|end occurred inside a group.*|Package inputenc Error:.*|Missing character:.*)",
    re.IGNORECASE,
)


def _parse_latex_log(log_text: str) -> tuple:
    """Return ``(needs_rerun: bool, warnings: List[str])`` from a pdflatex log."""
    needs_rerun = any(tok in log_text for tok in _RERUN_PATTERNS)
    warnings = [m.group(1).strip() for m in _WARNING_REGEX.finditer(log_text)]
    return needs_rerun, warnings


# ===========================================================================
# Public entry point
# ===========================================================================

_FIGURE_MAP = [
    ('plan', 'plan.png'),
    ('cross_section', 'cross_section.png'),
    ('final_geometry', 'final_geometry.png'),
    ('longitudinal_elevation', 'longitudinal_elevation.png'),
    ('girder_3d', 'girder_3d.png'),
    ('girder_top', 'girder_top.png'),
    ('section_preview', 'section_preview.png'),
    ('stiffener_preview', 'stiffener_preview.png'),
    ('cb_diagram', 'cb_diagram.png'),
    ('cb_bracing', 'cb_bracing.png'),
    ('cb_top_chord', 'cb_top_chord.png'),
    ('cb_bottom_chord', 'cb_bottom_chord.png'),
    ('ed_diagram', 'ed_diagram.png'),
    ('ed_bracing', 'ed_bracing.png'),
    ('ed_top_chord', 'ed_top_chord.png'),
    ('ed_bottom_chord', 'ed_bottom_chord.png'),
    ('bm_envelope', 'bm_envelope.png'),
    ('sf_envelope', 'sf_envelope.png'),
    ('defl_ll', 'defl_ll.png'),
]


def generate_report(payload, request, keep_assets: bool = False):
    # type: (ReportPayload, ReportRequest, bool) -> ReportResult
    """Compile the full OsdagBridge Design Report to PDF (+ .tex source)."""
    tex_path = None
    log_out_path = None
    warnings: List[str] = []
    passes_run = 0

    try:
        # Discover bundled pdflatex without mutating process-global os.environ
        compiler = 'pdflatex'
        run_env = os.environ.copy()
        try:
            module = importlib.import_module('osdag_latex_env.__main__')
            latex_env = getattr(module, 'OsdagLatexEnv')()
            if latex_env.pdflatex:
                compiler = str(latex_env.pdflatex)
                if latex_env.bin_dir:
                    run_env['PATH'] = str(latex_env.bin_dir) + os.pathsep + run_env.get('PATH', '')
        except Exception as e:
            logger.info("osdag_latex_env not found or failed to load. (%s)", e)

        logger.info("Compiler: %s", compiler)
        os.makedirs(request.output_dir, exist_ok=True)

        pdf_path = os.path.join(request.output_dir, request.file_stem + '.pdf')
        tex_path = os.path.join(request.output_dir, request.file_stem + '.tex')

        # Work off a local shallow copy so caller's payload.inputs is never mutated
        local_inputs = dict(payload.inputs or {})
        quantities = calculate_material_quantities(local_inputs, payload.output_dict)
        boq_numeric = quantities.get('_numeric', {}) or {}
        for qk, qv in quantities.items():
            if qk != '_numeric':
                local_inputs[qk] = qv

        bridge = ReportDataBridge(payload.output_dict, local_inputs, payload)
        ur_summary = bridge.extract_component_ur_summary()
        span_m = float(local_inputs.get(KEY_SPAN, 0) or 0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Ensure pdflatex/mktexpk always has a writable TEXMFVAR cache
            # (important when osdag_latex_env is installed in a read-only folder).
            texmf_var_tmp = os.path.join(tmp_dir, 'texmf-var')
            os.makedirs(texmf_var_tmp, exist_ok=True)
            run_env.setdefault('TEXMFVAR', texmf_var_tmp)
            tmp_images = os.path.join(tmp_dir, 'images')
            os.makedirs(tmp_images, exist_ok=True)
            fig_paths: Dict[str, str] = {}

            # Write incoming figure bytes using relative paths ('images/<attr>.png')
            for attr, img_bytes in list(payload.figure_data.items()):
                if img_bytes:
                    p = os.path.join(tmp_images, attr + '.png')
                    with open(p, 'wb') as fh:
                        fh.write(img_bytes)
                    fig_paths[attr] = 'images/' + attr + '.png'
            payload.figure_data.clear()

            # Programmatically generate Section 5.5 UR & Chapter 7 MTO charts
            if payload.options.include_figures:
                try:
                    ur_png = generate_ur_summary_chart(ur_summary.get('components', {}))
                    if ur_png:
                        ur_file = os.path.join(tmp_images, 'ur_summary_chart.png')
                        with open(ur_file, 'wb') as fh:
                            fh.write(ur_png)
                        fig_paths['ur_summary_chart'] = 'images/ur_summary_chart.png'
                except Exception as exc:
                    logger.warning("Failed to generate UR summary chart: %s", exc)

                try:
                    mto_charts = generate_material_quantity_charts(boq_numeric)
                    for key, png_bytes in mto_charts.items():
                        if png_bytes:
                            out_file = os.path.join(tmp_images, key + '.png')
                            with open(out_file, 'wb') as fh:
                                fh.write(png_bytes)
                            fig_paths[key] = 'images/' + key + '.png'
                except Exception as exc:
                    logger.warning("Failed to generate MTO charts: %s", exc)

            # Title-page logos into tmp_dir/assets (relative paths)
            tmp_assets = os.path.join(tmp_dir, 'assets')
            os.makedirs(tmp_assets, exist_ok=True)

            osdag_logo_src = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'data', 'ResourceFiles', 'vectors', 'Osdag Logo.png',
            )
            iit_logo_src = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'assets', 'IIT Bombay Logo.png',
            )

            osdag_logo_latex = None
            if os.path.exists(osdag_logo_src):
                shutil.copy2(osdag_logo_src, os.path.join(tmp_assets, 'osdag_logo.png'))
                osdag_logo_latex = 'assets/osdag_logo.png'

            org_logo_latex = None
            org_logo_src = (
                payload.metadata.logo_path
                if (payload.metadata.logo_path and os.path.exists(payload.metadata.logo_path))
                else (iit_logo_src if os.path.exists(iit_logo_src) else None)
            )
            if org_logo_src:
                shutil.copy2(org_logo_src, os.path.join(tmp_assets, 'org_logo.png'))
                org_logo_latex = 'assets/org_logo.png'

            # Assemble LaTeX document
            doc_parts = [
                preamble(
                    payload.metadata.project_name,
                    payload.metadata.job_number,
                    payload.metadata.report_date,
                    payload.metadata.subtitle or 'Rev 0',
                ),
                title_page(payload.metadata, osdag_logo_latex, org_logo_latex),
            ]

            if payload.options.include_toc:
                doc_parts.append(toc_section())

            secs = payload.options.sections
            doc_parts.append(executive_summary(local_inputs, payload.output_dict, fig_paths, ur_summary=ur_summary))
            doc_parts.append(ch1_project_info(payload.metadata))
            doc_parts.append(ch2_input_parameters(payload.metadata, local_inputs, payload.output_dict))

            if 'loads' in secs:
                doc_parts.append(ch3_loads(local_inputs))
            if 'analysis' in secs:
                doc_parts.append(ch4_analysis(payload.analysis_summary, fig_paths, bridge, span_m))
            if 'design_checks' in secs:
                doc_parts.append(ch5_design_checks(payload.design_checks, bridge, fig_paths=fig_paths))
            if 'drawings' in secs and payload.options.include_figures:
                doc_parts.append(ch6_drawings(fig_paths))

            doc_parts.append(ch7_quantities(local_inputs, fig_paths=fig_paths))
            doc_parts.append(ch8_design_log(payload.log_entries, local_inputs))
            doc_parts.append(references())
            doc_parts.append(r"\end{document}")

            full_tex = "\n".join(doc_parts)

            tmp_tex = os.path.join(tmp_dir, request.file_stem + '.tex')
            tmp_pdf = os.path.join(tmp_dir, request.file_stem + '.pdf')
            tmp_log = os.path.join(tmp_dir, request.file_stem + '.log')

            with open(tmp_tex, 'w', encoding='utf-8') as f:
                f.write(full_tex)

            # Dynamic convergence loop: minimum 2 passes, up to 4 passes for
            # longtable column widths, TOC, and LastPage references.
            res = None
            for pass_idx in range(1, 5):
                passes_run = pass_idx
                try:
                    kwargs = {
                        'cwd': tmp_dir,
                        'stdout': subprocess.PIPE,
                        'stderr': subprocess.PIPE,
                        'check': False,
                        'env': run_env,
                    }
                    if os.name == 'nt':
                        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

                    res = subprocess.run(
                        [compiler, '-interaction=nonstopmode', request.file_stem + '.tex'],
                        **kwargs,
                    )
                except Exception as exc:
                    logger.warning(f"pdflatex run failed: {exc}")
                    break

                if pass_idx >= 2 and os.path.exists(tmp_log):
                    try:
                        with open(tmp_log, 'r', encoding='utf-8', errors='ignore') as lf:
                            log_text = lf.read()
                        needs_rerun, warnings = _parse_latex_log(log_text)
                        if not needs_rerun:
                            break
                    except Exception:
                        break

            if os.path.exists(tmp_tex):
                shutil.copy2(tmp_tex, tex_path)
            if os.path.exists(tmp_pdf):
                shutil.copy2(tmp_pdf, pdf_path)
            if keep_assets:
                if os.path.exists(tmp_log):
                    log_out_path = os.path.join(request.output_dir, request.file_stem + '.log')
                    shutil.copy2(tmp_log, log_out_path)
                for sub in ('images', 'assets'):
                    src_sub = os.path.join(tmp_dir, sub)
                    dst_sub = os.path.join(request.output_dir, sub)
                    if os.path.exists(src_sub):
                        shutil.copytree(src_sub, dst_sub, dirs_exist_ok=True)

        if os.path.exists(pdf_path):
            logger.info("Report generated in %d pass(es): %s", passes_run, pdf_path)
            return ReportResult(
                pdf_path=pdf_path,
                tex_path=tex_path,
                warnings=warnings,
                log_path=log_out_path,
                passes=passes_run,
            )

        logger.error("pdflatex ran but no PDF was produced.")
        if res is not None:
            logger.error("pdflatex STDOUT:\n%s", res.stdout.decode('utf-8', 'ignore'))
            logger.error("pdflatex STDERR:\n%s", res.stderr.decode('utf-8', 'ignore'))
        return ReportResult(
            pdf_path=None,
            tex_path=tex_path,
            warnings=warnings,
            log_path=log_out_path,
            passes=passes_run,
        )

    except Exception as exc:
        logger.error("generate_report failed: %s", exc, exc_info=True)
        if tex_path and os.path.exists(tex_path):
            return ReportResult(pdf_path=None, tex_path=tex_path, warnings=warnings, passes=passes_run)
        return ReportResult(pdf_path=None, tex_path=None, warnings=warnings, passes=passes_run)
