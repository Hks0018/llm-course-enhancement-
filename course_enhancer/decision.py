"""Enhancement Decision Engine.

Turns analysis signals into candidate enhancements, each with cited
evidence and a pedagogical rationale - never "this looks impressive" but
always "here is the specific signal that justifies this". A lesson that
trips no threshold gets an explicit, reasoned NO ENHANCEMENT REQUIRED
verdict; that is a first-class, expected outcome, not a fallback.
"""
from __future__ import annotations

from course_enhancer.analysis import MIN_WORDS_FOR_ANY_ENHANCEMENT, LONG_LESSON_WORD_THRESHOLD

# Baseline implementation complexity (1-10) per enhancement type, independent
# of any one lesson - used for priority scoring and for the Odoo requirements
# generator's phase assignment.
IMPLEMENTATION_COMPLEXITY = {
    "structural_recommendation": 1,
    "summary_and_key_takeaways": 2,
    "example": 2,
    "comparison_table": 3,
    "knowledge_check": 3,
    "timeline": 4,
    "flowchart": 4,
    "scenario_exercise": 5,
    "decision_tree": 5,
    "mind_map": 5,
    "sequence_diagram": 6,
    "concept_diagram": 6,
    "video_explanation": 8,
    "whiteboard_video": 9,
}


def _impact(strength: int, cap: int = 10) -> int:
    return max(1, min(cap, 4 + strength))


def _priority(impact: int, complexity: int) -> str:
    score = impact - 0.4 * complexity
    if score >= 5:
        return "HIGH"
    if score >= 2.5:
        return "MEDIUM"
    return "LOW"


def _candidate(enh_type, trigger, evidence, rationale, impact):
    complexity = IMPLEMENTATION_COMPLEXITY[enh_type]
    return {
        "enhancement_type": enh_type,
        "trigger": trigger,
        "evidence": evidence,
        "rationale": rationale,
        "educational_impact": impact,
        "implementation_complexity": complexity,
        "priority": _priority(impact, complexity),
    }


def decide_enhancements(lesson: dict, signals: dict) -> dict:
    candidates = []
    wc = signals["word_count"]

    if wc < MIN_WORDS_FOR_ANY_ENHANCEMENT:
        return {
            "lesson_id": lesson["id"],
            "sufficient": True,
            "candidates": [],
            "no_enhancement_reason": (
                f"Lesson is only {wc} words - too short for any enhancement to add value without "
                "padding it artificially."
            ),
        }

    if signals["numbered_list_items"] >= 3 or signals["sequence_signal_hits"] >= 2:
        strength = max(signals["numbered_list_items"] - 2, signals["sequence_signal_hits"] - 1)
        candidates.append(_candidate(
            "flowchart", "Multi-step process",
            f"{signals['numbered_list_items']} numbered list items and {signals['sequence_signal_hits']} "
            "sequence-marker phrases (e.g. 'first', 'then', 'finally') detected.",
            "A sequential process is faster to scan and remember as a flowchart than as prose the "
            "learner must re-read to reconstruct the order.",
            _impact(strength),
        ))

    if signals["condition_signal_hits"] >= 2:
        strength = signals["condition_signal_hits"] - 1
        candidates.append(_candidate(
            "decision_tree", "Decision with conditions",
            f"{signals['condition_signal_hits']} conditional phrases (e.g. 'if', 'when', 'depending on') detected.",
            "Branching logic described in paragraph form forces the learner to mentally track "
            "every 'if' - a decision tree externalizes that logic instead.",
            _impact(strength),
        ))

    if signals["relationship_signal_hits"] >= 2 and signals["distinct_capitalized_terms"] >= 3:
        strength = signals["relationship_signal_hits"] - 1
        candidates.append(_candidate(
            "mind_map", "Connected concepts",
            f"{signals['relationship_signal_hits']} relationship phrases and "
            f"{signals['distinct_capitalized_terms']} distinct named terms detected.",
            "Multiple concepts described as related to one another benefit from a visual map; "
            "reading about relationships is a weaker encoding than seeing them.",
            _impact(strength),
        ))

    if signals["distinct_year_mentions"] >= 2:
        strength = signals["distinct_year_mentions"] - 1
        candidates.append(_candidate(
            "timeline", "Sequence over time",
            f"{signals['distinct_year_mentions']} distinct year/date references detected.",
            "Chronological information is easy to misorder when read as prose; a timeline makes "
            "the sequence unambiguous.",
            _impact(strength),
        ))

    if signals["comparison_signal_hits"] >= 2:
        strength = signals["comparison_signal_hits"] - 1
        candidates.append(_candidate(
            "comparison_table", "Two or more items need comparison",
            f"{signals['comparison_signal_hits']} comparison phrases (e.g. 'compared to', 'versus') detected.",
            "Comparisons buried in paragraphs require the learner to hold each attribute in "
            "memory across sentences; a table lets them scan by criterion.",
            _impact(strength),
        ))

    if signals["system_interaction_hits"] >= 3:
        strength = signals["system_interaction_hits"] - 2
        candidates.append(_candidate(
            "sequence_diagram", "System interactions",
            f"{signals['system_interaction_hits']} system/actor interaction phrases "
            "(e.g. 'request', 'response', 'API') detected.",
            "Multi-actor request/response flows are difficult to trace in prose once more than "
            "two exchanges occur; a sequence diagram makes the order of messages explicit.",
            _impact(strength),
        ))

    if (
        signals["cognitive_load"] == "high"
        and signals["distinct_capitalized_terms"] >= 2
        and not any(c["enhancement_type"] == "mind_map" for c in candidates)
    ):
        candidates.append(_candidate(
            "concept_diagram", "Complex concept",
            f"Cognitive load rated 'high' ({signals['avg_sentence_length']} avg words/sentence, "
            f"{signals['jargon_density']*100:.0f}% long/technical words) with "
            f"{signals['distinct_capitalized_terms']} named concepts and no existing diagram.",
            "Dense, abstract material is easier to parse when its concepts and their relationships "
            "are laid out visually rather than compressed into long sentences.",
            _impact(2),
        ))

    if signals["definition_hits"] >= 2 and wc > 120:
        candidates.append(_candidate(
            "knowledge_check", "Knowledge retention required",
            f"{signals['definition_hits']} definitional statements detected in a {wc}-word lesson.",
            "Definitional content is quickly forgotten without active retrieval; a short knowledge "
            "check converts passive reading into active recall.",
            _impact(signals["definition_hits"] - 1),
        ))

    if signals["example_hits"] == 0 and signals["definition_hits"] >= 1:
        if wc > 150:
            candidates.append(_candidate(
                "scenario_exercise", "Practical understanding required",
                f"No worked examples detected despite {signals['definition_hits']} definitional "
                f"statements in a {wc}-word lesson.",
                "Learners who can recite a definition often still cannot apply it; a scenario "
                "exercise tests and builds transfer to a realistic situation.",
                _impact(1),
            ))
        else:
            candidates.append(_candidate(
                "example", "Missing worked example",
                f"No worked examples detected despite {signals['definition_hits']} definitional "
                f"statement(s) in a {wc}-word lesson.",
                "An abstract definition without a concrete example is one of the most common gaps "
                "between 'covered' and 'understood'.",
                _impact(1),
            ))

    if (
        signals["cognitive_load"] == "high"
        and (signals["system_interaction_hits"] >= 2 or signals["numbered_list_items"] >= 4)
        and wc > 200
    ):
        candidates.append(_candidate(
            "video_explanation", "Complex explanation requiring demonstration",
            f"High cognitive load on a {wc}-word lesson combining "
            f"{signals['numbered_list_items']} process steps and/or {signals['system_interaction_hits']} "
            "system-interaction phrases.",
            "Some material genuinely benefits from motion and narration to show state changing "
            "over time - text and static diagrams both fall short here.",
            _impact(2),
        ))

    if wc > LONG_LESSON_WORD_THRESHOLD:
        candidates.append(_candidate(
            "summary_and_key_takeaways", "Long lesson",
            f"Lesson is {wc} words (threshold: {LONG_LESSON_WORD_THRESHOLD}).",
            "Long lessons benefit from a closing summary that lets learners check their "
            "understanding and reviewers skim without re-reading the whole lesson.",
            _impact((wc - LONG_LESSON_WORD_THRESHOLD) // 150),
        ))

    if signals["cognitive_load"] == "high" or (signals["heading_count"] == 0 and wc > 250):
        candidates.append(_candidate(
            "structural_recommendation", "High cognitive load / no structure",
            f"Cognitive load '{signals['cognitive_load']}' with {signals['heading_count']} sub-headings "
            f"across {wc} words.",
            "Breaking a dense, unstructured lesson into labeled sub-sections reduces cognitive load "
            "before any other enhancement is even considered.",
            _impact(1),
        ))

    sufficient = len(candidates) == 0
    no_reason = None
    if sufficient:
        no_reason = (
            f"Lesson is {wc} words, cognitive load is '{signals['cognitive_load']}', and no process, "
            "comparison, condition, relationship, or retention-gap signals were detected above "
            "threshold. The lesson is already clear and appropriately scoped - no enhancement "
            "is recommended."
        )

    return {
        "lesson_id": lesson["id"],
        "sufficient": sufficient,
        "candidates": candidates,
        "no_enhancement_reason": no_reason,
    }
