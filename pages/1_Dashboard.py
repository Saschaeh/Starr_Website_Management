"""Restaurants — Kinsta-style list view + detail view with tabs."""

import io
import json
import os
import time
import zipfile
from datetime import datetime

import streamlit as st
st.session_state.pop('_on_restaurants_page', None)
import streamlit.components.v1 as components
from PIL import Image

from src import db
from src.restaurant_registry import (
    display_name, get_city, city_from_address, CITY_ORDER,
    detect_restaurant, ensure_restaurant, normalize_to_slug,
)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _pill_html(label, done, total):
    if done >= total:
        bg, fg = "#DCFCE7", "#166534"
    elif done > 0:
        bg, fg = "#FEF3C7", "#92400E"
    else:
        bg, fg = "#F3F4F6", "#9CA3AF"
    return (f'<span style="display:inline-block;padding:2px 8px;border-radius:10px;'
            f'font-size:0.7rem;font-weight:600;background:{bg};color:{fg};'
            f'margin-right:4px;">{label} {done}/{total}</span>')


def _dot(color):
    return (f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{color};margin-right:6px;vertical-align:middle;"></span>')


def _fmt_date(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d")
    except Exception:
        return ""


# Staging URL mapping (slug -> kinsta subdomain)
_STAGING_URLS = {
    "makoto": "stg-makoto",
    "lecafe-menu": "stg-lecafelouisvuitton",
    "slims": "stg-slims",
    "upland": "stg-upland",
    "babbo": "stg-babbo",
    "barclay-prime": "stg-barclayprime",
    "borromini-new": "stg-borromini",
    "buddakan-nyc": "stg-buddakannewyor",
    "buddakan-pa": "stg-buddakanphiladelphia",
    "butcher-and-singer": "stg-butcherandsinger",
    "the-continental-mid-town": "stg-continentalmidtown",
    "el-presidente": "stg-elpresidente",
    "el-rey": "stg-elreyd",
    "el-vez-ft-lauderdale": "stg-elvezftlauderdale",
    "el-vez-nyc": "stg-elveznewyork",
    "el-vez-philadelphia": "stg-elvezphiladelphia",
    "electric-lemon": "stg-electriclemon",
    "fette-sau": "stg-fettesau",
    "frankford-hall": "stg-frankfordhall",
    "le-coucou": "stg-lecoucou",
    "le-diplomate": "stg-lediplomate",
    "lmno": "stg-lmnophilly",
    "morimoto": "stg-morimotophiladelphia",
    "osteria-mozza": "stg-osteriamozza",
    "parc": "stg-parcrestaurant",
    "pastis-nyc": "stg-pastisnewyork",
    "pastis-dc": "stg-pastisdc",
    "pastis-miami": "stg-pastismiami",
    "pastis-nashville": "stg-pastisnashville",
    "pizzeria-stella": "stg-pizzeriastella",
    "st-anselm": "stg-stanselm",
    "steak-954": "stg-steak954",
    "talulas-garden": "stg-talulasgarden",
    "talulas-daily": "stg-talulasdaily",
    "the-clocktower": "stg-theclocktower",
    "the-dandelion": "stg-thedandelion",
    "the-love": "stg-thelove",
    "the-occidental": "stg-theoccidental",
}

def _staging_url(slug):
    sub = _STAGING_URLS.get(slug)
    if sub:
        return f"https://{sub}-staging.kinsta.cloud"
    return ""

# ═══════════════════════════════════════════════════════════════════════════
# LIST VIEW — Full-width restaurant table (Kinsta-style)
# ═══════════════════════════════════════════════════════════════════════════

def _show_list_view():
    restaurants = db.get_all_restaurants()
    menus_list = db.list_menus()
    menu_slugs = {m['restaurant'] for m in menus_list}
    menu_dates = {m['restaurant']: m.get('updated_at', '') for m in menus_list}

    # Pre-compute progress using bulk queries (2 DB calls instead of 76+)
    img_counts, chef_counts = db.get_all_image_counts()
    copy_counts = db.get_all_copy_counts()
    brand_ok = {}
    ids_ok = {}
    links_ok = {}
    contact_ok = {}
    for r in restaurants:
        s = r['name']
        brand_ok[s] = bool(r.get('primary_color'))
        # IDs: must have booking platform ID (OT or Resy) AND tripleseat
        has_booking = bool(r.get('opentable_rid') or r.get('resy_url'))
        has_tripleseat = bool(r.get('tripleseat_form_id'))
        ids_ok[s] = has_booking and has_tripleseat
        # Links: any link set
        links_ok[s] = bool(r.get('mailing_list_url') or r.get('order_online_url')
                           or r.get('facebook_url') or r.get('instagram_url'))
        # Contact: any contact info set
        contact_ok[s] = bool(r.get('phone') or r.get('address') or r.get('email_general'))

    def _is_complete(s):
        return (s in menu_slugs
                and img_counts.get(s, 0) >= 9
                and copy_counts.get(s, 0) >= 5
                and brand_ok.get(s)
                and ids_ok.get(s)
                and links_ok.get(s)
                and contact_ok.get(s))

    total = len(restaurants)
    complete = sum(1 for r in restaurants if _is_complete(r['name']))

    # --- Header row ---
    hc1, hc2 = st.columns([3, 1])
    with hc1:
        st.markdown('<h1 style="font-family:\'Playfair Display\',serif;font-size:2rem;'
                    'font-weight:600;margin:0;padding:0;">Restaurants</h1>',
                    unsafe_allow_html=True)
    with hc2:
        pct = int((complete / total) * 100) if total else 0
        st.markdown(
            f'<div style="text-align:right;padding-top:0.5rem;">'
            f'<span style="font-size:0.85rem;font-weight:600;color:#1A1A2E;">'
            f'{complete} / {total} complete</span>'
            f'<div style="margin-top:4px;height:4px;background:#E5E7EB;border-radius:2px;">'
            f'<div style="width:{pct}%;height:100%;background:#22C55E;border-radius:2px;'
            f'transition:width 0.3s;"></div></div></div>',
            unsafe_allow_html=True)

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # --- Search + Filters + Actions row ---
    # Filter group                          gap    Manage group
    fc1, fc2, fc3, _gap, fc4, fc5, fc6 = st.columns(
        [2, 0.9, 0.9, 0.4, 0.7, 0.7, 0.7], vertical_alignment="bottom")
    with fc1:
        search = st.text_input("Search", placeholder="Search restaurants...",
                               label_visibility="collapsed", key="ls")
    with fc2:
        city_opts = ["All Cities"] + CITY_ORDER
        extras = sorted(set(r.get('city', '') for r in restaurants) - set(CITY_ORDER) - {''})
        if extras:
            city_opts += extras
        city_filter = st.selectbox("City", city_opts, label_visibility="collapsed", key="lc")
    with fc3:
        status_opts = ["All Status", "Complete", "In Progress", "Not Started"]
        status_filter = st.selectbox("Status", status_opts, label_visibility="collapsed",
                                     key="lf")
    with fc4:
        edit_clicked = st.button("Edit", key="edit_btn")
    with fc5:
        delete_clicked = st.button("Delete", key="del_btn")
    with fc6:
        if st.button("+ Add Restaurant", key="add_btn"):
            st.session_state['show_add_form'] = True
            st.rerun()

    # --- Filter ---
    filtered = restaurants
    if search:
        q = search.lower()
        filtered = [r for r in filtered
                    if q in (r.get('display_name') or '').lower() or q in r['name']]
    if city_filter != "All Cities":
        filtered = [r for r in filtered if (r.get('city') or get_city(r['name'])) == city_filter]
    if status_filter == "Complete":
        filtered = [r for r in filtered if _is_complete(r['name'])]
    elif status_filter == "In Progress":
        filtered = [r for r in filtered if not _is_complete(r['name'])]
    elif status_filter == "Not Started":
        filtered = [r for r in filtered
                    if r['name'] not in menu_slugs
                    and img_counts.get(r['name'], 0) == 0
                    and copy_counts.get(r['name'], 0) == 0
                    and not brand_ok.get(r['name'])
                    and not ids_ok.get(r['name'])
                    and not links_ok.get(r['name'])
                    and not contact_ok.get(r['name'])]

    # --- Table header ---
    _hdr = '<span style="font-size:0.7rem;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:0.08em;">'
    _COL_W = [0.3, 2.0, 0.6, 0.7, 0.5, 0.6, 0.55, 0.5, 0.5, 0.6, 0.5]
    _COL_LABELS = ["", "Name", "Menu", "Images", "Chef", "Copy", "Brand", "IDs", "Links", "Contact", "Synced"]
    cols_h = st.columns(_COL_W)
    for col, label in zip(cols_h, _COL_LABELS):
        with col:
            if label:
                st.markdown(f'{_hdr}{label}</span>', unsafe_allow_html=True)

    st.markdown('<hr style="margin:0 0 4px 0;border:none;border-top:2px solid #E5E7EB;">',
                unsafe_allow_html=True)

    _check = '<span style="color:#22C55E;font-weight:700;">&#10003;</span>'
    _dash = '<span style="color:#D1D5DB;">—</span>'
    _x_red = '<span style="color:#EF4444;font-weight:700;">&#10005;</span>'
    _x_orange = '<span style="color:#F59E0B;font-weight:700;">&#10005;</span>'
    _sync_live = '<span style="color:#22C55E;font-size:0.85rem;" title="Live">&#128077;</span>'
    _sync_pending = '<span style="color:#94A3B8;font-size:0.85rem;" title="Not synced">&#9203;</span>'

    # --- Restaurant rows ---
    if not filtered:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#9CA3AF;font-size:0.9rem;">'
            'No restaurants match your filters.</div>', unsafe_allow_html=True)
    else:
        for r in filtered:
            slug = r['name']
            dname = r.get('display_name') or display_name(slug)
            has_menu = slug in menu_slugs
            ic = img_counts.get(slug, 0)
            chc = chef_counts.get(slug, 0)
            cc = copy_counts.get(slug, 0)

            cols = st.columns(_COL_W)
            # Checkbox
            with cols[0]:
                st.checkbox(dname, key=f"sel_{slug}", label_visibility="collapsed")
            # Name + website link
            with cols[1]:
                wurl = r.get('website_url', '')
                nc1, nc2 = st.columns([4, 1])
                with nc1:
                    if st.button(f"{dname}", key=f"row_{slug}"):
                        st.session_state['selected_restaurant'] = slug
                        st.rerun()
                with nc2:
                    stg_url = _staging_url(slug)
                    if stg_url:
                        st.markdown(f'<a href="{stg_url}" target="_blank" style="font-size:0.75rem;color:#6B7280;text-decoration:none;">&#128279;</a>', unsafe_allow_html=True)
            # Menu
            with cols[2]:
                if has_menu:
                    st.markdown(_check, unsafe_allow_html=True)
                else:
                    st.markdown(_x_red, unsafe_allow_html=True)
            # Images (x/9)
            with cols[3]:
                if ic > 0:
                    st.markdown(_pill_html("", ic, 9), unsafe_allow_html=True)
                else:
                    st.markdown(_dash, unsafe_allow_html=True)
            # Chef (x/3)
            with cols[4]:
                if chc > 0:
                    st.markdown(_pill_html("", chc, 3), unsafe_allow_html=True)
                else:
                    st.markdown(_dash, unsafe_allow_html=True)
            # Copy
            with cols[5]:
                if cc > 0:
                    st.markdown(_pill_html("", cc, 5), unsafe_allow_html=True)
                else:
                    st.markdown(_dash, unsafe_allow_html=True)
            # Brand
            with cols[6]:
                st.markdown(_check if brand_ok.get(slug) else _dash,
                            unsafe_allow_html=True)
            # IDs
            with cols[7]:
                st.markdown(_check if ids_ok.get(slug) else _x_red,
                            unsafe_allow_html=True)
            # Links
            with cols[8]:
                st.markdown(_check if links_ok.get(slug) else _x_orange,
                            unsafe_allow_html=True)
            # Contact
            with cols[9]:
                st.markdown(_check if contact_ok.get(slug) else _x_orange,
                            unsafe_allow_html=True)
            # Synced
            with cols[10]:
                st.markdown(_sync_live if r.get('pull_data') else _sync_pending,
                            unsafe_allow_html=True)

    # --- Handle Edit / Delete actions ---
    selected_slugs = [r['name'] for r in filtered
                      if st.session_state.get(f"sel_{r['name']}")]
    if edit_clicked:
        if selected_slugs:
            st.session_state['selected_restaurant'] = selected_slugs[0]
            st.rerun()
        else:
            st.toast("Select a restaurant first.")
    if delete_clicked:
        if not selected_slugs:
            st.toast("Select restaurant(s) to delete.")
        elif not st.session_state.get('_confirm_delete'):
            st.session_state['_confirm_delete'] = True
            st.rerun()

    if st.session_state.get('_confirm_delete') and selected_slugs:
        names = ", ".join(display_name(s) for s in selected_slugs)
        st.warning(f"Delete **{len(selected_slugs)}** restaurant(s): {names}?")
        cd1, cd2, _ = st.columns([1, 1, 4])
        with cd1:
            if st.button("Confirm Delete", key="confirm_del", type="primary"):
                for s in selected_slugs:
                    db.delete_restaurant(s)
                st.session_state['_confirm_delete'] = False
                st.rerun()
        with cd2:
            if st.button("Cancel", key="cancel_del"):
                st.session_state['_confirm_delete'] = False
                st.rerun()



# ═══════════════════════════════════════════════════════════════════════════
# ADD FORM
# ═══════════════════════════════════════════════════════════════════════════

def _show_add_form():
    # Back button
    if st.button("< Back to Restaurants", key="add_back"):
        st.session_state.pop('show_add_form', None)
        st.switch_page("pages/1_Dashboard.py")

    st.markdown('<h1 style="font-family:\'Playfair Display\',serif;font-size:1.75rem;'
                'font-weight:600;">Add New Restaurant</h1>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input("Restaurant Name", placeholder="e.g. Barclay Prime",
                                 key="add_name")
    with c2:
        new_url = st.text_input("Website URL", placeholder="https://barclayprime.com",
                                key="add_url")
    a1, a2 = st.columns([1, 3])
    with a1:
        if st.button("Add Restaurant", type="primary", disabled=not (new_name or '').strip(),
                     key="add_submit"):
            slug = normalize_to_slug(new_name.strip())
            if db.get_restaurant(slug):
                st.warning(f"'{new_name}' already exists.")
            else:
                dn = display_name(new_name.strip())
                db.add_restaurant(slug, dn, website_url=(new_url or '').strip())
                st.success(f"Added **{dn}**!")
                st.session_state['selected_restaurant'] = slug
                st.session_state.pop('show_add_form', None)
                st.rerun()
    with a2:
        if st.button("Cancel", key="add_cancel"):
            st.session_state.pop('show_add_form', None)
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# DETAIL VIEW — Restaurant detail with tabs
# ═══════════════════════════════════════════════════════════════════════════

def _show_detail_view(slug):
    r_data = db.get_restaurant(slug)
    if not r_data:
        st.session_state.pop('selected_restaurant', None)
        st.rerun()
        return

    dname = r_data.get('display_name') or display_name(slug)
    city = r_data.get('city') or get_city(slug)

    menus_list = db.list_menus()
    menu_slugs = {m['restaurant'] for m in menus_list}

    # Back button
    if st.button("< Back to Restaurants", key="detail_back"):
        st.session_state.pop('selected_restaurant', None)
        st.switch_page("pages/1_Dashboard.py")

    # Restaurant header
    hc1, hc2 = st.columns([3, 1])
    with hc1:
        stg_url = _staging_url(slug)
        link_html = f' <a href="{stg_url}" target="_blank" style="font-size:0.85rem;color:#6B7280;text-decoration:none;font-weight:400;">&#128279;</a>' if stg_url else ''
'
        st.markdown(
            f'<h1 style="font-family:\'Playfair Display\',serif;font-size:2rem;'
            f'font-weight:600;margin:0;">{dname}{link_html}</h1>'
            f'<p style="color:#6B7280;font-size:0.9rem;margin-top:4px;">{city}</p>',
            unsafe_allow_html=True)
    with hc2:
        # Quick status pills
        has_menu = slug in menu_slugs
        imgs = db.get_images_for_restaurant(slug)
        ic = sum(1 for v in imgs.values() if v.get('has_image'))
        cp = db.get_copy_for_restaurant(slug)
        cc = sum(1 for v in cp.values() if v.strip())
        st.markdown(
            f'<div style="text-align:right;padding-top:0.75rem;">'
            f'{_pill_html("Menu", 1 if has_menu else 0, 1)} '
            f'{_pill_html("Img", ic, 9)} '
            f'{_pill_html("Copy", cc, 5)}'
            f'</div>', unsafe_allow_html=True)

    # Tabs
    tab_ov, tab_mn, tab_im, tab_cp, tab_br, tab_res, tab_lnk, tab_loc = st.tabs(
        ["Overview", "Menu", "Images", "Copy", "Brand",
         "IDs", "Links", "Contact"])

    with tab_ov:
        _render_overview(slug, r_data, dname)
    with tab_mn:
        _render_menu_tab(slug, dname, menus_list)
    with tab_im:
        _render_images_tab(slug, dname)
    with tab_cp:
        _render_copy_tab(slug, r_data, dname)
    with tab_br:
        _render_brand_tab(slug, r_data, dname)
    with tab_res:
        _render_reservations_tab(slug, r_data, dname)
    with tab_lnk:
        _render_links_tab(slug, r_data, dname)
    with tab_loc:
        _render_contact_tab(slug, r_data, dname)


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Overview
# ═══════════════════════════════════════════════════════════════════════════

def _render_overview(slug, r_data, dname):
    st.subheader("Overview")
    c1, c2 = st.columns(2)
    with c1:
        url = st.text_input("Website URL", value=r_data.get('website_url') or '',
                            key=f"ov_url_{slug}", placeholder="https://...")
    with c2:
        city_val = r_data.get('city') or get_city(slug)
        cities = ["", "New York", "Philadelphia", "Florida", "Nashville",
                  "Washington D.C.", "Other"]
        city_idx = cities.index(city_val) if city_val in cities else 0
        new_city = st.selectbox("City", cities, index=city_idx, key=f"ov_city_{slug}")

    notes = st.text_area("Notes", value=r_data.get('notes') or '',
                         key=f"ov_notes_{slug}", height=80, placeholder="Internal notes...")
    cs, cd = st.columns([3, 1])
    with cs:
        if st.button("Save Changes", key=f"ov_save_{slug}", type="primary"):
            fields = {'website_url': url, 'notes': notes}
            if new_city:
                fields['city'] = new_city
            db.update_restaurant(slug, **fields)
            st.success("Saved!")
            st.rerun()
    with cd:
        ck = f"ov_cdel_{slug}"
        if st.session_state.get(ck):
            if st.button("Confirm Delete?", key=f"ov_dc_{slug}", type="primary"):
                db.delete_restaurant(slug)
                st.session_state.pop(ck, None)
                st.session_state.pop('selected_restaurant', None)
                st.rerun()
        else:
            if st.button("Delete Restaurant", key=f"ov_del_{slug}", type="secondary"):
                st.session_state[ck] = True
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Menu
# ═══════════════════════════════════════════════════════════════════════════

def _render_menu_tab(slug, dname, menus_list):
    st.subheader("Menu")
    from src.models import Restaurant as RestModel, ParsedMenu
    from src.menu.docx_parser import extract_text, filter_menu_content
    from src.menu.llm_client import parse_menu, parse_live_menu
    from src.menu.column_balancer import balance_menu
    from src.menu.web_scraper import scrape_menu_page
    from src.menu.menu_differ import (
        compare_menus, restaurant_to_parsed_menu, apply_diff, ChangeType, MenuDiff)

    model_id = "claude-sonnet-4-5"
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        api_key = None
    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY")

    # Upload
    uploaded = st.file_uploader("Upload .docx menu", type=["docx"],
                                key=f"mu_{slug}", label_visibility="collapsed")
    if uploaded is not None:
        fid = uploaded.file_id
        if st.session_state.get(f"_mp_{slug}") != fid:
            if not st.session_state.get(f"_mb_{slug}"):
                st.session_state[f"_mb_{slug}"] = True
                try:
                    with st.status("Preparing your menu...", expanded=True) as status:
                        bar = st.progress(0, text="Reading...")
                        raw = extract_text(uploaded.read())
                        bar.progress(5)
                        filt = filter_menu_content(raw)
                        bar.progress(10)
                        rd = db.get_restaurant(slug) or {}
                        ac = rd.get('accent_color') or '#c8102e'
                        al = rd.get('accent_light') or '#fef2f2'
                        bar.progress(15, text=f"Parsing **{dname}**...")

                        def cb(tn, i, t):
                            bar.progress(15 + int((i/t)*70), text=f"Course {i}/{t}: **{tn}**...")
                        try:
                            pm, _ = parse_menu(filt, model=model_id,
                                               api_key=api_key or None, on_progress=cb)
                        except Exception as e:
                            status.update(label="Error", state="error")
                            st.error(str(e))
                            st.session_state[f"_mb_{slug}"] = False
                            st.stop()
                        bar.progress(90, text="Balancing...")
                        rm = balance_menu(pm, restaurant_name=dname, slug=slug,
                                          accent_color=ac, accent_light=al)
                        bar.progress(95, text="Saving...")
                        db.save_menu(slug, rm)
                        bar.progress(100)
                        status.update(label="Done!", state="complete")
                    time.sleep(1)
                finally:
                    st.session_state[f"_mb_{slug}"] = False
                st.session_state[f"_mp_{slug}"] = fid
                st.rerun()

    restaurant_model = db.load_menu(slug)
    if not restaurant_model:
        st.info("No menu yet. Upload a .docx above.")
        return

    menu_record = next((m for m in menus_list if m['restaurant'] == slug), {})

    if st.session_state.get(f"editing_{slug}"):
        _render_menu_edit(slug, restaurant_model)
        return

    # Toolbar
    c1, c2, c3 = st.columns([1, 1, 1.5])
    with c1:
        if st.button("Edit", key=f"me_{slug}", width="stretch"):
            st.session_state[f"editing_{slug}"] = True
            st.rerun()
    with c2:
        dk = f"md_c_{slug}"
        if st.session_state.get(dk):
            if st.button("Confirm?", key=f"mdc_{slug}", type="primary", width="stretch"):
                db.delete_menu(slug)
                st.session_state.pop(dk, None)
                st.rerun()
        else:
            if st.button("Delete", key=f"md_{slug}", type="secondary", width="stretch"):
                st.session_state[dk] = True
                st.rerun()
    with c3:
        rk = f"rev_{slug}"
        if st.button("Review", key=f"mr_{slug}", width="stretch"):
            st.session_state[rk] = not st.session_state.get(rk, False)
            st.rerun()
    # Review
    rk = f"rev_{slug}"
    if st.session_state.get(rk):
        uc, bc = st.columns([5, 1])
        with uc:
            murl = st.text_input("URL", value=menu_record.get('menu_url') or '',
                                 key=f"mru_{slug}", placeholder="https://...",
                                 label_visibility="collapsed")
        with bc:
            chk = st.button("Check", key=f"mck_{slug}", type="primary", width="stretch")
        if chk:
            if not murl:
                st.warning("Enter a URL.")
            else:
                with st.status("Checking...", expanded=True) as status:
                    st.write("Fetching...")
                    try:
                        pt = scrape_menu_page(murl)
                    except Exception as e:
                        status.update(label="Failed", state="error")
                        st.error(str(e))
                        return
                    pg = st.empty()
                    try:
                        lm = parse_live_menu(pt, model=model_id, api_key=api_key or None,
                                             on_progress=lambda m: pg.write(m))
                    except Exception as e:
                        status.update(label="Failed", state="error")
                        st.error(str(e))
                        return
                    pg.empty()
                    dm = restaurant_to_parsed_menu(restaurant_model)
                    diff = compare_menus(dm, lm)
                    db.set_menu_url(slug, murl)
                    status.update(label=f"Done — {diff.summary}", state="complete")
                st.session_state[f"rd_{slug}"] = diff.model_dump()
                st.session_state[f"rl_{slug}"] = lm.model_dump()

        if f"rd_{slug}" in st.session_state:
            diff = MenuDiff.model_validate(st.session_state[f"rd_{slug}"])
            _render_diff(diff, ChangeType)
            hc = (diff.total_modified + diff.total_added + diff.total_removed) > 0
            if hc and f"rl_{slug}" in st.session_state:
                if diff.total_removed > 0:
                    st.warning(f"Will remove {diff.total_removed} item(s).")
                if st.button("Apply", key=f"ma_{slug}", type="primary"):
                    st.session_state[f"bak_{slug}"] = restaurant_model.model_dump_json()
                    live = ParsedMenu.model_validate(st.session_state[f"rl_{slug}"])
                    doc = restaurant_to_parsed_menu(restaurant_model)
                    res = balance_menu(apply_diff(doc, diff, live),
                                       restaurant_name=restaurant_model.name, slug=slug,
                                       accent_color=restaurant_model.accent_color,
                                       accent_light=restaurant_model.accent_light)
                    db.save_menu(slug, res)
                    del st.session_state[f"rd_{slug}"]
                    del st.session_state[f"rl_{slug}"]
                    st.rerun()

    if f"bak_{slug}" in st.session_state:
        if st.button("Undo Changes", key=f"mu_{slug}_u", type="secondary"):
            db.save_menu(slug, RestModel.model_validate_json(st.session_state[f"bak_{slug}"]))
            del st.session_state[f"bak_{slug}"]
            st.rerun()

    if restaurant_model.tabs:
        _render_menu_preview(restaurant_model)


def _render_menu_preview(rm):
    tdir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(tdir), autoescape=True)
    tpl = env.get_template("menu_tab_template.html")

    def html(t):
        return tpl.render(tab=t, accent_color=rm.accent_color, accent_light=rm.accent_light)

    def ht(t):
        mx = 0
        for c in t.columns:
            h = 80
            for s in c.sections:
                h += 60 + (30 if s.note else 0)
                for i in s.items:
                    h += 40 + (20 if i.description else 0) + (24 if i.tags else 0)
            mx = max(mx, h)
        return max(300, mx + 80 + (70 if t.description else 0) + (80 if t.footnote else 0))

    if len(rm.tabs) > 1:
        tabs = st.tabs([t.label for t in rm.tabs])
        for i, t in enumerate(rm.tabs):
            with tabs[i]:
                components.html(html(t), height=ht(t), scrolling=False)
    else:
        t = rm.tabs[0]
        components.html(html(t), height=ht(t), scrolling=False)


def _render_menu_edit(slug, restaurant_model):
    from src.models import Restaurant as RestModel
    ek = f"ed_{slug}"
    if ek not in st.session_state:
        st.session_state[ek] = restaurant_model.model_dump()
    data = st.session_state[ek]
    for ti, td in enumerate(data['tabs']):
        with st.expander(f"Tab: {td['label']}", expanded=False):
            td['label'] = st.text_input("Tab", value=td['label'], key=f"et_{slug}_{ti}_l")
            td['description'] = st.text_area("Desc", value=td.get('description') or '',
                                             key=f"et_{slug}_{ti}_d", height=68) or None
            for ci, cd in enumerate(td['columns']):
                for si, sd in enumerate(cd['sections']):
                    st.markdown("---")
                    st.markdown(f"**Col {ci+1} — Sec {si+1}**")
                    sd['title'] = st.text_input("Title", value=sd['title'],
                                                key=f"et_{slug}_{ti}_{ci}_{si}_t")
                    sd['note'] = st.text_input("Note", value=sd.get('note') or '',
                                               key=f"et_{slug}_{ti}_{ci}_{si}_n") or None
                    rm = []
                    for ii, it in enumerate(sd['items']):
                        cols = st.columns([3, 2, 3, 1])
                        with cols[0]:
                            it['name'] = st.text_input("N", value=it['name'],
                                key=f"et_{slug}_{ti}_{ci}_{si}_{ii}_n",
                                label_visibility="collapsed", placeholder="Name")
                        with cols[1]:
                            it['price'] = st.text_input("P", value=it.get('price') or '',
                                key=f"et_{slug}_{ti}_{ci}_{si}_{ii}_p",
                                label_visibility="collapsed", placeholder="Price") or None
                        with cols[2]:
                            it['description'] = st.text_input("D", value=it.get('description') or '',
                                key=f"et_{slug}_{ti}_{ci}_{si}_{ii}_d",
                                label_visibility="collapsed", placeholder="Desc") or None
                        with cols[3]:
                            if st.button("X", key=f"et_{slug}_{ti}_{ci}_{si}_{ii}_x",
                                         type="secondary"):
                                rm.append(ii)
                    for ri in sorted(rm, reverse=True):
                        sd['items'].pop(ri)
                        st.rerun()
                    if st.button("+ Item", key=f"et_{slug}_{ti}_{ci}_{si}_a", type="secondary"):
                        sd['items'].append({'name': '', 'price': None, 'description': None,
                                            'raw': False, 'supplement': None, 'tags': []})
                        st.rerun()
    cs, cc, _sp = st.columns([1, 1, 8])
    with cs:
        if st.button("Save", key=f"es_{slug}", type="primary"):
            db.save_menu(slug, RestModel.model_validate(data))
            del st.session_state[ek]
            st.session_state[f"editing_{slug}"] = False
            st.rerun()
    with cc:
        if st.button("Cancel", key=f"ec_{slug}"):
            st.session_state.pop(ek, None)
            st.session_state[f"editing_{slug}"] = False
            st.rerun()


def _render_diff(diff, ChangeType):
    parts = []
    if diff.total_matched:
        parts.append(f":green[{diff.total_matched} matched]")
    if diff.total_modified:
        parts.append(f":orange[{diff.total_modified} changed]")
    if diff.total_removed:
        parts.append(f":red[{diff.total_removed} missing]")
    if diff.total_added:
        parts.append(f":blue[{diff.total_added} new]")
    st.markdown(" | ".join(parts) if parts else "No items")
    for td in diff.tabs:
        ic = {ChangeType.matched: ":green[OK]", ChangeType.modified: ":orange[~]",
              ChangeType.removed: ":red[-]", ChangeType.added: ":blue[+]"}.get(td.change_type, "")
        with st.expander(f"{ic} **{td.tab_label}**",
                         expanded=td.change_type != ChangeType.matched):
            for sd in td.section_diffs:
                si = {ChangeType.matched: ":green[OK]", ChangeType.modified: ":orange[~]",
                      ChangeType.removed: ":red[-]", ChangeType.added: ":blue[+]"}.get(
                    sd.change_type, "")
                st.markdown(f"**{si} {sd.section_title}**")
                for it in sd.item_diffs:
                    if it.change_type == ChangeType.matched:
                        st.markdown(f"&emsp;:green[OK] {it.item_name}")
                    elif it.change_type == ChangeType.modified:
                        st.markdown(f"&emsp;:orange[~] {it.item_name} — {it.details}")
                    elif it.change_type == ChangeType.removed:
                        st.markdown(f"&emsp;:red[-] {it.item_name}")
                    elif it.change_type == ChangeType.added:
                        st.markdown(f"&emsp;:blue[+] {it.item_name}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Images
# ═══════════════════════════════════════════════════════════════════════════

IMAGE_FIELDS = [
    ('Hero_Image_Desktop', "Main Desktop Banner Image (Horizontal)",
     "Target: 1920x1080px \u2014 Horizontal image, 16:9 aspect ratio.", 1920, 1080, False),
    ('Hero_Image_Mobile', "Main Mobile Banner Image (Horizontal)",
     "Target: 750x472px \u2014 Horizontal image, ~1.59:1 aspect ratio.", 750, 472, False),
    ('Concept_1', "First About Us Image (Vertical)",
     "Target: 696x825px \u2014 Vertical image, ~5:6 aspect ratio.", 696, 825, False),
    ('Concept_2', "Second About Us Image (Near-Square)",
     "Target: 525x544px \u2014 Near-square image, ~1:1 aspect ratio.", 525, 544, False),
    ('Concept_3', "Third About Us Image (Near-Square)",
     "Target: 696x693px \u2014 Near-square image, ~1:1 aspect ratio.", 696, 693, False),
    ('Cuisine_1', "First Cuisine Image (Vertical)",
     "Target: 529x767px \u2014 Vertical image, ~2:3 aspect ratio.", 529, 767, False),
    ('Cuisine_2', "Second Cuisine Image (Landscape)",
     "Target: 696x606px \u2014 Landscape image, ~1.15:1 aspect ratio.", 696, 606, False),
    ('Menu_1', "Menu Image (Wide Horizontal)",
     "Target: 1321x558px \u2014 Wide horizontal image, ~2.4:1 aspect ratio.", 1321, 558, False),
    ('Group_Dining_1', "Group Dining Image (Square)",
     "Target: 696x696px \u2014 Square image, 1:1 aspect ratio.", 696, 696, False),
    ('Chef_1', "First Chef Image (Vertical + Black&White)",
     "Target: 600x800px \u2014 Vertical image, 3:4 aspect ratio.", 600, 800, True),
    ('Chef_2', "Second Chef Image (Vertical + Black&White)",
     "Target: 600x800px \u2014 Vertical image, 3:4 aspect ratio.", 600, 800, True),
    ('Chef_3', "Third Chef Image (Vertical + Black&White)",
     "Target: 600x800px \u2014 Vertical image, 3:4 aspect ratio.", 600, 800, True),
]
HERO_FIELDS = {"Hero_Image_Desktop", "Hero_Image_Mobile"}
CHEF_FIELDS = {"Chef_1", "Chef_2", "Chef_3"}
REQUIRED_FIELDS = {f[0] for f in IMAGE_FIELDS if not f[5]}


def _render_images_tab(slug, dname):
    st.subheader("Images")
    from src.cms.image_processor import (
        resize_and_crop, fix_exif_orientation, make_image_filename,
        is_black_and_white, apply_black_overlay)
    from src.cms.alt_text import generate_alt_text
    from src.ui.components import copy_button

    existing = db.get_images_for_restaurant(slug)
    ic = sum(1 for v in existing.values() if v.get('has_image'))
    req = sum(1 for f in IMAGE_FIELDS if not f[5]
              and f[0] in existing and existing[f[0]].get('has_image'))
    st.markdown(f"**{ic}** uploaded ({req}/{len(REQUIRED_FIELDS)} required)")

    _chef_expander = None

    for idx, (fn, header, description, tw, th, is_chef) in enumerate(IMAGE_FIELDS):
        # Chef images go inside a collapsible expander
        if fn == 'Chef_1':
            _chef_expander = st.expander("Chef Pictures (Optional)", expanded=False)

        parent = _chef_expander if fn in CHEF_FIELDS else None

        with (parent if parent else st.container()):
            # Card header with title + requirement
            st.markdown(f"""
            <div class="image-field-card">
                <div class="field-title">{header}</div>
                <div class="field-requirement">{description}</div>
            </div>
            """, unsafe_allow_html=True)

            meta = existing.get(fn, {})
            has = meta.get('has_image', False)
            idata = None

            # Show existing image preview directly under header card
            if has:
                idata = db.get_image_data(slug, fn)
                if idata:
                    # Hero images: before/after overlay preview
                    if fn in HERO_FIELDS:
                        pil_img = Image.open(io.BytesIO(idata))
                        cur_op = meta.get('overlay_opacity', 40)

                        col_before, col_after = st.columns(2)
                        with col_before:
                            st.caption("Without Filter")
                            st.image(idata, width=300)
                        with col_after:
                            st.caption(f"With Filter ({cur_op}% opacity)")
                            if cur_op > 0:
                                buf = io.BytesIO()
                                apply_black_overlay(pil_img, cur_op).save(
                                    buf, format='JPEG', quality=95)
                                st.image(buf.getvalue(), width=300)
                            else:
                                st.image(idata, width=300)

                        # Filter opacity controls above uploader
                        st.markdown('<div class="field-label">Filter Opacity</div>',
                                    unsafe_allow_html=True)
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            op = st.slider(
                                "Opacity", 0, 100, cur_op, step=5,
                                key=f"io_{slug}_{fn}", label_visibility="collapsed")
                        with c2:
                            st.metric("Opacity", f"{op}%")
                        if op != cur_op:
                            db.update_overlay(slug, fn, op)
                    else:
                        st.image(idata, width=300)

            # File uploader
            up = st.file_uploader(
                "Upload image", type=['jpg', 'jpeg', 'png', 'webp'],
                key=f"iu_{slug}_{fn}", label_visibility="collapsed")

            if up:
                pil = fix_exif_orientation(Image.open(up))
                if pil.mode in ('RGBA', 'LA', 'PA', 'P'):
                    pil = pil.convert('RGB')
                if is_chef:
                    pil = pil.convert('L').convert('RGB')
                pil = resize_and_crop(pil, tw, th)
                buf = io.BytesIO()
                pil.save(buf, format='JPEG', quality=100, subsampling=0)
                at = ''
                with st.spinner("Generating alt text..."):
                    at = generate_alt_text(pil) or ''
                db.save_image(slug, fn, buf.getvalue(), up.name, at)
                st.success(f"Saved {header.split('(')[0].strip()}!")
                st.rerun()

            # Remaining controls for existing images
            if has and idata:
                # Chef B&W check
                if is_chef:
                    pil_img = Image.open(io.BytesIO(idata))
                    if not is_black_and_white(pil_img):
                        wc, bc = st.columns([3, 1])
                        with wc:
                            st.warning("Brand guidelines suggest Black & White images.")
                        with bc:
                            if st.button("Convert to B&W", key=f"ib_{slug}_{fn}"):
                                bw = resize_and_crop(
                                    pil_img.convert('L').convert('RGB'), tw, th)
                                buf = io.BytesIO()
                                bw.save(buf, format='JPEG', quality=100, subsampling=0)
                                db.save_image(slug, fn, buf.getvalue(),
                                              meta.get('original_filename', ''),
                                              meta.get('alt_text', ''))
                                st.rerun()

                # Download button
                alt = meta.get('alt_text', '')
                dl = make_image_filename(slug, fn, tw, th, 'jpg', alt)
                st.download_button(
                    f"Download Resized {fn.replace('_', ' ')}",
                    data=idata, file_name=dl, mime="image/jpeg",
                    key=f"id_{slug}_{fn}")

                # Alt text (ADA)
                st.markdown('<div class="field-label">Alt Text (ADA)</div>',
                            unsafe_allow_html=True)
                alt_key = f"ia_{slug}_{fn}"
                new_alt = st.text_area(
                    f"Alt text for {header}", value=alt,
                    key=alt_key, label_visibility="collapsed", height=68)
                if new_alt != alt:
                    db.update_alt_text(slug, fn, new_alt)

                # Action buttons row — equal width, left-aligned
                bc1, bc2, bc3, _bsp = st.columns([1, 1, 1, 7], gap="small")
                with bc1:
                    if new_alt.strip():
                        if st.button("Copy", key=f"imgbtn_copy_{slug}_{fn}"):
                            st.session_state[f"_copied_{slug}_{fn}"] = True
                            st.rerun()
                        if st.session_state.pop(f"_copied_{slug}_{fn}", False):
                            components.html(
                                f'<script>navigator.clipboard.writeText({json.dumps(new_alt)})</script>',
                                height=0)
                            st.toast("Copied!")
                with bc2:
                    if st.button("Generate ADA", key=f"imgbtn_gen_{slug}_{fn}"):
                        with st.spinner("Generating..."):
                            g = generate_alt_text(Image.open(io.BytesIO(idata)))
                        if g:
                            db.update_alt_text(slug, fn, g)
                            st.rerun()
                with bc3:
                    if st.button("Remove Image", key=f"imgbtn_del_{slug}_{fn}"):
                        db.delete_image(slug, fn)
                        st.rerun()

            # Dividers between fields (skip before chef expander)
            if idx < len(IMAGE_FIELDS) - 1:
                next_is_chef = IMAGE_FIELDS[idx + 1][0] in CHEF_FIELDS
                curr_is_chef = fn in CHEF_FIELDS
                if not (not curr_is_chef and next_is_chef):
                    st.markdown("---")

    # Download all as ZIP
    st.markdown("---")
    if st.button("Download All as ZIP", type="primary", key=f"iz_{slug}"):
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fn, _, _, w, h, _ in IMAGE_FIELDS:
                d = db.get_image_data(slug, fn)
                if d:
                    zf.writestr(make_image_filename(
                        slug, fn, w, h, 'jpg',
                        existing.get(fn, {}).get('alt_text', '')), d)
        st.download_button("Download ZIP", data=zbuf.getvalue(),
                           file_name=f"{slug}_images.zip", mime="application/zip",
                           key=f"izd_{slug}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Copy
# ═══════════════════════════════════════════════════════════════════════════

def _render_copy_tab(slug, r_data, dname):
    st.subheader("Copy")
    from src.cms.copy_generator import (
        COPY_SECTIONS, generate_copy, load_master_instructions,
        save_master_instructions, DEFAULT_COPY_INSTRUCTIONS)
    from src.cms.brand_detector import scrape_website
    from src.ui.components import render_copy_section

    _WEBSITE_COPY_IDS = {'the_concept', 'the_cuisine', 'group_dining'}
    _META_IDS = {'meta_title', 'meta_description'}

    wurl = r_data.get('website_url', '')
    cu, cb = st.columns([4, 1])
    with cu:
        url = st.text_input("Website URL", value=wurl, key=f"cu_{slug}",
                            placeholder="https://...", label_visibility="collapsed")
    with cb:
        gen = st.button("Generate Copy", type="primary", width="stretch", key=f"cg_{slug}")

    with st.expander("Edit Copy Instructions", expanded=False):
        cur = load_master_instructions()
        ik = f"{slug}_ci"
        if ik not in st.session_state:
            st.session_state[ik] = cur
        ni = st.text_area("Instructions", value=st.session_state[ik], height=300,
                          key=f"_w_ci_{slug}", label_visibility="collapsed")
        st.session_state[ik] = ni
        ci1, ci2 = st.columns(2)
        with ci1:
            if st.button("Save Default", key=f"cis_{slug}"):
                save_master_instructions(ni)
                st.success("Saved.")
        with ci2:
            if st.button("Reset", key=f"cir_{slug}"):
                st.session_state[ik] = DEFAULT_COPY_INSTRUCTIONS
                st.rerun()

    ec = db.get_copy_for_restaurant(slug)
    for sid, label, wmin, wmax, desc in COPY_SECTIONS:
        sk = f"{slug}_copy_{sid}"
        if sk not in st.session_state:
            st.session_state[sk] = ec.get(sid, '')

    if gen:
        if not url:
            st.warning("Enter a URL first.")
        else:
            with st.spinner("Scraping..."):
                ok, text, error, detected = scrape_website(url)
            if not ok:
                st.error(error)
            else:
                if detected and r_data:
                    fields = {}
                    for k in ('primary_color', 'booking_platform', 'opentable_rid',
                              'resy_url', 'tripleseat_form_id', 'mailing_list_url',
                              'facebook_url', 'instagram_url', 'phone',
                              'email_general', 'email_events', 'email_marketing',
                              'email_press', 'address', 'google_maps_url', 'order_online_url'):
                        dk = k if k != 'booking_platform' else 'booking'
                        val = detected.get(dk, '')
                        if val:
                            fields[k] = val
                    if fields:
                        db.update_restaurant(slug, **fields)
                if url != wurl:
                    db.update_restaurant(slug, website_url=url)
                instr = st.session_state.get(f"{slug}_ci", load_master_instructions())
                with st.spinner("Generating copy..."):
                    success, cd, err = generate_copy(text, dname, instructions=instr)
                if success:
                    for sid, content in cd.items():
                        if content:
                            st.session_state[f"{slug}_copy_{sid}"] = content
                            st.session_state[f"_w_{slug}_copy_{sid}"] = content
                    st.success("Generated!")
                    st.rerun()
                else:
                    st.error(err)

    # === Website Copy ===
    st.subheader("Website Copy")
    for sid, label, wmin, wmax, desc in COPY_SECTIONS:
        if sid in _WEBSITE_COPY_IDS:
            render_copy_section(slug, sid, label, wmin, wmax, desc)
            if st.button(f"Regen {label}", key=f"cr_{slug}_{sid}", type="secondary"):
                if not url:
                    st.warning("Enter a URL first.")
                else:
                    with st.spinner(f"Regenerating {label}..."):
                        ok, text, error, _ = scrape_website(url)
                        if ok:
                            instr = st.session_state.get(f"{slug}_ci", load_master_instructions())
                            s, cd, err = generate_copy(text, dname, section=sid, instructions=instr)
                            if s and cd.get(sid):
                                st.session_state[f"{slug}_copy_{sid}"] = cd[sid]
                                st.session_state[f"_w_{slug}_copy_{sid}"] = cd[sid]
                                st.rerun()
                            elif err:
                                st.error(err)
                        else:
                            st.error(error)

    # === SEO Meta Tags ===
    st.markdown("---")
    st.subheader("SEO Meta Tags")
    st.caption("HTML meta title and description tags for search engine optimization.")
    for sid, label, wmin, wmax, desc in COPY_SECTIONS:
        if sid in _META_IDS:
            height = 68 if sid == 'meta_title' else 80
            render_copy_section(slug, sid, label, wmin, wmax, desc, height=height)
            if st.button(f"Regen {label}", key=f"cr_{slug}_{sid}", type="secondary"):
                if not url:
                    st.warning("Enter a URL first.")
                else:
                    with st.spinner(f"Regenerating {label}..."):
                        ok, text, error, _ = scrape_website(url)
                        if ok:
                            instr = st.session_state.get(f"{slug}_ci", load_master_instructions())
                            s, cd, err = generate_copy(text, dname, section=sid, instructions=instr)
                            if s and cd.get(sid):
                                st.session_state[f"{slug}_copy_{sid}"] = cd[sid]
                                st.session_state[f"_w_{slug}_copy_{sid}"] = cd[sid]
                                st.rerun()
                            elif err:
                                st.error(err)
                        else:
                            st.error(error)

    st.markdown("---")
    if st.button("Save All Copy", type="primary", key=f"cs_{slug}"):
        d = {sid: st.session_state.get(f"{slug}_copy_{sid}", '') for sid, *_ in COPY_SECTIONS}
        db.save_all_copy(slug, d)
        st.success("Saved!")


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Brand
# ═══════════════════════════════════════════════════════════════════════════

def _render_brand_tab(slug, r_data, dname):
        # ── Brand Identity: Logo + Favicon + Color (3-column) ──
    st.subheader("Brand Identity")
    col_logo, col_favicon, col_color = st.columns([2, 1, 3])

    with col_logo:
        st.markdown("**Logo**")
        ld = db.get_image_data(slug, "Logo")
        if ld:
            st.image(ld, width=150)
            if st.button("Remove", key=f"brl_{slug}", type="secondary"):
                db.delete_image(slug, "Logo")
                st.rerun()
        else:
            st.caption("No logo detected.")
        with st.expander("Replace logo" if ld else "Add logo"):
            ul = st.file_uploader("Upload file", type=["jpg", "jpeg", "png", "svg", "webp", "gif"],
                                  key=f"bl_{slug}", label_visibility="collapsed")
            if ul:
                db.save_image(slug, "Logo", ul.read(), ul.name)
                st.rerun()

    with col_favicon:
        st.markdown("**Site Icon**")
        fd = db.get_image_data(slug, "Favicon")
        if fd:
            st.image(fd, width=48)
            if st.button("Remove", key=f"brf_{slug}", type="secondary"):
                db.delete_image(slug, "Favicon")
                st.rerun()
        else:
            st.caption("No icon detected.")
        with st.expander("Replace icon" if fd else "Add icon"):
            uf = st.file_uploader("Upload file", type=["jpg", "jpeg", "png", "ico", "svg", "webp"],
                                  key=f"bf_{slug}", label_visibility="collapsed")
            if uf:
                db.save_image(slug, "Favicon", uf.read(), uf.name)
                st.rerun()

    with col_color:
        st.markdown("**Primary Color**")
        cc = r_data.get('primary_color') or '#000000'
        pc, ph, _ = st.columns([0.5, 1.5, 3], vertical_alignment="bottom")
        with pc:
            nc = st.color_picker("Pick color", value=cc, key=f"bc_{slug}",
                                 label_visibility="collapsed")
        with ph:
            hx = st.text_input("Hex color", value=cc, placeholder="#000000",
                                key=f"bh_{slug}", label_visibility="collapsed")

    st.markdown("---")
    bc1, bc2 = st.columns([1, 1], gap="small")
    with bc1:
        if st.button("Save Brand Data", type="primary", key=f"bs_{slug}"):
            fields = {'primary_color': hx}
            db.update_restaurant(slug, **fields)
            st.success("Saved!")
            st.rerun()
    with bc2:
        if st.button("Detect from Website", key=f"bd_detect_{slug}"):
            url = r_data.get('website_url', '')
            if not url:
                st.warning("No website URL set. Add one in the Overview tab first.")
            else:
                from src.cms.brand_detector import scrape_website
                with st.spinner(f"Scraping {url}..."):
                    ok, _, err, detected = scrape_website(url)
                if not ok:
                    st.error(f"Could not scrape: {err}")
                elif detected:
                    updates = {}
                    saved_items = []
                    if detected.get('primary_color'):
                        updates['primary_color'] = detected['primary_color']
                    if detected.get('booking'):
                        updates['booking_platform'] = detected['booking']
                    # Download and save logo
                    if detected.get('logo_url'):
                        try:
                            import requests as _req
                            _r = _req.get(detected['logo_url'], timeout=10,
                                          headers={'User-Agent': 'Mozilla/5.0'})
                            if _r.ok and len(_r.content) > 100:
                                db.save_image(slug, 'Logo', _r.content,
                                              detected['logo_url'].split('/')[-1].split('?')[0])
                                saved_items.append('Logo')
                        except Exception:
                            pass
                    # Download and save favicon
                    if detected.get('favicon_url'):
                        try:
                            import requests as _req
                            _r = _req.get(detected['favicon_url'], timeout=10,
                                          headers={'User-Agent': 'Mozilla/5.0'})
                            if _r.ok and len(_r.content) > 100:
                                db.save_image(slug, 'Favicon', _r.content,
                                              detected['favicon_url'].split('/')[-1].split('?')[0])
                                saved_items.append('Favicon')
                        except Exception:
                            pass
                    if updates:
                        db.update_restaurant(slug, **updates)
                        saved_items.extend(updates.keys())
                    if saved_items:
                        st.success(f"Detected: {', '.join(saved_items)}")
                        st.rerun()
                    else:
                        st.info("No brand data detected.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB: IDs
# ═══════════════════════════════════════════════════════════════════════════

def _render_reservations_tab(slug, r_data, dname):
    st.subheader("IDs & Integrations")
    booking_val = r_data.get('booking_platform', '')
    if booking_val:
        st.caption(f"Detected platform: **{booking_val}**")

    col_ot, col_resy = st.columns(2)
    with col_ot:
        ot = st.text_input("OpenTable RID", value=r_data.get('opentable_rid', ''),
                           key=f"bot_{slug}", placeholder="e.g. 123456",
                           help="Numeric Restaurant ID used in OpenTable widgets.")
    with col_resy:
        rs = st.text_input("Resy URL", value=r_data.get('resy_url', ''),
                           key=f"brs_{slug}", placeholder="https://resy.com/cities/...",
                           help="Full Resy venue URL.")

    col_ts, col_ot_id = st.columns(2)
    with col_ts:
        ts = st.text_input("Tripleseat Form ID", value=r_data.get('tripleseat_form_id', ''),
                           key=f"bts_{slug}", placeholder="e.g. 6616",
                           help="Numeric lead_form_id from Tripleseat.")
        if not r_data.get('tripleseat_form_id'):
            st.caption(":gray[No group bookings / TripleSeat detected]")
    with col_ot_id:
        onetrust = st.text_input("OneTrust ID", value=r_data.get('onetrust_id', ''),
                                 key=f"bont_{slug}", placeholder="e.g. 01234567-abcd-...",
                                 help="OneTrust cookie consent domain script ID.")

    col_wf, col_gtm = st.columns(2)
    with col_wf:
        wordfence = st.text_input("Wordfence API Key", value=r_data.get('wordfence_api_key', ''),
                                  key=f"bwf_{slug}", placeholder="e.g. abc123def456...",
                                  help="Wordfence security plugin license key.")
    with col_gtm:
        gtm = st.text_input("GTM ID", value=r_data.get('gtm_id', ''),
                             key=f"bgtm_{slug}", placeholder="e.g. GTM-XXXXXXX",
                             help="Google Tag Manager container ID.")

    st.markdown("---")
    dc1, dc2 = st.columns([1, 1], gap="small")
    with dc1:
        if st.button("Save IDs", type="primary", key=f"brs_save_{slug}"):
            db.update_restaurant(slug, booking_platform=booking_val,
                                 opentable_rid=ot, resy_url=rs,
                                 tripleseat_form_id=ts, onetrust_id=onetrust,
                                 wordfence_api_key=wordfence, gtm_id=gtm)
            st.success("Saved!")
            st.rerun()
    with dc2:
        if st.button("Detect from Website", key=f"brs_detect_{slug}"):
            url = r_data.get('website_url', '')
            if not url:
                st.warning("No website URL set. Add one in the Overview tab first.")
            else:
                from src.cms.brand_detector import scrape_website
                with st.spinner(f"Scraping {url}..."):
                    ok, text_content, err, detected = scrape_website(url)
                if not ok:
                    st.error(f"Could not scrape: {err}")
                elif detected:
                    # If no TripleSeat found, try group/events pages directly
                    if not detected.get('tripleseat_form_id'):
                        import requests as _req
                        from src.cms.brand_detector import _detect_site_metadata
                        _hdrs = {'User-Agent': 'Mozilla/5.0'}
                        for _sub in ('/private-events/', '/group-dining/', '/private-dining/',
                                     '/events/', '/parties/', '/private-events', '/group-dining'):
                            try:
                                _su = url.rstrip('/') + _sub
                                _sr = _req.get(_su, headers=_hdrs, timeout=5)
                                if _sr.ok and 'tripleseat' in _sr.text.lower():
                                    _sm = _detect_site_metadata(_sr.content)
                                    if _sm.get('tripleseat_form_id'):
                                        detected['tripleseat_form_id'] = _sm['tripleseat_form_id']
                                        break
                            except Exception:
                                pass
                    updates = {}
                    if detected.get('booking'):
                        updates['booking_platform'] = detected['booking']
                    if detected.get('opentable_rid'):
                        updates['opentable_rid'] = detected['opentable_rid']
                    if detected.get('resy_url'):
                        updates['resy_url'] = detected['resy_url']
                    if detected.get('tripleseat_form_id'):
                        updates['tripleseat_form_id'] = detected['tripleseat_form_id']
                    if detected.get('address'):
                        updates['address'] = detected['address']
                        detected_city = city_from_address(detected['address'])
                        if detected_city:
                            updates['city'] = detected_city
                    if updates:
                        db.update_restaurant(slug, **updates)
                        st.success(f"Detected and saved: {', '.join(updates.keys())}")
                        st.rerun()
                    else:
                        st.info("No group booking page or TripleSeat form found. Restaurant likely doesn't offer group bookings.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Links
# ═══════════════════════════════════════════════════════════════════════════

def _render_links_tab(slug, r_data, dname):
    l1, l2 = st.columns(2)
    with l1:
        ml = st.text_input("Mailing List URL", value=r_data.get('mailing_list_url', ''),
                           key=f"bml_{slug}", placeholder="https://signup.e2ma.net/...")
        fb = st.text_input("Facebook", value=r_data.get('facebook_url', ''), key=f"bfb_{slug}")
    with l2:
        oo = st.text_input("Order Online URL", value=r_data.get('order_online_url', ''),
                           key=f"boo_{slug}", placeholder="https://order.online/store/...")
        ig = st.text_input("Instagram", value=r_data.get('instagram_url', ''), key=f"big_{slug}")

    st.markdown("---")
    bc1, bc2 = st.columns([1, 1], gap="small")
    with bc1:
        if st.button("Save Links", type="primary", key=f"blnk_save_{slug}"):
            db.update_restaurant(slug, mailing_list_url=ml, order_online_url=oo,
                                 facebook_url=fb, instagram_url=ig)
            st.success("Saved!")
            st.rerun()
    with bc2:
        if st.button("Detect from Website", key=f"blnk_detect_{slug}"):
            url = r_data.get('website_url', '')
            if not url:
                st.warning("No website URL set. Add one in the Overview tab first.")
            else:
                from src.cms.brand_detector import scrape_website
                with st.spinner(f"Scraping {url}..."):
                    ok, _, err, detected = scrape_website(url)
                if not ok:
                    st.error(f"Could not scrape: {err}")
                elif detected:
                    updates = {}
                    for k in ('mailing_list_url', 'order_online_url', 'facebook_url', 'instagram_url'):
                        if detected.get(k):
                            updates[k] = detected[k]
                    if updates:
                        db.update_restaurant(slug, **updates)
                        st.success(f"Detected: {', '.join(updates.keys())}")
                        st.rerun()
                    else:
                        st.info("Nothing detected on the website.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB: Contact & Location
# ═══════════════════════════════════════════════════════════════════════════

def _render_contact_tab(slug, r_data, dname):
    st.subheader("Contact & Location")
    c1, c2 = st.columns(2)
    with c1:
        ph_val = st.text_input("Phone", value=r_data.get('phone', ''), key=f"bph_{slug}")
        addr = st.text_input("Address", value=r_data.get('address', ''), key=f"bad_{slug}")
        gm = st.text_input("Google Maps", value=r_data.get('google_maps_url', ''), key=f"bgm_{slug}")
    with c2:
        eg = st.text_input("Email (General)", value=r_data.get('email_general', ''), key=f"beg_{slug}")
        ee = st.text_input("Email (Events)", value=r_data.get('email_events', ''), key=f"bee_{slug}")
        em = st.text_input("Email (Marketing)", value=r_data.get('email_marketing', ''), key=f"bem_{slug}")
        ep = st.text_input("Email (Press)", value=r_data.get('email_press', ''), key=f"bep_{slug}")

    st.markdown("---")
    bc1, bc2 = st.columns([1, 1], gap="small")
    with bc1:
        if st.button("Save Contact Info", type="primary", key=f"bloc_save_{slug}"):
            db.update_restaurant(slug, phone=ph_val, address=addr, google_maps_url=gm,
                                 email_general=eg, email_events=ee,
                                 email_marketing=em, email_press=ep)
            st.success("Saved!")
            st.rerun()
    with bc2:
        if st.button("Detect from Website", key=f"bloc_detect_{slug}"):
            url = r_data.get('website_url', '')
            if not url:
                st.warning("No website URL set. Add one in the Overview tab first.")
            else:
                from src.cms.brand_detector import scrape_website
                with st.spinner(f"Scraping {url}..."):
                    ok, _, err, detected = scrape_website(url)
                if not ok:
                    st.error(f"Could not scrape: {err}")
                elif detected:
                    updates = {}
                    for k in ('phone', 'address', 'google_maps_url',
                              'email_general', 'email_events', 'email_marketing', 'email_press'):
                        if detected.get(k):
                            updates[k] = detected[k]
                    if detected.get('address'):
                        detected_city = city_from_address(detected['address'])
                        if detected_city:
                            updates['city'] = detected_city
                    if updates:
                        db.update_restaurant(slug, **updates)
                        st.success(f"Detected: {', '.join(updates.keys())}")
                        st.rerun()
                    else:
                        st.info("Nothing detected on the website.")


# ═══════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════

def run():
    _selected = st.session_state.get('selected_restaurant')
    if _selected and db.get_restaurant(_selected):
        _show_detail_view(_selected)
    elif st.session_state.get('show_add_form'):
        _show_add_form()
    else:
        _show_list_view()

# Guard: skip auto-run when imported by another page (e.g. 3_Restaurants.py)
if not st.session_state.get('_importing_dashboard'):
    run()
