"""Ensure filetree_create keeps Jinja placeholders in notification messages literal."""

from pathlib import Path
import re
import unittest

from jinja2 import Environment, FileSystemLoader
import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / "roles" / "filetree_create" / "templates"

MESSAGES = {
    "error": {"body": "{{ job_metadata }}", "message": "{{ job_friendly_name }} failed"},
    "started": None,
    "success": {"body": "line one {{ job.id }}\nline two {{ url }}"},
    "workflow_approval": {
        "denied": {"body": '{"body": "The approval node {{ approval_node_name }} was denied. {{ workflow_url }}"}'},
        "running": {"body": "needs review\n{{ workflow_url }}"},
    },
}


def _build_environment():
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    environment.filters["dict2items"] = lambda value: [{"key": key, "value": item} for key, item in value.items()]
    environment.filters["items2dict"] = lambda value: {item["key"]: item["value"] for item in value}
    environment.filters["bool"] = lambda value: str(value).lower() in ("true", "1", "yes")
    environment.filters["int"] = int
    environment.filters["float"] = float
    environment.filters["regex_replace"] = lambda value, pattern, repl: re.sub(pattern, repl, str(value))
    environment.tests["boolean"] = lambda value: isinstance(value, bool)
    environment.tests["number"] = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)
    environment.tests["match"] = lambda value, pattern: re.match(pattern, str(value)) is not None
    return environment


def _export(asset):
    template = _build_environment().get_template("controller_notification_templates.j2")
    rendered = template.render(
        current_notification_templates_asset_value=asset,
        env_fields_as_variables=False,
        secrets_as_variables=False,
    )
    return yaml.safe_load(rendered)["controller_notifications"][0]


def _read_back(value):
    """Template a string the way include_vars data is templated when it is used."""
    return Environment().from_string(value).render()


class TestNotificationMessagesRaw(unittest.TestCase):
    def setUp(self):
        self.exported = _export(
            {
                "name": "Webhook Notifier",
                "description": "Posts job: results",
                "summary_fields": {"organization": {"name": "Test Org"}},
                "notification_type": "webhook",
                "notification_configuration": {"url": "https://www.example.com/hook", "http_method": "POST"},
                "messages": MESSAGES,
            }
        )

    def test_messages_round_trip(self):
        messages = self.exported["messages"]
        for key in ("error", "success"):
            for field, value in MESSAGES[key].items():
                self.assertEqual(_read_back(messages[key][field]), value)
        for key in ("denied", "running"):
            self.assertEqual(_read_back(messages["workflow_approval"][key]["body"]), MESSAGES["workflow_approval"][key]["body"])

    def test_description_exported(self):
        self.assertEqual(_read_back(self.exported["description"]), "Posts job: results")


if __name__ == "__main__":
    unittest.main()
