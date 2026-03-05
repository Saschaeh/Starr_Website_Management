"""Shared CSS theming and header for Starr Content Hub."""

import streamlit as st

# Brand constants
NAVY = "#031E41"
GOLD = "#C5A258"
CREAM = "#FAFAF7"
SECONDARY_BG = "#F2F0EB"
TEXT_DARK = "#1A1A2E"
TEXT_MUTED = "#6B7280"
BORDER_LIGHT = "#DDD9D1"


def render_header():
    """Render the branded Starr header."""
    st.markdown("""
    <div class="starr-header">
        <div>
            <h1>Starr Restaurants</h1>
            <div class="starr-subtitle">Content Hub</div>
        </div>
        <div class="made-tooled">Made{<i>Tooled</i>}</div>
    </div>
    """, unsafe_allow_html=True)


def inject_css():
    """Inject the master CSS for the entire app."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@400;500;600&display=swap');

    /* === GLOBAL === */
    [data-testid="stDecoration"] { display: none !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }

    img { border-radius: 0 !important; }

    /* Give form elements white backgrounds */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [data-baseweb="select"],
    [data-testid="stNumberInput"] input {
        background-color: #FFFFFF !important;
    }

    /* === BRANDED HEADER === */
    .starr-header {
        background: linear-gradient(135deg, #031E41 0%, #0A3366 100%);
        padding: 1.5rem 2rem;
        margin: -1rem -1rem 1.5rem -1rem;
        position: relative;
        border-top: 3px solid #C5A258;
        border-bottom: 3px solid #C5A258;
    }
    .starr-header h1 {
        font-family: 'Playfair Display', Georgia, serif;
        color: #FFFFFF !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
        margin: 0 !important;
        padding: 0 !important;
    }
    .starr-header .starr-subtitle {
        font-family: 'DM Sans', sans-serif;
        color: #C5A258;
        font-size: 0.8rem;
        font-weight: 500;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-top: 0.35rem;
    }
    .starr-header .made-tooled {
        font-family: 'DM Sans', sans-serif;
        position: absolute;
        bottom: 0.5rem;
        right: 1rem;
        color: #C5A258;
        font-style: italic;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
        font-weight: 400;
    }

    /* === BUTTONS === */
    [data-testid="stButton"] > button {
        border: 1.5px solid #031E41 !important;
        color: #031E41 !important;
        background-color: transparent !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.3px;
        padding: 0.25rem 1.2rem !important;
        border-radius: 4px !important;
        transition: all 0.2s ease !important;
        min-height: 0 !important;
        line-height: 1.4 !important;
    }
    [data-testid="stButton"] > button:hover {
        background-color: #031E41 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stButton"] > button[kind="primary"] {
        background-color: #031E41 !important;
        color: #FFFFFF !important;
        border: 1.5px solid #031E41 !important;
        font-weight: 600 !important;
    }
    [data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #0A3366 !important;
        border-color: #0A3366 !important;
    }

    /* Download buttons */
    [data-testid="stDownloadButton"] > button {
        border: 1.5px solid #031E41 !important;
        color: #031E41 !important;
        background-color: transparent !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        border-radius: 4px !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background-color: #031E41 !important;
        color: #FFFFFF !important;
    }

    /* === FILE UPLOADER === */
    [data-testid="stFileUploader"] {
        border: 2px dashed #DDD9D1;
        border-radius: 12px;
        padding: 1rem;
        background: #FFFFFF;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #C5A258;
    }

    /* === NAVIGATION SIDEBAR === */
    [data-testid="stSidebar"] {
        background-color: #031E41 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #FFFFFF !important;
    }

    /* === PROGRESS PILLS === */
    .progress-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .pill-complete {
        background: #E8F5E9;
        color: #2E7D32;
    }
    .pill-partial {
        background: #FFF3E0;
        color: #EF6C00;
    }
    .pill-empty {
        background: #FAFAFA;
        color: #9E9E9E;
        border: 1px solid #E0E0E0;
    }

    /* === COPY SECTION CARDS === */
    .copy-section-card {
        background: #FFFFFF;
        border: 1px solid #E8E5DE;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.25rem;
    }
    .copy-section-card .section-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    .copy-section-card .section-label {
        font-weight: 600;
        font-size: 0.9rem;
        color: #031E41;
    }
    .copy-section-card .section-desc {
        font-size: 0.75rem;
        color: #6B7280;
        margin-top: 2px;
    }
    .word-count-badge {
        font-size: 0.7rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        white-space: nowrap;
    }
    .word-count-badge.empty { background: #F5F5F5; color: #9E9E9E; }
    .word-count-badge.in-range { background: #E8F5E9; color: #2E7D32; }
    .word-count-badge.warn { background: #FFF3E0; color: #EF6C00; }
    .word-count-badge.over { background: #FFEBEE; color: #C62828; }

    /* === RESTAURANT ROW CARDS === */
    .restaurant-row {
        background: #FFFFFF;
        border: 1px solid #E8E5DE;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .restaurant-row .color-pill {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .restaurant-row .r-name {
        font-weight: 600;
        font-size: 0.9rem;
        color: #031E41;
    }
    .restaurant-row .r-meta {
        font-size: 0.75rem;
        color: #6B7280;
    }

    /* === DASHBOARD GRID === */
    .dash-col {
        font-family: 'DM Sans', sans-serif;
    }
    .dash-col .city-label {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #031E41;
        margin: 0 0 0.3rem 0;
        padding: 0;
    }
    .dash-col .city-group {
        margin-bottom: 0.9rem;
    }
    .dash-col a.r-link {
        display: flex;
        align-items: baseline;
        gap: 0.4rem;
        text-decoration: none;
        padding: 0.08rem 0;
        line-height: 1.4;
    }
    .dash-col a.r-link:hover .r-name {
        color: #C5A258;
    }
    .dash-col .r-name {
        font-size: 0.85rem;
        font-weight: 500;
        color: #1A1A2E;
    }
    .dash-col .r-date {
        font-size: 0.7rem;
        color: #6B7280;
        white-space: nowrap;
    }
    .dash-col .upload-link {
        display: inline-block;
        margin-top: 1rem;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        font-weight: 500;
        color: #C5A258;
        text-decoration: none;
    }
    .dash-col .upload-link:hover {
        color: #031E41;
    }

    /* === IMAGE FIELD CARDS === */
    .image-field-card {
        background: #FFFFFF;
        border: 1px solid #E8E5DE;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .image-field-card .field-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #031E41;
        margin-bottom: 0.25rem;
    }
    .image-field-card .field-requirement {
        font-size: 0.78rem;
        color: #6B7280;
    }
    .field-label {
        font-weight: 600;
        font-size: 0.85rem;
        color: #031E41;
        margin-bottom: 0.25rem;
    }

    /* === TOOLBAR === */
    [class*="st-key-toolbar_"] {
        background: #E8EEF4;
        border-bottom: 1px solid #D0DAE4;
        padding: 0.4rem 0.5rem;
        margin-bottom: 0.5rem;
    }
    [class*="st-key-toolbar_"] [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
    [class*="st-key-toolbar_"] button {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.75rem !important;
        padding: 0.2rem 0.5rem !important;
        min-height: 0 !important;
    }

    /* === TABS (for menu preview) === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #1A1A2E;
        padding: 0 1rem;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #a09888;
        padding: 0.75rem 1.25rem;
        border: none;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #FFFFFF; }
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        border-bottom: 2px solid #C5A258 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding: 0; }

    /* === BACK BUTTON === */
    [class*="st-key-back_btn"],
    [class*="st-key-back_btn"] [data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        background: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    [class*="st-key-back_btn"] button {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        min-height: 0 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.85rem !important;
        color: #6B7280 !important;
    }
    [class*="st-key-back_btn"] button:hover {
        color: #C5A258 !important;
    }

    /* === STATUS WIDGET === */
    [data-testid="stStatusWidget"] {
        background: #FFFFFF;
        border: 1px solid #DDD9D1;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }

    /* === ALERT BOXES === */
    [data-testid="stAlert"] {
        background: #FFFFFF;
        border-radius: 8px;
    }

    /* === RESTAURANT LIST TABLE ROWS === */
    [class*="st-key-row_"] button {
        text-align: left !important;
        justify-content: flex-start !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 0.25rem 0 !important;
        border-radius: 0 !important;
        border: none !important;
        background: transparent !important;
        color: #031E41 !important;
        min-height: 0 !important;
    }
    [class*="st-key-row_"] button:hover {
        background: none !important;
        color: #C5A258 !important;
    }

    /* Vertically center columns in restaurant rows */
    [data-testid="stHorizontalBlock"] [data-testid="stColumn"] [data-testid="stMarkdown"] {
        display: flex;
        align-items: center;
        min-height: 38px;
    }

    /* Edit + Delete + Add buttons — subtle, matching dropdown height */
    [class*="st-key-edit_btn"] button,
    [class*="st-key-del_btn"] button,
    [class*="st-key-add_btn"] button {
        background: transparent !important;
        border: 1px solid #DDD9D1 !important;
        color: #6B7280 !important;
        font-weight: 400 !important;
        font-size: 0.78rem !important;
        height: 36px !important;
        min-height: 36px !important;
        width: 130px !important;
        min-width: 130px !important;
        max-width: 130px !important;
        white-space: nowrap !important;
        padding: 0 0.75rem !important;
        border-radius: 4px !important;
    }
    [class*="st-key-edit_btn"] button:hover,
    [class*="st-key-del_btn"] button:hover,
    [class*="st-key-add_btn"] button:hover {
        border-color: #031E41 !important;
        color: #031E41 !important;
        background: transparent !important;
    }

    /* Back button in detail view */
    [class*="st-key-detail_back"] button,
    [class*="st-key-add_back"] button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        min-height: 0 !important;
        font-size: 0.85rem !important;
        color: #6B7280 !important;
        font-weight: 500 !important;
    }
    [class*="st-key-detail_back"] button:hover,
    [class*="st-key-add_back"] button:hover {
        color: #C5A258 !important;
        background: none !important;
    }

    /* Image tab action buttons — same style as Edit/Delete/Add */
    [class*="st-key-imgbtn_"] button {
        background: transparent !important;
        border: 1px solid #DDD9D1 !important;
        color: #6B7280 !important;
        font-weight: 400 !important;
        font-size: 0.78rem !important;
        height: 36px !important;
        min-height: 36px !important;
        width: 130px !important;
        min-width: 130px !important;
        max-width: 130px !important;
        white-space: nowrap !important;
        padding: 0 0.75rem !important;
        border-radius: 4px !important;
    }
    [class*="st-key-imgbtn_"] button:hover {
        border-color: #031E41 !important;
        color: #031E41 !important;
        background: transparent !important;
    }

    /* Widen the main content area */
    .block-container {
        max-width: 1400px !important;
    }
    </style>
    """, unsafe_allow_html=True)
