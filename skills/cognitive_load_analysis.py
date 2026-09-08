from course_enhancer.analysis import analyze_lesson, cognitive_load_report

SKILL = {"skill": "cognitive-load-analysis", "source": "internal", "enabled": True, "dependencies": ["course-analysis"]}


def run(lesson: dict, course_objectives: list = None) -> dict:
    """Report a lesson's cognitive-load rating with the specific reasons behind it."""
    signals = analyze_lesson(lesson, course_objectives)
    return cognitive_load_report(signals)
