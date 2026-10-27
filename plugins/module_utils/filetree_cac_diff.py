# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import os

try:
    from ansible.module_utils.common.yaml import HAS_YAML as _ANSIBLE_HAS_YAML
    from ansible.module_utils.common.yaml import yaml_dump as _ansible_yaml_dump
    from ansible.module_utils.common.yaml import yaml_load_all as _ansible_yaml_load_all
except ImportError:
    _ANSIBLE_HAS_YAML = False
    _ansible_yaml_dump = None
    _ansible_yaml_load_all = None

try:
    import yaml as _yaml

    HAS_YAML = True
    yaml_load_all = _ansible_yaml_load_all or _yaml.safe_load_all
    yaml_dump = _ansible_yaml_dump or _yaml.safe_dump
except ImportError:
    HAS_YAML = _ANSIBLE_HAS_YAML
    yaml_dump = _ansible_yaml_dump
    yaml_load_all = _ansible_yaml_load_all

try:
    from yaml import YAMLError
except ImportError:
    YAMLError = Exception

try:
    from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError
except ImportError:
    BaseLoader = None
    Environment = None

# YAML root key -> object type used for identity and comparison.
ROOT_KEY_OBJECT_TYPE = {
    "aap_organizations": "organization",
    "controller_credential_types": "credential_type",
    "controller_instance_groups": "instance_group",
    "controller_instances": "instance",
    "controller_labels": "label",
    "controller_settings": "settings",
    "aap_user_accounts": "user",
    "controller_groups": "group",
    "controller_hosts": "host",
    "controller_schedules": "schedule",
    "controller_execution_environments": "execution_environment",
    "controller_credentials": "credential",
    "controller_credential_input_sources": "credential_input_source",
    "controller_inventory_sources": "inventory_source",
    "controller_workflows": "workflow_job_template",
    "controller_workflow_job_templates": "workflow_job_template",
    "controller_templates": "job_template",
    "controller_job_templates": "job_template",
    "controller_projects": "project",
    "controller_inventories": "inventory",
    "controller_notifications": "notification_template",
    "controller_notification_templates": "notification_template",
    "aap_teams": "team",
    "aap_applications": "application",
    "controller_roles": "role",
    "gateway_organizations": "organization",
    "gateway_authenticators": "authenticator",
    "gateway_authenticator_maps": "authenticator_map",
    "gateway_settings": "settings",
    "gateway_http_ports": "http_port",
    "gateway_service_clusters": "service_cluster",
    "gateway_service_keys": "service_key",
    "gateway_service_nodes": "service_node",
    "gateway_services": "gateway_service",
    "gateway_role_definitions": "role_definition",
    "gateway_role_team_assignments": "role_team_assignment",
    "gateway_role_user_assignments": "role_user_assignment",
    "gateway_routes": "route",
    "eda_credential_types": "eda_credential_type",
    "eda_credentials": "eda_credential",
    "eda_decision_environments": "eda_decision_environment",
    "eda_event_streams": "eda_event_stream",
    "eda_projects": "eda_project",
    "eda_rulebook_activations": "eda_rulebook_activation",
    "hub_namespaces": "hub_namespace",
    "hub_collections": "hub_collection",
    "hub_collection_remotes": "hub_collection_remote",
    "hub_collection_repositories": "hub_collection_repository",
    "hub_ee_registries": "hub_ee_registry",
    "hub_ee_repositories": "hub_ee_repository",
    "hub_ee_images": "hub_ee_image",
}

# Normalize live-export root keys to the CaC root keys used by filetree_read.
ROOT_KEY_CANONICAL = {
    "gateway_organizations": "aap_organizations",
}

# Settings are a single mapping per root key (not a list of objects).
DICT_ROOT_OBJECT_TYPES = frozenset({"settings"})

OBJECT_ID_KEYS = {
    "organization": ["name"],
    "credential_type": ["name"],
    "instance_group": ["name"],
    "instance": ["hostname"],
    "label": ["name", "organization"],
    "settings": [],
    "user": ["username"],
    "group": ["name", "inventory"],
    "host": ["name", "inventory"],
    "schedule": ["name", "unified_job_template"],
    "execution_environment": ["name", "organization", "image"],
    "credential": ["name", "organization", "credential_type"],
    "credential_input_source": [
        "target_credential",
        "source_credential",
        "input_field_name",
    ],
    "inventory_source": ["name", "organization", "inventory"],
    "workflow_job_template_node": [
        "workflow_job_template",
        "unified_job_template",
        "identifier",
    ],
    "role": None,
    "authenticator": ["name"],
    "authenticator_map": ["name", "authenticator"],
    "http_port": ["name"],
    "service_cluster": ["name"],
    "service_key": ["name"],
    "service_node": ["name"],
    "gateway_service": ["name"],
    "role_definition": ["name"],
    "role_team_assignment": [
        "role_definition",
        "team",
        "team_ansible_id",
        "assignment_objects",
    ],
    "role_user_assignment": [
        "role_definition",
        "user",
        "user_ansible_id",
        "object_ids",
    ],
    "route": ["name"],
    "eda_credential_type": ["name"],
    "eda_credential": ["name", "organization"],
    "eda_decision_environment": ["name", "organization"],
    "eda_event_stream": ["name", "organization"],
    "eda_project": ["name", "organization"],
    "eda_rulebook_activation": ["name", "organization_name"],
    "hub_namespace": ["name"],
    "hub_collection": ["namespace", "name"],
    "hub_collection_remote": ["name"],
    "hub_collection_repository": ["name"],
    "hub_ee_registry": ["name"],
    "hub_ee_repository": ["name"],
    "hub_ee_image": ["name"],
}

DEFAULT_ID_KEYS = ["name", "organization"]

# Secrets / non-config noise only. Do not ignore "credential" or "credentials":
# those are name references (inventory sources, instance groups, JTs, …) and must
# produce deltas when they change. Role helper lists such as _ROLE_TARGET_DUP_KEYS
# may still mention "credential" for field expansion; that is unrelated to ignore.
DEFAULT_IGNORE_KEYS = {
    "state",
    "type",
    "password",
    "token",
    "oauth_token",
    "secret",
    "client_secret",
    "ssh_key_data",
    "vault_password",
    "become_password",
    "passphrase",
    "inputs",
    "pull",
}

EMPTY_COMPARE_VALUES = (None, "", [], {}, [{}])

YAML_EXTENSIONS = (".yaml", ".yml")

REPORT_FILENAME = "_filetree_object_diff_report.yaml"

# Root keys filtered when skip_system_roles is enabled.
SYSTEM_ROLE_ASSIGNMENT_ROOT_KEYS = frozenset(
    {
        "gateway_role_user_assignments",
        "gateway_role_team_assignments",
    }
)
GALAXY_ROLE_DEFINITION_PREFIX = "galaxy."

_ROLE_TARGET_DUP_KEYS = [
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

_ROLE_FIELD_EXPANSIONS = [
    ("target_team", "team", False),
    ("target_teams", "team", True),
    ("job_template", "job_template", False),
    ("job_templates", "job_template", True),
    ("workflow", "workflow_job_template", False),
    ("workflows", "workflow_job_template", True),
    ("inventory", "inventory", False),
    ("inventories", "inventory", True),
    ("project", "project", False),
    ("projects", "project", True),
]


def get_id_keys(object_type):
    return OBJECT_ID_KEYS.get(object_type, DEFAULT_ID_KEYS)


def canonical_root_key(root_key):
    return ROOT_KEY_CANONICAL.get(root_key, root_key)


def object_identity(object_type, item):
    if object_type == "role":
        normalized = normalize_role_items([copy.deepcopy(item)])
        if not normalized:
            return None
        item = normalized[0]
        return tuple(sorted((key, _identity_value(item.get(key))) for key in sorted(item.keys())))
    id_keys = get_id_keys(object_type)
    if id_keys is None:
        return None
    # Empty id_keys = singleton mapping (e.g. settings).
    return tuple(_identity_value(item.get(key)) for key in id_keys)


def _identity_value(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _identity_value(value[key])) for key in value))
    if isinstance(value, list):
        return tuple(_identity_value(element) for element in value)
    return value


def filter_compare_item(item, ignore_keys):
    return {key: value for key, value in item.items() if key not in ignore_keys and value not in EMPTY_COMPARE_VALUES}


def normalize_scalar(value):
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def values_equal(cac_value, live_value):
    """Compare a CaC-desired value against live; nested dicts are CaC-subset."""
    if isinstance(cac_value, dict) and isinstance(live_value, dict):
        for key, value in cac_value.items():
            if value in EMPTY_COMPARE_VALUES:
                continue
            if key not in live_value or live_value[key] in EMPTY_COMPARE_VALUES:
                return False
            if not values_equal(value, live_value[key]):
                return False
        return True
    if isinstance(cac_value, list) and isinstance(live_value, list):
        if len(cac_value) != len(live_value):
            return False
        return all(values_equal(left, right) for left, right in zip(cac_value, live_value))
    return normalize_scalar(cac_value) == normalize_scalar(live_value)


def equal_dicts(cac_item, live_item, ignore_keys):
    """Return True when every non-empty CaC field matches live (ignore_keys excluded).

    Comparison is CaC-driven: live-only keys are ignored. A CaC field missing or
    empty on the live side is a mismatch so dispatch can apply the desired state.
    """
    return not field_changes(cac_item, live_item, ignore_keys)


def _append_nested_field_changes(prefix, cac_value, live_value, changes):
    if isinstance(cac_value, dict) and isinstance(live_value, dict):
        for key, value in cac_value.items():
            if value in EMPTY_COMPARE_VALUES:
                continue
            field_path = "{0}.{1}".format(prefix, key) if prefix else key
            if key not in live_value or live_value[key] in EMPTY_COMPARE_VALUES:
                changes.append({"field": field_path, "from": None, "to": copy.deepcopy(value)})
                continue
            if isinstance(value, dict) and isinstance(live_value[key], dict):
                _append_nested_field_changes(field_path, value, live_value[key], changes)
            elif not values_equal(value, live_value[key]):
                changes.append(
                    {
                        "field": field_path,
                        "from": copy.deepcopy(live_value[key]),
                        "to": copy.deepcopy(value),
                    }
                )
        return
    if not values_equal(cac_value, live_value):
        changes.append(
            {
                "field": prefix,
                "from": copy.deepcopy(live_value),
                "to": copy.deepcopy(cac_value),
            }
        )


def field_changes(cac_item, live_item, ignore_keys):
    """Return per-field from/to changes for non-empty CaC fields vs live."""
    changes = []
    cac_filtered = filter_compare_item(cac_item, ignore_keys)
    live_filtered = filter_compare_item(live_item, ignore_keys)
    for key, value in cac_filtered.items():
        if key not in live_filtered:
            changes.append({"field": key, "from": None, "to": copy.deepcopy(value)})
            continue
        live_value = live_filtered[key]
        if isinstance(value, dict) and isinstance(live_value, dict):
            _append_nested_field_changes(key, value, live_value, changes)
        elif not values_equal(value, live_value):
            changes.append(
                {
                    "field": key,
                    "from": copy.deepcopy(live_value),
                    "to": copy.deepcopy(value),
                }
            )
    return changes


def report_identity(object_type, item):
    """Stable identity dict for report entries (id keys or full role item)."""
    if object_type == "role":
        identity = {}
        for key in sorted(item.keys()):
            if key in ("state", "roles"):
                continue
            identity[key] = copy.deepcopy(item.get(key))
        return identity
    id_keys = get_id_keys(object_type) or []
    return {key: copy.deepcopy(item.get(key)) for key in id_keys if key in item}


def is_system_role_item(root_key, item):
    """Return True for managed gateway role definitions or galaxy.* assignments."""
    if root_key == "gateway_role_definitions" and item.get("managed") is True:
        return True
    if root_key in SYSTEM_ROLE_ASSIGNMENT_ROOT_KEYS:
        role_definition = item.get("role_definition") or ""
        if isinstance(role_definition, str) and role_definition.startswith(GALAXY_ROLE_DEFINITION_PREFIX):
            return True
    return False


def filter_system_roles_from_index(index, skip_system_roles=True):
    if not skip_system_roles:
        return index
    return {key: entry for key, entry in index.items() if not is_system_role_item(entry["root_key"], entry["item"])}


def map_item(item, new_attribute_name, attribute_value, dupitems):
    new_item = copy.deepcopy(item)
    for dupitem in [dupitem for dupitem in dupitems if dupitem in new_item]:
        new_item.pop(dupitem)
    new_item.update({new_attribute_name: attribute_value})
    return new_item


def _expand_role_item(item, expansions, dupitems):
    extensions = []
    expanded = False
    for source_key, target_key, is_list in expansions:
        if source_key not in item:
            continue
        expanded = True
        values = item[source_key] if is_list else [item[source_key]]
        for value in values:
            extensions.append(map_item(item, target_key, value, dupitems))
    return expanded, extensions


def _apply_role_expansions(items, expansions, dupitems):
    result = list(items)
    list_to_extend = []
    list_to_remove = []
    for item in result:
        expanded, extensions = _expand_role_item(item, expansions, dupitems)
        if not expanded:
            continue
        list_to_remove.append(item)
        list_to_extend.extend(extensions)
    for item in list_to_remove:
        result.remove(item)
    result.extend(list_to_extend)
    return result


def normalize_role_items(role_list):
    normalized = copy.deepcopy(role_list)
    normalized = _apply_role_expansions(normalized, _ROLE_FIELD_EXPANSIONS, _ROLE_TARGET_DUP_KEYS)
    normalized = _apply_role_expansions(normalized, [("roles", "role", True)], ["roles", "role"])
    return normalized


def role_items_match(left, right, ignore_keys):
    if equal_dicts(left, right, ignore_keys):
        return True
    if "organization" in left and len(left) == 3 and equal_dicts(left, right, list(ignore_keys) + list(right.keys() - left.keys())):
        return True
    return False


def render_template(content, template_vars):
    if not template_vars or Environment is None:
        return content
    environment = Environment(loader=BaseLoader(), keep_trailing_newline=True)
    try:
        return environment.from_string(content).render(**template_vars)
    except (TemplateSyntaxError, UndefinedError):
        return content


def load_yaml_documents(path, template_vars=None):
    if not HAS_YAML:
        raise ImportError("PyYAML is required for filetree_cac_diff")
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    if template_vars:
        content = render_template(content, template_vars)
    documents = []
    for document in yaml_load_all(content):
        if document:
            documents.append(document)
    return documents


def _is_yaml_file(filename):
    return filename.endswith(YAML_EXTENSIONS)


def _track_yaml_file(full_path, seen):
    if full_path in seen:
        return None
    seen.add(full_path)
    return full_path


def _iter_yaml_files_in_directory(path, seen):
    for root, _dirs, files in os.walk(path):
        for filename in files:
            if not _is_yaml_file(filename):
                continue
            tracked = _track_yaml_file(os.path.join(root, filename), seen)
            if tracked:
                yield tracked


def iter_yaml_files(paths):
    seen = set()
    for path in paths:
        if not path or not os.path.isdir(path):
            continue
        for tracked in _iter_yaml_files_in_directory(path, seen):
            yield tracked


def _value_to_object_entries(root_key, object_type, value):
    if isinstance(value, list):
        return [(root_key, object_type, item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [(root_key, object_type, value)]
    return []


def extract_root_objects(documents):
    entries = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        for root_key, value in document.items():
            if root_key not in ROOT_KEY_OBJECT_TYPE:
                continue
            object_type = ROOT_KEY_OBJECT_TYPE[root_key]
            entries.extend(_value_to_object_entries(root_key, object_type, value))
    return entries


def index_filetree(paths, template_vars=None):
    index = {}
    for path in iter_yaml_files(paths):
        try:
            documents = load_yaml_documents(path, template_vars=template_vars)
        except (YAMLError, OSError):
            continue
        for root_key, object_type, item in extract_root_objects(documents):
            identity = object_identity(object_type, item)
            if identity is None:
                continue
            canonical_key = canonical_root_key(root_key)
            index[(canonical_key, identity)] = {
                "root_key": canonical_key,
                "object_type": object_type,
                "item": copy.deepcopy(item),
                "source_path": path,
            }
    return index


def sanitize_filename(value):
    if value is None:
        return "none"
    return str(value).replace("/", "_").replace(" ", "_")


def diff_filename(root_key, object_type, item, state):
    id_keys = get_id_keys(object_type)
    if object_type == "role":
        parts = []
        for key in sorted(item.keys()):
            if key in ("state", "roles", "role"):
                continue
            parts.append(sanitize_filename(item.get(key)))
        suffix = "_".join(parts) or "role"
    elif not id_keys:
        suffix = "singleton"
    else:
        suffix = "_".join(sanitize_filename(item.get(key)) for key in id_keys)
    return "{0}_{1}_{2}.yaml".format(root_key, suffix, state)


def minimal_absent_item(object_type, item):
    absent_item = {"state": "absent"}
    if object_type == "role":
        for key, value in item.items():
            if key in DEFAULT_IGNORE_KEYS or key == "inputs":
                continue
            absent_item[key] = copy.deepcopy(value)
        if absent_item.get("role") == "member" and "team" in absent_item:
            absent_item["target_team"] = absent_item["team"]
        return absent_item
    id_keys = get_id_keys(object_type) or []
    for key in id_keys:
        if key in item:
            absent_item[key] = copy.deepcopy(item[key])
    return absent_item


def write_diff_file(diff_path, root_key, item):
    os.makedirs(diff_path, exist_ok=True)
    object_type = ROOT_KEY_OBJECT_TYPE[root_key]
    state = item.get("state", "present")
    # Settings are a mapping applied as a whole; absent is not meaningful.
    if object_type in DICT_ROOT_OBJECT_TYPES:
        if state == "absent":
            return None
        payload_item = copy.deepcopy(item)
        payload_item.pop("state", None)
        payload = {root_key: payload_item}
    else:
        payload = {root_key: [item]}
    filename = diff_filename(root_key, object_type, item, state)
    destination = os.path.join(diff_path, filename)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write("---\n")
        yaml_dump(
            payload,
            handle,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        handle.write("...\n")
    return destination


def item_organization_name(item):
    for key in ("organization", "organization_name"):
        organization = item.get(key)
        if isinstance(organization, str) and organization:
            return organization
    return None


def matches_organization_filter(item, organization_filter):
    if not organization_filter:
        return True
    item_org = item_organization_name(item)
    if item_org is not None:
        return item_org == organization_filter
    if item.get("inventory") is not None:
        return True
    # Schedules reference an org-scoped job template by name and omit organization.
    if item.get("unified_job_template") is not None:
        return True
    return False


def _cac_scope_names(cac_index, organization_filter):
    """Names from CaC used to scope live-only Gateway RBAC assignment absents."""
    names = set()
    if organization_filter:
        names.add(organization_filter)
    for entry in cac_index.values():
        item = entry["item"]
        for key in ("name", "username"):
            value = item.get(key)
            if isinstance(value, str) and value:
                names.add(value)
        for object_id in item.get("object_ids") or []:
            if isinstance(object_id, str) and object_id:
                names.add(object_id)
    return names


def _assignment_in_cac_scope(item, cac_scope_names):
    object_ids = item.get("object_ids") or []
    return any(object_id in cac_scope_names for object_id in object_ids)


def filter_index_by_organization(index, organization_filter):
    if not organization_filter:
        return index
    filtered = {}
    for key, entry in index.items():
        if matches_organization_filter(entry["item"], organization_filter):
            filtered[key] = entry
            continue
        # Gateway RBAC assignments are scoped by object_ids, not organization.
        if entry["object_type"] in ("role_user_assignment", "role_team_assignment"):
            if entry["item"].get("object_ids"):
                filtered[key] = entry
    return filtered


def filter_live_index_scope(live_index, cac_index, organization_filter):
    if not organization_filter:
        return live_index
    cac_keys = set(cac_index.keys())
    cac_scope_names = _cac_scope_names(cac_index, organization_filter)
    scoped = {}
    for key, entry in live_index.items():
        if key in cac_keys or matches_organization_filter(entry["item"], organization_filter):
            scoped[key] = entry
            continue
        # Live-only Gateway assignments omit organization; keep those targeting CaC names.
        if entry["object_type"] in ("role_user_assignment", "role_team_assignment"):
            if _assignment_in_cac_scope(entry["item"], cac_scope_names):
                scoped[key] = entry
    return scoped


def _prepare_diff_directory(diff_path):
    if os.path.exists(diff_path):
        for root, _dirs, files in os.walk(diff_path):
            for filename in files:
                if filename.endswith(YAML_EXTENSIONS):
                    os.remove(os.path.join(root, filename))
    else:
        os.makedirs(diff_path, exist_ok=True)


def _resolve_compare_options(ignore_keys, root_keys_filter, template_vars, organization_filter):
    return (
        set(ignore_keys or []) | DEFAULT_IGNORE_KEYS,
        set(root_keys_filter or ROOT_KEY_OBJECT_TYPE.keys()),
        organization_filter or (template_vars or {}).get("orgs"),
    )


def _items_match(cac_item, live_item, object_type, ignore_keys):
    if object_type == "role":
        return role_items_match(
            normalize_role_items([cac_item])[0],
            normalize_role_items([live_item])[0],
            ignore_keys,
        )
    return equal_dicts(cac_item, live_item, ignore_keys)


def _empty_report():
    return {
        "summary": {"create": 0, "update": 0, "delete": 0, "unchanged": 0},
        "objects": [],
    }


def _append_report_object(report, root_key, object_type, item, action, changes=None):
    entry = {
        "root_key": root_key,
        "object_type": object_type,
        "identity": report_identity(object_type, item),
        "action": action,
    }
    if changes:
        entry["changes"] = changes
    report["objects"].append(entry)
    report["summary"][action] = report["summary"].get(action, 0) + 1


def write_report_file(diff_path, report):
    os.makedirs(diff_path, exist_ok=True)
    destination = os.path.join(diff_path, REPORT_FILENAME)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write("---\n")
        yaml_dump(
            report,
            handle,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        handle.write("...\n")
    return destination


def _process_cac_entry(key, cac_entry, live_index, diff_path, root_keys_filter, ignore_keys, report):
    root_key, _identity = key
    if root_key not in root_keys_filter:
        return 0, 0, []

    live_entry = live_index.get(key)
    cac_item = cac_entry["item"]
    object_type = cac_entry["object_type"]

    if live_entry is None:
        output_item = copy.deepcopy(cac_item)
        output_item["state"] = "present"
        written = write_diff_file(diff_path, root_key, output_item)
        if written:
            _append_report_object(report, root_key, object_type, cac_item, "create")
            return 1, 0, [written]
        return 0, 0, []

    if _items_match(cac_item, live_entry["item"], object_type, ignore_keys):
        _append_report_object(report, root_key, object_type, cac_item, "unchanged")
        return 0, 1, []

    if object_type == "role":
        cac_compare = normalize_role_items([copy.deepcopy(cac_item)])[0]
        live_compare = normalize_role_items([copy.deepcopy(live_entry["item"])])[0]
    else:
        cac_compare = cac_item
        live_compare = live_entry["item"]
    changes = field_changes(cac_compare, live_compare, ignore_keys)

    output_item = copy.deepcopy(cac_item)
    output_item["state"] = "present"
    written = write_diff_file(diff_path, root_key, output_item)
    if written:
        _append_report_object(report, root_key, object_type, cac_item, "update", changes)
        return 1, 0, [written]
    return 0, 0, []


def _process_absent_entries(live_index, cac_index, diff_path, root_keys_filter, report):
    absent_files = []
    absent_count = 0
    for key, live_entry in live_index.items():
        root_key, _identity = key
        if root_key not in root_keys_filter or key in cac_index:
            continue
        if live_entry["object_type"] in DICT_ROOT_OBJECT_TYPES:
            continue
        output_item = minimal_absent_item(live_entry["object_type"], live_entry["item"])
        written = write_diff_file(diff_path, root_key, output_item)
        if written:
            absent_files.append(written)
            absent_count += 1
            _append_report_object(
                report,
                root_key,
                live_entry["object_type"],
                live_entry["item"],
                "delete",
            )
    return absent_count, absent_files


def compare_filetrees(
    live_paths,
    cac_paths,
    diff_path,
    ignore_keys=None,
    template_vars=None,
    set_absent=True,
    root_keys_filter=None,
    organization_filter=None,
    write_report=True,
    skip_system_roles=True,
):
    ignore_keys, root_keys_filter, organization_filter = _resolve_compare_options(
        ignore_keys,
        root_keys_filter,
        template_vars,
        organization_filter,
    )

    cac_index = filter_system_roles_from_index(
        filter_index_by_organization(
            index_filetree(cac_paths, template_vars=template_vars),
            organization_filter,
        ),
        skip_system_roles=skip_system_roles,
    )
    _prepare_diff_directory(diff_path)

    live_index = filter_system_roles_from_index(
        filter_live_index_scope(
            filter_index_by_organization(
                index_filetree(live_paths, template_vars=None),
                organization_filter,
            ),
            cac_index,
            organization_filter,
        ),
        skip_system_roles=skip_system_roles,
    )

    report = _empty_report()
    present_count = 0
    unchanged_count = 0
    diff_files = []

    for key, cac_entry in cac_index.items():
        present_delta, unchanged_delta, files = _process_cac_entry(
            key,
            cac_entry,
            live_index,
            diff_path,
            root_keys_filter,
            ignore_keys,
            report,
        )
        present_count += present_delta
        unchanged_count += unchanged_delta
        diff_files.extend(files)

    absent_count = 0
    if set_absent:
        absent_count, absent_files = _process_absent_entries(
            live_index,
            cac_index,
            diff_path,
            root_keys_filter,
            report,
        )
        diff_files.extend(absent_files)

    report["summary"]["unchanged"] = unchanged_count
    report_path = None
    if write_report:
        report_path = write_report_file(diff_path, report)

    return {
        "diff_files": diff_files,
        "present_count": present_count,
        "absent_count": absent_count,
        "unchanged_count": unchanged_count,
        "changed": bool(diff_files),
        "report": report,
        "report_path": report_path,
    }
