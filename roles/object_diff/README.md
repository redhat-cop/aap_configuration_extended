# infra.aap_configuration_extended.object_diff

An ansible role to manage the object diff of the AWX or Automation Controller configuration. This role leverage the controller_object_diff.py lookup plugin of the infra.aap_configuration_extended, comparing two lists, one taken directly from the API and the other one from the git repository, and it could be used to delete objects in the AWX or Automation Controller that are not defined in the git repository list.

## Requirements

`ansible-galaxy collection install -r tests/collections/requirements.yml` to be installed. Currently: `infra.aap_configuration`, `ansible.platform` and `ansible.hub`.

## Role Variables

### Organization and Environment Variables

The following Variables set the organization where should be applied the configuration, the absolute or relative of the directory structure where the variables will be stored and the life-cycle environment to use.

| Variable Name | Default Value | Required | Description |
| :------------ | :-----------: | :------: | :---------- |
| `drop_user_external_accounts` | `False` | no | When is true, all users will be taken to compare with SCM configuration as code |
| `protect_not_empty_orgs` | `N/A` | no | When is true, orgs which are not empty, will not be removed |
| `query_controller_api_max_objects` | 10000 | no | Sets the maximum number of objects to be returned from the API |
<!--- | `drop_teams` | `False` | no | When is true, all teams will be taken to compare with SCM configuration as code | -->

## Role Tags

The role is designed to be used with tags; each tag corresponds to an AWX or Automation Controller object type managed by this role. The default task list is defined in `defaults/main.yml` as `controller_configuration_object_diff_tasks`.

> :warning: Object types managed by this role: `controller_applications`, `controller_credentials`, `controller_credential_types`, `controller_execution_environments`, `controller_host_groups`, `controller_hosts`, `controller_instance_groups`, `controller_inventories`, `controller_inventory_sources`, `controller_job_templates`, `controller_notification_templates`, `controller_organizations`, `controller_projects`, `controller_roles`, `controller_schedules`, `controller_teams`, `controller_users`, `controller_workflow_job_templates`.

```bash
$ ansible-playbook object_diff.yml --list-tags
      TASK TAGS: [always, controller_applications, controller_credentials, controller_credential_types, controller_execution_environments, controller_host_groups, controller_hosts, controller_instance_groups, controller_inventories, controller_inventory_sources, controller_job_templates, controller_notification_templates, controller_organizations, controller_projects, controller_roles, controller_schedules, controller_teams, controller_users, controller_workflow_job_templates]
```

## IMPORTANT

To correctly manage `roles`, they can only be defined by a super-admin organization, so all the roles in the Ansible Controller instance are managed by only one organization.

## Workflow Job Template nodes

`object_diff` compares **Workflow Job Templates as whole objects** (typically by name and organization). It does **not** compare or mark individual workflow nodes as `state: absent`.

If a Workflow Job Template still exists in both the Controller API and your CaC list, but you removed one or more nodes from the YAML definition, `__workflow_job_templates_difference` will stay empty for that template. That is expected: the template itself is still present in code.

To remove nodes that exist in AAP but are no longer defined in CaC, set `destroy_current_nodes: true` on the workflow (or rely on the equivalent option in `infra.aap_configuration.controller_workflow_job_templates`) when applying configuration via `dispatch`. See the [controller_workflow_job_templates role documentation](https://github.com/redhat-cop/infra.aap_configuration/blob/devel/roles/controller_workflow_job_templates/README.md) for details.

Example:

```yaml
controller_workflows:
  - name: My Workflow
    organization: Default
    destroy_current_nodes: true
    workflow_nodes:
      - identifier: node_a
        unified_job_template: Job Template A
        success_nodes:
          - node_b
      - identifier: node_b
        unified_job_template: Job Template B
```

Related: [issue #149](https://github.com/redhat-cop/aap_configuration_extended/issues/149).

## Example Playbook

```yaml
---
- hosts: localhost
  connection: local
  gather_facts: false
  vars:
    aap_username: "{{ vault_aap_username | default(lookup('env', 'CONTROLLER_USERNAME')) }}"
    aap_password: "{{ vault_aap_password | default(lookup('env', 'CONTROLLER_PASSWORD')) }}"
    aap_hostname: "{{ vault_aap_hostname | default(lookup('env', 'CONTROLLER_HOST')) }}"
    controller_validate_certs: "{{ vault_controller_validate_certs | default(lookup('env', 'CONTROLLER_VERIFY_SSL')) }}"

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
            aap_validate_certs: "{{ aap_validate_certs | default(controller_validate_certs) }}"

        - name: "Expose aap_token dict for collection roles"
          ansible.builtin.set_fact:
            aap_token: "{{ ansible_facts['aap_token'] }}"
      no_log: "{{ controller_configuration_object_diff_secure_logging }}"
      when: not (ansible_facts.get('aap_token') or aap_token is defined)
      tags:
        - always

  roles:
    - role: infra.aap_configuration_extended.filetree_read
    - role: infra.aap_configuration_extended.object_diff
    - role: infra.aap_configuration.dispatch
      vars:
        controller_configuration_dispatcher_roles:
          - {role: controller_schedules, var: controller_schedules, tags: controller_schedules}
          - {role: controller_workflow_job_templates, var: controller_workflows, tags: controller_workflow_job_templates}
          - {role: controller_job_templates, var: controller_templates, tags: controller_job_templates}
          - {role: controller_roles, var: controller_roles, tags: controller_roles}
          - {role: controller_teams, var: aap_teams, tags: controller_teams}
          - {role: controller_users, var: aap_user_accounts, tags: controller_users}
          - {role: controller_host_groups, var: controller_groups, tags: controller_host_groups}
          - {role: controller_hosts, var: controller_hosts, tags: controller_hosts}
          - {role: controller_applications, var: aap_applications, tags: controller_applications}
          - {role: controller_execution_environments, var: controller_execution_environments, tags: controller_execution_environments}
          - {role: controller_inventory_sources, var: controller_inventory_sources, tags: controller_inventory_sources}
          - {role: controller_inventories, var: controller_inventories, tags: controller_inventories}
          - {role: controller_projects, var: controller_projects, tags: controller_projects}
          - {role: controller_notification_templates, var: controller_notifications, tags: controller_notification_templates}
          - {role: controller_credentials, var: controller_credentials, tags: controller_credentials}
          - {role: controller_credential_types, var: controller_credential_types, tags: controller_credential_types}
          - {role: controller_organizations, var: aap_organizations, tags: controller_organizations}
          - {role: controller_instance_groups, var: controller_instance_groups, tags: controller_instance_groups}

  post_tasks:
    - name: "Delete the Authentication Token used"
      ansible.platform.token:
        existing_token: "{{ aap_token }}"
        state: absent
        aap_hostname: "{{ aap_hostname }}"
        aap_username: "{{ aap_username }}"
        aap_password: "{{ aap_password }}"
        aap_validate_certs: "{{ aap_validate_certs | default(controller_validate_certs) }}"
      when:
        - aap_token is defined
        - aap_token is mapping
```

```bash
ansible-playbook drop_diff.yml --tags ${CONTROLLER_OBJECT} -e "{orgs: ${ORGANIZATION}, dir_orgs_vars: orgs_vars, env: ${ENVIRONMENT} }" --vault-password-file ./.vault_pass.txt -e @orgs_vars/env/${ENVIRONMENT}/configure_connection_controller_credentials.yml ${OTHER}
```

## License

GPLv3+

## Author Information

- [Silvio Perez](https://github.com/silvinux)

- [Ivan Aragonés](https://github.com/ivarmu)

- [Adonis García](https://github.com/adonisgarciac)

## Important things to take into account

- Issues:
  - Users and Teams must be managed by users with privileges.
  - Due to the Team Object doesn't return from API any field related to external account on Controller API, which help to filter if the teams comes from an External Source and not to be deleted by the Object Diff Ansible automation process.
  - Workflow Job Template **nodes** are outside the scope of `object_diff`. Removing a node from CaC does not produce an absent entry in `__workflow_job_templates_difference`; use `destroy_current_nodes: true` when applying the workflow (see [Workflow Job Template nodes](#workflow-job-template-nodes)).
