# aap_config_vars

Load Ansible Automation Platform configuration-as-code variables for `infra.aap_configuration.dispatch`. This replaces `ansible.builtin.include_vars` for the `config/all/` plus `config/<env>/` layout used by [aap_configuration_template](https://github.com/redhat-cop/aap_configuration_template).

By default the module performs a **full load** (every object). Set `changed_only` to apply only objects whose YAML content changed in git.

See `ansible-doc infra.aap_configuration_extended.aap_config_vars` for the full option list.

## Full apply

```yaml
- name: Load AAP configuration
  infra.aap_configuration_extended.aap_config_vars:
    config_dir: "{{ playbook_dir }}/../config"
    env: "{{ env }}"

- name: Call dispatch role
  ansible.builtin.include_role:
    name: infra.aap_configuration.dispatch
  vars:
    dispatch_include_wildcard_vars: true
```

## Incremental apply (git-changed objects)

The module compares parsed YAML objects, not raw git line hunks. Comment-only or formatting-only edits are ignored.

Identity for list items is `name` (plus `organization` when present). Assignment objects without a name use fields such as `user`, `team`, and `role`.

Unchanged object-type vars are omitted so dispatch skips those roles. Files listed in `always_load` (`secrets.yml` and `aap_install.yml` by default) are always included in full.

Removed objects are not deleted unless `include_absent` is true. Use a full run (`changed_only: false`, the default) for the first apply or if the cluster may have drifted from git.

```yaml
- name: Load only objects that changed since HEAD
  infra.aap_configuration_extended.aap_config_vars:
    config_dir: "{{ playbook_dir }}/../config"
    env: "{{ env }}"
    changed_only: true
    git_base: HEAD

- name: Load objects that changed on this branch vs origin/main
  infra.aap_configuration_extended.aap_config_vars:
    config_dir: "{{ playbook_dir }}/../config"
    env: "{{ env }}"
    changed_only: true
    git_base: origin/main
    include_absent: true
```

Typical extra vars when driving this from the configuration template playbook:

```bash
ansible-playbook -i inventory/inventory_dev.yml -l dev playbooks/aap_config.yml --ask-vault-pass \
  -e aap_config_changed_only=true -e aap_config_git_base=origin/main
```

`git_base: HEAD` compares the working tree (including uncommitted edits) to the last commit. Use `origin/main` (or another branch) in CI to apply everything that changed on the branch.

The task result includes `aap_config_mode` (`full` or `incremental`) and `aap_config_changed_vars` (object names only, not secret inputs).

An action plugin with the same name runs on the controller: it resolves `playbook_dir` and decrypts vault with the same DataLoader as `include_vars`.
