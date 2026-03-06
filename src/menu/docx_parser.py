"""Extract and annotate text from .docx files for LLM consumption."""

from __future__ import annotations

import re
from io import BytesIO

from docx import Document
from docx.oxml.ns import qn


def _is_bold(run) -> bool:
    """Determine if a run is bold, handling tri-state (True / None / False)."""
    return run.bold is True


def _get_heading_level(para) -> int | None:
    """Return heading level (1, 2, ...) or None if not a heading."""
    style_name = para.style.name if para.style else ""
    if style_name == "Title":
        return 1
    match = re.match(r"Heading (\d+)", style_name)
    if match:
        return int(match.group(1))
    return None


def _is_list_paragraph(para) -> bool:
    return (para.style.name if para.style else "") == "List Paragraph"


# Meal-type keywords that indicate a tab-level heading
_MEAL_TAB_RE = re.compile(
    r"^\*\*\s*"
    r"(dinner|lunch|brunch|breakfast|desserts?|bar\s+menu|drinks?|"
    r"cocktails?|wine|beer|beverages?|happy\s+hour|tasting\s+menu|"
    r"prix\s+fixe|kids|children|late\s+night|supper)"
    r"\s*\*\*$",
    re.IGNORECASE,
)

# Title lines that act as section separators (not tab content)
_TITLE_RE = re.compile(
    r"^\*\*.*(?:working\s+menu|menu\s*s?)\s*\*\*$",
    re.IGNORECASE,
)


def _promote_bold_to_headings(text: str) -> str:
    """When no heading styles exist, promote bold meal-type lines to ## headings."""
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        if _TITLE_RE.match(line):
            inner = line.strip("*").strip()
            out.append(f"# {inner}")
        elif _MEAL_TAB_RE.match(line):
            inner = line.strip("*").strip()
            out.append(f"## {inner}")
        else:
            out.append(line)
    return "\n".join(out)


def extract_text(file_bytes: bytes) -> str:
    """Extract annotated text from a .docx file."""
    doc = Document(BytesIO(file_bytes))
    lines: list[str] = []
    in_menu_section = False

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        text = text.replace("\xa0", " ")

        heading = _get_heading_level(para)
        if heading == 1:
            if re.match(r"Menu Pages", text, re.IGNORECASE):
                in_menu_section = True
            lines.append(f"# {text}")
            continue
        if heading == 2:
            lines.append(f"## {text}")
            continue

        if _is_list_paragraph(para) and not in_menu_section:
            continue

        runs_with_text = [r for r in para.runs if r.text.strip()]
        if runs_with_text and all(_is_bold(r) for r in runs_with_text):
            lines.append(f"**{text}**")
        else:
            lines.append(text)

    result = "\n".join(lines)

    # If no ## headings found, promote bold meal-type lines to tab headings
    if "\n## " not in result and not result.startswith("## "):
        result = _promote_bold_to_headings(result)

    return result


def filter_menu_content(text: str) -> str:
    """Filter extracted text to only include menu content."""
    lines = text.split("\n")

    menu_start = None
    for i, line in enumerate(lines):
        if re.match(r"^#\s+Menu Pages", line, re.IGNORECASE):
            menu_start = i + 1
            break

    if menu_start is None:
        for i, line in enumerate(lines):
            if line.startswith("## "):
                menu_start = i
                break

    if menu_start is None:
        return text

    lines = lines[menu_start:]

    filtered: list[str] = []
    skip_patterns = [
        r"^DOWNLOAD PDF$",
        r"^Click.*(vegan|vegetarian|gluten-free|menu).*$",
        r"^Click\s*here\s",
        r"^Menu Header\s*\(",
        r"^STARR RESTAURANTS$",
        r"^(Facebook|Instagram|Spotify|LinkedIn|Careers|Shop|Donations)$",
        r"^(Privacy Policy|Accessibility|Terms of Use)$",
        r"^JOIN OUR MAILING LIST$",
        r"^CONNECT WITH US$",
        r"^(HOURS|CONTACT|LOCATION)$",
        r"^PHONE:",
        r"^GENERAL:",
        r"^(GROUP DINING|MARKETING|PRESS):",
        r"^ORDER NOW",
        r"^RESERVE A TABLE$",
        r"^VIEW ALL HAPPENINGS$",
        r"^Book your spot",
        r"^SAVE THE DATES",
    ]

    skip_tab_patterns = [
        r"vegan|vegetarian|gluten.free",
        r"^VEG\s+",
        r"group\s+dining",
        r"happenings?",
        r"private\s+(dining|events?)",
        r"gift\s+cards?",
    ]

    in_nav_block = False
    nav_labels: set[str] = set()
    skip_current_tab = False

    for line in lines:
        m = re.match(r"^##\s+(.+?)(?:\s+Page)?:?\s*$", line)
        if m:
            nav_labels.add(m.group(1).strip().upper())

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("## "):
            tab_label = stripped[3:].strip()
            skip_current_tab = any(
                re.search(pat, tab_label, re.IGNORECASE)
                for pat in skip_tab_patterns
            )
            if skip_current_tab:
                continue
            in_nav_block = False

        if skip_current_tab:
            continue

        if any(re.match(pat, stripped, re.IGNORECASE) for pat in skip_patterns):
            continue

        if stripped.upper() in nav_labels and not stripped.startswith("## "):
            if in_nav_block or (filtered and re.match(r"^##\s+", filtered[-1])):
                in_nav_block = True
                continue

        if in_nav_block and stripped.upper() not in nav_labels:
            in_nav_block = False

        filtered.append(line)

    return "\n".join(filtered)
