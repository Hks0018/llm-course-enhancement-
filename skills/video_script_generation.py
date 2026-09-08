from course_enhancer.video import generate_video_package

SKILL = {
    "skill": "video-script-generation", "source": "internal", "enabled": True,
    "dependencies": ["scene-generation"],
}


def run(lesson: dict) -> dict:
    """Generate a video package (script, storyboard, scenes) for a lesson that
    warrants a demonstrative video explanation."""
    return generate_video_package(lesson)
