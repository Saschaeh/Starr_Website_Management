"""DB-driven restaurant registry — replaces hardcoded restaurant_config.py."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.db import get_all_restaurants, get_restaurant, add_restaurant, normalize_to_slug


# ---------------------------------------------------------------------------
# City mapping (seeded from Menu Organiser's restaurant_config.py)
# ---------------------------------------------------------------------------

CITY_ORDER = ["New York", "Philadelphia", "Florida", "Nashville", "Washington D.C."]

RESTAURANT_CITIES = {
    # New York
    "borromini-new": "New York",
    "buddakan-nyc": "New York",
    "el-vez-nyc": "New York",
    "electric-lemon": "New York",
    "lecafe-menu": "New York",
    "le-coucou": "New York",
    "lmno": "New York",
    "pastis-nyc": "New York",
    "the-clocktower": "New York",
    "upland": "New York",
    # Philadelphia
    "barclay-prime": "Philadelphia",
    "buddakan-pa": "Philadelphia",
    "butcher-and-singer": "Philadelphia",
    "the-continental-mid-town": "Philadelphia",
    "el-rey": "Philadelphia",
    "el-vez-philadelphia": "Philadelphia",
    "fette-sau": "Philadelphia",
    "frankford-hall": "Philadelphia",
    "morimoto": "Philadelphia",
    "parc": "Philadelphia",
    "pizzeria-stella": "Philadelphia",
    "talulas-garden": "Philadelphia",
    "talulas-daily": "Philadelphia",
    "the-dandelion": "Philadelphia",
    "the-love": "Philadelphia",
    # Florida
    "el-vez-ft-lauderdale": "Florida",
    "makoto": "Florida",
    "osteria-mozza": "Florida",
    "pastis-wynwood": "Florida",
    "pastis-miami": "Florida",
    "steak-954": "Florida",
    # Nashville
    "pastis-nashville": "Nashville",
    # Washington D.C.
    "le-diplomate": "Washington D.C.",
    "pastis-dc": "Washington D.C.",
    "st-anselm": "Washington D.C.",
    "the-occidental": "Washington D.C.",
}

# Known accent colors (from Menu Organiser's restaurant_config.py)
ACCENT_COLORS = {
    "makoto": ("#c8102e", "#fef2f2"),
    "barclay-prime": ("#1a1a2e", "#f0f0f5"),
    "buddakan-nyc": ("#8b0000", "#fdf2f2"),
    "le-coucou": ("#2c5f2d", "#f2f7f2"),
    "clocktower": ("#6b4226", "#faf5f0"),
    "el-vez-fl": ("#d4a017", "#fefbf0"),
}

# Words that should stay uppercase in display names
_UPPERCASE_WORDS = {"nyc", "dc", "pa", "lmno", "fl"}
_LOWERCASE_WORDS = {"and", "of", "the", "in", "at", "by", "for", "or", "on", "to"}


def display_name(name: str) -> str:
    """Convert a slug or raw name to a clean display name."""
    name = name.replace("-", " ").replace("_", " ").strip()
    parts = []
    for i, word in enumerate(name.split()):
        lower = word.lower()
        if lower in _UPPERCASE_WORDS:
            parts.append(word.upper())
        elif i > 0 and lower in _LOWERCASE_WORDS:
            parts.append(lower)
        else:
            parts.append(word.capitalize())
    return " ".join(parts)


def get_city(slug: str) -> str:
    """Return the city for a restaurant slug, or 'Other'."""
    return RESTAURANT_CITIES.get(slug, "Other")


def list_restaurants():
    """Return all restaurants from DB."""
    return get_all_restaurants()


def list_by_city():
    """Return restaurants grouped by city (ordered)."""
    restaurants = get_all_restaurants()
    groups = {}
    for r in restaurants:
        city = r.get('city') or get_city(r['name'])
        groups.setdefault(city, []).append(r)

    ordered = []
    for city in CITY_ORDER:
        if city in groups:
            ordered.append((city, groups.pop(city)))
    if "Other" in groups:
        ordered.append(("Other", groups.pop("Other")))
    for city, rests in sorted(groups.items()):
        ordered.append((city, rests))
    return ordered


def detect_restaurant(filename: str, text: str):
    """Detect restaurant from filename or document content.

    Returns (slug, display_name, accent_color, accent_light).
    """
    name_base = re.sub(r"\.(docx?|pdf)$", "", filename, flags=re.IGNORECASE).strip()
    slug = normalize_to_slug(name_base)

    # Try to find accent colors from known configs
    accent_color = "#c8102e"
    accent_light = "#fef2f2"

    for key, (ac, al) in ACCENT_COLORS.items():
        if key in slug or slug in key:
            accent_color = ac
            accent_light = al
            break

    dname = display_name(name_base)
    return slug, dname, accent_color, accent_light


def ensure_restaurant(slug, dname=None, city=None,
                      accent_color='', accent_light=''):
    """Ensure a restaurant exists in the DB. Create if missing."""
    existing = get_restaurant(slug)
    if existing:
        return existing
    if not dname:
        dname = display_name(slug)
    if not city:
        city = get_city(slug)
    add_restaurant(slug, dname, city=city,
                   accent_color=accent_color, accent_light=accent_light)
    return get_restaurant(slug)
