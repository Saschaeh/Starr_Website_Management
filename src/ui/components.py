"""Reusable UI helpers — copy buttons, copy section cards."""

import base64

import streamlit as st
import streamlit.components.v1 as components


def copy_button(text, key):
    """Render a click-to-copy button using HTML/JS in an iframe."""
    b64 = base64.b64encode(text.encode()).decode()
    components.html(f"""
    <button id="btn_{key}" onclick="
        var text = atob('{b64}');
        navigator.clipboard.writeText(text).then(function() {{
            document.getElementById('btn_{key}').innerText = 'Copied!';
            document.getElementById('btn_{key}').style.background = '#2D7D46';
            document.getElementById('btn_{key}').style.borderColor = '#2D7D46';
            document.getElementById('btn_{key}').style.color = '#FFFFFF';
            setTimeout(function() {{
                document.getElementById('btn_{key}').innerText = 'Copy';
                document.getElementById('btn_{key}').style.background = 'transparent';
                document.getElementById('btn_{key}').style.borderColor = '#031E41';
                document.getElementById('btn_{key}').style.color = '#031E41';
            }}, 1500);
        }});
    " style="
        background: transparent; color: #031E41; border: 1.5px solid #031E41;
        padding: 0.4rem 1.2rem; border-radius: 4px; cursor: pointer; font-size: 0.85rem;
        font-weight: 500; letter-spacing: 0.3px; transition: all 0.2s ease;
        font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, sans-serif;
        line-height: 1.6;
    "
    onmouseover="if(this.innerText==='Copy'){{this.style.background='#031E41';this.style.color='#FFFFFF';}}"
    onmouseout="if(this.innerText==='Copy'){{this.style.background='transparent';this.style.color='#031E41';}}"
    >Copy</button>
    """, height=50)


def render_copy_section(restaurant_slug, section_id, section_label,
                        word_min, word_max, description, height=120):
    """Render a copy section card with word count badge, text area, and copy button."""
    section_key = f"{restaurant_slug}_copy_{section_id}"
    if section_key not in st.session_state:
        st.session_state[section_key] = ""

    text = st.session_state[section_key]
    word_count = len(text.split()) if text.strip() else 0
    if word_count == 0:
        badge_class = "empty"
    elif word_min <= word_count <= word_max:
        badge_class = "in-range"
    elif word_count > word_max * 1.2:
        badge_class = "over"
    else:
        badge_class = "warn"

    st.markdown(f"""
    <div class="copy-section-card">
        <div class="section-header">
            <div>
                <div class="section-label">{section_label}</div>
                <div class="section-desc">{description}</div>
            </div>
            <span class="word-count-badge {badge_class}">{word_count} / {word_min}-{word_max} words</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    widget_key = f"_w_{section_key}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = text
    new_text = st.text_area(
        f"Edit {section_label}",
        value=text,
        key=widget_key,
        height=height,
        placeholder="No content generated yet. Click 'Generate Copy' above to create content.",
        label_visibility="collapsed"
    )
    st.session_state[section_key] = new_text

    if new_text.strip():
        copy_button(new_text, f"copy_{section_id}")

    st.markdown("---")
