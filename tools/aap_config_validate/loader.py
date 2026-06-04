"""Load YAML config files, handling Jinja expressions gracefully."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import yaml

if TYPE_CHECKING:
    from aap_config_validate.config import ValidatorConfig

_JINJA_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")
_LOOKUP_RE = re.compile(r"lookup\s*\(")

JINJA_SENTINEL = "__JINJA_EXPRESSION__"


class _SafeLoaderIgnoreJinja(yaml.SafeLoader):
    """YAML loader that tolerates unresolved Jinja and Ansible YAML tags."""


def _jinja_constructor(loader, node):
    """Return the raw string for any value containing Jinja markup."""
    value = loader.construct_scalar(node)
    return value


def _unsafe_constructor(loader, node):
    """Handle Ansible ``!unsafe`` tags by returning the raw string."""
    return loader.construct_scalar(node)


def _vault_constructor(loader, node):
    """Handle Ansible ``!vault`` tags by returning the raw string."""
    return loader.construct_scalar(node)


_SafeLoaderIgnoreJinja.add_constructor("!unsafe", _unsafe_constructor)
_SafeLoaderIgnoreJinja.add_constructor("!vault", _vault_constructor)
_SafeLoaderIgnoreJinja.add_constructor("!vault-encrypted", _vault_constructor)


_SafeLoaderIgnoreJinja.add_implicit_resolver(
    "!jinja",
    re.compile(r".*\{\{.*\}\}.*|.*\{%.*%\}.*", re.DOTALL),
    None,
)
_SafeLoaderIgnoreJinja.add_constructor("!jinja", _jinja_constructor)


def is_jinja(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_JINJA_RE.search(value)) or bool(_LOOKUP_RE.search(value))


def load_yaml_file(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = yaml.load(fh, Loader=_SafeLoaderIgnoreJinja)
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level, got {type(data).__name__}")
    return data


def load_config_dir(config_dir: str | Path, cfg: Optional[ValidatorConfig] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Load all .yml/.yaml files from *config_dir* into a merged namespace.

    Returns ``(merged_vars, parse_errors)``.
    """
    config_dir = Path(config_dir)
    merged: Dict[str, Any] = {}
    errors: List[str] = []

    from itertools import chain
    yml_files = sorted(chain(config_dir.rglob("*.yml"), config_dir.rglob("*.yaml")))
    if not yml_files:
        errors.append(f"No .yml/.yaml files found in {config_dir}")
        return merged, errors

    for path in yml_files:
        if cfg:
            rel = path.relative_to(config_dir)
            if cfg.should_exclude_file(path) or cfg.should_exclude_file(rel):
                continue
            if any(cfg.should_exclude_dir(part) for part in rel.parent.parts):
                continue
        try:
            data = load_yaml_file(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for key, value in data.items():
            if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key].extend(value)
            else:
                merged[key] = value

    return merged, errors


def load_paths(paths: List[str], cfg: Optional[ValidatorConfig] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Load config from one or more file/directory paths."""
    merged: Dict[str, Any] = {}
    errors: List[str] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            if cfg and cfg.should_exclude_dir(pp):
                continue
            data, errs = load_config_dir(pp, cfg)
        elif pp.is_file():
            if cfg and cfg.should_exclude_file(pp):
                continue
            try:
                data = load_yaml_file(pp)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            errs = []
        else:
            errors.append(f"Path not found: {p}")
            continue

        errors.extend(errs)
        for key, value in data.items():
            if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key].extend(value)
            else:
                merged[key] = value

    return merged, errors
