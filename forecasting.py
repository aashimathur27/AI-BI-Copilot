"""
forecasting.py
--------------
Feature 6 — Sales Forecasting.

MVP uses scikit-learn Linear Regression on a monthly-aggregated time
index (fast, dependency-light, works with tiny datasets). If the
`prophet` package is installed, `forecast_sales(..., method="prophet")`
will use it automatically for a more sophisticated seasonal forecast.
ARIMA (statsmodels) is left as an optional extension - see
`forecast_arima` below, only called if statsmodels is available.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


def _monthly_series(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    tmp = df.dropna(subset=[date_col, value_col]).copy()
    tmp["Month"] = tmp[date_col].dt.to_period("M").dt.to_timestamp()
    monthly = tmp.groupby("Month", as_index=False)[value_col].sum()
    return monthly.sort_values("Month").reset_index(drop=True)


def forecast_linear(df, date_col, value_col, periods=3):
    monthly = _monthly_series(df, date_col, value_col)
    if len(monthly) < 2:
        return monthly, pd.DataFrame(columns=["Month", value_col])

    monthly["t"] = np.arange(len(monthly))
    model = LinearRegression()
    X = monthly[["t"]].to_numpy()
    model.fit(X, monthly[value_col])

    future_t = np.arange(len(monthly), len(monthly) + periods)
    preds = model.predict(future_t.reshape(-1, 1))
    preds = np.clip(preds, a_min=0, a_max=None)  # sales can't be negative

    last_month = monthly["Month"].iloc[-1]
    future_months = pd.date_range(last_month, periods=periods + 1, freq="MS")[1:]

    forecast_df = pd.DataFrame({"Month": future_months, value_col: preds})
    return monthly[["Month", value_col]], forecast_df


def forecast_prophet(df, date_col, value_col, periods=3):
    try:
        from prophet import Prophet
    except ImportError:
        return forecast_linear(df, date_col, value_col, periods)

    monthly = _monthly_series(df, date_col, value_col)
    if len(monthly) < 2:
        return monthly, pd.DataFrame(columns=["Month", value_col])

    prophet_df = monthly.rename(columns={"Month": "ds", value_col: "y"})
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.fit(prophet_df)
    future = model.make_future_dataframe(periods=periods, freq="MS")
    forecast = model.predict(future)

    hist = monthly[["Month", value_col]]
    future_part = forecast.tail(periods)[["ds", "yhat"]].rename(
        columns={"ds": "Month", "yhat": value_col}
    )
    future_part[value_col] = future_part[value_col].clip(lower=0)
    return hist, future_part


def forecast_sales(df, date_col, value_col, periods=3, method="linear"):
    """
    method: "linear" (default, always available) or "prophet" (auto-falls back to linear).
    periods: number of future months to predict (1, 3, or 6 typically).
    """
    if method == "prophet":
        return forecast_prophet(df, date_col, value_col, periods)
    return forecast_linear(df, date_col, value_col, periods)
