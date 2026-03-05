"""Push local SQLite data to Turso (HTTP API via libsql_client)."""

import asyncio
import base64
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import libsql_client

TURSO_DB_URL = os.getenv('TURSO_DB_URL')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN')
LOCAL_DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'starr_content_hub.db')


async def main():
    print(f"Local DB: {LOCAL_DB}")
    print(f"Turso URL: {TURSO_DB_URL}")

    # Connect to local SQLite
    local = sqlite3.connect(LOCAL_DB)
    local.row_factory = sqlite3.Row

    # Connect to Turso
    url = TURSO_DB_URL.replace('libsql://', 'https://')
    async with libsql_client.create_client(url=url, auth_token=TURSO_AUTH_TOKEN) as client:

        # 1. Create tables
        print("\n=== Creating tables ===")
        await client.execute("""CREATE TABLE IF NOT EXISTS restaurants (
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
            pull_data INTEGER DEFAULT 0,
            checklist TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        print("  restaurants: OK")

        await client.execute("""CREATE TABLE IF NOT EXISTS menus (
            restaurant TEXT PRIMARY KEY,
            menu_json TEXT NOT NULL,
            push_data INTEGER DEFAULT 0,
            menu_url TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (restaurant) REFERENCES restaurants(name) ON DELETE CASCADE
        )""")
        print("  menus: OK")

        await client.execute("""CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            field_name TEXT NOT NULL,
            original_filename TEXT DEFAULT '',
            image_data BLOB,
            alt_text TEXT DEFAULT '',
            overlay_opacity INTEGER DEFAULT 40,
            FOREIGN KEY (restaurant) REFERENCES restaurants(name) ON DELETE CASCADE,
            UNIQUE(restaurant, field_name)
        )""")
        print("  images: OK")

        await client.execute("""CREATE TABLE IF NOT EXISTS copy_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            section_id TEXT NOT NULL,
            content TEXT DEFAULT '',
            FOREIGN KEY (restaurant) REFERENCES restaurants(name) ON DELETE CASCADE,
            UNIQUE(restaurant, section_id)
        )""")
        print("  copy_sections: OK")

        # 2. Push restaurants
        print("\n=== Pushing restaurants ===")
        rows = local.execute("SELECT * FROM restaurants").fetchall()
        cols = [d[0] for d in local.execute("SELECT * FROM restaurants").description]
        for r in rows:
            vals = [r[c] for c in cols]
            placeholders = ', '.join(['?'] * len(cols))
            col_names = ', '.join(cols)
            await client.execute(
                f"INSERT OR REPLACE INTO restaurants ({col_names}) VALUES ({placeholders})",
                vals
            )
        print(f"  {len(rows)} restaurants pushed")

        # 3. Push menus
        print("\n=== Pushing menus ===")
        rows = local.execute("SELECT * FROM menus").fetchall()
        cols = [d[0] for d in local.execute("SELECT * FROM menus").description]
        for r in rows:
            vals = [r[c] for c in cols]
            placeholders = ', '.join(['?'] * len(cols))
            col_names = ', '.join(cols)
            await client.execute(
                f"INSERT OR REPLACE INTO menus ({col_names}) VALUES ({placeholders})",
                vals
            )
        print(f"  {len(rows)} menus pushed")

        # 4. Push copy sections
        print("\n=== Pushing copy sections ===")
        rows = local.execute("SELECT restaurant, section_id, content FROM copy_sections").fetchall()
        for r in rows:
            await client.execute(
                "INSERT OR REPLACE INTO copy_sections (restaurant, section_id, content) VALUES (?, ?, ?)",
                [r[0], r[1], r[2]]
            )
        print(f"  {len(rows)} copy sections pushed")

        # 5. Push images (BLOBs as base64)
        print("\n=== Pushing images ===")
        rows = local.execute(
            "SELECT restaurant, field_name, original_filename, image_data, alt_text, overlay_opacity FROM images"
        ).fetchall()
        for i, r in enumerate(rows):
            restaurant, field_name, orig_fn, img_data, alt_text, overlay = r
            # libsql_client handles bytes directly
            await client.execute(
                """INSERT OR REPLACE INTO images
                   (restaurant, field_name, original_filename, image_data, alt_text, overlay_opacity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [restaurant, field_name, orig_fn or '', img_data, alt_text or '', overlay or 40]
            )
            if (i + 1) % 20 == 0 or i == len(rows) - 1:
                print(f"  {i + 1}/{len(rows)} images pushed")

        # 6. Verify
        print("\n=== Verifying ===")
        rs = await client.execute("SELECT COUNT(*) FROM restaurants")
        print(f"  Restaurants: {rs.rows[0][0]}")
        rs = await client.execute("SELECT COUNT(*) FROM menus")
        print(f"  Menus: {rs.rows[0][0]}")
        rs = await client.execute("SELECT COUNT(*) FROM images")
        print(f"  Images: {rs.rows[0][0]}")
        rs = await client.execute("SELECT COUNT(*) FROM copy_sections")
        print(f"  Copy sections: {rs.rows[0][0]}")

    local.close()
    print("\nDone! All data pushed to Turso.")


if __name__ == '__main__':
    asyncio.run(main())
