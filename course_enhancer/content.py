"""Backs summary-generation, key-takeaway-generation, example-generation,
and case-study-generation.

Summaries/takeaways are purely extractive (built only from sentences that
already exist in the lesson) so nothing is invented. Examples/case studies
that need real-world facts the lesson doesn't contain are returned as
clearly-labeled scaffolds for an author/SME to fill in, per the "never
invent unsupported facts" rule.
"""
from __future__ import annotations

import re
from collections import Counter

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been", "to",
    "of", "in", "on", "for", "with", "as", "by", "that", "this", "it", "at", "from", "you",
    "your", "will", "can", "which", "these", "those", "into", "than", "then", "not", "if",
    "when", "so", "such", "also", "more", "most", "some", "each", "their", "its",
}


def _significant_words(text: str):
    return [w.lower() for w in re.findall(r"[A-Za-z']+", text) if w.lower() not in _STOPWORDS and len(w) > 2]


def generate_summary(lesson: dict, max_sentences: int = 4) -> dict:
    content = lesson.get("content", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
    if not sentences:
        return {
            "enhancement_type": "summary_and_key_takeaways",
            "summary": "",
            "key_takeaways": [],
            "notes": ["Lesson has no content to summarize."],
        }

    freq = Counter()
    for s in sentences:
        freq.update(_significant_words(s))

    def score(sentence, index):
        words = _significant_words(sentence)
        base = sum(freq[w] for w in words) / (len(words) or 1)
        position_bonus = 1.15 if index == 0 else 1.0
        return base * position_bonus

    ranked = sorted(range(len(sentences)), key=lambda i: score(sentences[i], i), reverse=True)
    top_indices = sorted(ranked[:max_sentences])
    summary_sentences = [sentences[i] for i in top_indices]

    takeaway_indices = sorted(ranked[:min(5, len(sentences))])
    key_takeaways = [sentences[i] for i in takeaway_indices]

    return {
        "enhancement_type": "summary_and_key_takeaways",
        "title": f"Summary: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Gives learners a closing checkpoint to confirm understanding without re-reading the "
            "full lesson, and gives reviewers a fast way to verify content coverage."
        ),
        "summary": " ".join(summary_sentences),
        "key_takeaways": key_takeaways,
        "generation_method": "extractive_frequency_ranking",
        "notes": ["Summary is extractive (built only from sentences already in the lesson)."],
    }


def generate_example(lesson: dict) -> dict:
    from course_enhancer.interactive import extract_definitions

    definitions = extract_definitions(lesson.get("content", ""))
    if definitions:
        term, definition = definitions[0]
        return {
            "enhancement_type": "example",
            "title": f"Worked Example: {term}",
            "educational_purpose": "Grounds the abstract definition in a concrete, applied instance.",
            "concept": term,
            "definition_from_lesson": definition,
            "example_scaffold": (
                f"[author: give one concrete instance of \"{term}\" in action, showing how the "
                f"definition — \"{definition}\" — plays out in practice]"
            ),
            "generation_method": "template_scaffold",
            "requires_subject_matter_review": True,
            "notes": ["Concept and definition are grounded in lesson text; the example itself needs author input."],
        }
    return {
        "enhancement_type": "example",
        "title": f"Worked Example: {lesson.get('title', 'Lesson')}",
        "educational_purpose": "Grounds the lesson's core idea in a concrete instance.",
        "concept": lesson.get("title", "Lesson"),
        "example_scaffold": "[author: add one concrete, realistic example illustrating this lesson's core idea]",
        "generation_method": "template_scaffold",
        "requires_subject_matter_review": True,
        "notes": ["No definitional statement found to anchor the example to; fully author-authored scaffold."],
    }


def generate_case_study(lesson: dict) -> dict:
    objective = (lesson.get("learning_objectives") or [None])[0]
    return {
        "enhancement_type": "case_study",
        "title": f"Case Study: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Case studies build transfer by requiring learners to apply multiple ideas from the "
            "lesson to a single, realistic, multi-part situation."
        ),
        "learning_objective": objective,
        "context_scaffold": "[author: describe a real or realistic organization/situation]",
        "challenge_scaffold": "[author: state the problem that requires applying this lesson's content]",
        "discussion_questions": [
            f"[author: question requiring application of \"{lesson.get('title', 'this lesson')}\"]",
            "[author: question requiring learners to justify a trade-off]",
        ],
        "generation_method": "template_scaffold",
        "requires_subject_matter_review": True,
        "notes": [
            "Case studies require real, verifiable facts that cannot be safely invented; this is a "
            "structural scaffold only, not populated content."
        ],
    }
