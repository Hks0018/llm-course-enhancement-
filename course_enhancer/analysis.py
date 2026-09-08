"""Course Analysis Engine: course-analysis, pedagogy-analysis, and
cognitive-load-analysis skills share this module's logic.

Every signal here is deterministic and evidence-based (regex/count driven)
so that every downstream enhancement decision can cite concrete evidence
("detected 5 numbered steps") instead of an unexplained judgment call.
"""
from __future__ import annotations

import re

NUMBERED_LIST_RE = re.compile(r"^\s*\d+[\.\)]\s+", re.M)
BULLET_LIST_RE = re.compile(r"^\s*[-*•]\s+", re.M)
HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.M)
COMPARISON_RE = re.compile(
    r"\b(vs\.?|versus|compared to|in contrast|on the other hand|whereas|difference between|"
    r"better than|worse than)\b", re.I,
)
CONDITION_RE = re.compile(r"\b(if\s|when\s|depending on|in case|unless\s|either\s.+\bor\b)\b", re.I)
SEQUENCE_RE = re.compile(
    r"\b(first,|firstly|first step|then,|next,|after that|finally,|lastly,|step\s+\d|"
    r"\d(st|nd|rd|th)\s+step)\b", re.I,
)
EXAMPLE_RE = re.compile(r"\b(for example|for instance|e\.g\.|such as|case in point|imagine)\b", re.I)
RELATIONSHIP_RE = re.compile(
    r"\b(relates to|related to|connected to|connects to|depends on|part of|consists of|"
    r"is a type of|belongs to|leads to|results in)\b", re.I,
)
DEFINITION_RE = re.compile(r"\b(is defined as|refers to|means that|is a term for|is known as)\b", re.I)
SYSTEM_WORDS_RE = re.compile(
    r"\b(api|request|response|client|server|endpoint|database|sends?|receives?|calls?\s+the|"
    r"returns?\s+a|webhook)\b", re.I,
)
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
CAPITALIZED_TERM_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,}){0,2})\b")

MIN_WORDS_FOR_ANY_ENHANCEMENT = 25
LONG_LESSON_WORD_THRESHOLD = 350


def _sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _words(text: str):
    return re.findall(r"[A-Za-z']+", text)


def analyze_lesson(lesson: dict, course_objectives=None) -> dict:
    content = lesson.get("content", "") or ""
    words = _words(content)
    sentences = _sentences(content)
    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    avg_sentence_len = word_count / sentence_count

    numbered_items = len(NUMBERED_LIST_RE.findall(content))
    bullet_items = len(BULLET_LIST_RE.findall(content))
    heading_count = len(HEADING_LINE_RE.findall(content))

    comparison_hits = len(COMPARISON_RE.findall(content))
    condition_hits = len(CONDITION_RE.findall(content))
    sequence_hits = len(SEQUENCE_RE.findall(content))
    example_hits = len(EXAMPLE_RE.findall(content))
    relationship_hits = len(RELATIONSHIP_RE.findall(content))
    definition_hits = len(DEFINITION_RE.findall(content))
    system_hits = len(SYSTEM_WORDS_RE.findall(content))
    year_hits = len(set(YEAR_RE.findall(content)))

    long_words = [w for w in words if len(w) >= 12]
    jargon_density = len(long_words) / word_count if word_count else 0.0

    capitalized_terms = CAPITALIZED_TERM_RE.findall(content)
    distinct_term_count = len({t.lower() for t in capitalized_terms})

    objectives_text = " ".join((lesson.get("learning_objectives") or []) + (course_objectives or [])).lower()
    objective_alignment_score = 0.0
    if objectives_text:
        obj_words = {w.lower() for w in _words(objectives_text) if len(w) > 4}
        content_words = {w.lower() for w in words}
        if obj_words:
            objective_alignment_score = round(len(obj_words & content_words) / len(obj_words), 2)

    cognitive_load = _cognitive_load(avg_sentence_len, jargon_density, heading_count, word_count)

    signals = {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sentence_len, 1),
        "reading_time_minutes": round(max(word_count / 200.0, 0.1), 1),
        "numbered_list_items": numbered_items,
        "bullet_list_items": bullet_items,
        "heading_count": heading_count,
        "comparison_signal_hits": comparison_hits,
        "condition_signal_hits": condition_hits,
        "sequence_signal_hits": sequence_hits,
        "example_hits": example_hits,
        "relationship_signal_hits": relationship_hits,
        "definition_hits": definition_hits,
        "system_interaction_hits": system_hits,
        "distinct_year_mentions": year_hits,
        "jargon_density": round(jargon_density, 3),
        "distinct_capitalized_terms": distinct_term_count,
        "objective_alignment_score": objective_alignment_score,
        "cognitive_load": cognitive_load,
    }
    signals["classification"] = classify(signals)
    return signals


def _cognitive_load(avg_sentence_len, jargon_density, heading_count, word_count) -> str:
    score = 0
    if avg_sentence_len > 22:
        score += 1
    if avg_sentence_len > 30:
        score += 1
    if jargon_density > 0.08:
        score += 1
    if jargon_density > 0.15:
        score += 1
    if word_count > 250 and heading_count == 0:
        score += 1
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def classify(signals: dict) -> list:
    """Coarse classification tags used as a quick summary; the enhancement
    decision engine (decision.py) does the fine-grained, evidence-cited
    reasoning independently of these tags.
    """
    tags = []
    wc = signals["word_count"]

    if wc < MIN_WORDS_FOR_ANY_ENHANCEMENT:
        tags.append("text_sufficient")
        return tags

    if signals["objective_alignment_score"] and signals["objective_alignment_score"] < 0.15:
        tags.append("needs_clarification")
    if signals["example_hits"] == 0 and signals["definition_hits"] > 0:
        tags.append("needs_example")
    if signals["numbered_list_items"] >= 3 or signals["sequence_signal_hits"] >= 2:
        tags.append("needs_visualization")
    if signals["condition_signal_hits"] >= 2:
        tags.append("needs_visualization")
    if signals["comparison_signal_hits"] >= 2:
        tags.append("needs_visualization")
    if signals["cognitive_load"] == "high":
        tags.append("needs_restructuring")
    if signals["definition_hits"] >= 2 and wc > 120:
        tags.append("needs_knowledge_check")
    if wc > LONG_LESSON_WORD_THRESHOLD:
        tags.append("needs_summary")
    if signals["heading_count"] == 0 and wc > 250:
        tags.append("needs_restructuring")

    if not tags:
        tags.append("text_sufficient")
    return tags


def cognitive_load_report(signals: dict) -> dict:
    """cognitive-load-analysis skill output: explains *why* the load rating
    was assigned, in terms a course author can act on.
    """
    reasons = []
    if signals["avg_sentence_length"] > 22:
        reasons.append(f"average sentence length is {signals['avg_sentence_length']} words (>22 is dense)")
    if signals["jargon_density"] > 0.08:
        reasons.append(f"{signals['jargon_density']*100:.1f}% of words are long/technical (>=12 characters)")
    if signals["word_count"] > 250 and signals["heading_count"] == 0:
        reasons.append(f"{signals['word_count']} words with no sub-headings to break up the content")
    if not reasons:
        reasons.append("sentence length, jargon density, and structure are all within comfortable ranges")
    return {"cognitive_load": signals["cognitive_load"], "reasons": reasons}
