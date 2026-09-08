from course_enhancer.quality import accessibility_review

SKILL = {"skill": "accessibility-review", "source": "internal", "enabled": True, "dependencies": ["quality-validation"]}


def run(enhancements: list) -> dict:
    """Sweep a list of generated enhancements for missing accessible-alternative
    content (alt text, captions/on-screen text, explanations)."""
    return accessibility_review(enhancements)
