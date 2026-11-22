from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_TS_NO_OF_GIRDERS,
)


def _tex(value):
    """Escape a Python value for safe LaTeX embedding (including UTF-8 symbols)."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    # 1. Normalize ASCII-safe Unicode glyphs before LaTeX metacharacter escaping
    for uni, ascii_ in [
        ('∠', 'L'),
        ('ⅹ', 'x'),
        ('×', 'x'),
        ('–', '--'),
        ('—', '---'),
    ]:
        s = s.replace(uni, ascii_)

    # 2. Escape LaTeX metacharacters
    s = s.replace('\\', r'\textbackslash{}')
    for ch, esc in [
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('_', r'\_\allowbreak{}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\^{}'),
    ]:
        s = s.replace(ch, esc)
    s = s.replace(':', r':\allowbreak{}')

    # 3. Map remaining non-ASCII engineering glyphs to safe LaTeX macros
    for uni, latex_macro in [
        ('°', r'\textdegree{}'),
        ('²', r'\textsuperscript{2}'),
        ('³', r'\textsuperscript{3}'),
        ('±', r'\textpm{}'),
        ('≤', r'$\leq$'),
        ('≥', r'$\geq$'),
        ('φ', r'$\phi$'),
        ('Φ', r'$\Phi$'),
        ('Ø', r'\O{}'),
        ('→', r'$\rightarrow$'),
    ]:
        s = s.replace(uni, latex_macro)
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Returns:
        List[Tuple[str, str]]
    """
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0) or 0)

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def extract_osdag_member_summary(result: dict) -> dict:
    """Pure-Python extractor matching ``results_data._extract_osdag_summary``
    without pulling in ``openseespy`` at report-generation time.
    """
    if not isinstance(result, dict) or not result:
        return {}

    def _first(*keys):
        for k in keys:
            v = result.get(k)
            if v is not None:
                return v
        return None

    return {
        "section": _first("section_size.designation", "Optimum.Designation"),
        "capacity_kN": _first("Member.tension_capacity", "Design.Strength"),
        "efficiency": _first("Member.efficiency", "Optimum.UR"),
        "slenderness": result.get("Member.Slenderness"),
        "connection": "Welded" if "Weld.Type" in result else "Bolted",
    }


def _fig_or_placeholder(path, caption, width=r'0.9\textwidth'):
    """Embed figure if path is provided, else show styled placeholder box."""
    if path:
        p = path.replace('\\', '/')
        return (
            r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\includegraphics[width=' + width + ']{' + p + '}\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}'
        )
    return (
        r'\begin{figure}[H]' + '\n'
        r'\centering' + '\n'
        r'\fbox{\parbox{0.97\textwidth}{' + '\n'
        r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
        r'}}' + '\n'
        r'\caption*{' + caption + '}\n'
        r'\end{figure}'
    )


def _fig_embed(path, caption, width=r'\textwidth', height=None):
    """Embed a figure when path is provided; otherwise render a compact placeholder."""
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (
            r'\begin{figure}[H]' + '\n'
            r'\vspace{-0.3em}' + '\n'
            r'\centering' + '\n'
            r'\includegraphics[' + opts + ']{' + p + '}\n'
            r'\vspace{0.3em}' + '\n'
            r'\caption*{\small ' + caption + '}\n'
            r'\vspace{-0.3em}' + '\n'
            r'\end{figure}'
        )
    return (
        r'\noindent\fbox{\parbox{0.97\textwidth}{' + '\n'
        r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
        r'}}'
    )


def _fig_numbered(path, title, label=None, width=r'0.85\textwidth'):
    """Numbered figure block (used in Chapters 5, 6, 7); placeholder if path absent."""
    label_tex = (r'\label{' + label + '}\n') if label else ''
    if path:
        p = path.replace('\\', '/')
        return (
            r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\vspace{4pt}' + '\n'
            r'\includegraphics[width=' + width + ']{' + p + '}\n'
            r'\caption{' + title + '}\n'
            + label_tex
            + r'\end{figure}' + '\n'
        )
    return (
        r'\begin{figure}[H]' + '\n'
        r'\centering' + '\n'
        r'\fbox{\parbox{0.97\textwidth}{' + '\n'
        r'\textit{[ PLACEHOLDER: ' + title + r' ]}' + '\n'
        r'}}' + '\n'
        r'\caption{' + title + '}\n'
        + label_tex
        + r'\end{figure}' + '\n'
    )


def _fig_minipage_cell(path, title, label=None, cell_width=r'0.31\textwidth'):
    """Minipage figure cell for side-by-side multi-figure rows (Chapter 6)."""
    label_tex = (r'\label{' + label + '}') if label else ''
    if path:
        p = path.replace('\\', '/')
        body = r'\includegraphics[width=\linewidth]{' + p + '}'
    else:
        body = r'\fbox{\parbox{0.95\linewidth}{\centering\textit{[ ' + title + r' ]}}}'
    return (
        r'\begin{minipage}[t]{' + cell_width + '}' + '\n'
        r'\centering' + '\n'
        + body + '\n'
        r'\captionof{figure}{' + title + '}\n'
        + label_tex + '\n'
        r'\end{minipage}'
    )
