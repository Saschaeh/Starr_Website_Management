"""Starr Content Hub — Unified CMS for Starr Restaurant Group."""

import os
import streamlit as st

# Page config MUST be the first Streamlit command
st.set_page_config(
    page_title="Starr Content Hub",
    page_icon=":fork_and_knife:",
    layout="wide",
)

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

# --- Password gate ---
def _get_app_password():
    try:
        return st.secrets["auth"]["password"]
    except Exception:
        return os.environ.get("APP_PASSWORD")

def _check_password():
    if st.session_state.get("authenticated"):
        return True
    expected = _get_app_password()
    if not expected:
        st.error("No app password configured. Add [auth] password to Streamlit secrets or set APP_PASSWORD env var.")
        return False
    with st.container():
        st.markdown("### :lock: Starr Content Hub")
        pwd = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Log in"):
            if pwd == expected:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False

if not _check_password():
    st.stop()

from src.db import init_db
from src.ui.theme import inject_css, render_header

# Initialize database on first run
init_db()

# --- Inject master CSS ---
inject_css()

# --- Header ---
render_header()

# --- Navigation ---
welcome = st.Page("pages/0_Welcome.py", title="Welcome", icon=":material/home:", default=True)
dashboard = st.Page("pages/1_Dashboard.py", title="Dashboard", icon=":material/bar_chart:")
batch = st.Page("pages/2_Batch.py", title="Batch Ops", icon=":material/bolt:")

# Arrow toggles based on whether restaurant list is expanded
_expanded = st.session_state.get('_sidebar_restaurants', False)
_arrow_icon = ":material/expand_more:" if _expanded else ":material/chevron_right:"
restaurants = st.Page("pages/3_Restaurants.py", title="Restaurants", icon=_arrow_icon)

pg = st.navigation([welcome, dashboard, batch, restaurants])

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
                st.switch_page("pages/3_Restaurants.py")

pg.run()
