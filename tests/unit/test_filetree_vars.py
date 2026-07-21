#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for filetree_create filetree_vars filter plugin."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
import os
import unittest


def _load_filter_module():
    plugin_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "roles",
        "filetree_create",
        "filter_plugins",
        "filetree_vars.py",
    )
    plugin_path = os.path.abspath(plugin_path)
    spec = importlib.util.spec_from_file_location("filetree_vars", plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFiletreeVarsFilters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_filter_module()

    def test_var_name_sanitizes(self):
        name = self.mod.filetree_var_name("controller_projects", "My Project!", "scm_url", prefix="vaulted")
        self.assertEqual(name, "vaulted_controller_projects_my_project__scm_url")

    def test_as_var_disabled_returns_value(self):
        result = self.mod.filetree_as_var(
            "https://git.example/repo.git",
            "controller_projects",
            "demo",
            "scm_url",
            enabled=False,
        )
        self.assertEqual(result, "https://git.example/repo.git")

    def test_as_var_enabled_returns_placeholder(self):
        result = self.mod.filetree_as_var(
            "https://git.example/repo.git",
            "controller_projects",
            "demo",
            "scm_url",
            enabled=True,
            prefix="vaulted",
        )
        self.assertEqual(result, "{{ vaulted_controller_projects_demo_scm_url }}")

    def test_filter_module_registers_filters(self):
        filters = self.mod.FilterModule().filters()
        self.assertIn("filetree_as_var", filters)
        self.assertIn("filetree_var_name", filters)


if __name__ == "__main__":
    unittest.main()
