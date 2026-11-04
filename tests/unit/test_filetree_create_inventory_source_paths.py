"""Check the filetree_create path selected for flattened inventory sources."""

from pathlib import Path
import unittest

from jinja2 import Environment
import yaml

ROOT = Path(__file__).resolve().parents[2]


class TestFlattenedInventorySourcePath(unittest.TestCase):
    def test_regular_and_constructed_inventories_use_controller_filename(self):
        environment = Environment()
        environment.filters["bool"] = bool

        for task_file in (
            "controller_inventories.yml",
            "controller_constructed_inventories.yml",
        ):
            with self.subTest(task_file=task_file):
                task_path = ROOT / "roles" / "filetree_create" / "tasks" / task_file
                tasks = yaml.safe_load(task_path.read_text(encoding="utf-8"))
                source_task = next(task for task in tasks if task.get("ansible.builtin.include_tasks") == "controller_inventory_sources.yml")
                expression = source_task["vars"]["inventory_sources_output_path"]
                output = environment.from_string(expression).render(output_path="/tmp/filetree_output", flatten_output=True)
                self.assertEqual(output, "/tmp/filetree_output/controller_inventory_sources.yaml")


if __name__ == "__main__":
    unittest.main()
