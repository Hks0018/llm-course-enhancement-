from course_enhancer.mermaid import generate_mind_map

SKILL = {
    "skill": "mind-map-generation", "source": "internal", "enabled": True,
    "dependencies": ["mermaid-diagram-generation"],
}


def run(lesson: dict, terms: list = None) -> dict:
    """Generate a Mermaid mind map connecting a lesson's key terms to its central topic."""
    return generate_mind_map(lesson, terms)
