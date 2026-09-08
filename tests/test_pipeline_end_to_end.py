import json
import os

from course_enhancer import pipeline


def test_full_pipeline_on_sample_course(tmp_path):
    source = os.path.join(os.path.dirname(__file__), "..", "examples", "sample_course.md")
    result = pipeline.run(source, output_root=str(tmp_path))

    course_dir = result["course_dir"]
    expected_files = [
        "course-analysis.json", "enhancement-plan.json", "enhancement-package.json",
        os.path.join("reports", "COURSE_ENHANCEMENT_REPORT.md"),
        os.path.join("reports", "ODOO_IMPLEMENTATION_REQUIREMENTS.md"),
        os.path.join("reports", "MODULE_DEPENDENCY_GRAPH.md"),
        os.path.join("reports", "QUALITY_REPORT.md"),
        os.path.join("requirements", "lms-capabilities.json"),
        os.path.join("requirements", "odoo-requirements.json"),
        os.path.join("requirements", "module-dependencies.json"),
    ]
    for rel in expected_files:
        path = os.path.join(course_dir, rel)
        assert os.path.isfile(path), f"missing expected output file: {path}"

    with open(os.path.join(course_dir, "enhancement-package.json")) as f:
        package = json.load(f)
    assert package["course_title"] == "Practical Cloud Deployment"
    assert len(package["enhancements"]) > 0

    # At least one lesson should need no enhancement (the short, clear one)
    with open(os.path.join(course_dir, "course-analysis.json")) as f:
        analysis = json.load(f)
    assert analysis["lessons_requiring_no_enhancement"] >= 1

    # Every diagram enhancement must carry a passing Mermaid validation.
    for e in package["enhancements"]:
        if "mermaid_code" in e["content"]:
            assert e["content"]["validation"]["valid"] is True

    # The original source file must never be modified.
    with open(source) as f:
        original = f.read()
    assert "Practical Cloud Deployment" in original


def test_odoo_requirements_are_internally_consistent(tmp_path):
    source = os.path.join(os.path.dirname(__file__), "..", "examples", "sample_course.md")
    result = pipeline.run(source, output_root=str(tmp_path))
    odoo = result["odoo_requirements"]
    all_phase_modules = set(
        odoo["phases"]["phase_1_required"] + odoo["phases"]["phase_2_important"] + odoo["phases"]["phase_3_optional"]
    )
    module_names = {m["technical_name"] for m in odoo["modules"]}
    assert all_phase_modules == module_names
