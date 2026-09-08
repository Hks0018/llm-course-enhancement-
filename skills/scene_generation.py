from course_enhancer.video import split_into_scenes

SKILL = {"skill": "scene-generation", "source": "internal", "enabled": True, "dependencies": []}


def run(content: str, max_scenes: int = 8) -> dict:
    """Split lesson content into scene-sized chunks. Shared by video-script-generation
    and whiteboard-video-generation; independently callable for custom video pipelines."""
    scenes = split_into_scenes(content, max_scenes)
    return {"scene_count": len(scenes), "scenes_raw_text": scenes}
