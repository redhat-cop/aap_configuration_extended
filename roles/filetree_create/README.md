# controller_configuration.filetree_create

The role `filetree_create` is intended to be used as the first step to begin using the Configuration as Code on Ansible Tower or Ansible Automation Platform, when you already have a running instance of any of them. Obviously, you also could start to write your objects as code from scratch, but the idea behind the creation of that role is to simplify your lives and make that task a little bit easier.

## Requirements

- for Red Hat Ansible Automation Platform >= 2.5, collections:
  - [ansible.controller](https://console.redhat.com/ansible/automation-hub/repo/published/ansible/controller), and
  - [ansible.platform](https://console.redhat.com/ansible/automation-hub/repo/published/ansible/platform/)

## Role Variables

The following variables are required for that role to work properly:

| Variable Name | Default Value | Required | Type | Description |
| :------------ | :-----------: | :------: | :------: | :---------- |
| `organization_filter` | N/A | no | str | Exports only the objects belonging to the specified organization **name** (preferred CaC selector). |
| `organization_id` | N/A | no | int | Legacy alternative to `organization_filter` using a numeric ID. Prefer organization **names**. |
| `organization_name` | N/A | no | str | Filter a single organization by **name** (used by related export). |
| `project_name` | N/A | no | str | Filter projects by **name**. Prefer this over `project_id`. |
| `project_id` | N/A | no | int | Legacy filter by project id. Prefer `project_name`. |
| `job_template_name` | N/A | no | str | Filter / select a job template by **name**. Prefer this over `job_template_id` for CaC. |
| `job_template_id` | N/A | no | int | Legacy filter by job template id. Prefer `job_template_name`. |
| `label_filter` | N/A | no | str | Specifiying a label to filter the job templates by. Exports all the job templates having the specified label assigned. |
| `inventory_name` | N/A | no | str | Filter inventories by **name**. Prefer this over `inventory_id`. |
| `inventory_id` | N/A | no | int | Legacy filter by inventory id. Prefer `inventory_name`. |
| `workflow_job_template_name` | N/A | no | str | Filter / select a workflow job template by **name**. Prefer this over `workflow_job_template_id` for CaC. |
| `workflow_job_template_id` | N/A | no | int | Legacy filter by workflow job template id. Prefer `workflow_job_template_name`. |
| `schedule_id` | N/A | no | int | Specifiying the schedule id to filter by. Prefer schedule **name** / related object links. |
| `output_path` | `/tmp/filetree_output` | yes | str | The path to the output directory where all the generated `yaml` files with the corresponding Objects as code will be written to. |
| `input_tag` | `['all']` | no | List of Strings | The tags which are applied to the 'sub-roles'. If 'all' is in the list (the default value) then all roles will be called.  Valid tags can be found under `vars/valid_tags`. |
| `flatten_output` | N/A | no | bool | Whether to flatten the output in single files per each object type instead of the normal exportation structure. |
| `secrets_as_variables` | True | no | bool | Whether to export the secrets as variables that can be populated from existing variables/files. An example: `vaulted_eda_credentials_my_eda_credential_password`, that follows the syntax: `<secrets_as_variables_prefix>_<object_type>_<object_name>_<field_name>`. |
| `secrets_as_variables_prefix` | vaulted | no | str | The prefix to use for the variables defined by `secrets_as_variables` feature. |
| `show_encrypted` | N/A | no | bool | Whether to remove the string '\$encrypted\$' in credentials output (not the actual credential value). |
| `omit_id` | N/A | no | bool | Whether to create output files without numeric object id prefixes. Recommended `true` for CaC. |
| `organization` | N/A | no | str | Default organization for all objects that have not been set in the source controller. |
| `export_related_objects` | False | no | bool | Whether to export related objects when a single JT or WFJT is exported by name. JT: organization, project, inventory (+ sources/hosts/groups unless skipped), credentials (+ types), EEs, labels, notification templates, schedules. WFJT: organization, inventories, nested workflow nodes recursively until Job Template leaves, each discovered JT with its full related set, labels, notification templates (incl. approvals), schedules. |
| `export_inline_object_roles` | False | no | bool | When true, embed `infra.aap_configuration` inline object `roles` (users/teams by role key) on inventories, projects, job templates, workflow job templates, credentials, and instance groups. Default keeps the separate `controller_roles` export only. |
| `env_fields_as_variables` | `export_related_objects` | no | bool | Whether to export selected non-secret but environment-specific fields as Ansible variable references (same naming scheme as `secrets_as_variables`). |
| `generate_env_variables_stub` | true when secrets/env-as-vars | no | bool | Whether to write `{output_path}/env_variables.yml` listing every discovered `{{ vaulted_* }}` placeholder for PRO (or other env) values. |
| `env_variables_stub_path` | `{{ output_path }}/env_variables.yml` | no | str | Destination path for the env variables stub file. |
| `env_variables_stub_placeholder` | `CHANGE_ME` | no | str | Placeholder value written for each discovered variable in the stub. |
| `env_fields_as_variables_map` | (see defaults) | no | dict | Map of object type → field names exported as variables when `env_fields_as_variables` is true. |
| `update_project_state` | False | no | bool | Whether the project should be updated after import to the target controller. |
| `skip_inventory_sources` | False | no | bool | Whether the inventory sources should be exported with inventory. |
| `skip_inventory_hosts` | False | no | bool | Whether the inventory hosts should be exported with inventory. |
| `skip_inventory_groups` | False | no | bool | Whether the inventory groups should be exported with inventory. |
| `templates_overrides_resources` | N/A | no | dict | Whether the certain objects should be modified during the export. |
| `templates_overrides_global` | N/A | no | dict | Whether the all objects should be modified during the export. |
| `hub_collection_name` | N/A | no | str | Filter the collections to be exported from the PAH through it's name. |
| `hub_collection_namespace` | N/A | no | str | Filter the collections to be exported from the PAH through it's namespace. |
| `hub_collection_remote_name` | N/A | no | str | Filter the collection remotes to be exported from the PAH through it's name. |
| `hub_collection_remote_url` | N/A | no | str | Filter the collection remotes to be exported from the PAH through it's url. |
| `hub_ee_repository_name` | N/A | no | str | Filter the repositories to be exported from the PAH throuhg it's repository name. |
| `hub_ee_repository_remote` | N/A | no | str | Filter the repositories to be exported from the PAH throuhg it's repository's remote field. |
| `hub_role_name` | N/A | no | str | Filter the Roles to be exported from the PAH through it's name. |

### Secure Logging Variables

These variables control Ansible `no_log` on tasks that may touch credentials or tokens.
If neither a role-specific nor a shared variable is set, secure logging defaults to `false`.

Each `*_filetree_create_secure_logging` variable defaults to `aap_configuration_secure_logging`, then to the legacy `controller_configuration_secure_logging`. That lets you toggle secure logging for the whole CaC suite with one variable, or override it per component (Controller / EDA / Hub).

| Variable Name | Default Value | Required | Type | Description |
| :------------ | :-----------: | :------: | :------: | :---------- |
| `controller_configuration_filetree_create_secure_logging` | `false` (via shared cascade) | no | bool | Whether to hide Controller export task output from the log (`no_log`). |
| `eda_configuration_filetree_create_secure_logging` | `false` (via shared cascade) | no | bool | Whether to hide EDA export task output from the log (`no_log`). |
| `hub_configuration_filetree_create_secure_logging` | `false` (via shared cascade) | no | bool | Whether to hide Hub export task output from the log (`no_log`). |
| `aap_configuration_secure_logging` | `false` | no | bool | Shared secure-logging default across `infra.aap_configuration` / `infra.aap_configuration_extended` roles. |
| `controller_configuration_secure_logging` | `false` | no | bool | Legacy shared default; used when `aap_configuration_secure_logging` is unset. |

## Dependencies

A list of other roles hosted on Galaxy should go here, plus any details in regards to parameters that may need to be set for other roles, or variables that are used from other roles.

## Example Playbook - export everything without modifications

```yaml
---
- hosts: all
  connection: local
  gather_facts: false
  vars:
    aap_username: "{{ vault_aap_username | default(lookup('env', 'CONTROLLER_USERNAME')) }}"
    aap_password: "{{ vault_aap_password | default(lookup('env', 'CONTROLLER_PASSWORD')) }}"
    aap_hostname: "{{ vault_aap_hostname | default(lookup('env', 'CONTROLLER_HOST')) }}"
    aap_validate_certs: "{{ vault_aap_validate_certs | default(lookup('env', 'CONTROLLER_VERIFY_SSL')) }}"

  pre_tasks:
    - name: "Setup authentication (block)"
      block:
        - name: "Create a new token using platform username/password"
          ansible.platform.token:
            description: 'Token for Automated Management'
            scope: "write"
            state: present
            aap_hostname: "{{ aap_hostname }}"
            aap_username: "{{ aap_username }}"
            aap_password: "{{ aap_password }}"
            aap_validate_certs: "{{ aap_validate_certs }}"

        - name: "Expose aap_token dict for collection roles"
          ansible.builtin.set_fact:
            aap_token: "{{ ansible_facts['aap_token'] }}"
      no_log: "{{ controller_configuration_filetree_create_secure_logging | default('false') }}"
      when: not (ansible_facts.get('aap_token') or aap_token is defined)
      tags:
        - always

  roles:
    - infra.aap_configuration_extended.filetree_create

  post_tasks:
    - name: "Delete the Authentication Token used"
      ansible.platform.token:
        existing_token: "{{ aap_token }}"
        state: absent
        aap_hostname: "{{ aap_hostname }}"
        aap_username: "{{ aap_username }}"
        aap_password: "{{ aap_password }}"
        aap_validate_certs: "{{ aap_validate_certs }}"
      when:
        - aap_token is defined
        - aap_token is mapping
...
```

This role can generate output files in two different ways:

- **Structured output**:

  The output files are distributed in separate directories, by organization first, and then by object type. Into each of these directories, one file per object is generated. This way allows to organize the files using different criteria, for example, by functionalities or applications.

  The export can be triggered with the following command:

  ```console
  ansible-playbook -i localhost, filetree_create.yml -e '{aap_validate_certs: false, aap_hostname: localhost:8443, aap_username: admin, aap_password: password}'
  ```

  One example of this approach follows:

  ```console
  /tmp/filetree_output_distributted
  ├── current_credential_types.yaml
  ├── current_execution_environments.yaml
  ├── current_instance_groups.yaml
  ├── current_settings.yaml
  ├── Default
  │   ├── applications
  │   │   ├── 23_controller_application-app2.yaml
  │   │   └── 24_controller_application-app3.yaml
  │   ├── credentials
  │   │   ├── 82_Demo Credential.yaml
  │   │   └── 84_Demo Custom Credential.yaml
  │   ├── current_organization.yaml
  │   ├── inventories
  │   │   ├── Demo Inventory
  │   │   │   └── 81_Demo Inventory.yaml
  │   │   └── Test Inventory - Smart
  │   │       ├── 78_Test Inventory - Smart.yaml
  │   │       └── current_hosts.yaml
  │   ├── job_templates
  │   │   ├── 177_test-template-1.yaml
  │   │   └── 190_Demo Job Template.yaml
  │   ├── labels
  │   │   ├── 52_Prod.yaml
  │   │   ├── 53_differential.yaml
  │   ├── notification_templates
  │   │   ├── Email notification differential.yaml
  │   │   └── Email notification.yaml
  │   ├── projects
  │   │   ├── 169_Test Project.yaml
  │   │   ├── 170_Demo Project.yaml
  │   ├── teams
  │   │   ├── 28_satellite-qe.yaml
  │   │   └── 29_tower-team.yaml
  │   └── workflow_job_templates
  │       ├── 191_Simple workflow schema.yaml
  │       └── 200_Complicated workflow schema.yaml
  ├── ORGANIZATIONLESS
  │   ├── credentials
  │   │   ├── 2_Ansible Galaxy.yaml
  │   │   └── 3_Default Execution Environment Registry Credential.yaml
  │   └── users
  │       ├── admin.yaml
  │       ├── controller_user.yaml
  ├── schedules
  │   ├── 1_Cleanup Job Schedule.yaml
  │   ├── 2_Cleanup Activity Schedule.yaml
  │   ├── 4_Cleanup Expired Sessions.yaml
  │   ├── 52_Demo Schedule.yaml
  │   ├── 53_Demo Schedule 2.yaml
  │   └── 5_Cleanup Expired OAuth 2 Tokens.yaml
  ├── team_roles
  │   ├── current_roles_satellite-qe.yaml
  │   └── current_roles_tower-team.yaml
  └── user_roles
      └── current_roles_controller_user.yaml
  ```

- **Flatten files**:

  The output files are all located in the same directory. Each file contains a YAML list with all the objects belonging to the same object type. This output format allows to load all the objects both from the standard Ansible `group_vars` and from the `infra.aap_configuration_extended.filetree_read` role.

  The expotation can be triggered with the following command:

  ```console
  ansible-playbook -i localhost, filetree_create.yml -e '{aap_validate_certs: false, aap_hostname: localhost:8443, aap_username: admin, aap_password: password, flatten_output: true}'
  ```

  One example of this approach follows:

  ```console
  /tmp/filetree_output_flatten
  ├── applications.yaml
  ├── credentials.yaml
  ├── current_credential_types.yaml
  ├── current_execution_environments.yaml
  ├── current_instance_groups.yaml
  ├── current_settings.yaml
  ├── groups.yaml
  ├── hosts.yaml
  ├── inventories.yaml
  ├── inventory_sources.yaml
  ├── job_templates.yaml
  ├── labels.yaml
  ├── notification_templates.yaml
  ├── organizations.yaml
  ├── projects.yaml
  ├── schedules.yaml
  ├── team_roles.yaml
  ├── teams.yaml
  ├── user_roles.yaml
  ├── users.yaml
  └── workflow_job_templates.yaml
  ```

A playbook to convert from the structured output to the flattened one is provided, and can be executed with the following command:

```console
ansible-playbook infra.aap_configuration_extended.flatten_filetree_create_output.yaml -e '{filetree_create_output_dir: /tmp/filetree_output}'
```

## Example Playbook - export object with modifications

This example will export all object but some with modifications:

- job template called `job_template_example` will be exported with the `dev` branch, while the rest of the job templates will use the `main` branch — the resources dictionary takes precedence over the global dictionary.
- all projects will have a Jinja2 expression assigned to the `scm_branch`.
- all schedules enabled state will be set as `false`.

```yaml
---
- hosts: all
  connection: local
  gather_facts: false
  vars:
    aap_token: "{{ vault_aap_token | default(lookup('env', 'CONTROLLER_OAUTHTOKEN')) }}"
    aap_hostname: "{{ vault_aap_hostname | default(lookup('env', 'CONTROLLER_HOST')) }}"
    aap_validate_certs: "{{ vault_aap_validate_certs | default(lookup('env', 'CONTROLLER_VERIFY_SSL')) }}"

    templates_overrides_resources:
      job_template:
        job_template_example:
          scm_branch: "dev"

    templates_overrides_global:
      job_template:
        scm_branch: "main"
      project:
        scm_branch: !unsafe  "{{ 'true' if AAP.environment == 'PROD' else 'false' }}"
      schedules:
        enabled: false

  roles:
    - infra.aap_configuration_extended.filetree_create

...
```

## Usage example for the `secrets_as_variables` feature

To let the credentials and the users to be exported and imported 'as is', without any modification, the sensitive data (that can't be exported through the API) can be abstracted to extra vars (or variable's file) and vaulted. Those variables can be referenced at the original objects' code, so they can be imported without any manual modification. To clarify the described scenario, the following output shows the exported object for a gateway user, using the `secrets_as_variable` feature:

Sample playbook:

```yaml
---
- name: Filetree Create Test
  hosts: all
  connection: local
  gather_facts: false
  vars:
    aap_username: "{{ vault_aap_username | default(lookup('env', 'CONTROLLER_USERNAME')) }}"
    aap_password: "{{ vault_aap_password | default(lookup('env', 'CONTROLLER_PASSWORD')) }}"
    aap_hostname: "{{ vault_aap_hostname | default(lookup('env', 'CONTROLLER_HOST')) }}"
    aap_validate_certs: "{{ vault_aap_validate_certs | default(lookup('env', 'CONTROLLER_VERIFY_SSL')) }}"
    output_path: /tmp/filetree_output_25
    # Let the secrets to be defined externally (and vaulted) through well known variables
    secrets_as_variables: true

  pre_tasks:
    - name: "Setup authentication (block)"
      no_log: "{{ controller_configuration_filetree_create_secure_logging }}"
      when: not (ansible_facts.get('aap_token') or aap_token is defined)
      tags:
        - always
      block:
        - name: "Create a new token using platform username/password"
          ansible.platform.token:
            description: 'Token for Automated Management'
            scope: "write"
            state: present
            aap_hostname: "{{ aap_hostname }}"
            aap_username: "{{ aap_username }}"
            aap_password: "{{ aap_password }}"
            aap_validate_certs: "{{ aap_validate_certs }}"

        - name: "Expose aap_token dict for collection roles"
          ansible.builtin.set_fact:
            aap_token: "{{ ansible_facts['aap_token'] }}"

  roles:
    - infra.aap_configuration_extended.filetree_create

  post_tasks:
    - name: "Delete the Authentication Token used"
      ansible.platform.token:
        existing_token: "{{ aap_token }}"
        state: absent
        aap_hostname: "{{ aap_hostname }}"
        aap_username: "{{ aap_username }}"
        aap_password: "{{ aap_password }}"
        aap_validate_certs: "{{ aap_validate_certs }}"
      when:
        - aap_token is defined
        - aap_token is mapping
...
```

Generated file: `/tmp/filetree_output_25/gateway_users.yaml`

```yaml
---
aap_user_accounts:
  - username: "test_user"
    email: ""
    first_name: ""
    last_name: ""
    password: "{{ vaulted_gateway_users_test_user_password }}"
    is_superuser: "False"
    authenticators: []
    authenticator_uid: ""
...
```

The variable `vaulted_gateway_users_test_user_password` can be defined in a third file:

`~/vaulted_credentials.yaml`:

```yaml
vaulted_gateway_users_test_user_password: "SuperSecretPassword"
```

That file can be encrypted using `ansible-vault`.

The import process can be executed directly, using that file with the extra_vars option: `ansible-playbook -e@~/vaulted_credentials.yaml`.

When `generate_env_variables_stub` is enabled (default whenever secrets or env-fields-as-variables are on), the role also writes `{output_path}/env_variables.yml` with every discovered `vaulted_*` key set to `CHANGE_ME`. Fill that file with target-environment values (and optionally vault-encrypt it) instead of hand-crafting the variable list.

## PRE → PRO: complete examples (Job Template and Workflow)

Move one **Job Template** or **Workflow Job Template** (and its dependencies) from a PRE AAP to a PRO AAP. Objects are identified by **name** only (Configuration as Code). Secrets and environment-specific fields are exported as `{{ vaulted_* }}` placeholders; fill them for PRO before import.

### Prerequisites

- Collections installed: `infra.aap_configuration_extended` (and its dependencies).
- Network access and credentials (or OAuth token) for PRE and PRO.
- Run the playbooks from the collection root (or adjust paths to `playbooks/`).

### What gets exported

| Object | Job Template export | Workflow Job Template export |
| ------ | ------------------- | ---------------------------- |
| Organization | yes | yes |
| Project | yes (JT project) | via each node JT |
| Inventory (+ sources/hosts/groups*) | yes | workflow-level + per-node inventories |
| Credentials (+ credential types) | yes | via each node JT (+ inventory sources) |
| Execution environments | yes | via each node JT |
| Labels | yes | yes |
| Notification templates | error/started/success | + approvals |
| Schedules | linked to the JT | linked to the WFJT |
| Job Template itself | yes | each node JT (type `job`) with **full related set** |
| Workflow Job Template itself | — | yes |

\* Respect `skip_inventory_sources` / `skip_inventory_hosts` / `skip_inventory_groups`.

Filenames use **names only** (`omit_id: true` in the export playbooks).

---

### Example A — Job Template

Scenario: promote JT `Deploy App` from PRE to PRO. Organization on PRE is `AppTeam`.

#### A.1 Export from PRE

```console
ansible-playbook playbooks/export_job_template_related.yml \
  -e aap_hostname=aap-pre.example.com \
  -e aap_username=admin \
  -e aap_password='***' \
  -e aap_validate_certs=false \
  -e '{"job_template_name":"Deploy App"}' \
  -e output_path=/tmp/jt_deploy_app_export
```

> **Names with spaces:** Ansible's plain `-e key=value` form truncates at the first space
> (`-e job_template_name='Deploy App'` becomes `Deploy`). Use JSON extra vars as above,
> or a vars file (`-e @export_vars.yml`).

Optional: limit API scope with `-e organization_filter=AppTeam`.

#### A.2 Example output tree

```text
/tmp/jt_deploy_app_export/
├── env_variables.yml
├── controller_credential_types.yaml          # if custom types were needed
├── controller_execution_environments.yaml
├── AppTeam/
│   ├── controller_organizations.d/
│   │   └── AppTeam.yaml
│   ├── controller_projects.d/
│   │   └── app-repo.yaml
│   ├── controller_inventories.d/
│   │   └── App Inventory.yaml
│   ├── controller_inventory_sources.d/       # if present
│   ├── controller_hosts.d/                   # if present
│   ├── controller_groups.d/                  # if present
│   ├── controller_credentials.d/
│   │   └── scm- cred.yaml
│   ├── controller_labels.d/
│   ├── controller_notification_templates.d/
│   ├── controller_job_templates.d/
│   │   └── Deploy App.yaml
│   └── controller_schedules.d/
```

Exported YAML references related objects **by name**, for example:

```yaml
---
controller_templates:
  - name: "Deploy App"
    organization: "AppTeam"
    project: "app-repo"
    inventory: "App Inventory"
    playbook: "deploy.yml"
    scm_branch: "{{ vaulted_controller_job_templates_deploy_app_scm_branch }}"
    credentials:
      - "scm-cred"
    execution_environment: "Default execution environment"
...
```

```yaml
---
controller_projects:
  - name: "app-repo"
    organization: "AppTeam"
    scm_type: "git"
    scm_url: "{{ vaulted_controller_projects_app_repo_scm_url }}"
    scm_branch: "{{ vaulted_controller_projects_app_repo_scm_branch }}"
    scm_credential: "scm-cred"
...
```

#### A.3 Fill PRO values (`env_variables.yml`)

After export, `/tmp/jt_deploy_app_export/env_variables.yml` looks like:

```yaml
---
# Stub of environment / secret variables discovered in the filetree export.
vaulted_controller_credentials_scm_cred_password: CHANGE_ME
vaulted_controller_job_templates_deploy_app_scm_branch: CHANGE_ME
vaulted_controller_projects_app_repo_scm_branch: CHANGE_ME
vaulted_controller_projects_app_repo_scm_url: CHANGE_ME
```

Edit for PRO (example):

```yaml
---
vaulted_controller_credentials_scm_cred_password: "pro-scm-token"
vaulted_controller_job_templates_deploy_app_scm_branch: "main"
vaulted_controller_projects_app_repo_scm_branch: "main"
vaulted_controller_projects_app_repo_scm_url: "https://git.example.com/app/repo.git"
```

Optionally encrypt:

```console
ansible-vault encrypt /tmp/jt_deploy_app_export/env_variables.yml
```

#### A.4 Import into PRO

```console
ansible-playbook playbooks/import_filetree.yml \
  -e aap_hostname=aap-pro.example.com \
  -e aap_username=admin \
  -e aap_password='***' \
  -e aap_validate_certs=false \
  -e dir_orgs_vars=/tmp/jt_deploy_app_export \
  -e filetree_create_layout=true \
  -e @/tmp/jt_deploy_app_export/env_variables.yml
```

If the file is vault-encrypted, add `--ask-vault-pass` (or `--vault-password-file`).

`filetree_create_layout=true` makes `filetree_read` search the export tree as produced by `filetree_create` (no need to rearrange into `env/common` vs `env/<env>` first).

---

### Example B — Workflow Job Template

Scenario: promote WFJT `Release Pipeline` from PRE to PRO. Nodes reference JTs `Build` and `Deploy App` (plus an approval node).

#### B.1 Export from PRE

```console
ansible-playbook playbooks/export_workflow_job_template_related.yml \
  -e aap_hostname=aap-pre.example.com \
  -e aap_username=admin \
  -e aap_password='***' \
  -e aap_validate_certs=false \
  -e '{"workflow_job_template_name":"Release Pipeline"}' \
  -e output_path=/tmp/wfjt_release_pipeline_export
```

This exports the WFJT **and**, for each node whose `unified_job_type` is `job`, the Job Template with its **full related set** (same cascade as Example A).

#### B.2 Example output tree

```text
/tmp/wfjt_release_pipeline_export/
├── env_variables.yml
├── controller_execution_environments.yaml
├── AppTeam/
│   ├── controller_organizations.d/
│   ├── controller_projects.d/              # from Build + Deploy App
│   ├── controller_inventories.d/
│   ├── controller_credentials.d/
│   ├── controller_labels.d/
│   ├── controller_notification_templates.d/  # may include approval notifications
│   ├── controller_job_templates.d/
│   │   ├── Build.yaml
│   │   └── Deploy App.yaml
│   ├── controller_workflow_job_templates.d/
│   │   └── Release Pipeline.yaml
│   └── controller_schedules.d/
```

Workflow YAML references nodes and templates **by name**:

```yaml
---
controller_workflows:
  - name: "Release Pipeline"
    organization: "AppTeam"
    simplified_workflow_nodes:
      - identifier: "build"
        unified_job_template: "Build"
        workflow_job_template: "Release Pipeline"
        organization: "AppTeam"
        success_nodes:
          - "approve"
      - identifier: "approve"
        approval_node:
          name: "Approve release"
          description: ""
          timeout: 0
        workflow_job_template: "Release Pipeline"
        organization: "AppTeam"
        success_nodes:
          - "deploy"
      - identifier: "deploy"
        unified_job_template: "Deploy App"
        inventory: "App Inventory"
        workflow_job_template: "Release Pipeline"
        organization: "AppTeam"
    notification_templates_approvals:
      - "Release Approvers Mail"
...
```

#### B.3 Fill PRO values

Same pattern as the JT example: edit `/tmp/wfjt_release_pipeline_export/env_variables.yml` (all `vaulted_*` keys discovered from the WFJT **and** nested JTs/projects/credentials), then optionally vault-encrypt.

#### B.4 Import into PRO

```console
ansible-playbook playbooks/import_filetree.yml \
  -e aap_hostname=aap-pro.example.com \
  -e aap_username=admin \
  -e aap_password='***' \
  -e aap_validate_certs=false \
  -e dir_orgs_vars=/tmp/wfjt_release_pipeline_export \
  -e filetree_create_layout=true \
  -e @/tmp/wfjt_release_pipeline_export/env_variables.yml
```

---

### Notes

- Prefer **names** (`job_template_name`, `workflow_job_template_name`, `organization_filter`) over numeric `*_id` variables.
- Re-run export after changing related objects on PRE; re-fill any new keys in `env_variables.yml`.
- Approval nodes are described inline in the WFJT YAML; they do not create separate Controller objects to export.
- Nested workflow nodes (`unified_job_type: workflow_job`) are followed recursively until Job Template
  (or approval) leaves are reached (lookup ``infra.aap_configuration_extended.workflow_related_graph``).
  Every nested Workflow Job Template on the path is exported, and every discovered Job Template is
  exported with its full related set. Cycles are skipped.
- Job nodes (`unified_job_type: job`) cascade each Job Template with its full related set.
- Nested workflow nodes (`unified_job_type: workflow_job`) are exported as Workflow Job Template
  objects (by name) without recursively cascading their related set (avoids cycles). Re-run related
  export on those nested workflows if you need their full dependency tree (and their `env_variables.yml` keys).
- Job nodes (`unified_job_type: job`) still cascade each Job Template with its full related set.
- If `env_variables.yml` has no keys, the export had no `vaulted_*` placeholders (for example a WFJT whose
  nodes are only nested workflows). Export those nested workflows (or a JT) with related objects enabled.
- If `yaml_format` warns about missing PyYAML, the export files are still valid; install PyYAML for
  the configured `interpreter_python`, or use `--skip-tags yaml_format`.
- See also playbooks: `export_job_template_related.yml`, `export_workflow_job_template_related.yml`, `import_filetree.yml`.

## License

GPLv3+

## Author Information

- [Ivan Aragonés](https://github.com/ivarmu)
