"""End-to-end orchestration: normalize -> analyze/decide/generate/validate ->
requirements engine -> reports -> write the output/<course-slug>/ tree
described in the spec.
"""
from __future__ import annotations

import json
import os

from course_enhancer import normalize, package_builder, requirements_engine, reports, integrator
from course_enhancer.schema import validate_course, slugify


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run(source: str, output_root: str = "output", fmt: str = None, course_slug: str = None) -> dict:
    normalized = normalize.normalize(source, fmt)
    errors = validate_course(normalized)
    if errors:
        raise ValueError("Normalized course failed validation:\n- " + "\n- ".join(errors))

    slug = course_slug or slugify(normalized["course"]["title"], "course")
    course_dir = os.path.join(output_root, slug)

    built = package_builder.build_course_package(normalized)

    odoo_requirements = requirements_engine.build_odoo_requirements(built["enhancement_package"])
    lms_capabilities = requirements_engine.build_lms_capabilities(built["enhancement_package"])
    dependency_graph = requirements_engine.build_module_dependency_graph(odoo_requirements)
    built["enhancement_package"]["implementation_requirements"] = odoo_requirements["modules"]

    # --- top-level JSON deliverables ---
    _write_json(os.path.join(course_dir, "course-analysis.json"), built["course_analysis"])
    _write_json(os.path.join(course_dir, "enhancement-plan.json"), built["enhancement_plan"])
    _write_json(os.path.join(course_dir, "enhancement-package.json"), built["enhancement_package"])

    # --- requirements/ ---
    _write_json(os.path.join(course_dir, "requirements", "lms-capabilities.json"), lms_capabilities)
    _write_json(os.path.join(course_dir, "requirements", "odoo-requirements.json"), odoo_requirements)
    _write_json(os.path.join(course_dir, "requirements", "module-dependencies.json"), dependency_graph)

    # --- reports/ ---
    _write_text(
        os.path.join(course_dir, "reports", "COURSE_ENHANCEMENT_REPORT.md"),
        reports.render_course_enhancement_report(built, normalized),
    )
    _write_text(
        os.path.join(course_dir, "reports", "ODOO_IMPLEMENTATION_REQUIREMENTS.md"),
        reports.render_odoo_requirements_report(odoo_requirements, normalized["course"]["title"]),
    )
    _write_text(
        os.path.join(course_dir, "reports", "MODULE_DEPENDENCY_GRAPH.md"),
        reports.render_module_dependency_graph_report(dependency_graph, odoo_requirements),
    )
    _write_text(
        os.path.join(course_dir, "reports", "QUALITY_REPORT.md"),
        reports.render_quality_report(built),
    )

    # --- single-document deliverables (original content + enhancements
    #     merged inline, same format as the input; and the Odoo requirements
    #     report standalone) - the two files most callers actually want ---
    enhanced_course_text, enhanced_course_ext = integrator.render_enhanced_course(normalized, built)
    enhanced_course_path = os.path.join(course_dir, f"enhanced-course.{enhanced_course_ext}")
    _write_text(enhanced_course_path, enhanced_course_text)
    odoo_requirements_report_path = os.path.join(course_dir, "reports", "ODOO_IMPLEMENTATION_REQUIREMENTS.md")

    # --- assets/ (diagram sources, mind maps, video/voiceover packages as
    #     individual files - convenient for a downstream renderer to consume
    #     one file per asset instead of parsing the whole package) ---
    diagram_dir = os.path.join(course_dir, "assets", "diagrams")
    mindmap_dir = os.path.join(course_dir, "assets", "mindmaps")
    video_dir = os.path.join(course_dir, "assets", "videos")
    voiceover_dir = os.path.join(course_dir, "assets", "voiceovers")
    os.makedirs(diagram_dir, exist_ok=True)
    os.makedirs(mindmap_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)
    os.makedirs(voiceover_dir, exist_ok=True)

    for e in built["all_accepted"]:
        g = e["generated"]
        if "mermaid_code" in g:
            target_dir = mindmap_dir if e["enhancement_type"] == "mind_map" else diagram_dir
            fname = f"{e['lesson_id']}__{e['enhancement_type']}.mmd"
            _write_text(os.path.join(target_dir, fname), g["mermaid_code"] + "\n")
        if e["enhancement_type"] == "video_explanation":
            _write_json(os.path.join(video_dir, f"{e['lesson_id']}__video_script.json"), g)

    for w in built["enhancement_package"]["whiteboard_video_packages"]:
        _write_json(os.path.join(video_dir, f"{w['lesson_id']}__whiteboard.json"), w["generated"])
    for v in built["enhancement_package"]["voiceover_packages"]:
        _write_json(os.path.join(voiceover_dir, f"{v['lesson_id']}__voiceover.json"), v["generated"])

    return {
        "course_dir": course_dir,
        "normalized": normalized,
        "built": built,
        "odoo_requirements": odoo_requirements,
        "lms_capabilities": lms_capabilities,
        "dependency_graph": dependency_graph,
        "enhanced_course_path": enhanced_course_path,
        "odoo_requirements_report_path": odoo_requirements_report_path,
    }
