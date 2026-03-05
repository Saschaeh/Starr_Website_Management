"""Restaurants — toggle sidebar list and show dashboard view."""

import importlib
import streamlit as st

# Toggle: if already expanded, collapse and go back to dashboard
if st.session_state.get('_sidebar_restaurants'):
    st.session_state['_sidebar_restaurants'] = False
    st.switch_page("pages/1_Dashboard.py")
else:
    st.session_state['_sidebar_restaurants'] = True

# Prevent double-execution: the import triggers the module body,
# so we guard Dashboard's auto-run() call with this flag.
st.session_state['_importing_dashboard'] = True
_dash = importlib.import_module("pages.1_Dashboard")
st.session_state.pop('_importing_dashboard', None)

_dash.run()
