from course_enhancer.requirements_engine import (
    required_modules_for, build_odoo_requirements, build_lms_capabilities, build_module_dependency_graph,
)


def _package(enhancement_types):
    return {
        "course_id": "test-course",
        "enhancements": [{"enhancement_type": t} for t in enhancement_types],
        "video_packages": [{"lesson_id": "l1"}] if "video_explanation" in enhancement_types else [],
        "whiteboard_video_packages": [],
        "voiceover_packages": [{"lesson_id": "l1"}] if "voiceover" in enhancement_types else [],
    }


def test_no_enhancements_requires_no_modules():
    pkg = _package([])
    assert required_modules_for(pkg) == set()
    odoo = build_odoo_requirements(pkg)
    assert odoo["modules"] == []
    assert odoo["phases"]["phase_1_required"] == []


def test_flowchart_requires_mermaid_and_core_and_assets():
    pkg = _package(["flowchart"])
    modules = required_modules_for(pkg)
    assert "course_enhancer_mermaid" in modules
    assert "course_enhancer_core" in modules
    assert "course_enhancer_assets" in modules
    assert "course_enhancer_video" not in modules
    assert "course_enhancer_audio" not in modules


def test_knowledge_check_pulls_in_interactive_dependency():
    pkg = _package(["knowledge_check"])
    modules = required_modules_for(pkg)
    assert "course_enhancer_quiz" in modules
    assert "course_enhancer_interactive" in modules  # transitive dependency
    assert "course_enhancer_analytics" in modules  # interactive triggers analytics


def test_video_requires_video_and_audio_but_not_quiz():
    pkg = _package(["video_explanation", "voiceover"])
    modules = required_modules_for(pkg)
    assert "course_enhancer_video" in modules
    assert "course_enhancer_audio" in modules
    assert "course_enhancer_quiz" not in modules


def test_odoo_requirements_never_claims_existing_modules():
    pkg = _package(["flowchart", "knowledge_check"])
    odoo = build_odoo_requirements(pkg)
    for module in odoo["modules"]:
        assert module["type"] == "Recommended Custom Odoo Module"


def test_dependency_graph_has_no_dangling_edges():
    pkg = _package(["flowchart", "knowledge_check", "video_explanation", "voiceover"])
    odoo = build_odoo_requirements(pkg)
    graph = build_module_dependency_graph(odoo)
    node_names = {n["technical_name"] for n in graph["nodes"]}
    for edge in graph["edges"]:
        assert edge["from"] in node_names
        assert edge["to"] in node_names


def test_lms_capabilities_only_lists_whats_actually_required():
    pkg = _package(["comparison_table"])
    caps = build_lms_capabilities(pkg)
    tech_names = {c["technical_module_name"] for c in caps["required_capabilities"]}
    assert "course_enhancer_comparison" in tech_names
    assert "course_enhancer_video" not in tech_names
    assert "course_enhancer_quiz" not in tech_names
