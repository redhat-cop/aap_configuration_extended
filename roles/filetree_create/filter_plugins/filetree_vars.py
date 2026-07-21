# -*- coding: utf-8 -*-
"""Jinja filters to export environment-specific values as Ansible variables."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re


def _sanitize(value):
    """Normalize a name/field to a safe Ansible variable fragment."""
    return re.sub(r"[^a-z0-9]", "_", str(value).lower())


def filetree_var_name(object_type, name, field, prefix="vaulted"):
    """Build the canonical variable name for an exported field."""
    return "{0}_{1}_{2}_{3}".format(
        prefix,
        object_type,
        _sanitize(name),
        _sanitize(field),
    )


def filetree_as_var(value, object_type, name, field, enabled=False, prefix="vaulted"):
    """
    Return a Jinja variable reference when enabled, otherwise the original value.

    The returned reference is the literal text ``{{ var_name }}`` so it survives
    rendering into YAML and can be resolved later via extra vars / vault files.
    """
    if not enabled:
        return value
    return "{{ " + filetree_var_name(object_type, name, field, prefix=prefix) + " }}"


class FilterModule(object):
    """Ansible filter plugin."""

    def filters(self):
        return {
            "filetree_as_var": filetree_as_var,
            "filetree_var_name": filetree_var_name,
        }
