"""
generate_sample_data.py
------------------------
One-off script that creates small, synthetic example datasets
(Superstore, Amazon Sales, Walmart Sales, Flipkart Sales style) under
sample_data/, so Feature 1 ("Example datasets") works out of the box
without requiring the user to source real copyrighted datasets.

Run once: `python generate_sample_data.py`
"""

import numpy as np
import pandas as pd
import os

np.random.seed(42)
OUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(OUT_DIR, exist_ok=True)

N = 600
dates = pd.date_range("2023-01-01", "2024-12-31", periods=N)

categories = ["Furniture", "Technology", "Office Supplies"]
regions = ["North", "South", "East", "West"]
products = {
    "Furniture": ["Office Chair", "Bookshelf", "Desk", "Sofa"],
    "Technology": ["Laptop", "Printer", "Monitor", "Router"],
    "Office Supplies": ["Paper", "Stapler", "Pen Pack", "Binder"],
}
customers = [f"Customer {i}" for i in range(1, 61)]


def build_dataset(name, price_range, profit_margin_range, seasonal_boost_month=None):
    cat_choice = np.random.choice(categories, N)
    rows = []
    for i in range(N):
        cat = cat_choice[i]
        product = np.random.choice(products[cat])
        region = np.random.choice(regions)
        customer = np.random.choice(customers)
        date = dates[i]
        base_sales = np.random.uniform(*price_range)
        qty = np.random.randint(1, 8)
        sales = round(base_sales * qty, 2)

        # seasonal boost
        if seasonal_boost_month and date.month == seasonal_boost_month:
            sales *= np.random.uniform(1.3, 1.8)

        # inject occasional anomaly spike
        if np.random.rand() < 0.01:
            sales *= np.random.uniform(5, 9)

        profit = round(sales * np.random.uniform(*profit_margin_range), 2)

        rows.append({
            "Order ID": f"{name[:3].upper()}-{10000+i}",
            "Order Date": date.strftime("%Y-%m-%d"),
            "Customer Name": customer,
            "Category": cat,
            "Product Name": product,
            "Region": region,
            "Quantity": qty,
            "Sales": round(sales, 2),
            "Profit": profit,
        })

    df = pd.DataFrame(rows)

    # inject some missing values, duplicates, and bad dtypes to showcase Feature 2
    missing_idx = np.random.choice(df.index, size=int(N * 0.03), replace=False)
    df.loc[missing_idx, "Sales"] = np.nan
    df = pd.concat([df, df.sample(5, random_state=1)], ignore_index=True)  # duplicates
    df["Sales"] = df["Sales"].astype(object)
    dtype_idx = np.random.choice(df.index, size=10, replace=False)
    df.loc[dtype_idx, "Sales"] = df.loc[dtype_idx, "Sales"].astype(str) + ",00"

    return df


datasets = {
    "Superstore_Sample.csv": build_dataset("Superstore", (50, 900), (0.05, 0.25), seasonal_boost_month=11),
    "Amazon_Sales_Sample.csv": build_dataset("Amazon", (20, 500), (0.03, 0.20), seasonal_boost_month=12),
    "Walmart_Sales_Sample.csv": build_dataset("Walmart", (30, 700), (0.04, 0.18), seasonal_boost_month=10),
    "Flipkart_Sales_Sample.csv": build_dataset("Flipkart", (15, 450), (0.02, 0.22), seasonal_boost_month=12),
}

for filename, df in datasets.items():
    df.to_csv(os.path.join(OUT_DIR, filename), index=False)
    print(f"Created {filename} ({len(df)} rows)")

print("\nAll sample datasets generated in sample_data/")
