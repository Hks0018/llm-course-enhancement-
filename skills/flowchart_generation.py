from course_enhancer.mermaid import generate_flowchart

SKILL = {
    "skill": "flowchart-generation", "source": "internal", "enabled": True,
    "dependencies": ["mermaid-diagram-generation"],
}


def run(lesson: dict, steps: list = None) -> dict:
    """Generate a Mermaid flowchart for a multi-step process described in a lesson."""
    return generate_flowchart(lesson, steps)
