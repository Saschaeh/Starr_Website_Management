"""Website scraping and brand/metadata detection."""

import re
from collections import Counter
from urllib.parse import urlparse, urljoin

import requests
import streamlit as st
from bs4 import BeautifulSoup

# Subpage path keywords
_SUBPAGE_KEYWORDS = [
    'about', 'concept', 'story', 'menu', 'cuisine', 'food',
    'group', 'private', 'dining', 'event', 'party', 'parties',
    'reserve', 'reservation', 'chef',
]

_COMMON_SUBPATHS = [
    '/about/', '/about-us/', '/group-dining/', '/private-dining/',
    '/private-events/', '/menu/', '/events/', '/the-cuisine/',
    '/the-concept/', '/chef/',
]


def _fetch_page_text(url, headers):
    """Fetch a single page and return (cleaned_text, raw_bytes)."""
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except Exception:
        return "", b""
    raw = response.content
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    content = soup.find('main') or soup.find('article') or soup.find('body')
    if not content:
        return "", raw
    text = content.get_text(separator=' ', strip=True)
    return re.sub(r'\s+', ' ', text).strip(), raw


def _extract_favicon_url(soup, base_url):
    """Extract the site favicon/icon URL."""
    for link in soup.find_all('link', rel=True):
        rels = [r.lower() for r in link['rel']]
        if 'apple-touch-icon' in rels and link.get('href'):
            return urljoin(base_url, link['href'])

    best_url = ""
    best_size = 0
    for link in soup.find_all('link', rel=True):
        rels = [r.lower() for r in link['rel']]
        if 'icon' in rels and link.get('href'):
            sizes = link.get('sizes', '')
            size = 0
            if sizes:
                try:
                    size = int(sizes.split('x')[0])
                except (ValueError, IndexError):
                    pass
            if size > best_size:
                best_size = size
                best_url = urljoin(base_url, link['href'])
            elif not best_url:
                best_url = urljoin(base_url, link['href'])

    if best_url:
        return best_url
    return urljoin(base_url, '/favicon.ico')


def _extract_logo_url(soup, base_url):
    """Extract the logo image URL."""
    def _has_logo_hint(tag):
        classes = ' '.join(tag.get('class', []))
        tag_id = tag.get('id', '')
        alt = tag.get('alt', '')
        return 'logo' in classes.lower() or 'logo' in tag_id.lower() or 'logo' in alt.lower()

    for img in soup.find_all('img', src=True):
        classes = ' '.join(img.get('class', [])).lower()
        if 'custom-logo' in classes or 'site-logo' in classes:
            return urljoin(base_url, img['src'])

    for container in soup.find_all(['header', 'nav']):
        for img in container.find_all('img', src=True):
            if _has_logo_hint(img):
                return urljoin(base_url, img['src'])

    for img in soup.find_all('img', src=True):
        if _has_logo_hint(img):
            return urljoin(base_url, img['src'])

    for link in soup.find_all('link', rel=True):
        rels = [r.lower() for r in link['rel']]
        if 'icon' in rels and link.get('href'):
            sizes = link.get('sizes', '')
            if sizes:
                try:
                    w = int(sizes.split('x')[0])
                    if w < 100:
                        continue
                except (ValueError, IndexError):
                    pass
            return urljoin(base_url, link['href'])
    return ""


def _extract_primary_color(soup, base_url):
    """Extract the likely primary brand color."""
    meta_theme = soup.find('meta', attrs={'name': 'theme-color'})
    if meta_theme and meta_theme.get('content'):
        val = meta_theme['content'].strip()
        if re.match(r'^#[0-9a-fA-F]{3,8}$', val):
            return val[:7]

    def _normalize_hex(h):
        if len(h) == 3:
            return (h[0]*2 + h[1]*2 + h[2]*2).lower()
        return h.lower()

    def _is_neutral(h):
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return max(r, g, b) - min(r, g, b) < 30

    def _extract_colors(css_text):
        hex6 = re.findall(r'#([0-9a-fA-F]{6})\b', css_text)
        hex3 = re.findall(r'#([0-9a-fA-F]{3})\b', css_text)
        all_c = [_normalize_hex(c) for c in hex6 + hex3]
        return [c for c in all_c if not _is_neutral(c)]

    inline_parts = []
    for style_tag in soup.find_all('style'):
        if style_tag.string:
            inline_parts.append(style_tag.string)
    for tag in soup.find_all(style=True):
        inline_parts.append(tag['style'])
    inline_css = '\n'.join(inline_parts)

    var_pattern = re.compile(
        r'--[a-zA-Z0-9_-]*(?:primary|brand|accent|main)[a-zA-Z0-9_-]*\s*:\s*(#[0-9a-fA-F]{3,8})\b',
        re.IGNORECASE,
    )
    var_match = var_pattern.search(inline_css)
    if var_match:
        val = var_match.group(1)
        if len(val) == 4:
            val = '#' + val[1]*2 + val[2]*2 + val[3]*2
        return val[:7]

    inline_colors = _extract_colors(inline_css)
    if inline_colors:
        top = Counter(inline_colors).most_common(1)[0]
        if top[1] >= 3:
            return '#' + top[0]

    skip_domains = ('fonts.googleapis.com', 'use.typekit.net', 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    external_parts = []
    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href', '')
        if not href or any(d in href for d in skip_domains):
            continue
        full_url = urljoin(base_url, href)
        try:
            css_resp = requests.get(full_url, headers=headers, timeout=5, stream=True)
            if css_resp.ok:
                css_text = css_resp.text[:500_000]
                external_parts.append(css_text)
        except Exception:
            pass

    external_css = '\n'.join(external_parts)

    var_match = var_pattern.search(external_css)
    if var_match:
        val = var_match.group(1)
        if len(val) == 4:
            val = '#' + val[1]*2 + val[2]*2 + val[3]*2
        return val[:7]

    all_colors = inline_colors * 3 + _extract_colors(external_css)
    if all_colors:
        return '#' + Counter(all_colors).most_common(1)[0][0]

    return ""


def _detect_site_metadata(html_bytes):
    """Extract booking, social, contact, and address metadata from raw HTML."""
    html_str = html_bytes.decode('utf-8', errors='ignore')
    html_lower = html_str.lower()

    result = {
        'booking': '', 'opentable_rid': '', 'tripleseat_form_id': '',
        'resy_url': '', 'mailing_list_url': '',
        'facebook_url': '', 'instagram_url': '',
        'phone': '', 'email_general': '', 'email_events': '',
        'email_marketing': '', 'email_press': '',
        'address': '', 'google_maps_url': '',
        'order_online_url': '',
        'spotify_url': '',
        'linkedin_url': '',
    }

    # Booking platform
    if any(m in html_lower for m in ('widgets.resy.com', 'resywidget', 'resy.com/cities/')):
        result['booking'] = "Resy"
        resy_match = re.search(r'https?://resy\.com/cities/[a-z0-9-]+/venues/[a-z0-9-]+', html_str, re.IGNORECASE)
        if not resy_match:
            resy_match = re.search(r'resy\.com/cities/([a-z0-9-]+)/([a-z0-9-]+)', html_str, re.IGNORECASE)
            if resy_match:
                result['resy_url'] = f"https://resy.com/cities/{resy_match.group(1)}/{resy_match.group(2)}"
        if resy_match and not result['resy_url']:
            result['resy_url'] = resy_match.group(0)
    elif any(m in html_lower for m in ('opentable.com/widget', 'opentable.com/r/', 'opentable.com/restref', 'ot-dtp-picker')):
        result['booking'] = "OpenTable"
        rid_match = re.search(r'opentable\.com[^"\']*[?&]rid=\s*(\d+)', html_str, re.IGNORECASE)
        result['opentable_rid'] = rid_match.group(1) if rid_match else ""

    # Tripleseat
    if 'tripleseat.com' in html_lower:
        ts_match = re.search(r'lead_form_id=(\d+)', html_str)
        result['tripleseat_form_id'] = ts_match.group(1) if ts_match else ""

    # Mailing list
    _mail_soup = BeautifulSoup(html_bytes, 'html.parser')
    _mail_keywords = ('mailing list', 'subscribe', 'newsletter', 'sign up for')
    for a_tag in _mail_soup.find_all('a', href=True):
        link_text = a_tag.get_text(strip=True).lower()
        if any(kw in link_text for kw in _mail_keywords):
            href = a_tag['href'].strip()
            if href and href.startswith('http'):
                result['mailing_list_url'] = href.rstrip('/')
                break
    if not result['mailing_list_url']:
        mail_match = re.search(
            r'https?://(?:[a-z0-9.-]+\.e2ma\.net/[^\s"\'<>]*|[a-z0-9.-]+\.list-manage\.com/subscribe[^\s"\'<>]*|[a-z0-9.-]+\.createsend\.com/[^\s"\'<>]*|mailchi\.mp/[^\s"\'<>]*)',
            html_str, re.IGNORECASE
        )
        if mail_match:
            result['mailing_list_url'] = mail_match.group(0).rstrip('/')

    # Order online
    order_match = re.search(
        r'href=["\']?(https?://order\.online/[^\s"\'<>]+)["\']?',
        html_str, re.IGNORECASE
    )
    if order_match:
        result['order_online_url'] = order_match.group(1).rstrip('/')

    # Social media
    fb_match = re.search(r'href=["\']https?://(?:www\.)?facebook\.com/([^"\']+)["\']', html_str, re.IGNORECASE)
    if fb_match:
        slug = fb_match.group(1).rstrip('/')
        if slug.lower() not in ('starrrestaurants', 'starr-restaurants', 'starr.restaurants'):
            result['facebook_url'] = f"https://www.facebook.com/{slug}"

    ig_match = re.search(r'href=["\']https?://(?:www\.)?instagram\.com/([^"\']+)["\']', html_str, re.IGNORECASE)
    if ig_match:
        slug = ig_match.group(1).rstrip('/')
        if slug.lower() not in ('starrrestaurants', 'starr_restaurants', 'starr.restaurants'):
            result['instagram_url'] = f"https://www.instagram.com/{slug}"

    # Spotify
    sp_match = re.search(r"href=[\"\x27]https?://open\.spotify\.com/([^\"\x27]+)[\"\x27]", html_str, re.IGNORECASE)
    if sp_match:
        result['spotify_url'] = "https://open.spotify.com/" + sp_match.group(1).rstrip('/')

    # LinkedIn
    li_match = re.search(r"href=[\"\x27]https?://(?:www\.)?linkedin\.com/(?:company|in)/([^\"\x27]+)[\"\x27]", html_str, re.IGNORECASE)
    if li_match:
        result['linkedin_url'] = "https://www.linkedin.com/company/" + li_match.group(1).rstrip('/')

    # Phone
    tel_match = re.search(r'href=["\']tel:([^"\']+)["\']', html_str, re.IGNORECASE)
    if tel_match:
        raw = re.sub(r'[^\d]', '', tel_match.group(1))
        if len(raw) == 11 and raw.startswith('1'):
            raw = raw[1:]
        if len(raw) == 10:
            result['phone'] = f"({raw[:3]}) {raw[3:6]}-{raw[6:]}"
    if not result['phone']:
        aria_match = re.search(r'(?:aria-label|title)="[^"]*?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', html_str)
        if aria_match:
            raw = re.sub(r'[^\d]', '', aria_match.group(1))
            if len(raw) == 10:
                result['phone'] = f"({raw[:3]}) {raw[3:6]}-{raw[6:]}"
    if not result['phone']:
        phone_block = re.search(r'PHONE:.*?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', html_str, re.IGNORECASE | re.DOTALL)
        if phone_block:
            raw = re.sub(r'[^\d]', '', phone_block.group(1))
            if len(raw) == 10:
                result['phone'] = f"({raw[:3]}) {raw[3:6]}-{raw[6:]}"

    # Emails
    emails = re.findall(r'([a-z0-9._-]+\.(?:info|events|marketing|press)@starr-restaurants\.com)', html_str, re.IGNORECASE)
    for email in emails:
        lower = email.lower()
        if '.info@' in lower and not result['email_general']:
            result['email_general'] = email
        elif '.events@' in lower and not result['email_events']:
            result['email_events'] = email
        elif '.marketing@' in lower and not result['email_marketing']:
            result['email_marketing'] = email
        elif '.press@' in lower and not result['email_press']:
            result['email_press'] = email

    # Address + Google Maps
    soup = BeautifulSoup(html_str, 'html.parser')
    maps_link = soup.find('a', href=re.compile(r'google\.com/maps/place/', re.IGNORECASE))
    if maps_link:
        result['google_maps_url'] = maps_link['href']
        addr_text = maps_link.get_text(separator=', ').strip()
        if addr_text:
            result['address'] = addr_text

    return result


def _search_opentable_rid(restaurant_display_name):
    """Search OpenTable.com for a restaurant and return its numeric RID."""
    try:
        query = restaurant_display_name.replace('_', ' ')
        search_url = f"https://www.opentable.com/s?term={requests.utils.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        rid_match = re.search(r'"restaurantId"\s*:\s*(\d+)', resp.text)
        return rid_match.group(1) if rid_match else ""
    except Exception:
        return ""


def _search_resy_url(restaurant_display_name):
    """Search Google for a restaurant on Resy and return the venue URL."""
    try:
        query = restaurant_display_name.replace('_', ' ')
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query + ' starr site:resy.com')}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        resy_match = re.search(
            r'https?://resy\.com/cities/([a-z0-9-]+)/([a-z0-9-]+)(?:\?[^"&\s]*)?',
            resp.text, re.IGNORECASE,
        )
        if resy_match:
            city = resy_match.group(1)
            venue = resy_match.group(2)
            if venue not in ('', 'new', 'trending', 'best'):
                return f"https://resy.com/cities/{city}/{venue}"
        return ""
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def scrape_website(url):
    """Scrape text content from a restaurant website and key subpages.

    Returns (ok, text, error, detected) where detected is a dict with keys:
    primary_color, logo_url, favicon_url, booking, opentable_rid,
    tripleseat_form_id, resy_url, mailing_list_url, facebook_url,
    instagram_url, phone, email_general, email_events, email_marketing,
    email_press, address, google_maps_url.
    """
    empty = {}
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return False, "", "Website took too long to respond. Please try again.", empty
    except requests.exceptions.ConnectionError:
        return False, "", "Could not connect to website. Please check the URL.", empty
    except requests.exceptions.HTTPError as e:
        return False, "", f"Website returned error {e.response.status_code}. Please verify the URL.", empty
    except Exception:
        return False, "", "Could not fetch website. Please check the URL and try again.", empty

    soup = BeautifulSoup(response.content, 'html.parser')
    parsed_base = urlparse(response.url)
    base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
    detected = _detect_site_metadata(response.content)
    detected['primary_color'] = _extract_primary_color(soup, base_url)
    detected['logo_url'] = _extract_logo_url(soup, base_url)
    detected['favicon_url'] = _extract_favicon_url(soup, base_url)
    base_domain = parsed_base.netloc

    subpage_urls = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(response.url, href)
        parsed = urlparse(full_url)
        if parsed.netloc != base_domain:
            continue
        path_lower = parsed.path.lower().strip('/')
        if path_lower and any(kw in path_lower for kw in _SUBPAGE_KEYWORDS):
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            subpage_urls.add(clean_url)

    for subpath in _COMMON_SUBPATHS:
        subpage_urls.add(base_url + subpath)

    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    content = soup.find('main') or soup.find('article') or soup.find('body')
    main_text = ""
    if content:
        main_text = content.get_text(separator=' ', strip=True)
        main_text = re.sub(r'\s+', ' ', main_text).strip()

    subpage_parts = []
    for sub_url in sorted(subpage_urls)[:10]:
        page_text, raw_html = _fetch_page_text(sub_url, headers)
        if raw_html:
            sub_meta = _detect_site_metadata(raw_html)
            for key, val in sub_meta.items():
                if val and not detected.get(key):
                    detected[key] = val
        if page_text and len(page_text) > 30:
            path_label = urlparse(sub_url).path.strip('/').upper().replace('-', ' ')
            subpage_parts.append(f"[{path_label}]\n{page_text}")

    all_text_parts = subpage_parts
    if main_text:
        all_text_parts.append(f"[HOME PAGE]\n{main_text}")

    combined_text = "\n\n".join(all_text_parts)

    if len(combined_text) < 50:
        return False, "", "Website had very little text content.", empty

    return True, combined_text[:8000], "", detected
