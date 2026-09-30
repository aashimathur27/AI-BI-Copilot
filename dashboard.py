"""
dashboard.py
------------
Builds the "Smart Dashboard": KPI cards + the standard chart set,
using columns auto-detected by charts.detect_columns().
"""

import streamlit as st
import pandas as pd
import charts as ch


def compute_kpis(df: pd.DataFrame, cols: dict) -> dict:
    sales_col = cols.get("sales")
    profit_col = cols.get("profit")
    order_col = cols.get("order_id")
    customer_col = cols.get("customer")

    kpis = {}
    kpis["Total Revenue"] = df[sales_col].sum() if sales_col else None
    kpis["Average Sales"] = df[sales_col].mean() if sales_col else None
    kpis["Profit"] = df[profit_col].sum() if profit_col else None
    kpis["Orders"] = df[order_col].nunique() if order_col else len(df)
    kpis["Customers"] = df[customer_col].nunique() if customer_col else None
    return kpis


def _fmt_currency(v):
    if v is None or pd.isna(v):
        return "N/A"
    return f"₹{v:,.0f}" if abs(v) >= 1 else f"₹{v:,.2f}"


def render_kpi_cards(kpis: dict):
    cols = st.columns(5)
    labels_fmt = {
        "Total Revenue": _fmt_currency,
        "Average Sales": _fmt_currency,
        "Profit": _fmt_currency,
        "Orders": lambda v: "N/A" if v is None else f"{v:,}",
        "Customers": lambda v: "N/A" if v is None else f"{v:,}",
    }
    for col, (label, value) in zip(cols, kpis.items()):
        fmt = labels_fmt.get(label, str)
        col.metric(label, fmt(value) if value is not None else "N/A")


def render_dashboard(df: pd.DataFrame):
    detected = ch.detect_columns(df)
    sales_col = detected.get("sales")
    date_col = detected.get("date")

    if sales_col is None:
        st.warning("Couldn't auto-detect a sales/revenue column — showing raw data preview only.")
        st.dataframe(df.head(20), use_container_width=True)
        return detected

    st.subheader("📌 Key Performance Indicators")
    kpis = compute_kpis(df, detected)
    render_kpi_cards(kpis)

    st.subheader("📊 Charts")
    row1c1, row1c2 = st.columns(2)
    if date_col:
        with row1c1:
            st.plotly_chart(ch.monthly_sales_chart(df, date_col, sales_col), use_container_width=True)
        with row1c2:
            st.plotly_chart(ch.revenue_trend_chart(df, date_col, sales_col), use_container_width=True)
    else:
        st.info("No date column detected — monthly/trend charts are skipped.")

    row2c1, row2c2 = st.columns(2)
    with row2c1:
        fig = ch.top_products_chart(df, detected.get("product"), sales_col)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with row2c2:
        fig = ch.category_revenue_chart(df, detected.get("category"), sales_col)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    row3c1, row3c2 = st.columns(2)
    with row3c1:
        fig = ch.region_revenue_chart(df, detected.get("region"), sales_col)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with row3c2:
        fig = ch.top_customers_chart(df, detected.get("customer"), sales_col)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    return detected
