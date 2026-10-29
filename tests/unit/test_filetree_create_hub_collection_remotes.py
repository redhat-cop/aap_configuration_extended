"""Check that Hub collection remote exports remain valid CaC YAML."""

from pathlib import Path
import re
import unittest

from jinja2 import Environment, FileSystemLoader
import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / "roles" / "filetree_create" / "templates"


def _render_remotes(remotes):
    environment = Environment(loader=FileSystemLoader(TEMPLATES))
    environment.filters["dict2items"] = lambda value: [{"key": key, "value": item} for key, item in value.items()]
    environment.filters["from_yaml"] = yaml.safe_load
    environment.filters["to_nice_yaml"] = lambda value, indent=2, sort_keys=False: yaml.safe_dump(value, indent=indent, sort_keys=sort_keys)
    environment.filters["bool"] = bool
    environment.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
    template = environment.get_template("hub_collection_remotes.j2")
    return yaml.safe_load(template.render(current_hub_collection_remotes_asset_value=remotes))


class TestHubCollectionRemoteExport(unittest.TestCase):
    def test_requirements_file_collections_become_remote_requirements(self):
        rendered = _render_remotes(
            [
                {
                    "name": "community",
                    "url": "https://galaxy.ansible.com/api/",
                    "requirements_file": "collections:\n  - community.general\n",
                    "sync_dependencies": True,
                }
            ]
        )
        remote = rendered["hub_collection_remotes"][0]
        self.assertEqual(remote["name"], "community")
        self.assertEqual(remote["requirements"], ["community.general"])
        self.assertTrue(remote["sync_dependencies"])
        self.assertNotIn("requirements_file", remote)
        self.assertNotIn("collections", remote)


if __name__ == "__main__":
    unittest.main()
