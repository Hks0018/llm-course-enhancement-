from course_enhancer.mermaid import validate_mermaid

SKILL = {"skill": "mermaid-diagram-generation", "source": "internal", "enabled": True, "dependencies": []}


def run(mermaid_code: str) -> dict:
    """Generic Mermaid validation layer - every diagram-producing skill
    (flowchart, decision-tree, mind-map, timeline, concept-diagram) routes
    its output through this before it is considered final."""
    return validate_mermaid(mermaid_code)
