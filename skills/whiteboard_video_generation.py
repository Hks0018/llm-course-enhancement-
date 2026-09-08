from course_enhancer.video import generate_whiteboard_video_package

SKILL = {
    "skill": "whiteboard-video-generation", "source": "internal", "enabled": True,
    "dependencies": ["video-script-generation", "scene-generation"],
}


def run(lesson: dict, video_package: dict = None) -> dict:
    """Generate whiteboard-style video instructions (drawing sequence, on-screen
    labels) for a lesson, reusing a video-script-generation package if provided."""
    return generate_whiteboard_video_package(lesson, video_package)
