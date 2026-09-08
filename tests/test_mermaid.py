from course_enhancer.mermaid import (
    validate_mermaid, generate_flowchart, generate_decision_tree,
    generate_mind_map, generate_timeline, generate_concept_diagram, generate_sequence_diagram,
)
from course_enhancer.schema import new_lesson


def test_validate_valid_flowchart():
    code = "flowchart TD\n    A[Start] --> B[End]"
    result = validate_mermaid(code)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_rejects_unknown_diagram_type():
    result = validate_mermaid("notarealdiagram\n    A --> B")
    assert result["valid"] is False


def test_validate_rejects_unbalanced_brackets():
    result = validate_mermaid("flowchart TD\n    A[Start --> B[End]")
    assert result["valid"] is False
    assert any("bracket" in e for e in result["errors"])


def test_validate_rejects_code_fences():
    result = validate_mermaid("```\nflowchart TD\n```")
    assert result["valid"] is False


def _lesson(content):
    return new_lesson("l1", "Test Lesson", content)


def test_generate_flowchart_is_valid():
    lesson = _lesson("1. First step.\n2. Second step.\n3. Third step.")
    result = generate_flowchart(lesson)
    assert result["validation"]["valid"] is True
    assert len(result["nodes"]) == 3
    assert result["accessibility_description"]


def test_generate_decision_tree_is_valid():
    lesson = _lesson("If X happens, do Y. If Z happens, do W.")
    result = generate_decision_tree(lesson)
    assert result["validation"]["valid"] is True


def test_generate_mind_map_is_valid():
    lesson = _lesson("Alpha Beta relates to Gamma Delta which connects to Epsilon Zeta in this system.")
    result = generate_mind_map(lesson)
    assert result["validation"]["valid"] is True


def test_generate_timeline_is_valid():
    lesson = _lesson("In 1999 this happened. In 2005 that happened. In 2020 the third thing happened.")
    result = generate_timeline(lesson)
    assert result["validation"]["valid"] is True
    assert len(result["nodes"]) == 3
    assert "1999" in result["mermaid_code"]


def test_generate_concept_diagram_is_valid():
    lesson = _lesson("The Client Module relates to the Server Module which depends on the Database Module.")
    result = generate_concept_diagram(lesson)
    assert result["validation"]["valid"] is True


def test_generate_sequence_diagram_is_valid():
    lesson = _lesson("The client sends a request to the server. The server calls the database and returns a response.")
    result = generate_sequence_diagram(lesson)
    assert result["validation"]["valid"] is True
