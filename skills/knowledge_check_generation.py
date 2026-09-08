from course_enhancer.interactive import generate_knowledge_check

SKILL = {
    "skill": "knowledge-check-generation", "source": "internal", "enabled": True,
    "dependencies": ["interactive-learning-generation"],
}


def run(lesson: dict) -> dict:
    """Generate a multiple-choice knowledge check grounded in the lesson's own definitions."""
    return generate_knowledge_check(lesson)
