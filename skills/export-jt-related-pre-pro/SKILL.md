---
name: export-jt-related-pre-pro
description: >-
  Export a Job Template or Workflow Job Template and related Controller objects
  from PRE and import into PRO using filetree_create/filetree_read. Use when
  migrating JT/WFJT between AAP environments, export_related_objects,
  env_variables stubs, or PRE→PRO CaC.
---

# Export JT / WFJT + related objects (PRE → PRO)

## CaC rule

**Names, never IDs.** Pass `job_template_name` or `workflow_job_template_name`, never numeric `*_id`. Related export resolves dependencies by object **name**. Keep `omit_id: true` on export.

## Workflow

### 1. Export from PRE

Job Template:

```bash
ansible-playbook playbooks/export_job_template_related.yml \
  -e aap_hostname=aap-pre.example.com \
  -e aap_username=admin -e aap_password=secret \
  -e aap_validate_certs=false \
  -e '{"job_template_name":"My Job Template"}' \
  -e output_path=/tmp/jt_export
```

Workflow Job Template:

```bash
ansible-playbook playbooks/export_workflow_job_template_related.yml \
  -e aap_hostname=aap-pre.example.com \
  -e aap_username=admin -e aap_password=secret \
  -e aap_validate_certs=false \
  -e '{"workflow_job_template_name":"My Workflow"}' \
  -e output_path=/tmp/wfjt_export
```

Names with spaces require JSON `-e` (or a vars file); plain `-e key='a b'` truncates at the first space.

**JT exports:** organization, project, inventory (+ sources/hosts/groups unless skipped), credentials + credential types, execution environments, labels, notification templates, schedules, and the JT.

**WFJT exports:** organization, inventories (workflow-level and per-node), each node Job Template **with its full related set**, labels, notification templates (including approvals), schedules, and the WFJT.

Secrets and curated env fields become `{{ vaulted_* }}` placeholders; stub at `{output_path}/env_variables.yml`.

### 2. Fill PRO values

Edit `{output_path}/env_variables.yml` (replace `CHANGE_ME`). Optionally `ansible-vault encrypt` it.

### 3. Import into PRO

```bash
ansible-playbook playbooks/import_filetree.yml \
  -e aap_hostname=aap-pro.example.com \
  -e aap_username=admin -e aap_password=secret \
  -e aap_validate_certs=false \
  -e dir_orgs_vars=/tmp/jt_export \
  -e @/tmp/jt_export/env_variables.yml
```

## Implementation notes

- JT related cascade: `roles/filetree_create/tasks/controller_job_templates.yml`
- WFJT related cascade: `roles/filetree_create/tasks/controller_workflow_job_templates.yml` (reuses JT related export per node)
- Filters use `*_name` / `*_names` (and related URLs for schedules), not public `*_id` vars
- **Complete worked examples** (tree layout, sample YAML, `env_variables.yml`, export/import commands): `roles/filetree_create/README.md` section **PRE → PRO: complete examples**
