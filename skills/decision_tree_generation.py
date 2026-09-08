from course_enhancer.mermaid import generate_decision_tree

SKILL = {
    "skill": "decision-tree-generation", "source": "internal", "enabled": True,
    "dependencies": ["mermaid-diagram-generation"],
}


def run(lesson: dict, pairs: list = None) -> dict:
    """Generate a Mermaid decision tree for branching/conditional logic described in a lesson."""
    return generate_decision_tree(lesson, pairs)
