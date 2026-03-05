"""
One-time migration script: copies data from both old Turso DBs into the new unified DB.

Usage:
    Set environment variables for the OLD databases:
        OLD_MENU_TURSO_URL, OLD_MENU_TURSO_TOKEN
        OLD_CMS_TURSO_URL, OLD_CMS_TURSO_TOKEN
    And for the NEW database:
        TURSO_DB_URL, TURSO_AUTH_TOKEN

    Then run:
        python scripts/migrate_data.py
"""

import json
import os
import re
import sys

# Add parent dir to path so we can import src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db import (
    init_db, add_restaurant, update_restaurant, save_menu, save_image,
    save_copy_section, normalize_to_slug, get_connection, _commit
)
from src.restaurant_registry import (
    RESTAURANT_CITIES, ACCENT_COLORS, display_name, get_city
)
from src.models import Restaurant


def _connect_old(url, token):
    """Connect to an old Turso database."""
    if url:
        import libsql_experimental as libsql
        return libsql.connect(url, auth_token=token)
    return None


def _rows_to_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def migrate_menu_organiser():
    """Migrate data from the Menu Organiser's Turso DB."""
    url = os.getenv('OLD_MENU_TURSO_URL', '')
    token = os.getenv('OLD_MENU_TURSO_TOKEN', '')
    if not url:
        print("Skipping Menu Organiser migration (OLD_MENU_TURSO_URL not set)")
        return

    print("Connecting to old Menu Organiser DB...")
    conn = _connect_old(url, token)

    # Get all menus
    cur = conn.execute("SELECT restaurant, menu_json, push_data, updated_at, menu_url FROM menus")
    menus = _rows_to_dicts(cur)
    print(f"  Found {len(menus)} menus")

    for m in menus:
        old_name = m['restaurant']
        slug = normalize_to_slug(old_name)
        dname = display_name(old_name)
        city = get_city(slug)

        # Get accent colors if known
        accent_color = '#c8102e'
        accent_light = '#fef2f2'
        for key, (ac, al) in ACCENT_COLORS.items():
            if key in slug or slug in key:
                accent_color = ac
                accent_light = al
                break

        # Ensure restaurant exists
        add_restaurant(slug, dname, city=city, accent_color=accent_color, accent_light=accent_light)

        if m.get('push_data'):
            update_restaurant(slug, push_data=int(m['push_data']))

        # Migrate menu data
        if m.get('menu_json'):
            try:
                restaurant_model = Restaurant.model_validate_json(m['menu_json'])
                # Update slug in model to match canonical
                restaurant_model.slug = slug
                save_menu(slug, restaurant_model)

                if m.get('menu_url'):
                    from src.db import set_menu_url
                    set_menu_url(slug, m['menu_url'])

                print(f"  Migrated menu: {old_name} -> {slug}")
            except Exception as e:
                print(f"  ERROR migrating menu {old_name}: {e}")

    print(f"  Menu migration complete")


def migrate_cms_tool():
    """Migrate data from the CMS Tool's Turso DB."""
    url = os.getenv('OLD_CMS_TURSO_URL', '')
    token = os.getenv('OLD_CMS_TURSO_TOKEN', '')
    if not url:
        print("Skipping CMS Tool migration (OLD_CMS_TURSO_URL not set)")
        return

    print("Connecting to old CMS Tool DB...")
    conn = _connect_old(url, token)

    # Get all restaurants
    cur = conn.execute(
        "SELECT name, display_name, website_url, notes, primary_color, checklist,"
        " booking_platform, opentable_rid, pull_data, tripleseat_form_id, resy_url,"
        " mailing_list_url, facebook_url, instagram_url, phone, email_general,"
        " email_events, email_marketing, email_press, address, google_maps_url,"
        " order_online_url FROM restaurants"
    )
    restaurants = _rows_to_dicts(cur)
    print(f"  Found {len(restaurants)} restaurants")

    for r in restaurants:
        old_name = r['name']
        slug = normalize_to_slug(old_name)
        dname = r.get('display_name') or display_name(old_name)
        city = get_city(slug)

        # Ensure restaurant exists
        add_restaurant(slug, dname, city=city)

        # Update all fields
        fields = {}
        if r.get('website_url'):
            fields['website_url'] = r['website_url']
        if r.get('notes'):
            fields['notes'] = r['notes']
        if r.get('primary_color'):
            fields['primary_color'] = r['primary_color']
        if r.get('checklist'):
            fields['checklist'] = r['checklist']
        if r.get('booking_platform'):
            fields['booking_platform'] = r['booking_platform']
        if r.get('opentable_rid'):
            fields['opentable_rid'] = r['opentable_rid']
        if r.get('pull_data'):
            fields['push_data'] = int(r['pull_data'])
        if r.get('tripleseat_form_id'):
            fields['tripleseat_form_id'] = r['tripleseat_form_id']
        if r.get('resy_url'):
            fields['resy_url'] = r['resy_url']
        if r.get('mailing_list_url'):
            fields['mailing_list_url'] = r['mailing_list_url']
        if r.get('facebook_url'):
            fields['facebook_url'] = r['facebook_url']
        if r.get('instagram_url'):
            fields['instagram_url'] = r['instagram_url']
        if r.get('phone'):
            fields['phone'] = r['phone']
        if r.get('email_general'):
            fields['email_general'] = r['email_general']
        if r.get('email_events'):
            fields['email_events'] = r['email_events']
        if r.get('email_marketing'):
            fields['email_marketing'] = r['email_marketing']
        if r.get('email_press'):
            fields['email_press'] = r['email_press']
        if r.get('address'):
            fields['address'] = r['address']
        if r.get('google_maps_url'):
            fields['google_maps_url'] = r['google_maps_url']
        if r.get('order_online_url'):
            fields['order_online_url'] = r['order_online_url']

        if fields:
            update_restaurant(slug, **fields)

        print(f"  Migrated restaurant: {old_name} -> {slug}")

    # Migrate images
    cur = conn.execute(
        "SELECT restaurant, field_name, original_filename, image_data, alt_text, overlay_opacity "
        "FROM images WHERE image_data IS NOT NULL"
    )
    images = _rows_to_dicts(cur)
    print(f"  Found {len(images)} images")

    for img in images:
        slug = normalize_to_slug(img['restaurant'])
        save_image(
            slug, img['field_name'],
            bytes(img['image_data']) if img['image_data'] else b'',
            img.get('original_filename', ''),
            img.get('alt_text', ''),
            img.get('overlay_opacity', 40),
        )
    print(f"  Image migration complete")

    # Migrate copy sections
    cur = conn.execute("SELECT restaurant, section_id, content FROM copy_sections")
    copies = _rows_to_dicts(cur)
    print(f"  Found {len(copies)} copy sections")

    for cp in copies:
        slug = normalize_to_slug(cp['restaurant'])
        save_copy_section(slug, cp['section_id'], cp.get('content', ''))
    print(f"  Copy migration complete")


def seed_city_data():
    """Seed city mapping for restaurants from the hardcoded config."""
    print("Seeding city data from restaurant_config...")
    for slug, city in RESTAURANT_CITIES.items():
        dname = display_name(slug)
        accent_color = ''
        accent_light = ''
        for key, (ac, al) in ACCENT_COLORS.items():
            if key in slug or slug in key:
                accent_color = ac
                accent_light = al
                break
        add_restaurant(slug, dname, city=city,
                       accent_color=accent_color, accent_light=accent_light)
    print(f"  Seeded {len(RESTAURANT_CITIES)} restaurants")


if __name__ == '__main__':
    print("=" * 60)
    print("Starr Content Hub — Data Migration")
    print("=" * 60)

    # Initialize the new unified DB
    print("\nInitializing unified database...")
    init_db()

    # Seed base restaurant data
    seed_city_data()

    # Migrate from both old databases
    print("\n--- Menu Organiser Migration ---")
    migrate_menu_organiser()

    print("\n--- CMS Tool Migration ---")
    migrate_cms_tool()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
