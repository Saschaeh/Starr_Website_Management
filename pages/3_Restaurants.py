"""Restaurants — same dashboard view with sidebar restaurant list expanded."""

import importlib
import streamlit as st

# Auto-expand sidebar restaurant list
st.session_state['_sidebar_restaurants'] = True

# Prevent double-execution: the import triggers the module body,
# so we guard Dashboard's auto-run() call with this flag.
st.session_state['_importing_dashboard'] = True
_dash = importlib.import_module("pages.1_Dashboard")
st.session_state.pop('_importing_dashboard', None)

_dash.run()
