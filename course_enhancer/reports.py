"""Markdown report generators: COURSE_ENHANCEMENT_REPORT.md,
ODOO_IMPLEMENTATION_REQUIREMENTS.md, MODULE_DEPENDENCY_GRAPH.md,
QUALITY_REPORT.md.
"""
from __future__ import annotations

import datetime


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def render_course_enhancement_report(built: dict, normalized_course: dict) -> str:
    course = normalized_course["course"]
    analysis = built["course_analysis"]
    plan = built["enhancement_plan"]
    lines = []
    lines.append(f"# Course Enhancement Report: {course['title']}")
    lines.append(f"\n_Generated {_now()} by the Universal Course Enhancement Engine._\n")

    lines.append("## 1. Executive Summary")
    lines.append(
        f"- **{analysis['total_lessons']} lessons** analyzed across **{analysis['total_modules']} modules**.\n"
        f"- **{analysis['lessons_requiring_no_enhancement']} lessons** are already clear and effective - "
        f"no enhancement recommended.\n"
        f"- **{analysis['lessons_with_recommendations']} lessons** received at least one evidence-based "
        f"enhancement recommendation.\n"
        f"- **{len(built['all_accepted'])} enhancements accepted**, "
        f"**{len(built['all_rejected'])} suppressed** by quality validation (duplicates, per-lesson cap, "
        f"or failed checks).\n"
    )

    lines.append("\n## 2. Course Analysis")
    lines.append(f"- Course description: {course.get('description') or '_(none provided)_'}")
    objs = course.get("learning_objectives") or []
    if objs:
        lines.append("- Course-level learning objectives:")
        lines.extend(f"  - {o}" for o in objs)

    lines.append("\n## 3. Lessons Analyzed")
    lines.append("| Lesson | Words | Cognitive Load | Verdict |")
    lines.append("|---|---|---|---|")
    for r in built["lesson_results"]:
        verdict = "No enhancement needed" if r["sufficient"] else f"{len(r['accepted_enhancements'])} enhancement(s)"
        lines.append(
            f"| {r['lesson_title']} | {r['analysis']['word_count']} | "
            f"{r['analysis']['cognitive_load']} | {verdict} |"
        )

    lines.append("\n## 4. Lessons Requiring No Changes")
    no_change = [r for r in built["lesson_results"] if r["sufficient"]]
    if no_change:
        for r in no_change:
            lines.append(f"- **{r['lesson_title']}** - {r['no_enhancement_reason']}")
    else:
        lines.append("_Every lesson in this course received at least one recommendation._")

    lines.append("\n## 5. Recommended Enhancements & 6. Educational Reason & 7. Priority")
    with_changes = [r for r in built["lesson_results"] if not r["sufficient"]]
    if not with_changes:
        lines.append("_None - see Section 4._")
    for r in with_changes:
        lines.append(f"\n### {r['lesson_title']}")
        for e in r["accepted_enhancements"]:
            lines.append(
                f"- **{e['enhancement_type']}** (priority: {e['priority']}, "
                f"impact {e['educational_impact']}/10, complexity {e['implementation_complexity']}/10)\n"
                f"  - Trigger: {e['trigger']}\n"
                f"  - Evidence: {e['evidence']}\n"
                f"  - Why: {e['rationale']}"
            )
        if r["rejected_enhancements"]:
            lines.append("  - _Suppressed candidates:_")
            for e in r["rejected_enhancements"]:
                lines.append(f"    - {e['enhancement_type']}: {e.get('suppressed_reason', 'n/a')}")

    lines.append("\n## 8. Generated Assets (Diagrams & Tables)")
    diagram_assets = built["enhancement_package"]["assets"]["diagrams"]
    if diagram_assets:
        for a in diagram_assets:
            lines.append(f"- `{a['lesson_id']}` - {a['generated'].get('title', a['enhancement_type'])} "
                          f"({a['enhancement_type']})")
    else:
        lines.append("_No diagrams/tables were generated for this course._")

    lines.append("\n## 9. Interactive Components")
    interactive = built["enhancement_package"]["interactive_components"]
    if interactive:
        for c in interactive:
            g = c["generated"]
            lines.append(f"- `{c['lesson_id']}` - {c['enhancement_type']} "
                          f"({g.get('type', '')}): {g.get('question') or g.get('scenario', '')[:100]}")
    else:
        lines.append("_No interactive components were generated for this course._")

    lines.append("\n## 10. Video Recommendations")
    videos = built["enhancement_package"]["video_packages"]
    if videos:
        for v in videos:
            g = v["generated"]
            lines.append(f"- `{v['lesson_id']}` - {g['title']} ({g['estimated_duration']}, "
                          f"{len(g['scenes'])} scenes) + companion whiteboard-video and voiceover packages")
    else:
        lines.append("_No video enhancements were recommended for this course._")

    lines.append("\n## 11. Quality Validation")
    acc = built["accessibility_review"]
    lines.append(f"- Accessibility review: {'PASS' if acc['pass'] else 'ISSUES FOUND'} "
                  f"({acc['total_enhancements_reviewed']} enhancements reviewed, {len(acc['findings'])} findings).")
    for f in acc["findings"]:
        lines.append(f"  - [{f['severity']}] `{f['lesson_id']}` ({f['enhancement_type']}): {f['issue']}")
    lines.append(f"- {len(built['all_rejected'])} candidate enhancement(s) were suppressed by quality "
                  f"validation across the course (see per-lesson detail above and QUALITY_REPORT.md).")

    return "\n".join(lines) + "\n"


def render_odoo_requirements_report(odoo_requirements: dict, course_title: str) -> str:
    lines = []
    lines.append("# ODOO IMPLEMENTATION REQUIREMENTS")
    lines.append(f"\n_Course: {course_title}. Generated {_now()}._")
    lines.append(
        "\n> **Every module below is a PROPOSED custom Odoo module.** None of these are claimed to "
        "already exist in this or any Odoo installation. Odoo deployment, self-hosting, custom "
        "module development, database implementation, UI rendering, API endpoints, and uploading "
        "enhancement packages into Odoo are the responsibility of a separate Odoo developer/team. "
        "This engine only specifies *what* is required and *why*."
    )

    lines.append("\n## Executive Summary")
    n = len(odoo_requirements["modules"])
    if n == 0:
        lines.append("This course's enhancement package requires **zero** custom Odoo modules - "
                      "no enhancements needing LMS rendering capability were generated.")
        return "\n".join(lines) + "\n"
    lines.append(
        f"This course's enhancement package requires **{n} recommended custom Odoo module(s)**: "
        f"{len(odoo_requirements['phases']['phase_1_required'])} required (Phase 1), "
        f"{len(odoo_requirements['phases']['phase_2_important'])} important (Phase 2), "
        f"{len(odoo_requirements['phases']['phase_3_optional'])} optional (Phase 3)."
    )

    lines.append("\n## Required Capabilities")
    for m in odoo_requirements["modules"]:
        lines.append(f"- **{m['module_name']}** (`{m['technical_name']}`) - {m['purpose']}")

    lines.append("\n## Required Custom Modules")
    for m in odoo_requirements["modules"]:
        lines.append(f"\n### {m['module_name']}")
        lines.append(f"**Technical Name:** `{m['technical_name']}`  ")
        lines.append(f"**Type:** {m['type']}  ")
        lines.append(f"**Classification:** {m['classification']} - {m['classification_note']}  ")
        lines.append(f"**Purpose:** {m['purpose']}\n")
        lines.append("**Features Required:**")
        lines.extend(f"- {f}" for f in m["required_features"])
        lines.append("\n**API Requirements:**")
        lines.extend(f"- {a}" for a in m["api_requirements"])
        lines.append(f"\n**Data Structure (input):** `{m['input_data']}`")
        lines.append(f"\n**Output Behavior:** {m['output_behavior']}")
        lines.append(f"\n**Dependencies:** {', '.join(f'`{d}`' for d in m['dependencies']) or 'none'}")
        lines.append(f"\n**Priority:** {m['priority']} (Phase {m['phase']})")
        lines.append(f"\n**Course Features Depending On It:** {', '.join(m['required_by_course_features'])}")

    lines.append("\n## Module Dependency Graph")
    lines.append("See `MODULE_DEPENDENCY_GRAPH.md` for the full graph.")

    lines.append("\n## Phase 1 Requirements")
    lines.append("Modules without which the enhanced course cannot function.")
    if odoo_requirements["phases"]["phase_1_required"]:
        lines.extend(f"- `{m}`" for m in odoo_requirements["phases"]["phase_1_required"])
    else:
        lines.append("_None._")

    lines.append("\n## Phase 2 Requirements")
    lines.append("Modules that significantly improve the learning experience.")
    if odoo_requirements["phases"]["phase_2_important"]:
        lines.extend(f"- `{m}`" for m in odoo_requirements["phases"]["phase_2_important"])
    else:
        lines.append("_None for this course._")

    lines.append("\n## Phase 3 Optional Features")
    if odoo_requirements["phases"]["phase_3_optional"]:
        lines.extend(f"- `{m}`" for m in odoo_requirements["phases"]["phase_3_optional"])
    else:
        lines.append("_None for this course._")

    lines.append("\n## Developer Handoff Checklist")
    lines.append("- [ ] Review `requirements/odoo-requirements.json` (machine-readable version of this document)")
    lines.append("- [ ] Review `requirements/lms-capabilities.json` for the LMS-agnostic capability list")
    lines.append("- [ ] Confirm classification of each module (A/B/C/D) against the actual target Odoo instance's installed apps")
    lines.append("- [ ] Scaffold Phase 1 modules first; nothing in the enhancement package can render without them")
    lines.append("- [ ] Build an import adapter that reads `enhancement-package.json` into `course_enhancer_core`'s data model")
    lines.append("- [ ] Confirm accessibility_description / on-screen-text fields are surfaced in each renderer's UI")
    lines.append("- [ ] Video/audio modules only need to store+play; actual video/audio production is a separate pipeline")

    return "\n".join(lines) + "\n"


def render_module_dependency_graph_report(dependency_graph: dict, odoo_requirements: dict) -> str:
    lines = ["# MODULE DEPENDENCY GRAPH", f"\n_Course: {dependency_graph['course_id']}. Generated {_now()}._\n"]

    if not dependency_graph["nodes"]:
        lines.append("No custom Odoo modules are required for this course's enhancement package.")
        return "\n".join(lines) + "\n"

    lines.append("## Mermaid Graph\n")
    lines.append("```mermaid")
    lines.append("graph TD")
    for node in dependency_graph["nodes"]:
        lines.append(f"    {node['technical_name']}[\"{node['technical_name']} (Phase {node['phase']})\"]")
    for edge in dependency_graph["edges"]:
        lines.append(f"    {edge['from']} --> {edge['to']}")
    lines.append("```\n")

    lines.append("## Text Tree\n")
    lines.append("```")
    lines.append("course_enhancer_core")
    children = {}
    for edge in dependency_graph["edges"]:
        children.setdefault(edge["from"], []).append(edge["to"])
    seen = {"course_enhancer_core"}

    def walk(name, depth):
        for child in children.get(name, []):
            if child in seen:
                continue
            seen.add(child)
            lines.append("    " * depth + f"+-- {child}")
            walk(child, depth + 1)

    walk("course_enhancer_core", 1)
    lines.append("```\n")

    lines.append("## Phase Grouping")
    for phase_key, label in (
        ("phase_1_required", "Phase 1 — Required"),
        ("phase_2_important", "Phase 2 — Important"),
        ("phase_3_optional", "Phase 3 — Optional"),
    ):
        lines.append(f"\n**{label}:**")
        mods = odoo_requirements["phases"][phase_key]
        lines.extend(f"- `{m}`" for m in mods) if mods else lines.append("- _none_")

    return "\n".join(lines) + "\n"


def render_quality_report(built: dict) -> str:
    lines = ["# QUALITY REPORT", f"\n_Generated {_now()}._\n"]

    lines.append("## Accepted Enhancements")
    lines.append(f"{len(built['all_accepted'])} enhancement(s) passed quality validation.\n")
    lines.append("| Lesson | Type | Priority | Impact | Complexity | Checks Passed |")
    lines.append("|---|---|---|---|---|---|")
    for e in built["all_accepted"]:
        checks = e["quality"]["checks"]
        passed = sum(1 for v in checks.values() if v is True)
        lines.append(
            f"| {e['lesson_id']} | {e['enhancement_type']} | {e['priority']} | "
            f"{e['educational_impact']}/10 | {e['implementation_complexity']}/10 | {passed}/{len(checks)} |"
        )
        if e["quality"]["issues"]:
            for issue in e["quality"]["issues"]:
                lines.append(f"  - ⚠ {issue}")

    lines.append("\n## Suppressed / Rejected Candidates")
    if built["all_rejected"]:
        for e in built["all_rejected"]:
            lines.append(f"- `{e.get('enhancement_type')}` — {e.get('suppressed_reason', 'n/a')}")
    else:
        lines.append("_None suppressed._")

    lines.append("\n## Accessibility Review")
    acc = built["accessibility_review"]
    lines.append(f"Status: **{'PASS' if acc['pass'] else 'ISSUES FOUND'}** "
                  f"({acc['total_enhancements_reviewed']} enhancements reviewed)")
    if acc["findings"]:
        lines.append("\n| Lesson | Type | Severity | Issue |")
        lines.append("|---|---|---|---|")
        for f in acc["findings"]:
            lines.append(f"| {f['lesson_id']} | {f['enhancement_type']} | {f['severity']} | {f['issue']} |")
    else:
        lines.append("No accessibility issues found.")

    return "\n".join(lines) + "\n"
