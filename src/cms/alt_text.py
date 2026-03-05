"""Alt text generation using HuggingFace Inference API (Qwen Vision)."""

import base64
import io

import streamlit as st
from huggingface_hub import InferenceClient


@st.cache_resource
def _get_hf_client(token):
    """Return a cached InferenceClient instance."""
    return InferenceClient(token=token)


def generate_alt_text(pil_image):
    """Generate ADA-compliant alt text from a PIL image.

    Uses Qwen Vision model via HuggingFace Inference API.
    Returns the alt text string, or None on failure.
    """
    api_token = st.session_state.get('hf_api_token', '')
    if not api_token:
        return None

    img_buffer = io.BytesIO()
    if pil_image.mode in ('RGBA', 'LA', 'PA', 'P'):
        pil_image = pil_image.convert('RGB')
    pil_image.save(img_buffer, format='JPEG', quality=85)
    img_b64 = base64.b64encode(img_buffer.getvalue()).decode()

    try:
        client = _get_hf_client(api_token)
        result = client.chat_completion(
            model="Qwen/Qwen2.5-VL-7B-Instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": (
                        "Write a concise, descriptive alt text for this image suitable for "
                        "ADA/WCAG compliance on a restaurant website. Focus on what is visually "
                        "depicted. Return only the alt text, no quotes or extra formatting. "
                        "Keep it under 125 characters."
                    )}
                ]
            }],
            max_tokens=100,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        error_str = str(e).lower()
        if '401' in error_str or 'unauthorized' in error_str:
            st.warning("Alt text generation unavailable: Invalid HF token in .env file.")
        elif '403' in error_str or 'permission' in error_str:
            st.warning("HF token needs 'Inference Providers' permission.")
        elif '503' in error_str or 'loading' in error_str:
            st.info("Alt text model is loading, please try again in a few seconds.")
        else:
            st.warning("Alt text generation temporarily unavailable.")
        return None
