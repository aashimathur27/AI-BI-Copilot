"""
cleaning.py
-----------
Automatic data cleaning - no user prompts required.

Detects and fixes, in order:
  1. Incorrect data types (numeric-looking strings, date-looking strings)
  2. Duplicate rows
  3. Missing values (median for numeric, mode for categorical)
  4. Outliers (capped using the IQR method; original values are preserved
     in a `<col>_was_outlier` flag column when `flag_outliers=True`)

Returns the cleaned DataFrame plus a human-readable summary of every
change made, so the UI can show the user exactly what happened.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def _try_numeric(series: pd.Series) -> pd.Series | None:
    """Return a numeric-coerced version of series if >=90% of non-null values convert."""
    coerced = pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )
    non_null = series.notna().sum()
    if non_null == 0:
        return None
    success_rate = coerced.notna().sum() / non_null
    return coerced if success_rate >= 0.9 else None


def _try_datetime(series: pd.Series) -> pd.Series | None:
    coerced = pd.to_datetime(series, errors="coerce")
    non_null = series.notna().sum()
    if non_null == 0:
        return None
    success_rate = coerced.notna().sum() / non_null
    return coerced if success_rate >= 0.9 else None


def clean_data(df: pd.DataFrame, flag_outliers: bool = True):
    """
    Clean a raw DataFrame automatically.

    Returns
    -------
    cleaned_df : pd.DataFrame
    summary    : dict  -- details of every fix applied (for display in the UI)
    """
    df = df.copy()
    summary = {
        "dtype_fixes": [],
        "duplicates_removed": 0,
        "missing_value_fixes": [],
        "outliers_fixed": [],
        "rows_before": len(df),
        "rows_after": None,
    }

    # 0. Normalise column names
    df.columns = [str(c).strip() for c in df.columns]

    # 1. Fix incorrect data types -------------------------------------------------
    for col in df.columns:
        is_textlike = df[col].dtype == object or pd.api.types.is_string_dtype(df[col])
        if is_textlike:
            numeric_version = _try_numeric(df[col])
            if numeric_version is not None:
                df[col] = numeric_version
                summary["dtype_fixes"].append(f"'{col}': text -> numeric")
                continue
            # only attempt datetime parsing on columns that look date-like
            if any(k in col.lower() for k in ("date", "time", "day", "month", "year")):
                dt_version = _try_datetime(df[col])
                if dt_version is not None:
                    df[col] = dt_version
                    summary["dtype_fixes"].append(f"'{col}': text -> datetime")

    # 2. Remove duplicate rows -----------------------------------------------------
    before = len(df)
    df = df.drop_duplicates()
    summary["duplicates_removed"] = before - len(df)

    # 3. Handle missing values ------------------------------------------------------
    for col in df.columns:
        n_missing = df[col].isna().sum()
        if n_missing == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            fill_value = df[col].median()
            df[col] = df[col].fillna(fill_value)
            summary["missing_value_fixes"].append(
                f"'{col}': {n_missing} missing -> filled with median ({round(fill_value, 2)})"
            )
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].ffill().bfill()
            summary["missing_value_fixes"].append(
                f"'{col}': {n_missing} missing -> forward/backward filled"
            )
        else:
            mode_series = df[col].mode(dropna=True)
            fill_value = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            df[col] = df[col].fillna(fill_value)
            summary["missing_value_fixes"].append(
                f"'{col}': {n_missing} missing -> filled with mode ('{fill_value}')"
            )

    # 4. Outlier detection & capping (IQR method) -----------------------------------
    for col in df.select_dtypes(include=[np.number]).columns:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_outliers = ((df[col] < lower) | (df[col] > upper)).sum()
        if n_outliers == 0:
            continue
        if flag_outliers:
            df[f"{col}_was_outlier"] = ((df[col] < lower) | (df[col] > upper))
        median_val = df[col].median()
        df[col] = df[col].where((df[col] >= lower) & (df[col] <= upper), median_val)
        summary["outliers_fixed"].append(
            f"'{col}': {n_outliers} outlier(s) capped -> replaced with median ({round(median_val, 2)})"
        )

    summary["rows_after"] = len(df)
    return df, summary
