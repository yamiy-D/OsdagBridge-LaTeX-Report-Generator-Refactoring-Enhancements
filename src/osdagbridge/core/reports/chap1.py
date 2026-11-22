from osdagbridge.core.reports.report_utils import _tex
from osdagbridge.core.reports.styles import make_simple_table


def ch1_project_info(m):
    rows = [
        ("Project Name", _tex(m.project_name)),
        ("Project Location", _tex(m.project_location)),
        ("Designer", _tex(m.designer)),
        ("Reviewer", _tex(m.reviewer)),
        ("Organization", _tex(m.company)),
        ("Client", _tex(m.client)),
        ("Software Version", "OsdagBridge"),
    ]
    body = "\n".join(
        rf"\textbf{{{k}}} & {v} \\[4pt]" + "\n" + r"\hline"
        for k, v in rows
    )
    info_table = make_simple_table(
        headers=["Parameter", "Value"],
        body_tex=body,
        col_alignments=["L", "L"],
        col_widths_cm=[5.5, 9.5],
        floating=False,
    )

    return (
        r"""
\chapter{Project Information}

This section records all project metadata as entered by the designer.

\section{Project and Design Team Details}
\label{sec:project-details}

"""
        + info_table
        + r"""

\section{Applicable Codes and Standards}
\label{sec:codes}

\begin{itemize}
\item Indian Roads Congress (IRC) 5: General Features of Design
\item Indian Roads Congress (IRC) 6: Loads and Load Combinations
\item Indian Roads Congress (IRC) 22: Composite Construction (Limit State Design)
\item Indian Roads Congress (IRC) 24: Steel Road Bridges (Limit State Method)
\item Indian Roads Congress (IRC) 112: Concrete Road Bridges (deck design)
\item Indian Roads Congress Special Publication (IRC SP) 114: Seismic Design of Road Bridges
\item Indian Standard (IS) 800: General Construction in Steel
\item Indian Standard (IS) 2062: Hot Rolled Structural Steel Specification
\item Indian Standard (IS) 6006: Steel Bearings
\end{itemize}
"""
    )
