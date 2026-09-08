# Architecture

## Pipeline

```
COURSE INPUT (html/md/json/csv/text)
        |
        v
   normalize.py  ------------------------------->  schema.py shape
        |                                          {course, modules[].lessons[]}
        v
   analysis.py            (course-analysis, pedagogy-analysis, cognitive-load-analysis)
        |
        v
   decision.py             (enhancement-decision: candidates + evidence, or "sufficient")
        |
        v
   quality.py::filter_candidates   (dedupe overlapping types, cap at 3/lesson)
        |
        v
   package_builder.py::GENERATORS  (mermaid.py / comparison.py / interactive.py / content.py / video.py)
        |
        v
   quality.py::validate_enhancement + accessibility_review   (post-generation gate)
        |
        v
   package_builder.py::build_course_package
        |            \
        v             v
course-analysis.json  enhancement-plan.json  enhancement-package.json
        |
        v
   requirements_engine.py   (LMS Capability Requirements Engine + Odoo Requirements Generator)
        |
        v
   reports.py -> COURSE_ENHANCEMENT_REPORT.md / ODOO_IMPLEMENTATION_REQUIREMENTS.md /
                 MODULE_DEPENDENCY_GRAPH.md / QUALITY_REPORT.md
        |
        v
   pipeline.py -> output/<course-slug>/**
```

Everything above the requirements_engine.py line has zero knowledge of Odoo, or of
any LMS. `requirements_engine.py` is the one deliberate seam where the engine talks
about a specific target LMS - and even there, it only *specifies requirements*, it
never renders anything or talks to a live Odoo instance.

## Why "no enhancement" is a first-class outcome, not a fallback

`decision.py::decide_enhancements` returns `{"sufficient": true, "candidates": []}`
whenever a lesson trips zero thresholds. This is not a degenerate case handled as an
afterthought - `package_builder.py`, `reports.py`, and the CLI's summary output all
treat it as an expected, common, positively-reported result ("N lessons need no
enhancement" is printed on every run). The alternative - an engine that always finds
something to add - would violate the explicit priority order the spec sets:
**learning quality > visual quality > novelty**.

## Evidence-first decisions

Every candidate enhancement carries:
- `trigger` - the human-readable rule from the decision table that fired (e.g. "Multi-step process")
- `evidence` - the actual counts detected in *this* lesson's text (e.g. "6 numbered list items and 1 sequence-marker phrases detected")
- `rationale` - the pedagogical reason this class of enhancement helps, independent of the specific lesson

No enhancement is ever recommended on vibes. If you disagree with a recommendation,
the evidence field tells you exactly what to go verify or dispute.

## Quality gates run twice

1. **Pre-generation** (`quality.filter_candidates`): dedupes enhancement types that
   address the same underlying gap (e.g. `example` vs `scenario_exercise`), and caps
   a lesson at 3 enhancements so a lesson with many weak signals doesn't get buried
   in generated content.
2. **Post-generation** (`quality.validate_enhancement`): checks the *generated
   content itself* - valid Mermaid syntax, presence of an accessibility description,
   presence of an explanation/feedback field, presence of scenes with a stated
   educational purpose. A candidate that fails here is moved to
   `rejected_enhancements` with a reason, never silently dropped.

`quality.accessibility_review` then runs a third, course-wide sweep across every
*accepted* enhancement, specifically for accessibility gaps.

## Never inventing facts

Generators are split into two groups:

- **Extractive** (`content.generate_summary`, diagram generators, `interactive.generate_knowledge_check`
  when definitions are present): every fact in the output is quoted or lightly
  reformatted from the lesson's own text.
- **Scaffold** (`content.generate_example`/`generate_case_study` when no definition
  is available, quiz distractors when too few real definitions exist): the output is
  explicitly labeled `requires_subject_matter_review: true` with `[author: ...]`
  placeholders, rather than fabricating a plausible-sounding but unverified fact.

This is why, e.g., `case_study` scaffolds never claim a specific company or number -
case studies need real facts an author must supply.

## The LMS Capability Requirements Engine + Odoo Requirements Generator

`requirements_engine.py::required_modules_for` computes the *transitive closure* of
Odoo modules needed for the specific enhancements a specific course actually
received - starting from the enhancement types present, walking each module's
`dependencies` to a fixed point, and always including the `course_enhancer_core` +
`course_enhancer_assets` base once anything is required.

This is intentionally the opposite of a static catalog dump: a course with only
comparison tables gets a 5-module Phase-1-only recommendation; a course with video
gets `course_enhancer_video`/`course_enhancer_audio` and their dependents too. A
course needing nothing gets an empty module list and an explicit "requires zero
custom Odoo modules" executive summary (see `reports.render_odoo_requirements_report`).

Every module is also classified A (existing Odoo capability) / B (existing custom
capability, worth checking before building new) / C (recommended new module) / D
(external service) - see `_classification_for` in `requirements_engine.py`. Nothing
is ever asserted to already exist; classification C is the default, and B is used
only where there's a genuine, named overlap worth an Odoo developer double-checking
(e.g. asset storage vs. `ir.attachment`).

## Extending the engine

- **New input format**: add a `parse_<format>()` function to `normalize.py` and
  register it in `SUPPORTED_FORMATS`/`_EXT_MAP`. Nothing downstream changes.
- **New enhancement type**: add a decision rule to `decision.py::decide_enhancements`
  (with `IMPLEMENTATION_COMPLEXITY` entry), a generator function, a `GENERATORS`
  entry in `package_builder.py`, and a capability mapping in
  `requirements_engine.ENHANCEMENT_TO_MODULE` + `MODULE_CATALOG`.
- **New skill**: add `skills/<name>.py` with a `SKILL` metadata dict and `run()`
  function, and register it in `skills/registry.json`. See
  [EXTERNAL_SKILLS_POLICY.md](EXTERNAL_SKILLS_POLICY.md) if it's not an internal
  implementation.
- **New LMS target**: write a new adapter that reads `enhancement-package.json` and
  the `requirements/` directory - `course_enhancer/` itself needs zero changes,
  by design.
