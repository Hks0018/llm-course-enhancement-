from course_enhancer.analysis import analyze_lesson

SKILL = {"skill": "course-analysis", "source": "internal", "enabled": True, "dependencies": []}


def run(lesson: dict, course_objectives: list = None) -> dict:
    """Analyze one lesson's structure, complexity, and content signals."""
    return analyze_lesson(lesson, course_objectives)
