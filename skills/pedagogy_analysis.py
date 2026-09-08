from course_enhancer.analysis import analyze_lesson

SKILL = {"skill": "pedagogy-analysis", "source": "internal", "enabled": True, "dependencies": ["course-analysis"]}


def run(lesson: dict, course_objectives: list = None) -> dict:
    """Pedagogy-focused view of a lesson: objective alignment, classification,
    and the specific gaps (clarity/example/retention/etc.) detected."""
    signals = analyze_lesson(lesson, course_objectives)
    return {
        "lesson_id": lesson.get("id"),
        "objective_alignment_score": signals["objective_alignment_score"],
        "classification": signals["classification"],
        "cognitive_load": signals["cognitive_load"],
        "full_signals": signals,
    }
