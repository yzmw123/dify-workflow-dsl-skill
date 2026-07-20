#!/usr/bin/env python3
"""CLI for the version-aware Dify Workflow DSL validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from dify_dsl_validator import SUPPORTED_VERSIONS, validate_path
except ImportError as exc:  # pragma: no cover - friendlier error when PyYAML is absent
    if exc.name == "yaml":
        raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc
    raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Dify App DSL 0.6.0 and 0.7.0 YAML files.")
    parser.add_argument("files", nargs="+", type=Path, help="One or more exported/generated YAML files.")
    parser.add_argument(
        "--target-version",
        choices=SUPPORTED_VERSIONS,
        help="Require every document to use this DSL version.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="Output human-readable text or machine-readable JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status for warnings as well as errors.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports = [validate_path(path, target_version=args.target_version) for path in args.files]
    if args.output_format == "json":
        payload: object = reports[0].as_dict() if len(reports) == 1 else [report.as_dict() for report in reports]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("\n".join(report.format_text() for report in reports))
    failed = any(report.errors or (args.strict and report.warnings) for report in reports)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
