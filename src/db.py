"""
Unified persistence layer for Starr Content Hub.

Dual-mode:
  - Local dev:  standard sqlite3 with a file at data/starr_content_hub.db
  - Production: Turso (hosted SQLite) via libsql_experimental

Single database, 4 tables, `name` as the universal restaurant key.
Field names match CMS Tool and Menu Organiser exactly for pipeline compatibility.
"""

import json
import os
import threading

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Connection setup — detect Turso vs local
# ---------------------------------------------------------------------------

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
DB_PATH = os.path.join(DB_DIR, 'starr_content_hub.db')

_local = threading.local()


def _use_turso():
    """Check at call time (not import time) so Streamlit secrets are loaded."""
    return bool(os.getenv('TURSO_DB_URL', ''))


def _rows_to_dicts(cursor):
    """Convert cursor result rows to a list of dicts."""
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _row_to_dict(cursor):
    """Convert a single cursor row to a dict, or None."""
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def get_connection():
    conn = getattr(_local, 'conn', None)
    if conn is not None:
        return conn
    if _use_turso():
        try:
            import libsql_experimental as libsql
            conn = libsql.connect(
                os.getenv('TURSO_DB_URL'),
                auth_token=os.getenv('TURSO_AUTH_TOKEN', ''))
        except ImportError:
            # libsql not installed (e.g. Windows dev) — fall back to local
            import sqlite3
            os.makedirs(DB_DIR, exist_ok=True)
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
    else:
        import sqlite3
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    _local.conn = conn
    return conn


_last_sync_status = ""


def _commit(conn):
    """Commit and, for Turso connections, sync."""
    global _last_sync_status
    try:
        conn.commit()
    except (ValueError, Exception) as e:
        # Connection may be stale — reconnect and retry
        _local.conn = None
        conn = get_connection()
        conn.commit()
    if _use_turso():
        if hasattr(conn, 'sync'):
            try:
                conn.sync()
                _last_sync_status = "sync OK"
            except Exception as e:
                _last_sync_status = f"sync FAILED: {e}"
        else:
            _last_sync_status = "no sync() method on connection"
    else:
        _last_sync_status = "local sqlite (no sync needed)"


# ---------------------------------------------------------------------------
# Schema  (matches CMS Tool + Menu Organiser field names exactly)
# ---------------------------------------------------------------------------

def init_db():
    """Create all 4 tables if they don't exist."""
    conn = get_connection()
    stmts = [
        """CREATE TABLE IF NOT EXISTS restaurants (
            name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            city TEXT DEFAULT '',
            website_url TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            accent_color TEXT DEFAULT '',
            accent_light TEXT DEFAULT '',
            primary_color TEXT DEFAULT '',
            booking_platform TEXT DEFAULT '',
            opentable_rid TEXT DEFAULT '',
            resy_url TEXT DEFAULT '',
            tripleseat_form_id TEXT DEFAULT '',
            mailing_list_url TEXT DEFAULT '',
            order_online_url TEXT DEFAULT '',
            facebook_url TEXT DEFAULT '',
            instagram_url TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email_general TEXT DEFAULT '',
            email_events TEXT DEFAULT '',
            email_marketing TEXT DEFAULT '',
            email_press TEXT DEFAULT '',
            address TEXT DEFAULT '',
            google_maps_url TEXT DEFAULT '',
            onetrust_id TEXT DEFAULT '',
            wordfence_api_key TEXT DEFAULT '',
            gtm_id TEXT DEFAULT '',
            pull_data INTEGER DEFAULT 0,
            checklist TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS menus (
            restaurant TEXT PRIMARY KEY,
            menu_json TEXT NOT NULL,
            push_data INTEGER DEFAULT 0,
            menu_url TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (restaurant) REFERENCES restaurants(name) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            field_name TEXT NOT NULL,
            original_filename TEXT DEFAULT '',
            image_data BLOB,
            alt_text TEXT DEFAULT '',
            overlay_opacity INTEGER DEFAULT 40,
            FOREIGN KEY (restaurant) REFERENCES restaurants(name) ON DELETE CASCADE,
            UNIQUE(restaurant, field_name)
        )""",
        """CREATE TABLE IF NOT EXISTS copy_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            section_id TEXT NOT NULL,
            content TEXT DEFAULT '',
            FOREIGN KEY (restaurant) REFERENCES restaurants(name) ON DELETE CASCADE,
            UNIQUE(restaurant, section_id)
        )""",
    ]
    for sql in stmts:
        conn.execute(sql)
    # Migrations — add columns that may not exist in older databases
    _migrations = [
        ("restaurants", "onetrust_id", "TEXT DEFAULT ''"),
        ("restaurants", "wordfence_api_key", "TEXT DEFAULT ''"),
        ("restaurants", "gtm_id", "TEXT DEFAULT ''"),
        ("restaurants", "city", "TEXT DEFAULT ''"),
        ("restaurants", "accent_color", "TEXT DEFAULT ''"),
        ("restaurants", "accent_light", "TEXT DEFAULT ''"),
        ("menus", "push_data", "INTEGER DEFAULT 0"),
        ("menus", "menu_url", "TEXT DEFAULT ''"),
        ("restaurants", "spotify_url", "TEXT DEFAULT ''"),
        ("restaurants", "linkedin_url", "TEXT DEFAULT ''"),
        ("restaurants", "opening_hours", "TEXT DEFAULT ''"),
        ("restaurants", "feedback", "TEXT DEFAULT ''"),
        ("restaurants", "push_changes", "INTEGER DEFAULT 0"),
    ]
    for table, col, col_def in _migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except Exception:
            pass  # column already exists
    # One-time: copy notes into feedback where feedback is still empty
    try:
        conn.execute("""UPDATE restaurants SET feedback = notes
                        WHERE (feedback IS NULL OR feedback = '') AND notes != ''""")
    except Exception:
        pass
    _commit(conn)


# ---------------------------------------------------------------------------
# Slug normalization
# ---------------------------------------------------------------------------

def normalize_to_slug(name: str) -> str:
    """Convert any restaurant name variant to a canonical slug.

    'barclay prime' -> 'barclay-prime'
    'Barclay_Prime' -> 'barclay-prime'
    'Barclay Prime' -> 'barclay-prime'
    """
    import re
    slug = name.strip().lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


# ─── Restaurant CRUD ─────────────────────────────────────────────────────────

def add_restaurant(name, display_name, city='', website_url='',
                   accent_color='', accent_light=''):
    """Insert a new restaurant (ignore if name already exists)."""
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO restaurants
           (name, display_name, city, website_url, accent_color, accent_light)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, display_name, city, website_url, accent_color, accent_light)
    )
    _commit(conn)


def update_restaurant(name, **fields):
    """Generic restaurant update — pass any column names as kwargs.

    Usage: update_restaurant('barclay-prime', phone='(215) 732-7560', city='Philadelphia')
    """
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = tuple(v if v is not None else "" for v in fields.values()) + (name,)
    conn = get_connection()
    conn.execute(f"UPDATE restaurants SET {set_clause} WHERE name = ?", values)
    _commit(conn)


def get_restaurant(name):
    """Return a single restaurant as a dict, or None."""
    conn = get_connection()
    cur = conn.execute("SELECT * FROM restaurants WHERE name = ?", (name,))
    return _row_to_dict(cur)


def get_all_restaurants():
    """Return list of dicts with all restaurant columns, ordered by display_name."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM restaurants ORDER BY display_name COLLATE NOCASE"
    )
    return _rows_to_dicts(cur)


def delete_restaurant(name):
    """Delete restaurant and all associated data."""
    conn = get_connection()
    conn.execute("DELETE FROM images WHERE restaurant = ?", (name,))
    conn.execute("DELETE FROM copy_sections WHERE restaurant = ?", (name,))
    conn.execute("DELETE FROM menus WHERE restaurant = ?", (name,))
    conn.execute("DELETE FROM restaurants WHERE name = ?", (name,))
    _commit(conn)


# ─── Menu CRUD ────────────────────────────────────────────────────────────────

def save_menu(name, restaurant_model):
    """Save a Restaurant model as JSON to the menus table."""
    from datetime import datetime
    menu_json = restaurant_model.model_dump_json()
    now = datetime.utcnow().isoformat() + "Z"
    conn = get_connection()
    conn.execute("""
        INSERT INTO menus (restaurant, menu_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(restaurant) DO UPDATE SET
            menu_json = excluded.menu_json,
            updated_at = excluded.updated_at
    """, (name, menu_json, now))
    _commit(conn)


def load_menu(name):
    """Load and return a Restaurant model, or None."""
    from src.models import Restaurant
    conn = get_connection()
    cur = conn.execute(
        "SELECT menu_json FROM menus WHERE restaurant = ?", (name,)
    )
    row = _row_to_dict(cur)
    if row and row['menu_json']:
        return Restaurant.model_validate_json(row['menu_json'])
    return None


def list_menus():
    """Return list of dicts with menu metadata (no JSON blob)."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT restaurant, push_data, menu_url, updated_at FROM menus ORDER BY restaurant"
    )
    return _rows_to_dicts(cur)


def delete_menu(name):
    conn = get_connection()
    conn.execute("DELETE FROM menus WHERE restaurant = ?", (name,))
    _commit(conn)


def set_menu_url(name, url):
    conn = get_connection()
    conn.execute(
        "UPDATE menus SET menu_url = ? WHERE restaurant = ?", (url, name)
    )
    _commit(conn)


def set_push_data(name, flag):
    conn = get_connection()
    conn.execute(
        "UPDATE restaurants SET pull_data = ? WHERE name = ?", (int(flag), name)
    )
    _commit(conn)


def set_menu_push_data(name, flag):
    conn = get_connection()
    conn.execute(
        "UPDATE menus SET push_data = ? WHERE restaurant = ?", (int(flag), name)
    )
    _commit(conn)


# ─── Image CRUD ──────────────────────────────────────────────────────────────

def save_image(name, field_name, image_bytes, original_filename,
               alt_text='', overlay_opacity=40):
    """Save processed image bytes as a BLOB."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO images (restaurant, field_name, original_filename,
                            image_data, alt_text, overlay_opacity)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(restaurant, field_name) DO UPDATE SET
            original_filename = excluded.original_filename,
            image_data = excluded.image_data,
            alt_text = excluded.alt_text,
            overlay_opacity = excluded.overlay_opacity
    """, (name, field_name, original_filename, image_bytes, alt_text, overlay_opacity))
    _commit(conn)


def delete_image(name, field_name):
    conn = get_connection()
    conn.execute(
        "DELETE FROM images WHERE restaurant = ? AND field_name = ?",
        (name, field_name)
    )
    _commit(conn)


def update_alt_text(name, field_name, alt_text):
    conn = get_connection()
    conn.execute(
        "UPDATE images SET alt_text = ? WHERE restaurant = ? AND field_name = ?",
        (alt_text, name, field_name)
    )
    _commit(conn)


def update_overlay(name, field_name, overlay_opacity):
    conn = get_connection()
    conn.execute(
        "UPDATE images SET overlay_opacity = ? WHERE restaurant = ? AND field_name = ?",
        (overlay_opacity, name, field_name)
    )
    _commit(conn)


def get_images_for_restaurant(name):
    """Return dict of field_name -> metadata (no BLOB)."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT field_name, alt_text, overlay_opacity, original_filename, "
        "(CASE WHEN image_data IS NOT NULL THEN 1 ELSE 0 END) AS has_image "
        "FROM images WHERE restaurant = ?",
        (name,)
    )
    rows = _rows_to_dicts(cur)
    return {r['field_name']: r for r in rows}


def get_image_data(name, field_name):
    """Return the raw image bytes for a single field, or None."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT image_data FROM images WHERE restaurant = ? AND field_name = ?",
        (name, field_name)
    )
    row = _row_to_dict(cur)
    if row and row['image_data']:
        return bytes(row['image_data'])
    return None


def get_image_record(name, field_name):
    """Return metadata (no blob) for a single image field."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT field_name, alt_text, overlay_opacity, original_filename "
        "FROM images WHERE restaurant = ? AND field_name = ?",
        (name, field_name)
    )
    return _row_to_dict(cur)


# ─── Copy CRUD ────────────────────────────────────────────────────────────────

def save_copy_section(name, section_id, content):
    conn = get_connection()
    conn.execute("""
        INSERT INTO copy_sections (restaurant, section_id, content)
        VALUES (?, ?, ?)
        ON CONFLICT(restaurant, section_id) DO UPDATE SET content = excluded.content
    """, (name, section_id, content))
    _commit(conn)


def get_copy_for_restaurant(name):
    """Return dict of section_id -> content."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT section_id, content FROM copy_sections WHERE restaurant = ?",
        (name,)
    )
    rows = _rows_to_dicts(cur)
    return {r['section_id']: r['content'] for r in rows}


def save_all_copy(name, copy_dict):
    """Save multiple copy sections at once."""
    conn = get_connection()
    for section_id, content in copy_dict.items():
        conn.execute("""
            INSERT INTO copy_sections (restaurant, section_id, content)
            VALUES (?, ?, ?)
            ON CONFLICT(restaurant, section_id) DO UPDATE SET content = excluded.content
        """, (name, section_id, content))
    _commit(conn)


def get_all_image_counts():
    """Return dicts of restaurant -> image count and chef count (single query)."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT restaurant, field_name FROM images WHERE image_data IS NOT NULL"
    )
    rows = _rows_to_dicts(cur)
    img_counts = {}
    chef_counts = {}
    chef_fields = ('Chef_1', 'Chef_2', 'Chef_3', 'Logo', 'Favicon')
    for r in rows:
        name = r['restaurant']
        fn = r['field_name']
        if fn in ('Chef_1', 'Chef_2', 'Chef_3'):
            chef_counts[name] = chef_counts.get(name, 0) + 1
        elif fn not in ('Logo', 'Favicon'):
            img_counts[name] = img_counts.get(name, 0) + 1
    return img_counts, chef_counts


def get_all_copy_counts():
    """Return dict of restaurant -> count of non-empty copy sections (single query)."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT restaurant, COUNT(*) as cnt FROM copy_sections "
        "WHERE content != '' GROUP BY restaurant"
    )
    rows = _rows_to_dicts(cur)
    return {r['restaurant']: r['cnt'] for r in rows}
