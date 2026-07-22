---
name: filetree-roundtrip-test
description: >-
  Run a full filetree import → export → import roundtrip against AAP using
  test_filetree_read.yaml and test_filetree_create.yaml. Use when validating
  filetree_create/filetree_read changes, issue fixes, or when the user asks for
  a complete roundtrip test. Never filter object types; export and import all
  supported objects.
---

# Filetree roundtrip test (full)

## Requirement

Sempre que facis una prova completa com aquesta, no filtris cap tipus d'objecte, fes la prova completa, amb tots els objectes.

- Do **not** pass a narrowed `input_tag` to `filetree_create` (default `all` is correct).
- Do **not** limit `filetree_read` / `dispatch` to a subset of object tags; use tag `all`.
- Use the most complete config set under `tests/configs/roundtrip/` (merge of `fcf` + `custom`).
- Roundtrip fixtures and assertions must use object **names**, never numeric API IDs (CaC baseline).

## Config set

| Path | Purpose |
| ---- | ------- |
| `tests/configs/roundtrip/` | Canonical full seed (72 files: controller + gateway + eda + hub + custom scenarios) |
| `/tmp/filetree_roundtrip_test/input/` | Temp copy of seed for an isolated run |
| `/tmp/filetree_output_default/` | Export output from `test_filetree_create.yaml` (use `--skip-tags cleanup`) |

Copy seed before import:

```bash
rm -rf /tmp/filetree_roundtrip_test
mkdir -p /tmp/filetree_roundtrip_test/input /tmp/filetree_roundtrip_test/export
cp -a tests/configs/roundtrip/* /tmp/filetree_roundtrip_test/input/
```

**Platform-managed objects:** filetree export filters API queries with `managed: false` for controller/EDA credentials and credential types, gateway role definitions, and EDA event streams. Platform-managed credentials (e.g. `Default Execution Environment Registry Credential`) are never exported or imported via filetree.

Override all `filetree_*` paths to the temp input/export dir (see `tests/configs/roundtrip_extra_vars/extra_vars_read.yml`).

## Workflow

Run from `tests/` with `vault-aap-controller.yaml` (or env vars).

### 1. Import (seed → AAP)

Do **not** pass the reserved tag `all` on the CLI (it runs every play). Use `tests/configs/roundtrip/ansible_tags` instead:

```bash
ansible-playbook test_filetree_read.yaml \
  -e@vault-aap-controller.yaml \
  -e@configs/roundtrip_extra_vars/extra_vars_read.yml \
  --skip-tags custom,fc,fcf,gv \
  --tags "$(tr -d '\n' < configs/roundtrip/ansible_tags)"
```

The roundtrip play sets `filetree_read_run_all: true` so every filetree_read object type is loaded.

### 2. Export (AAP → filetree, all objects)

```bash
ansible-playbook test_filetree_create.yaml \
  -e@vault-aap-controller.yaml \
  --tags "always,default,yaml_format" \
  --skip-tags "cleanup,flatten"
```

Do **not** override `input_tag`. Export is written to `/tmp/filetree_output_default/`.

### 3. Re-import (export → AAP, idempotent check)

```bash
ansible-playbook test_filetree_read.yaml \
  -e@vault-aap-controller.yaml \
  -e@configs/roundtrip_extra_vars/extra_vars_read_export.yml \
  --skip-tags custom,fc,fcf,gv \
  --tags "$(tr -d '\n' < configs/roundtrip/ansible_tags)"
```

Point `extra_vars_read_export.yml` at `/tmp/filetree_output_default`.

`gateway_role_user_assignments.yaml` references org `Default` and credential `roundtrip-rbac-credential` by name. Name resolution is handled by `ansible.platform.role_user_assignment` (fix upstream in `ansible.platform` if a content type is not resolved correctly).

## Success criteria

- All three playbooks exit `failed=0`.
- Step 3 is idempotent (`changed=0` or only benign async retries).
- For data-type fixes: spot-check `controller_settings.yaml` / `gateway_settings.yaml` for native YAML types (`int`, `bool`, dicts), not quoted strings.

## Logs

Save logs under `/tmp/filetree_roundtrip_test/step{1,2,3}_*.log` for post-mortem.

## Tags reference

Do **not** use `--tags all` on the CLI: `all` is reserved in Ansible and runs every play (including `custom`). Use `configs/roundtrip/ansible_tags` for the full object-type tag set, plus `--skip-tags custom,fc,fcf,gv`.
