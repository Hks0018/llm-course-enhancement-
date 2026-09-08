from course_enhancer.content import generate_summary

SKILL = {"skill": "summary-generation", "source": "internal", "enabled": True, "dependencies": []}


def run(lesson: dict, max_sentences: int = 4) -> dict:
    """Generate an extractive summary + key takeaways for a long lesson."""
    return generate_summary(lesson, max_sentences)
