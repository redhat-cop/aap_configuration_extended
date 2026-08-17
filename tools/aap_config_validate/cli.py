"""CLI entry point for aap-config-validate."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

from aap_config_validate import __version__
from aap_config_validate.config import load_config
from aap_config_validate.loader import load_paths
from aap_config_validate.models import Issue, Severity
from aap_config_validate.reporter import report_json, report_text
from aap_config_validate.validators import config_has_wildcard_vars, merge_wildcard_vars, validate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aap-config-validate",
        description="Validate AAP configuration files against infra.aap_configuration schemas.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="YAML files or directories to validate",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        metavar="FILE",
        help="Path to .aap-validate.yml config file (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default=None,
        dest="output_format",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=None,
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        default=False,
        help="Do not treat warnings as errors (overrides config file)",
    )
    parser.add_argument(
        "--component",
        action="append",
        choices=["controller", "gateway", "hub", "eda"],
        dest="components",
        help="Limit validation to specific component(s); may be repeated",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable coloured output",
    )
    parser.add_argument(
        "--show-info",
        action="store_true",
        default=None,
        help="Include INFO-level messages in output",
    )
    parser.add_argument(
        "--wildcard-vars",
        choices=["auto", "always", "never"],
        default=None,
        help=(
            "Wildcard variable merging: 'auto' enables when "
            "dispatch_include_wildcard_vars is set or suffixed vars are present "
            "(default), 'always' forces merging, 'never' disables it"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_option(cli_val, cfg_val, default):
    """CLI flags take precedence over config file, then fall back to default."""
    if cli_val is not None:
        return cli_val
    if cfg_val is not None:
        return cfg_val
    return default


def _use_color(no_color: bool) -> bool:
    if no_color:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = load_config(path=args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    output_format = _resolve_option(args.output_format, cfg.output_format, "text")
    if args.no_strict:
        strict = False
    else:
        strict = _resolve_option(args.strict, cfg.strict, False)
    show_info = _resolve_option(args.show_info, cfg.show_info, False)
    wildcard_vars = _resolve_option(args.wildcard_vars, cfg.wildcard_vars, "auto")
    components = args.components or cfg.components or None

    config, load_errors, sources = load_paths(args.paths, cfg=cfg)
    issues: List[Issue] = []

    for err in load_errors:
        issues.append(Issue(severity=Severity.ERROR, path="<loader>", message=err))

    if config:
        do_wildcard = wildcard_vars == "always" or (
            wildcard_vars == "auto" and (bool(config.get("dispatch_include_wildcard_vars", False)) or config_has_wildcard_vars(config))
        )
        if do_wildcard:
            config, wildcard_issues = merge_wildcard_vars(config, sources=sources)
            issues.extend(wildcard_issues)
        issues.extend(validate(config, components=components, cfg=cfg, sources=sources))

    if not show_info:
        issues = [i for i in issues if i.severity is not Severity.INFO]

    if strict:
        for issue in issues:
            if issue.severity is Severity.WARNING:
                issue.severity = Severity.ERROR

    if output_format == "json":
        report_json(issues)
    else:
        report_text(issues, color=_use_color(args.no_color))

    has_errors = any(i.severity is Severity.ERROR for i in issues)
    sys.exit(1 if has_errors else 0)
