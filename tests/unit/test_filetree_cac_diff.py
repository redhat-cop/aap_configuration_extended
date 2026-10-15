#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for filetree_cac_diff module utilities."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
import os
import tempfile
import unittest


def _load_module_utils():
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "plugins",
        "module_utils",
        "filetree_cac_diff.py",
    )
    spec = importlib.util.spec_from_file_location("filetree_cac_diff", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFiletreeCacDiff(unittest.TestCase):
    def setUp(self):
        self.module = _load_module_utils()

    def test_gateway_organizations_normalized_to_aap_organizations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            live_path = os.path.join(tmpdir, "live")
            cac_path = os.path.join(tmpdir, "cac")
            diff_path = os.path.join(tmpdir, "diff")
            os.makedirs(live_path)
            os.makedirs(cac_path)

            with open(os.path.join(live_path, "organizations.yaml"), "w", encoding="utf-8") as handle:
                handle.write("---\ngateway_organizations:\n  - name: Default\n")

            with open(os.path.join(cac_path, "organizations.yaml"), "w", encoding="utf-8") as handle:
                handle.write("---\naap_organizations:\n  - name: Default\n")

            result = self.module.compare_filetrees(
                live_paths=[live_path],
                cac_paths=[cac_path],
                diff_path=diff_path,
                root_keys_filter=["aap_organizations"],
            )

            self.assertEqual(result["unchanged_count"], 1)
            self.assertEqual(result["present_count"], 0)
            self.assertEqual(result["absent_count"], 0)
            self.assertEqual(result["diff_files"], [])

    def test_canonical_root_key_alias(self):
        self.assertEqual(
            self.module.canonical_root_key("gateway_organizations"),
            "aap_organizations",
        )
        self.assertEqual(
            self.module.canonical_root_key("controller_projects"),
            "controller_projects",
        )

    def test_schedule_without_organization_passes_org_filter(self):
        schedule = {
            "name": "Object Diff Shared Schedule",
            "unified_job_template": "Object Diff Shared Job Template",
            "rrule": "DTSTART:20260101T000000Z RRULE:FREQ=DAILY;INTERVAL=1",
        }
        self.assertTrue(self.module.matches_organization_filter(schedule, "Object Diff Test"))

    def test_credential_input_source_identity_keys(self):
        self.assertEqual(
            self.module.get_id_keys("credential_input_source"),
            ["target_credential", "source_credential", "input_field_name"],
        )
        self.assertEqual(
            self.module.ROOT_KEY_OBJECT_TYPE["controller_credential_input_sources"],
            "credential_input_source",
        )

    def test_gateway_hub_eda_root_keys_registered(self):
        for root_key in (
            "gateway_authenticators",
            "gateway_role_user_assignments",
            "gateway_settings",
            "controller_instances",
            "controller_labels",
            "controller_settings",
            "eda_credentials",
            "eda_rulebook_activations",
            "hub_namespaces",
            "hub_ee_images",
        ):
            self.assertIn(root_key, self.module.ROOT_KEY_OBJECT_TYPE)

    def test_list_valued_identity_keys_are_hashable(self):
        identity = self.module.object_identity(
            "role_user_assignment",
            {
                "role_definition": "Organization Admin",
                "user": "admin",
                "object_ids": ["Default"],
            },
        )
        self.assertIsInstance(identity, tuple)
        # Must be usable as a dict key.
        self.assertEqual({identity: True}[identity], True)

    def test_settings_written_as_mapping_not_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            live_path = os.path.join(tmpdir, "live")
            cac_path = os.path.join(tmpdir, "cac")
            diff_path = os.path.join(tmpdir, "diff")
            os.makedirs(live_path)
            os.makedirs(cac_path)

            with open(os.path.join(live_path, "settings.yaml"), "w", encoding="utf-8") as handle:
                handle.write("---\ngateway_settings:\n  gateway_basic_auth_enabled: 'true'\n")

            with open(os.path.join(cac_path, "settings.yaml"), "w", encoding="utf-8") as handle:
                handle.write("---\ngateway_settings:\n  gateway_basic_auth_enabled: 'false'\n")

            result = self.module.compare_filetrees(
                live_paths=[live_path],
                cac_paths=[cac_path],
                diff_path=diff_path,
                root_keys_filter=["gateway_settings"],
            )

            self.assertEqual(result["present_count"], 1)
            self.assertEqual(result["absent_count"], 0)
            self.assertEqual(len(result["diff_files"]), 1)
            with open(result["diff_files"][0], encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("gateway_settings:", content)
            self.assertNotIn("gateway_settings:\n- ", content)
            self.assertIn("gateway_basic_auth_enabled: 'false'", content)
            self.assertNotIn("state:", content)

    def test_instance_identity_uses_hostname(self):
        self.assertEqual(self.module.get_id_keys("instance"), ["hostname"])
        self.assertEqual(
            self.module.object_identity(
                "instance",
                {"hostname": "exec1.example.com", "node_type": "execution"},
            ),
            ("exec1.example.com",),
        )

    def test_equal_dicts_compares_cac_fields_not_only_identity(self):
        ignore = set()
        cac = {
            "name": "Demo Project",
            "organization": "Default",
            "scm_type": "git",
            "scm_url": "https://example.com/desired.git",
        }
        live_same_identity_different_url = {
            "name": "Demo Project",
            "organization": "Default",
            "scm_type": "git",
            "scm_url": "https://example.com/live.git",
        }
        live_missing_cac_field = {
            "name": "Demo Project",
            "organization": "Default",
            "scm_type": "git",
        }
        live_extra_field_ok = dict(cac, scm_branch="devel")

        self.assertFalse(self.module.equal_dicts(cac, live_same_identity_different_url, ignore))
        self.assertFalse(self.module.equal_dicts(cac, live_missing_cac_field, ignore))
        self.assertTrue(self.module.equal_dicts(cac, live_extra_field_ok, ignore))
        self.assertTrue(self.module.equal_dicts(cac, dict(cac), ignore))

    def test_field_drift_emits_present_with_full_cac_item(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            live_path = os.path.join(tmpdir, "live")
            cac_path = os.path.join(tmpdir, "cac")
            diff_path = os.path.join(tmpdir, "diff")
            os.makedirs(live_path)
            os.makedirs(cac_path)

            with open(os.path.join(live_path, "projects.yaml"), "w", encoding="utf-8") as handle:
                handle.write(
                    "---\n"
                    "controller_projects:\n"
                    "  - name: Demo\n"
                    "    organization: Default\n"
                    "    scm_type: git\n"
                    "    scm_url: https://example.com/live.git\n"
                )

            with open(os.path.join(cac_path, "projects.yaml"), "w", encoding="utf-8") as handle:
                handle.write(
                    "---\n"
                    "controller_projects:\n"
                    "  - name: Demo\n"
                    "    organization: Default\n"
                    "    scm_type: git\n"
                    "    scm_url: https://example.com/desired.git\n"
                    "    scm_branch: main\n"
                )

            result = self.module.compare_filetrees(
                live_paths=[live_path],
                cac_paths=[cac_path],
                diff_path=diff_path,
                root_keys_filter=["controller_projects"],
            )

            self.assertEqual(result["present_count"], 1)
            self.assertEqual(result["unchanged_count"], 0)
            self.assertEqual(result["absent_count"], 0)
            with open(result["diff_files"][0], encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("scm_url: https://example.com/desired.git", content)
            self.assertIn("scm_branch: main", content)
            self.assertIn("state: present", content)

    def test_nested_cac_dict_subset_comparison(self):
        ignore = set()
        cac = {"name": "JT", "organization": "Default", "extra_vars": {"env": "pro", "region": "eu"}}
        live_missing_nested = {"name": "JT", "organization": "Default", "extra_vars": {"env": "pro"}}
        live_with_extra_nested = {
            "name": "JT",
            "organization": "Default",
            "extra_vars": {"env": "pro", "region": "eu", "debug": True},
        }
        self.assertFalse(self.module.equal_dicts(cac, live_missing_nested, ignore))
        self.assertTrue(self.module.equal_dicts(cac, live_with_extra_nested, ignore))


if __name__ == "__main__":
    unittest.main()
