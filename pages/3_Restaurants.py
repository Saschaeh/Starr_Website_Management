"""Restaurants — same dashboard view with sidebar restaurant list expanded."""

import importlib
import streamlit as st

# Auto-expand sidebar restaurant list
st.session_state['_sidebar_restaurants'] = True

# Reuse the dashboard logic (can't import directly due to numeric prefix)
_dash = importlib.import_module("pages.1_Dashboard")
_dash.run()
