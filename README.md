# Universal Course Enhancement Engine

A production-quality, LMS-independent engine that analyzes a course, decides which
enhancements would genuinely improve learning (and, just as often, decides that
none are needed), generates that enhancement content, validates it, and produces
a complete implementation-requirements handoff for whichever LMS will eventually
render it - Odoo today, something else tomorrow.

**Learning quality > visual quality > novelty.** Nothing here forces a flowchart,
quiz, or video onto a lesson that doesn't need one. See [ARCHITECTURE.md](ARCHITECTURE.md)
for the full design rationale.

## Quickstart

No install step required - pure standard library.

```bash
cd universal-course-enhancement-engine
python3 -m course_enhancer.cli examples/sample_course.md
```

This writes a full deliverable set to `output/practical-cloud-deployment/`. Try it
against your own course:

```bash
python3 -m course_enhancer.cli path/to/your-course.html --format html --out output
python3 -m course_enhancer.cli path/to/your-course.csv  --out output
```

Supported input formats: HTML, Markdown, JSON, CSV, plain text (auto-detected from
the file extension, or force one with `--format`). Run the test suite with:

```bash
python3 -m pytest tests/ -q
```

## What it produces

For every course, under `output/<course-slug>/`:

```
course-analysis.json              # per-lesson signals (word count, cognitive load, etc.)
enhancement-plan.json             # what was recommended/suppressed and why, per lesson
enhancement-package.json          # full generated content, LMS-agnostic
reports/
  COURSE_ENHANCEMENT_REPORT.md
  ODOO_IMPLEMENTATION_REQUIREMENTS.md
  MODULE_DEPENDENCY_GRAPH.md
  QUALITY_REPORT.md
requirements/
  lms-capabilities.json           # generic capabilities required (not Odoo-specific)
  odoo-requirements.json          # proposed custom Odoo modules (never claimed to exist)
  module-dependencies.json
assets/
  diagrams/   *.mmd                Mermaid source per diagram
  mindmaps/   *.mmd
  videos/     *.json                video_explanation + whiteboard packages
  voiceovers/ *.json                narration scripts + timing/asset metadata
```

Nothing here is Odoo-specific except the `requirements/` and
`reports/ODOO_IMPLEMENTATION_REQUIREMENTS.md` files, which exist specifically to
hand off to an Odoo (or other LMS) developer - see "Architecture rule" below.

## Architecture rule: never coupled to an LMS

```
COURSE INPUT -> UNIVERSAL COURSE ENHANCEMENT ENGINE -> ENHANCEMENT PACKAGE -> LMS ADAPTER -> ODOO
```

`course_enhancer/` never imports or references Odoo. It stops at
`enhancement-package.json` plus a requirements handoff. Uploading that package into
Odoo, building the rendering modules, and running the LMS is explicitly a separate
team's job - see `requirements/odoo-requirements.json`, which proposes
`course_enhancer_*` custom modules and is always careful to label them
"Recommended Custom Odoo Module," never an existing one.

If the company migrates off Odoo later, only a new adapter needs to be written;
`course_enhancer/` does not change.

## Project layout

```
course_enhancer/        core engine (format-agnostic, no LMS references)
  schema.py              the one normalized course shape everything else depends on
  normalize.py           HTML / Markdown / JSON / CSV / plain text -> schema.py shape
  analysis.py            course-analysis, pedagogy-analysis, cognitive-load-analysis
  decision.py            enhancement decision engine (cites evidence, can say "none needed")
  mermaid.py             flowchart / decision-tree / mind-map / timeline / concept / sequence diagrams + validator
  comparison.py          comparison-table generation
  interactive.py         knowledge-check / scenario / matching / true-false generation
  content.py             summary / key-takeaway / example / case-study generation
  video.py               video-script / whiteboard-video / scene / voiceover packages
  quality.py             quality-validation + accessibility-review (dedupe, cap, gate)
  package_builder.py     orchestrates one lesson -> one course into the 3 top-level JSON deliverables
  requirements_engine.py LMS Capability Requirements Engine + Odoo Requirements Generator
  reports.py             the 4 markdown reports
  pipeline.py            end-to-end run + output/ directory writer
  cli.py                 `python -m course_enhancer.cli`
skills/                  24 independently-callable skills, thin wrappers over the above
  registry.json          canonical skill catalog (source/enabled/dependencies)
examples/sample_course.md  a demo course exercising every branch of the decision engine
tests/                   pytest suite (normalize, decision, mermaid, requirements, end-to-end)
```

## The 24 skills

Every skill in `skills/` is independently callable (`from skills import flowchart_generation;
flowchart_generation.run(lesson)`) and listed in `skills/registry.json` with its
source, enabled state, and dependencies - exactly the registry shape a future
external skill would also need to satisfy. See
[EXTERNAL_SKILLS_POLICY.md](EXTERNAL_SKILLS_POLICY.md) before adding one that isn't
internal.

## Extending content quality with an LLM

Every content generator in this engine (`interactive.py`, `content.py`, `video.py`,
etc.) is currently **heuristic/rule-based only** - regex- and structure-driven, zero
network calls, zero API keys required, fully deterministic and testable. That's a
deliberate default: the engine has to run for anyone, offline, with nothing invented
that isn't grounded in the lesson's own text.

Every generator that produces a placeholder (look for `requires_subject_matter_review: true`
or `[author: ...]` scaffolding) is a natural seam for swapping in a real LLM call
later - the function signatures already take just `(lesson, ...)` and return the
same structured dict either way. This mirrors the pluggable-provider pattern already
used by the sibling `course-intelligence-extractor` project, without taking a hard
dependency on it.

## Quality guarantees enforced in code, not just policy

- `decision.py` can and does return zero candidates for a lesson (`sufficient: true`) - verified in `tests/test_decision.py`.
- `quality.py` dedupes overlapping enhancement types and caps enhancements per lesson at 3.
- `mermaid.py::validate_mermaid` runs before any diagram is considered final; invalid diagrams are rejected, not shipped.
- `quality.accessibility_review` fails any diagram missing alt text, any video missing on-screen text, any interactive component missing feedback.
- `requirements_engine.py` only ever proposes modules this specific course's *actual* generated enhancements need (`tests/test_requirements_engine.py::test_no_enhancements_requires_no_modules`) - never the full catalog of everything the engine could theoretically produce.
- The original course source is never modified - the pipeline only ever writes to `output/`.
