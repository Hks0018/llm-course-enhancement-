from course_enhancer.mermaid import generate_timeline

SKILL = {
    "skill": "timeline-generation", "source": "internal", "enabled": True,
    "dependencies": ["mermaid-diagram-generation"],
}


def run(lesson: dict) -> dict:
    """Generate a Mermaid timeline for chronological or staged content in a lesson."""
    return generate_timeline(lesson)
