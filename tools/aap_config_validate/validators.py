"""Core validation engine."""

from __future__ import annotations

import difflib
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from aap_config_validate.loader import is_jinja
from aap_config_validate.models import (
    Issue,
    ResourceSchema,
    Severity,
    VALID_STATES,
)
from aap_config_validate.registry import (
    LEGACY_ALIASES,
    get_all_known_vars,
    get_dispatch_var_names,
)
from aap_config_validate.schemas import get_all_schemas

if TYPE_CHECKING:
    from aap_config_validate.config import ValidatorConfig


def _suggest_match(name: str, candidates: set[str], cutoff: float = 0.6) -> Optional[str]:
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _item_label(schema: ResourceSchema, item: dict, index: int) -> str:
    id_field = schema.item_id_field
    id_val = item.get(id_field)
    if id_val and isinstance(id_val, str) and not is_jinja(id_val):
        return f'{schema.var}[{index}] ("{id_val}")'
    return f"{schema.var}[{index}]"


def _get_all_known_field_names(schema: ResourceSchema) -> set[str]:
    names: set[str] = set(schema.item_schema.keys())
    for field_def in schema.item_schema.values():
        if field_def.aliases:
            names.update(field_def.aliases)
    # related.* keys from API exports are allowed as pass-through
    names.add("related")
    return names


# ── Type checking ───────────────────────────────────────────────────

_PYTHON_TYPE_MAP = {
    "str": (str,),
    "int": (int,),
    "float": (int, float),
    "bool": (bool,),
    "list": (list,),
    "dict": (dict,),
    "any": (str, int, float, bool, list, dict, type(None)),
}


def _check_type(value: Any, type_spec: str) -> bool:
    if is_jinja(value):
        return True
    for part in type_spec.split("|"):
        part = part.strip()
        if part.startswith("list["):
            if isinstance(value, list):
                return True
        if part in _PYTHON_TYPE_MAP:
            if isinstance(value, _PYTHON_TYPE_MAP[part]):
                return True
    return False


# ── Wildcard variable merging ───────────────────────────────────────


def _build_wildcard_regex() -> re.Pattern:
    """Build a regex that matches ``{dispatch_var}_{suffix}`` for any
    known dispatch variable name.  Longer names are tried first so that
    e.g. ``controller_inventory_sources`` is matched before
    ``controller_inventories``.
    """
    base_names = sorted(get_dispatch_var_names(), key=len, reverse=True)
    return re.compile(r"^(" + "|".join(re.escape(n) for n in base_names) + r")_(.+)$")


def is_wildcard_var(key: str, pattern: re.Pattern | None = None) -> Optional[str]:
    """If *key* is a wildcard-suffixed dispatch variable, return the base
    variable name.  Otherwise return ``None``.

    The ``_secure_logging`` suffix is excluded — it's a role override,
    not a data variable.
    """
    if key.endswith("_secure_logging"):
        return None
    pat = pattern or _build_wildcard_regex()
    m = pat.match(key)
    return m.group(1) if m else None


def merge_wildcard_vars(config: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Issue]]:
    """Merge wildcard-suffixed variables into their base variables.

    Mirrors the Ansible logic in ``roles/dispatch/tasks/include_wildcard_vars.yml``:
    - Lists are concatenated (with dedup via seen-name tracking)
    - Dicts are deep-merged (``combine(..., recursive=true)``)

    Returns a *new* config dict and any issues found during merging.
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

            if isinstance(suffix_val, list):
                if base_val is None:
                    merged[base_var] = list(suffix_val)
                elif isinstance(base_val, list):
                    merged[base_var] = base_val + suffix_val
                else:
                    issues.append(
                        Issue(
                            severity=Severity.ERROR,
                            path=skey,
                            message=f"wildcard var is a list but base var {base_var} is {type(base_val).__name__}",
                        )
                    )
                    continue
            elif isinstance(suffix_val, dict):
                if base_val is None:
                    merged[base_var] = dict(suffix_val)
                elif isinstance(base_val, dict):
                    merged[base_var] = {**base_val, **suffix_val}
                else:
                    issues.append(
                        Issue(
                            severity=Severity.ERROR,
                            path=skey,
                            message=f"wildcard var is a dict but base var {base_var} is {type(base_val).__name__}",
                        )
                    )
                    continue
            else:
                issues.append(
                    Issue(
                        severity=Severity.WARNING,
                        path=skey,
                        message=f"wildcard var has unexpected type {type(suffix_val).__name__}; expected list or dict",
                    )
                )
                continue

            del merged[skey]

    return merged, issues


# ── Public validation entry point ───────────────────────────────────


def validate(config: Dict[str, Any], *, components: Optional[List[str]] = None, cfg: Optional[ValidatorConfig] = None) -> List[Issue]:
    issues: List[Issue] = []
    schemas = get_all_schemas()
    known_vars = get_all_known_vars()

    if cfg and cfg.extra_known_vars:
        known_vars = known_vars | set(cfg.extra_known_vars)

    if components:
        schemas = {k: v for k, v in schemas.items() if v.component in components}

    if not (cfg and cfg.is_check_disabled("var_names")):
        issues.extend(_check_variable_names(config, known_vars, schemas, cfg=cfg))

    for var_name, schema in schemas.items():
        if var_name not in config:
            alias_var = _find_alias(var_name, config, schema)
            if alias_var:
                var_name = alias_var
            else:
                continue

        value = config[var_name]
        if not (cfg and cfg.is_check_disabled("structure")):
            issues.extend(_check_structure(var_name, value, schema))

        if schema.is_list and isinstance(value, list):
            for idx, item in enumerate(value):
                if not isinstance(item, dict):
                    continue
                label = _item_label(schema, item, idx)
                if not (cfg and cfg.is_check_disabled("required_fields")):
                    issues.extend(_check_required_fields(label, item, schema))
                if not (cfg and cfg.is_check_disabled("types")):
                    issues.extend(_check_field_types(label, item, schema))
                if not (cfg and cfg.is_check_disabled("unknown_fields")):
                    issues.extend(_check_unknown_fields(label, item, schema, cfg=cfg))
                if not (cfg and cfg.is_check_disabled("state")):
                    issues.extend(_check_state_value(label, item, schema))
                if not (cfg and cfg.is_check_disabled("choices")):
                    issues.extend(_check_choices(label, item, schema))

    if not (cfg and cfg.is_check_disabled("xref")):
        issues.extend(_check_cross_references(config, schemas))
    return issues


def _find_alias(var_name: str, config: Dict[str, Any], schema: ResourceSchema) -> Optional[str]:
    if schema.aliases:
        for alias in schema.aliases:
            if alias in config:
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
    wildcard_pattern = _build_wildcard_regex()

    for key in config:
        if key in known_vars or key in all_schema_aliases:
            continue
        if cfg and cfg.is_var_ignored(key):
            continue
        # Skip private/internal vars
        if key.startswith("_") or key.startswith("__"):
            continue
        # Per-role override vars like controller_configuration_*_async_delay
        if key.startswith(("controller_configuration_", "hub_configuration_", "eda_configuration_")):
            if any(key.endswith(s) for s in _ROLE_OVERRIDE_SUFFIXES):
                continue
        # Wildcard-suffixed vars (e.g. controller_templates_production)
        if is_wildcard_var(key, wildcard_pattern) is not None:
            continue
        suggestion = _suggest_match(key, known_vars)
        issues.append(
            Issue(
                severity=Severity.WARNING,
                path=key,
                message="unknown variable name — not in the dispatch registry",
                suggestion=f'did you mean "{suggestion}"?' if suggestion else None,
            )
        )
    return issues


# ── Structural validation ───────────────────────────────────────────


def _check_structure(var_name: str, value: Any, schema: ResourceSchema) -> List[Issue]:
    issues: List[Issue] = []
    if schema.is_list:
        if not isinstance(value, list):
            # controller_settings can be a dict or list
            if var_name in ("controller_settings", "gateway_settings") and isinstance(value, dict):
                return issues
            issues.append(
                Issue(
                    severity=Severity.ERROR,
                    path=var_name,
                    message=f"expected a list, got {type(value).__name__}",
                )
            )
        else:
            for idx, item in enumerate(value):
                if not isinstance(item, dict):
                    issues.append(
                        Issue(
                            severity=Severity.ERROR,
                            path=f"{var_name}[{idx}]",
                            message=f"expected a dict, got {type(item).__name__}",
                        )
                    )
    else:
        if not isinstance(value, dict):
            issues.append(
                Issue(
                    severity=Severity.ERROR,
                    path=var_name,
                    message=f"expected a dict, got {type(value).__name__}",
                )
            )
    return issues


# ── Required field validation ───────────────────────────────────────


def _check_required_fields(label: str, item: dict, schema: ResourceSchema) -> List[Issue]:
    issues: List[Issue] = []
    for field_name, field_def in schema.item_schema.items():
        if not field_def.required:
            continue
        present = field_name in item
        if not present and field_def.aliases:
            present = any(a in item for a in field_def.aliases)
        if not present:
            issues.append(
                Issue(
                    severity=Severity.ERROR,
                    path=label,
                    message=f'missing required field "{field_name}"',
                )
            )
    return issues


# ── Type validation ─────────────────────────────────────────────────


def _check_field_types(label: str, item: dict, schema: ResourceSchema) -> List[Issue]:
    issues: List[Issue] = []
    for field_name, field_def in schema.item_schema.items():
        if field_name not in item:
            continue
        value = item[field_name]
        if value is None:
            continue
        if is_jinja(value):
            issues.append(
                Issue(
                    severity=Severity.INFO,
                    path=f"{label}.{field_name}",
                    message="skipped — Jinja expression",
                )
            )
            continue
        if not _check_type(value, field_def.type):
            issues.append(
                Issue(
                    severity=Severity.WARNING,
                    path=f"{label}.{field_name}",
                    message=f"expected type {field_def.type}, got {type(value).__name__}",
                )
            )
    return issues


# ── Unknown field validation ────────────────────────────────────────


def _check_unknown_fields(label: str, item: dict, schema: ResourceSchema, *, cfg: Optional[ValidatorConfig] = None) -> List[Issue]:
    issues: List[Issue] = []
    known = _get_all_known_field_names(schema)
    for key in item:
        if key in known:
            continue
        if cfg and cfg.is_field_ignored(schema.var, key):
            continue
        suggestion = _suggest_match(key, known)
        issues.append(
            Issue(
                severity=Severity.WARNING,
                path=label,
                message=f'field "{key}" not recognised',
                suggestion=f'did you mean "{suggestion}"?' if suggestion else None,
            )
        )
    return issues


# ── State value validation ──────────────────────────────────────────


def _check_state_value(label: str, item: dict, schema: ResourceSchema) -> List[Issue]:
    issues: List[Issue] = []
    state = item.get("state")
    if state is None or is_jinja(state):
        return issues
    state_field = schema.item_schema.get("state")
    allowed = set(state_field.choices) if state_field and state_field.choices else VALID_STATES
    if state not in allowed:
        issues.append(
            Issue(
                severity=Severity.ERROR,
                path=label,
                message=f'invalid state "{state}"',
                suggestion=f"allowed values: {', '.join(sorted(allowed))}",
            )
        )
    return issues


# ── Choice validation ───────────────────────────────────────────────


def _check_choices(label: str, item: dict, schema: ResourceSchema) -> List[Issue]:
    issues: List[Issue] = []
    for field_name, field_def in schema.item_schema.items():
        if field_name == "state" or not field_def.choices:
            continue
        if field_name not in item:
            continue
        value = item[field_name]
        if is_jinja(value):
            continue
        if value not in field_def.choices:
            issues.append(
                Issue(
                    severity=Severity.ERROR,
                    path=f"{label}.{field_name}",
                    message=f'value "{value}" not in allowed choices',
                    suggestion=f"allowed: {', '.join(str(c) for c in field_def.choices)}",
                )
            )
    return issues


# ── Cross-reference validation ──────────────────────────────────────


def _resolve_xref_name(value: Any) -> Optional[str]:
    """Extract the name from a string or ``{name: ...}`` dict."""
    if isinstance(value, str):
        return value if not is_jinja(value) else None
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and not is_jinja(name):
            return name
    return None


def _check_cross_references(
    config: Dict[str, Any],
    schemas: Dict[str, ResourceSchema],
) -> List[Issue]:
    issues: List[Issue] = []

    # Build lookup tables: var_name -> set of defined names
    name_index: Dict[str, Set[str]] = {}
    for var_name, schema in schemas.items():
        data = config.get(var_name)
        if data is None and schema.aliases:
            for alias in schema.aliases:
                if alias in config:
                    data = config[alias]
                    break
        if not isinstance(data, list):
            continue
        names: Set[str] = set()
        for item in data:
            if not isinstance(item, dict):
                continue
            id_val = item.get(schema.item_id_field)
            if isinstance(id_val, str) and not is_jinja(id_val):
                names.add(id_val)
        name_index[var_name] = names

    # Now check every xref
    for var_name, schema in schemas.items():
        data = config.get(var_name)
        if data is None and schema.aliases:
            for alias in schema.aliases:
                if alias in config:
                    data = config[alias]
                    break
        if not isinstance(data, list):
            continue

        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            label = _item_label(schema, item, idx)
            for field_name, field_def in schema.item_schema.items():
                if not field_def.xref:
                    continue
                if field_name not in item:
                    continue

                target_var, target_field = field_def.xref.split(".", 1)
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

                if target_var not in name_index:
                    for ref_name in refs:
                        issues.append(
                            Issue(
                                severity=Severity.INFO,
                                path=f"{label}.{field_name}",
                                message=f'references "{ref_name}" but {target_var} is not defined in config',
                                suggestion="it may already exist on the server",
                            )
                        )
                    continue

                target_names = name_index[target_var]
                for ref_name in refs:
                    if ref_name not in target_names:
                        issues.append(
                            Issue(
                                severity=Severity.WARNING,
                                path=f"{label}.{field_name}",
                                message=f'references "{ref_name}" not found in {target_var}',
                                suggestion=_suggest_match(ref_name, target_names),
                            )
                        )
    return issues
