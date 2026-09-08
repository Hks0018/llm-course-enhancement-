from course_enhancer.analysis import analyze_lesson
from course_enhancer.decision import decide_enhancements

SKILL = {"skill": "enhancement-decision", "source": "internal", "enabled": True, "dependencies": ["course-analysis"]}


def run(lesson: dict, course_objectives: list = None, signals: dict = None) -> dict:
    """Decide which enhancement(s), if any, a lesson needs. May return
    sufficient=True with zero candidates - that is a valid, expected result."""
    signals = signals or analyze_lesson(lesson, course_objectives)
    return decide_enhancements(lesson, signals)
