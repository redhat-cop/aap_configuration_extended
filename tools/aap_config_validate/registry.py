"""Dispatch registry: canonical var-to-role mapping and legacy aliases."""

from __future__ import annotations

from typing import Dict, List, Set

from aap_config_validate.models import DispatchEntry

# Built from roles/dispatch/defaults/main.yml — the single source of truth
# for which variable names trigger which roles.

GATEWAY_DISPATCH: List[DispatchEntry] = [
    DispatchEntry(
        role="gateway_authenticators",
        var="gateway_authenticators",
        tags=["authenticators", "gateway_authenticators"],
    ),
    DispatchEntry(
        role="gateway_authenticator_maps",
        var="gateway_authenticator_maps",
        tags=["authenticator_maps", "gateway_authenticator_maps"],
    ),
    DispatchEntry(
        role="gateway_settings",
        var="gateway_settings",
        tags=["settings", "gateway_settings"],
    ),
    DispatchEntry(
        role="gateway_organizations",
        var="aap_organizations",
        tags=["organizations", "gateway_organizations"],
    ),
    DispatchEntry(
        role="gateway_applications",
        var="aap_applications",
        tags=["applications", "gateway_applications"],
    ),
    DispatchEntry(
        role="gateway_http_ports",
        var="gateway_http_ports",
        tags=["http_ports", "gateway_http_ports"],
    ),
    DispatchEntry(
        role="gateway_service_clusters",
        var="gateway_service_clusters",
        tags=["service_clusters", "gateway_service_clusters"],
    ),
    DispatchEntry(
        role="gateway_service_keys",
        var="gateway_service_keys",
        tags=["service_keys", "gateway_service_keys"],
    ),
    DispatchEntry(
        role="gateway_service_nodes",
        var="gateway_service_nodes",
        tags=["service_nodes", "gateway_service_nodes"],
    ),
    DispatchEntry(
        role="gateway_services",
        var="gateway_services",
        tags=["services", "gateway_services"],
    ),
    DispatchEntry(role="gateway_teams", var="aap_teams", tags=["teams", "gateway_teams"]),
    DispatchEntry(role="gateway_users", var="aap_user_accounts", tags=["users", "gateway_users"]),
    DispatchEntry(
        role="gateway_role_definitions",
        var="gateway_role_definitions",
        tags=["role_definitions", "gateway_role_definitions"],
    ),
    DispatchEntry(
        role="gateway_role_team_assignments",
        var="gateway_role_team_assignments",
        tags=["role_team_assignments", "gateway_role_team_assignments"],
    ),
    DispatchEntry(
        role="gateway_role_user_assignments",
        var="gateway_role_user_assignments",
        tags=["role_user_assignments", "gateway_role_user_assignments"],
    ),
    DispatchEntry(role="gateway_routes", var="gateway_routes", tags=["routes", "gateway_routes"]),
]

HUB_DISPATCH: List[DispatchEntry] = [
    DispatchEntry(
        role="hub_namespace",
        var="hub_namespaces",
        tags=["namespaces", "hub_namespaces"],
    ),
    DispatchEntry(
        role="hub_collection",
        var="hub_collections",
        tags=["collections", "hub_collections"],
    ),
    DispatchEntry(
        role="hub_ee_registry",
        var="hub_ee_registries",
        tags=["registries", "hub_ee_registries"],
    ),
    DispatchEntry(
        role="hub_ee_repository",
        var="hub_ee_repositories",
        tags=["repos", "hub_ee_repositories"],
    ),
    DispatchEntry(
        role="hub_ee_repository_sync",
        var="hub_ee_repository_sync",
        tags=["reposync", "hub_ee_repository_sync"],
    ),
    DispatchEntry(role="hub_ee_image", var="hub_ee_images", tags=["images", "hub_ee_images"]),
    DispatchEntry(
        role="hub_ee_registry_index",
        var="hub_ee_registries",
        tags=["ee_indices", "hub_ee_registry_index"],
    ),
    DispatchEntry(
        role="hub_ee_registry_sync",
        var="hub_ee_registries",
        tags=["regsync", "hub_ee_registry_sync"],
    ),
    DispatchEntry(
        role="hub_collection_remote",
        var="hub_collection_remotes",
        tags=["collectionremote", "hub_collection_remotes"],
    ),
    DispatchEntry(
        role="hub_collection_repository",
        var="hub_collection_repositories",
        tags=["collectionsrep", "hub_collection_repositories"],
    ),
    DispatchEntry(
        role="hub_collection_repository_sync",
        var="hub_collection_repositories",
        tags=["collectionsrepsync", "hub_collection_repository_sync"],
    ),
]

CONTROLLER_DISPATCH: List[DispatchEntry] = [
    DispatchEntry(
        role="controller_settings",
        var="controller_settings",
        tags=["settings", "controller_settings"],
    ),
    DispatchEntry(
        role="controller_instances",
        var="controller_instances",
        tags=["instances", "controller_instances"],
    ),
    DispatchEntry(
        role="controller_labels",
        var="controller_labels",
        tags=["labels", "controller_labels"],
    ),
    DispatchEntry(
        role="controller_credential_types",
        var="controller_credential_types",
        tags=["credential_types", "controller_credential_types"],
    ),
    DispatchEntry(
        role="controller_credentials",
        var="controller_credentials",
        tags=["credentials", "controller_credentials"],
    ),
    DispatchEntry(
        role="controller_credential_input_sources",
        var="controller_credential_input_sources",
        tags=["credential_input_sources", "controller_credential_input_sources"],
    ),
    DispatchEntry(
        role="controller_instance_groups",
        var="controller_instance_groups",
        tags=["instance_groups", "controller_instance_groups"],
    ),
    DispatchEntry(
        role="controller_execution_environments",
        var="controller_execution_environments",
        tags=["execution_environments", "controller_execution_environments"],
    ),
    DispatchEntry(
        role="controller_applications",
        var="aap_applications",
        tags=["applications", "controller_applications"],
    ),
    DispatchEntry(
        role="controller_notification_templates",
        var="controller_notifications",
        tags=["notification_templates", "controller_notification_templates"],
    ),
    DispatchEntry(
        role="gateway_organizations",
        var="aap_organizations",
        tags=["organizations", "controller_organizations", "gateway_organizations"],
    ),
    DispatchEntry(
        role="controller_projects",
        var="controller_projects",
        tags=["inventories", "projects", "controller_projects"],
    ),
    DispatchEntry(
        role="controller_inventories",
        var="controller_inventories",
        tags=["inventories", "controller_inventories"],
    ),
    DispatchEntry(
        role="controller_inventory_sources",
        var="controller_inventory_sources",
        tags=["inventories", "inventory_sources", "controller_inventory_sources"],
    ),
    DispatchEntry(
        role="controller_inventory_source_update",
        var="controller_inventory_sources",
        tags=["inventories", "inventory_sources", "controller_inventory_sources"],
    ),
    DispatchEntry(
        role="controller_hosts",
        var="controller_hosts",
        tags=["inventories", "hosts", "controller_hosts"],
    ),
    DispatchEntry(
        role="controller_bulk_host_create",
        var="controller_bulk_hosts",
        tags=["inventories", "bulk_hosts", "controller_bulk_hosts"],
    ),
    DispatchEntry(
        role="controller_host_groups",
        var="controller_groups",
        tags=["inventories", "host_groups", "controller_groups"],
    ),
    DispatchEntry(
        role="controller_job_templates",
        var="controller_templates",
        tags=["job_templates", "controller_job_templates"],
    ),
    DispatchEntry(
        role="controller_workflow_job_templates",
        var="controller_workflows",
        tags=["workflow_job_templates", "controller_workflow_job_templates"],
    ),
    DispatchEntry(
        role="controller_schedules",
        var="controller_schedules",
        tags=["schedules", "controller_schedules"],
    ),
    DispatchEntry(
        role="controller_roles",
        var="controller_roles",
        tags=["roles", "controller_roles"],
    ),
    DispatchEntry(
        role="controller_job_launch",
        var="controller_launch_jobs",
        tags=["job_launch", "controller_job_launch"],
    ),
    DispatchEntry(
        role="controller_workflow_launch",
        var="controller_workflow_launch_jobs",
        tags=["workflow_launch", "controller_workflow_launch"],
    ),
]

EDA_DISPATCH: List[DispatchEntry] = [
    DispatchEntry(
        role="eda_credential_types",
        var="eda_credential_types",
        tags=["credential_type", "eda_credential_types"],
    ),
    DispatchEntry(
        role="eda_credentials",
        var="eda_credentials",
        tags=["credential", "eda_credentials"],
    ),
    DispatchEntry(
        role="eda_credential_input_sources",
        var="eda_credential_input_sources",
        tags=["credential_input_sources", "eda_credential_input_sources"],
    ),
    DispatchEntry(
        role="eda_controller_tokens",
        var="eda_controller_tokens",
        tags=["controller_token", "eda_controller_tokens"],
    ),
    DispatchEntry(role="eda_projects", var="eda_projects", tags=["project", "eda_projects"]),
    DispatchEntry(
        role="eda_event_streams",
        var="eda_event_streams",
        tags=["event_stream", "eda_event_streams"],
    ),
    DispatchEntry(
        role="eda_decision_environments",
        var="eda_decision_environments",
        tags=["decision_environment", "eda_decision_environments"],
    ),
    DispatchEntry(
        role="eda_rulebook_activations",
        var="eda_rulebook_activations",
        tags=["rulebook_activation", "eda_rulebook_activations"],
    ),
]

ALL_DISPATCH = GATEWAY_DISPATCH + HUB_DISPATCH + CONTROLLER_DISPATCH + EDA_DISPATCH

# Legacy loop-variable aliases accepted by controller roles.
# If a user defines e.g. ``job_templates`` instead of ``controller_templates``,
# the role's task file will still pick it up — we should not flag it.
LEGACY_ALIASES: Dict[str, str] = {
    "credential_types": "controller_credential_types",
    "credentials": "controller_credentials",
    "execution_environments": "controller_execution_environments",
    "notification_templates": "controller_notifications",
    "projects": "controller_projects",
    "inventory": "controller_inventories",
    "inventory_sources": "controller_inventory_sources",
    "job_templates": "controller_templates",
    "workflow_job_templates": "controller_workflows",
    "schedules": "controller_schedules",
}

# Well-known non-resource variables that are valid in config files.
KNOWN_GLOBAL_VARS: Set[str] = {
    "aap_hostname",
    "aap_username",
    "aap_password",
    "aap_token",
    "aap_validate_certs",
    "aap_request_timeout",
    "aap_configuration_secure_logging",
    "aap_configuration_async_retries",
    "aap_configuration_async_delay",
    "aap_configuration_loop_delay",
    "aap_configuration_enforce_defaults",
    "aap_configuration_collect_logs",
    "aap_configuration_async_dir",
    "aap_configuration_apply_object_roles",
    "platform_state",
    "controller_hostname",
    "controller_host",
    "controller_username",
    "controller_password",
    "controller_oauthtoken",
    "controller_validate_certs",
    "controller_request_timeout",
    "gateway_hostname",
    "gateway_username",
    "gateway_password",
    "gateway_token",
    "gateway_validate_certs",
    "gateway_request_timeout",
    "ah_host",
    "ah_username",
    "ah_password",
    "ah_token",
    "ah_path_prefix",
    "ah_validate_certs",
    "hub_path_prefix",
    "hub_token",
    "hub_username",
    "hub_password",
    "hub_host",
    "hub_validate_certs",
    "hub_request_timeout",
    "users_default_password",
    "ssh_private_key",
    # Ad-hoc command variables (not yet in dispatch but accepted by some setups)
    "controller_ad_hoc_commands",
    "controller_ad_hoc_command_defaults",
    # Test/staging helper vars
    "differential_items",
    "controller_templates_invalid",
    "controller_settings_individuale",
    "temp_controller_bulk_hosts",
    "temp_controller_bulk_launch_jobs",
    # Hub publish vars
    "hub_collection_list",
    "hub_custom_collections",
    "hub_configuration_dispatcher_roles_include_publish",
    # Dispatch control
    "aap_configuration_dispatcher_exclude_roles",
    "dispatch_include_wildcard_vars",
}


def get_dispatch_var_names() -> Set[str]:
    """Return the set of all dispatch variable names (base names only)."""
    return {entry.var for entry in ALL_DISPATCH}


def get_all_known_vars() -> Set[str]:
    """Return the set of all variable names the collection recognises."""
    known = set(KNOWN_GLOBAL_VARS)
    known.update(get_dispatch_var_names())
    for alias in LEGACY_ALIASES:
        known.add(alias)
    return known


def get_var_to_entries() -> Dict[str, List[DispatchEntry]]:
    """Map each dispatch variable name to the list of entries that use it."""
    mapping: Dict[str, List[DispatchEntry]] = {}
    for entry in ALL_DISPATCH:
        mapping.setdefault(entry.var, []).append(entry)
    return mapping
