"""CLI entry point.

Usage (from the project root):
    python -m course_enhancer.cli examples/sample_course.md
    python -m course_enhancer.cli path/to/course.html --format html --out output
"""
from __future__ import annotations

import argparse
import os
import sys

from course_enhancer import pipeline


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="course-enhancer", description="Universal Course Enhancement Engine")
    parser.add_argument("source", help="Path to a course file (HTML/Markdown/JSON/CSV/plain text)")
    parser.add_argument("--format", "-f", choices=["html", "markdown", "json", "csv", "text"], default=None,
                         help="Force input format (auto-detected from extension/content by default)")
    parser.add_argument("--out", "-o", default="output", help="Output root directory (default: output)")
    parser.add_argument("--slug", default=None, help="Course slug for the output subdirectory (default: derived from course title)")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.source):
        print(f"error: source file not found: {args.source}", file=sys.stderr)
        return 1

    try:
        result = pipeline.run(args.source, output_root=args.out, fmt=args.format, course_slug=args.slug)
    except Exception as exc:  # surface a clean CLI error rather than a traceback
        print(f"error: {exc}", file=sys.stderr)
        return 1

    built = result["built"]
    analysis = built["course_analysis"]
    print(f"Course: {result['normalized']['course']['title']}")
    print(f"  {analysis['total_lessons']} lessons across {analysis['total_modules']} modules")
    print(f"  {analysis['lessons_requiring_no_enhancement']} lessons need no enhancement")
    print(f"  {len(built['all_accepted'])} enhancements generated, {len(built['all_rejected'])} suppressed")
    print(f"  {len(result['odoo_requirements']['modules'])} recommended Odoo module(s)")
    print(f"Output written to: {result['course_dir']}/")
    print(f"  Enhanced course: {result['enhanced_course_path']}")
    print(f"  Odoo requirements: {result['odoo_requirements_report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
