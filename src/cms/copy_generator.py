"""Marketing copy generation using Anthropic Claude API."""

import json
import os
import re

import streamlit as st
import anthropic

# Copy sections: (id, label, word_min, word_max, description)
COPY_SECTIONS = [
    ('the_concept', 'The Concept', 30, 100,
     "Concise overview of the restaurant's concept, chef's vision, history, and cultural influences"),
    ('the_cuisine', 'The Cuisine', 30, 50,
     'Describe the cuisine, key dishes, cooking styles, ingredients, and any fusion or innovative elements'),
    ('group_dining', 'Group Dining', 30, 100,
     'Summarize group dining, private events, or large party details in a straightforward style'),
    ('meta_title', 'Website Title (SEO)', 5, 10,
     'On-brand and SEO-friendly website title meta tag'),
    ('meta_description', 'Meta Description (SEO)', 15, 30,
     'On-brand and SEO-friendly website description meta tag'),
]

DEFAULT_COPY_INSTRUCTIONS = """Generate content for the following sections on a new restaurant website being built.

Source Website: Website provided as prompt and sometimes with word document with copy and details inside you can use.

Thoroughly analyze the source site's pages (e.g., home, about, menu, private/group dining) to extract and adapt relevant details. First, determine the site's unique tone and style by examining its existing copy - such as word choice, sentence structure, formality, and overall vibe (e.g., it might be elegant and promotional with narrative, descriptive language highlighting innovation, heritage, and sensory experiences, but adapt based on what you observe). Ensure all new content matches this analyzed tone and style without being overly salesy. To preserve authenticity, incorporate as much of the original words and sentences from the source as available, possible, and makes sense - while still ensuring the content flows naturally and meets word count requirements.

Sections to generate:
1. **The Concept**
   Craft a concise overview of the restaurant's overall concept, drawing from the source site's about page or similar. Focus on the chef's vision, history, unique selling points, and cultural influences. If no explicit details exist, create an original description based on the site's analyzed tone and inferred elements (e.g., from imagery, menu themes, or homepage).
2. **The Cuisine**
   Describe the cuisine in a tone and style matching the source site's analyzed voice (e.g., evocative and refined if that's what you observe), emphasizing key dishes, cooking styles, ingredients, and any fusion or innovative elements based on menu or description pages. If no explicit details exist, create an original description based on the site's tone and inferred elements (e.g., from menu items or photos), erring on the shorter word count of around 30-50 words.
3. **Group Dining**
   Summarize group dining, private events, or large party details in a straightforward, matter-of-fact style. CRITICAL: If the source text contains specific seating capacities or guest counts, you MUST copy those exact numbers verbatim. Do NOT paraphrase, round, or estimate any numbers. If no group dining details exist in the source, use exactly: "For groups or private events, please contact us directly to discuss customized options and availability."

Also write on brand and SEO friendly Website Title and Description meta tags.

Guidelines:
- Each section must be 30-100 words (except for The Cuisine, which should be 30-50 words if creating original content i.e.: you can't copy cuisine copy section from source).
- Ensure content is original, engaging, and aligned with the source site's analyzed professional voice (e.g., vivid yet refined descriptions if applicable). Incorporate original wording from the source exactly where possible if it makes sense and does not disrupt flow; otherwise, rephrase creatively while staying factual.
- Research the source site thoroughly via browsing tools if needed for accurate, up-to-date details.
- Do not use these dashes in the copy: "-"
- Never speak in first person.
- In Group Dining section you do not need to add contact details or email.
- IMPORTANT: Never invent, approximate, or round any numbers. If the source text states specific figures (seating capacity, guest counts, square footage, etc.), use exactly those numbers. If the source does not provide specific numbers, omit them entirely rather than guessing.
"""

MASTER_INSTRUCTIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..', 'master_copy_instructions.json'
)


def _get_api_key():
    """Get Anthropic API key from secrets or env."""
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        key = None
    if not key:
        key = os.getenv("ANTHROPIC_API_KEY", "")
    return key


def load_master_instructions():
    """Load master copy instructions from disk."""
    try:
        with open(MASTER_INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('instructions', DEFAULT_COPY_INSTRUCTIONS)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_COPY_INSTRUCTIONS


def save_master_instructions(instructions):
    """Save copy instructions as the new master default."""
    with open(MASTER_INSTRUCTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'instructions': instructions}, f, ensure_ascii=False, indent=2)


def generate_copy(website_text, restaurant_name, section=None, instructions=None):
    """Generate marketing copy from website text using Claude.

    Returns (success: bool, copy_dict: dict, error: str).
    """
    api_key = _get_api_key()
    if not api_key:
        return False, {}, "Anthropic API key not configured. Add ANTHROPIC_API_KEY to secrets."

    if not instructions:
        instructions = DEFAULT_COPY_INSTRUCTIONS

    if section:
        section_info = next((s for s in COPY_SECTIONS if s[0] == section), None)
        if not section_info:
            return False, {}, f"Unknown section: {section}"
        sid, label, wmin, wmax, desc = section_info
        prompt = (
            f"You are a professional copywriter for upscale restaurants.\n\n"
            f"INSTRUCTIONS:\n{instructions}\n\n"
            f"Based on this website content for {restaurant_name}:\n{website_text[:6000]}\n\n"
            f"Write a {label} ({desc}). STRICT word limit: {wmin}-{wmax} words.\n"
            f"Return ONLY the copy text, nothing else."
        )
        max_tokens = 300
    else:
        section_list = "\n".join(
            f"{i+1}. [{s[0].upper()}] {s[1]} (STRICT: {s[2]}-{s[3]} words) - {s[4]}"
            for i, s in enumerate(COPY_SECTIONS)
        )
        prompt = (
            f"You are a professional copywriter for upscale restaurants.\n\n"
            f"INSTRUCTIONS:\n{instructions}\n\n"
            f"Based on this website content for {restaurant_name}:\n{website_text[:6000]}\n\n"
            f"Generate marketing copy for these {len(COPY_SECTIONS)} sections:\n{section_list}\n\n"
            f"Format your response EXACTLY as:\n"
            f"[THE_CONCEPT]\nyour text\n[/THE_CONCEPT]\n\n"
            f"[THE_CUISINE]\nyour text\n[/THE_CUISINE]\n\n"
            f"[GROUP_DINING]\nyour text\n[/GROUP_DINING]\n\n"
            f"[META_TITLE]\nyour text\n[/META_TITLE]\n\n"
            f"[META_DESCRIPTION]\nyour text\n[/META_DESCRIPTION]\n\n"
            f"IMPORTANT: You MUST stay within the word limits for each section."
        )
        max_tokens = 2500

    try:
        client = anthropic.Anthropic(api_key=api_key)
        result = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = result.content[0].text.strip()
    except anthropic.AuthenticationError:
        return False, {}, "Invalid Anthropic API key."
    except anthropic.RateLimitError:
        return False, {}, "Rate limit reached. Please wait a minute and try again."
    except anthropic.APIStatusError as e:
        return False, {}, f"API error: {e.message}"
    except Exception as e:
        return False, {}, f"Copy generation failed: {e}"

    if section:
        return True, {section: response_text}, ""

    copy_dict = {}
    tag_map = {
        'the_concept': 'THE_CONCEPT',
        'the_cuisine': 'THE_CUISINE',
        'group_dining': 'GROUP_DINING',
        'meta_title': 'META_TITLE',
        'meta_description': 'META_DESCRIPTION',
    }
    for key, tag in tag_map.items():
        # Allow spaces, underscores, or hyphens between words in tags
        flexible_tag = tag.replace('_', r'[\s_-]?')
        pattern = rf'\[{flexible_tag}\](.*?)\[/{flexible_tag}\]'
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        copy_dict[key] = match.group(1).strip() if match else ""

    if not any(copy_dict.values()):
        return False, {}, "Could not parse generated copy. Please try again."

    return True, copy_dict, ""
