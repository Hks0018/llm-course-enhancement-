"""Merges a course's original content with its generated enhancements into
ONE enhanced document, in the same format as the input (HTML or Markdown).

Important limitation: normalize.py deliberately discards the input file's
own markup/styling when it extracts lessons (see its module docstring) - so
this is NOT a byte-for-byte reconstruction of the original file's design.
It's a clean, freshly-rendered document containing the same title/modules/
lesson text, with each lesson's accepted enhancements (diagrams, tables,
knowledge checks, etc.) inserted directly beneath it.

json/csv/text inputs have no native "authored" format to mirror, so they
fall back to Markdown - the most broadly readable option.
"""
from __future__ import annotations

import html as _html


def _esc(value) -> str:
    return _html.escape(str(value), quote=False)


# ---------------------------------------------------------------------------
# Lesson body -> generic blocks (paragraphs / bullet lists), shared by both
# the Markdown and HTML renderers so list/paragraph detection lives in one
# place.
# ---------------------------------------------------------------------------

def _content_blocks(content: str) -> list:
    blocks = []
    buf: list = []
    bullets: list = []

    def flush_para():
        if buf:
            blocks.append({"type": "paragraph", "text": " ".join(buf).strip()})
            buf.clear()

    def flush_bullets():
        if bullets:
            blocks.append({"type": "bullet_list", "items": list(bullets)})
            bullets.clear()

    for raw_line in (content or "").splitlines():
        line = raw_line.strip()
        if not line:
            flush_para()
            flush_bullets()
            continue
        if line.startswith("- "):
            flush_para()
            bullets.append(line[2:].strip())
        else:
            flush_bullets()
            buf.append(line)
    flush_para()
    flush_bullets()
    return blocks


# ---------------------------------------------------------------------------
# One accepted enhancement -> generic blocks
# ---------------------------------------------------------------------------

def _enhancement_blocks(entry: dict) -> list:
    g = entry["generated"]
    et = entry["enhancement_type"]
    blocks = [{"type": "heading", "text": g.get("title") or et.replace("_", " ").title()}]

    purpose = g.get("educational_purpose") or g.get("purpose")
    if purpose:
        blocks.append({"type": "italic_para", "text": purpose})

    if "mermaid_code" in g:
        blocks.append({"type": "mermaid", "code": g["mermaid_code"]})
        if g.get("accessibility_description"):
            blocks.append({"type": "note", "text": f"Accessibility description: {g['accessibility_description']}"})
    elif et == "comparison_table":
        blocks.append({"type": "raw_md_table", "md": g.get("markdown_table", "")})
    elif et == "knowledge_check":
        if g.get("type") == "matching":
            if g.get("instructions"):
                blocks.append({"type": "paragraph", "text": g["instructions"]})
            blocks.append({
                "type": "bullet_list",
                "items": [f"{p.get('term', '')} → {p.get('match', '')}" for p in g.get("pairs", [])],
            })
        else:
            if g.get("question"):
                blocks.append({"type": "paragraph", "text": g["question"]})
            if g.get("options"):
                blocks.append({
                    "type": "bullet_list",
                    "items": [
                        f"{opt} (correct)" if opt == g.get("correct_answer") else opt
                        for opt in g["options"]
                    ],
                })
        if g.get("explanation"):
            blocks.append({"type": "italic_para", "text": f"Explanation: {g['explanation']}"})
    elif et == "scenario_exercise":
        if g.get("scenario"):
            blocks.append({"type": "paragraph", "text": g["scenario"]})
        if g.get("prompt"):
            blocks.append({"type": "paragraph", "text": f"Prompt: {g['prompt']}"})
        if g.get("model_answer_guidance"):
            blocks.append({"type": "italic_para", "text": f"Guidance: {g['model_answer_guidance']}"})
    elif et == "example":
        if g.get("definition_from_lesson"):
            blocks.append({"type": "paragraph", "text": f"{g.get('concept', '')}: {g['definition_from_lesson']}"})
        if g.get("example_scaffold"):
            blocks.append({"type": "paragraph", "text": g["example_scaffold"]})
    elif et == "summary_and_key_takeaways":
        if g.get("summary"):
            blocks.append({"type": "paragraph", "text": g["summary"]})
        if g.get("key_takeaways"):
            blocks.append({"type": "bullet_list", "items": g["key_takeaways"]})
    elif et == "video_explanation":
        blocks.append({
            "type": "paragraph",
            "text": f"Recommended style: {g.get('recommended_style', '')} — "
                    f"estimated duration: {g.get('estimated_duration', '')}",
        })
        blocks.append({"type": "note", "text": "Video script only — this engine does not render an actual video file."})
        for scene in g.get("scenes", []):
            blocks.append({"type": "paragraph", "text": f"Scene {scene.get('scene_number')}: {scene.get('voiceover', '')}"})
    elif et == "structural_recommendation":
        if g.get("recommendation"):
            blocks.append({"type": "paragraph", "text": g["recommendation"]})
    else:
        blocks.append({"type": "paragraph", "text": str(g)})

    if g.get("requires_subject_matter_review"):
        blocks.append({"type": "note", "text": "Needs subject-matter-expert review before publishing (auto-generated scaffold)."})
    return blocks


# ---------------------------------------------------------------------------
# Block renderers
# ---------------------------------------------------------------------------

def _blocks_to_markdown(blocks: list) -> str:
    parts = []
    for b in blocks:
        t = b["type"]
        if t == "heading":
            parts.append(f"#### {b['text']}")
        elif t == "paragraph":
            parts.append(b["text"])
        elif t == "italic_para":
            parts.append(f"_{b['text']}_")
        elif t == "note":
            parts.append(f"> {b['text']}")
        elif t == "bullet_list":
            parts.append("\n".join(f"- {item}" for item in b["items"]))
        elif t == "mermaid":
            parts.append("```mermaid\n" + b["code"].strip() + "\n```")
        elif t == "raw_md_table":
            parts.append(b["md"])
    return "\n\n".join(p for p in parts if p.strip())


def _markdown_table_to_html(md_table: str) -> str:
    rows = [r for r in md_table.strip().splitlines() if r.strip()]
    if len(rows) < 2:
        return f"<pre>{_esc(md_table)}</pre>"

    def cells(row):
        return [c.strip() for c in row.strip().strip("|").split("|")]

    header = cells(rows[0])
    body_rows = [cells(r) for r in rows[2:]]  # rows[1] is the '---|---' separator
    thead = "<tr>" + "".join(f"<th>{_esc(c)}</th>" for c in header) + "</tr>"
    tbody = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in body_rows)
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def _blocks_to_html(blocks: list) -> str:
    parts = []
    for b in blocks:
        t = b["type"]
        if t == "heading":
            parts.append(f"<h4>{_esc(b['text'])}</h4>")
        elif t == "paragraph":
            parts.append(f"<p>{_esc(b['text'])}</p>")
        elif t == "italic_para":
            parts.append(f"<p><em>{_esc(b['text'])}</em></p>")
        elif t == "note":
            parts.append(f"<blockquote>{_esc(b['text'])}</blockquote>")
        elif t == "bullet_list":
            items = "".join(f"<li>{_esc(i)}</li>" for i in b["items"])
            parts.append(f"<ul>{items}</ul>")
        elif t == "mermaid":
            parts.append(f'<pre class="mermaid">\n{_esc(b["code"].strip())}\n</pre>')
        elif t == "raw_md_table":
            parts.append(_markdown_table_to_html(b["md"]))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Full-course renderers
# ---------------------------------------------------------------------------

def _enhancements_by_lesson(built: dict) -> dict:
    grouped: dict = {}
    for e in built["all_accepted"]:
        grouped.setdefault(e["lesson_id"], []).append(e)
    return grouped


def render_course_markdown(normalized: dict, built: dict) -> str:
    course = normalized["course"]
    grouped = _enhancements_by_lesson(built)
    out = [f"# {course['title']}", ""]

    if course.get("description"):
        out += [course["description"], ""]
    if course.get("learning_objectives"):
        out.append("**Learning Objectives**")
        out += [f"- {o}" for o in course["learning_objectives"]] + [""]

    for module in normalized["modules"]:
        out += [f"## {module['title']}", ""]
        for lesson in module["lessons"]:
            out += [f"### {lesson['title']}", ""]
            if lesson.get("learning_objectives"):
                out.append("**Learning Objectives**")
                out += [f"- {o}" for o in lesson["learning_objectives"]] + [""]
            body = _blocks_to_markdown(_content_blocks(lesson.get("content", "")))
            if body:
                out += [body, ""]
            for entry in grouped.get(lesson["id"], []):
                out += ["---", "", _blocks_to_markdown(_enhancement_blocks(entry)), ""]

    return "\n".join(out).strip() + "\n"


_MERMAID_SCRIPT = (
    '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>\n'
    "<script>mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });</script>"
)

# Hardcoded house theme (sidebar nav, hero header, colored module sections,
# card-style lessons, styled callouts, interactive quiz) - lifted verbatim
# from a hand-authored reference course so every generated course gets the
# same look. Pure CSS (checkbox-hack sidebar toggle, :checked-driven quiz
# feedback) - no JS beyond the mermaid renderer.
_THEME_CSS = """
:root{
  --ink:#1f2937; --muted:#475569; --faint:#94a3b8; --bg:#f6f8fc; --line:#e8edf5;
  --p1-a:#1e3a8a; --p1-b:#2563eb; --p1-soft:#eef2ff;
  --p2-a:#3730a3; --p2-b:#4f46e5; --p2-soft:#f0eeff;
  --p3-a:#0f766e; --p3-b:#0d9488; --p3-soft:#effaf8;
  --good:#15803d; --good-soft:#eafaf0;
  --warn:#b45309; --warn-soft:#fef6ec;
  --bad:#b91c1c; --bad-soft:#fdecec;
  --qz-a:#3730a3; --qz-b:#4f46e5; --qz-soft:#f0eeff;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.65;}
a{color:inherit;}
code{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:5px;padding:1px 6px;font-size:.87em;font-family:ui-monospace,"SF Mono",Menlo,monospace;color:#1e293b;}
pre{background:#0f172a;color:#e2e8f0;border-radius:10px;padding:14px 16px;overflow-x:auto;font-size:.83rem;font-family:ui-monospace,"SF Mono",Menlo,monospace;margin:12px 0;}

.sidebar-toggle-input{display:none;}
.app-shell{display:flex;align-items:flex-start;}
.course-sidebar{width:300px;flex:0 0 300px;position:sticky;top:0;height:100vh;overflow-y:auto;
  background:#0f172a;color:#cbd5e1;padding:20px 14px;transition:margin-left .22s ease, opacity .18s ease;}
.sidebar-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding:0 6px;position:sticky;top:0;background:#0f172a;z-index:2;padding-bottom:10px;}
.sidebar-brand{font-weight:800;color:#fff;font-size:.85rem;}
.sidebar-close{cursor:pointer;color:#94a3b8;font-size:1rem;padding:3px 8px;border-radius:6px;}
.sidebar-close:hover{background:rgba(255,255,255,.08);color:#fff;}
.sidebar-group{margin-bottom:10px;}
.sidebar-group-label{display:block;font-size:.68rem;color:#94a3b8;font-weight:600;margin-bottom:4px;padding-left:6px;line-height:1.3;}
.course-sidebar a{display:block;padding:5px 8px;border-radius:6px;font-size:.78rem;color:#cbd5e1;text-decoration:none;margin-bottom:1px;line-height:1.35;}
.course-sidebar a:hover{background:rgba(255,255,255,.08);color:#fff;}

.content-area{flex:1 1 0%;min-width:0;}
.wrap{max-width:900px;margin:0 auto;padding:0 24px 100px;transition:max-width .22s ease;}

.reopen-btn{display:none;position:fixed;top:16px;left:16px;z-index:30;width:42px;height:42px;border-radius:10px;
  background:#1e3a8a;color:#fff;align-items:center;justify-content:center;cursor:pointer;font-size:1.15rem;box-shadow:0 8px 20px rgba(15,23,42,.28);}
.reopen-btn:hover{background:#2563eb;}
#sidebar-toggle:checked ~ .app-shell .course-sidebar{margin-left:-300px;opacity:0;pointer-events:none;position:absolute;}
#sidebar-toggle:checked ~ .app-shell .reopen-btn{display:flex;}
#sidebar-toggle:checked ~ .app-shell .content-area .wrap{max-width:1200px;}
@media(max-width:900px){
  .app-shell{display:block;}
  .course-sidebar{position:fixed;left:0;top:0;z-index:25;margin-left:-300px;opacity:0;pointer-events:none;box-shadow:0 10px 40px rgba(0,0,0,.35);}
  #sidebar-toggle:not(:checked) ~ .app-shell .course-sidebar{margin-left:0;opacity:1;pointer-events:auto;}
  #sidebar-toggle:not(:checked) ~ .app-shell .reopen-btn{display:none;}
  .reopen-btn{display:flex;}
  #sidebar-toggle:checked ~ .app-shell .reopen-btn{display:flex;}
  .content-area .wrap{max-width:100%;}
}

.course-hero{background:linear-gradient(120deg,#1e3a8a,#2563eb);color:#fff;padding:56px 24px 44px;text-align:center;}
.course-hero h1{font-weight:800;font-size:2.3rem;margin:0 0 10px;}
.course-hero p{max-width:640px;margin:0 auto;color:#eaf1ff;font-size:1.05rem;}
.course-meta{margin-top:20px;display:flex;justify-content:center;gap:10px;flex-wrap:wrap;}
.course-meta span{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:6px 14px;font-size:.85rem;font-weight:600;}

.phase-block{margin-top:64px;}
.phase-block.p1{--accent-a:var(--p1-a);--accent-b:var(--p1-b);--accent-soft:var(--p1-soft);}
.phase-block.p2{--accent-a:var(--p2-a);--accent-b:var(--p2-b);--accent-soft:var(--p2-soft);}
.phase-block.p3{--accent-a:var(--p3-a);--accent-b:var(--p3-b);--accent-soft:var(--p3-soft);}
.module-block{margin-top:32px;}
.module-head{font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--accent-a);border-bottom:2px solid var(--accent-soft);padding-bottom:8px;margin:0 0 18px;}

.lesson{background:#fff;border:1px solid var(--line);border-radius:16px;padding:30px 30px 26px;margin-bottom:26px;box-shadow:0 6px 18px rgba(15,23,42,.05);}
.lesson-eyebrow{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);font-weight:700;margin:0 0 6px;}
.lesson h3{margin:0 0 8px;font-size:1.35rem;color:var(--accent-a);}
.lesson-hook{color:var(--muted);font-size:1.02rem;margin:0 0 18px;padding-bottom:16px;border-bottom:1px solid var(--line);}
.lesson-hook p{margin:0;}

.section-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;font-weight:800;color:var(--faint);margin:26px 0 8px;}
.lesson-content{color:#334155;}
.lesson-content p{margin:0 0 12px;}
.lesson-content ul,.lesson-content ol{margin:0 0 12px;padding-left:22px;}
.lesson-content li{margin-bottom:5px;}
.lesson-content strong{color:var(--ink);}
.lesson-content > *:first-child{margin-top:0;}
.lesson-content .hero-diagram{margin:16px 0;border-radius:10px;overflow:hidden;background:#fbfdff;border:1px solid var(--line);padding:10px;}
.lesson-content .hero-diagram svg{max-width:100%;height:auto;display:block;margin:0 auto;}
.lesson-content table{border-collapse:collapse;width:100%;margin:12px 0 16px;font-size:.92rem;}
.lesson-content th,.lesson-content td{border:1px solid var(--line);padding:8px 12px;text-align:left;}
.lesson-content th{background:#fbfdff;color:var(--ink);font-weight:700;}

.callout{border-radius:12px;padding:14px 18px;margin:16px 0;font-size:.95rem;border:1px solid transparent;}
.callout-label{display:block;font-weight:800;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}
.callout--objectives{background:var(--warn-soft);border-color:#f3ddb8;}
.callout--objectives .callout-label{color:var(--warn);}
.callout--objectives ul{margin:0;padding-left:20px;}
.callout--mistake{background:var(--bad-soft);border-color:#f6c9c9;}
.callout--mistake .callout-label{color:var(--bad);}
.callout--tip{background:var(--p3-soft);border-color:#bfe9e2;}
.callout--tip .callout-label{color:var(--p3-a);}
.callout--homework{background:var(--p2-soft);border-color:#d8d3fb;}
.callout--homework .callout-label{color:var(--p2-a);}
.callout ul,.callout ol{margin:0;padding-left:20px;}
.callout ul li,.callout ol li{margin-bottom:6px;}
.callout p{margin:0 0 8px;}

.takeaways{background:#0f172a;color:#e2e8f0;border-radius:14px;padding:20px 22px;margin-top:22px;}
.takeaways h4{margin:0 0 10px;color:#fff;font-size:.85rem;text-transform:uppercase;letter-spacing:.06em;}
.takeaways p{margin:0;color:#cbd5e1;}
.takeaways ul{margin:8px 0 0;padding-left:20px;color:#cbd5e1;}

.quiz-group{margin:18px 0;}
.quiz-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;color:var(--qz-a);margin:0 0 8px;}
.quiz{background:#fbfdff;border:1.5px dashed #c7d2fe;border-radius:12px;padding:16px 18px;margin-bottom:10px;}
.quiz-q{font-weight:700;margin:0 0 10px;}
.quiz input[type=radio]{position:absolute;opacity:0;width:1px;height:1px;}
.quiz-opt{display:block;padding:10px 14px;border:1.5px solid var(--line);border-radius:8px;margin-bottom:6px;cursor:pointer;font-size:.89rem;color:#334155;background:#fff;}
.quiz-opt:hover{border-color:#a5b4fc;}
.quiz input:checked + .quiz-opt{border-color:var(--qz-b);background:var(--qz-soft);font-weight:600;}
.quiz input.is-correct:checked + .quiz-opt{border-color:var(--good);background:var(--good-soft);color:var(--good);}
.quiz input.is-correct:checked + .quiz-opt::after{content:" \\2014 Correct";font-weight:800;}
.quiz input:not(.is-correct):checked + .quiz-opt{border-color:var(--bad);background:var(--bad-soft);color:var(--bad);}
.quiz input:not(.is-correct):checked + .quiz-opt::after{content:" \\2014 Not quite";font-weight:800;}
.quiz-feedback{display:none;margin-top:8px;}
.quiz input:checked ~ .quiz-feedback{display:block;}
.quiz-feedback .fb{margin:0 0 6px;font-weight:800;font-size:.86rem;display:none;}
.quiz input.is-correct:checked ~ .quiz-feedback .fb-correct{display:block;color:var(--good);}
.quiz input:not(.is-correct):checked ~ .quiz-feedback .fb-wrong{display:block;color:var(--bad);}
.quiz-feedback .fb-explain{margin:0;background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:.87rem;color:#334155;}

footer{text-align:center;color:var(--faint);font-size:.82rem;padding:36px 20px;}
"""

_PHASE_CLASSES = ("p1", "p2", "p3")


def _knowledge_check_html(entry: dict, quiz_index: int) -> str:
    g = entry["generated"]
    lesson_id = entry["lesson_id"]
    name = f"{lesson_id}-kc{quiz_index}"

    if g.get("type") == "matching":
        rows = "".join(
            f"<li>{_esc(p.get('term', ''))} → {_esc(p.get('match', ''))}</li>"
            for p in g.get("pairs", [])
        )
        body = f'<p class="quiz-q">{_esc(g.get("instructions", "Match each term to its definition."))}</p><ul>{rows}</ul>'
    else:
        options_html = []
        for i, opt in enumerate(g.get("options", [])):
            is_correct = opt == g.get("correct_answer")
            opt_id = f"{name}-o{i}"
            correct_class = ' class="is-correct"' if is_correct else ""
            options_html.append(
                f'<input type="radio" name="{_esc(name)}" id="{_esc(opt_id)}"{correct_class}>'
                f'<label for="{_esc(opt_id)}" class="quiz-opt">{_esc(opt)}</label>'
            )
        feedback = (
            '<div class="quiz-feedback">'
            '<p class="fb fb-correct">✓ Correct</p>'
            '<p class="fb fb-wrong">✗ Not quite — see the highlighted option.</p>'
            f'<p class="fb-explain">{_esc(g.get("explanation", ""))}</p>'
            "</div>"
        )
        body = f'<p class="quiz-q">{_esc(g.get("question", ""))}</p>' + "".join(options_html) + feedback

    return f'<div class="quiz-group"><p class="quiz-label">Knowledge Check</p><div class="quiz">{body}</div></div>'


def _enhancement_html(entry: dict, quiz_index: int) -> str:
    g = entry["generated"]
    et = entry["enhancement_type"]
    title = g.get("title") or et.replace("_", " ").title()
    review_note = (
        '<p style="font-size:.8rem;color:var(--warn);margin-top:8px;">⚠ Needs subject-matter-expert review before publishing.</p>'
        if g.get("requires_subject_matter_review") else ""
    )

    if "mermaid_code" in g:
        access = (
            f'<p style="font-size:.85rem;color:var(--muted);margin-top:8px;">{_esc(g["accessibility_description"])}</p>'
            if g.get("accessibility_description") else ""
        )
        return (
            f'<div class="section-label">{_esc(title)}</div>'
            f'<div class="lesson-content"><div class="hero-diagram"><pre class="mermaid">{_esc(g["mermaid_code"].strip())}</pre></div>{access}</div>'
        )
    if et == "comparison_table":
        return f'<div class="section-label">{_esc(title)}</div><div class="lesson-content">{_markdown_table_to_html(g.get("markdown_table", ""))}</div>'
    if et == "knowledge_check":
        return _knowledge_check_html(entry, quiz_index)
    if et == "summary_and_key_takeaways":
        items = "".join(f"<li>{_esc(t)}</li>" for t in g.get("key_takeaways", []))
        return (
            f'<div class="takeaways"><h4>{_esc(title)}</h4>'
            f'<p>{_esc(g.get("summary", ""))}</p>'
            + (f"<ul>{items}</ul>" if items else "")
            + "</div>"
        )
    if et == "scenario_exercise":
        return (
            '<div class="callout callout--tip"><span class="callout-label">Scenario Exercise</span>'
            f'<p>{_esc(g.get("scenario", ""))}</p>'
            f'<p><strong>Prompt:</strong> {_esc(g.get("prompt", ""))}</p>'
            f'<p><em>{_esc(g.get("model_answer_guidance", ""))}</em></p></div>'
            + review_note
        )
    if et == "example":
        definition = f'<p>{_esc(g.get("concept", ""))}: {_esc(g["definition_from_lesson"])}</p>' if g.get("definition_from_lesson") else ""
        return (
            f'<div class="callout callout--tip"><span class="callout-label">{_esc(title)}</span>'
            f"{definition}<p>{_esc(g.get('example_scaffold', ''))}</p></div>"
            + review_note
        )
    if et == "video_explanation":
        scenes = "".join(
            f'<li>Scene {s.get("scene_number")}: {_esc(s.get("voiceover", ""))}</li>' for s in g.get("scenes", [])
        )
        return (
            '<div class="callout callout--homework"><span class="callout-label">Video Script (not rendered)</span>'
            f'<p>{_esc(g.get("recommended_style", ""))} — estimated duration: {_esc(g.get("estimated_duration", ""))}</p>'
            f"<ul>{scenes}</ul></div>"
        )
    if et == "structural_recommendation":
        return (
            '<div class="callout callout--mistake"><span class="callout-label">Restructuring Recommendation</span>'
            f'<p>{_esc(g.get("recommendation", ""))}</p></div>'
        )
    return f'<div class="section-label">{_esc(title)}</div><div class="lesson-content"><p>{_esc(str(g))}</p></div>' + review_note


def render_course_html(normalized: dict, built: dict) -> str:
    course = normalized["course"]
    grouped = _enhancements_by_lesson(built)
    total_lessons = sum(len(m["lessons"]) for m in normalized["modules"])
    total_enhancements = len(built["all_accepted"])

    sidebar = ['<div class="sidebar-top"><span class="sidebar-brand">' + _esc(course["title"]) + '</span>'
               '<label for="sidebar-toggle" class="sidebar-close" aria-label="Close course menu">&#10005; Close</label></div>']
    for module in normalized["modules"]:
        links = "".join(f'<a href="#{_esc(lesson["id"])}">{_esc(lesson["title"])}</a>' for lesson in module["lessons"])
        sidebar.append(f'<div class="sidebar-group"><span class="sidebar-group-label">{_esc(module["title"])}</span>{links}</div>')

    hero = (
        f'<div class="course-hero"><h1>{_esc(course["title"])}</h1>'
        + (f'<p>{_esc(course["description"])}</p>' if course.get("description") else "")
        + '<div class="course-meta">'
        + f'<span>{len(normalized["modules"])} Modules</span>'
        + f'<span>{total_lessons} Lessons</span>'
        + f'<span>{total_enhancements} Enhancements</span>'
        + "</div></div>"
    )

    sections = []
    quiz_counter = 0
    for module_index, module in enumerate(normalized["modules"]):
        phase_class = _PHASE_CLASSES[module_index % len(_PHASE_CLASSES)]
        lessons_html = []
        for lesson_index, lesson in enumerate(module["lessons"], start=1):
            parts = [
                f'<article class="lesson" id="{_esc(lesson["id"])}">',
                f'<p class="lesson-eyebrow">{_esc(module["title"])} · Lesson {lesson_index}</p>',
                f'<h3>{_esc(lesson["title"])}</h3>',
            ]
            if lesson.get("learning_objectives"):
                items = "".join(f"<li>{_esc(o)}</li>" for o in lesson["learning_objectives"])
                parts.append(f'<div class="callout callout--objectives"><span class="callout-label">Learning Objectives</span><ul>{items}</ul></div>')
            parts.append('<div class="section-label">Lesson Content</div>')
            parts.append(f'<div class="lesson-content">{_blocks_to_html(_content_blocks(lesson.get("content", "")))}</div>')
            for entry in grouped.get(lesson["id"], []):
                if entry["enhancement_type"] == "knowledge_check":
                    quiz_counter += 1
                parts.append(_enhancement_html(entry, quiz_counter))
            parts.append("</article>")
            lessons_html.append("".join(parts))

        sections.append(
            f'<section class="phase-block {phase_class}"><div class="module-block">'
            f'<div class="module-head">{_esc(module["title"])}</div>'
            + "".join(lessons_html) +
            "</div></section>"
        )

    footer = (
        f'<footer>{_esc(course["title"])} · Enhanced Course · {len(normalized["modules"])} Modules '
        f'· {total_lessons} Lessons</footer>'
    )

    body = (
        '<input type="checkbox" id="sidebar-toggle" class="sidebar-toggle-input">'
        '<div class="app-shell">'
        '<label for="sidebar-toggle" class="reopen-btn" aria-label="Open course menu">&#9776;</label>'
        '<nav class="course-sidebar">' + "".join(sidebar) + "</nav>"
        '<main class="content-area">'
        + hero
        + '<div class="wrap">' + "".join(sections) + "</div>"
        + footer
        + "</main></div>"
    )

    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{_esc(course['title'])} — Enhanced Course</title>\n"
        f"<style>{_THEME_CSS}</style>\n{_MERMAID_SCRIPT}\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


def render_enhanced_course(normalized: dict, built: dict) -> tuple:
    """Returns (document_text, file_extension)."""
    if normalized.get("source_format") == "html":
        return render_course_html(normalized, built), "html"
    return render_course_markdown(normalized, built), "md"
