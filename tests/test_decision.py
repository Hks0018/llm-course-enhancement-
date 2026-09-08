from course_enhancer.analysis import analyze_lesson
from course_enhancer.decision import decide_enhancements
from course_enhancer.schema import new_lesson


def _decide(content, objectives=None):
    lesson = new_lesson("l1", "Test Lesson", content, objectives or [])
    signals = analyze_lesson(lesson)
    return decide_enhancements(lesson, signals), signals


def test_short_lesson_needs_nothing():
    decision, _ = _decide("A single short sentence.")
    assert decision["sufficient"] is True
    assert decision["candidates"] == []
    assert "too short" in decision["no_enhancement_reason"].lower()


def test_clear_lesson_with_no_signals_is_sufficient():
    content = (
        "This lesson explains one single idea clearly, in plain language, without listing steps, "
        "without comparing anything, and without introducing branching conditions of any kind at all."
    )
    decision, signals = _decide(content)
    assert decision["sufficient"] is True
    assert decision["candidates"] == []


def test_numbered_process_triggers_flowchart():
    content = (
        "Follow these steps carefully and in the exact order shown below, since skipping ahead "
        "will cause later steps to fail in confusing ways.\n"
        "1. Open the application and sign in with your account credentials.\n"
        "2. Navigate to the settings page from the main menu.\n"
        "3. Update the configuration values to match your environment.\n"
        "4. Save your changes and restart the application to finish."
    )
    decision, _ = _decide(content)
    types = {c["enhancement_type"] for c in decision["candidates"]}
    assert "flowchart" in types
    flowchart = next(c for c in decision["candidates"] if c["enhancement_type"] == "flowchart")
    assert "numbered list items" in flowchart["evidence"]


def test_conditions_trigger_decision_tree():
    content = (
        "If the input is valid, accept it and continue. When the input is invalid, reject it immediately. "
        "If the system is under heavy load, queue the request. When capacity frees up, process the queue."
    )
    decision, _ = _decide(content)
    types = {c["enhancement_type"] for c in decision["candidates"]}
    assert "decision_tree" in types


def test_comparisons_trigger_comparison_table():
    content = (
        "Option A is faster compared to Option B in most cases. Option B, in contrast, is cheaper than Option A. "
        "Option A versus Option B ultimately comes down to your budget and performance needs."
    )
    decision, _ = _decide(content)
    types = {c["enhancement_type"] for c in decision["candidates"]}
    assert "comparison_table" in types


def test_long_lesson_triggers_summary():
    content = " ".join(["This is one sentence of filler content for testing purposes."] * 60)
    decision, signals = _decide(content)
    assert signals["word_count"] > 350
    types = {c["enhancement_type"] for c in decision["candidates"]}
    assert "summary_and_key_takeaways" in types


def test_every_candidate_has_evidence_and_rationale():
    content = "1. Step one happens first.\n2. Step two happens next.\n3. Step three happens after that.\n4. Step four finishes it."
    decision, _ = _decide(content)
    for c in decision["candidates"]:
        assert c["evidence"]
        assert c["rationale"]
        assert c["priority"] in ("HIGH", "MEDIUM", "LOW")
