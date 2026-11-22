# =============================================================================
# Chapter 3: Loads and Load Combinations (Consuming Centralized styles.py)
# =============================================================================

from osdagbridge.core.reports.report_utils import _render_value, _tex
from osdagbridge.core.reports.styles import (
    COMPACT_TABCOLSEP_PT,
    make_longtable,
    na_cell,
)
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import (
    KEY_BL_IRC_CLASS_SV,
    KEY_CARRIAGEWAY_WIDTH,
    KEY_CB_LOAD,
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE,
)

# Canonical ordered mapping of UI Loading-Tab vehicle checkboxes to IRC 6 catalog keys
_UI_VEHICLE_KEYS = [
    (KEY_LL_IRC_CLASS_A, "class_a"),
    (KEY_LL_IRC_70R_WHEELED, "70r_wheeled"),
    (KEY_LL_IRC_70R_TRACKED, "70r_tracked"),
    (KEY_LL_IRC_70R_BOGIE, "70r_bogie"),
    (KEY_LL_IRC_AA_WHEELED, "aa_wheeled"),
    (KEY_LL_IRC_AA_TRACKED, "aa_tracked"),
    (KEY_LL_IRC_CLASS_SV, "class_sv"),
    (KEY_LL_IRC_CLASS_FATIGUE, "class_fatigue"),
]


def _compute_vehicle_impact_factor(span_m, impact_kind: str) -> str:
    """Return ``1 + IM`` formatted to 3 decimals for the given span and vehicle class."""
    if impact_kind == "none":
        return "1.000"
    if span_m is None:
        return na_cell("N/A")
    try:
        s = float(span_m)
        if impact_kind == "class_a":
            im = IRC6_2017.cl_208_2_impact_factor(s)
        elif impact_kind == "wheeled":
            im = IRC6_2017.cl_208_3_impact_factor(s, vehicle_type="wheeled")
        elif impact_kind == "tracked":
            im = IRC6_2017.cl_208_3_impact_factor(s, vehicle_type="tracked")
        else:
            return na_cell("N/A")
        return f"{1.0 + im:.3f}"
    except Exception:
        return na_cell("N/A")


def _build_vehicle_live_load_rows(input_dict: dict) -> str:
    """Build per-vehicle rows for Table 3.3(a) strictly matching UI Loading tab checkboxes."""
    catalog = IRC6_2017.get_live_load_vehicle_catalog()
    span_raw = input_dict.get(KEY_SPAN)
    try:
        span_m = float(span_raw) if span_raw not in (None, "") else None
    except (TypeError, ValueError):
        span_m = None

    ecc_raw = input_dict.get(KEY_LL_ECCENTRICITY)
    if ecc_raw in (None, ""):
        ecc_str = f"{IRC6_2017.cl_211_3_braking_force_location()['height_m']:.2f}"
    else:
        try:
            ecc_str = f"{float(ecc_raw):.2f}"
        except (TypeError, ValueError):
            ecc_str = _tex(ecc_raw)

    sv_braking_opt = bool(input_dict.get(KEY_BL_IRC_CLASS_SV, False))
    rows = []

    for ui_key, cat_key in _UI_VEHICLE_KEYS:
        if not input_dict.get(ui_key):
            continue
        meta = catalog[cat_key]
        total_kn = meta["total_load_kN"]
        impact_str = _compute_vehicle_impact_factor(span_m, meta["impact_kind"])

        if cat_key == "class_sv":
            braking_considered = sv_braking_opt
        else:
            braking_considered = bool(meta["braking_default"])

        if braking_considered and meta["braking_fraction"] > 0.0:
            braking_val = f"{total_kn * meta['braking_fraction']:.2f}"
            braking_ecc = ecc_str
            considered_str = "Yes"
        else:
            braking_val = "---"
            braking_ecc = "---"
            considered_str = "No"

        rows.append(
            f"{_tex(meta['name'])} & {total_kn:.2f} & {impact_str} & "
            f"{considered_str} & {braking_val} & {braking_ecc} & {na_cell('N/A')} "
            + r"\\[4pt]" + "\n\\hline"
        )

    # Append any user-defined custom vehicles selected in UI
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if custom and isinstance(custom, list):
        for c in custom:
            if isinstance(c, dict):
                cname = c.get("name") or "Custom Vehicle"
                cload = c.get("total_load_kN")
                cload_s = f"{float(cload):.2f}" if cload not in (None, "") else "---"
                c_brk = bool(c.get("braking_considered", False))
                c_brk_s = "Yes" if c_brk else "No"
                c_brk_v = f"{float(cload) * 0.20:.2f}" if (c_brk and cload not in (None, "")) else "---"
                c_ecc = ecc_str if c_brk else "---"
                rows.append(
                    f"{_tex(cname)} & {cload_s} & {na_cell('N/A')} & "
                    f"{c_brk_s} & {c_brk_v} & {c_ecc} & {na_cell('N/A')} "
                    + r"\\[4pt]" + "\n\\hline"
                )
            elif isinstance(c, str) and c.strip():
                rows.append(
                    f"{_tex(c)} & --- & {na_cell('N/A')} & No & --- & --- & {na_cell('N/A')} "
                    + r"\\[4pt]" + "\n\\hline"
                )

    if not rows:
        rows.append(
            rf"\multicolumn{{7}}{{|c|}}{{{na_cell('No live-load vehicles selected in UI')}}} \\[4pt]"
            + "\n\\hline"
        )
    return "\n".join(rows)


def _build_footpath_live_load_table(input_dict: dict) -> str:
    """Build Table 3.3(b): dedicated Footpath Live Load table gated on KEY_FOOTPATH."""
    fp_cfg = str(input_dict.get(KEY_FOOTPATH, "None") or "None").strip()
    has_footpath = fp_cfg.lower() not in ("", "none", "no", "false", "0")

    fp_mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "As per IRC 6") or "As per IRC 6").strip()
    fp_val_raw = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    fp_width_raw = input_dict.get(KEY_TS_FOOTPATH_WIDTH, "")

    if not has_footpath:
        rows = [
            ("Footpath Configuration", "None", "---"),
            ("Footpath Width", na_cell("N/A"), "m"),
            ("Pressure Calculation Mode", na_cell("N/A"), "---"),
            ("Design Footpath Pressure", na_cell("N/A (No footpath provided)"), r"kN/m\textsuperscript{2}"),
            ("Line Load per Footpath", na_cell("N/A"), "kN/m"),
        ]
    else:
        pressure_kn_m2 = None
        if fp_mode.lower() in ("as per irc 6", "as per irc6", "automatic"):
            try:
                pressure_kn_m2 = float(IRC6_2017.cl_206_1_footway_load())
                pressure_ref = r"kN/m\textsuperscript{2} (IRC 6 Cl. 206.1)"
            except Exception:
                pressure_ref = r"kN/m\textsuperscript{2}"
        else:
            try:
                if fp_val_raw not in (None, ""):
                    pressure_kn_m2 = float(fp_val_raw)
            except (TypeError, ValueError):
                pressure_kn_m2 = None
            pressure_ref = r"kN/m\textsuperscript{2} (User Custom)"

        width_m = None
        try:
            if fp_width_raw not in (None, ""):
                width_m = float(fp_width_raw)
        except (TypeError, ValueError):
            width_m = None

        p_str = f"{pressure_kn_m2:.3f}" if pressure_kn_m2 is not None else na_cell("N/A")
        w_str = f"{width_m:.2f}" if width_m is not None else na_cell("N/A")
        line_load_str = (
            f"{pressure_kn_m2 * width_m:.3f}"
            if (pressure_kn_m2 is not None and width_m is not None and width_m > 0)
            else na_cell("N/A")
        )

        rows = [
            ("Footpath Configuration", _tex(fp_cfg), "IRC 5 Cl. 104.3.6"),
            ("Footpath Width", w_str, "m"),
            ("Pressure Calculation Mode", _tex(fp_mode), "---"),
            ("Design Footpath Pressure", p_str, pressure_ref),
            ("Line Load per Footpath", line_load_str, r"kN/m ($q \times w_{fp}$)"),
        ]

    body = "\n".join(rf"\textnormal{{{k}}} & {v} & {u} \\[4pt]" + "\n\\hline" for k, v, u in rows)
    return make_longtable(
        caption="Footpath Live Load (IRC 6 Cl. 206.1)",
        headers=["Parameter", "Value", "Unit / Reference"],
        body_tex=body,
        col_alignments=["L", "C", "L"],
        col_widths_cm=[5.6, 4.4, 5.2],
        label="tab:footpath-live-load",
        note="Note: Separated from vehicular live loads for clarity. Applied to each provided footpath.",
    )


def ch3_loads(input_dict):
    input_dict = input_dict or {}

    # Design lanes: prefer KEY_WC_LD_LANE_TABLE_COUNT, else IRC 6 Table 6 from carriageway width
    lanes_val = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    design_lanes = None
    if lanes_val not in (None, ""):
        try:
            design_lanes = int(lanes_val)
        except (TypeError, ValueError):
            design_lanes = None
    if design_lanes is None:
        cw = input_dict.get(KEY_CARRIAGEWAY_WIDTH)
        if cw not in (None, ""):
            try:
                design_lanes = int(IRC6_2017.table_6(float(cw)))
            except Exception:
                design_lanes = None

    braking_summary_str = "N/A"
    if design_lanes is not None and design_lanes >= 1:
        try:
            bf_t = IRC6_2017.cl_211_2_braking_force(design_lanes)
            bf_kn = bf_t * 9.81
            braking_summary_str = f"{bf_kn:.2f} kN ({bf_t:.2f} MT for {design_lanes} design lane(s))"
        except Exception:
            braking_summary_str = "N/A"

    # Wind Vz / Pz — wire computed fallbacks cleanly
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if vz_val in (None, "") or pz_val in (None, ""):
        try:
            _vb = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get('wind_speed')
            _h = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            if _vb not in (None, "") and _h not in (None, ""):
                _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
                if vz_val in (None, ""):
                    vz_val = _res.get("Vz")
                if pz_val in (None, ""):
                    pz_val = _res.get("Pz")
        except Exception:
            pass
    vz_str = f"{float(vz_val):.2f} m/s" if vz_val not in (None, "") else na_cell("N/A")
    pz_str = rf"{float(pz_val):.2f} N/m\textsuperscript{{2}}" if pz_val not in (None, "") else na_cell("N/A")

    # Seismic — wire computed fallbacks cleanly
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if sl_ah in (None, "") or sl_zone_factor in (None, ""):
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get('seismic_zone')
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z = str(_zone or "").strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z, _z)
            _smap = {
                "Type I \u2013 Rocky or Hard": 1,
                "Type I - Rocky or Hard": 1,
                "Type II \u2013 Medium Soil": 2,
                "Type II - Medium Soil": 2,
                "Type III \u2013 Soft Soil": 3,
                "Type III - Soft Soil": 3,
            }
            _st = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            if _z:
                _res = IRC6_2017.cl_218_5_1(
                    zone=f"Zone {_z}",
                    soil_type=_st,
                    dead_load_kN=_dead,
                    live_load_kN=_live,
                    period_T=float(_tp) if _tp else None,
                    damping_percent=float(_damp),
                )
                if sl_zone_factor in (None, ""):
                    sl_zone_factor = _res.get("Z")
                if sl_spectral in (None, ""):
                    sl_spectral = _res.get("Sa_g_adjusted")
                if sl_ah in (None, ""):
                    sl_ah = _res.get("Ah")
                if sl_av in (None, ""):
                    sl_av = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    def _sl(v):
        if v in (None, ""):
            return na_cell("N/A")
        try:
            return f"{float(v):.4f}"
        except (TypeError, ValueError):
            return _tex(v)

    # Temperature — wire stored or computed fallbacks cleanly
    tl_temp_min = input_dict.get(KEY_TL_BRIDGE_TEMP_MIN)
    tl_temp_max = input_dict.get(KEY_TL_BRIDGE_TEMP_MAX)
    tl_rise = input_dict.get(KEY_TL_TEMP_RISE)
    tl_fall = input_dict.get(KEY_TL_TEMP_FALL)
    if tl_temp_min in (None, "") or tl_temp_max in (None, ""):
        try:
            _tmax = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get('shade_temp_max')
            _tmin = input_dict.get(KEY_TL_LOWEST_MIN_TEMP) or input_dict.get('shade_temp_min')
            if _tmax and _tmin:
                _res = IRC6_2017.cl_215_2_effective_bridge_temperature(
                    float(_tmax), float(_tmin), 'metallic', False
                )
                _bt_min = _res.get('T_min', 0)
                _bt_max = _res.get('T_max', 0)
                _mean = (_bt_max + _bt_min) / 2.0
                tl_temp_min = f"{_bt_min:.2f}"
                tl_temp_max = f"{_bt_max:.2f}"
                tl_rise = f"{_bt_max - _mean:.2f}"
                tl_fall = f"{_mean - _bt_min:.2f}"
        except Exception:
            pass

    def _tl(v):
        return _tex(v) if v not in (None, "") else na_cell("N/A")

    # --- Table 3.1: Dead Load ---
    dl_rows = [
        ("Steel Self-Weight Applied", _render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, r' kN/m\textsuperscript{3}')),
        ("Concrete Deck Weight", _render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, r' kN/m\textsuperscript{3}')),
        ("Self-Weight Factor", _render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)),
    ]
    dl_table = make_longtable(
        caption="Dead Load -- Self Weight",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in dl_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    # --- Table 3.2: Surfacing (DW) ---
    dw_rows = [
        (
            "Wearing Course Load",
            _render_value(input_dict, KEY_WC_MATERIAL) + " x " + _render_value(input_dict, KEY_WC_THICKNESS, " mm"),
        ),
        ("Additional SIDL (Crash Barrier)", _render_value(input_dict, KEY_CB_LOAD, " kN/m per barrier")),
        ("Railing Load", _render_value(input_dict, KEY_RL_LOAD_VALUE) + r" kN/m\sdstar{}"),
    ]
    dw_table = make_longtable(
        caption="Dead Load for Surfacing (DW)",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in dw_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    # --- Table 3.3(a): Vehicular Live Loads (2-tier grouped header) ---
    # Note: Place \multirow{-2}{*} on Row 2 so colortbl's Row 2 tint never
    # paints over the multi-row header labels.
    veh_body = _build_vehicle_live_load_rows(input_dict)
    veh_hdr_lines = (
        r"\hline" + "\n"
        r"\rowcolor{osdagGreenTint}" + "\n"
        r" &  &  & "
        r"\multicolumn{3}{c|}{\cellcolor{osdagGreenTint}\textcolor{osdagGreenDark}{\textbf{Braking Load}}} & "
        r" \\" + "\n"
        r"\cline{4-6}" + "\n"
        r"\rowcolor{osdagGreenTint}" + "\n"
        r"\multirow{-2.5}{*}{\textcolor{osdagGreenDark}{\textbf{Vehicle}}} & "
        r"\multirow{-2.5}{*}{\makecell{\textcolor{osdagGreenDark}{\textbf{Total Load}}\\\textcolor{osdagGreenDark}{\textbf{(kN)}}}} & "
        r"\multirow{-2.5}{*}{\makecell{\textcolor{osdagGreenDark}{\textbf{Impact}}\\\textcolor{osdagGreenDark}{\textbf{Factor}}}} & "
        r"\textcolor{osdagGreenDark}{\textbf{Considered?}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Value}}\\\textcolor{osdagGreenDark}{\textbf{(kN)}}} & "
        r"\makecell{\textcolor{osdagGreenDark}{\textbf{Eccentricity}}\\\textcolor{osdagGreenDark}{\textbf{(m)}}} & "
        r"\multirow{-2.5}{*}{\makecell{\textcolor{osdagGreenDark}{\textbf{Centrifugal}}\\\textcolor{osdagGreenDark}{\textbf{Force (kN)}}}} \\[4pt]" + "\n"
        r"\hline"
    )
    veh_first_head = (
        r"\caption{\textbf{Vehicular Live Loads (LL) -- per IRC 6}}\label{tab:vehicular-live-load}\\" + "\n"
        + veh_hdr_lines
    )
    veh_cont_head = (
        r"\multicolumn{7}{l}{\small\textit{Table \thetable\ (continued): Vehicular Live Loads (LL) -- per IRC 6}} \\" + "\n"
        + veh_hdr_lines
    )
    veh_table = make_longtable(
        caption="Vehicular Live Loads (LL) -- per IRC 6",
        headers=None,
        body_tex=veh_body,
        col_alignments=["L", "C", "C", "C", "C", "C", "C"],
        col_widths_cm=[2.7, 1.95, 1.55, 2.20, 1.95, 2.25, 2.15],
        raw_first_head=veh_first_head,
        raw_head=veh_cont_head,
        tabcolsep_pt=COMPACT_TABCOLSEP_PT,
        font_size=r"\footnotesize",
        note=(
            f"Note: Vehicles listed strictly match those selected in the UI Loading tab. "
            f"Governing multi-lane braking force per IRC 6 Cl. 211.2: {_tex(braking_summary_str)}. "
            f"Centrifugal force (IRC 6 Cl. 212) is N/A for straight bridge alignments."
        ),
    )

    # --- Table 3.3(b): Footpath Live Load ---
    fp_table = _build_footpath_live_load_table(input_dict)

    # --- Table 3.4: Wind Load ---
    vb_val = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get('wind_speed')
    vb_str = f"{_tex(vb_val)} m/s [from Project Location]" if vb_val not in (None, "") else na_cell("N/A")
    wl_rows = [
        ("Basic Wind Speed, $V_b$", vb_str),
        ("Terrain Type", _render_value(input_dict, KEY_WL_TERRAIN_TYPE) or na_cell("N/A")),
        ("Average Exposed Height, H (m)", _render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, " m") or na_cell("N/A")),
        ("Hourly Mean Wind Speed, $V_z$", vz_str),
        ("Hourly Wind Pressure, $P_z$", pz_str),
        ("Transverse Wind Force", _render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, " kN") or na_cell("N/A")),
        ("Longitudinal Wind Force", _render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, " kN") or na_cell("N/A")),
        ("Vertical Wind Force", _render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, " kN") or na_cell("N/A")),
    ]
    wl_table = make_longtable(
        caption="Wind Load (WL) --- per IRC 6",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in wl_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    # --- Table 3.5: Earthquake Load ---
    sz_val = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get('seismic_zone')
    sz_str = f"{_tex(sz_val)} [from Project Location]" if sz_val not in (None, "") else na_cell("N/A")
    el_rows = [
        ("Seismic Zone", sz_str),
        ("Zone Factor, Z", _sl(sl_zone_factor)),
        ("Importance Factor, I", _render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR) or na_cell("N/A")),
        ("Type of Soil", _render_value(input_dict, KEY_SL_SOIL_TYPE) or na_cell("N/A")),
        ("Spectral Acceleration Coefficient, $S_a/g$", _sl(sl_spectral)),
        ("Horizontal Seismic Coefficient, $A_h$", _sl(sl_ah)),
        ("Vertical Seismic Coefficient, $A_v$", _sl(sl_av)),
    ]
    el_table = make_longtable(
        caption="Earthquake Load (EL) --- per IRC 6",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in el_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    # --- Table 3.6: Temperature Load ---
    tmax_shade = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get('shade_temp_max')
    tmin_shade = input_dict.get(KEY_TL_LOWEST_MIN_TEMP) or input_dict.get('shade_temp_min')
    tl_rows = [
        ("Maximum Shade Temperature", (f"{_tex(tmax_shade)} " + r"\textdegree{}C") if tmax_shade not in (None, "") else na_cell("N/A")),
        ("Minimum Shade Temperature", (f"{_tex(tmin_shade)} " + r"\textdegree{}C") if tmin_shade not in (None, "") else na_cell("N/A")),
        ("Effective Bridge Temp. Range", f"{_tl(tl_temp_min)} to {_tl(tl_temp_max)} " + r"\textdegree{}C"),
        ("Temperature Rise / Fall for Design", f"+{_tl(tl_rise)} " + r"\textdegree{}C / \textminus{}" + f"{_tl(tl_fall)} " + r"\textdegree{}C"),
    ]
    tl_table = make_longtable(
        caption="Temperature Load (TL) --- per IRC 6",
        headers=["Parameter", "Value"],
        body_tex="\n".join(rf"\textnormal{{{k}}} & {v} \\[4pt]" + "\n\\hline" for k, v in tl_rows),
        col_alignments=["L", "L"],
        col_widths_cm=[5.8, 9.6],
    )

    # --- Table 3.7: Load Combinations ---
    _LOAD_LABEL_MAP = {
        'dead_load': 'DL',
        'surfacing': 'SIDL',
        'live_load': 'LL',
        'wind_load': 'WL',
        'thermal_load': 'TL',
        'vehicle_collision': 'VC',
        'barge_impact': 'BI',
        'floating_bodies': 'FB',
        'seismic': 'EQ',
    }

    def _fmt_factors(factors):
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):
                add = val.get('adding')
                rel = val.get('relieving')
                add_s = f"{add:.2f}" if add is not None else '--'
                rel_s = f"{rel:.2f}" if rel is not None else '--'
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue
                parts.append(f"{label}({val:.2f})")
        return ' + '.join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        lc_rows.append(f"ULS-{i:02d} & {_fmt_factors(combo['factors'])} " + r"\\[4pt]" + "\n\\hline")
    for i, combo in enumerate(sls_combos, start=1):
        lc_rows.append(f"SLS-{i:02d} & {_fmt_factors(combo['factors'])} " + r"\\[4pt]" + "\n\\hline")

    lc_table = make_longtable(
        caption="Load Combinations",
        headers=["Combination ID", "Load Cases"],
        body_tex="\n".join(lc_rows),
        col_alignments=["C", "L"],
        col_widths_cm=[3.6, 11.8],
        note="Note: All IRC 6 load combinations are auto-generated by OsdagBridge. User-defined custom combinations, if any, are appended.",
    )

    return (
        r"""
\chapter{Loads and Load Combinations}

This section summarizes all loads applied to the bridge and the load combinations considered for analysis and design.

"""
        + dl_table + "\n\n"
        + dw_table + "\n\n"
        + veh_table + "\n\n"
        + fp_table + "\n\n"
        + wl_table + "\n\n"
        + el_table + "\n\n"
        + tl_table + "\n\n"
        + lc_table + "\n"
    )
