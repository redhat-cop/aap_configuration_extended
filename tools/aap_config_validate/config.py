"""Load and manage the validator configuration file."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

DEFAULT_CONFIG_FILENAMES = [".aap-validate.yml", ".aap-validate.yaml"]


@dataclass
class ValidatorConfig:
    """Settings loaded from a ``.aap-validate.yml`` configuration file."""

    # Files/directories to skip during loading (glob patterns, matched against relative path)
    exclude_files: List[str] = dc_field(default_factory=list)
    exclude_dirs: List[str] = dc_field(default_factory=list)

    # Variable names to silently ignore (no "unknown variable" warning)
    ignore_vars: List[str] = dc_field(default_factory=list)

    # Per-variable field names to ignore (no "field not recognised" warning)
    # e.g. {"controller_templates": ["custom_field"]}
    ignore_fields: Dict[str, List[str]] = dc_field(default_factory=dict)

    # Validation checks to disable entirely
    # Choices: var_names, structure, required_fields, types, unknown_fields, state, choices, xref, duplicates
    disable_checks: List[str] = dc_field(default_factory=list)

    # Extra known variables to register (treated like KNOWN_GLOBAL_VARS)
    extra_known_vars: List[str] = dc_field(default_factory=list)

    # CLI defaults that can be set in config
    strict: Optional[bool] = None
    show_info: Optional[bool] = None
    wildcard_vars: Optional[str] = None
    components: Optional[List[str]] = None
    output_format: Optional[str] = None

    def should_exclude_file(self, filepath: str | Path) -> bool:
        """Return True if *filepath* matches any exclude_files pattern."""
        name = str(filepath)
        return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(Path(name).name, pat) for pat in self.exclude_files)

    def should_exclude_dir(self, dirpath: str | Path) -> bool:
        """Return True if *dirpath* matches any exclude_dirs pattern.

        Patterns match the full relative path (``tests/fixtures``), the
        final path component (``.git``), or a glob against either.
        """
        path = Path(dirpath)
        candidates = {str(dirpath), path.as_posix(), path.name}
        return any(fnmatch.fnmatch(candidate, pat) for candidate in candidates for pat in self.exclude_dirs)

    def is_var_ignored(self, var_name: str) -> bool:
        return any(fnmatch.fnmatch(var_name, pat) for pat in self.ignore_vars)

    def is_field_ignored(self, var_name: str, field_name: str) -> bool:
        patterns = self.ignore_fields.get(var_name, []) + self.ignore_fields.get("*", [])
        return any(fnmatch.fnmatch(field_name, pat) for pat in patterns)

    def is_check_disabled(self, check_name: str) -> bool:
        return check_name in self.disable_checks


VALID_CHECK_NAMES = frozenset({"var_names", "structure", "required_fields", "types", "unknown_fields", "state", "choices", "xref", "duplicates"})


def load_config(path: Optional[str | Path] = None, search_dir: Optional[str | Path] = None) -> ValidatorConfig:
    """Load a validator config file.

    If *path* is given, load that file directly.  Otherwise search
    *search_dir* (or cwd) for one of the default filenames.
    Returns a default config if nothing is found.
    """
    if path is not None:
        config_path = Path(path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return _parse_config_file(config_path)

    search_dir = Path(search_dir) if search_dir else Path.cwd()
    for name in DEFAULT_CONFIG_FILENAMES:
        candidate = search_dir / name
        if candidate.is_file():
            return _parse_config_file(candidate)

    return ValidatorConfig()


def _parse_config_file(path: Path) -> ValidatorConfig:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        return ValidatorConfig()
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping, got {type(raw).__name__}")

    cfg = ValidatorConfig()

    if "exclude_files" in raw:
        cfg.exclude_files = _as_str_list(raw["exclude_files"], "exclude_files")
    if "exclude_dirs" in raw:
        cfg.exclude_dirs = _as_str_list(raw["exclude_dirs"], "exclude_dirs")
    if "ignore_vars" in raw:
        cfg.ignore_vars = _as_str_list(raw["ignore_vars"], "ignore_vars")
    if "ignore_fields" in raw:
        val = raw["ignore_fields"]
        if not isinstance(val, dict):
            raise ValueError(f"ignore_fields: expected a mapping, got {type(val).__name__}")
        cfg.ignore_fields = {k: _as_str_list(v, f"ignore_fields.{k}") for k, v in val.items()}
    if "disable_checks" in raw:
        checks = _as_str_list(raw["disable_checks"], "disable_checks")
        unknown = set(checks) - VALID_CHECK_NAMES
        if unknown:
            raise ValueError(f"disable_checks: unknown check(s): {', '.join(sorted(unknown))}. Valid: {', '.join(sorted(VALID_CHECK_NAMES))}")
        cfg.disable_checks = checks
    if "extra_known_vars" in raw:
        cfg.extra_known_vars = _as_str_list(raw["extra_known_vars"], "extra_known_vars")

    if "strict" in raw:
        cfg.strict = bool(raw["strict"])
    if "show_info" in raw:
        cfg.show_info = bool(raw["show_info"])
    if "wildcard_vars" in raw:
        val = raw["wildcard_vars"]
        if val not in ("auto", "always", "never"):
            raise ValueError(f"wildcard_vars: must be auto, always, or never; got '{val}'")
        cfg.wildcard_vars = val
    if "components" in raw:
        cfg.components = _as_str_list(raw["components"], "components")
    if "output_format" in raw:
        val = raw["output_format"]
        if val not in ("text", "json"):
            raise ValueError(f"output_format: must be text or json; got '{val}'")
        cfg.output_format = val

    return cfg


def _as_str_list(val: Any, label: str) -> List[str]:
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [str(v) for v in val]
    raise ValueError(f"{label}: expected a string or list, got {type(val).__name__}")
