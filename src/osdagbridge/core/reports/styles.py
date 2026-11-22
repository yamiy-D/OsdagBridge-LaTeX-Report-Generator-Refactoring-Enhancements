# =============================================================================
# OsdagBridge — Centralized Report Formatting & Style System (Single Source of Truth)
# =============================================================================
"""Centralized visual tokens, page geometry, LaTeX preamble builder, and
width-safe table/badge helpers consumed by all report chapter modules and
Matplotlib chart generators.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

# -----------------------------------------------------------------------------
# Page Geometry & Dimension Constants (A4)
# -----------------------------------------------------------------------------
PT_TO_CM: float = 2.54 / 72.27
A4_WIDTH_CM: float = 21.0
TOP_MARGIN_IN: float = 1.0
BOTTOM_MARGIN_IN: float = 1.2
LEFT_MARGIN_IN: float = 0.9
RIGHT_MARGIN_IN: float = 0.9
HEAD_HEIGHT_PT: float = 18.0
HEAD_SEP_PT: float = 16.0
FOOT_SKIP_PT: float = 42.0

# Exact printable text width: 21.0 - 2 * (0.9 * 2.54) = 16.428 cm.
# Keep a small safety buffer (~0.23 cm) to prevent Overfull \hbox rounding edge cases.
TEXTWIDTH_CM: float = round(A4_WIDTH_CM - 2.0 * (LEFT_MARGIN_IN * 2.54), 2)  # 16.43 cm
SAFE_TABLE_WIDTH_CM: float = 16.20

DEFAULT_TABCOLSEP_PT: float = 4.5
COMPACT_TABCOLSEP_PT: float = 3.0
DEFAULT_ARRAYSTRETCH: float = 1.18
DEFAULT_ARRAYRULEWIDTH_PT: float = 0.5
DEFAULT_EXTRAROWHEIGHT_PT: float = 1.0
DEFAULT_ROW_SKIP: str = r"\\[4pt]"
DEFAULT_NEEDSPACE_LINES: int = 10
DEFAULT_LINE_STRETCH: float = 1.15


# -----------------------------------------------------------------------------
# Brand & Semantic Color Palette (Shared by LaTeX and Matplotlib)
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ColorPalette:
    """Canonical color tokens anchored on Osdag brand green (#91B014).

    Contrast notes:
    - osdagGreenDark (#4A5D0A) on osdagGreenTint (#EEF4D6) yields ~6.5:1 (WCAG AA).
    """

    OSDAG_GREEN: str = "91B014"
    OSDAG_GREEN_DARK: str = "4A5D0A"
    OSDAG_GREEN_TINT: str = "EEF4D6"
    OSDAG_BORDER: str = "B8C78A"
    OSDAG_TEXT: str = "1F2937"
    OSDAG_PASS: str = "2E7D32"
    OSDAG_WARN: str = "B45309"
    OSDAG_FAIL: str = "C62828"
    OSDAG_MUTED: str = "6B7280"
    OSDAG_ACCENT_BLUE: str = "2B6CB0"
    OSDAG_ACCENT_SLATE: str = "475569"

    @classmethod
    def latex_definitions(cls) -> str:
        mapping = [
            ("osdagGreen", cls.OSDAG_GREEN),
            ("osdagGreenDark", cls.OSDAG_GREEN_DARK),
            ("osdagGreenTint", cls.OSDAG_GREEN_TINT),
            ("osdagBorder", cls.OSDAG_BORDER),
            ("osdagText", cls.OSDAG_TEXT),
            ("osdagPass", cls.OSDAG_PASS),
            ("osdagWarn", cls.OSDAG_WARN),
            ("osdagFail", cls.OSDAG_FAIL),
            ("osdagMuted", cls.OSDAG_MUTED),
            ("osdagAccentBlue", cls.OSDAG_ACCENT_BLUE),
            ("osdagAccentSlate", cls.OSDAG_ACCENT_SLATE),
        ]
        return "\n".join(
            rf"\definecolor{{{name}}}{{HTML}}{{{hex_code}}}"
            for name, hex_code in mapping
        )

    @classmethod
    def chart_colors(cls) -> Dict[str, str]:
        """Hex color map prefixed with '#' for Matplotlib charts."""
        return {
            "primary": f"#{cls.OSDAG_GREEN}",
            "primary_dark": f"#{cls.OSDAG_GREEN_DARK}",
            "tint": f"#{cls.OSDAG_GREEN_TINT}",
            "border": f"#{cls.OSDAG_BORDER}",
            "text": f"#{cls.OSDAG_TEXT}",
            "pass": f"#{cls.OSDAG_PASS}",
            "warn": f"#{cls.OSDAG_WARN}",
            "fail": f"#{cls.OSDAG_FAIL}",
            "muted": f"#{cls.OSDAG_MUTED}",
            "concrete": f"#{cls.OSDAG_ACCENT_BLUE}",
            "rebar": f"#{cls.OSDAG_ACCENT_SLATE}",
        }


CHART_PALETTE: Dict[str, str] = ColorPalette.chart_colors()


# -----------------------------------------------------------------------------
# Preamble Builder
# -----------------------------------------------------------------------------
def build_preamble(
    project_name_tex: str,
    job_number_tex: str,
    report_date_tex: str,
    report_version_tex: str = "Rev 0",
) -> str:
    """Build the complete LaTeX preamble from centralized style settings.

    All arguments must already be LaTeX-escaped via ``report_utils._tex``.
    """
    color_defs = ColorPalette.latex_definitions()

    # Footrule uses e-TeX \marks (\topmarks vs \botmarks on a monotonic counter)
    # so the '* Software default value' footnote appears strictly on pages where
    # \sdstar actually landed — immune to TeX page-builder lookahead — inside a
    # zero-downward-height box that fits cleanly within footskip=42pt.
    footrule_def = (
        r"\renewcommand{\footrule}{%" + "\n"
        r"  \vbox to 0pt{\vss" + "\n"
        r"    \ifSDonPage{%" + "\n"
        r"      \hbox to \headwidth{\textcolor{osdagMuted}{\footnotesize\textit{* Software default value}}\hfil}%" + "\n"
        r"      \vspace{3pt}%" + "\n"
        r"    }{}%" + "\n"
        r"    \color{osdagGreen}\hrule width\headwidth height 1pt" + "\n"
        r"    \vspace{4pt}%" + "\n"
        r"  }%" + "\n"
        r"}"
    )

    firstpage_footrule_def = (
        r"\renewcommand{\footrule}{%" + "\n"
        r"  \vbox to 0pt{\vss" + "\n"
        r"    \color{osdagGreen}\hrule width\headwidth height 1pt" + "\n"
        r"    \vspace{4pt}%" + "\n"
        r"  }%" + "\n"
        r"}"
    )

    return (
        r"""
\documentclass[12pt,a4paper]{report}

% Encoding & Typography
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{textcomp}
\emergencystretch=1.5em

% Page Geometry (A4, generous footer clearance to prevent table/footer overlap)
\usepackage[a4paper, top="""
        + f"{TOP_MARGIN_IN}in, bottom={BOTTOM_MARGIN_IN}in, left={LEFT_MARGIN_IN}in, right={RIGHT_MARGIN_IN}in, "
        + f"headheight={HEAD_HEIGHT_PT:.0f}pt, headsep={HEAD_SEP_PT:.0f}pt, footskip={FOOT_SKIP_PT:.0f}pt"
        + r"""]{geometry}

% Core Packages
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage[table]{xcolor}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{longtable}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{lastpage}
\usepackage{makecell}
\usepackage{etoolbox}
\usepackage{needspace}

\captionsetup{
    labelfont=bf,
    justification=raggedright,
    singlelinecheck=false,
    format=plain,
    skip=4pt
}

\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}

% Global Table Spacing & Pagination Constraints
\setlength{\LTleft}{\fill}
\setlength{\LTright}{\fill}
\setlength{\tabcolsep}{"""
        + f"{DEFAULT_TABCOLSEP_PT}pt"
        + r"""}
\renewcommand{\arraystretch}{"""
        + f"{DEFAULT_ARRAYSTRETCH}"
        + r"""}
\setlength{\LTpre}{6pt}
\setlength{\LTpost}{8pt}
\setlength{\arrayrulewidth}{"""
        + f"{DEFAULT_ARRAYRULEWIDTH_PT}pt"
        + r"""}
\setlength{\extrarowheight}{"""
        + f"{DEFAULT_EXTRAROWHEIGHT_PT}pt"
        + r"""}
\widowpenalty=10000
\clubpenalty=10000

% Note: longtable natively evaluates available vertical space before switching
% TeX's output routine; avoid injecting \needspace hooks on longtable.

% Centralized Brand & Semantic Color Palette
"""
        + color_defs
        + r"""

% Shipout-Synchronized Software-Default Page Registry (works inside longtable cells)
\makeatletter
\newcommand{\sd@markpage}[1]{\global\@namedef{sd@onpage@#1}{1}}
\newcommand{\sdstar}{\textsuperscript{*}\protected@write\@auxout{}{\string\sd@markpage{\thepage}}}
\newcommand{\ifSDonPage}[2]{\ifcsname sd@onpage@\thepage\endcsname #1\else #2\fi}
\makeatother

% Header / Footer Themes
\fancypagestyle{main}{
  \fancyhf{}
  \fancyhead[L]{\small """
        + project_name_tex
        + r""" $|$ """
        + job_number_tex
        + r"""}
  \fancyhead[R]{\small """
        + report_date_tex
        + r""" $|$ """
        + report_version_tex
        + r"""}
  \fancyfoot[L]{\small Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{\small Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}
"""
        + footrule_def
        + r"""
}
\fancypagestyle{plain}{
  \fancyhf{}
  \fancyhead[L]{\small """
        + project_name_tex
        + r""" $|$ """
        + job_number_tex
        + r"""}
  \fancyhead[R]{\small """
        + report_date_tex
        + r""" $|$ """
        + report_version_tex
        + r"""}
  \fancyfoot[L]{\small Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{\small Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}
"""
        + footrule_def
        + r"""
}
\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyfoot[L]{\small Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{\small Page \thepage\ of \pageref{LastPage}}
"""
        + firstpage_footrule_def
        + r"""
}
\pagestyle{main}
\setstretch{"""
        + f"{DEFAULT_LINE_STRETCH}"
        + r"""}

% Custom Column Types & Helpers
\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}

\title{\Large\textbf{OsdagBridge} \\ \normalsize Open Source Software for Steel Girder Bridge Design \\ \vspace{2cm} \large Design Report}
\author{}
\date{}

\begin{document}
"""
    )


def chapter_title_format_tex() -> str:
    """Return consistent numbered chapter formatting with subtle Osdag rule."""
    return (
        r"\titleformat{\chapter}[block]" + "\n"
        r"  {\normalfont\Large\bfseries\color{osdagGreenDark}}{\thechapter}{1em}{}" + "\n"
        r"  [\vspace{2pt}{\color{osdagGreen}\titlerule[0.8pt]}]" + "\n"
        r"\titlespacing*{\chapter}{0pt}{-20pt}{12pt}"
    )


# -----------------------------------------------------------------------------
# Width Budget Calculation & Column Spec Builder
# -----------------------------------------------------------------------------
def compute_table_total_width_cm(
    col_widths_cm: Sequence[float],
    tabcolsep_pt: float = DEFAULT_TABCOLSEP_PT,
    rule_width_pt: float = DEFAULT_ARRAYRULEWIDTH_PT,
) -> float:
    """Compute exact rendered LaTeX table width in cm including padding and rules."""
    n_cols = len(col_widths_cm)
    padding_cm = 2.0 * n_cols * tabcolsep_pt * PT_TO_CM
    rules_cm = (n_cols + 1) * rule_width_pt * PT_TO_CM
    return sum(col_widths_cm) + padding_cm + rules_cm


def fit_column_widths(
    col_widths_cm: Sequence[float],
    tabcolsep_pt: float = DEFAULT_TABCOLSEP_PT,
    max_width_cm: float = SAFE_TABLE_WIDTH_CM,
    rule_width_pt: float = DEFAULT_ARRAYRULEWIDTH_PT,
) -> List[float]:
    """Ensure table column widths fit strictly within ``max_width_cm``.

    If ``sum(col_widths_cm) + 2*N*tabcolsep + (N+1)*rule_width > max_width_cm``,
    scales all columns proportionally so the rendered table cannot overflow
    ``\\textwidth``.
    """
    n_cols = len(col_widths_cm)
    if n_cols == 0:
        return []
    overhead_cm = (
        2.0 * n_cols * tabcolsep_pt * PT_TO_CM
        + (n_cols + 1) * rule_width_pt * PT_TO_CM
    )
    available_cm = max(1.0, max_width_cm - overhead_cm)
    raw_sum = sum(col_widths_cm)
    if raw_sum <= available_cm:
        return [round(w, 2) for w in col_widths_cm]
    scale = available_cm / raw_sum
    # Floor at 2 decimal places so rounding never pushes total back over budget
    return [int(w * scale * 100.0) / 100.0 for w in col_widths_cm]


def build_col_spec(
    col_alignments: Sequence[str],
    col_widths_cm: Sequence[float],
    tabcolsep_pt: float = DEFAULT_TABCOLSEP_PT,
    max_width_cm: float = SAFE_TABLE_WIDTH_CM,
) -> str:
    """Build a LaTeX column specification string (e.g. ``|L{3.50cm}|C{2.00cm}|``).

    Supported alignment codes: ``'L'``, ``'C'``, ``'R'``, ``'p'``.
    """
    if len(col_alignments) != len(col_widths_cm):
        raise ValueError(
            f"Column alignment count ({len(col_alignments)}) != width count ({len(col_widths_cm)})"
        )
    fitted = fit_column_widths(
        col_widths_cm, tabcolsep_pt=tabcolsep_pt, max_width_cm=max_width_cm
    )
    parts = []
    for align, width in zip(col_alignments, fitted):
        code = align.strip()
        if code in ("L", "C", "R", "p"):
            parts.append(f"{code}{{{width:.2f}cm}}")
        else:
            parts.append(f"L{{{width:.2f}cm}}")
    return "|" + "|".join(parts) + "|"


# -----------------------------------------------------------------------------
# Cell, Badge, Banner & Note Helpers
# -----------------------------------------------------------------------------
def style_header_cells(headers: Sequence[str]) -> str:
    """Format a styled header row with Osdag light green tint and dark olive text."""
    styled = [
        rf"\textcolor{{osdagGreenDark}}{{\textbf{{{h}}}}}" if h else ""
        for h in headers
    ]
    return r"\rowcolor{osdagGreenTint}" + "\n" + " & ".join(styled) + r" \\[4pt]"


def girder_banner_row(label_tex: str, n_cols: int) -> str:
    """Full-width tinted group banner row inside a ``longtable``.

    Uses starred line break ``\\\\*`` plus ``\\noalign{\\nobreak}`` around
    ``\\hline`` so LaTeX keeps the banner attached to the first data row
    below it across page breaks.
    """
    return (
        rf"\multicolumn{{{n_cols}}}{{|l|}}"
        rf"{{\cellcolor{{osdagGreenTint}}\textcolor{{osdagGreenDark}}{{\textbf{{{label_tex}}}}}}} \\*"
        "\n"
        r"\noalign{\nobreak}\hline\noalign{\nobreak}"
    )


def status_badge(status: Optional[str]) -> str:
    """Format PASS / WARN / FAIL / N/A status text using centralized palette colors."""
    if status is None:
        return "---"
    raw = str(status).strip()
    if not raw or raw == "---":
        return "---"
    upper = raw.upper()
    if "FAIL" in upper:
        return rf"\textcolor{{osdagFail}}{{\textbf{{{raw}}}}}"
    if "WARN" in upper:
        return rf"\textcolor{{osdagWarn}}{{\textbf{{{raw}}}}}"
    if "PASS" in upper:
        return rf"\textcolor{{osdagPass}}{{\textbf{{{raw}}}}}"
    if upper in ("N/A", "N.A."):
        return na_cell(raw)
    return raw


def ur_cell(value: Optional[float], decimals: int = 2) -> str:
    """Format a numeric Utilization Ratio cell with semantic threshold coloring."""
    if value is None:
        return "---"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "---"
    text = f"{f:.{decimals}f}"
    if f > 1.0:
        return rf"\textcolor{{osdagFail}}{{\textbf{{{text}}}}}"
    if f >= 0.90:
        return rf"\textcolor{{osdagWarn}}{{\textbf{{{text}}}}}"
    return text


def na_cell(text: str = "N/A") -> str:
    """Render an explicit muted N/A cell."""
    return rf"\textit{{\textcolor{{osdagMuted}}{{{text}}}}}"


def section_note(text: str) -> str:
    """Format a table or section footnote cleanly beneath a table."""
    return r"\noindent\footnotesize\textit{" + text + r"}\normalsize"


# -----------------------------------------------------------------------------
# Balanced LongTable & Simple Table Builders
# -----------------------------------------------------------------------------
def make_longtable(
    caption: str,
    headers: Optional[Sequence[str]],
    body_tex: str,
    col_alignments: Sequence[str],
    col_widths_cm: Sequence[float],
    *,
    label: Optional[str] = None,
    note: Optional[str] = None,
    tabcolsep_pt: float = DEFAULT_TABCOLSEP_PT,
    arraystretch: Optional[float] = None,
    font_size: Optional[str] = None,
    raw_first_head: Optional[str] = None,
    raw_head: Optional[str] = None,
    continued_footer: bool = True,
) -> str:
    """Emit a balanced, width-safe ``longtable`` with repeated page-break headers.

    Guarantees:
    - Wrapped in balanced ``\\begingroup ... \\endgroup`` so local ``tabcolsep``,
      ``arraystretch``, and font size never leak to downstream chapters.
    - Column widths auto-fitted inside ``SAFE_TABLE_WIDTH_CM``.
    - Mandatory trailing ``\\\\`` after ``\\caption{\\textbf{...}}``.
    - Complete ``\\endfirsthead`` and ``\\endhead`` blocks so every page break
      repeats column headers automatically.
    - Optional ``Continued on next page`` footer via ``\\endfoot`` / ``\\endlastfoot``.
    """
    n_cols = len(col_alignments)
    col_spec = build_col_spec(col_alignments, col_widths_cm, tabcolsep_pt=tabcolsep_pt)
    label_tex = rf"\label{{{label}}}" if label else ""

    if raw_first_head is not None and raw_head is not None:
        first_head_block = raw_first_head.strip()
        cont_head_block = raw_head.strip()
    else:
        hdr_row = style_header_cells(headers or [])
        first_head_block = (
            rf"\caption{{\textbf{{{caption}}}}}{label_tex}\\" + "\n"
            r"\hline" + "\n"
            + hdr_row + "\n"
            r"\hline"
        )
        cont_head_block = (
            rf"\multicolumn{{{n_cols}}}{{l}}{{\small\textit{{Table \thetable\ (continued): {caption}}}}} \\" + "\n"
            r"\hline" + "\n"
            + hdr_row + "\n"
            r"\hline"
        )

    if continued_footer:
        foot_block = (
            rf"\multicolumn{{{n_cols}}}{{r}}{{\footnotesize\textit{{\textcolor{{osdagMuted}}{{Continued on next page\ldots}}}}}} \\" + "\n"
            r"\endfoot" + "\n"
            r"\endlastfoot"
        )
    else:
        foot_block = r"\endfoot" + "\n" + r"\endlastfoot"

    local_cmds = [rf"\setlength{{\tabcolsep}}{{{tabcolsep_pt}pt}}"]
    if arraystretch is not None:
        local_cmds.append(rf"\renewcommand{{\arraystretch}}{{{arraystretch}}}")
    if font_size:
        local_cmds.append(font_size)

    parts = [
        r"\begingroup",
        "\n".join(local_cmds),
        rf"\begin{{longtable}}{{{col_spec}}}",
        first_head_block,
        r"\endfirsthead",
        cont_head_block,
        r"\endhead",
        foot_block,
        body_tex.strip(),
        r"\end{longtable}",
        r"\endgroup",
    ]
    if note:
        parts.append(section_note(note))
    return "\n".join(parts)


def make_simple_table(
    headers: Optional[Sequence[str]],
    body_tex: str,
    col_alignments: Sequence[str],
    col_widths_cm: Sequence[float],
    *,
    caption: Optional[str] = None,
    label: Optional[str] = None,
    note: Optional[str] = None,
    tabcolsep_pt: float = DEFAULT_TABCOLSEP_PT,
    arraystretch: Optional[float] = None,
    font_size: Optional[str] = None,
    floating: bool = True,
) -> str:
    """Emit a balanced, width-safe non-splitting ``tabular`` table.

    When ``caption`` is provided and ``floating=True``, wraps inside ``table[H]``.
    """
    col_spec = build_col_spec(col_alignments, col_widths_cm, tabcolsep_pt=tabcolsep_pt)
    local_cmds = [rf"\setlength{{\tabcolsep}}{{{tabcolsep_pt}pt}}"]
    if arraystretch is not None:
        local_cmds.append(rf"\renewcommand{{\arraystretch}}{{{arraystretch}}}")
    if font_size:
        local_cmds.append(font_size)

    tab_lines = [
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"\hline",
    ]
    if headers:
        tab_lines.append(style_header_cells(headers))
        tab_lines.append(r"\hline")
    tab_lines.append(body_tex.strip())
    tab_lines.append(r"\end{tabular}")
    tabular_tex = "\n".join(tab_lines)

    parts = [r"\begingroup", "\n".join(local_cmds)]
    if floating and caption:
        parts.append(r"\begin{table}[H]")
        parts.append(r"\centering")
        parts.append(rf"\caption{{\textbf{{{caption}}}}}")
        if label:
            parts.append(rf"\label{{{label}}}")
        parts.append(tabular_tex)
        parts.append(r"\end{table}")
    else:
        parts.append(r"\begin{center}")
        parts.append(tabular_tex)
        parts.append(r"\end{center}")
    parts.append(r"\endgroup")

    if note:
        parts.append(section_note(note))
    return "\n".join(parts)
