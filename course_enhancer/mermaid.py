"""Mermaid generation + validation.

Backs the flowchart-generation, decision-tree-generation, mind-map-generation,
timeline-generation, concept-diagram-generation, and mermaid-diagram-generation
skills. Every generator here returns a dict with 'mermaid_code' that has
already passed validate_mermaid() - the engine never emits unvalidated
Mermaid source.
"""
from __future__ import annotations

import re

from course_enhancer.analysis import NUMBERED_LIST_RE, BULLET_LIST_RE, SEQUENCE_RE, YEAR_RE
from course_enhancer.schema import slugify

VALID_DIAGRAM_KEYWORDS = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram-v2", "stateDiagram",
    "mindmap", "timeline", "gantt",
)


def validate_mermaid(code: str) -> dict:
    errors = []
    lines = [l for l in code.strip().splitlines() if l.strip()]
    if not lines:
        return {"valid": False, "errors": ["empty diagram source"]}

    first = lines[0].strip()
    if not any(first == kw or first.startswith(kw + " ") or first.startswith(kw + "\n") for kw in VALID_DIAGRAM_KEYWORDS):
        errors.append(f"first line '{first}' does not start with a recognized diagram type {VALID_DIAGRAM_KEYWORDS}")

    for opener, closer, name in (("[", "]", "square"), ("(", ")", "paren"), ("{", "}", "curly")):
        if code.count(opener) != code.count(closer):
            errors.append(f"unbalanced {name} brackets: {code.count(opener)} '{opener}' vs {code.count(closer)} '{closer}'")

    if "```" in code:
        errors.append("diagram source must not contain markdown code fences")

    for line in lines[1:]:
        for bad_char in ("<script", "javascript:"):
            if bad_char in line.lower():
                errors.append(f"disallowed content '{bad_char}' found in diagram source")

    return {"valid": len(errors) == 0, "errors": errors}


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


def _wrap_label(text: str, max_len: int = 40) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace('"', "'")
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def extract_steps(content: str) -> list:
    """Pull an ordered list of process steps out of lesson content."""
    numbered = re.findall(r"^\s*\d+[\.\)]\s+(.*)$", content, re.M)
    if len(numbered) >= 2:
        return [s.strip() for s in numbered]
    bulleted = re.findall(r"^\s*[-*•]\s+(.*)$", content, re.M)
    if len(bulleted) >= 2 and SEQUENCE_RE.search(content):
        return [s.strip() for s in bulleted]
    # Fall back to sentences containing sequence markers, in order.
    sentences = re.split(r"(?<=[.!?])\s+", content)
    seq_sentences = [s.strip() for s in sentences if SEQUENCE_RE.search(s)]
    return seq_sentences


def extract_conditions(content: str) -> list:
    """Pull (condition, outcome) pairs out of lesson content for decision trees."""
    pairs = []
    for sentence in re.split(r"(?<=[.!?])\s+", content):
        m = re.search(r"\bif\s+(.+?),\s*(.+)", sentence, re.I)
        if m:
            pairs.append((m.group(1).strip(" .:"), m.group(2).strip(" .:")))
            continue
        m = re.search(r"\bwhen\s+(.+?),\s*(.+)", sentence, re.I)
        if m:
            pairs.append((m.group(1).strip(" .:"), m.group(2).strip(" .:")))
    return pairs


def generate_flowchart(lesson: dict, steps: list = None) -> dict:
    steps = steps or extract_steps(lesson.get("content", ""))
    approximate = False
    if not steps:
        sentences = re.split(r"(?<=[.!?])\s+", lesson.get("content", ""))
        steps = [s.strip() for s in sentences if s.strip()][:5]
        approximate = True

    lines = ["flowchart TD"]
    node_ids = []
    for i, step in enumerate(steps):
        nid = _node_id("S", i)
        node_ids.append(nid)
        shape = f'["{_wrap_label(step, 55)}"]' if 0 < i < len(steps) - 1 else f'(["{_wrap_label(step, 55)}"])'
        lines.append(f"    {nid}{shape}")
    relationships = []
    for a, b in zip(node_ids, node_ids[1:]):
        lines.append(f"    {a} --> {b}")
        relationships.append({"from": a, "to": b})

    code = "\n".join(lines)
    validation = validate_mermaid(code)
    return {
        "enhancement_type": "flowchart",
        "title": f"Process: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Makes a multi-step process scannable at a glance instead of forcing the learner "
            "to hold the sequence in working memory while reading prose."
        ),
        "mermaid_code": code,
        "nodes": [{"id": nid, "label": s.strip()} for nid, s in zip(node_ids, steps)],
        "relationships": relationships,
        "accessibility_description": (
            "Sequential process diagram: " + " → ".join(_wrap_label(s, 60) for s in steps)
        ),
        "validation": validation,
        "notes": ["Steps were approximated from sentence splitting; recommend author review."] if approximate else [],
    }


def generate_decision_tree(lesson: dict, pairs: list = None) -> dict:
    pairs = pairs or extract_conditions(lesson.get("content", ""))
    approximate = False
    if not pairs:
        pairs = [("condition A is met", "outcome A"), ("condition A is not met", "outcome B")]
        approximate = True

    lines = ["flowchart TD", '    ROOT{"Decision point"}']
    relationships = []
    for i, (cond, outcome) in enumerate(pairs):
        oid = _node_id("O", i)
        lines.append(f'    ROOT -->|{_wrap_label(cond, 30)}| {oid}["{_wrap_label(outcome)}"]')
        relationships.append({"from": "ROOT", "to": oid, "condition": _wrap_label(cond, 30)})

    code = "\n".join(lines)
    validation = validate_mermaid(code)
    return {
        "enhancement_type": "decision_tree",
        "title": f"Decision Logic: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Externalizes branching conditions so the learner can see every path and its "
            "outcome instead of re-deriving the logic from paragraph text."
        ),
        "mermaid_code": code,
        "nodes": [{"id": "ROOT", "label": "Decision point"}]
        + [{"id": _node_id("O", i), "label": _wrap_label(o)} for i, (_, o) in enumerate(pairs)],
        "relationships": relationships,
        "accessibility_description": "Decision tree with branches: "
        + "; ".join(f"if {c} then {o}" for c, o in pairs),
        "validation": validation,
        "notes": ["Conditions were approximated; recommend author review for accuracy."] if approximate else [],
    }


def generate_mind_map(lesson: dict, terms: list = None) -> dict:
    content = lesson.get("content", "")
    if terms is None:
        from course_enhancer.analysis import CAPITALIZED_TERM_RE
        seen = []
        for m in CAPITALIZED_TERM_RE.findall(content):
            if m not in seen and m.lower() not in {"the", "this", "these"}:
                seen.append(m)
        terms = seen[:6]
    approximate = not terms
    if not terms:
        terms = [lesson.get("title", "Topic")]

    root_label = _wrap_label(lesson.get("title", "Topic"), 30)
    lines = ["mindmap", f"  root(({root_label}))"]
    for term in terms:
        lines.append(f"    {_wrap_label(term, 30)}")

    code = "\n".join(lines)
    validation = validate_mermaid(code)
    return {
        "enhancement_type": "mind_map",
        "title": f"Concept Map: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Shows how the lesson's key terms relate back to the central topic, helping learners "
            "build an integrated mental model instead of a list of disconnected facts."
        ),
        "mermaid_code": code,
        "nodes": [{"id": "root", "label": root_label}] + [{"id": slugify(t), "label": t} for t in terms],
        "relationships": [{"from": "root", "to": slugify(t)} for t in terms],
        "accessibility_description": f"Mind map centered on '{root_label}' connected to: " + ", ".join(terms),
        "validation": validation,
        "notes": ["No strong recurring terms detected; used lesson title only."] if approximate else [],
    }


def generate_timeline(lesson: dict) -> dict:
    content = lesson.get("content", "")
    years = sorted(set(YEAR_RE.findall(content)))
    events = []
    if years:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
        for year in years:
            sentence = next((s for s in sentences if re.search(rf"\b{year}\b", s)), year)
            events.append((year, _wrap_label(sentence, 70)))
    else:
        steps = extract_steps(content)
        events = [(f"Step {i+1}", _wrap_label(s)) for i, s in enumerate(steps)]
    approximate = not years and not events
    if not events:
        events = [("Stage 1", _wrap_label(lesson.get("title", "Lesson")))]
        approximate = True

    lines = ["timeline", f"    title {_wrap_label(lesson.get('title', 'Lesson'), 50)}"]
    for label, event in events:
        lines.append(f"    {label} : {event}")

    code = "\n".join(lines)
    validation = validate_mermaid(code)
    return {
        "enhancement_type": "timeline",
        "title": f"Timeline: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Anchors a chronological or staged progression visually so the order of events is "
            "unambiguous."
        ),
        "mermaid_code": code,
        "nodes": [{"id": slugify(label), "label": event} for label, event in events],
        "relationships": [],
        "accessibility_description": "Timeline: " + "; ".join(f"{l} — {e}" for l, e in events),
        "validation": validation,
        "notes": ["No explicit dates found; used process stages instead."] if approximate else [],
    }


def generate_sequence_diagram(lesson: dict) -> dict:
    from course_enhancer.analysis import SYSTEM_WORDS_RE

    content = lesson.get("content", "")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if SYSTEM_WORDS_RE.search(s)]
    approximate = len(sentences) < 2
    if approximate:
        sentences = [
            "Client sends a request to the Server.",
            "Server processes the request and returns a response.",
        ]

    participants = ["Client", "Server"]
    for extra in ("Database", "API"):
        if any(extra.lower() in s.lower() for s in sentences) and extra not in participants:
            participants.append(extra)

    lines = ["sequenceDiagram"] + [f"    participant {p}" for p in participants]
    steps = []
    for i, sentence in enumerate(sentences[:6]):
        src = participants[i % 2]
        dst = participants[(i + 1) % 2]
        label = _wrap_label(sentence, 50)
        lines.append(f"    {src}->>{dst}: {label}")
        steps.append({"from": src, "to": dst, "message": label})

    code = "\n".join(lines)
    validation = validate_mermaid(code)
    return {
        "enhancement_type": "sequence_diagram",
        "title": f"System Interaction: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Visualizes the order of messages between interacting systems/actors, which is hard "
            "to track from prose alone once more than two exchanges are involved."
        ),
        "mermaid_code": code,
        "nodes": [{"id": p, "label": p} for p in participants],
        "relationships": steps,
        "accessibility_description": "Sequence of interactions: " + "; ".join(
            f"{s['from']} to {s['to']}: {s['message']}" for s in steps
        ),
        "validation": validation,
        "notes": ["Interaction steps were approximated; recommend author review."] if approximate else [],
    }


def generate_concept_diagram(lesson: dict) -> dict:
    from course_enhancer.analysis import CAPITALIZED_TERM_RE, RELATIONSHIP_RE

    content = lesson.get("content", "")
    seen = []
    for m in CAPITALIZED_TERM_RE.findall(content):
        if m not in seen:
            seen.append(m)
    terms = seen[:5]
    approximate = len(terms) < 2
    if approximate:
        terms = [lesson.get("title", "Concept A"), "Related Concept"]

    lines = ["graph LR"]
    ids = [f"C{i}" for i in range(len(terms))]
    for nid, term in zip(ids, terms):
        lines.append(f'    {nid}["{_wrap_label(term)}"]')
    relationships = []
    has_relationship_language = bool(RELATIONSHIP_RE.search(content))
    for a, b in zip(ids, ids[1:]):
        verb = "relates to" if has_relationship_language else "connects to"
        lines.append(f"    {a} -- {verb} --> {b}")
        relationships.append({"from": a, "to": b, "label": verb})

    code = "\n".join(lines)
    validation = validate_mermaid(code)
    return {
        "enhancement_type": "concept_diagram",
        "title": f"Concept Relationships: {lesson.get('title', 'Lesson')}",
        "educational_purpose": (
            "Makes the relationships between abstract concepts explicit and visual, reducing the "
            "cognitive load of tracking them purely through prose."
        ),
        "mermaid_code": code,
        "nodes": [{"id": nid, "label": t} for nid, t in zip(ids, terms)],
        "relationships": relationships,
        "accessibility_description": "Concept diagram linking: " + " -> ".join(terms),
        "validation": validation,
        "notes": ["Fewer than 2 distinct concepts detected; diagram is a placeholder scaffold."] if approximate else [],
    }
