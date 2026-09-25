# -*- coding: utf-8 -*-
"""Jinja filter for managing true/false values as strings in surveys."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleFilterError
from ansible.module_utils._text import to_native


def filetree_surveys_cleanup(templates):
    """
    Returns the input templates list with surveys values fixed where needed.

    For surveys with type other than integer and float, the "default" and "choices" values are forced to be string.
    String values like "true" and "false" are implicitly converted into boolean by jinja, thus causing an import failure
    for survey types where those strings are allowed.
    """
    if not isinstance(templates, list):
        raise AnsibleFilterError("Input value must be a list")

    try:
        for template in templates:
            if "survey_spec" in template:
                for question in template["survey_spec"]["spec"]:
                    if question.get("type") not in ("integer", "float"):
                        if "default" in question:
                            question["default"] = str(question["default"])
                        if "choices" in question:
                            question["choices"] = [str(x) for x in question["choices"]]

        return templates

    except Exception as e:
        raise AnsibleFilterError("Failed! Original exception was: %s" % to_native(e))


class FilterModule(object):
    """Ansible filter plugin."""

    def filters(self):
        return {"filetree_surveys_cleanup": filetree_surveys_cleanup}
