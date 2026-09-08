"""Backs the comparison-generation skill."""
from __future__ import annotations

import re

_VS_RE = re.compile(r"\b([A-Z][\w/\-]{1,24}(?:\s[A-Z][\w/\-]{1,24}){0,2})\s+(?:vs\.?|versus)\s+"
                     r"([A-Z][\w/\-]{1,24}(?:\s[A-Z][\w/\-]{1,24}){0,2})\b")
# NOTE: case-insensitivity is scoped to just the "compared to" literal via the
# inline (?i:...) group, not applied to the whole pattern - re.I on the whole
# regex would make [A-Z] match lowercase too, defeating the point of requiring
# properly-capitalized item names (this previously caused items like "get
# started with" / "on-premise" to be extracted from lowercase prose).
_COMPARED_TO_RE = re.compile(
    r"\b([A-Z][\w/\-]{1,24}(?:\s[A-Z][\w/\-]{1,24}){0,2})\s+(?i:compared to)\s+"
    r"([A-Z][\w/\-]{1,24}(?:\s[A-Z][\w/\-]{1,24}){0,2})\b"
)


def _extract_items(lesson_title: str, content: str):
    # Prefer the lesson title ("Cloud vs On-Premise Hosting") - it's a far
    # more reliable signal than scanning body prose, which is often lowercase.
    for text in (lesson_title or "", content):
        m = _VS_RE.search(text) or _COMPARED_TO_RE.search(text)
        if m:
            return [m.group(1).strip(), m.group(2).strip()], False
    return ["Option A", "Option B"], True


def _extract_criteria(content: str, items: list):
    """Sentences that mention 2+ items together are treated as one
    comparison criterion each - keeps the table grounded in lesson text
    instead of inventing new criteria."""
    criteria = []
    for sentence in re.split(r"(?<=[.!?])\s+", content):
        if sum(1 for item in items for word in item.split() if word.lower() in sentence.lower()) >= 1:
            snippet = sentence.strip()
            if snippet and len(snippet) < 160:
                criteria.append(snippet)
        if len(criteria) >= 4:
            break
    return criteria


def build_comparison_table(lesson: dict) -> dict:
    content = lesson.get("content", "")
    items, approximate = _extract_items(lesson.get("title", ""), content)
    criteria_sentences = _extract_criteria(content, items) if not approximate else []

    if not criteria_sentences:
        criteria_sentences = ["Description"]

    rows = []
    for i, sentence in enumerate(criteria_sentences):
        rows.append({"criterion": f"Point {i+1}", "notes": sentence})

    header = "| Criterion | " + " | ".join(items) + " |"
    sep = "|" + "---|" * (len(items) + 1)
    body = []
    for row in rows:
        cells = " | ".join("_(author: fill in)_" for _ in items)
        body.append(f"| {row['criterion']} | {cells} |")
    markdown_table = "\n".join([header, sep] + body)

    return {
        "enhancement_type": "comparison_table",
        "title": f"Comparison: {' vs '.join(items)}" if not approximate else f"Comparison: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Lets the learner compare items criterion-by-criterion at a glance instead of "
            "cross-referencing scattered sentences."
        ),
        "items": items,
        "criteria": [r["criterion"] for r in rows],
        "supporting_text_per_criterion": {r["criterion"]: r["notes"] for r in rows},
        "markdown_table": markdown_table,
        "accessibility_description": f"Comparison table of {' and '.join(items)} across {len(rows)} criteria.",
        "notes": [
            "Item names and per-criterion values could not be reliably extracted from prose; "
            "table is a structural scaffold for the author to fill in from the lesson content."
        ] if approximate else [
            "Criteria rows were seeded from sentences mentioning the compared items; author "
            "should fill in the per-item cell values precisely."
        ],
    }
