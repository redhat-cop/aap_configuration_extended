"""Core validation engine."""

from __future__ import annotations

import difflib
import json
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from aap_config_validate.loader import _deep_merge_dicts, is_jinja
from aap_config_validate.models import (
    Issue,
    ResourceSchema,
    Severity,
    VALID_STATES,
)
from aap_config_validate.registry import (
    LEGACY_ALIASES,
    VAR_ALIASES,
    get_all_known_vars,
    get_canonical_var,
    get_wildcard_base_names,
)
from aap_config_validate.schemas import get_all_schemas

if TYPE_CHECKING:
    from aap_config_validate.config import ValidatorConfig


def _suggest_match(name: str, candidates: set[str], cutoff: float = 0.6) -> Optional[str]:
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _is_unset(value: Any) -> bool:
    """Empty string and None are treated as 'not set' (Ansible omit-style)."""
    return value is None or value == ""


def _item_label(schema: ResourceSchema, item: dict, index: int, var_name: Optional[str] = None) -> str:
    var = var_name or schema.var
    id_field = schema.item_id_field
    id_val = item.get(id_field)
    if id_val and isinstance(id_val, str) and not is_jinja(id_val):
        return f'{var}[{index}] ("{id_val}")'
    return f"{var}[{index}]"


def _source_for(sources: Optional[Dict[str, Any]], var_name: str, index: Optional[int] = None) -> Optional[str]:
    if not sources:
        return None
    loc = sources.get(var_name)
    if isinstance(loc, list):
        if index is not None and 0 <= index < len(loc):
            val = loc[index]
            return val if isinstance(val, str) else None
        return None
    if isinstance(loc, str):
        return loc
    return None


def _issue(
    severity: Severity,
    path: str,
    message: str,
    *,
    suggestion: Optional[str] = None,
    sources: Optional[Dict[str, Any]] = None,
    var_name: Optional[str] = None,
    index: Optional[int] = None,
) -> Issue:
    return Issue(
        severity=severity,
        path=path,
        message=message,
        suggestion=suggestion,
        source=_source_for(sources, var_name, index) if var_name else None,
    )


def _get_all_known_field_names(schema: ResourceSchema) -> set[str]:
    names: set[str] = set(schema.item_schema.keys())
    for field_def in schema.item_schema.values():
        if field_def.aliases:
            names.update(field_def.aliases)
    names.add("related")
    return names


def _keys_for_schema(schema: ResourceSchema, config: Dict[str, Any]) -> List[str]:
    """All config keys that hold items for this schema (canonical + aliases)."""
    keys: List[str] = []
    seen: Set[str] = set()
    candidates = [schema.var]
    if schema.aliases:
        candidates.extend(schema.aliases)
    for alias, canonical in VAR_ALIASES.items():
        if canonical == schema.var:
            candidates.append(alias)
    for key in candidates:
        if key in config and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


# ── Type checking ───────────────────────────────────────────────────

_BOOL_TRUE = frozenset({"true", "yes", "on", "1", "y"})
_BOOL_FALSE = frozenset({"false", "no", "off", "0", "n"})


def _matches_builtin(value: Any, type_name: str) -> bool:
    if type_name == "str":
        return isinstance(value, str)
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "bool":
        return isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "dict":
        return isinstance(value, dict)
    if type_name == "any":
        return True
    return False


def _coerces_to(value: Any, type_name: str) -> bool:
    """Whether a YAML/Ansible-quoted scalar is acceptable for *type_name*."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if type_name == "int":
        try:
            int(text, 10)
            return True
        except ValueError:
            return False
    if type_name == "float":
        try:
            float(text)
            return True
        except ValueError:
            return False
    if type_name == "bool":
        return text.casefold() in _BOOL_TRUE or text.casefold() in _BOOL_FALSE
    if type_name == "dict":
        try:
            parsed = json.loads(text)
            return isinstance(parsed, dict)
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
    if type_name == "list":
        try:
            parsed = json.loads(text)
            return isinstance(parsed, list)
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
    return False


def _check_type(value: Any, type_spec: str) -> bool:
    if is_jinja(value):
        return True
    for part in type_spec.split("|"):
        part = part.strip()
        if part.startswith("list["):
            if isinstance(value, list):
                return True
            continue
        if _matches_builtin(value, part) or _coerces_to(value, part):
            return True
    return False


# ── Wildcard variable merging ───────────────────────────────────────


def _build_wildcard_regex() -> re.Pattern:
    """Build a regex that matches ``{dispatch_var}_{suffix}`` for any
    known dispatch variable or alias.  Longer names are tried first so
    that e.g. ``controller_inventory_sources`` is matched before
    ``controller_inventories``.
    """
    base_names = sorted(get_wildcard_base_names(), key=len, reverse=True)
    return re.compile(r"^(" + "|".join(re.escape(n) for n in base_names) + r")_(.+)$")


def is_wildcard_var(key: str, pattern: re.Pattern | None = None) -> Optional[str]:
    """If *key* is a wildcard-suffixed dispatch variable, return the
    *canonical* base variable name.  Otherwise return ``None``.

    The ``_secure_logging`` suffix is excluded — it's a role override,
    not a data variable.  Exact known variable names (e.g.
    ``controller_settings_individuale``) are not treated as suffixes.
    """
    if key.endswith("_secure_logging"):
        return None
    if key in get_all_known_vars():
        return None
    pat = pattern or _build_wildcard_regex()
    m = pat.match(key)
    if not m:
        return None
    return get_canonical_var(m.group(1))


def config_has_wildcard_vars(config: Dict[str, Any]) -> bool:
    pattern = _build_wildcard_regex()
    return any(is_wildcard_var(key, pattern) is not None for key in config)


def merge_wildcard_vars(
    config: Dict[str, Any],
    sources: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Issue]]:
    """Merge wildcard-suffixed variables into their canonical base variables.

    Mirrors the Ansible logic in ``roles/dispatch/tasks/include_wildcard_vars.yml``:
    - Lists are concatenated
    - Dicts are deep-merged (``combine(..., recursive=true)``)

    Duplicate names in the merged list are reported later by the
    duplicate-name check.  If *sources* is provided it is updated in place.
    """
    issues: List[Issue] = []
    merged = dict(config)
    pattern = _build_wildcard_regex()

    wildcard_keys: Dict[str, List[str]] = {}
    for key in list(config.keys()):
        base = is_wildcard_var(key, pattern)
        if base is not None:
            wildcard_keys.setdefault(base, []).append(key)

    for base_var, suffixed_keys in wildcard_keys.items():
        for skey in sorted(suffixed_keys):
            suffix_val = config[skey]
            base_val = merged.get(base_var)

            # Empty env overlays (``controller_settings_dev: []`` next to a
            # dict-form ``controller_settings_all``) are a no-op.
            if suffix_val in ([], {}):
                del merged[skey]
                if sources is not None:
                    sources.pop(skey, None)
                continue
            if base_val in ([], {}):
                merged[base_var] = suffix_val
                if sources is not None:
                    extra = sources.get(skey)
                    sources[base_var] = extra if extra is not None else skey
                    sources.pop(skey, None)
                del merged[skey]
                continue

            if isinstance(suffix_val, list):
                extra_len = len(suffix_val)
                if base_val is None:
                    merged[base_var] = list(suffix_val)
                    if sources is not None:
                        extra_src = sources.get(skey, [skey] * extra_len)
                        if not isinstance(extra_src, list):
                            extra_src = [extra_src] * extra_len
                        sources[base_var] = list(extra_src)
                elif isinstance(base_val, list):
                    merged[base_var] = base_val + suffix_val
                    if sources is not None:
                        prev = sources.get(base_var, [None] * len(base_val))
                        if not isinstance(prev, list):
                            prev = [prev] * len(base_val)
                        extra_src = sources.get(skey, [skey] * extra_len)
                        if not isinstance(extra_src, list):
                            extra_src = [extra_src] * extra_len
                        sources[base_var] = list(prev) + list(extra_src)
                else:
                    issues.append(
                        _issue(
                            Severity.ERROR,
                            skey,
                            f"wildcard var is a list but base var {base_var} is {type(base_val).__name__}",
                            sources=sources,
                            var_name=skey,
                        )
                    )
                    continue
            elif isinstance(suffix_val, dict):
                if base_val is None:
                    merged[base_var] = dict(suffix_val)
                elif isinstance(base_val, dict):
                    merged[base_var] = _deep_merge_dicts(base_val, suffix_val)
                else:
                    issues.append(
                        _issue(
                            Severity.ERROR,
                            skey,
                            f"wildcard var is a dict but base var {base_var} is {type(base_val).__name__}",
                            sources=sources,
                            var_name=skey,
                        )
                    )
                    continue
                if sources is not None:
                    prev = sources.get(base_var)
                    extra = sources.get(skey, skey)
                    extra_s = extra if isinstance(extra, str) else skey
                    if isinstance(prev, str) and prev != extra_s:
                        sources[base_var] = f"{prev}, {extra_s}"
                    else:
                        sources[base_var] = extra_s
            else:
                issues.append(
                    _issue(
                        Severity.WARNING,
                        skey,
                        f"wildcard var has unexpected type {type(suffix_val).__name__}; expected list or dict",
                        sources=sources,
                        var_name=skey,
                    )
                )
                continue

            del merged[skey]
            if sources is not None:
                sources.pop(skey, None)

    return merged, issues


# ── Public validation entry point ───────────────────────────────────


def validate(
    config: Dict[str, Any],
    *,
    components: Optional[List[str]] = None,
    cfg: Optional[ValidatorConfig] = None,
    sources: Optional[Dict[str, Any]] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    all_schemas = get_all_schemas()
    known_vars = get_all_known_vars()

    if cfg and cfg.extra_known_vars:
        known_vars = known_vars | set(cfg.extra_known_vars)

    active_schemas = all_schemas
    if components:
        active_schemas = {k: v for k, v in all_schemas.items() if v.component in components}

    if not (cfg and cfg.is_check_disabled("var_names")):
        issues.extend(_check_variable_names(config, known_vars, all_schemas, cfg=cfg, sources=sources))

    for var_name, schema in active_schemas.items():
        present_keys = _keys_for_schema(schema, config)
        if not present_keys:
            alias_var = _find_alias(var_name, config, schema)
            if alias_var:
                present_keys = [alias_var]
            else:
                continue

        for actual_var in present_keys:
            value = config[actual_var]
            if not (cfg and cfg.is_check_disabled("structure")):
                issues.extend(_check_structure(actual_var, value, schema, sources=sources))

            if schema.is_list and isinstance(value, list):
                for idx, item in enumerate(value):
                    if not isinstance(item, dict):
                        continue
                    label = _item_label(schema, item, idx, actual_var)
                    if not (cfg and cfg.is_check_disabled("required_fields")):
                        issues.extend(_check_required_fields(label, item, schema, sources=sources, var_name=actual_var, index=idx))
                    if not (cfg and cfg.is_check_disabled("types")):
                        issues.extend(_check_field_types(label, item, schema, sources=sources, var_name=actual_var, index=idx))
                    if not (cfg and cfg.is_check_disabled("unknown_fields")):
                        issues.extend(_check_unknown_fields(label, item, schema, cfg=cfg, sources=sources, var_name=actual_var, index=idx))
                    if not (cfg and cfg.is_check_disabled("state")):
                        issues.extend(_check_state_value(label, item, schema, sources=sources, var_name=actual_var, index=idx))
                    if not (cfg and cfg.is_check_disabled("choices")):
                        issues.extend(_check_choices(label, item, schema, sources=sources, var_name=actual_var, index=idx))
                if not (cfg and cfg.is_check_disabled("duplicates")):
                    issues.extend(_check_duplicate_names(actual_var, value, schema, sources=sources))

    if not (cfg and cfg.is_check_disabled("xref")):
        issues.extend(_check_cross_references(config, all_schemas, active_schemas, sources=sources))
    return issues


def _find_alias(var_name: str, config: Dict[str, Any], schema: ResourceSchema) -> Optional[str]:
    if schema.aliases:
        for alias in schema.aliases:
            if alias in config:
                return alias
    for alias, canonical in VAR_ALIASES.items():
        if canonical == var_name and alias in config:
            return alias
    for legacy, canonical in LEGACY_ALIASES.items():
        if canonical == var_name and legacy in config:
            return legacy
    return None


# ── Variable-name validation ────────────────────────────────────────


def _check_variable_names(
    config: Dict[str, Any],
    known_vars: Set[str],
    schemas: Dict[str, ResourceSchema],
    *,
    cfg: Optional[ValidatorConfig] = None,
    sources: Optional[Dict[str, Any]] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    all_schema_aliases: Set[str] = set()
    for s in schemas.values():
        if s.aliases:
            all_schema_aliases.update(s.aliases)

    _ROLE_OVERRIDE_SUFFIXES = (
        "_async_retries",
        "_async_delay",
        "_loop_delay",
        "_secure_logging",
        "_enforce_defaults",
    )
    _KNOWN_PREFIXES = (
        "aap_setup_",
        "aap_configuration_working_dir",
        "filetree_",
        "controller_configuration_",
        "hub_configuration_",
        "eda_configuration_",
        "gateway_configuration_",
    )
    wildcard_pattern = _build_wildcard_regex()
    known_sorted = sorted(known_vars, key=len, reverse=True)

    for key in config:
        if key in known_vars or key in all_schema_aliases or key in VAR_ALIASES:
            continue
        if cfg and cfg.is_var_ignored(key):
            continue
        if key.startswith("_") or key.startswith("__"):
            continue
        if key.startswith(("controller_configuration_", "hub_configuration_", "eda_configuration_", "gateway_configuration_")):
            if any(key.endswith(s) for s in _ROLE_OVERRIDE_SUFFIXES):
                continue
        if any(key.startswith(prefix) for prefix in _KNOWN_PREFIXES):
            continue
        if is_wildcard_var(key, wildcard_pattern) is not None:
            continue
        # controller_license_dev, hub_roles_all, …
        if any(key.startswith(known + "_") for known in known_sorted if len(known) >= 8):
            continue
        suggestion = _suggest_match(key, known_vars)
        issues.append(
            _issue(
                Severity.WARNING,
                key,
                "unknown variable name — not in the dispatch registry",
                suggestion=f'did you mean "{suggestion}"?' if suggestion else None,
                sources=sources,
                var_name=key,
            )
        )
    return issues


# ── Structural validation ───────────────────────────────────────────


def _check_structure(
    var_name: str,
    value: Any,
    schema: ResourceSchema,
    *,
    sources: Optional[Dict[str, Any]] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    if schema.is_list:
        if not isinstance(value, list):
            if var_name in ("controller_settings", "gateway_settings") and isinstance(value, dict):
                return issues
            canonical = get_canonical_var(var_name)
            if canonical in ("controller_settings", "gateway_settings") and isinstance(value, dict):
                return issues
            issues.append(
                _issue(
                    Severity.ERROR,
                    var_name,
                    f"expected a list, got {type(value).__name__}",
                    sources=sources,
                    var_name=var_name,
                )
            )
        else:
            for idx, item in enumerate(value):
                if not isinstance(item, dict):
                    issues.append(
                        _issue(
                            Severity.ERROR,
                            f"{var_name}[{idx}]",
                            f"expected a dict, got {type(item).__name__}",
                            sources=sources,
                            var_name=var_name,
                            index=idx,
                        )
                    )
    else:
        if not isinstance(value, dict):
            issues.append(
                _issue(
                    Severity.ERROR,
                    var_name,
                    f"expected a dict, got {type(value).__name__}",
                    sources=sources,
                    var_name=var_name,
                )
            )
    return issues


def _check_duplicate_names(
    var_name: str,
    value: list,
    schema: ResourceSchema,
    *,
    sources: Optional[Dict[str, Any]] = None,
) -> List[Issue]:
    # Role assignments and similar objects are not unique by their id field
    # (many items share role: "use" with different targets).
    if schema.item_id_field not in {"name", "username", "hostname"}:
        return []
    issues: List[Issue] = []
    seen: Dict[str, int] = {}
    id_field = schema.item_id_field
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        name = item.get(id_field)
        if not isinstance(name, str) or is_jinja(name) or name == "":
            continue
        if name in seen:
            issues.append(
                _issue(
                    Severity.WARNING,
                    _item_label(schema, item, idx, var_name),
                    f'duplicate {id_field} "{name}" (also at index {seen[name]})',
                    sources=sources,
                    var_name=var_name,
                    index=idx,
                )
            )
        else:
            seen[name] = idx
    return issues


# ── Required field validation ───────────────────────────────────────


def _field_present(item: dict, field_name: str, field_def) -> bool:
    if field_name in item and not _is_unset(item.get(field_name)):
        return True
    if field_def.aliases:
        for alias in field_def.aliases:
            if alias in item and not _is_unset(item.get(alias)):
                return True
    return False


def _is_absent(item: dict) -> bool:
    state = item.get("state")
    return isinstance(state, str) and state == "absent" and not is_jinja(state)


def _check_required_fields(
    label: str,
    item: dict,
    schema: ResourceSchema,
    *,
    sources: Optional[Dict[str, Any]] = None,
    var_name: Optional[str] = None,
    index: Optional[int] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    absent = _is_absent(item)
    for field_name, field_def in schema.item_schema.items():
        if not field_def.required:
            continue
        if absent and field_name != schema.item_id_field:
            continue
        if not _field_present(item, field_name, field_def):
            issues.append(
                _issue(
                    Severity.ERROR,
                    label,
                    f'missing required field "{field_name}"',
                    sources=sources,
                    var_name=var_name,
                    index=index,
                )
            )
    return issues


# ── Type validation ─────────────────────────────────────────────────


def _check_field_types(
    label: str,
    item: dict,
    schema: ResourceSchema,
    *,
    sources: Optional[Dict[str, Any]] = None,
    var_name: Optional[str] = None,
    index: Optional[int] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    for field_name, field_def in schema.item_schema.items():
        if field_name not in item:
            continue
        value = item[field_name]
        if _is_unset(value):
            continue
        if is_jinja(value):
            issues.append(
                _issue(
                    Severity.INFO,
                    f"{label}.{field_name}",
                    "skipped — Jinja expression",
                    sources=sources,
                    var_name=var_name,
                    index=index,
                )
            )
            continue
        if not _check_type(value, field_def.type):
            issues.append(
                _issue(
                    Severity.WARNING,
                    f"{label}.{field_name}",
                    f"expected type {field_def.type}, got {type(value).__name__}",
                    sources=sources,
                    var_name=var_name,
                    index=index,
                )
            )
    return issues


# ── Unknown field validation ────────────────────────────────────────


def _check_unknown_fields(
    label: str,
    item: dict,
    schema: ResourceSchema,
    *,
    cfg: Optional[ValidatorConfig] = None,
    sources: Optional[Dict[str, Any]] = None,
    var_name: Optional[str] = None,
    index: Optional[int] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    known = _get_all_known_field_names(schema)
    schema_var = schema.var
    for key in item:
        if key in known:
            continue
        if cfg and (cfg.is_field_ignored(schema_var, key) or cfg.is_field_ignored(var_name or schema_var, key)):
            continue
        suggestion = _suggest_match(key, known)
        issues.append(
            _issue(
                Severity.WARNING,
                label,
                f'field "{key}" not recognised',
                suggestion=f'did you mean "{suggestion}"?' if suggestion else None,
                sources=sources,
                var_name=var_name,
                index=index,
            )
        )
    return issues


# ── State value validation ──────────────────────────────────────────


def _check_state_value(
    label: str,
    item: dict,
    schema: ResourceSchema,
    *,
    sources: Optional[Dict[str, Any]] = None,
    var_name: Optional[str] = None,
    index: Optional[int] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    state = item.get("state")
    if _is_unset(state) or is_jinja(state):
        return issues
    state_field = schema.item_schema.get("state")
    allowed = set(state_field.choices) if state_field and state_field.choices else VALID_STATES
    if state not in allowed:
        issues.append(
            _issue(
                Severity.ERROR,
                label,
                f'invalid state "{state}"',
                suggestion=f"allowed values: {', '.join(sorted(str(a) for a in allowed))}",
                sources=sources,
                var_name=var_name,
                index=index,
            )
        )
    return issues


# ── Choice validation ───────────────────────────────────────────────


def _check_choices(
    label: str,
    item: dict,
    schema: ResourceSchema,
    *,
    sources: Optional[Dict[str, Any]] = None,
    var_name: Optional[str] = None,
    index: Optional[int] = None,
) -> List[Issue]:
    issues: List[Issue] = []
    for field_name, field_def in schema.item_schema.items():
        if field_name == "state" or not field_def.choices:
            continue
        if field_name not in item:
            continue
        value = item[field_name]
        if _is_unset(value) or is_jinja(value):
            continue
        # Quoted numeric choices (verbosity: "3")
        comparable = value
        if isinstance(value, str) and value.isdigit():
            try:
                comparable = int(value)
            except ValueError:
                comparable = value
        if comparable not in field_def.choices and value not in field_def.choices:
            issues.append(
                _issue(
                    Severity.ERROR,
                    f"{label}.{field_name}",
                    f'value "{value}" not in allowed choices',
                    suggestion=f"allowed: {', '.join(str(c) for c in field_def.choices)}",
                    sources=sources,
                    var_name=var_name,
                    index=index,
                )
            )
    return issues


# ── Cross-reference validation ──────────────────────────────────────


def _resolve_xref_name(value: Any) -> Optional[str]:
    """Extract the name from a string or ``{name: ...}`` dict."""
    if isinstance(value, str):
        if _is_unset(value) or is_jinja(value):
            return None
        return value
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and not is_jinja(name) and not _is_unset(name):
            return name
    return None


def _name_index_for_schema(config: Dict[str, Any], schema: ResourceSchema) -> Set[str]:
    names: Set[str] = set()
    for key in _keys_for_schema(schema, config):
        data = config.get(key)
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            id_val = item.get(schema.item_id_field)
            if isinstance(id_val, str) and not is_jinja(id_val) and id_val:
                names.add(id_val)
    return names


def _check_cross_references(
    config: Dict[str, Any],
    all_schemas: Dict[str, ResourceSchema],
    active_schemas: Dict[str, ResourceSchema],
    sources: Optional[Dict[str, Any]] = None,
) -> List[Issue]:
    issues: List[Issue] = []

    name_index: Dict[str, Set[str]] = {}
    defined_targets: Set[str] = set()
    for var_name, schema in all_schemas.items():
        names = _name_index_for_schema(config, schema)
        name_index[var_name] = names
        if _keys_for_schema(schema, config):
            defined_targets.add(var_name)

    for var_name, schema in active_schemas.items():
        present_keys = _keys_for_schema(schema, config)
        if not present_keys:
            continue

        for actual_var in present_keys:
            data = config.get(actual_var)
            if not isinstance(data, list):
                continue

            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                label = _item_label(schema, item, idx, actual_var)
                for field_name, field_def in schema.item_schema.items():
                    if not field_def.xref:
                        continue
                    if field_name not in item:
                        continue

                    target_var, _target_field = field_def.xref.split(".", 1)
                    target_var = get_canonical_var(target_var)
                    value = item[field_name]

                    if isinstance(value, list):
                        refs = []
                        for v in value:
                            n = _resolve_xref_name(v)
                            if n:
                                refs.append(n)
                    else:
                        n = _resolve_xref_name(value)
                        refs = [n] if n else []

                    if target_var not in defined_targets:
                        for ref_name in refs:
                            issues.append(
                                _issue(
                                    Severity.INFO,
                                    f"{label}.{field_name}",
                                    f'references "{ref_name}" but {target_var} is not defined in config',
                                    suggestion="it may already exist on the server",
                                    sources=sources,
                                    var_name=actual_var,
                                    index=idx,
                                )
                            )
                        continue

                    target_names = name_index.get(target_var, set())
                    for ref_name in refs:
                        if ref_name not in target_names:
                            issues.append(
                                _issue(
                                    Severity.WARNING,
                                    f"{label}.{field_name}",
                                    f'references "{ref_name}" not found in {target_var}',
                                    suggestion=_suggest_match(ref_name, target_names),
                                    sources=sources,
                                    var_name=actual_var,
                                    index=idx,
                                )
                            )
    return issues
