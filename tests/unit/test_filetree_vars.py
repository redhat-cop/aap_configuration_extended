#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for filetree_create filetree_vars filter plugin."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
import os
import unittest


def _load_filter_module():
    candidates = [
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "plugins",
            "filter",
            "filetree_vars.py",
        ),
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "roles",
            "filetree_create",
            "filter_plugins",
            "filetree_vars.py",
        ),
    ]
    for candidate in candidates:
        plugin_path = os.path.abspath(candidate)
        if os.path.exists(plugin_path):
            spec = importlib.util.spec_from_file_location("filetree_vars", plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise FileNotFoundError("filetree_vars filter plugin not found in plugins/filter or role filter_plugins")


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
        self.assertIn("filetree_safe_path_component", filters)

    def test_safe_path_component_neutralizes_dotdot(self):
        self.assertEqual(self.mod.filetree_safe_path_component(".."), "_")
        self.assertEqual(self.mod.filetree_safe_path_component("."), "_")
        self.assertEqual(self.mod.filetree_safe_path_component("../x"), "x")
        self.assertEqual(self.mod.filetree_safe_path_component("org/../evil"), "org_evil")

    def test_safe_path_component_collapses_separators(self):
        self.assertEqual(self.mod.filetree_safe_path_component("a/b"), "a_b")
        self.assertEqual(self.mod.filetree_safe_path_component(r"a\b"), "a_b")
        self.assertEqual(self.mod.filetree_safe_path_component(""), "_")
        self.assertEqual(self.mod.filetree_safe_path_component(None), "_")

    def test_safe_path_component_preserves_normal_names(self):
        self.assertEqual(self.mod.filetree_safe_path_component("My Org"), "My Org")
        self.assertEqual(self.mod.filetree_safe_path_component("project-name"), "project-name")

    # --- Variable name collisions --------------------------------------------------------------

    @staticmethod
    def _cred(name, org="Default"):
        return {"name": name, "summary_fields": {"organization": {"name": org}}}

    def _names(self, objects, field="password"):
        collisions = self.mod.filetree_var_collisions(objects, "name", "summary_fields.organization.name")
        return [
            self.mod.filetree_var_name(
                "controller_credentials",
                o["name"],
                field,
                "vaulted",
                o["summary_fields"]["organization"]["name"],
                collisions,
            )
            for o in objects
        ]

    def test_collisions_names_differing_only_in_punctuation_or_case(self):
        objects = [self._cred("RH Insights"), self._cred("RH-Insights"), self._cred("rh insights"), self._cred("Other")]
        self.assertEqual(
            self.mod.filetree_var_collisions(objects, "name", "summary_fields.organization.name"),
            ["Default/RH Insights", "Default/RH-Insights", "Default/rh insights"],
        )

    def test_collisions_same_name_in_two_scopes(self):
        objects = [self._cred("GitHub", "Org A"), self._cred("GitHub", "Org B")]
        self.assertEqual(
            self.mod.filetree_var_collisions(objects, "name", "summary_fields.organization.name"),
            ["Org A/GitHub", "Org B/GitHub"],
        )

    def test_collisions_none_when_unique(self):
        objects = [self._cred("A"), self._cred("B"), {"name": None}, "not-a-dict", {"no_name": 1}]
        self.assertEqual(self.mod.filetree_var_collisions(objects, "name", "summary_fields.organization.name"), [])
        self.assertEqual(self.mod.filetree_var_collisions(None), [])

    def test_collisions_missing_scope_path_is_empty_scope(self):
        objects = [{"name": "EE"}, {"name": "ee"}]
        self.assertEqual(self.mod.filetree_var_collisions(objects, "name", "summary_fields.organization.name"), ["/EE", "/ee"])

    def test_colliding_objects_get_distinct_stable_names(self):
        objects = [self._cred("RH Insights"), self._cred("RH-Insights"), self._cred("Other")]
        names = self._names(objects)
        self.assertEqual(len(set(names)), 3)
        self.assertRegex(names[0], r"^vaulted_controller_credentials_rh_insights_[0-9a-f]{6}_password$")
        self.assertRegex(names[1], r"^vaulted_controller_credentials_rh_insights_[0-9a-f]{6}_password$")
        # Objects that don't collide keep the historical name.
        self.assertEqual(names[2], "vaulted_controller_credentials_other_password")
        # Stable across runs and independent of list order.
        self.assertEqual(self._names(list(reversed(objects))), list(reversed(names)))

    def test_same_name_in_two_scopes_gets_distinct_names(self):
        names = self._names([self._cred("GitHub", "Org A"), self._cred("GitHub", "Org B")])
        self.assertNotEqual(names[0], names[1])

    def test_var_name_without_collisions_is_unchanged(self):
        self.assertEqual(
            self.mod.filetree_var_name("controller_credentials", "RH Insights", "password", "vaulted", "Default", []),
            "vaulted_controller_credentials_rh_insights_password",
        )
        self.assertEqual(
            self.mod.filetree_var_name("controller_credentials", "RH Insights", "password", "vaulted", "Default", None),
            "vaulted_controller_credentials_rh_insights_password",
        )

    def test_as_var_passes_scope_and_collisions(self):
        collisions = ["Default/RH Insights", "Default/RH-Insights"]
        result = self.mod.filetree_as_var("", "controller_credentials", "RH Insights", "password", True, "vault", "Default", collisions)
        self.assertRegex(result, r"^\{\{ vault_controller_credentials_rh_insights_[0-9a-f]{6}_password \}\}$")

    def test_filter_module_registers_collisions_filter(self):
        self.assertIn("filetree_var_collisions", self.mod.FilterModule().filters())


if __name__ == "__main__":
    unittest.main()
