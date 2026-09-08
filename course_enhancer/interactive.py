"""Backs interactive-learning-generation, knowledge-check-generation, and
scenario-generation.

The engine generates CONTENT and CONFIGURATION for these interactions; the
LMS renders them (per the architecture boundary). Every option/answer is
derived from the lesson's own text - never fabricated - so when the lesson
doesn't contain enough material for a solid distractor, that's surfaced as
`requires_review: true` rather than invented.
"""
from __future__ import annotations

import re

_DEFINITION_RE = re.compile(
    r"([A-Z][\w\s\-]{2,40}?)\s+(?:is defined as|refers to|means that|is known as)\s+([^.]+)\.",
)


def extract_definitions(content: str):
    return [(m.group(1).strip(), m.group(2).strip()) for m in _DEFINITION_RE.finditer(content)]


def generate_knowledge_check(lesson: dict) -> dict:
    definitions = extract_definitions(lesson.get("content", ""))
    objective = (lesson.get("learning_objectives") or [None])[0]
    requires_review = False

    if definitions:
        term, definition = definitions[0]
        correct = definition
        distractor_pool = [d for t, d in definitions[1:]]
        while len(distractor_pool) < 3:
            distractor_pool.append("[author: add a plausible-but-incorrect alternative]")
            requires_review = True
        options = [correct] + distractor_pool[:3]
        question = f"According to this lesson, what does \"{term}\" refer to?"
    else:
        question = f"[author: write a knowledge-check question testing the core idea of \"{lesson.get('title', 'this lesson')}\"]"
        options = [
            "[author: correct answer, grounded in lesson content]",
            "[author: plausible distractor]",
            "[author: plausible distractor]",
            "[author: plausible distractor]",
        ]
        correct = options[0]
        requires_review = True

    return {
        "enhancement_type": "knowledge_check",
        "type": "multiple_choice",
        "question": question,
        "options": options,
        "correct_answer": correct,
        "explanation": (
            f"Restates the definition from the lesson: \"{correct}\"" if definitions
            else "[author: explain why the correct answer is correct, citing the lesson text]"
        ),
        "learning_objective": objective,
        "generation_method": "heuristic_extraction",
        "requires_subject_matter_review": requires_review,
        "notes": [
            "Fewer than 3 alternative definitions were available in this lesson to use as "
            "distractors; some options are placeholders for author input."
        ] if requires_review else [],
    }


def generate_true_false(lesson: dict) -> dict:
    content = lesson.get("content", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if 40 < len(s.strip()) < 180]
    if not sentences:
        sentences = [lesson.get("title", "This lesson covers an important concept.")]
    statement = sentences[0]

    negated, did_negate = _negate(statement)
    return {
        "enhancement_type": "knowledge_check",
        "type": "true_false",
        "question": negated,
        "correct_answer": "False" if did_negate else "True",
        "explanation": f"Original lesson text: \"{statement}\"",
        "learning_objective": (lesson.get("learning_objectives") or [None])[0],
        "generation_method": "heuristic_negation" if did_negate else "heuristic_verbatim",
        "requires_subject_matter_review": False,
    }


_NEGATION_PAIRS = [("always", "never"), ("can", "cannot"), ("is", "is not"), ("will", "will not")]


def _negate(sentence: str):
    for pos, neg in _NEGATION_PAIRS:
        pattern = re.compile(rf"\b{pos}\b", re.I)
        if pattern.search(sentence):
            return pattern.sub(neg, sentence, count=1), True
    return sentence, False


def generate_matching_exercise(lesson: dict) -> dict:
    definitions = extract_definitions(lesson.get("content", ""))
    requires_review = len(definitions) < 3
    pairs = [{"term": t, "match": d} for t, d in definitions[:6]]
    if not pairs:
        pairs = [{"term": "[author: term]", "match": "[author: definition]"} for _ in range(3)]
    return {
        "enhancement_type": "knowledge_check",
        "type": "matching",
        "instructions": "Match each term to its definition from the lesson.",
        "pairs": pairs,
        "explanation": "Pairs are drawn verbatim from definitional statements in the lesson.",
        "learning_objective": (lesson.get("learning_objectives") or [None])[0],
        "generation_method": "heuristic_extraction",
        "requires_subject_matter_review": requires_review,
        "notes": ["Fewer than 3 definitions found; matching exercise needs author-supplied pairs."] if requires_review else [],
    }


def generate_scenario_exercise(lesson: dict) -> dict:
    from course_enhancer.mermaid import extract_steps

    steps = extract_steps(lesson.get("content", ""))
    title = lesson.get("title", "this lesson")
    objective = (lesson.get("learning_objectives") or [None])[0]

    if steps:
        scenario = (
            f"You are applying what you learned in \"{title}\". A real situation calls for the "
            f"process described in this lesson."
        )
        prompt = f"Walk through what you would do, in order. (The lesson describes {len(steps)} steps.)"
        model_answer_guidance = "Steps in the order described in the lesson: " + " -> ".join(steps)
        requires_review = False
    else:
        scenario = f"[author: describe a realistic situation where a learner must apply \"{title}\"]"
        prompt = "[author: what should the learner decide or do, and why?]"
        model_answer_guidance = "[author: outline the reasoning a strong answer would include]"
        requires_review = True

    return {
        "enhancement_type": "scenario_exercise",
        "type": "scenario_question",
        "scenario": scenario,
        "prompt": prompt,
        "model_answer_guidance": model_answer_guidance,
        "explanation": model_answer_guidance,
        "learning_objective": objective,
        "generation_method": "heuristic_extraction" if steps else "template_scaffold",
        "requires_subject_matter_review": requires_review,
    }
