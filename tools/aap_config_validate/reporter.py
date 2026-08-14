"""Format and emit validation results."""

from __future__ import annotations

import json
import sys
from typing import List

from aap_config_validate.models import Issue, Severity


def _colorize(severity: Severity) -> str:
    colors = {
        Severity.ERROR: "\033[91m",
        Severity.WARNING: "\033[93m",
        Severity.INFO: "\033[94m",
    }
    reset = "\033[0m"
    return f"{colors.get(severity, '')}{severity.value}{reset}"


def _format_line(issue: Issue, *, color: bool) -> str:
    tag = _colorize(issue.severity) if color else issue.severity.value
    location = f"{issue.source}: {issue.path}" if issue.source else issue.path
    line = f"{tag}: {location}: {issue.message}"
    if issue.suggestion:
        line += f" ({issue.suggestion})"
    return line


def report_text(issues: List[Issue], *, color: bool = True, file=None) -> None:
    file = file or sys.stdout
    for issue in issues:
        print(_format_line(issue, color=color), file=file)

    errors = sum(1 for i in issues if i.severity is Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity is Severity.WARNING)
    print(file=file)
    if errors or warnings:
        print(
            f"Found {errors} error(s), {warnings} warning(s). " f"Config is {'NOT valid' if errors else 'valid (with warnings)'}.",
            file=file,
        )
    else:
        print("No issues found. Config looks good.", file=file)


def report_json(issues: List[Issue], *, file=None) -> None:
    file = file or sys.stdout
    payload = {
        "issues": [
            {
                "severity": i.severity.value,
                "path": i.path,
                "message": i.message,
                "suggestion": i.suggestion,
                "file": i.source,
            }
            for i in issues
        ],
        "summary": {
            "errors": sum(1 for i in issues if i.severity is Severity.ERROR),
            "warnings": sum(1 for i in issues if i.severity is Severity.WARNING),
            "info": sum(1 for i in issues if i.severity is Severity.INFO),
        },
    }
    json.dump(payload, file, indent=2)
    print(file=file)
