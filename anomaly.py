"""
anomaly.py
----------
Feature 7 — Anomaly Detection.

Two interchangeable methods:
  - Z-score        : fast, simple, good default for smaller datasets.
  - Isolation Forest: better for larger, less normally-distributed data.

Both work on a daily-aggregated sales series and return the aggregated
DataFrame with an `is_anomaly` boolean column, ready for charts.anomaly_chart().
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest


def _daily_series(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    tmp = df.dropna(subset=[date_col, value_col]).copy()
    tmp["Day"] = tmp[date_col].dt.floor("D")
    daily = tmp.groupby("Day", as_index=False)[value_col].sum().sort_values("Day")
    return daily.reset_index(drop=True)


def detect_anomalies_zscore(df, date_col, value_col, threshold=3.0):
    daily = _daily_series(df, date_col, value_col)
    if len(daily) < 3:
        daily["is_anomaly"] = False
        return daily
    mean, std = daily[value_col].mean(), daily[value_col].std()
    if std == 0 or pd.isna(std):
        daily["is_anomaly"] = False
        return daily
    daily["z_score"] = (daily[value_col] - mean) / std
    daily["is_anomaly"] = daily["z_score"].abs() > threshold
    return daily


def detect_anomalies_isolation_forest(df, date_col, value_col, contamination=0.05):
    daily = _daily_series(df, date_col, value_col)
    if len(daily) < 10:
        # Isolation Forest needs a reasonable sample size; fall back to z-score
        return detect_anomalies_zscore(df, date_col, value_col)
    model = IsolationForest(contamination=contamination, random_state=42)
    preds = model.fit_predict(daily[[value_col]])
    daily["is_anomaly"] = preds == -1
    return daily


def detect_anomalies(df, date_col, value_col, method="isolation_forest", **kwargs):
    if method == "zscore":
        return detect_anomalies_zscore(df, date_col, value_col, **kwargs)
    return detect_anomalies_isolation_forest(df, date_col, value_col, **kwargs)
