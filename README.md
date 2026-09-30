# AI BI Copilot

An AI-powered business intelligence assistant: upload a sales dataset and get
automatic cleaning, dashboards, natural-language insights, forecasting,
anomaly detection, and a one-click PDF report.

## Features

1. **Dataset Upload** — CSV / Excel, or one of four bundled example datasets
   (Superstore, Amazon Sales, Walmart Sales, Flipkart Sales).
2. **Automatic Data Cleaning** — fixes missing values (median/mode), removes
   duplicates, corrects data types, and caps outliers (IQR method) — no
   prompts needed.
3. **Smart Dashboard** — KPI cards (Revenue, Avg Sales, Profit, Orders,
   Customers) + charts (Monthly Sales, Revenue Trend, Top Products,
   Category/Region Revenue, Top Customers).
4. **AI Insight Generator** — rule-based natural-language insights
   ("Sales increased by 22% during November", "Furniture category has
   declining sales", etc.). Swap in an LLM later for more natural phrasing.
5. **Ask Questions (Natural Language)** — template-matched Q&A over your
   data ("Which month had highest sales?", "Show me top 5 customers").
6. **Sales Forecasting** — next 1/3/6 months via Linear Regression
   (Prophet auto-used if installed).
7. **Anomaly Detection** — Isolation Forest or Z-score, visualized in red.
8. **Report Generator** — one-click downloadable PDF with KPIs, insights,
   forecast, recommendations, and charts.
9. **User Authentication** — sign up / login / forgot password, with
   uploaded datasets tracked per user.

## Tech Stack

| Layer          | Technology                     |
|----------------|---------------------------------|
| Frontend       | Streamlit                       |
| Data           | Pandas, openpyxl                |
| Visualization  | Plotly (dashboard), Matplotlib (PDF export) |
| ML             | Scikit-learn (Linear Regression, Isolation Forest) |
| Database       | SQLite (swap for PostgreSQL by editing `database.py`) |
| Auth           | Salted-hash passwords + session state (JWT helpers included in `auth.py` for a future API backend) |
| PDF            | fpdf2                           |

## Getting Started

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Regenerate the bundled example datasets
python generate_sample_data.py

# 4. Run the app
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501), sign up
for an account, and either upload your own CSV/Excel file or load one of the
example datasets from the "Use an example dataset" tab.

## Folder Structure

```
AI-BI-Copilot/
│
├── app.py                  # Main Streamlit entry point / page orchestration
├── auth.py                 # Sign up / login / forgot password + JWT helpers
├── cleaning.py              # Feature 2 — automatic data cleaning
├── charts.py                # Plotly chart builders + column auto-detection
├── dashboard.py             # Feature 3 — KPI cards + dashboard layout
├── insights.py               # Feature 4 — rule-based AI insight generator
├── nlq.py                    # Feature 5 — natural-language Q&A templates
├── forecasting.py            # Feature 6 — sales forecasting
├── anomaly.py                 # Feature 7 — anomaly detection
├── report.py                  # Feature 8 — PDF report generator (matplotlib + fpdf2)
├── database.py                 # SQLite schema + helpers (users, reports)
├── generate_sample_data.py     # Script that builds the bundled example datasets
│
├── models/                     # Reserved for saved ML models (currently trained on the fly)
├── uploads/                    # Per-user uploaded datasets land here
├── reports/                    # Generated PDF reports land here
├── sample_data/                # Bundled Superstore/Amazon/Walmart/Flipkart-style datasets
│
└── requirements.txt
```

## Security Notes (before pushing to GitHub)

- No API keys or secrets are hardcoded anywhere in this project — it's safe
  to push as-is. A `.gitignore` is included that keeps `app_data.db` (the
  local SQLite file — it holds usernames and salted password hashes once you
  start signing up users), `uploads/`, `reports/`, and `__pycache__/` out of
  version control. Run the app locally at least once *before* your first
  `git add .` so those files exist and get correctly ignored rather than
  accidentally staged.
- `auth.py` includes optional JWT helpers (`create_jwt`/`decode_jwt`) for a
  future FastAPI backend — they're unused by the Streamlit app itself (auth
  here runs via session state) and will raise a clear error unless you set an
  `APP_JWT_SECRET` environment variable before calling them. Never hardcode
  that secret in the file; set it via your shell, a `.env` file (already
  git-ignored), or your hosting provider's secrets manager.
- Passwords are stored as salted SHA-256 hashes — fine for an MVP, but swap
  in `bcrypt` or `argon2` (`pip install argon2-cffi`) before using this with
  real user data in production.

## Notes & Next Steps

- **Sample datasets are synthetic** (generated by `generate_sample_data.py`),
  designed to resemble Superstore/Amazon/Walmart/Flipkart-style sales data —
  they intentionally include some missing values, duplicates, and mixed data
  types so Feature 2 has something to fix. Swap in real datasets by dropping
  a CSV into `sample_data/` and adding an entry to `SAMPLE_DATASETS` in `app.py`.
- **Column auto-detection** (`charts.detect_columns`) guesses which column is
  Sales, Date, Category, Region, etc. from common naming patterns. If your
  own dataset uses very different column names, extend `FIELD_KEYWORDS` in
  `charts.py`.
- **Upgrading insights/NLQ to an LLM**: both `insights.py` and `nlq.py` are
  built to be LLM-upgradeable — keep the underlying Pandas calculations
  (they keep the numbers grounded/correct) and simply have an LLM rewrite the
  final sentences, or replace `nlq.answer_question`'s template matching with
  an LLM that generates a small Pandas expression from the question.
- **Auth** currently uses Streamlit session state (appropriate for a
  single-process Streamlit app). `auth.py` also includes JWT helpers, ready
  to reuse if/when you split this into a separate FastAPI backend per the
  original architecture diagram.
- **Database**: SQLite is used for the MVP (`app_data.db`, created
  automatically). To move to PostgreSQL, swap the `sqlite3` calls in
  `database.py` for `psycopg2`/`SQLAlchemy` — the function signatures can
  stay the same.
- **Prophet / ARIMA**: `forecasting.py` defaults to Linear Regression (no
  extra dependencies). If you `pip install prophet`, selecting "Prophet" in
  the UI will automatically use it. ARIMA can be added the same way via
  `statsmodels`.
