# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat Automation Community of Practice
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for controller_object_diff lookup (EE identity)."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
LOOKUP_PATH = ROOT / "plugins" / "lookup" / "controller_object_diff.py"


def _load_lookup_module():
    """Load lookup with ansible deps stubbed so LookupBase is a real base class."""

    class LookupBase(object):
        pass

    ansible_errors = mock.MagicMock()
    ansible_errors.AnsibleError = Exception
    ansible_errors.AnsibleLookupError = Exception

    sys.modules["ansible"] = mock.MagicMock()
    sys.modules["ansible.errors"] = ansible_errors
    sys.modules["ansible.module_utils"] = mock.MagicMock()
    sys.modules["ansible.module_utils._text"] = mock.MagicMock(to_native=lambda x: x)
    sys.modules["ansible.plugins"] = mock.MagicMock()
    lookup_mod = mock.MagicMock()
    lookup_mod.LookupBase = LookupBase
    sys.modules["ansible.plugins.lookup"] = lookup_mod
    sys.modules["ansible.utils"] = mock.MagicMock()
    display_mod = mock.MagicMock()
    display_mod.Display = mock.MagicMock
    sys.modules["ansible.utils.display"] = display_mod

    spec = importlib.util.spec_from_file_location("controller_object_diff", LOOKUP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diff_mod = _load_lookup_module()


class FakeLookup(diff_mod.LookupModule):
    """LookupModule with option getters stubbed for direct run() calls."""

    def __init__(self, options):
        self._options = options
        self.display = mock.MagicMock()
        self._display = self.display

    def set_options(self, direct=None, **kwargs):
        if direct:
            self._options.update(direct)

    def get_option(self, name):
        return self._options[name]


class ExecutionEnvironmentIdentityTest(unittest.TestCase):
    def test_image_change_is_present_only(self):
        """Same name+org with different image must not emit state=absent (#421)."""
        api_list = [
            {
                "type": "execution_environment",
                "name": "my-ee",
                "image": "quay.io/old:1",
                "summary_fields": {"organization": {"name": "Default"}},
            }
        ]
        compare_list = [
            {
                "name": "my-ee",
                "organization": "Default",
                "image": "quay.io/new:2",
            }
        ]
        lookup = FakeLookup(
            {
                "api_list": api_list,
                "compare_list": compare_list,
                "set_absent": True,
                "with_present": True,
                "warn_on_empty_api": True,
            }
        )
        result = lookup.run([], None)
        items = result[0]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "my-ee")
        self.assertEqual(items[0]["state"], "present")
        self.assertEqual(items[0]["image"], "quay.io/new:2")
        self.assertFalse(any(item.get("state") == "absent" for item in items))


if __name__ == "__main__":
    unittest.main()
