# controller_configuration.filetree_create

The role `filetree_create` is intended to be used as the first step to begin using the Configuration as Code on Ansible Tower or Ansible Automation Platform, when you already have a running instance of any of them. Obviously, you also could start to write your objects as code from scratch, but the idea behind the creation of that role is to simplify your lives and make that task a little bit easier.

## Requirements

* for Red Hat Ansible Automation Platform >= 2.5, collections:
  * [ansible.controller](https://console.redhat.com/ansible/automation-hub/repo/published/ansible/controller), and
  * [ansible.platform](https://console.redhat.com/ansible/automation-hub/repo/published/ansible/platform/)

## Role Variables

The following variables are required for that role to work properly:

| Variable Name | Default Value | Required | Type | Description |
| :------------ | :-----------: | :------: | :------: | :---------- |
| `organization_filter` | N/A | no | str | Exports only the objects belonging to the specified organization (applies to all the objects that can be assigned to an organization). |
| `organization_id` | N/A | no | int | Alternative to `organization_filter`, but specifiying the current organization's ID to filter by. Exports only the objects belonging to the specified organization (applies to all the objects that can be assigned to an organization). |
| `project_id` | N/A | no | int | Specifiying the project id to filter by. Exports the project belonging to the specified organization. |
| `job_template_id` | N/A | no | int | Specifiying the job template id to filter by. Exports the job template belonging to the specified organization. |
| `label_filter` | N/A | no | str | Specifiying a label to filter the job templates by. Exports all the job templates having the specified label assigned. |
| `inventory_id` | N/A | no | int | Specifiying the inventory id to filter by. Exports the inventory belonging to the specified organization. |
| `workflow_job_template_id` | N/A | no | int | Specifiying the workflow job template id to filter by. Exports the workflow job template belonging to the specified organization. |
| `schedule_id` | N/A | no | int | Specifiying the schedule id to filter by. Exports the schedule belonging to the specified object. |
| `output_path` | `/tmp/filetree_output` | yes | str | The path to the output directory where all the generated `yaml` files with the corresponding Objects as code will be written to. |
| `input_tag` | `['all']` | no | List of Strings | The tags which are applied to the 'sub-roles'. If 'all' is in the list (the default value) then all roles will be called.  Valid tags can be found under `vars/valid_tags` |
| `flatten_output` | N/A | no | bool | Whether to flatten the output in single files per each object type instead of the normal exportation structure |
| `show_encrypted` | N/A | no | bool | Whether to remove the string '\$encrypted\$' in credentials output (not the actual credential value) |
| `omit_id` | N/A | no | bool | Whether to create output files without objects id.|
| `organization`| N/A | no | str | Default organization for all objects that have not been set in the source controller.|
| `export_related_objects` | False | no | bool | Whether to export related objects (job templates related to certain workflows and the projects associated with these job templates) when a single JT or a single WFJT are being exported. |
| `update_project_state` | False | no | bool | Whether the project should be updated after import to the target controller. |
| `skip_inventory_sources` | False | no | bool | Whether the inventory sources should be exported with inventory. |
| `skip_inventory_hosts` | False | no | bool | Whether the inventory hosts should be exported with inventory. |
| `skip_inventory_groups` | False | no | bool | Whether the inventory groups should be exported with inventory. |
| `templates_overrides_resources`| N/A | no | dict | Whether the certain objects should be modified during the export |
| `templates_overrides_global`| N/A | no | dict | Whether the all objects should be modified during the export |

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
        - name: "Get the Authentication Token for the future requests"
          ansible.builtin.uri:
            url: "https://{{ aap_hostname }}/api/gateway/v1/tokens/"
            user: "{{ aap_username }}"
            password: "{{ aap_password }}"
            method: POST
            force_basic_auth: true
            validate_certs: "{{ aap_validate_certs }}"
            status_code: 201
          register: authtoken_res

        - name: "Set the oauth token to be used since now"
          ansible.builtin.set_fact:
            aap_oauthtoken: "{{ authtoken_res.json.token }}"
            aap_oauthtoken_url: "{{ authtoken_res.json.url }}"
      no_log: "{{ controller_configuration_filetree_create_secure_logging | default('false') }}"
      when: aap_oauthtoken is not defined
      tags:
        - always

  roles:
    - infra.aap_configuration_extended.filetree_create

  post_tasks:
    - name: "Delete the Authentication Token used"
      ansible.builtin.uri:
        url: "https://{{ aap_hostname }}{{ aap_oauthtoken_url }}"
        user: "{{ aap_username }}"
        password: "{{ aap_password }}"
        method: DELETE
        force_basic_auth: true
        validate_certs: "{{ aap_validate_certs }}"
        status_code: 204
      when: aap_oauthtoken_url is defined
...
```

This role can generate output files in two different ways:

* **Structured output**:

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

* **Flatten files**:

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

* job template called `job_template_example` will be exported with the `dev` branch, while the rest of the job templates will use the `main` branch — the resources dictionary takes precedence over the global dictionary.
* all projects will have a Jinja2 expression assigned to the `scm_branch`.
* all schedules enabled state will be set as `false`.

```yaml
---
- hosts: all
  connection: local
  gather_facts: false
  vars:
    aap_username: "{{ vault_aap_username | default(lookup('env', 'CONTROLLER_USERNAME')) }}"
    aap_oauthtoken : "{{ vault_aap_password | default(lookup('env', 'CONTROLLER_OAUTHTOKEN')) }}"
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

## License

GPLv3+

## Author Information

* [Ivan Aragonés](https://github.com/ivarmu)
