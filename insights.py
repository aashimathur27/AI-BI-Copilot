"""
insights.py
-----------
Feature 4 — AI Insight Generator.

Rule-based (deterministic) natural-language insights computed straight
from the data — no LLM required for the MVP. Each rule below is a small,
self-contained function so it's easy to add more later. To upgrade to
LLM-polished phrasing, feed the raw `facts` dict this module returns into
an LLM prompt template ("rewrite these bullet facts as a friendly
executive summary") — the numbers stay grounded in real calculations,
only the wording changes.
"""

from __future__ import annotations
import pandas as pd
import charts as ch


def _pct_change(curr, prev):
    if prev in (0, None) or pd.isna(prev):
        return None
    return (curr - prev) / prev * 100


def generate_insights(df: pd.DataFrame, cols: dict | None = None) -> list[str]:
    cols = cols or ch.detect_columns(df)
    sales_col = cols.get("sales")
    date_col = cols.get("date")
    category_col = cols.get("category")
    region_col = cols.get("region")
    profit_col = cols.get("profit")

    insights: list[str] = []
    if sales_col is None:
        return ["Not enough recognizable sales data to generate insights."]

    # 1. Month-over-month sales change ------------------------------------------------
    if date_col:
        tmp = df.dropna(subset=[date_col, sales_col]).copy()
        tmp["Month"] = tmp[date_col].dt.to_period("M")
        monthly = tmp.groupby("Month")[sales_col].sum().sort_index()
        if len(monthly) >= 2:
            latest, prev = monthly.iloc[-1], monthly.iloc[-2]
            change = _pct_change(latest, prev)
            month_name = monthly.index[-1].strftime("%B")
            if change is not None:
                direction = "increased" if change >= 0 else "decreased"
                insights.append(
                    f"Sales {direction} by {abs(change):.1f}% during {month_name} "
                    f"compared to the previous month."
                )
        if len(monthly) >= 1:
            best_month = monthly.idxmax()
            insights.append(
                f"{best_month.strftime('%B %Y')} had the highest sales, "
                f"totaling ₹{monthly.max():,.0f}."
            )

    # 2. Best category by revenue -------------------------------------------------------
    if category_col:
        cat_sales = df.groupby(category_col)[sales_col].sum().sort_values(ascending=False)
        if len(cat_sales) > 0:
            insights.append(
                f"'{cat_sales.index[0]}' category generated the highest revenue "
                f"(₹{cat_sales.iloc[0]:,.0f})."
            )
            if len(cat_sales) > 1:
                # Declining category check needs a time trend; approximate using date if available
                if date_col:
                    tmp = df.dropna(subset=[date_col, sales_col, category_col]).copy()
                    tmp["Month"] = tmp[date_col].dt.to_period("M")
                    for cat in cat_sales.index:
                        series = tmp[tmp[category_col] == cat].groupby("Month")[sales_col].sum().sort_index()
                        if len(series) >= 3:
                            recent_trend = series.iloc[-1] - series.iloc[-3]
                            if recent_trend < 0 and series.iloc[-3] > 0:
                                drop_pct = abs(recent_trend) / series.iloc[-3] * 100
                                insights.append(
                                    f"'{cat}' category shows declining sales, down "
                                    f"{drop_pct:.1f}% over the last 3 months."
                                )
                                break

    # 3. Best region by profit or sales --------------------------------------------------
    if region_col:
        metric_col = profit_col if profit_col else sales_col
        metric_label = "profit" if profit_col else "sales"
        reg_metric = df.groupby(region_col)[metric_col].sum().sort_values(ascending=False)
        if len(reg_metric) > 0:
            insights.append(
                f"'{reg_metric.index[0]}' region had the maximum {metric_label} "
                f"(₹{reg_metric.iloc[0]:,.0f})."
            )

    # 4. Overall profit margin -------------------------------------------------------------
    if profit_col:
        total_sales = df[sales_col].sum()
        total_profit = df[profit_col].sum()
        if total_sales:
            margin = total_profit / total_sales * 100
            insights.append(f"Overall profit margin stands at {margin:.1f}%.")

    if not insights:
        insights.append("Dataset loaded successfully, but no category/region/date columns "
                         "were detected to generate deeper insights.")

    return insights
