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

# --- Navigation ---
dashboard = st.Page("pages/1_Dashboard.py", title="Progress", icon=":material/bar_chart:", default=True)
restaurants = st.Page("pages/3_Restaurants.py", title="Restaurants", icon=":material/restaurant:")
batch = st.Page("pages/2_Batch.py", title="Batch Ops", icon=":material/bolt:")

pg = st.navigation([dashboard, restaurants, batch])

# --- Sidebar: Restaurant sub-list when expanded ---
from src.db import get_all_restaurants
from src.restaurant_registry import display_name

if st.session_state.get('_sidebar_restaurants'):
    with st.sidebar:
        for r in get_all_restaurants():
            name = r['name']
            dname = r.get('display_name') or display_name(name)
            if st.button(dname, key=f"sidebar_{name}"):
                st.session_state['selected_restaurant'] = name
                st.rerun()

pg.run()
