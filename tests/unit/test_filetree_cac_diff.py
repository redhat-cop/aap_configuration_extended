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


if __name__ == "__main__":
    unittest.main()
