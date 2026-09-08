from course_enhancer.interactive import (
    generate_knowledge_check, generate_true_false, generate_matching_exercise, generate_scenario_exercise,
)

SKILL = {"skill": "interactive-learning-generation", "source": "internal", "enabled": True, "dependencies": []}

_DISPATCH = {
    "multiple_choice": generate_knowledge_check,
    "true_false": generate_true_false,
    "matching": generate_matching_exercise,
    "scenario_question": generate_scenario_exercise,
}


def run(lesson: dict, interaction_type: str = "multiple_choice") -> dict:
    """Generate structured content + configuration for an interactive component.
    The LMS renders the interaction; this skill only produces its content."""
    generator = _DISPATCH.get(interaction_type, generate_knowledge_check)
    return generator(lesson)
