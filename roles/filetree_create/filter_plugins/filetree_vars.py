# -*- coding: utf-8 -*-
"""Jinja filters to export environment-specific values as Ansible variables."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import hashlib
import re


def _sanitize(value):
    """Normalize a name/field to a safe Ansible variable fragment."""
    return re.sub(r"[^a-z0-9]", "_", str(value).lower())


def _dig(obj, path):
    """Return obj[a][b]... for a dotted path, or None if any part is missing."""
    for part in str(path).split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def _collision_key(scope, name):
    """Exact identity of an object within its type: scope (organization, inventory...) + name."""
    return "{0}/{1}".format("" if scope is None else scope, name)


def _collision_suffix(scope, name):
    """Short, stable suffix that tells colliding objects apart."""
    return hashlib.sha256(_collision_key(scope, name).encode("utf-8")).hexdigest()[:6]


def filetree_var_collisions(objects, name_attr="name", scope_attr=None):
    """
    Return the identities (``scope/name``) of objects whose variable names would collide.

    Two objects collide when their names sanitize to the same fragment: names that differ
    only in case or punctuation (``RH Insights`` / ``RH-Insights``), or the same name in two
    scopes (for example two organizations). Pass the result to ``filetree_var_name`` /
    ``filetree_as_var`` (``collisions``) so those objects get a distinguishing suffix.
    """
    groups = {}
    for obj in objects or []:
        if not isinstance(obj, dict):
            continue
        name = _dig(obj, name_attr)
        if name is None or name == "":
            continue
        scope = _dig(obj, scope_attr) if scope_attr else None
        groups.setdefault(_sanitize(name), set()).add(_collision_key(scope, name))
    return sorted(key for keys in groups.values() if len(keys) > 1 for key in keys)


def filetree_var_name(object_type, name, field, prefix="vaulted", scope=None, collisions=None):
    """
    Build the canonical variable name for an exported field.

    When the object is listed in ``collisions`` (see ``filetree_var_collisions``), a short
    hash of its scope and exact name is added after the name, so objects whose names would
    otherwise map to the same variable each get their own. Other names are unchanged.
    """
    fragment = _sanitize(name)
    if collisions and _collision_key(scope, name) in set(collisions):
        fragment = "{0}_{1}".format(fragment, _collision_suffix(scope, name))
    return "{0}_{1}_{2}_{3}".format(
        prefix,
        object_type,
        fragment,
        _sanitize(field),
    )


def filetree_as_var(value, object_type, name, field, enabled=False, prefix="vaulted", scope=None, collisions=None):
    """
    Return a Jinja variable reference when enabled, otherwise the original value.

    The returned reference is the literal text ``{{ var_name }}`` so it survives
    rendering into YAML and can be resolved later via extra vars / vault files.
    """
    if not enabled:
        return value
    return "{{ " + filetree_var_name(object_type, name, field, prefix=prefix, scope=scope, collisions=collisions) + " }}"


def filetree_safe_path_component(value):
    """
    Return a single path component safe to join under ``output_path``.

    Replaces path separators, drops ``.`` / ``..`` segments so AAP object names
    cannot escape the export directory, and returns ``_`` when nothing remains.
    """
    if value is None:
        return "_"
    normalized = str(value).replace("\\", "/")
    parts = []
    for part in normalized.split("/"):
        if part in ("", ".", ".."):
            continue
        parts.append(part)
    joined = "_".join(parts)
    if joined in ("", ".", ".."):
        return "_"
    return joined


class FilterModule(object):
    """Ansible filter plugin."""

    def filters(self):
        return {
            "filetree_as_var": filetree_as_var,
            "filetree_var_name": filetree_var_name,
            "filetree_var_collisions": filetree_var_collisions,
            "filetree_safe_path_component": filetree_safe_path_component,
        }
