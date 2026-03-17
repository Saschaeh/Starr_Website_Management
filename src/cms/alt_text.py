"""Alt text generation using Anthropic Claude API."""

import base64
import io
import os

import streamlit as st
import anthropic


def _get_api_key():
    """Get Anthropic API key from secrets or env."""
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        key = None
    if not key:
        key = os.getenv("ANTHROPIC_API_KEY", "")
    return key


def generate_alt_text(pil_image):
    """Generate ADA-compliant alt text from a PIL image.

    Uses Claude vision via Anthropic API.
    Returns the alt text string, or None on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        st.warning("Alt text generation unavailable: ANTHROPIC_API_KEY not configured.")
        return None

    img_buffer = io.BytesIO()
    if pil_image.mode in ('RGBA', 'LA', 'PA', 'P'):
        pil_image = pil_image.convert('RGB')
    pil_image.save(img_buffer, format='JPEG', quality=85)
    img_b64 = base64.b64encode(img_buffer.getvalue()).decode()

    try:
        client = anthropic.Anthropic(api_key=api_key)
        result = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_b64,
                    }},
                    {"type": "text", "text": (
                        "Write a concise, descriptive alt text for this image suitable for "
                        "ADA/WCAG compliance on a restaurant website. Focus on what is visually "
                        "depicted. Return only the alt text, no quotes or extra formatting. "
                        "Keep it under 125 characters."
                    )}
                ]
            }],
        )
        return result.content[0].text.strip()
    except anthropic.AuthenticationError:
        st.warning("Alt text generation failed: Invalid Anthropic API key.")
        return None
    except anthropic.RateLimitError:
        st.warning("Alt text generation: Rate limit reached. Try again in a minute.")
        return None
    except Exception as e:
        st.warning(f"Alt text generation failed: {e}")
        return None
