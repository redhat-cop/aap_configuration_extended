#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guard against self-referential Jinja in Ansible task ``vars:`` blocks.

``key: "{{ key | default([]) }}"`` under task ``vars:`` evaluates the key while
defining it and raises ``Recursive loop detected in template`` (see issue #430).

``set_fact`` accumulation (``x: "{{ x | default([]) + [...] }}"``) is allowed
and is not scanned here.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import re
import unittest

# Pure self-default: name: "{{ name | default(...) }}" with nothing else.
_SELF_DEFAULT = re.compile(r"^([ \t]*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*" r"[\"']\{\{\s*\2\s*\|\s*default\([^)]*\)\s*\}\}[\"']\s*$")
_VARS_KEY = re.compile(r"^([ \t]*)vars\s*:\s*$")
_TASK_KEY = re.compile(r"^([ \t]*)-\s+name\s*:")


def _role_task_yaml_files():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "roles"))
    for dirpath, _dirnames, filenames in os.walk(root):
        if os.path.basename(dirpath) != "tasks":
            continue
        for name in filenames:
            if name.endswith((".yml", ".yaml")):
                yield os.path.join(dirpath, name)


def _find_self_ref_in_task_vars(path):
    """Return list of (lineno, line) for self-defaults inside task vars blocks."""
    hits = []
    in_vars = False
    vars_indent = None
    with open(path, encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue

            task_match = _TASK_KEY.match(line)
            if task_match is not None:
                in_vars = False
                vars_indent = None
                continue

            vars_match = _VARS_KEY.match(line)
            if vars_match is not None:
                in_vars = True
                vars_indent = len(vars_match.group(1))
                continue

            if not in_vars:
                continue

            indent = len(line) - len(line.lstrip(" \t"))
            # Left the vars: mapping (sibling or outer key).
            if indent <= vars_indent and not line.lstrip().startswith("-"):
                in_vars = False
                vars_indent = None
                continue

            match = _SELF_DEFAULT.match(line)
            if match is not None:
                hits.append((lineno, line.strip()))
    return hits


class TestNoJinjaSelfRefTaskVars(unittest.TestCase):
    def test_no_self_default_under_task_vars(self):
        violations = []
        for path in _role_task_yaml_files():
            for lineno, text in _find_self_ref_in_task_vars(path):
                rel = os.path.relpath(path, os.path.join(os.path.dirname(__file__), "..", ".."))
                violations.append("{0}:{1}: {2}".format(rel, lineno, text))

        self.assertEqual(
            violations,
            [],
            msg=(
                "Self-referential Jinja under task vars: causes recursive loops "
                "(issue #430). Remove the mapping or rename the RHS source. "
                "Found:\n  - " + "\n  - ".join(violations)
            ),
        )


if __name__ == "__main__":
    unittest.main()
