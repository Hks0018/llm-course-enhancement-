from course_enhancer.video import generate_voiceover_package

SKILL = {
    "skill": "voiceover-generation", "source": "internal", "enabled": True,
    "dependencies": ["video-script-generation", "scene-generation"],
}


def run(lesson: dict, video_package: dict = None) -> dict:
    """Generate a narration script + timing/asset metadata for a lesson's video
    package. Produces metadata only - actual audio synthesis is a separate step;
    see assets/voiceovers/ naming convention in the output."""
    return generate_voiceover_package(lesson, video_package)
