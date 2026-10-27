"""Load YAML config files, handling Jinja expressions gracefully."""

from __future__ import annotations

import re
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import yaml

if TYPE_CHECKING:
    from aap_config_validate.config import ValidatorConfig

_JINJA_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")
_LOOKUP_RE = re.compile(r"lookup\s*\(")

JINJA_SENTINEL = "__JINJA_EXPRESSION__"

# Applied when scanning directories (not when a file is passed explicitly).
DEFAULT_EXCLUDE_FILES = ["secrets.yml", "secrets.yaml"]
DEFAULT_EXCLUDE_DIRS = [".git", ".github", ".svn", "__pycache__", ".tox"]


class _SafeLoaderIgnoreJinja(yaml.SafeLoader):
    """YAML loader that tolerates unresolved Jinja and Ansible YAML tags."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicate_keys: List[str] = []


def _jinja_constructor(loader, node):
    """Return the raw string for any value containing Jinja markup."""
    value = loader.construct_scalar(node)
    return value


def _unsafe_constructor(loader, node):
    """Handle Ansible ``!unsafe`` tags by returning the raw string."""
    return loader.construct_scalar(node)


def _vault_constructor(loader, node):
    """Handle Ansible ``!vault`` tags by returning the raw string."""
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return "\n".join(str(v) for v in loader.construct_sequence(node))
    return loader.construct_scalar(node)


def _construct_mapping(loader, node, deep=False):
    """Like SafeConstructor.construct_mapping, but records duplicate keys."""
    loader.flatten_mapping(node)
    mapping: Dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping and isinstance(key, str):
            if hasattr(loader, "duplicate_keys"):
                loader.duplicate_keys.append(key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_SafeLoaderIgnoreJinja.add_constructor("!unsafe", _unsafe_constructor)
_SafeLoaderIgnoreJinja.add_constructor("!vault", _vault_constructor)
_SafeLoaderIgnoreJinja.add_constructor("!vault-encrypted", _vault_constructor)
_SafeLoaderIgnoreJinja.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


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


def _deep_merge_dicts(base: dict, extra: dict) -> dict:
    """Recursive dict merge (Ansible ``combine(..., recursive=true)``)."""
    merged = dict(base)
    for key, value in extra.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _record_source(sources: Dict[str, Any], key: str, value: Any, file_path: str) -> None:
    if isinstance(value, list):
        sources[key] = [file_path] * len(value)
    else:
        sources[key] = file_path


def merge_loaded_data(
    merged: Dict[str, Any],
    sources: Dict[str, Any],
    data: Dict[str, Any],
    file_path: str,
) -> None:
    """Merge one file's mapping into *merged*, tracking per-item sources."""
    for key, value in data.items():
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            merged[key].extend(value)
            prev = sources.get(key)
            if not isinstance(prev, list):
                prev_len = len(merged[key]) - len(value)
                prev = [prev if isinstance(prev, str) else None] * prev_len
            sources[key] = list(prev) + [file_path] * len(value)
        elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
            prev = sources.get(key)
            if isinstance(prev, str) and prev != file_path:
                sources[key] = f"{prev}, {file_path}"
            else:
                sources[key] = file_path
        else:
            merged[key] = value
            _record_source(sources, key, value, file_path)


def load_yaml_file(path: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Load a YAML mapping from *path*.

    Returns ``(data, duplicate_keys)`` where *duplicate_keys* lists mapping
    keys that appeared more than once in the file (PyYAML keeps the last).
    """
    with open(path, "r", encoding="utf-8") as fh:
        loader = _SafeLoaderIgnoreJinja(fh)
        try:
            data = loader.get_single_data()
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse {path}: {exc}") from exc
        finally:
            loader.dispose()
    duplicate_keys = list(getattr(loader, "duplicate_keys", []) or [])
    if data is None:
        return {}, duplicate_keys
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level, got {type(data).__name__}")
    return data, duplicate_keys


def _skip_dir_scan_path(path: Path, rel: Path, cfg: Optional[ValidatorConfig]) -> bool:
    from aap_config_validate.config import ValidatorConfig

    exclude_files = list(DEFAULT_EXCLUDE_FILES)
    exclude_dirs = list(DEFAULT_EXCLUDE_DIRS)
    if cfg:
        exclude_files.extend(cfg.exclude_files)
        exclude_dirs.extend(cfg.exclude_dirs)
    combined = ValidatorConfig(exclude_files=exclude_files, exclude_dirs=exclude_dirs)

    if combined.should_exclude_file(rel) or combined.should_exclude_file(path):
        return True

    parent = rel.parent
    if parent == Path("."):
        return False
    if combined.should_exclude_dir(parent):
        return True
    acc = Path()
    for part in parent.parts:
        acc = acc / part
        if combined.should_exclude_dir(acc) or combined.should_exclude_dir(part):
            return True
    return False


def load_config_dir(config_dir: str | Path, cfg: Optional[ValidatorConfig] = None) -> Tuple[Dict[str, Any], List[str], Dict[str, Any], List[Tuple[str, str]]]:
    """Load all .yml/.yaml files from *config_dir* into a merged namespace.

    Returns ``(merged_vars, parse_errors, sources, same_file_dupes)`` where
    *same_file_dupes* is a list of ``(key, file_path)`` for duplicate keys.
    """
    config_dir = Path(config_dir)
    merged: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}
    errors: List[str] = []
    same_file_dupes: List[Tuple[str, str]] = []

    yml_files = sorted(chain(config_dir.rglob("*.yml"), config_dir.rglob("*.yaml")))
    if not yml_files:
        errors.append(f"No .yml/.yaml files found in {config_dir}")
        return merged, errors, sources, same_file_dupes

    for path in yml_files:
        rel = path.relative_to(config_dir)
        if _skip_dir_scan_path(path, rel, cfg):
            continue
        try:
            data, dup_keys = load_yaml_file(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for key in dup_keys:
            same_file_dupes.append((key, str(path)))
        merge_loaded_data(merged, sources, data, str(path))

    return merged, errors, sources, same_file_dupes


def _merge_namespace(
    merged: Dict[str, Any],
    sources: Dict[str, Any],
    data: Dict[str, Any],
    incoming_sources: Dict[str, Any],
    fallback_path: str,
) -> None:
    """Merge an already-loaded namespace (with its own source map) into *merged*."""
    for key, value in data.items():
        incoming = incoming_sources.get(key)
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            merged[key].extend(value)
            prev = sources.get(key)
            extra = incoming if isinstance(incoming, list) else [incoming or fallback_path] * len(value)
            if not isinstance(prev, list):
                prev_len = len(merged[key]) - len(value)
                prev = [prev if isinstance(prev, str) else None] * prev_len
            sources[key] = list(prev) + list(extra)
        elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
            prev = sources.get(key)
            hint = incoming if isinstance(incoming, str) else fallback_path
            if isinstance(prev, str) and prev != hint:
                sources[key] = f"{prev}, {hint}"
            else:
                sources[key] = hint
        else:
            merged[key] = value
            if incoming is not None:
                sources[key] = incoming
            else:
                _record_source(sources, key, value, fallback_path)


def load_paths(paths: List[str], cfg: Optional[ValidatorConfig] = None) -> Tuple[Dict[str, Any], List[str], Dict[str, Any], List[Tuple[str, str]]]:
    """Load config from one or more file/directory paths.

    Explicit file arguments are always loaded (directory default excludes
    such as ``secrets.yml`` do not apply). Directory scans apply default
    plus config-file exclusions.

    Returns ``(merged, errors, sources, same_file_dupes)``.
    """
    merged: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}
    errors: List[str] = []
    same_file_dupes: List[Tuple[str, str]] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            from aap_config_validate.config import ValidatorConfig

            exclude_dirs = list(DEFAULT_EXCLUDE_DIRS)
            if cfg:
                exclude_dirs.extend(cfg.exclude_dirs)
            dir_cfg = ValidatorConfig(exclude_dirs=exclude_dirs)
            if dir_cfg.should_exclude_dir(pp) or dir_cfg.should_exclude_dir(pp.name):
                continue
            data, errs, src, dupes = load_config_dir(pp, cfg)
            errors.extend(errs)
            same_file_dupes.extend(dupes)
            _merge_namespace(merged, sources, data, src, str(pp))
        elif pp.is_file():
            if cfg and cfg.should_exclude_file(pp):
                continue
            try:
                data, dup_keys = load_yaml_file(pp)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            for key in dup_keys:
                same_file_dupes.append((key, str(pp)))
            src: Dict[str, Any] = {}
            merge_loaded_data({}, src, data, str(pp))
            _merge_namespace(merged, sources, data, src, str(pp))
        else:
            errors.append(f"Path not found: {p}")

    return merged, errors, sources, same_file_dupes
