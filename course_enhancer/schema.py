"""Normalized course schema shared by every input format and every skill.

This is the one data shape the rest of the engine is allowed to depend on.
Parsers (normalize.py) convert HTML/Markdown/JSON/CSV/plain text into this
shape; everything downstream (analysis, decision, generation, requirements)
only ever reads/writes this shape. That boundary is what keeps the engine
independent of both the input source and the eventual LMS.
"""
from __future__ import annotations

import re
import unicodedata

SCHEMA_VERSION = "1.0.0"


def slugify(text: str, fallback: str = "item") -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or fallback


def new_course(title: str = "", description: str = "", learning_objectives=None) -> dict:
    return {
        "title": title.strip() if title else "Untitled Course",
        "description": (description or "").strip(),
        "learning_objectives": list(learning_objectives or []),
    }


def new_module(module_id: str, title: str) -> dict:
    return {"id": module_id, "title": title.strip() if title else module_id, "lessons": []}


def new_lesson(lesson_id: str, title: str, content: str = "", learning_objectives=None) -> dict:
    return {
        "id": lesson_id,
        "title": title.strip() if title else lesson_id,
        "content": (content or "").strip(),
        "learning_objectives": list(learning_objectives or []),
    }


def new_normalized_course(course: dict, modules) -> dict:
    return {"schema_version": SCHEMA_VERSION, "course": course, "modules": list(modules)}


def validate_course(doc: dict) -> list:
    """Return a list of human-readable validation errors. Empty list = valid."""
    errors = []
    if not isinstance(doc, dict):
        return ["top-level course document must be an object"]
    if "course" not in doc or not isinstance(doc["course"], dict):
        errors.append("missing 'course' object")
    else:
        if not doc["course"].get("title"):
            errors.append("course.title is empty")
    if "modules" not in doc or not isinstance(doc["modules"], list):
        errors.append("missing 'modules' array")
        return errors
    if len(doc["modules"]) == 0:
        errors.append("course has zero modules")
    seen_lesson_ids = set()
    for mi, module in enumerate(doc["modules"]):
        if not isinstance(module, dict):
            errors.append(f"modules[{mi}] is not an object")
            continue
        if not module.get("id"):
            errors.append(f"modules[{mi}].id is missing")
        if not module.get("title"):
            errors.append(f"modules[{mi}].title is missing")
        lessons = module.get("lessons")
        if not isinstance(lessons, list) or len(lessons) == 0:
            errors.append(f"modules[{mi}] ('{module.get('title')}') has no lessons")
            continue
        for li, lesson in enumerate(lessons):
            if not isinstance(lesson, dict):
                errors.append(f"modules[{mi}].lessons[{li}] is not an object")
                continue
            lid = lesson.get("id")
            if not lid:
                errors.append(f"modules[{mi}].lessons[{li}].id is missing")
            elif lid in seen_lesson_ids:
                errors.append(f"duplicate lesson id '{lid}'")
            else:
                seen_lesson_ids.add(lid)
            if not lesson.get("title"):
                errors.append(f"lesson '{lid}' has no title")
            if not (lesson.get("content") or "").strip():
                errors.append(f"lesson '{lid}' ('{lesson.get('title')}') has empty content")
    return errors


def iter_lessons(doc: dict):
    """Yield (module, lesson) pairs in document order."""
    for module in doc.get("modules", []):
        for lesson in module.get("lessons", []):
            yield module, lesson


def lesson_count(doc: dict) -> int:
    return sum(len(m.get("lessons", [])) for m in doc.get("modules", []))
