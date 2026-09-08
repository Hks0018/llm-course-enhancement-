"""Input normalization layer.

Converts HTML, Markdown, JSON, CSV, plain text, or already-structured
API-provided course data into the single normalized course format defined
in schema.py. This is the only place format-specific parsing logic lives -
everything downstream never looks at raw HTML/Markdown/CSV again.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from html.parser import HTMLParser

from course_enhancer import schema

SUPPORTED_FORMATS = ("html", "markdown", "json", "csv", "text")

_EXT_MAP = {
    ".html": "html",
    ".htm": "html",
    ".md": "markdown",
    ".markdown": "markdown",
    ".json": "json",
    ".csv": "csv",
    ".txt": "text",
}


def detect_format(path_or_text: str, explicit_format: str = None) -> str:
    if explicit_format:
        fmt = explicit_format.lower()
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format '{fmt}'. Supported: {SUPPORTED_FORMATS}")
        return fmt
    _, ext = os.path.splitext(path_or_text)
    if ext.lower() in _EXT_MAP and os.path.exists(path_or_text):
        return _EXT_MAP[ext.lower()]
    # Fall back to sniffing raw text content
    stripped = path_or_text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    if re.search(r"<\s*(html|body|h1|div|p)\b", stripped, re.I):
        return "html"
    if re.search(r"^#{1,3}\s+\S", stripped, re.M):
        return "markdown"
    if "," in stripped.splitlines()[0] if stripped.splitlines() else False:
        return "csv"
    return "text"


def load_source(source: str) -> str:
    """source may be a filesystem path or raw content; return raw text either way."""
    if os.path.exists(source) and os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as f:
            return f.read()
    return source


def normalize(source: str, fmt: str = None) -> dict:
    """Normalize any supported course input into the schema.py shape.

    `source` may be a file path or a raw content string. `fmt` overrides
    auto-detection (one of SUPPORTED_FORMATS).
    """
    raw = load_source(source)
    resolved_fmt = detect_format(source, fmt)
    parser = {
        "html": parse_html,
        "markdown": parse_markdown,
        "json": parse_json,
        "csv": parse_csv,
        "text": parse_text,
    }[resolved_fmt]
    title_hint = None
    if os.path.exists(source) and os.path.isfile(source):
        title_hint = os.path.splitext(os.path.basename(source))[0].replace("_", " ").replace("-", " ").title()
    doc = parser(raw, title_hint=title_hint)
    doc["source_format"] = resolved_fmt
    _assign_missing_ids(doc)
    return doc


def _assign_missing_ids(doc: dict) -> None:
    for mi, module in enumerate(doc.get("modules", []), start=1):
        if not module.get("id"):
            module["id"] = f"m{mi:02d}-{schema.slugify(module.get('title', ''), f'module-{mi}')}"
        for li, lesson in enumerate(module.get("lessons", []), start=1):
            if not lesson.get("id"):
                lesson["id"] = f"{module['id']}-l{li:02d}-{schema.slugify(lesson.get('title', ''), f'lesson-{li}')}"


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

_OBJECTIVES_HEADING_RE = re.compile(r"^(learning objectives|objectives)\s*:?\s*$", re.I)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")


def parse_markdown(text: str, title_hint: str = None) -> dict:
    lines = text.splitlines()
    course = schema.new_course(title_hint or "Untitled Course")
    modules = []
    current_module = None
    current_lesson = None
    content_buffer = []
    collecting_objectives_for = None  # 'course' | 'lesson' | None

    def flush_lesson_content():
        if current_lesson is not None:
            text_block = "\n".join(content_buffer).strip()
            if text_block:
                current_lesson["content"] = (current_lesson["content"] + "\n" + text_block).strip()
        content_buffer.clear()

    def ensure_module():
        nonlocal current_module
        if current_module is None:
            current_module = schema.new_module(None, "Module 1")
            modules.append(current_module)
        return current_module

    def ensure_lesson():
        nonlocal current_lesson
        m = ensure_module()
        if current_lesson is None:
            current_lesson = schema.new_lesson(None, "Overview")
            m["lessons"].append(current_lesson)
        return current_lesson

    got_h1 = False
    for raw_line in lines:
        line = raw_line.rstrip()
        h1 = re.match(r"^#\s+(.*)$", line)
        h2 = re.match(r"^##\s+(.*)$", line)
        h3 = re.match(r"^###\s+(.*)$", line)

        if h1 and not got_h1:
            flush_lesson_content()
            course["title"] = h1.group(1).strip()
            got_h1 = True
            current_module = None
            current_lesson = None
            collecting_objectives_for = None
            continue
        if h2:
            flush_lesson_content()
            current_module = schema.new_module(None, h2.group(1).strip())
            modules.append(current_module)
            current_lesson = None
            collecting_objectives_for = None
            continue
        if h3:
            flush_lesson_content()
            m = ensure_module()
            current_lesson = schema.new_lesson(None, h3.group(1).strip())
            m["lessons"].append(current_lesson)
            collecting_objectives_for = None
            continue

        if _OBJECTIVES_HEADING_RE.match(line.strip().strip("*:")):
            flush_lesson_content()
            collecting_objectives_for = "lesson" if current_lesson is not None else "course"
            continue

        bullet = _BULLET_RE.match(line)
        if collecting_objectives_for and bullet:
            target = ensure_lesson() if collecting_objectives_for == "lesson" else course
            target["learning_objectives"].append(bullet.group(1).strip())
            continue
        elif collecting_objectives_for and line.strip() == "":
            continue
        elif collecting_objectives_for:
            collecting_objectives_for = None  # objectives list ended

        if current_module is None:
            # Text before the first module/lesson boundary is course-level intro prose.
            if line.strip():
                course["description"] = (course["description"] + "\n" + raw_line).strip()
            continue
        if line.strip() == "" and current_lesson is None:
            continue
        ensure_lesson()
        content_buffer.append(raw_line)

    flush_lesson_content()

    if not modules:
        modules = [schema.new_module(None, "Module 1")]
        modules[0]["lessons"].append(schema.new_lesson(None, "Overview", text.strip()))

    return schema.new_normalized_course(course, modules)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

class _CourseHTMLParser(HTMLParser):
    """Best-effort structural extraction: h1 -> course title, h2 -> module,
    h3/h4 -> lesson, everything else -> lesson content (lists rendered as
    '- item' lines so downstream analysis can still detect list structure).
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.course_title = None
        self.course_description_parts = []
        self.modules = []
        self._cur_module = None
        self._cur_lesson = None
        self._buffer = []
        self._tag_stack = []
        self._capture_heading = None  # 'h1'|'h2'|'h3'
        self._heading_text = []
        self._li_prefix = ""

    def _flush_paragraph(self):
        text = "".join(self._buffer).strip()
        self._buffer = []
        if not text:
            return
        text = re.sub(r"[ \t]+", " ", text)
        if self._cur_module is None:
            # Text before the first module boundary is course-level intro prose.
            self.course_description_parts.append(text)
            return
        self._ensure_lesson()
        self._cur_lesson["content"] = (self._cur_lesson["content"] + "\n" + text).strip()

    def _ensure_module(self):
        if self._cur_module is None:
            self._cur_module = schema.new_module(None, "Module 1")
            self.modules.append(self._cur_module)
        return self._cur_module

    def _ensure_lesson(self):
        m = self._ensure_module()
        if self._cur_lesson is None:
            self._cur_lesson = schema.new_lesson(None, "Overview")
            m["lessons"].append(self._cur_lesson)
        return self._cur_lesson

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in ("h1", "h2", "h3", "h4"):
            self._flush_paragraph()
            self._capture_heading = tag
            self._heading_text = []
        elif tag == "li":
            self._li_prefix = "- "
        elif tag in ("p", "div", "section", "article", "br"):
            pass

    def handle_endtag(self, tag):
        if self._tag_stack and tag in self._tag_stack:
            while self._tag_stack and self._tag_stack.pop() != tag:
                pass
        if tag in ("h1", "h2", "h3", "h4") and self._capture_heading == tag:
            heading = "".join(self._heading_text).strip()
            heading = re.sub(r"\s+", " ", heading)
            self._capture_heading = None
            if tag == "h1" and self.course_title is None:
                self.course_title = heading
            elif tag == "h2":
                self._cur_module = schema.new_module(None, heading)
                self.modules.append(self._cur_module)
                self._cur_lesson = None
            elif tag in ("h3", "h4"):
                m = self._ensure_module()
                self._cur_lesson = schema.new_lesson(None, heading)
                m["lessons"].append(self._cur_lesson)
        elif tag in ("p", "div", "li"):
            if tag == "li":
                self._flush_paragraph()
                self._li_prefix = ""
            else:
                self._flush_paragraph()

    def handle_data(self, data):
        if self._capture_heading:
            self._heading_text.append(data)
        else:
            if self._li_prefix and data.strip():
                self._buffer.append(self._li_prefix)
                self._li_prefix = ""
            self._buffer.append(data)

    def close(self):
        super().close()
        self._flush_paragraph()


_CONTAINER_TAG_RE = re.compile(r"<(/?)([a-zA-Z][\w-]*)\b[^>]*>")
_HEADING_RE = re.compile(r"<h([1-4])\b[^>]*>(.*?)</h\1>", re.I | re.S)


class _PlainTextHTMLParser(HTMLParser):
    """Strips tags to plain text: <li> becomes '- item' lines, block-level
    tags become line breaks, <script>/<style> content is discarded. Used by
    the container-based HTML path (below) to flatten one lesson's inner
    markup regardless of how many decorative headings it contains."""

    _BLOCK_TAGS = {"p", "div", "section", "article", "ul", "ol", "tr", "td", "th", "table",
                   "h1", "h2", "h3", "h4", "h5", "h6"}
    _SKIP_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._chunks = []
        self._li_prefix = ""
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "li":
            self._chunks.append("\n")
            self._li_prefix = "- "
        elif tag == "br":
            self._chunks.append("\n")
        elif tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._li_prefix and data.strip():
            self._chunks.append(self._li_prefix)
            self._li_prefix = ""
        self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        lines = [l.strip() for l in raw.split("\n")]
        return "\n".join(l for l in lines if l)


def _strip_html_to_text(fragment: str) -> str:
    parser = _PlainTextHTMLParser()
    parser.feed(fragment)
    parser.close()
    return parser.text()


def _pull_first_heading(fragment: str):
    """Return (title_text_or_None, fragment_with_that_heading_removed)."""
    m = _HEADING_RE.search(fragment)
    if not m:
        return None, fragment
    title = re.sub(r"\s+", " ", _strip_html_to_text(m.group(2))).strip()
    remaining = fragment[: m.start()] + fragment[m.end():]
    return (title or None), remaining


def _find_top_level_spans(html: str, tag: str):
    """Byte-offset (start_of_open_tag, end_of_close_tag) for each top-level
    (not nested inside another instance of the same tag) occurrence of
    `tag` in `html`."""
    spans = []
    depth = 0
    start = None
    for m in _CONTAINER_TAG_RE.finditer(html):
        if m.group(2).lower() != tag:
            continue
        if not m.group(1):  # opening tag
            if depth == 0:
                start = m.start()
            depth += 1
        else:  # closing tag
            depth = max(0, depth - 1)
            if depth == 0 and start is not None:
                spans.append((start, m.end()))
                start = None
    return spans


def _parse_html_by_containers(html: str, title_hint: str = None):
    """Alternate HTML extraction path using HTML5's own <article>/<section>
    containment semantics, rather than heading depth, to find lesson/module
    boundaries. This is what real-world page-builder-exported course sites
    often need: headings get reused constantly for visual styling inside a
    lesson (accordion questions, feature cards) with no relation to the
    document's real outline, while <article> (one lesson) nested in
    <section> (one module containing 1+ lessons) stays reliable because it
    reflects actual page structure rather than typographic choices.

    Returns None (signaling "fall back to the heading-based parser") when
    the document has no <article> tags at all.
    """
    article_spans = _find_top_level_spans(html, "article")
    if not article_spans:
        return None

    section_spans = _find_top_level_spans(html, "section")
    module_sections = [s for s in section_spans if "<article" in html[s[0]:s[1]].lower()]

    first_article_start = article_spans[0][0]
    course_title, _ = _pull_first_heading(html[:first_article_start])
    course = schema.new_course(course_title or title_hint or "Untitled Course")

    def module_for(article_start):
        for s in module_sections:
            if s[0] <= article_start < s[1]:
                return s
        return None

    modules_by_span = {}
    ordered_module_spans = []
    default_module = None

    for a_start, a_end in article_spans:
        mod_span = module_for(a_start)
        if mod_span is None:
            if default_module is None:
                default_module = schema.new_module(None, "Module 1")
            module = default_module
        else:
            if mod_span not in modules_by_span:
                preamble = html[mod_span[0]:a_start]
                mod_title, _ = _pull_first_heading(preamble)
                module = schema.new_module(None, mod_title or f"Module {len(ordered_module_spans) + 1}")
                modules_by_span[mod_span] = module
                ordered_module_spans.append(mod_span)
            module = modules_by_span[mod_span]

        lesson_title, remaining = _pull_first_heading(html[a_start:a_end])
        content = _strip_html_to_text(remaining)
        module["lessons"].append(schema.new_lesson(None, lesson_title or "Lesson", content))

    modules = [modules_by_span[s] for s in ordered_module_spans]
    if default_module is not None:
        modules.append(default_module)
    modules = [m for m in modules if m["lessons"]]

    if not modules:
        return None
    return schema.new_normalized_course(course, modules)


def parse_html(text: str, title_hint: str = None) -> dict:
    container_result = _parse_html_by_containers(text, title_hint)
    if container_result is not None:
        return container_result

    p = _CourseHTMLParser()
    p.feed(text)
    p.close()
    course = schema.new_course(p.course_title or title_hint or "Untitled Course", " ".join(p.course_description_parts))
    modules = p.modules
    if not modules:
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        modules = [schema.new_module(None, "Module 1")]
        modules[0]["lessons"].append(schema.new_lesson(None, "Overview", plain))
    return schema.new_normalized_course(course, modules)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def parse_json(text: str, title_hint: str = None) -> dict:
    data = json.loads(text)
    if isinstance(data, dict) and "course" in data and "modules" in data:
        course = schema.new_course(
            data["course"].get("title", title_hint or "Untitled Course"),
            data["course"].get("description", ""),
            data["course"].get("learning_objectives", []),
        )
        modules = []
        for module in data.get("modules", []):
            mod = schema.new_module(module.get("id"), module.get("title", ""))
            for lesson in module.get("lessons", []):
                mod["lessons"].append(
                    schema.new_lesson(
                        lesson.get("id"),
                        lesson.get("title", ""),
                        lesson.get("content", ""),
                        lesson.get("learning_objectives", []),
                    )
                )
            modules.append(mod)
        return schema.new_normalized_course(course, modules)

    if isinstance(data, list):
        # Best-effort: a flat list of lesson-like objects -> one module.
        course = schema.new_course(title_hint or "Untitled Course")
        mod = schema.new_module(None, "Module 1")
        for item in data:
            mod["lessons"].append(
                schema.new_lesson(
                    item.get("id"),
                    item.get("title", item.get("name", "")),
                    item.get("content", item.get("body", "")),
                    item.get("learning_objectives", []),
                )
            )
        return schema.new_normalized_course(course, [mod])

    raise ValueError(
        "Unrecognized JSON course structure. Expected {'course': {...}, 'modules': [...]} "
        "or a flat list of lesson objects."
    )


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def parse_csv(text: str, title_hint: str = None) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header row")
    fields = {f.lower().strip(): f for f in reader.fieldnames}
    required = ["module_title", "lesson_title", "content"]
    missing = [r for r in required if r not in fields]
    if missing:
        raise ValueError(
            f"CSV missing required columns {missing}. Expected columns: "
            f"module_id, module_title, lesson_id, lesson_title, content, learning_objectives"
        )

    course = schema.new_course(title_hint or "Untitled Course")
    modules_by_key = {}
    modules = []
    for row in reader:
        mod_title = row.get(fields["module_title"], "").strip()
        mod_id = row.get(fields.get("module_id", ""), "") if "module_id" in fields else None
        key = mod_id or mod_title or "module-1"
        if key not in modules_by_key:
            module = schema.new_module(mod_id or None, mod_title or "Module 1")
            modules_by_key[key] = module
            modules.append(module)
        module = modules_by_key[key]

        objectives_raw = row.get(fields.get("learning_objectives", ""), "") if "learning_objectives" in fields else ""
        objectives = [o.strip() for o in objectives_raw.split(";") if o.strip()] if objectives_raw else []
        lesson_id = row.get(fields.get("lesson_id", ""), "") if "lesson_id" in fields else None
        module["lessons"].append(
            schema.new_lesson(
                lesson_id or None,
                row.get(fields["lesson_title"], "").strip(),
                row.get(fields["content"], ""),
                objectives,
            )
        )
    return schema.new_normalized_course(course, modules)


# ---------------------------------------------------------------------------
# Plain text
# ---------------------------------------------------------------------------

def parse_text(text: str, title_hint: str = None) -> dict:
    course = schema.new_course(title_hint or "Untitled Course")
    module = schema.new_module(None, "Module 1")
    module["lessons"].append(schema.new_lesson(None, "Lesson 1", text.strip()))
    return schema.new_normalized_course(course, [module])
