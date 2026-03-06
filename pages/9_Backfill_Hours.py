"""One-off: scrape opening hours for all restaurants and update Turso DB.

Temporarily copy to pages/ folder, run via Streamlit Cloud, then remove.
"""

import re
import os
import requests
from bs4 import BeautifulSoup
import streamlit as st

# Load secrets into env
try:
    if hasattr(st, 'secrets'):
        for key in ('TURSO_DB_URL', 'TURSO_AUTH_TOKEN'):
            if key in st.secrets and key not in os.environ:
                os.environ[key] = st.secrets[key]
except Exception:
    pass

from src import db


def _detect_hours(html_bytes):
    html_str = html_bytes.decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html_str, 'html.parser')
    day_re = re.compile(r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)', re.IGNORECASE)
    time_re = re.compile(r'[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)', re.IGNORECASE)
    for tag in soup.find_all(['p', 'li', 'span']):
        inner_html = str(tag)
        plain = re.sub(r'<[^>]+>', '', inner_html)
        if len(plain) > 500 or len(plain) < 10:
            continue
        if day_re.search(plain) and time_re.search(plain):
            parts = re.split(r'<br\s*/?>', inner_html, flags=re.IGNORECASE)
            lines = [re.sub(r'<[^>]+>', '', p).strip() for p in parts]
            lines = [ln for ln in lines if ln]
            cleaned = []
            for ln in lines:
                ln = re.sub(r'(?<=\w)\s*[-–—]\s*(?=\w)', chr(8211), ln)
                cleaned.append(ln)
            sep = chr(92) + 'n'
            return sep.join(cleaned)
    return ''


def _scrape_hours(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return ''
    hours = _detect_hours(resp.content)
    if hours:
        return hours
    for path in ['/contact/', '/about/', '/hours/']:
        try:
            r = requests.get(url.rstrip('/') + path, headers=headers, timeout=5)
            if r.ok:
                hours = _detect_hours(r.content)
                if hours:
                    return hours
        except Exception:
            pass
    return ''


st.set_page_config(page_title='Backfill Hours', layout='wide')
st.title('Backfill Opening Hours')
st.caption('Scrapes all restaurant websites and updates opening_hours in Turso.')

if st.button('Run Backfill', type='primary'):
    db.init_db()
    restaurants = db.get_all_restaurants()
    progress = st.progress(0, text='Starting...')
    results = []
    total = len(restaurants)

    for i, r in enumerate(restaurants):
        slug = r['name']
        url = r.get('website_url', '')
        existing = r.get('opening_hours', '')
        progress.progress((i + 1) / total, text=f'Scraping {slug}...')

        if not url:
            results.append((slug, 'SKIP', 'no URL'))
            continue
        if existing:
            results.append((slug, 'SKIP', f'already set'))
            continue

        hours = _scrape_hours(url)
        if hours:
            db.update_restaurant(slug, opening_hours=hours)
            results.append((slug, 'OK', hours.replace(chr(92) + 'n', ' | ')))
        else:
            results.append((slug, 'NONE', f'not found on {url}'))

    progress.empty()
    ok = sum(1 for _, s, _ in results if s == 'OK')
    skip = sum(1 for _, s, _ in results if s == 'SKIP')
    none_ = sum(1 for _, s, _ in results if s == 'NONE')
    st.success(f'Done! Updated: {ok}, Skipped: {skip}, Not found: {none_}')

    for slug, status, detail in results:
        if status == 'OK':
            st.markdown(f'**{slug}**: {detail}')
        elif status == 'NONE':
            st.warning(f'**{slug}**: {detail}')
        else:
            st.caption(f'{slug}: {detail}')
