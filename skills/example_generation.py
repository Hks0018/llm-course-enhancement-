from course_enhancer.content import generate_example

SKILL = {"skill": "example-generation", "source": "internal", "enabled": True, "dependencies": []}


def run(lesson: dict) -> dict:
    """Generate a worked-example scaffold grounded in the lesson's own definitions."""
    return generate_example(lesson)
