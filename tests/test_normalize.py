from course_enhancer import normalize
from course_enhancer.schema import validate_course

MARKDOWN = """# My Course

Course intro paragraph.

Learning Objectives:
- Objective one
- Objective two

## Module One

### Lesson A

Some content for lesson A that is reasonably long so it is not treated as too short for analysis purposes here.

### Lesson B

Some content for lesson B, also long enough to pass the minimum-word threshold used elsewhere in the engine.
"""


def test_markdown_structure():
    doc = normalize.normalize(MARKDOWN, fmt="markdown")
    assert doc["course"]["title"] == "My Course"
    assert doc["course"]["description"] == "Course intro paragraph."
    assert doc["course"]["learning_objectives"] == ["Objective one", "Objective two"]
    assert len(doc["modules"]) == 1
    assert len(doc["modules"][0]["lessons"]) == 2
    assert validate_course(doc) == []


def test_markdown_no_module_heading_falls_back():
    doc = normalize.normalize("# Solo Course\n\nJust one lesson worth of text here, no module headings at all in this document.", fmt="markdown")
    assert len(doc["modules"]) == 1
    assert len(doc["modules"][0]["lessons"]) == 1


def test_html_structure():
    html = """
    <html><body>
    <h1>HTML Course</h1>
    <h2>Mod 1</h2>
    <h3>Lesson 1</h3>
    <p>Some paragraph text describing the lesson content in enough detail to be meaningful.</p>
    <ul><li>Item one</li><li>Item two</li></ul>
    </body></html>
    """
    doc = normalize.normalize(html, fmt="html")
    assert doc["course"]["title"] == "HTML Course"
    assert len(doc["modules"]) == 1
    lesson = doc["modules"][0]["lessons"][0]
    assert "Item one" in lesson["content"]
    assert validate_course(doc) == []


def test_json_structured_input():
    import json
    payload = json.dumps({
        "course": {"title": "JSON Course", "description": "d", "learning_objectives": ["o1"]},
        "modules": [{"id": "m1", "title": "Mod 1", "lessons": [
            {"id": "l1", "title": "Lesson 1", "content": "Enough content words here to pass validation checks cleanly.", "learning_objectives": []}
        ]}],
    })
    doc = normalize.normalize(payload, fmt="json")
    assert doc["course"]["title"] == "JSON Course"
    assert validate_course(doc) == []


def test_csv_groups_by_module():
    csv_text = (
        "module_title,lesson_title,content,learning_objectives\n"
        "Mod A,Lesson X,This is lesson content comparing X versus Y in reasonable detail for testing.,obj1;obj2\n"
        "Mod A,Lesson Y,More lesson content here for a second lesson in the very same module for this test.,obj3\n"
        "Mod B,Lesson Z,A third lesson in a brand new module to check module grouping works correctly here.,\n"
    )
    doc = normalize.normalize(csv_text, fmt="csv")
    assert len(doc["modules"]) == 2
    assert len(doc["modules"][0]["lessons"]) == 2
    assert len(doc["modules"][1]["lessons"]) == 1
    assert validate_course(doc) == []


def test_html_article_section_containers_override_heading_depth():
    """Real-world page-builder-exported course sites often reuse h1-h4 purely
    for visual styling inside a lesson (accordion questions, feature cards)
    while the *real* lesson/module boundaries are <article>/<section>
    containers. This must take priority over naive heading-depth parsing -
    otherwise every decorative heading fragments into a bogus module/lesson.
    """
    html = """
    <html><body>
    <section class="hero"><h1>Demo Course</h1></section>
    <section class="module-block">
      <div class="module-header"><h2>Module One</h2></div>
      <article class="lesson">
        <h1>Lesson Alpha</h1>
        <p>Real lesson content that should not be split by decorative headings below.</p>
        <div class="card"><h2 style="color:red">Not a new module</h2><p>Card blurb text.</p></div>
        <div class="accordion"><h2 class="accordion-header"><button>Not a new module either?</button></h2></div>
        <ul><li>First point</li><li>Second point</li></ul>
        <table><tr><th>Col A</th><th>Col B</th></tr><tr><td>1</td><td>2</td></tr></table>
      </article>
      <article class="lesson">
        <h1>Lesson Beta</h1>
        <p>Second lesson content, long enough to be meaningful for this test.</p>
      </article>
    </section>
    </body></html>
    """
    doc = normalize.normalize(html, fmt="html")
    assert doc["course"]["title"] == "Demo Course"
    assert len(doc["modules"]) == 1
    assert doc["modules"][0]["title"] == "Module One"
    lessons = doc["modules"][0]["lessons"]
    assert len(lessons) == 2
    assert lessons[0]["title"] == "Lesson Alpha"
    assert lessons[1]["title"] == "Lesson Beta"
    # decorative in-lesson headings must not fragment the lesson
    assert "Not a new module" in lessons[0]["content"]
    # list items must be separated, not run together
    assert "- First point" in lessons[0]["content"]
    assert "- Second point" in lessons[0]["content"]
    assert "- First point- Second point" not in lessons[0]["content"]
    # table cells must be separated, not smashed into one word
    assert "Col ACol B" not in lessons[0]["content"]
    assert validate_course(doc) == []


def test_html_without_article_tags_falls_back_to_heading_based_parser():
    html = "<html><body><h1>T</h1><h2>M</h2><h3>L</h3><p>Enough content words for validation here.</p></body></html>"
    doc = normalize.normalize(html, fmt="html")
    assert doc["course"]["title"] == "T"
    assert doc["modules"][0]["lessons"][0]["title"] == "L"


def test_plain_text_wraps_as_single_lesson():
    doc = normalize.normalize("Just a wall of plain text with no structure at all, long enough to be meaningful for analysis.", fmt="text")
    assert len(doc["modules"]) == 1
    assert len(doc["modules"][0]["lessons"]) == 1
    assert validate_course(doc) == []
