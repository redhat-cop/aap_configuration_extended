---
name: add-filetree-entity
description: >-
  Add a new Controller, Gateway, Hub, or EDA object to infra.aap_configuration_extended
  filetree_create and filetree_read roles. Use when exporting or importing CaC YAML,
  adding filetree_create output, filetree_read loaders, or fixing missing entity support.
---

# Add a filetree entity (create + read)

Pair **filetree_create** (API → YAML) with **filetree_read** (YAML → Ansible vars → dispatch).
Use FQCN `infra.aap_configuration_extended.*` and existing naming (`controller_*`, `gateway_*`, `hub_*`, `eda_*`).

## Checklist

### 1. Scope

| Kind | Example | Output file (flatten) | `filetree_read` path default |
| ---- | ------- | --------------------- | ---------------------------- |
| Global controller | instances, settings | `controller_instances.yaml` | `.../controller_instances.d/` |
| Per-org | projects | under `ORG/controller_projects.d/` | `.../controller_projects.d/` |

Confirm the **CaC variable** in `infra.aap_configuration` (e.g. `controller_instances`) and dispatch tag (e.g. `instances`).

### 2. filetree_create

1. `roles/filetree_create/tasks/controller_<entity>.yml` — `gateway_api` query, optional lookups, `template` → `{{ output_path }}/controller_<entity>.yaml`.
2. `roles/filetree_create/templates/controller_<entity>.j2` — top-level key = CaC variable; omit empty fields.
   - At the top of the template (after the YAML `---` list header), define Jinja lists with `{% set %}`: always `__empty_values`, plus any allowlists (e.g. `__exportable_node_types`, `__exportable_node_states`). Do not inline list literals in `{% if %}` conditions.
   - Use `__empty_values` for every optional scalar/mapping field before exporting (e.g. `field is defined and field not in __empty_values`). Combine with allowlists when the API returns runtime-only values that must not be applied via CaC.
   - **Jinja control-tag indentation** (match existing templates; do not use `{%- … %}` trim on block tags unless output whitespace requires it):

     ```jinja2
     {% for a in all %}
     {%   if a is blablabla %}
     {%     if a is blabla %}
     {%     endif %}
     {%   endif %}
     {% endfor %}
     ```

     Rules:
     - Top-level `for` / file header `if`: `{% for %}`, `{% if %}`, `{% endfor %}`, `{% endif %}` (no leading spaces after `{%`).
     - Each nesting level adds **two spaces** after `{%`: level 1 → `{%   if %}`, level 2 → `{%     if %}`, level 3 → `{%       if %}`, etc.
     - Closing tags use the **same** indentation as their opening tag (`{%   endif %}` closes `{%   if %}`, not `{%-  endif %}`).
     - Inner `for` inside an outer `for`: `{%   for … %}` … `{%   endfor %}`; outer loop closes with `{% endfor %}`.
3. `roles/filetree_create/tasks/all.yml` — `include_tasks` with `when: "'controller_<entity>' in input_tag or 'controller' in input_tag or 'all' in input_tag"`.
4. `roles/filetree_create/defaults/main.yml` — add `controller_<entity>` to `valid_tags`.

#### API / CaC pitfalls

- **Names, never IDs (mandatory):** CaC identifies objects by **name**. In templates, related objects must use `summary_fields.*.name` (or equivalent name fields). Do **not** emit `id`, `*_id`, or `*_ids` into generated YAML. User-facing filters and examples must use `*_name` / `organization_filter` / `label_filter`, not numeric IDs. Prefer `omit_id: true` for output filenames.
- **Peers** on instances: API returns `receptor_addresses` IDs. Query `api/controller/v2/receptor_addresses/`, map `id` → `summary_fields.instance.hostname` or `address`; export hostnames for `ansible.controller.instance`.
- **Instances CaC fields**: at the top of `controller_instances.j2` define `__exportable_node_types` (`execution`, `hop`) and `__exportable_node_states` (`installed`, `deprovisioning`). Loop only over instances whose `node_type` is importable; do not export control/hybrid/controller nodes. Use `__empty_values` on optional scalars.
- **Related objects**: use `query('ansible.platform.gateway_api', ...)` with `return_all=true`, `max_objects=query_controller_api_max_objects`. When selecting a subset for export, filter by **name** / `name__in` (or related URLs), not by numeric id in public vars.
- **Secrets**: follow existing templates (`{%- raw -%}`, `secrets_as_variables`).

### 3. filetree_read (required for every new create entity)

Mirror `controller_instance_groups.yml`:

1. `roles/filetree_read/tasks/controller_<entity>.yml` — `find` on `filetree_controller_<entity>` with `contains: "controller_<entity>:"`, `include_vars`, merge into `__populate_controller_<entity>`, set `controller_<entity>`.
2. `roles/filetree_read/defaults/main.yml` — `filetree_controller_<entity>` path + entry in `controller_configuration_filetree_read_tasks` (`name`, `var`, `tags`).
3. `roles/filetree_read/meta/argument_specs.yml` — document `filetree_controller_<entity>`.
4. Tests: set `filetree_controller_<entity>: *<configs>_path` in `tests/test_filetree_read.yaml` (custom, fc, fcf, gv plays).
5. Sample data: add `tests/configs/fcf/controller_<entity>.yaml` (flatten fixture) when tests use fcf.

`controller_location` segregation: copy the block from `controller_instance_groups.yml` if entities can be site-specific.

### 4. Verify

```bash
# Export (venv + collections path as in collection README / local practice)
ansible-playbook tests/test_filetree_create.yaml -e@vault-aap-controller.yaml --tags flatten --skip-tags cleanup

# Import instances on fcf fixtures (add tag instances; skip unrelated dispatch roles)
ansible-playbook tests/test_filetree_read.yaml --tags fcf,instances \
  --skip-tags gateway_organizations,gateway_applications,gateway_teams,gateway_users,settings,instance_groups,execution_environments,schedules,roles,credentials,notification_templates \
  -e@vault-aap-controller.yaml
```

### 5. Changelog

`changelogs/fragments/issueNNN.yaml` — bugfix or minor entry for create and read.

## Reference implementation

**controller_instances** (issue #235): global object, peers resolved via `receptor_addresses_lookvar` + `__receptor_peer_hostname_by_id` in create; read task matches instance_groups pattern with tag `instances`.
