# filetree_object_diff

Compare a live Ansible Automation Platform export (via `filetree_create`) against repository Configuration as Code (CaC) **at file level**, and produce a delta suitable for `infra.aap_configuration.dispatch`.

## Workflow

1. **Export** live state with `filetree_create` into a temporary directory.
2. **Compare files on disk** with the `filetree_cac_diff` module (repository CaC paths vs live export).
3. **Write difference YAML files** under `filetree_object_diff_diff_path` (`state: present` / `state: absent`).
4. **Load only the difference files** with `filetree_read` into Ansible variables.
5. **Apply** with `infra.aap_configuration.dispatch`.

No full in-memory comparison of both sides: only diff files are loaded.

## Requirements

- Ansible Automation Platform 2.5+
- `infra.aap_configuration` collection
- Repository `filetree_*` paths configured (as for `filetree_read`)

## Variables

| Variable | Default | Description |
| :------- | :------ | :---------- |
| `filetree_object_diff_live_path` | `/tmp/filetree_object_diff_live` | Live export directory |
| `filetree_object_diff_diff_path` | `/tmp/filetree_object_diff_delta` | Generated diff files |
| `filetree_object_diff_config_dir` | *(unset)* | Org-root or flat directory for on-disk CaC comparison. When unset, paths are captured from `filetree_*` variables before `filetree_read` runs |
| `filetree_object_diff_flatten_output` | `false` | Passed to `filetree_create` as `flatten_output`. Supports both normal tree and flat per-type layouts |
| `filetree_object_diff_omit_id` | `true` | Passed to `filetree_create` as `omit_id` for live export filenames |
| `filetree_object_diff_template_vars` | `{orgs, env}` | Render Jinja in repo CaC before compare |
| `filetree_object_diff_ignore_keys` | `[]` | Extra keys ignored in comparison |
| `filetree_object_diff_cleanup_live_path` | `true` | Remove live export after diff |
| `controller_configuration_filetree_object_diff_tasks` | *(see defaults)* | Object types to export, compare, and load |

### Secret / variable handling

Repository CaC may use Jinja for secrets (`{{ vault_password }}`). Pass all required variables via `filetree_object_diff_template_vars` so the module can render CaC files before comparing. Sensitive keys (`password`, `inputs`, etc.) are ignored by default during comparison.

### Coverage

Default `controller_configuration_filetree_object_diff_tasks` covers the full intersection of `filetree_create` and `infra.aap_configuration.dispatch`: Gateway, Controller, Hub, and EDA. Runtime-only dispatch roles (job launch, sync, publish, bulk hosts) are excluded.

### Organizations and super-admin object types

- Organizations are exported with `controller_organizations` so live YAML uses the `aap_organizations` root key expected by `filetree_read`. Legacy live exports that still use `gateway_organizations` are normalized to `aap_organizations` during comparison.
- Tasks marked `superuser_only: true` (platform Gateway infrastructure, organizations, roles, instance groups, instances, settings, …) are skipped automatically when the OAuth user is not a platform super-admin. Org-scoped objects remain available.

## Full example

A complete, production-oriented playbook and variable templates are provided:

| Path | Purpose |
| :--- | :------ |
| [`playbooks/filetree_object_diff.yml`](../../playbooks/filetree_object_diff.yml) | OAuth, diff, optional apply, convergence check |
| [`examples/filetree_object_diff/`](../../examples/filetree_object_diff/) | Variable templates and step-by-step guide |

Preview the delta without applying:

```bash
ansible-playbook playbooks/filetree_object_diff.yml \
  -e @examples/filetree_object_diff/vars/filetree_object_diff.yml \
  -e @examples/filetree_object_diff/vars/vault.yml \
  -e apply_changes=false
```

Apply changes:

```bash
ansible-playbook playbooks/filetree_object_diff.yml \
  -e @examples/filetree_object_diff/vars/filetree_object_diff.yml \
  -e @examples/filetree_object_diff/vars/vault.yml
```

## Minimal example (role only)

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  vars:
    orgs: "Default"
    env: common
    dir_orgs_vars: /srv/cac/orgs_vars
    filetree_object_diff_config_dir: "{{ dir_orgs_vars }}/{{ orgs }}"
    aap_hostname: aap.example.com
    aap_oauthtoken: "{{ lookup('env', 'AAP_TOKEN') }}"
  roles:
    - infra.aap_configuration_extended.filetree_object_diff
```

After the role completes, variables such as `controller_projects` and
`controller_inventories` contain only the delta. Pass them to dispatch:

```yaml
    - role: infra.aap_configuration.dispatch
      vars:
        controller_configuration_dispatcher_roles:
          - {role: controller_projects, var: controller_projects, tags: controller_projects}
          - {role: controller_inventories, var: controller_inventories, tags: controller_inventories}
```

## Tags

Uses the same tags as `filetree_create` / `object_diff` (for example `controller_inventories`, `controller_projects`).

## See also

- [`examples/filetree_object_diff/README.md`](../../examples/filetree_object_diff/README.md) — repository layout and quick start
- `infra.aap_configuration_extended.filetree_cac_diff` — on-disk file comparison module
- `infra.aap_configuration_extended.controller_filetree_diff` — in-memory lookup (alternative API)
- `infra.aap_configuration_extended.object_diff` — legacy API-based diff
