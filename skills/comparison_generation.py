from course_enhancer.comparison import build_comparison_table

SKILL = {"skill": "comparison-generation", "source": "internal", "enabled": True, "dependencies": []}


def run(lesson: dict) -> dict:
    """Generate a comparison table for two or more items discussed in a lesson."""
    return build_comparison_table(lesson)
