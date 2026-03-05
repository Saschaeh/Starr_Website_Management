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


# --- Batch Brand Detection ---
st.markdown("---")
st.markdown("### Batch Brand Detection")
st.markdown("Auto-detect brand data (color, booking, social, contact) for all restaurants.")

if st.button("Detect Missing Brand Data", type="primary", key="batch_brand"):
    from src.cms.brand_detector import scrape_website

    progress = st.progress(0)
    total = len([r for r in restaurants if r.get('website_url')])
    updated = 0

    for i, r in enumerate(restaurants):
        slug = r['name']
        url = r.get('website_url', '')
        if not url:
            continue

        progress.progress((i + 1) / total,
                          text=f"Detecting {display_name(slug)}...")

        ok, text, error, detected = scrape_website(url)
        if ok and detected:
            fields = {}
            for k in ('primary_color', 'opentable_rid', 'resy_url',
                      'tripleseat_form_id', 'mailing_list_url',
                      'facebook_url', 'instagram_url', 'phone',
                      'email_general', 'email_events', 'email_marketing',
                      'email_press', 'address', 'google_maps_url',
                      'order_online_url'):
                detected_key = k if k != 'booking_platform' else 'booking'
                val = detected.get(detected_key, '')
                if val and not r.get(k):
                    fields[k] = val
            if detected.get('booking') and not r.get('booking_platform'):
                fields['booking_platform'] = detected['booking']
            # Auto-detect city from address
            addr_val = detected.get('address', '') or fields.get('address', '')
            if addr_val:
                detected_city = city_from_address(addr_val)
                if detected_city and not r.get('city'):
                    fields['city'] = detected_city
            if fields:
                db.update_restaurant(slug, **fields)
                updated += 1

    st.success(f"Updated brand data for {updated} restaurants.")
