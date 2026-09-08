from course_enhancer.quality import validate_enhancement, filter_candidates

SKILL = {"skill": "quality-validation", "source": "internal", "enabled": True, "dependencies": []}


def run(candidate: dict = None, generated: dict = None, lesson_signals: dict = None, candidates: list = None) -> dict:
    """Two modes: pass `candidates` (a list of decision-engine outputs) to dedupe
    + cap them, or pass `candidate`/`generated`/`lesson_signals` to validate one
    already-generated enhancement's quality."""
    if candidates is not None:
        return filter_candidates(candidates)
    return validate_enhancement(candidate, generated, lesson_signals)
