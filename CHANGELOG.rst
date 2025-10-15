================================================
infra.aap\_configuration\_extended Release Notes
================================================

.. contents:: Topics

v3.0.2
======

Bugfixes
--------

- Fix default value for webhook_service in workflow job templates
- Fix verbosity key in workflow job templates
- Upgraded offline_sync to work with AAP 2.5+
- upgrade_config fix the names of the variables in the generated files

v3.0.1
======

Bugfixes
--------

- Fix the issues detected in the last import log (galaxy)

v3.0.0
======

Major Changes
-------------

- Remove controller_api_plugin and controller_role_plugin variables in favour of ansible.platform.gateway_api and infra.aap_configuration_extended.controller_object_diff

Minor Changes
-------------

- Export PAH objects.
- Fix the markdown errors for the CI to work properly

Bugfixes
--------

- Fixes a bug where a survey option's default choice wasn't included in the choice list
- Fixes an issue with the filetree_create role adding a '...' separate between each item in the job templates list flatten output is set to true.

v2.0.0
======

Major Changes
-------------

- New role to update Configuration as Code files from 2.4 (infra.controller_configuration) format to 2.5 (infra.aap_configuration_extended)
- Remove controller_api_plugin and eda_api_plugin variables in favour of ansible.platform.gateway_api

Minor Changes
-------------

- Let the sensitive data of the credentials and users to be defined externally through a well know variables
- Use correct API endpoint when connecting to AAP 2.5 when determining super user privileges

Breaking Changes / Porting Guide
--------------------------------

- Remove aap<=2.4 api endpoints and version detections in the filetree_create role

Bugfixes
--------

- Change connection variables to AAP from 'controller_*' to 'aap_*' when exporting the 'inventory_sources'.
- Fix the exported contents of survey's choices in workflow job templates to avoid to have the clause '!unsafe' inside the generated string.
- Set the correct API URL for the controller applications endpoint
- There was a format error in the output after each key occurence. The template has been fixed.
- There was an indentation error in the output at the `inputs` and `injectors` sections. The template has been fixed.
- There was an indentation error in the output at the `inputs` and `injectors` sections. The template has been fixed.

v1.1.1
======

Bugfixes
--------

- object_diff adapt object diff api calls to fit with AAP 2.5 api changes. It means to use api/controller or api/gateway for each particular case.

v1.1.0
======

Minor Changes
-------------

- Add a filter to allow exporting the Job Templates based on an assigned label
- Updated linting rules to mock infra.aap_configuration collection

Bugfixes
--------

- BREAKING - filetree_read default var updated to align with new aap_users — may break old user definitions if they're using default path for users definition.
- Fix the organization ID variable used to look for the organization name of the current decision environment
- Fix the wrong variable path used at inventory_sources to access the source_project field
- Set the lookup plugin in filetree_create to use the ansible.platform.gateway_api plugin to capture the AAP version
- filetree_create no longer has issue with backslashes in survey and extra vars
- filetree_create no longer has issue with strings like 123-123-123 in survey and extra vars
- fix a truthy value at the survey for the workflow job templates. Set it to lowercase.

v1.0.0
======

Major Changes
-------------

- filetree_create is able to use external dictionary to modify object during the export

Minor Changes
-------------

- Add credential_input_sources to the filetree create
- Constructed inventories now produce an inventory source which can be used to control items such as limit and source_vars for the constructed inventory
- filetree_create able to export single inventory
- filetree_create is able to export approval node of workflow
- filetree_create is able to export inventory without sources/hosts/groups.
- filetree_create is able to export variables without key sorting
- filetree_create projects bool variables are stored without quotes
- filetree_create should not export hosts of smart/constructed inventories as they are based on existing inventories
- filetree_create should use plural inventories word instead of singular inventory

Bugfixes
--------

- Add input_inventories to the output of Constructed Inventories.
- Add instance_groups to the output of Constructed Inventories.
- Fixes issue where the input tags were not accepted or being skipped
- filetree_create - Corrected th4e following vars; controller_hostname, controller_oauthtoken, and controller_validate_certs
- filetree_create export inventories source vars with proper indention
- filetree_create export missing inventory ask settings of workflows
- filetree_create export missing inventory for workflow node
- filetree_create export missing limit of workflow nodes
- filetree_create export missing limits settings of workflows
- filetree_create export missing verbosity for node
- filetree_create export verbosity for node when ask_verbosity_on_launch is defined
- filetree_create exported properly smart inventories host filter (double quotes issue)
- filetree_create extra_vars regex issue
- filetree_create fix wrong object type name in user roles template
- filetree_create is able to export empty extra vars of JT and WF
- filetree_create job_template and workflow_job_template issues with complex fields
- filetree_create job_template and workflow_job_template survey default values issue when they are multiline
- filetree_create job_template and workflow_job_template survey issue when the survey_spec was empty (but defined)
- filetree_create job_template and workflow_job_template survey was failing when it was empty
- filetree_create job_template double quote issue
- filetree_create missing single quotes for hostfilter in smart inventories
- filetree_create no longer export schedules extra data when extra_vars of job template is empty (null issue)
- filetree_create properly escape every variable with unsafe
- filetree_create remove state from workflow job templates output to avoid problems when importing those files
- filetree_create roles export issue
- filetree_create roles export issues introduced by PR
- filetree_create use proper global template variable name
- fix empty and malformed file for credential_types

v0.1.0
======

Major Changes
-------------

- Adds Configuration as Code filetree_create - A role to export and convert all  Controller's objects configuration in yaml files to be consumed with previous roles.
- Adds Configuration as Code filetree_read role - A role to load controller variables (objects) from a hierarchical and scalable directory structure.
- Adds Configuration as Code object_diff role - A role to get differences between code and controller. It will give us the lists to remove absent objects in the controller which they are not in code.

Minor Changes
-------------

- Adds credential and organization options for schedule role.
- inventory_sources - update ``source_vars`` to parse Jinja variables using the same workaround as inventories role.
