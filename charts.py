"""
charts.py
---------
Reusable Plotly chart builders + a small "column detector" that guesses
which columns represent sales/revenue, profit, date, category, region,
customer, orders, etc. This lets the rest of the app work with datasets
that use different column-naming conventions (Superstore, Amazon, Walmart,
Flipkart, or a user's own file) without asking the user to map fields.
"""

from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Candidate keywords per semantic role, checked against lowercased column names.
FIELD_KEYWORDS = {
    "date": ["date", "order date", "order_date", "purchase date"],
    "sales": ["sales", "revenue", "amount", "total", "price"],
    "profit": ["profit", "margin"],
    "quantity": ["quantity", "qty", "units"],
    "category": ["category", "product category", "product_category"],
    "product": ["product name", "product", "item"],
    "region": ["region", "state", "country", "market"],
    "customer": ["customer name", "customer", "client"],
    "order_id": ["order id", "order_id", "invoice", "transaction id"],
}


def detect_columns(df: pd.DataFrame) -> dict:
    """Best-effort guess of which column plays which business role."""
    cols_lower = {c: c.lower() for c in df.columns}
    detected = {}
    for role, keywords in FIELD_KEYWORDS.items():
        match = None
        for col, low in cols_lower.items():
            if any(kw == low for kw in keywords):
                match = col
                break
        if match is None:
            for col, low in cols_lower.items():
                if any(kw in low for kw in keywords):
                    match = col
                    break
        detected[role] = match

    # Fallback: if no explicit "sales" column found, use first numeric column
    if detected["sales"] is None:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        # exclude columns already used for other numeric roles
        used = {detected.get("profit"), detected.get("quantity")}
        numeric_cols = [c for c in numeric_cols if c not in used]
        if numeric_cols:
            detected["sales"] = numeric_cols[0]

    # Fallback: if no date column detected, try any datetime dtype column
    if detected["date"] is None:
        dt_cols = df.select_dtypes(include="datetime").columns.tolist()
        if dt_cols:
            detected["date"] = dt_cols[0]

    return detected


# ---------------------------------------------------------------------------
# Chart builders (all return a Plotly Figure)
# ---------------------------------------------------------------------------

def monthly_sales_chart(df, date_col, sales_col):
    tmp = df.dropna(subset=[date_col, sales_col]).copy()
    tmp["Month"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
    monthly = tmp.groupby("Month", as_index=False)[sales_col].sum()
    fig = px.bar(monthly, x="Month", y=sales_col, title="Monthly Sales")
    fig.update_layout(margin=dict(t=50, l=10, r=10, b=10))
    return fig


def revenue_trend_chart(df, date_col, sales_col):
    tmp = df.dropna(subset=[date_col, sales_col]).copy()
    tmp["Month"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
    monthly = tmp.groupby("Month", as_index=False)[sales_col].sum()
    fig = px.line(monthly, x="Month", y=sales_col, markers=True, title="Revenue Trend")
    fig.update_layout(margin=dict(t=50, l=10, r=10, b=10))
    return fig


def top_products_chart(df, product_col, sales_col, n=10):
    if product_col is None:
        return None
    top = df.groupby(product_col, as_index=False)[sales_col].sum().sort_values(
        sales_col, ascending=False
    ).head(n)
    fig = px.bar(top, x=sales_col, y=product_col, orientation="h", title=f"Top {n} Products")
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
    return fig


def category_revenue_chart(df, category_col, sales_col):
    if category_col is None:
        return None
    cat = df.groupby(category_col, as_index=False)[sales_col].sum().sort_values(
        sales_col, ascending=False
    )
    fig = px.pie(cat, names=category_col, values=sales_col, title="Category-wise Revenue", hole=0.4)
    fig.update_layout(margin=dict(t=50, l=10, r=10, b=10))
    return fig


def region_revenue_chart(df, region_col, sales_col):
    if region_col is None:
        return None
    reg = df.groupby(region_col, as_index=False)[sales_col].sum().sort_values(
        sales_col, ascending=False
    )
    fig = px.bar(reg, x=region_col, y=sales_col, title="Region-wise Revenue", color=region_col)
    fig.update_layout(showlegend=False, margin=dict(t=50, l=10, r=10, b=10))
    return fig


def top_customers_chart(df, customer_col, sales_col, n=10):
    if customer_col is None:
        return None
    top = df.groupby(customer_col, as_index=False)[sales_col].sum().sort_values(
        sales_col, ascending=False
    ).head(n)
    fig = px.bar(top, x=sales_col, y=customer_col, orientation="h", title=f"Top {n} Customers")
    fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
    return fig


def forecast_chart(history_df, forecast_df, date_col, value_col):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history_df[date_col], y=history_df[value_col],
        mode="lines+markers", name="Historical", line=dict(color="#3366CC")
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df[date_col], y=forecast_df[value_col],
        mode="lines+markers", name="Forecast", line=dict(color="#DC3912", dash="dash")
    ))
    fig.update_layout(title="Historical + Forecast", margin=dict(t=50, l=10, r=10, b=10))
    return fig


def anomaly_chart(df, date_col, value_col, anomaly_flag_col):
    fig = go.Figure()
    normal = df[~df[anomaly_flag_col]]
    anomalies = df[df[anomaly_flag_col]]
    fig.add_trace(go.Scatter(
        x=normal[date_col], y=normal[value_col], mode="lines+markers",
        name="Normal", line=dict(color="#3366CC")
    ))
    fig.add_trace(go.Scatter(
        x=anomalies[date_col], y=anomalies[value_col], mode="markers",
        name="Anomaly", marker=dict(color="red", size=11, symbol="x")
    ))
    fig.update_layout(title="Anomaly Detection", margin=dict(t=50, l=10, r=10, b=10))
    return fig
