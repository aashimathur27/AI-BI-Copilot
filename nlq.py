"""
nlq.py
------
Feature 5 — Ask Questions (Natural Language).

MVP approach: match the user's question against a set of predefined
templates using keyword/regex matching, then compute the answer with
Pandas. Each handler returns a dict:
    { "answer": str, "table": pd.DataFrame|None, "chart": plotly.Figure|None }

To evolve this into a full NL-to-Pandas system later, swap `answer_question`
for a call to an LLM that generates a small Pandas expression (sandboxed)
from the question + a description of the columns, then run the same
render logic on the result.
"""

from __future__ import annotations
import re
import pandas as pd
import plotly.express as px
import charts as ch


def _extract_n(question: str, default: int = 5) -> int:
    match = re.search(r"\b(\d+)\b", question)
    if match:
        return int(match.group(1))
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for w, n in words.items():
        if w in question.lower():
            return n
    return default


def answer_question(df: pd.DataFrame, question: str, cols: dict | None = None) -> dict:
    cols = cols or ch.detect_columns(df)
    q = question.lower().strip()
    sales_col = cols.get("sales")
    date_col = cols.get("date")
    customer_col = cols.get("customer")
    product_col = cols.get("product")
    category_col = cols.get("region")
    region_col = cols.get("region")

    if sales_col is None:
        return {"answer": "I couldn't detect a sales column in this dataset.", "table": None, "chart": None}

    # --- "highest/best/top month" ------------------------------------------------------
    if date_col and re.search(r"(highest|best|top|max).*(month)", q) or "which month" in q:
        tmp = df.dropna(subset=[date_col, sales_col]).copy()
        tmp["Month"] = tmp[date_col].dt.to_period("M")
        monthly = tmp.groupby("Month")[sales_col].sum().sort_values(ascending=False)
        if len(monthly):
            best_month = monthly.index[0]
            value = monthly.iloc[0]
            table = monthly.reset_index()
            table.columns = ["Month", "Sales"]
            table["Month"] = table["Month"].astype(str)
            fig = px.bar(table.head(12), x="Month", y="Sales", title="Sales by Month")
            return {
                "answer": f"**{best_month.strftime('%B %Y')}** had the highest sales — "
                          f"Revenue = ₹{value:,.0f}.",
                "table": table.head(10),
                "chart": fig,
            }

    # --- "top N customers" --------------------------------------------------------------
    if customer_col and re.search(r"(top|best).*(customer)", q):
        n = _extract_n(q, 5)
        top = df.groupby(customer_col)[sales_col].sum().sort_values(ascending=False).head(n).reset_index()
        top.columns = [customer_col, "Sales"]
        fig = px.bar(top, x="Sales", y=customer_col, orientation="h", title=f"Top {n} Customers")
        return {
            "answer": f"Here are the top {n} customers by total sales.",
            "table": top,
            "chart": fig,
        }

    # --- "top N products" -----------------------------------------------------------------
    if product_col and re.search(r"(top|best).*(product)", q):
        n = _extract_n(q, 5)
        top = df.groupby(product_col)[sales_col].sum().sort_values(ascending=False).head(n).reset_index()
        top.columns = [product_col, "Sales"]
        fig = px.bar(top, x="Sales", y=product_col, orientation="h", title=f"Top {n} Products")
        return {
            "answer": f"Here are the top {n} products by total sales.",
            "table": top,
            "chart": fig,
        }

    # --- "total sales / revenue" -----------------------------------------------------------
    if re.search(r"(total|overall).*(sales|revenue)", q):
        total = df[sales_col].sum()
        return {"answer": f"Total revenue = ₹{total:,.0f}.", "table": None, "chart": None}

    # --- "average sales" ---------------------------------------------------------------------
    if re.search(r"average.*(sales|order)", q):
        avg = df[sales_col].mean()
        return {"answer": f"Average sales value = ₹{avg:,.0f}.", "table": None, "chart": None}

    # --- "which region/category performed best" -----------------------------------------------
    if region_col and "region" in q:
        reg = df.groupby(region_col)[sales_col].sum().sort_values(ascending=False)
        table = reg.reset_index()
        table.columns = [region_col, "Sales"]
        fig = px.bar(table, x=region_col, y="Sales", title="Sales by Region")
        return {
            "answer": f"**{reg.index[0]}** leads with ₹{reg.iloc[0]:,.0f} in sales.",
            "table": table,
            "chart": fig,
        }

    if category_col and "category" in q:
        cat = df.groupby(category_col)[sales_col].sum().sort_values(ascending=False)
        table = cat.reset_index()
        table.columns = [category_col, "Sales"]
        fig = px.pie(table, names=category_col, values="Sales", title="Sales by Category")
        return {
            "answer": f"**{cat.index[0]}** leads with ₹{cat.iloc[0]:,.0f} in sales.",
            "table": table,
            "chart": fig,
        }

    return {
        "answer": "I couldn't match that question to a known template yet. Try asking things like "
                   "\"Which month had highest sales?\", \"Show me top 5 customers\", "
                   "\"What is the total revenue?\", or \"Which region performed best?\"",
        "table": None,
        "chart": None,
    }
