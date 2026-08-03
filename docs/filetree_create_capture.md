# Capturing existing AAP objects as Configuration as Code

The [`filetree_create`](../roles/filetree_create/README.md) role is the supported way to capture objects that already exist in Ansible Automation Platform and turn them into YAML suitable for `infra.aap_configuration.dispatch` (via [`filetree_read`](../roles/filetree_read/README.md)).

Use it when you want to move from ClickOps / GUI-created objects to GitOps, or when you need a starting definition for an object type without browsing the API explorer by hand.

## What it does today

- Exports Controller, Gateway, EDA, and Hub objects that the collection supports into a file tree (or flattened YAML files with `flatten_output: true`).
- Filters by object **name** for common types (prefer names over numeric IDs), for example:
  - `organization_filter` / `organization_name`
  - `project_name`, `inventory_name`
  - `job_template_name`, `workflow_job_template_name`
  - Hub filters such as `hub_collection_name`, `hub_ee_repository_name`
- Narrows by organization with `organization_filter`.
- Limits which object types run with `input_tag`.
- Exports related objects for a single JT / WFJT when `export_related_objects` is enabled (see the role README PRE → PRO examples).
- Omits numeric IDs from filenames when `omit_id: true` (recommended for CaC).

Example — export one inventory by name:

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  vars:
    aap_hostname: "{{ aap_hostname }}"
    aap_username: "{{ aap_username }}"
    aap_password: "{{ aap_password }}"
    aap_validate_certs: false
    output_path: /tmp/filetree_output
    omit_id: true
    inventory_name: "My Inventory"
    input_tag:
      - controller_inventories
  roles:
    - infra.aap_configuration_extended.filetree_create
```

Then import with `filetree_read` + `infra.aap_configuration.dispatch` (see `playbooks/import_filetree.yml`).

## Gaps that remain (not implemented here)

The original enhancement request also asked for:

1. **Stdout-only capture** — emit the YAML via `ansible.builtin.debug` (or similar) without writing files. Today the role always writes under `output_path`. Workarounds: `flatten_output: true` and read the generated file(s), or pipe/cat after the run.
2. **Name filters for every object type** — several types already support `*_name` filters; others still export the full type (optionally limited by org / tags). Broader per-type name selectors can be added as follow-up enhancements.
3. **Strip API defaults aggressively** — templates already omit many empty / unset fields; they are not a full “diff against factory defaults” for every attribute.

Those items can be separate issues/PRs if still needed; they are not blockers for using `filetree_create` as the capture tool.

## See also

- [filetree_create README](../roles/filetree_create/README.md)
- [filetree_read README](../roles/filetree_read/README.md)
- [EXPORT_README.md](../EXPORT_README.md) (awx / ansible.controller export alternatives)
