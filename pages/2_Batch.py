"""Batch Operations — Bulk menu upload, image upload, alt text, copy generation, brand detection."""

import streamlit as st
st.session_state.pop('_on_restaurants_page', None)

from src import db
from src.restaurant_registry import display_name, city_from_address


restaurants = db.get_all_restaurants()
if not restaurants:
    st.info("No restaurants yet. Go to **Restaurants** to add some first.")
    st.stop()

st.subheader("Batch Operations")

# --- Batch Alt Text Generation ---
st.markdown("### Batch Alt Text Generation")
st.markdown("Generate ADA-compliant alt text for all images missing alt text.")

if st.button("Generate Missing Alt Text", type="primary", key="batch_alt"):
    from src.cms.alt_text import generate_alt_text
    from PIL import Image
    import io

    progress = st.progress(0)
    total = 0
    generated = 0

    for r in restaurants:
        slug = r['name']
        images = db.get_images_for_restaurant(slug)
        for field_name, meta in images.items():
            if meta.get('has_image') and not meta.get('alt_text', '').strip():
                total += 1

    if total == 0:
        st.info("All images already have alt text!")
    else:
        i = 0
        for r in restaurants:
            slug = r['name']
            images = db.get_images_for_restaurant(slug)
            for field_name, meta in images.items():
                if meta.get('has_image') and not meta.get('alt_text', '').strip():
                    img_data = db.get_image_data(slug, field_name)
                    if img_data:
                        pil_img = Image.open(io.BytesIO(img_data))
                        alt = generate_alt_text(pil_img)
                        if alt:
                            db.update_alt_text(slug, field_name, alt)
                            generated += 1
                    i += 1
                    progress.progress(i / total,
                                      text=f"{display_name(slug)} / {field_name}")
        st.success(f"Generated alt text for {generated}/{total} images.")


# --- Batch Copy Generation ---
st.markdown("---")
st.markdown("### Batch Copy Generation")
st.markdown("Generate marketing copy for all restaurants with a website URL but missing copy.")

if st.button("Generate Missing Copy", type="primary", key="batch_copy"):
    from src.cms.copy_generator import generate_copy, load_master_instructions
    from src.cms.brand_detector import scrape_website

    instructions = load_master_instructions()
    progress = st.progress(0)
    total = len([r for r in restaurants if r.get('website_url')])
    generated = 0

    for i, r in enumerate(restaurants):
        slug = r['name']
        url = r.get('website_url', '')
        if not url:
            continue

        existing_copy = db.get_copy_for_restaurant(slug)
        has_copy = any(v.strip() for v in existing_copy.values())
        if has_copy:
            progress.progress((i + 1) / total,
                              text=f"Skipping {display_name(slug)} (has copy)")
            continue

        progress.progress((i + 1) / total,
                          text=f"Generating for {display_name(slug)}...")

        ok, text, error, detected = scrape_website(url)
        if ok:
            dname = r.get('display_name') or display_name(slug)
            success, copy_dict, err = generate_copy(text, dname,
                                                    instructions=instructions)
            if success:
                db.save_all_copy(slug, copy_dict)
                generated += 1

    st.success(f"Generated copy for {generated} restaurants.")


# shared batch detect helper
def _batch_detect(keys, label, download_images=False):
    from src.cms.brand_detector import scrape_website

    with_url = [r for r in restaurants if r.get('website_url')]
    progress = st.progress(0)
    updated = 0
    details = []

    for i, r in enumerate(with_url):
        slug = r['name']
        url = r['website_url']
        dname = r.get('display_name') or display_name(slug)
        progress.progress((i + 1) / len(with_url), text=f"Detecting {dname}...")

        ok, text, error, detected = scrape_website(url)
        if not ok:
            details.append(f"~{dname}~: scrape failed ({error})")
            continue
        if not detected:
            details.append(f"~{dname}~: no data detected")
            continue

        fields = {}
        saved_extras = []

        for k in keys:
            if k == 'booking_platform':
                val = detected.get('booking', '')
            else:
                val = detected.get(k, '')
            if val and not r.get(k):
                fields[k] = val

        if 'address' in keys:
            addr_val = detected.get('address', '') or fields.get('address', '')
            if addr_val:
                detected_city = city_from_address(addr_val)
                if detected_city and not r.get('city'):
                    fields['city'] = detected_city

        if download_images:
            import requests as _req
            _hdrs = {'User-Agent': 'Mozilla/5.0'}
            if detected.get('logo_url') and not db.get_image_data(slug, 'Logo'):
                try:
                    _r = _req.get(detected['logo_url'], timeout=10, headers=_hdrs)
                    if _r.ok and len(_r.content) > 100:
                        db.save_image(slug, 'Logo', _r.content,
                                      detected['logo_url'].split('/')[-1].split('?')[0])
                        saved_extras.append('Logo')
                except Exception:
                    pass
            if detected.get('favicon_url') and not db.get_image_data(slug, 'Favicon'):
                try:
                    _r = _req.get(detected['favicon_url'], timeout=10, headers=_hdrs)
                    if _r.ok and len(_r.content) > 100:
                        db.save_image(slug, 'Favicon', _r.content,
                                      detected['favicon_url'].split('/')[-1].split('?')[0])
                        saved_extras.append('Favicon')
                except Exception:
                    pass

        if fields:
            db.update_restaurant(slug, **fields)
            updated += 1
            all_keys = list(fields.keys()) + saved_extras
            details.append(f"**{dname}**: {', '.join(all_keys)}")
        elif saved_extras:
            updated += 1
            details.append(f"**{dname}**: {', '.join(saved_extras)}")

    progress.empty()
    st.success(f"{label}: updated {updated}/{len(with_url)} restaurants.")
    for d in details:
        st.markdown(d)


# --- Detect All Missing Data ---
st.markdown("---")
st.markdown("### Detect All Missing Data")
st.markdown("Run all detection (Brand, IDs, Links, Contact) in a single pass.")

if st.button("Detect All Missing Data", type="primary", key="batch_all"):
    _batch_detect(
        keys=['primary_color', 'booking_platform', 'opentable_rid', 'resy_url',
              'tripleseat_form_id', 'order_online_url', 'mailing_list_url',
              'facebook_url', 'instagram_url', 'spotify_url', 'linkedin_url',
              'phone', 'email_general', 'email_events', 'email_marketing',
              'email_press', 'address', 'google_maps_url', 'opening_hours'],
        label="All",
        download_images=True,
    )


# --- Batch Brand Detection ---
st.markdown("---")
st.markdown("### Batch Brand Detection")
st.markdown("Detect primary color, logo, and site icon for all restaurants.")

if st.button("Detect Missing Brand Data", type="primary", key="batch_brand"):
    _batch_detect(
        keys=['primary_color', 'booking_platform'],
        label="Brand",
        download_images=True,
    )


# --- Batch IDs Detection ---
st.markdown("---")
st.markdown("### Batch IDs Detection")
st.markdown("Detect OpenTable, Resy, Tripleseat, and Order Online for all restaurants.")

if st.button("Detect Missing IDs", type="primary", key="batch_ids"):
    _batch_detect(
        keys=['booking_platform', 'opentable_rid', 'resy_url',
              'tripleseat_form_id', 'order_online_url'],
        label="IDs",
    )


# --- Batch Links Detection ---
st.markdown("---")
st.markdown("### Batch Links Detection")
st.markdown("Detect mailing list, social media, and other links for all restaurants.")

if st.button("Detect Missing Links", type="primary", key="batch_links"):
    _batch_detect(
        keys=['mailing_list_url', 'facebook_url', 'instagram_url',
              'spotify_url', 'linkedin_url'],
        label="Links",
    )


# --- Batch Contact Detection ---
st.markdown("---")
st.markdown("### Batch Contact Detection")
st.markdown("Detect phone, emails, address, opening hours, and Google Maps for all restaurants.")

if st.button("Detect Missing Contact Info", type="primary", key="batch_contact"):
    _batch_detect(
        keys=['phone', 'email_general', 'email_events', 'email_marketing',
              'email_press', 'address', 'google_maps_url', 'opening_hours'],
        label="Contact",
    )
