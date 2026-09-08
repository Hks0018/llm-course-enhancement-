"""24 independently-callable skills, each a thin wrapper around
course_enhancer/ core logic. See skills/registry.json for the canonical
list, source, enabled state, and dependencies of each skill.

Every skill module exposes:
  SKILL   - metadata dict matching its registry.json entry
  run(**kwargs) -> dict
"""
