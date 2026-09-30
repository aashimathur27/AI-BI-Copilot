"""
app.py
------
Main Streamlit entry point for AI BI Copilot.

Run with:  streamlit run app.py
"""

import os
import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database as db
import auth
import cleaning
import charts as ch
import dashboard as dash
import insights as ins
import nlq
import forecasting as fc
import anomaly as an
import report as rpt
import styling

st.set_page_config(page_title="AI BI Copilot", page_icon="📊", layout="wide")
styling.inject_custom_css()
db.init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

SAMPLE_DATASETS = {
    "Superstore": "Superstore_Sample.csv",
    "Amazon Sales": "Amazon_Sales_Sample.csv",
    "Walmart Sales": "Walmart_Sales_Sample.csv",
    "Flipkart Sales": "Flipkart_Sales_Sample.csv",
}


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for key, default in {
    "user": None,
    "raw_df": None,
    "clean_df": None,
    "clean_summary": None,
    "detected_cols": None,
    "auth_mode": "Login",
    "last_upload_signature": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Feature 9 — Authentication screens
# ---------------------------------------------------------------------------
def render_auth_screen():
    styling.render_hero(
        "📊 AI BI Copilot",
        "Automated data cleaning, dashboards, insights, forecasting & anomaly detection.",
    )
    styling.suppress_password_manager_popups()

    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        mode = st.radio("Choose an action", ["Login", "Sign Up", "Forgot Password"], horizontal=True,
                         index=["Login", "Sign Up", "Forgot Password"].index(st.session_state.auth_mode),
                         label_visibility="collapsed")
        st.session_state.auth_mode = mode
        st.write("")

        if mode == "Login":
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                ok, msg, user = auth.login(username, password)
                if ok:
                    st.session_state.user = user
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        elif mode == "Sign Up":
            with st.form("signup_form"):
                username = st.text_input("Choose a username")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                question = st.selectbox(
                    "Security question (used for password recovery)",
                    ["What city were you born in?", "What was your first pet's name?",
                     "What is your favorite book?"],
                )
                answer = st.text_input("Answer")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                ok, msg = auth.signup(username, email, password, question, answer)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.session_state.auth_mode = "Login"

        else:  # Forgot Password
            with st.form("forgot_form"):
                username = st.text_input("Username")
                user_preview = db.get_user_by_username(username) if username else None
                if user_preview:
                    st.info(f"Security question: {user_preview['security_question']}")
                answer = st.text_input("Security answer")
                new_password = st.text_input("New password", type="password")
                submitted = st.form_submit_button("Reset Password", use_container_width=True)
            if submitted:
                ok, msg = auth.reset_password(username, answer, new_password)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.session_state.auth_mode = "Login"


# ---------------------------------------------------------------------------
# Feature 1 — Dataset upload
# ---------------------------------------------------------------------------
def load_dataframe_from_upload(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file, engine="openpyxl")


def render_upload_section():
    st.subheader("1️⃣ Upload Your Dataset")
    tab1, tab2 = st.tabs(["Upload a file", "Use an example dataset"])

    with tab1:
        uploaded_file = st.file_uploader("CSV or Excel file", type=["csv", "xlsx", "xls"])
        if uploaded_file is not None:
            # Streamlit reruns this whole script on every interaction anywhere in the
            # app, and the file_uploader keeps holding the same file across reruns.
            # Without this guard we'd re-save + re-insert a DB record every single
            # rerun (e.g. every time the user typed a question or clicked a button
            # elsewhere), which is why "Your uploaded datasets" showed duplicates.
            upload_signature = (uploaded_file.name, uploaded_file.size)
            if st.session_state.get("last_upload_signature") != upload_signature:
                try:
                    df = load_dataframe_from_upload(uploaded_file)
                    st.session_state.raw_df = df
                    st.session_state.clean_df = None  # reset downstream state
                    # persist a copy + record in DB (per-user reports)
                    save_path = os.path.join(UPLOAD_DIR, f"{st.session_state.user['id']}_{uploaded_file.name}")
                    df.to_csv(save_path, index=False)
                    db.save_report_record(
                        st.session_state.user["id"], save_path, uploaded_file.name, len(df), len(df.columns)
                    )
                    st.session_state.last_upload_signature = upload_signature
                    st.success(f"Loaded '{uploaded_file.name}' — {len(df)} rows × {len(df.columns)} columns.")
                except Exception as e:
                    st.error(f"Could not read file: {e}")

    with tab2:
        choice = st.selectbox("Example datasets", list(SAMPLE_DATASETS.keys()))
        if st.button("Load example dataset"):
            path = os.path.join(SAMPLE_DIR, SAMPLE_DATASETS[choice])
            df = pd.read_csv(path)
            st.session_state.raw_df = df
            st.session_state.clean_df = None
            st.success(f"Loaded example dataset '{choice}' — {len(df)} rows × {len(df.columns)} columns.")

    if st.session_state.raw_df is not None:
        with st.expander("Preview raw data"):
            st.dataframe(st.session_state.raw_df.head(20), use_container_width=True)


# ---------------------------------------------------------------------------
# Feature 2 — Automatic data cleaning
# ---------------------------------------------------------------------------
def render_cleaning_section():
    st.subheader("2️⃣ Automatic Data Cleaning")
    if st.session_state.raw_df is None:
        st.info("Upload or select a dataset above first.")
        return

    if st.session_state.clean_df is None:
        with st.spinner("Cleaning data automatically..."):
            clean_df, summary = cleaning.clean_data(st.session_state.raw_df)
            st.session_state.clean_df = clean_df
            st.session_state.clean_summary = summary
            st.session_state.detected_cols = ch.detect_columns(clean_df)

    summary = st.session_state.clean_summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows before", summary["rows_before"])
    c2.metric("Rows after", summary["rows_after"])
    c3.metric("Duplicates removed", summary["duplicates_removed"])
    c4.metric("Columns fixed", len(summary["dtype_fixes"]))

    with st.expander("See exactly what was fixed"):
        if summary["dtype_fixes"]:
            st.markdown("**✔ Data type fixes**")
            for line in summary["dtype_fixes"]:
                st.write(f"- {line}")
        if summary["missing_value_fixes"]:
            st.markdown("**✔ Missing values filled**")
            for line in summary["missing_value_fixes"]:
                st.write(f"- {line}")
        if summary["outliers_fixed"]:
            st.markdown("**✔ Outliers capped**")
            for line in summary["outliers_fixed"]:
                st.write(f"- {line}")
        if summary["duplicates_removed"]:
            st.markdown(f"**✔ Removed {summary['duplicates_removed']} duplicate row(s)**")

    with st.expander("Preview cleaned data"):
        st.dataframe(st.session_state.clean_df.head(20), use_container_width=True)


# ---------------------------------------------------------------------------
# Feature 3 — Smart dashboard  &  Feature 4 — AI insights
# ---------------------------------------------------------------------------
def render_dashboard_and_insights():
    st.subheader("3️⃣ Smart Dashboard")
    detected = dash.render_dashboard(st.session_state.clean_df)
    st.session_state.detected_cols = detected

    st.subheader("4️⃣ ⭐ AI Insight Generator")
    insights_list = ins.generate_insights(st.session_state.clean_df, detected)
    for insight in insights_list:
        st.markdown(f'<div class="insight-bullet">💡 {insight}</div>', unsafe_allow_html=True)
    st.session_state["_last_insights"] = insights_list


# ---------------------------------------------------------------------------
# Feature 5 — Ask questions
# ---------------------------------------------------------------------------
def render_ask_questions():
    st.subheader("5️⃣ Ask Questions (Natural Language)")
    st.caption("Try: \"Which month had highest sales?\", \"Show me top 5 customers\", "
               "\"What is the total revenue?\", \"Which region performed best?\"")
    question = st.text_input("Ask a question about your data")
    if question:
        result = nlq.answer_question(st.session_state.clean_df, question, st.session_state.detected_cols)
        st.markdown(f"**Answer:** {result['answer']}")
        if result["table"] is not None:
            st.dataframe(result["table"], use_container_width=True)
        if result["chart"] is not None:
            st.plotly_chart(result["chart"], use_container_width=True)


# ---------------------------------------------------------------------------
# Feature 6 — Forecasting
# ---------------------------------------------------------------------------
def render_forecasting():
    st.subheader("6️⃣ Sales Forecasting")
    cols = st.session_state.detected_cols
    date_col, sales_col = cols.get("date"), cols.get("sales")
    if not date_col or not sales_col:
        st.info("Forecasting needs both a date column and a sales column, which weren't detected in this dataset.")
        return

    horizon_label = st.radio("Forecast horizon", ["Next Month", "Next 3 Months", "Next 6 Months"], horizontal=True)
    periods = {"Next Month": 1, "Next 3 Months": 3, "Next 6 Months": 6}[horizon_label]
    method = st.selectbox("Model", ["Linear Regression (fast, always available)", "Prophet (if installed)"])
    method_key = "prophet" if method.startswith("Prophet") else "linear"

    hist, forecast_df = fc.forecast_sales(st.session_state.clean_df, date_col, sales_col, periods, method_key)
    if forecast_df.empty:
        st.warning("Not enough historical data points to build a forecast.")
        return

    fig = ch.forecast_chart(hist, forecast_df, "Month", sales_col)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(forecast_df.rename(columns={sales_col: f"Forecasted {sales_col}"}), use_container_width=True)

    total_forecast = forecast_df[sales_col].sum()
    summary = (f"Forecasted total {sales_col} for the {horizon_label.lower()}: "
               f"₹{total_forecast:,.0f} (using {method_key} regression).")
    st.info(summary)
    st.session_state["_forecast_data"] = (hist, forecast_df)
    st.session_state["_forecast_summary"] = summary


# ---------------------------------------------------------------------------
# Feature 7 — Anomaly detection
# ---------------------------------------------------------------------------
def render_anomaly_detection():
    st.subheader("7️⃣ Anomaly Detection")
    cols = st.session_state.detected_cols
    date_col, sales_col = cols.get("date"), cols.get("sales")
    if not date_col or not sales_col:
        st.info("Anomaly detection needs both a date column and a sales column, which weren't detected in this dataset.")
        return

    method = st.selectbox("Algorithm", ["Isolation Forest", "Z-score"])
    method_key = "isolation_forest" if method == "Isolation Forest" else "zscore"

    daily = an.detect_anomalies(st.session_state.clean_df, date_col, sales_col, method_key)
    n_anomalies = int(daily["is_anomaly"].sum())
    st.metric("Anomalies detected", n_anomalies)

    fig = ch.anomaly_chart(daily, "Day", sales_col, "is_anomaly")
    st.plotly_chart(fig, use_container_width=True)

    if n_anomalies:
        st.dataframe(daily[daily["is_anomaly"]][["Day", sales_col]], use_container_width=True)
    st.session_state["_anomaly_data"] = daily


# ---------------------------------------------------------------------------
# Feature 8 — Report generator
# ---------------------------------------------------------------------------
def render_report_generator():
    st.subheader("8️⃣ One-Click Report Generator")
    if st.button("📄 Generate PDF Report", type="primary"):
        with st.spinner("Building your report..."):
            cols = st.session_state.detected_cols
            kpis = dash.compute_kpis(st.session_state.clean_df, cols)
            insights_list = st.session_state.get("_last_insights") or ins.generate_insights(
                st.session_state.clean_df, cols
            )
            recommendations = _build_recommendations(insights_list)

            figures = {}
            date_col, sales_col = cols.get("date"), cols.get("sales")
            if date_col and sales_col:
                figures["Monthly Sales"] = rpt.chart_monthly_line(
                    st.session_state.clean_df, date_col, sales_col, "Monthly Sales"
                )
            if cols.get("category"):
                figures["Category-wise Revenue"] = rpt.chart_pie_by_group(
                    st.session_state.clean_df, cols.get("category"), sales_col, "Category-wise Revenue"
                )
            if cols.get("region"):
                figures["Region-wise Revenue"] = rpt.chart_bar_by_group(
                    st.session_state.clean_df, cols.get("region"), sales_col, "Region-wise Revenue"
                )
            if cols.get("product"):
                figures["Top Products"] = rpt.chart_bar_by_group(
                    st.session_state.clean_df, cols.get("product"), sales_col, "Top Products",
                    top_n=10, horizontal=True
                )
            if st.session_state.get("_forecast_data"):
                hist, forecast_df = st.session_state["_forecast_data"]
                figures["Forecast"] = rpt.chart_forecast(hist, forecast_df, "Month", sales_col)
            if st.session_state.get("_anomaly_data") is not None:
                daily = st.session_state["_anomaly_data"]
                figures["Anomaly Detection"] = rpt.chart_anomalies(daily, "Day", sales_col, "is_anomaly")

            out_path = os.path.join(
                REPORT_DIR, f"report_{st.session_state.user['id']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            rpt.generate_pdf_report(
                kpis, insights_list, recommendations, figures,
                st.session_state.get("_forecast_summary"), out_path
            )

        with open(out_path, "rb") as f:
            st.download_button("⬇️ Download Report PDF", f, file_name=os.path.basename(out_path),
                                mime="application/pdf", type="primary")
        st.success("Report generated!")


def _build_recommendations(insights_list):
    recs = []
    for text in insights_list:
        low = text.lower()
        if "declining" in low:
            recs.append("Investigate the declining category with targeted promotions or bundle offers.")
        if "highest" in low and "region" in low:
            recs.append("Double down on marketing spend in the top-performing region.")
        if "increased" in low:
            recs.append("Sustain recent growth by replicating what worked in the best-performing month.")
    if not recs:
        recs.append("Continue monitoring KPIs monthly and re-run this analysis as new data arrives.")
    return recs


# ---------------------------------------------------------------------------
# Sidebar — user's past reports (Feature 9: per-user storage)
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 👋 {st.session_state.user['username']}")
        if st.button("Log out", use_container_width=True):
            st.session_state.user = None
            st.session_state.raw_df = None
            st.session_state.clean_df = None
            st.session_state.last_upload_signature = None
            st.rerun()
        st.divider()
        st.markdown("#### 📁 Your uploaded datasets")
        past_reports = db.get_reports_for_user(st.session_state.user["id"])
        # Defensive de-duplication: keep only the most recent record per
        # (original filename, row count) pair, in case older duplicate rows
        # exist in the database from before this was fixed.
        seen = set()
        deduped = []
        for r in past_reports:
            key = (r["original_name"], r["rows"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)

        if not deduped:
            st.caption("No uploads yet.")
        for r in deduped[:10]:
            st.markdown(
                f"""<div class="sidebar-file-card">
                        <div class="sidebar-file-name">📄 {r['original_name']}</div>
                        <div class="sidebar-file-meta">{r['rows']:,} rows • {r['uploaded_at'][:10]}</div>
                    </div>""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Main app flow
# ---------------------------------------------------------------------------
def main():
    if st.session_state.user is None:
        render_auth_screen()
        return

    render_sidebar()
    styling.render_hero(
        "📊 AI BI Copilot",
        f"Welcome back, {st.session_state.user['username']} — let's turn your data into decisions.",
    )

    render_upload_section()
    st.divider()

    if st.session_state.raw_df is not None:
        render_cleaning_section()
        st.divider()

    if st.session_state.clean_df is not None:
        render_dashboard_and_insights()
        st.divider()
        render_ask_questions()
        st.divider()
        render_forecasting()
        st.divider()
        render_anomaly_detection()
        st.divider()
        render_report_generator()


if __name__ == "__main__":
    main()
