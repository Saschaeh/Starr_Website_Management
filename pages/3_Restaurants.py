"""Restaurants — browse and manage individual restaurants."""

import importlib
import streamlit as st

# Toggle: if already on this page with list expanded, collapse and go to Progress
if st.session_state.get('_on_restaurants_page'):
    st.session_state['_sidebar_restaurants'] = False
    st.session_state['_on_restaurants_page'] = False
    st.switch_page("pages/1_Dashboard.py")

# Mark that we're on this page and expand the list
st.session_state['_sidebar_restaurants'] = True
st.session_state['_on_restaurants_page'] = True

# If a restaurant is selected, show its detail view
_selected = st.session_state.get('selected_restaurant')

if _selected:
    # Import dashboard module for the detail view
    st.session_state['_importing_dashboard'] = True
    _dash = importlib.import_module("pages.1_Dashboard")
    st.session_state.pop('_importing_dashboard', None)

    from src.db import get_restaurant
    if get_restaurant(_selected):
        _dash._show_detail_view(_selected)
    else:
        st.session_state.pop('selected_restaurant', None)
        st.rerun()
else:
    # No restaurant selected — prompt
    st.markdown("""
    <div style="
        text-align: center;
        padding: 4rem 2rem;
        color: #6B7280;
        font-family: 'DM Sans', sans-serif;
    ">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">&#127860;</div>
        <div style="font-size: 1.1rem; font-weight: 500; color: #031E41; margin-bottom: 0.5rem;">
            Select a Restaurant
        </div>
        <div style="font-size: 0.85rem;">
            Choose a restaurant from the sidebar to view and manage its content.
        </div>
    </div>
    """, unsafe_allow_html=True)
