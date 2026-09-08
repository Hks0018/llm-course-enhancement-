from course_enhancer.content import generate_case_study

SKILL = {"skill": "case-study-generation", "source": "internal", "enabled": True, "dependencies": ["example-generation"]}


def run(lesson: dict) -> dict:
    """Generate a case-study scaffold for a lesson (structure only - real facts
    must come from an author/SME, never invented)."""
    return generate_case_study(lesson)
