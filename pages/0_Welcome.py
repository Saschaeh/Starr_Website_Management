"""Welcome — Landing page for Starr Content Hub."""

import streamlit as st
from src.db import get_all_restaurants, list_menus, get_images_for_restaurant, get_copy_for_restaurant

# --- Gather live stats ---
restaurants = get_all_restaurants()
n_restaurants = len(restaurants)
n_menus = len(list_menus())
n_images = sum(len(get_images_for_restaurant(r['name'])) for r in restaurants)
n_copy = sum(1 for r in restaurants if get_copy_for_restaurant(r['name']))
n_booking = sum(1 for r in restaurants if r.get('opentable_rid') or r.get('resy_url'))
n_tripleseat = sum(1 for r in restaurants if r.get('tripleseat_form_id'))
n_onetrust = sum(1 for r in restaurants if r.get('onetrust_id'))

# Hide the top Starr header on the Welcome page to avoid double header
st.markdown("""<style>.starr-header { display: none !important; }</style>""", unsafe_allow_html=True)

# --- Hero ---
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #031E41 0%, #0A3366 60%, #122B4F 100%);
    border-radius: 12px;
    padding: 3rem 2.5rem 2.5rem;
    margin-bottom: 2rem;
    border: 1px solid rgba(197,162,88,0.3);
    position: relative;
    overflow: hidden;
">
    <div style="
        position: absolute; top: 0; right: 0; width: 200px; height: 200px;
        background: radial-gradient(circle, rgba(197,162,88,0.08) 0%, transparent 70%);
    "></div>
    <div style="
        font-family: 'DM Sans', sans-serif;
        color: #C5A258;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    ">Content Management Platform</div>
    <div style="
        font-family: 'Playfair Display', Georgia, serif;
        color: #FFFFFF;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    ">Starr Content Hub</div>
    <div style="
        font-family: 'DM Sans', sans-serif;
        color: rgba(255,255,255,0.7);
        font-size: 1rem;
        line-height: 1.6;
        max-width: 640px;
    ">
        Your central platform for managing website content, images, menus,
        and brand assets across the entire Starr Restaurant Group portfolio.
    </div>
</div>
""", unsafe_allow_html=True)

# --- Live Stats ---
st.markdown("""
<div style="
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #6B7280;
    margin-bottom: 0.75rem;
">Portfolio at a Glance</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
_stat_style = """
<div style="
    background: #FFFFFF;
    border: 1px solid #E8E5DE;
    border-radius: 10px;
    padding: 1.25rem 1rem;
    text-align: center;
">
    <div style="font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 700; color: #031E41;">{value}</div>
    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.78rem; color: #6B7280; margin-top: 0.25rem;">{label}</div>
</div>
"""
with c1:
    st.markdown(_stat_style.format(value=n_restaurants, label="Restaurants"), unsafe_allow_html=True)
with c2:
    st.markdown(_stat_style.format(value=n_menus, label="Menus Processed"), unsafe_allow_html=True)
with c3:
    st.markdown(_stat_style.format(value=n_images, label="Images Managed"), unsafe_allow_html=True)
with c4:
    st.markdown(_stat_style.format(value=n_copy, label="Copy Sets"), unsafe_allow_html=True)

st.markdown("<div style='height: 0.75rem'></div>", unsafe_allow_html=True)

c5, c6, c7, _sp = st.columns(4)
with c5:
    st.markdown(_stat_style.format(value=n_booking, label="Booking IDs"), unsafe_allow_html=True)
with c6:
    st.markdown(_stat_style.format(value=n_tripleseat, label="Tripleseat IDs"), unsafe_allow_html=True)
with c7:
    st.markdown(_stat_style.format(value=n_onetrust, label="OneTrust IDs"), unsafe_allow_html=True)

st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

# --- What This Platform Does ---
st.markdown("""
<div style="
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #6B7280;
    margin-bottom: 0.75rem;
">What This Platform Does</div>
""", unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)

_feature_card = """
<div style="
    background: #FFFFFF;
    border: 1px solid #E8E5DE;
    border-radius: 10px;
    padding: 1.5rem;
    height: 100%;
">
    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
    <div style="font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 0.95rem; color: #031E41; margin-bottom: 0.5rem;">
        {title}
    </div>
    <div style="font-family: 'DM Sans', sans-serif; font-size: 0.82rem; color: #6B7280; line-height: 1.6;">
        {desc}
    </div>
</div>
"""

with f1:
    st.markdown(_feature_card.format(
        icon="&#128444;",
        title="Image Pipeline",
        desc="Upload once, automatically resize to every format your websites need. "
             "Consistent file naming conventions across all restaurants. "
             "Brand-aware processing — automatic B&W conversion for chef photos."
    ), unsafe_allow_html=True)

with f2:
    st.markdown(_feature_card.format(
        icon="&#128221;",
        title="Website Copy",
        desc="Generate on-brand website copy and SEO meta tags in seconds. "
             "Pulls context from your live site, follows your brand voice guidelines, "
             "and produces publish-ready content for every restaurant."
    ), unsafe_allow_html=True)

with f3:
    st.markdown(_feature_card.format(
        icon="&#127860;",
        title="Menu Management",
        desc="Convert Word document menus into structured, website-ready HTML. "
             "Handles multi-section layouts, dietary markers, and price formatting "
             "across your entire portfolio."
    ), unsafe_allow_html=True)

st.markdown("<div style='height: 1.5rem'></div>", unsafe_allow_html=True)

# --- More features ---
f4, f5 = st.columns(2)

with f4:
    st.markdown(_feature_card.format(
        icon="&#9855;",
        title="ADA Compliance",
        desc="Every image gets a descriptive alt tag for screen readers. "
             "Standardised file naming ensures consistency across all restaurants. "
             "Stay compliant with accessibility requirements without the manual work."
    ), unsafe_allow_html=True)

with f5:
    st.markdown(_feature_card.format(
        icon="&#9889;",
        title="Batch Operations",
        desc="Run bulk actions across your entire portfolio — export all images, "
             "regenerate copy, audit content completeness. "
             "What used to take days now takes minutes."
    ), unsafe_allow_html=True)

st.markdown("<div style='height: 2rem'></div>", unsafe_allow_html=True)

# --- Built For You ---
st.markdown("""
<div style="
    background: linear-gradient(135deg, #FAFAF7 0%, #F2F0EB 100%);
    border: 1px solid #E8E5DE;
    border-radius: 10px;
    padding: 1.5rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
">
    <div>
        <div style="font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 0.95rem; color: #031E41; margin-bottom: 0.35rem;">
            Built for Starr Restaurant Group
        </div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 0.82rem; color: #6B7280; line-height: 1.6;">
            This platform was designed and developed specifically for your team
            by <strong style="color: #031E41;">Made{<em>Tooled</em>}</strong> — purpose-built to fit your
            workflows, your brand standards, and your scale.
        </div>
    </div>
    <div style="
        font-family: 'DM Sans', sans-serif;
        color: #C5A258;
        font-style: italic;
        font-size: 1.1rem;
        white-space: nowrap;
        letter-spacing: 0.5px;
    ">Made{<em>Tooled</em>}</div>
</div>
""", unsafe_allow_html=True)
