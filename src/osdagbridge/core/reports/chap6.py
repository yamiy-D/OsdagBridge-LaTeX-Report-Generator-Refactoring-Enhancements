from osdagbridge.core.reports.report_utils import _fig_minipage_cell, _fig_numbered


def ch6_drawings(fig_paths):
    """Chapter 6 -- Drawings and Visualizations."""
    fig_paths = fig_paths or {}

    sup3d = _fig_numbered(fig_paths.get('final_geometry'), 'Overall 3D Bridge Superstructure', 'fig:bridge-3d')
    cs = _fig_numbered(fig_paths.get('cross_section'), 'Typical Cross Section', 'fig:cross-section')
    gtop = _fig_numbered(fig_paths.get('girder_top'), 'Top View', 'fig:top-view')
    g3d = _fig_numbered(fig_paths.get('girder_3d'), '3D View of Plate Girders', 'fig:girder-3d')
    gxsec = _fig_numbered(fig_paths.get('section_preview'), 'Cross Section of Plate Girder', 'fig:girder-xsec')
    gside = _fig_numbered(fig_paths.get('stiffener_preview'), 'Side View of Girder', 'fig:girder-side')
    cbdia = _fig_numbered(fig_paths.get('cb_diagram'), 'Cross Bracing Layout', 'fig:cb-layout')

    cb_bracing = _fig_minipage_cell(fig_paths.get('cb_bracing'), 'Cross Bracing -- Bracing Section', 'fig:cb-bracing-sec')
    cb_top = _fig_minipage_cell(fig_paths.get('cb_top_chord'), 'Cross Bracing -- Top Chord Section', 'fig:cb-top-chord')
    cb_bottom = _fig_minipage_cell(fig_paths.get('cb_bottom_chord'), 'Cross Bracing -- Bottom Chord Section', 'fig:cb-bottom-chord')
    cb_sections_row = (
        r'\noindent' + '\n'
        + cb_bracing + '\n'
        + r'\hfill' + '\n'
        + cb_top + '\n'
        + r'\hfill' + '\n'
        + cb_bottom
    )

    eddia = _fig_numbered(fig_paths.get('ed_diagram'), 'End Diaphragm Layout', 'fig:ed-layout')
    ed_bracing = _fig_minipage_cell(fig_paths.get('ed_bracing'), 'End Diaphragm -- Bracing Section', 'fig:ed-bracing-sec')
    ed_top = _fig_minipage_cell(fig_paths.get('ed_top_chord'), 'End Diaphragm -- Top Chord Section', 'fig:ed-top-chord')
    ed_bottom = _fig_minipage_cell(fig_paths.get('ed_bottom_chord'), 'End Diaphragm -- Bottom Chord Section', 'fig:ed-bottom-chord')
    ed_sections_row = (
        r'\noindent' + '\n'
        + ed_bracing + '\n'
        + r'\hfill' + '\n'
        + ed_top + '\n'
        + r'\hfill' + '\n'
        + ed_bottom
    )

    return (
        r"""
\chapter{Drawings and Visualizations}
\label{ch:drawings}

This section presents CAD-generated views of the designed bridge and its components. All views are generated automatically by OsdagBridge using pythonOCC.

\section{Bridge Configuration and Layout}
\label{sec:bridge-layout}

"""
        + sup3d + '\n\n'
        + cs + '\n\n'
        + gtop + r"""

\section{Plate Girder --- Detailed Views}
\label{sec:girder-views}

"""
        + g3d + '\n\n'
        + gxsec + '\n\n'
        + gside + r"""

\section{Cross Bracing Detail}
\label{sec:bracing-detail}

"""
        + cbdia + '\n\n'
        + cb_sections_row + r"""

\section{End Diaphragm Detail}
\label{sec:diaphragm-detail}

"""
        + eddia + '\n\n'
        + ed_sections_row + "\n"
    )
