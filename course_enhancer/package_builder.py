"""Orchestrates one lesson (and then a whole course) through:
analysis -> decision -> quality filtering -> content generation -> quality
validation, and assembles the three top-level deliverables described in the
spec: course-analysis.json, enhancement-plan.json, enhancement-package.json.

This is the module the CLI/pipeline calls; it is also what each of the 24
skills in skills/ ultimately delegates into, so the skills stay thin.
"""
from __future__ import annotations

from course_enhancer import analysis as analysis_mod
from course_enhancer import decision as decision_mod
from course_enhancer import quality as quality_mod
from course_enhancer import mermaid, comparison, interactive, content, video
from course_enhancer.schema import iter_lessons, lesson_count


def _structural_recommendation_content(candidate: dict, lesson: dict) -> dict:
    return {
        "enhancement_type": "structural_recommendation",
        "title": f"Restructuring recommendation: {lesson.get('title', 'Lesson')}",
        "educational_purpose": candidate["rationale"],
        "recommendation": (
            "Split this lesson into labeled sub-sections (add headings every ~150-200 words) "
            "before or alongside any other enhancement - dense unstructured text undermines "
            "every other enhancement layered on top of it."
        ),
        "evidence": candidate["evidence"],
        "notes": [],
    }


GENERATORS = {
    "flowchart": lambda c, l: mermaid.generate_flowchart(l),
    "decision_tree": lambda c, l: mermaid.generate_decision_tree(l),
    "mind_map": lambda c, l: mermaid.generate_mind_map(l),
    "timeline": lambda c, l: mermaid.generate_timeline(l),
    "concept_diagram": lambda c, l: mermaid.generate_concept_diagram(l),
    "sequence_diagram": lambda c, l: mermaid.generate_sequence_diagram(l),
    "comparison_table": lambda c, l: comparison.build_comparison_table(l),
    "knowledge_check": lambda c, l: interactive.generate_knowledge_check(l),
    "scenario_exercise": lambda c, l: interactive.generate_scenario_exercise(l),
    "example": lambda c, l: content.generate_example(l),
    "summary_and_key_takeaways": lambda c, l: content.generate_summary(l),
    "video_explanation": lambda c, l: video.generate_video_package(l),
    "structural_recommendation": _structural_recommendation_content,
}


def process_lesson(lesson: dict, course_objectives=None) -> dict:
    signals = analysis_mod.analyze_lesson(lesson, course_objectives)
    decision = decision_mod.decide_enhancements(lesson, signals)
    filtered = quality_mod.filter_candidates(decision["candidates"])

    accepted = []
    rejected = list(filtered["rejected"])
    video_companions = {"whiteboard_video": [], "voiceover": []}

    for candidate in filtered["accepted"]:
        generator = GENERATORS.get(candidate["enhancement_type"])
        if generator is None:
            rejected.append({**candidate, "suppressed_reason": "No generator registered for this type."})
            continue
        generated = generator(candidate, lesson)
        qa = quality_mod.validate_enhancement(candidate, generated, signals)
        if not qa["passed"]:
            rejected.append({**candidate, "suppressed_reason": f"Failed quality validation: {qa['issues']}"})
            continue
        entry = {**candidate, "lesson_id": lesson["id"], "generated": generated, "quality": qa}
        accepted.append(entry)

        if candidate["enhancement_type"] == "video_explanation":
            wb = video.generate_whiteboard_video_package(lesson, generated)
            vo = video.generate_voiceover_package(lesson, generated)
            video_companions["whiteboard_video"].append({"lesson_id": lesson["id"], "generated": wb})
            video_companions["voiceover"].append({"lesson_id": lesson["id"], "generated": vo})

    return {
        "lesson_id": lesson["id"],
        "lesson_title": lesson["title"],
        "analysis": signals,
        "sufficient": decision["sufficient"],
        "no_enhancement_reason": decision["no_enhancement_reason"],
        "accepted_enhancements": accepted,
        "rejected_enhancements": rejected,
        "video_companions": video_companions,
    }


def build_course_package(normalized_course: dict) -> dict:
    course = normalized_course["course"]
    course_objectives = course.get("learning_objectives", [])

    lesson_results = []
    for module, lesson in iter_lessons(normalized_course):
        result = process_lesson(lesson, course_objectives)
        result["module_id"] = module["id"]
        result["module_title"] = module["title"]
        lesson_results.append(result)

    all_accepted = [e for r in lesson_results for e in r["accepted_enhancements"]]
    all_rejected = [e for r in lesson_results for e in r["rejected_enhancements"]]
    all_whiteboard = [w for r in lesson_results for w in r["video_companions"]["whiteboard_video"]]
    all_voiceover = [w for r in lesson_results for w in r["video_companions"]["voiceover"]]

    accessibility = quality_mod.accessibility_review(all_accepted)

    total_lessons = lesson_count(normalized_course)
    sufficient_count = sum(1 for r in lesson_results if r["sufficient"])

    course_analysis = {
        "course_title": course["title"],
        "course_description": course.get("description", ""),
        "course_learning_objectives": course_objectives,
        "total_modules": len(normalized_course["modules"]),
        "total_lessons": total_lessons,
        "lessons_requiring_no_enhancement": sufficient_count,
        "lessons_with_recommendations": total_lessons - sufficient_count,
        "lessons": [
            {
                "lesson_id": r["lesson_id"],
                "module_id": r["module_id"],
                "lesson_title": r["lesson_title"],
                "analysis": r["analysis"],
                "sufficient": r["sufficient"],
            }
            for r in lesson_results
        ],
    }

    enhancement_plan = {
        "course_title": course["title"],
        "total_lessons": total_lessons,
        "lessons": [
            {
                "lesson_id": r["lesson_id"],
                "module_id": r["module_id"],
                "lesson_title": r["lesson_title"],
                "sufficient": r["sufficient"],
                "no_enhancement_reason": r["no_enhancement_reason"],
                "recommended_enhancements": [
                    {
                        "enhancement_type": e["enhancement_type"],
                        "trigger": e["trigger"],
                        "evidence": e["evidence"],
                        "rationale": e["rationale"],
                        "educational_impact": e["educational_impact"],
                        "implementation_complexity": e["implementation_complexity"],
                        "priority": e["priority"],
                    }
                    for e in r["accepted_enhancements"]
                ],
                "suppressed_enhancements": [
                    {
                        "enhancement_type": e["enhancement_type"],
                        "trigger": e.get("trigger"),
                        "reason_suppressed": e.get("suppressed_reason"),
                    }
                    for e in r["rejected_enhancements"]
                ],
            }
            for r in lesson_results
        ],
    }

    enhancement_package = {
        "course_id": course["title"].lower().replace(" ", "-"),
        "course_title": course["title"],
        "analysis_summary": {
            "total_lessons": total_lessons,
            "lessons_requiring_no_enhancement": sufficient_count,
            "lessons_with_recommendations": total_lessons - sufficient_count,
        },
        "enhancements": [
            {
                "lesson_id": e["lesson_id"],
                "enhancement_type": e["enhancement_type"],
                "priority": e["priority"],
                "educational_impact": e["educational_impact"],
                "implementation_complexity": e["implementation_complexity"],
                "content": e["generated"],
            }
            for e in all_accepted
        ],
        "assets": {
            "diagrams": [e for e in all_accepted if "mermaid_code" in e["generated"]],
        },
        "interactive_components": [
            e for e in all_accepted
            if e["enhancement_type"] in ("knowledge_check", "scenario_exercise")
        ],
        "video_packages": [e for e in all_accepted if e["enhancement_type"] == "video_explanation"],
        "whiteboard_video_packages": all_whiteboard,
        "voiceover_packages": all_voiceover,
        "implementation_requirements": [],  # filled in by requirements_engine
        "accessibility_review": accessibility,
    }

    return {
        "course_analysis": course_analysis,
        "enhancement_plan": enhancement_plan,
        "enhancement_package": enhancement_package,
        "lesson_results": lesson_results,
        "all_accepted": all_accepted,
        "all_rejected": all_rejected,
        "accessibility_review": accessibility,
    }
