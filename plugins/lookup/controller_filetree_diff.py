# (c) 2026 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
name: controller_filetree_diff
author: "Ivan Aragonés (@ivarmu)"
short_description: Return CaC delta between live filetree export and repository CaC
requirements:
  - None
description:
  - >-
    Compares two CaC-format object lists. C(live_list) comes from a C(filetree_create) export;
    C(cac_list) comes from repository CaC via C(filetree_read).
  - >-
    Returns only objects that differ. C(state=present) for CaC-only or modified objects;
    C(state=absent) for live-only objects. Matching objects are omitted.
  - >-
    Supports ignoring sensitive keys so CaC variables used for secrets do not cause false positives.
options:
  live_list:
    description:
      - Objects loaded from a C(filetree_create) export via C(filetree_read).
    type: list
    elements: dict
    required: true
  cac_list:
    description:
      - Objects loaded from the repository CaC via C(filetree_read).
    type: list
    elements: dict
    required: true
  object_type:
    description:
      - Object type used to select identity and comparison keys (for example C(inventory), C(project), C(role)).
    type: str
    required: true
  ignore_keys:
    description:
      - Top-level keys omitted when comparing object content. Useful for credentials and other secret fields.
    type: list
    elements: str
    default:
      - state
      - type
      - password
      - token
      - oauth_token
      - secret
      - client_secret
      - ssh_key_data
      - vault_password
      - become_password
      - passphrase
      - inputs
  with_present:
    description:
      - C(false) — return only the delta.
      - C(true) — return the full C(cac_list) as C(state=present) plus live-only objects as C(state=absent).
    type: bool
    default: false
  set_absent:
    description:
      - When C(true), mark live-only objects with C(state=absent).
    type: bool
    default: true
  warn_on_empty_live:
    description:
      - When the live list is empty, warn and treat all CaC objects as C(state=present).
    type: bool
    default: true
"""

EXAMPLES = """
- name: Find inventory delta between live export and repository CaC
  ansible.builtin.set_fact:
    inventory_difference: "{{ query('infra.aap_configuration_extended.controller_filetree_diff',
      live_list=__live_controller_inventories,
      cac_list=controller_inventories,
      object_type='inventory',
      with_present=false,
      set_absent=true) | flatten
    }}"
...
"""

RETURN = """
_raw:
  description:
    - List of objects to synchronize.
  type: list
  returned: on successful differential
"""

import copy

from ansible.errors import AnsibleError, AnsibleLookupError
from ansible.module_utils.common.text.converters import to_native
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

# Identity keys per object type (both sides use CaC/filetree format).
OBJECT_ID_KEYS = {
    "organization": ["name"],
    "credential_type": ["name"],
    "instance_group": ["name"],
    "user": ["username"],
    "group": ["name", "inventory"],
    "host": ["name", "inventory"],
    "schedule": ["name", "unified_job_template"],
    "execution_environment": ["name", "organization", "image"],
    "credential": ["name", "organization", "credential_type"],
    "credential_input_source": ["target_credential", "source_credential", "input_field_name"],
    "inventory_source": ["name", "organization", "inventory"],
    "workflow_job_template_node": [
        "workflow_job_template",
        "unified_job_template",
        "identifier",
    ],
    "role": None,
}

DEFAULT_ID_KEYS = ["name", "organization"]


class LookupModule(LookupBase):
    display = Display()

    def handle_error(self, **kwargs):
        raise AnsibleError(to_native(kwargs.get("msg")))

    def warn_callback(self, warning):
        self.display.warning(warning)

    def map_item(self, item, new_attribute_name, attribute_value, dupitems):
        new_item = copy.deepcopy(item)
        for dupitem in [dupitem for dupitem in dupitems if dupitem in new_item]:
            new_item.pop(dupitem)
        new_item.update({new_attribute_name: attribute_value})
        return new_item

    def equal_dicts(self, d1, d2, ignore_keys):
        d1_filtered = {k: v for k, v in d1.items() if k not in ignore_keys}
        d2_filtered = {k: v for k, v in d2.items() if k not in ignore_keys}
        return d1_filtered == d2_filtered

    def get_id_keys(self, object_type):
        return OBJECT_ID_KEYS.get(object_type, DEFAULT_ID_KEYS)

    def object_key(self, item, id_keys):
        return tuple(item.get(key) for key in id_keys)

    def validate_id_keys(self, items, id_keys, list_name):
        for item in items:
            for key in id_keys:
                if key not in item:
                    self.handle_error(msg="Key: '{0}' missing from item in {1}: {2}".format(key, list_name, item))

    def normalize_role_list(self, role_list):
        normalized = copy.deepcopy(role_list)
        list_to_extend = []
        list_to_remove = []
        dupitems = [
            "target_team",
            "target_teams",
            "job_template",
            "job_templates",
            "workflow",
            "workflows",
            "inventory",
            "inventories",
            "project",
            "projects",
            "credential",
            "credentials",
        ]
        for item in normalized:
            expanded = False
            if "target_team" in item:
                list_to_extend.append(self.map_item(item, "team", item["target_team"], dupitems))
                expanded = True
            if "target_teams" in item:
                for team in item["target_teams"]:
                    list_to_extend.append(self.map_item(item, "team", team, dupitems))
                expanded = True
            if "job_template" in item:
                list_to_extend.append(self.map_item(item, "job_template", item["job_template"], dupitems))
                expanded = True
            if "job_templates" in item:
                for job_template in item["job_templates"]:
                    list_to_extend.append(self.map_item(item, "job_template", job_template, dupitems))
                expanded = True
            if "workflow" in item:
                list_to_extend.append(self.map_item(item, "workflow_job_template", item["workflow"], dupitems))
                expanded = True
            if "workflows" in item:
                for workflow in item["workflows"]:
                    list_to_extend.append(self.map_item(item, "workflow_job_template", workflow, dupitems))
                expanded = True
            if "inventory" in item:
                list_to_extend.append(self.map_item(item, "inventory", item["inventory"], dupitems))
                expanded = True
            if "inventories" in item:
                for inventory in item["inventories"]:
                    list_to_extend.append(self.map_item(item, "inventory", inventory, dupitems))
                expanded = True
            if "project" in item:
                list_to_extend.append(self.map_item(item, "project", item["project"], dupitems))
                expanded = True
            if "projects" in item:
                for project in item["projects"]:
                    list_to_extend.append(self.map_item(item, "project", project, dupitems))
                expanded = True
            if expanded:
                list_to_remove.append(item)
        for item in list_to_remove:
            normalized.remove(item)
        normalized.extend(list_to_extend)

        list_to_extend = []
        list_to_remove = []
        for item in normalized:
            expanded = False
            role_dupitems = ["roles", "role"]
            if "roles" in item:
                for role in item["roles"]:
                    list_to_extend.append(self.map_item(item, "role", role, role_dupitems))
                expanded = True
            if expanded:
                list_to_remove.append(item)
        for item in list_to_remove:
            normalized.remove(item)
        normalized.extend(list_to_extend)
        return normalized

    def role_items_match(self, cac_item, live_item, ignore_keys):
        if self.equal_dicts(cac_item, live_item, ignore_keys):
            return True
        if (
            "organization" in cac_item
            and len(cac_item) == 3
            and self.equal_dicts(
                cac_item,
                live_item,
                list(ignore_keys) + list(live_item.keys() - cac_item.keys()),
            )
        ):
            return True
        return False

    def build_index(self, items, id_keys):
        index = {}
        for item in items:
            key = self.object_key(item, id_keys)
            index[key] = item
        return index

    def run(self, terms, variables=None, **kwargs):
        self.set_options(direct=kwargs)

        live_list = self.get_option("live_list") or []
        cac_list = self.get_option("cac_list") or []
        object_type = self.get_option("object_type")
        ignore_keys = set(self.get_option("ignore_keys") or [])
        warn_on_empty_live = self.get_option("warn_on_empty_live")

        if not live_list:
            if warn_on_empty_live:
                if not cac_list:
                    self._display.warning("Skipping, did not find items in neither live_list nor cac_list")
                    return [[]]
                present_only = copy.deepcopy(cac_list)
                for item in present_only:
                    item.update({"state": "present"})
                return [present_only]
            raise AnsibleLookupError("Unable to find items in live_list")

        if object_type == "role":
            return [self._diff_roles(live_list, cac_list, ignore_keys)]

        id_keys = self.get_id_keys(object_type)
        self.validate_id_keys(live_list, id_keys, "live_list")
        self.validate_id_keys(cac_list, id_keys, "cac_list")

        live_index = self.build_index(live_list, id_keys)
        cac_index = self.build_index(cac_list, id_keys)

        present_items = []
        absent_items = []

        for key, cac_item in cac_index.items():
            live_item = live_index.get(key)
            if live_item is None:
                cac_copy = copy.deepcopy(cac_item)
                cac_copy.update({"state": "present"})
                present_items.append(cac_copy)
            elif not self.equal_dicts(cac_item, live_item, ignore_keys):
                cac_copy = copy.deepcopy(cac_item)
                cac_copy.update({"state": "present"})
                present_items.append(cac_copy)

        if self.get_option("set_absent"):
            for key, live_item in live_index.items():
                if key not in cac_index:
                    live_copy = copy.deepcopy(live_item)
                    live_copy.update({"state": "absent"})
                    absent_items.append(live_copy)

        if self.get_option("with_present"):
            output = []
            for item in cac_list:
                item_copy = copy.deepcopy(item)
                item_copy.update({"state": "present"})
                output.append(item_copy)
            output.extend(absent_items)
            return [output]

        return [present_items + absent_items]

    def _diff_roles(self, live_list, cac_list, ignore_keys):
        live_normalized = self.normalize_role_list(live_list)
        cac_normalized = self.normalize_role_list(cac_list)

        present_items = []
        absent_items = []

        for cac_item in cac_normalized:
            matched = False
            for live_item in live_normalized:
                if self.role_items_match(cac_item, live_item, ignore_keys):
                    matched = True
                    break
            if not matched:
                cac_copy = copy.deepcopy(cac_item)
                cac_copy.update({"state": "present"})
                if "team" in cac_copy and cac_copy.get("role") == "member":
                    cac_copy.update({"target_team": cac_copy["team"]})
                present_items.append(cac_copy)

        if self.get_option("set_absent"):
            for live_item in live_normalized:
                matched = False
                for cac_item in cac_normalized:
                    if self.role_items_match(cac_item, live_item, ignore_keys):
                        matched = True
                        break
                if not matched:
                    live_copy = copy.deepcopy(live_item)
                    live_copy.update({"state": "absent"})
                    if "team" in live_copy and live_copy.get("role") == "member":
                        live_copy.update({"target_team": live_copy["team"]})
                    absent_items.append(live_copy)

        if self.get_option("with_present"):
            output = []
            for item in cac_list:
                item_copy = copy.deepcopy(item)
                item_copy.update({"state": "present"})
                output.append(item_copy)
            output.extend(absent_items)
            return output

        difference = present_items + absent_items
        difference_to_remove = []
        for item in difference:
            if "no_resource_type" in item or len(item) <= 3:
                difference_to_remove.append(item)
        for item in difference_to_remove:
            difference.remove(item)
        return difference
