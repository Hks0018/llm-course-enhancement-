from course_enhancer.interactive import generate_scenario_exercise

SKILL = {
    "skill": "scenario-generation", "source": "internal", "enabled": True,
    "dependencies": ["interactive-learning-generation"],
}


def run(lesson: dict) -> dict:
    """Generate a practical scenario exercise testing applied understanding of a lesson."""
    return generate_scenario_exercise(lesson)
