from course_enhancer.mermaid import generate_concept_diagram, generate_sequence_diagram

SKILL = {
    "skill": "concept-diagram-generation", "source": "internal", "enabled": True,
    "dependencies": ["mermaid-diagram-generation"],
}


def run(lesson: dict, mode: str = "concept") -> dict:
    """Generate a Mermaid diagram for abstract concept relationships (mode='concept')
    or multi-actor system interactions (mode='sequence')."""
    if mode == "sequence":
        return generate_sequence_diagram(lesson)
    return generate_concept_diagram(lesson)
