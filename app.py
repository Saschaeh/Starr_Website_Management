"""Starr Content Hub — Unified CMS for Starr Restaurant Group."""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Forward Streamlit Cloud secrets to env vars (before importing db)
try:
    if hasattr(st, 'secrets'):
        for key in ('TURSO_DB_URL', 'TURSO_AUTH_TOKEN', 'HF_API_TOKEN', 'ANTHROPIC_API_KEY'):
            if key in st.secrets and key not in os.environ:
                os.environ[key] = st.secrets[key]
except Exception:
    pass

from src.db import init_db
from src.ui.theme import inject_css, render_header

# Initialize database on first run
init_db()

# Store HF token in session state for downstream use
hf_token = os.getenv('HF_API_TOKEN', '')
if hf_token and 'hf_api_token' not in st.session_state:
    st.session_state['hf_api_token'] = hf_token

# --- Page Config ---
st.set_page_config(
    page_title="Starr Content Hub",
    page_icon=":fork_and_knife:",
    layout="wide",
)

# --- Inject master CSS ---
inject_css()

# --- Header ---
render_header()

# --- Sidebar title ---
with st.sidebar:
    st.markdown('<div class="sidebar-title-wrapper"><div class="sidebar-title">Management Tools</div></div>', unsafe_allow_html=True)

# --- Navigation ---
dashboard = st.Page("pages/1_Dashboard.py", title="Restaurants", icon=":material/restaurant:", default=True)
batch = st.Page("pages/2_Batch.py", title="Batch Ops", icon=":material/bolt:")

pg = st.navigation([dashboard, batch])
pg.run()
