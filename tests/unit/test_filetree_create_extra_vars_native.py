"""Ensure filetree_create exports extra_vars with native YAML types."""

from pathlib import Path
import re
import unittest

from jinja2 import Environment, FileSystemLoader
import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / "roles" / "filetree_create" / "templates"

# Mirrors the extra_vars mapping branch in controller_job_templates.j2 /
# controller_workflow_job_templates.j2 so unit tests stay free of Ansible filters.
EXTRA_VARS_SNIPPET = """
{% import 'macros/yaml_value.j2' as yamlval %}
---
extra_vars:
{% for extra_vars_item in (extra_vars_contents | dict2items) if (
     extra_vars_item.value == ''
     or ((extra_vars_item.value | string | length) > 0 and (extra_vars_item.value | string) is not match('None'))
   ) %}
{%   if extra_vars_item.value | type_debug is match('list') %}
{%     if (extra_vars_item.value | length) == 0 %}
  {{ extra_vars_item.key }}: []
{%     else %}
  {{ extra_vars_item.key }}:
{%       for current_list_item in extra_vars_item.value
           if ((extra_vars_item.value | string | length) > 0
               and (extra_vars_item.value | string) is not match('None')) %}
    - {{ yamlval.render_cac_scalar(current_list_item) }}
{%       endfor %}
{%     endif %}
{%   elif extra_vars_item.value is mapping %}
  {{ extra_vars_item.key }}:
{{ yamlval.render_value(extra_vars_item.value, indent_width=4, first_indent=true) }}
{%   else %}
  {{ extra_vars_item.key }}: {{ yamlval.render_cac_scalar(extra_vars_item.value) }}
{%   endif %}
{% endfor %}
"""


def _build_environment():
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    environment.filters["dict2items"] = lambda value: [{"key": key, "value": item} for key, item in value.items()]
    environment.filters["to_nice_yaml"] = lambda value, indent=2, sort_keys=False: yaml.safe_dump(value, indent=indent, sort_keys=sort_keys)
    environment.filters["bool"] = lambda value: str(value).lower() in (
        "true",
        "1",
        "yes",
    )
    environment.filters["int"] = int
    environment.filters["float"] = float
    environment.filters["lower"] = lambda value: str(value).lower()
    environment.filters["regex_replace"] = lambda value, pattern, repl: re.sub(pattern, repl, str(value))
    environment.filters["string"] = str
    environment.filters["type_debug"] = lambda value: type(value).__name__
    environment.tests["boolean"] = lambda value: isinstance(value, bool)
    environment.tests["number"] = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)
    environment.tests["match"] = lambda value, pattern: re.match(pattern, str(value)) is not None
    return environment


def _render_cac_scalar(value):
    environment = _build_environment()
    template = environment.from_string("{% import 'macros/yaml_value.j2' as yamlval %}{{ yamlval.render_cac_scalar(value) }}")
    return template.render(value=value).strip()


def _render_extra_vars(extra_vars_contents):
    environment = _build_environment()
    rendered = environment.from_string(EXTRA_VARS_SNIPPET).render(extra_vars_contents=extra_vars_contents)
    return yaml.safe_load(rendered)


class TestExtraVarsNativeExport(unittest.TestCase):
    def test_render_cac_scalar_native_types(self):
        self.assertEqual(_render_cac_scalar(15), "15")
        self.assertEqual(_render_cac_scalar("15"), "15")
        self.assertEqual(_render_cac_scalar(True), "true")
        self.assertEqual(_render_cac_scalar("false"), "false")
        self.assertEqual(_render_cac_scalar(1.5), "1.5")

    def test_render_cac_scalar_preserves_jinja_strings(self):
        rendered = _render_cac_scalar("{{ ansible_user }}")
        self.assertIn("raw", rendered)
        self.assertIn("ansible_user", rendered)

    def test_extra_vars_export_native_types(self):
        document = _render_extra_vars(
            {
                "ansible_ssh_timeout": 15,
                "enable_feature": True,
                "region": "eu-west-1",
                "tags": [1, "prod", True],
                "nested": {"retries": 3, "enabled": False},
            }
        )
        extra_vars = document["extra_vars"]
        self.assertEqual(extra_vars["ansible_ssh_timeout"], 15)
        self.assertIsInstance(extra_vars["ansible_ssh_timeout"], int)
        self.assertIs(extra_vars["enable_feature"], True)
        self.assertEqual(extra_vars["tags"][0], 1)
        self.assertIs(extra_vars["tags"][2], True)
        self.assertEqual(extra_vars["nested"]["retries"], 3)
        self.assertIs(extra_vars["nested"]["enabled"], False)
        self.assertIn("raw", str(extra_vars["region"]))
        self.assertIn("eu-west-1", str(extra_vars["region"]))


if __name__ == "__main__":
    unittest.main()
