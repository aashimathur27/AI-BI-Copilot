"""
styling.py
----------
Visual polish for the Streamlit app: a custom CSS theme (cards, gradients,
typography) plus a small JS snippet that stops browsers from popping up
"suggest a strong password" / "save password?" prompts on the login and
sign-up forms.

Why the password popup happens
-------------------------------
Chrome/Edge/Firefox show the "suggest a strong password" bubble when they
detect a password field they believe belongs to an *account-creation* form.
Setting `autocomplete="current-password"` on the field (instead of leaving
it unset, which defaults to a "new password" heuristic) tells the browser
"this is a field for entering an *existing* password", which suppresses
the suggestion — this is the standard, widely-used workaround, since browsers
intentionally ignore `autocomplete="off"` on password fields for security UX
reasons. We also add `data-lpignore`/`data-1p-ignore`/`data-bwignore` to quiet
LastPass/1Password/Bitwarden's own icons for the same reason.

Streamlit doesn't expose raw `<input>` attributes, so we inject a small
script (via an embedded iframe that reaches into the parent document) that
finds every password field and patches its attributes — re-run automatically
whenever Streamlit redraws the DOM.
"""

import streamlit as st
import streamlit.components.v1 as components


def suppress_password_manager_popups():
    """Call this once on the auth screen to stop 'strong password' prompts."""
    components.html(
        """
        <script>
        function patchPasswordFields() {
            try {
                const doc = window.parent.document;
                const inputs = doc.querySelectorAll('input[type="password"]');
                inputs.forEach(function (el) {
                    el.setAttribute('autocomplete', 'current-password');
                    el.setAttribute('data-lpignore', 'true');
                    el.setAttribute('data-1p-ignore', 'true');
                    el.setAttribute('data-bwignore', 'true');
                    el.setAttribute('data-form-type', 'other');
                });
            } catch (e) { /* no-op if the parent DOM isn't reachable yet */ }
        }
        patchPasswordFields();
        try {
            const target = window.parent.document.body;
            const observer = new MutationObserver(patchPasswordFields);
            observer.observe(target, { childList: true, subtree: true });
        } catch (e) {}
        </script>
        """,
        height=0,
        width=0,
    )


CUSTOM_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}
h1, h2, h3, .app-hero-title {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
    letter-spacing: -0.01em;
}

/* ---- App background ---- */
.stApp {
    background: linear-gradient(180deg, #F6F7FD 0%, #FFFFFF 320px);
}

/* ---- Hero banner ---- */
.app-hero {
    background: linear-gradient(120deg, #6C5CE7 0%, #8E7BFF 55%, #63C7FF 100%);
    border-radius: 18px;
    padding: 28px 32px;
    margin-bottom: 22px;
    box-shadow: 0 10px 30px rgba(108, 92, 231, 0.25);
}
.app-hero-title {
    color: white;
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
}
.app-hero-subtitle {
    color: rgba(255,255,255,0.9);
    font-size: 0.95rem;
    margin-top: 6px;
}

/* ---- Section headers (st.subheader) ---- */
h2, h3 {
    color: #2D2A45 !important;
}
h3::before {
    content: "";
}

/* ---- Metric / KPI cards ---- */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #ECEAFB;
    border-top: 4px solid #6C5CE7;
    border-radius: 14px;
    padding: 14px 16px 10px 16px;
    box-shadow: 0 4px 14px rgba(108, 92, 231, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 22px rgba(108, 92, 231, 0.15);
}
div[data-testid="stMetricValue"] {
    color: #2D2A45;
    font-weight: 700;
}
div[data-testid="stMetricLabel"] {
    color: #7A7593;
}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button,
div[data-testid="stFormSubmitButton"] button,
button[data-testid^="stBaseButton"] {
    border-radius: 10px;
    border: none;
    background: linear-gradient(120deg, #6C5CE7, #8E7BFF);
    color: white;
    font-weight: 600;
    padding: 0.55rem 1.1rem;
    box-shadow: 0 4px 12px rgba(108, 92, 231, 0.25);
    transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover,
div[data-testid="stFormSubmitButton"] button:hover,
button[data-testid^="stBaseButton"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(108, 92, 231, 0.35);
    color: white;
}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #F1EFFB;
    border-radius: 10px 10px 0 0;
    padding: 8px 18px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background-color: #6C5CE7 !important;
    color: white !important;
}

/* ---- Expanders ---- */
details {
    border: 1px solid #ECEAFB !important;
    border-radius: 10px !important;
    background: #FCFCFF;
}

/* ---- Dataframes ---- */
div[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #ECEAFB;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2D2A45 0%, #423E68 100%);
}
section[data-testid="stSidebar"] * {
    color: #F1EFFB !important;
}
.sidebar-file-card {
    background: rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 8px;
    border-left: 3px solid #8E7BFF;
}
.sidebar-file-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: #FFFFFF !important;
}
.sidebar-file-meta {
    font-size: 0.75rem;
    color: #C6C2E8 !important;
}

/* ---- Auth screen card ---- */
.auth-card-wrapper {
    max-width: 460px;
    margin: 0 auto;
}

/* ---- Insight bullets ---- */
.insight-bullet {
    background: #F8F7FF;
    border-left: 4px solid #6C5CE7;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    color: #2D2A45;
}

/* ---- Radio (auth mode switch) ---- */
div[role="radiogroup"] {
    gap: 10px;
}
</style>
"""


def inject_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str):
    st.markdown(
        f"""<div class="app-hero">
                <p class="app-hero-title">{title}</p>
                <p class="app-hero-subtitle">{subtitle}</p>
            </div>""",
        unsafe_allow_html=True,
    )
