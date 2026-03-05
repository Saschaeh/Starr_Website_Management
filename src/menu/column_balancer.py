"""Distribute flat sections into balanced columns for CMS layout."""

from __future__ import annotations

from src.models import Column, MenuItem, ParsedMenu, ParsedTab, Restaurant, Section, Tab


def _count_items(sections: list[Section]) -> int:
    return sum(len(s.items) for s in sections)


def _target_columns(total_items: int, num_sections: int) -> int:
    if num_sections >= 4:
        return 3
    if num_sections >= 2 and total_items > 8:
        return 3
    if num_sections >= 2:
        return min(2, num_sections)
    if total_items <= 8:
        return 1
    if total_items <= 16:
        return 2
    return 3


def _split_section(section: Section, max_items: int) -> list[Section]:
    if len(section.items) <= max_items:
        return [section]

    parts: list[Section] = []
    items = section.items
    for i in range(0, len(items), max_items):
        chunk = items[i : i + max_items]
        if i == 0:
            parts.append(Section(title=section.title, note=section.note, items=chunk))
        else:
            parts.append(Section(title=f"{section.title} (cont.)", note=section.note, items=chunk))
    return parts


def _prepare_sections(sections: list[Section], num_columns: int) -> list[Section]:
    if num_columns <= 1:
        return list(sections)

    total_items = _count_items(sections)
    target_per_col = max(total_items // num_columns, 4)
    max_per_section = int(target_per_col * 1.5)

    result: list[Section] = []
    for section in sections:
        if len(section.items) > max_per_section:
            result.extend(_split_section(section, target_per_col))
        else:
            result.append(section)
    return result


def _balance_sections(sections: list[Section], num_columns: int) -> list[Column]:
    if num_columns <= 1 or not sections:
        return [Column(sections=list(sections))]

    prepared = _prepare_sections(sections, num_columns)
    total = _count_items(prepared)
    target_per_col = total / num_columns

    columns: list[Column] = []
    current_sections: list[Section] = []
    current_count = 0

    for section in prepared:
        section_count = len(section.items)
        if (
            current_count > 0
            and current_count + section_count > target_per_col * 1.15
            and len(columns) < num_columns - 1
        ):
            columns.append(Column(sections=current_sections))
            current_sections = []
            current_count = 0

        current_sections.append(section)
        current_count += section_count

    if current_sections:
        columns.append(Column(sections=current_sections))

    return columns


def _balance_single_section(section: Section, num_columns: int) -> list[Column]:
    items = section.items
    total = len(items)
    per_col = max(1, (total + num_columns - 1) // num_columns)

    columns: list[Column] = []
    for i in range(0, total, per_col):
        chunk = items[i : i + per_col]
        title = section.title if i == 0 else "\u00a0"
        columns.append(Column(sections=[Section(
            title=title,
            note=section.note if i == 0 else None,
            items=chunk,
        )]))
    return columns


def balance_tab(parsed_tab: ParsedTab) -> Tab:
    sections = parsed_tab.sections
    total_items = _count_items(sections)
    num_columns = _target_columns(total_items, len(sections))

    if len(sections) == 1 and num_columns > 1 and total_items >= 4:
        columns = _balance_single_section(sections[0], num_columns)
    else:
        columns = _balance_sections(sections, num_columns)

    return Tab(
        id=parsed_tab.id,
        label=parsed_tab.label,
        description=parsed_tab.description,
        columns=columns,
        footnote=parsed_tab.footnote,
    )


def balance_menu(
    parsed_menu: ParsedMenu,
    restaurant_name: str,
    slug: str,
    accent_color: str,
    accent_light: str,
) -> Restaurant:
    tabs = [balance_tab(pt) for pt in parsed_menu.tabs]
    return Restaurant(
        name=restaurant_name,
        slug=slug,
        accent_color=accent_color,
        accent_light=accent_light,
        tabs=tabs,
    )
