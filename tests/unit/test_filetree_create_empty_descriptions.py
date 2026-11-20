"""Check that filetree_create leaves out descriptions that are not set."""

from pathlib import Path
import unittest

from jinja2 import ChainableUndefined, Environment, FileSystemLoader
import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / "roles" / "filetree_create" / "templates"


class TestEmptyDescriptionExport(unittest.TestCase):
    def test_empty_description_is_not_exported(self):
        environment = Environment(loader=FileSystemLoader(TEMPLATES), undefined=ChainableUndefined, trim_blocks=True)
        environment.filters["bool"] = bool
        environment.filters["to_nice_yaml"] = yaml.safe_dump
        overrides = {"template_overrides_resources": {}, "template_overrides_global": {}}

        for template, variables, key in (
            (
                "controller_credential_input_sources.j2",
                {
                    "current_credential": {"name": "target"},
                    "credential_input_sources_lookvar": [
                        {
                            "summary_fields": {"source_credential": {"name": "source"}},
                            "input_field_name": "password",
                            "description": "",
                            "metadata": {"secret_path": "x"},
                        }
                    ],
                },
                "controller_credential_input_sources",
            ),
            ("eda_credentials.j2", {"current_eda_credentials_asset_value": [{"name": "eda", "description": ""}]}, "eda_credentials"),
            (
                "controller_teams.j2",
                {"current_teams_asset_value": {"name": "team", "description": "", "summary_fields": {"organization": {"name": "Default"}}}},
                "aap_teams",
            ),
        ):
            with self.subTest(template=template):
                rendered = yaml.safe_load(environment.get_template(template).render(**overrides, **variables))
                self.assertNotIn("description", rendered[key][0])


if __name__ == "__main__":
    unittest.main()
