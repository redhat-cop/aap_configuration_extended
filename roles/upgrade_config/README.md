# Upgrade Config Role

This role is designed to automatically convert the configuration files used for AAP <= 2.4 CaC collections to the new format supported by the AAP >= 2.5 CaC collections.

The following conversions are implemented:

<!-- markdownlint-disable-line MD033 --><table>
<!-- markdownlint-disable-line MD033 -->    <thead>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <th>Component</th>
<!-- markdownlint-disable-line MD033 -->            <th>AAP <= 2.4</th>
<!-- markdownlint-disable-line MD033 -->            <th>AAP >= 2.5</th>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->    </thead>
<!-- markdownlint-disable-line MD033 -->    <tbody>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td rowspan=2>LDAP Configuration</td>
<!-- markdownlint-disable-line MD033 -->            <td>Connection variables</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticators</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td>User and group mappings</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticator Maps</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td rowspan=2>SAML Configuration</td>
<!-- markdownlint-disable-line MD033 -->            <td>Connection variables</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticators</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td>User and group mappings</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticator Maps</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->    </tbody>
<!-- markdownlint-disable-line MD033 --></table>

## Role Variables

|Variable|Required|Type|Description|
|:---|:---:|:---:|:---|
|aap24_configs_dir|Yes|Path|Directory with the CaC files for AAP <= 2.4 (input).|
|aap25_configs_dir|Yes|Path|Directory where upgraded CaC files for AAP >= 2.5 are written (output).|
|sanitize|No|bool|If true, deletes `aap25_configs_dir` before writing so the output directory starts empty.|
|input_authenticator_name|No|str|LDAP gateway authenticator name; also used as fallback for SAML organization maps when `saml_organization_map_authenticator` is unset. Example: `IDM LDAP`.|
|input_authenticator_enabled|No|bool|Sets the LDAP authenticator `enabled` field in `gateway_authenticators.yaml` (defaults to true).|
|input_filename_prefix|No|str|Optional prefix for 2.4 source filenames under `aap24_configs_dir` (e.g. if files are named `prefix_workflows.yaml`).|
|saml_organization_map_authenticator|No|str|Authenticator name on SAML-derived **organization** maps. If unset, uses `input_authenticator_name` when defined, otherwise the resolved SAML IdP name. Set explicitly to the IdP name (e.g. `RHSSO`) when `input_authenticator_name` names LDAP but SAML org maps must reference SAML.|

**Development-only check:** the playbook `roles/upgrade_config/tests/upgrade_config.yaml` can write output to a temporary directory and run `roles/upgrade_config/tests/compare_upgrade_output.py` against `tests/configs/upgrade_configs/aap_25`. That script and the compare task exist only to harden the role during development; **you may delete `compare_upgrade_output.py` and remove the compare task from the playbook** (and this paragraph) once you no longer need the fixture check. While present: the reference `aap_25` tree is not modified; the script parses YAML so quote style differences are ignored; `gateway_settings.yaml` in `aap_25` is not required in generated output; for `gateway_authenticators` / `gateway_authenticator_maps`, reference entries are matched by `name` and extra generated entries are allowed.

**YAML formatting:** after LDAP/SAML and after copying common CaC objects, the role runs `infra.aap_configuration_extended.format_yaml` with `preserve_comments: false` and `auto_block_scalars: true` on:

- `gateway_authenticators.yaml` and `gateway_authenticator_maps.yaml`
- `aap_notifications.yaml` and `aap_workflows.yaml`

This normalizes block-style lists, multiline `!unsafe` and PEM blocks, omits the literal `null` keyword for nulls (empty keys instead), and uses double-quoted scalars for slash-style regex strings that contain backslashes. The optional **tag** `yaml_format` on a final block in `tasks/main.yml` reformats every `*.yaml` / `*.yml` under `aap25_configs_dir` the same way (skipped unless you apply that tag).

The dev compare step needs Python 3 with PyYAML on the controller (same as Ansible).

## Known problems

- After the conversion, the generated file `gateway_authenticators.yaml` must be updated by, at least, the following two fields:
  - SAML:
    - configuration -> CALLBACK_URL: This field must be set to the correct URL
    - configuration -> SP_PRIVATE_KEY: This field must be set to the correct private key, having the following format:

      ```yaml
      SP_PRIVATE_KEY: |
        -----BEGIN PRIVATE KEY-----
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXX
        -----END PRIVATE KEY-----

      ```

## Example Playbook

```yaml
---
#
# ansible-playbook -i localhost, roles/upgrade_config/tests/upgrade_config.yaml -e '{sanitize: true}'
#
- name: "Playbook to upgrade CaC from AAP <= 2.4 to AAP >= 2.5 format"
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    upgrade_config_reference_aap25_dir: "{{ playbook_dir }}/../../../tests/configs/upgrade_configs/aap_25"
  tasks:
    - name: "Create temporary directory for role output"
      ansible.builtin.tempfile:
        state: directory
        suffix: upgrade_config
      register: upgrade_config_generated_dir

    - name: "Run upgrade and compare to reference"
      block:
        - name: "Call upgrade_config role"
          ansible.builtin.include_role:
            name: infra.aap_configuration_extended.upgrade_config
          vars:
            aap24_configs_dir: "{{ playbook_dir }}/../../../tests/configs/upgrade_configs/aap_24"
            aap25_configs_dir: "{{ upgrade_config_generated_dir.path }}"
            input_authenticator_name: "IDM LDAP"

        # Dev-only: delete compare_upgrade_output.py and this task when the role is stable.
        - name: "Semantic YAML compare to tests/configs/upgrade_configs/aap_25"
          ansible.builtin.command:
            argv:
              - python3
              - "{{ playbook_dir }}/compare_upgrade_output.py"
              - "{{ upgrade_config_reference_aap25_dir }}"
              - "{{ upgrade_config_generated_dir.path }}"
          register: upgrade_config_diff
          changed_when: false
          failed_when: upgrade_config_diff.rc != 0

      always:
        - ansible.builtin.file:
            path: "{{ upgrade_config_generated_dir.path }}"
            state: absent
          when: upgrade_config_generated_dir.path is defined
```

For a normal migration, set `aap25_configs_dir` to your target directory and omit the `tempfile` / dev comparison steps.

## License

GPLv3+

## Author Information

- [ivarmu](https://github.com/ivarmu)
