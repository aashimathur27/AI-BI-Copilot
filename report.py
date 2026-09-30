"""
report.py
---------
Feature 8 — Report Generator.

Builds a single-click downloadable PDF containing KPIs, charts, insights,
forecast, and recommendations, using fpdf2 (pure-Python) + matplotlib for
chart images. Matplotlib is used here (instead of Plotly/kaleido) because
kaleido v1 requires a local Chrome install, which many lightweight hosting
environments don't have — matplotlib works everywhere with zero extra setup.
The interactive Streamlit dashboard still uses Plotly; this module only
needs static images for the PDF.
"""

from __future__ import annotations
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless backend, no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from fpdf import FPDF


def _sanitize(text) -> str:
    """FPDF's core fonts only support latin-1. Swap common unicode chars for
    safe equivalents and strip anything else that won't encode."""
    if text is None:
        return ""
    text = str(text)
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u20b9": "Rs. ",
        "\u2022": "-",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 30, 30)
        self.cell(0, 12, _sanitize("AI BI Copilot - Business Report"), ln=True, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, _sanitize(datetime.now().strftime("Generated on %d %B %Y, %H:%M")), ln=True, align="C")
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 20, 20)
        self.ln(2)
        self.set_x(10)
        self.cell(0, 9, _sanitize(title), ln=True)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)


# ---------------------------------------------------------------------------
# Matplotlib chart builders — produce PNG files, no browser dependency
# ---------------------------------------------------------------------------

_ACCENT = "#3366CC"
_ACCENT2 = "#DC3912"


def _style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.tick_params(axis="x", labelrotation=30)


def chart_bar_by_group(df, group_col, value_col, title, top_n=None, horizontal=False):
    grouped = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
    if top_n:
        grouped = grouped.head(top_n)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    if horizontal:
        ax.barh(grouped.index.astype(str)[::-1], grouped.values[::-1], color=_ACCENT)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    else:
        ax.bar(grouped.index.astype(str), grouped.values, color=_ACCENT)
        _style_ax(ax)
    ax.set_title(title)
    fig.tight_layout()
    return fig


def chart_pie_by_group(df, group_col, value_col, title):
    grouped = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.pie(grouped.values, labels=grouped.index.astype(str), autopct="%1.0f%%",
           startangle=90, colors=plt.cm.Set2.colors)
    ax.set_title(title)
    fig.tight_layout()
    return fig


def chart_monthly_line(df, date_col, value_col, title):
    tmp = df.dropna(subset=[date_col, value_col]).copy()
    tmp["Month"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
    monthly = tmp.groupby("Month")[value_col].sum().sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(monthly.index, monthly.values, marker="o", color=_ACCENT)
    ax.set_title(title)
    _style_ax(ax)
    fig.tight_layout()
    return fig


def chart_forecast(hist_df, forecast_df, date_col, value_col, title="Historical + Forecast"):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(hist_df[date_col], hist_df[value_col], marker="o", color=_ACCENT, label="Historical")
    ax.plot(forecast_df[date_col], forecast_df[value_col], marker="o", linestyle="--",
            color=_ACCENT2, label="Forecast")
    ax.set_title(title)
    ax.legend()
    _style_ax(ax)
    fig.tight_layout()
    return fig


def chart_anomalies(daily_df, date_col, value_col, flag_col, title="Anomaly Detection"):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    normal = daily_df[~daily_df[flag_col]]
    anomalies = daily_df[daily_df[flag_col]]
    ax.plot(normal[date_col], normal[value_col], marker="o", markersize=3, color=_ACCENT, label="Normal")
    ax.scatter(anomalies[date_col], anomalies[value_col], color="red", marker="x", s=70, label="Anomaly", zorder=5)
    ax.set_title(title)
    ax.legend()
    _style_ax(ax)
    fig.tight_layout()
    return fig


def _save_fig(fig, path):
    try:
        fig.savefig(path, dpi=170, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception:
        plt.close(fig)
        return False


# ---------------------------------------------------------------------------
# Main PDF assembly
# ---------------------------------------------------------------------------

def generate_pdf_report(kpis: dict, insights: list[str], recommendations: list[str],
                         figures: dict, forecast_summary: str | None, output_path: str):
    """
    kpis            : dict of {label: value}
    insights        : list of insight sentences
    recommendations : list of recommendation sentences
    figures         : dict of {chart_title: matplotlib.figure.Figure}
    forecast_summary: optional sentence summarizing the forecast
    output_path     : where to write the .pdf
    """
    pdf = Report()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # --- KPIs -------------------------------------------------------------
    pdf.section_title("Key Performance Indicators")
    items = list(kpis.items())
    for idx in range(0, len(items), 2):
        pair = items[idx:idx + 2]
        pdf.set_x(10)
        for label, value in pair:
            display = "N/A" if value is None else (
                f"Rs. {value:,.0f}" if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(30, 8, _sanitize(f"{label}:"), border=0)
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(65, 8, _sanitize(display), border=0)
        pdf.ln(8)
    pdf.ln(6)

    # --- Insights -----------------------------------------------------------
    pdf.section_title("AI-Generated Insights")
    pdf.set_font("Helvetica", "", 11)
    for insight in insights:
        pdf.set_x(10)
        pdf.multi_cell(0, 7, _sanitize(f"- {insight}"))
    pdf.ln(2)

    # --- Forecast --------------------------------------------------------------
    if forecast_summary:
        pdf.section_title("Sales Forecast")
        pdf.set_font("Helvetica", "", 11)
        pdf.set_x(10)
        pdf.multi_cell(0, 7, _sanitize(forecast_summary))
        pdf.ln(2)

    # --- Recommendations -----------------------------------------------------------
    if recommendations:
        pdf.section_title("Recommendations")
        pdf.set_font("Helvetica", "", 11)
        for rec in recommendations:
            pdf.set_x(10)
            pdf.multi_cell(0, 7, _sanitize(f"- {rec}"))
        pdf.ln(2)

    # --- Charts --------------------------------------------------------------------
    if figures:
        with tempfile.TemporaryDirectory() as tmpdir:
            for title, fig in figures.items():
                if fig is None:
                    continue
                img_path = os.path.join(tmpdir, f"{title.replace(' ', '_')}.png")
                if _save_fig(fig, img_path):
                    pdf.add_page()
                    pdf.section_title(title)
                    pdf.image(img_path, x=10, w=190)

    pdf.output(output_path)
    return output_path
