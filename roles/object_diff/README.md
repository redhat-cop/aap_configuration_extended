# controller_configuration.object_diff

An ansible role to manage the object diff of the AWX or Automation Controller configuration. This role leverage the controller_object_diff.py lookup plugin of the infra.controller_configuration, comparing two lists, one taken directly from the API and the other one from the git repository, and it could be used to delete objects in the AWX or Automation Controller that are not defined in the git repository list.

## Requirements

`ansible-galaxy collection install -r tests/collections/requirements.yml` to be installed. Currently: `infra.controller_configuration`, `ansible.platform` and `ansible.hub`.

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

The role is designed to be used with tags, each tags correspond to an AWX or Automation Controller object to be managed by ansible.

> :warning: List of object type managed by this role: controller_credentials, controller_credential_types, controller_host_groups, controller_hosts, controller_inventories, controller_inventory_sources, controller_job_templates, controller_organizations, controller_projects, controller_teams, controller_users, controller_workflow_job_templates.

```bash
$ ansible-playbook object_diff.yml --list-tags
      TASK TAGS: [controller_credentials, controller_credential_types, controller_host_groups, controller_hosts, controller_inventories, controller_inventory_sources, controller_job_templates, controller_organizations, controller_projects, controller_teams, controller_users, controller_workflow_job_templates]
```

## IMPORTANT

To correctly manage `roles`, they can only be defined by a super-admin organization, so all the roles in the Ansible Controller instance are managed by only one organization.

## Example Playbook

```bash
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
        - name: "Get the Authentication Token for the future requests"
          ansible.builtin.uri:
            url: "https://{{ aap_hostname }}/api/gateway/v1/tokens/"
            user: "{{ aap_username }}"
            password: "{{ aap_password }}"
            method: POST
            force_basic_auth: true
            validate_certs: "{{ controller_validate_certs }}"
            status_code: 201
          register: authtoken_res

        - name: "Set the oauth token to be used since now"
          ansible.builtin.set_fact:
            aap_oauthtoken: "{{ authtoken_res.json.token }}"
            aap_oauthtoken_url: "{{ authtoken_res.json.url }}"
      no_log: "{{ controller_configuration_object_diff_secure_logging }}"
      when: aap_oauthtoken is not defined
      tags:
        - always

  roles:
    - role: infra.aap_configuration_extended.filetree_read
    - role: infra.aap_configuration_extended.object_diff
      vars:
        controller_configuration_object_diff_tasks:
          - {name: controller_workflow_job_templates, var: controller_workflows, tags: controller_workflow_job_templates}
          - {name: controller_job_templates, var: controller_templates, tags: controller_job_templates}
          - {name: controller_user_accounts, var: aap_user_accounts, tags: controller_users}
          - {name: controller_host_groups, var: controller_groups, tags: controller_host_groups}
          - {name: controller_hosts, var: controller_hosts, tags: controller_hosts}
          - {name: controller_inventory_sources, var: controller_inventory_sources, tags: controller_inventory_sources}
          - {name: controller_inventories, var: controller_inventories, tags: controller_inventories}
          - {name: controller_projects, var: controller_projects, tags: controller_projects}
          - {name: controller_credentials, var: controller_credentials, tags: controller_credentials}
          - {name: controller_credential_types, var: controller_credential_types, tags: controller_credential_types}
          - {name: controller_organizations, var: aap_organizations, tags: controller_organizations}
    - role: infra.aap_configuration_extended.dispatch
      vars:
        controller_configuration_dispatcher_roles:
          - {role: controller_workflow_job_templates, var: controller_workflows, tags: controller_workflow_job_templates}
          - {role: controller_job_templates, var: controller_templates, tags: controller_job_templates}
          - {role: controller_users, var: aap_user_accounts, tags: controller_users}
          - {role: controller_host_groups, var: controller_groups, tags: controller_host_groups}
          - {role: controller_hosts, var: controller_hosts, tags: controller_hosts}
          - {role: controller_inventory_sources, var: controller_inventory_sources, tags: controller_inventory_sources}
          - {role: controller_inventories, var: controller_inventories, tags: controller_inventories}
          - {role: controller_projects, var: controller_projects, tags: controller_projects}
          - {role: controller_credentials, var: controller_credentials, tags: controller_credentials}
          - {role: controller_credential_types, var: controller_credential_types, tags: controller_credential_types}
          - {role: controller_organizations, var: aap_organizations, tags: controller_organizations}

  post_tasks:
    - name: "Delete the Authentication Token used"
      ansible.builtin.uri:
        url: "https://{{ aap_hostname }}{{ aap_oauthtoken_url }}"
        user: "{{ aap_username }}"
        password: "{{ aap_password }}"
        method: DELETE
        force_basic_auth: true
        validate_certs: "{{ controller_validate_certs }}"
        status_code: 204
      when: aap_oauthtoken_url is defined

$ ansible-playbook drop_diff.yml --tags ${CONTROLLER_OBJECT} -e "{orgs: ${ORGANIZATION}, dir_orgs_vars: orgs_vars, env: ${ENVIRONMENT} }" --vault-password-file ./.vault_pass.txt -e @orgs_vars/env/${ENVIRONMENT}/configure_connection_controller_credentials.yml ${OTHER}
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
