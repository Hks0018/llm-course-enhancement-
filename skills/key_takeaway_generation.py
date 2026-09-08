from course_enhancer.content import generate_summary

SKILL = {"skill": "key-takeaway-generation", "source": "internal", "enabled": True, "dependencies": ["summary-generation"]}


def run(lesson: dict) -> dict:
    """Generate just the key-takeaways list for a lesson (independently callable
    from summary-generation, which returns both summary and takeaways together)."""
    summary = generate_summary(lesson)
    return {
        "enhancement_type": "key_takeaways",
        "lesson_id": lesson.get("id"),
        "key_takeaways": summary["key_takeaways"],
        "generation_method": summary["generation_method"],
    }
