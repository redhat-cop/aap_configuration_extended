#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for filetree_create API permission-denied soft-skip detection."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import re
import unittest

import yaml

_DEFAULTS = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "roles",
        "filetree_create",
        "defaults",
        "main.yml",
    )
)

_PERMISSION_DENIED_SAMPLES = [
    "You don't have permission to GET (HTTP 403).",
    "403 Client Error: Forbidden for url: https://aap.example/apps/",
    "Status code was not [200]: HTTP Error 403: Forbidden",
    "Authentication failed: HTTP 403",
    "Forbidden",
]

_OTHER_FAILURE_SAMPLES = [
    "gateway_api lookup: failed to connect: Connection refused",
    "500 Server Error: Internal Server Error for url: https://aap.example/apps/",
    "401 Client Error: Unauthorized for url: https://aap.example/apps/",
    "Read timed out.",
    "SSL: CERTIFICATE_VERIFY_FAILED",
]


def _load_permission_denied_regex():
    with open(_DEFAULTS, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    regex = data.get("filetree_create_api_permission_denied_regex")
    if not regex:
        raise AssertionError("missing filetree_create_api_permission_denied_regex")
    return regex


class TestFiletreeCreateApiPermissionDenied(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pattern = re.compile(_load_permission_denied_regex())

    def test_matches_http_403_variants(self):
        for sample in _PERMISSION_DENIED_SAMPLES:
            self.assertIsNotNone(
                self.pattern.search(sample),
                msg="expected permission-denied match for: {0}".format(sample),
            )

    def test_does_not_match_unrelated_failures(self):
        for sample in _OTHER_FAILURE_SAMPLES:
            self.assertIsNone(
                self.pattern.search(sample),
                msg="unexpected permission-denied match for: {0}".format(sample),
            )


if __name__ == "__main__":
    unittest.main()
