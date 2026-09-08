"""Backs video-script-generation, whiteboard-video-generation,
scene-generation, and voiceover-generation.

Everything here produces a structured PACKAGE (script/storyboard/voiceover
metadata) - never a rendered video or audio file. Actually producing pixels
or audio is explicitly a downstream renderer's job (see README); this
engine's job stops at a package an LMS or a video-production adapter can
consume. Voiceover audio file paths are generated as a naming convention
only (assets/voiceovers/<lesson_id>/scene_NN.mp3) - the files themselves are
not created here.
"""
from __future__ import annotations

import re

WORDS_PER_MINUTE = 150
MAX_SCENES = 8
MIN_SCENE_SECONDS = 4
MAX_SCENE_SECONDS = 20

_DEFINITION_RE = re.compile(r"\b(is defined as|refers to|means that|is known as)\b", re.I)
_PROCESS_RE = re.compile(r"^\s*\d+[\.\)]\s+", re.M)
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")


def _duration_for(word_count: int) -> int:
    seconds = round((word_count / WORDS_PER_MINUTE) * 60)
    return max(MIN_SCENE_SECONDS, min(MAX_SCENE_SECONDS, seconds))


def split_into_scenes(content: str, max_scenes: int = MAX_SCENES) -> list:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if len(paragraphs) <= 1:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
        chunks, current = [], []
        for s in sentences:
            current.append(s)
            if sum(len(c.split()) for c in current) >= 35:
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))
        paragraphs = chunks or [content.strip()]
    return paragraphs[:max_scenes]


def _visual_description(text: str) -> str:
    if _DEFINITION_RE.search(text):
        return "Display the key term in large text with its definition appearing below it."
    if _PROCESS_RE.search(text) or re.match(r"^\s*\d", text):
        return "Show a numbered step indicator with a simple icon representing the action described."
    if re.search(r"\b(vs\.?|versus|compared to)\b", text, re.I):
        return "Split-screen layout contrasting the two items being compared."
    return "Display supporting text and a simple illustration matching the narration."


def _animation_instructions(index: int, text: str) -> str:
    base = "Fade in on-screen text, " if index == 0 else "Transition from previous scene, "
    if _DEFINITION_RE.search(text):
        return base + "highlight the defined term in the accent color, hold for reading time."
    if _PROCESS_RE.search(text):
        return base + "animate the step number counting up, then reveal the step text."
    return base + "reveal supporting text line by line, synced to narration pacing."


def generate_video_package(lesson: dict) -> dict:
    content = lesson.get("content", "")
    chunks = split_into_scenes(content)
    scenes = []
    for i, chunk in enumerate(chunks, start=1):
        word_count = len(chunk.split())
        duration = _duration_for(word_count)
        on_screen = chunk.split(".")[0].strip()
        on_screen = (on_screen[:70] + "…") if len(on_screen) > 70 else on_screen
        scenes.append({
            "scene_number": i,
            "duration_seconds": duration,
            "voiceover": chunk,
            "on_screen_text": on_screen,
            "visual_description": _visual_description(chunk),
            "animation_instructions": _animation_instructions(i, chunk),
            "educational_purpose": (
                "Introduces the lesson's core idea" if i == 1
                else "Reinforces and builds on the preceding scene" if i < len(chunks)
                else "Closes the explanation and reinforces the key takeaway"
            ),
        })

    total_seconds = sum(s["duration_seconds"] for s in scenes)
    return {
        "enhancement_type": "video_explanation",
        "title": f"Explainer: {lesson.get('title', 'Lesson')}",
        "purpose": (
            "Demonstrates a concept that involves state changing over time or multiple "
            "interacting steps, where static text/diagrams lose the sequence."
        ),
        "recommended_style": "narrated explainer with on-screen text and simple motion graphics",
        "estimated_duration": f"{total_seconds}s (~{max(1, round(total_seconds/60))} min)",
        "scenes": scenes,
        "notes": ["Scenes are segmented from the lesson's own paragraphs/sentences; no new facts were added."],
    }


def generate_whiteboard_video_package(lesson: dict, video_package: dict = None) -> dict:
    video_package = video_package or generate_video_package(lesson)
    scenes = []
    for scene in video_package["scenes"]:
        text = scene["voiceover"]
        drawing_sequence = ["Draw title text for this scene at the top of the frame."]
        if _DEFINITION_RE.search(text):
            drawing_sequence += [
                "Sketch a simple icon representing the defined term.",
                "Write the definition text below the icon, one line at a time.",
            ]
        elif _PROCESS_RE.search(text) or scene["scene_number"] > 1:
            drawing_sequence += [
                f"Draw a numbered circle with '{scene['scene_number']}' inside it.",
                "Sketch a simple arrow or icon representing the action, then write the step text beside it.",
            ]
        else:
            drawing_sequence += ["Sketch a simple illustration matching the narration, then add supporting text."]

        scenes.append({
            "scene": scene["scene_number"],
            "voiceover": text,
            "drawing_sequence": drawing_sequence,
            "on_screen_text": [scene["on_screen_text"]],
            "duration_seconds": scene["duration_seconds"],
        })

    return {
        "enhancement_type": "whiteboard_video",
        "style": "whiteboard explainer",
        "title": video_package["title"],
        "educational_purpose": video_package["purpose"],
        "scenes": scenes,
        "notes": ["Derived from the same scene segmentation as the video_explanation package."],
    }


def generate_voiceover_package(lesson: dict, video_package: dict = None) -> dict:
    video_package = video_package or generate_video_package(lesson)
    scenes = []
    for scene in video_package["scenes"]:
        acronyms = sorted(set(_ACRONYM_RE.findall(scene["voiceover"])))
        scenes.append({
            "scene_number": scene["scene_number"],
            "narration_script": scene["voiceover"],
            "estimated_duration_seconds": scene["duration_seconds"],
            "pronunciation_notes": [f"Spell out or verify pronunciation of acronym: {a}" for a in acronyms],
            "pacing_instructions": "Deliver at a measured pace; pause briefly after the on-screen text appears.",
            "asset_path": f"assets/voiceovers/{lesson['id']}/scene_{scene['scene_number']:02d}.mp3",
        })

    return {
        "enhancement_type": "voiceover",
        "lesson_id": lesson["id"],
        "title": f"Voiceover script: {lesson.get('title', 'Lesson')}",
        "scenes": scenes,
        "notes": [
            "This package is the narration script + timing/asset metadata only. Actual audio "
            "synthesis/recording is a separate downstream step; the naming convention above is "
            "where the resulting audio files are expected to be placed once generated.",
        ],
    }
