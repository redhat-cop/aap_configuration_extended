================================================
infra.aap\_configuration\_extended Release Notes
================================================

.. contents:: Topics

v4.10.0
=======

Minor Changes
-------------

- Add collection filter ``infra.aap_configuration_extended.filetree_as_var`` and document JSON ``-e`` usage for object names that contain spaces.
- Add playbooks ``export_job_template_related.yml``, ``export_workflow_job_template_related.yml``, and ``import_filetree.yml`` for PRE→PRO migration (name-based).
- Added lookup plugin ``infra.aap_configuration_extended.workflow_related_graph`` (uses the ansible.platform Gateway client) so nested WFJT discovery is not embedded Python in role tasks.
- aap-config-validate - Accept Ansible-quoted scalars (``"0"``, ``"false"``, ``"{}"``), treat empty strings as unset, and skip extra required fields when ``state: absent``.
- aap-config-validate - Recognise filetree and template aliases (``gateway_organizations``, ``controller_user_accounts``, ``controller_templates_all``, …) and merge env-suffixed vars in ``auto`` mode when those suffixes are present.
- aap-config-validate - Report the source YAML file on each issue; deep-merge dicts across files; match nested ``exclude_dirs`` paths such as ``tests/fixtures``.
- aap_config_vars - Add a module and action plugin that loads AAP configuration-as-code vars from ``config/all`` and ``config/<env>``, optionally keeping only objects that changed in git for use with ``infra.aap_configuration.dispatch``.
- docs - Clarify that ``filetree_create`` is the supported way to capture existing AAP objects as Configuration as Code, including name filters and remaining gaps (related to redhat-cop/aap_configuration_extended#110).
- filetree_create - Add ``env_fields_as_variables`` to export curated environment-specific fields as Ansible variable placeholders, and generate an ``env_variables.yml`` stub for PRE→PRO workflows.
- filetree_create - Add ``job_template_name`` / ``workflow_job_template_name`` and other ``*_name`` filters; prefer names over numeric IDs for Configuration as Code.
- filetree_create - Add optional ``export_inline_object_roles`` to embed ``infra.aap_configuration`` inline object ``roles`` (users/teams) on inventories, projects, job templates, workflow job templates, credentials, and instance groups (fixes redhat-cop/aap_configuration_extended#311).
- filetree_create - Document ``ansible.platform.token`` and passing the returned token dict as ``aap_token`` in README and test playbooks.
- filetree_create - Expand ``export_related_objects`` for Job Templates and Workflow Job Templates to export related Controller objects by **object name** (organization, inventory, credentials, credential types, execution environments, labels, notification templates, schedules; WFJT also exports each node JT with its related set).
- filetree_create - Export gateway role team assignments (``gateway_role_team_assignments``) by name, mirroring user assignments export (fixes
- filetree_create - Export nested Workflow Job Template nodes by name; make ``yaml_format`` non-fatal when PyYAML is missing for the configured interpreter.
- filetree_create - Use ``aap_token`` for API authentication (``aap_oauthtoken`` retained as deprecated string alias; fixes redhat-cop/aap_configuration_extended#266).
- filetree_create - When exporting a Workflow Job Template with ``export_related_objects``, walk nested workflow nodes recursively until Job Template leaves, export every nested WFJT on the path, and export each discovered Job Template with its full related set (with cycle detection).
- filetree_read - Accept both short and prefixed Ansible tags (matching ``infra.aap_configuration.dispatch``) and add ``filetree_gateway_*`` path aliases that also search legacy ``aap_*`` and ``filetree_create`` output directories (fixes redhat-cop/aap_configuration_extended#267).
- object_diff - Document that Workflow Job Template node removal is not handled by object_diff and requires ``destroy_current_nodes: true`` on ``infra.aap_configuration.controller_workflow_job_templates`` (fixes documentation gap for redhat-cop/aap_configuration_extended#149).
- object_diff - Use ``aap_token`` for API authentication (``aap_oauthtoken`` retained as deprecated alias).
- object_diff, filetree_read - Migrate test playbooks and README examples from ``ansible.builtin.uri`` to ``ansible.platform.token``.

Bugfixes
--------

- Bump pre-commit changelog hook to v26.8.1 so fragment YAML is linted as strictly as release.
- CI - approval-gate accepts ci-approved label and waits for populate-collections-cache before running tests
- CI - populate Ansible collections cache in the trusted pre-commit approval workflow (with Automation Hub secrets); pre-commit-tests only restores the cache
- CI - restore pull-requests write permission on approval labeling jobs so ci-approved can be applied
- CI - run sanity against an ansible_collections tree that symlinks Automation Hub deps from the trusted cache (no ade / no AH token in tests)
- Document max_retries and retry_backoff_factor on controller_export_diff so validate-modules matches ansible.controller 4.8.3 AUTH_ARGSPEC.
- Inline auth lookup documentation in ``workflow_related_graph`` so automated release changelog generation does not require ``ansible.platform`` at doc-build time.
- aap-config-validate - Do not treat ``bool`` as ``int``; do not treat known vars such as ``controller_settings_individuale`` as wildcard suffixes; ignore empty ``[]`` overlays on dict-form settings.
- aap-config-validate - Keep organization names in the cross-reference index when ``--component controller`` is used.
- auto-approve trusted collaborator PRs when .github workflows are unchanged; require manual approval for external contributors or workflow edits
- compute the Ansible collections cache key in cache steps instead of job env, because hashFiles is not available in jobs.<job_id>.env
- filetree_create - Add attributes to the workflow jinja2 template (ask_tags_on_launch, ask_skip_tags_on_launch, job_tags, skip_tags, ask_labels_on_launch, ask_scm_branch_on_launch)
- filetree_create - Apply ``organization_filter`` to gateway teams, gateway authenticator maps, and controller schedules. Fixes #312.
- filetree_create - Avoid ansible-core task-name templating warnings by not referencing the loop variable in the organizations output-directory task name (path remains in the loop label).
- filetree_create - Document ``*_secure_logging`` role variables in the README and align defaults with ``aap_configuration_secure_logging`` (with legacy ``controller_configuration_secure_logging`` fallback) (fixes redhat-cop/aap_configuration_extended#304).
- filetree_create - Export YAML with native types (booleans, integers, floats, dicts, lists) instead of quoted strings across settings, authenticators, workflow extra_data, hub objects, and related templates via shared Jinja macros (fixes redhat-cop/aap_configuration_extended#203).
- filetree_create - Export ``AUTOMATION_ANALYTICS_LAST_ENTRIES`` when the API returns Python dict strings instead of JSON.
- filetree_create - Export ``AWX_ANSIBLE_CALLBACK_PLUGINS`` and ``DEFAULT_EXECUTION_ENVIRONMENT`` in controller_settings via ``template_overrides_global.controller_setting`` defaults. Fixes #342.
- filetree_create - Export ``DEFAULT_EXECUTION_ENVIRONMENT`` as ``null`` and include ``AWX_TASK_ENV`` in controller_settings defaults. Fixes #342 follow-up.
- filetree_create - Export ``enabled`` on hosts, ``overwrite_vars`` and ``execution_environment`` on inventory sources, top-level ``inventory`` on workflows, node ``credentials`` on workflow nodes, and ``organization`` on schedules. Fixes #308.
- filetree_create - Export gateway role team assignments with named ``assignment_objects`` instead of numeric ``object_id``. Follow-up to #298.
- filetree_create - Export gateway role user assignments with ``object_ids`` (resource names) instead of deprecated numeric ``object_id``. Fixes #298.
- filetree_create - Export job/workflow template ``extra_vars`` that contain only YAML comments without failing on ``dict2items`` when ``from_yaml`` returns ``None`` (fixes redhat-cop/aap_configuration_extended#321; regression from redhat-cop/aap_configuration_extended#270 after redhat-cop/aap_configuration_extended#226).
- filetree_create - Export native integers and additional fields for ``controller_instance_groups``. Fixes #339.
- filetree_create - Export organization ``max_hosts``, ``custom_virtualenv``, ``default_environment``, ``galaxy_credentials``, and ``instance_groups`` (by name) into ``aap_organizations`` alongside existing notification templates (fixes
- filetree_create - Export workflow node ``extra_data`` numeric and boolean survey values with native YAML types instead of quoted raw strings (fixes redhat-cop/aap_configuration_extended#250).
- filetree_create - Fix ``default_environment`` export for projects (was reading the wrong asset variable). Fixes #308.
- filetree_create - Fix notification template export (IRC/messages), gateway role user assignments, hub EE image tag filtering, and collection repository sync defaults.
- filetree_create - Fix stray Jinja trim markers that broke YAML export for job templates, workflows, and inventories.
- filetree_create - Guard missing ``summary_fields.resource_name`` when exporting gateway role user and team assignments.
- filetree_create - Honor ``secrets_as_variables`` when exporting ``gateway_settings`` password fields. Fixes #340.
- filetree_create - Remove single quotes escaping in description attributes when surrounded by a raw block
- filetree_create - Respect boolean ``omit_id`` value when building output filenames (``omit_id: false`` keeps numeric id prefixes; ``omit_id: true`` omits them). Fixes #302.
- filetree_create - Standardize Jinja control-tag indentation in export templates.
- filetree_create - Stop writing an empty mapping (``{}``) into ``env_variables.yml`` when no ``vaulted_*`` placeholders are found, and exclude that stub from ``yaml_format`` so comments are preserved.
- filetree_create hub_namespaces export normalizes API empty-string links to an empty list before the shared export macros decide whether to omit the field
- filetree_read - Add ``controller_configuration_filetree_read_layout`` (``hierarchical`` / ``create`` / ``flatten``) so a ``filetree_create`` export tree can be loaded by remapping ``filetree_*`` paths to ``dir_orgs_vars``. Deprecated alias ``filetree_create_layout`` (when true) still maps to ``create`` (fixes
- filetree_read - Default ``orgs`` to an empty string so argument_specs path defaults resolve under create/flatten layouts, and apply layout remap with ``apply.tags=always`` so CLI ``--tags`` runs still remap paths.
- filetree_read sanitizes hub_namespaces links and hub collection remotes or repositories empty-string fields so previously exported files import correctly
- fix invalid actions/cache commit pin that prevented cache restore and save
- gate pull_request test execution on a successful pre-commit approval workflow run for the current head SHA
- object_diff - Align ``controller_configuration_object_diff_tasks`` notification entry ``var`` with ``controller_notifications``.
- object_diff - Document all supported object tags (including notification templates, roles, schedules, applications, execution environments, and instance groups) in the role README (fixes redhat-cop/aap_configuration_extended#13).
- object_diff - Fail clearly when ``aap_user_accounts`` is empty while the Controller still has users, surface user-diff errors outside ``no_log``, and skip users missing ``associated_authenticators`` (fixes
- remove ci-approved labels now that approval completion is the gate signal
- restore Ansible collections for external PRs from a default-branch cache populated by trusted push and schedule runs
- skip sanity-py3.12-milestone because ansible-core milestone requires Python >=3.13
- split pre-commit CI into trusted approval and untrusted test workflows to avoid fork pull request checkout failures in pull_request_target
- tox-ansible - set skip_missing_interpreters so CI matrix jobs only run sanity envs for the installed Python
- wait in the pull request approval-gate job until pre-commit approval completes before running tests, instead of re-running workflows via workflow_run

New Modules
-----------

- infra.aap_configuration_extended.aap_config_vars - Load AAP configuration\-as\-code vars (optionally only changed objects)

v4.9.1
======

Bugfixes
--------

- filetree_read - Restore ``tags: always`` on the include loop so ``--tags`` filtering works when specific tags are requested.
- skip sanity-py3.12-milestone because ansible-core milestone requires Python >=3.13

v4.9.0
======

Minor Changes
-------------

- filetree_create - Widen ``to_nice_yaml`` output and use non-greedy Jinja wrapping so exported variables with ``{{ }}`` are not split across lines.
- format_yaml - Normalize YAML for ansible-lint (``yaml[truthy]``, ``yaml[document-end]``, ``yaml[indentation]``, trailing whitespace) and apply it to all files generated by filetree_create.

Bugfixes
--------

- add tox-ansible.ini to skip sanity environments that pair ansible-core devel with Python <3.13
- controller_export_diff - Added missing ``oauth_token``, ``controller_oauthtoken``, and ``tower_oauthtoken`` aliases for the ``aap_token`` parameter to match the current ``ansible.controller`` AUTH_ARGSPEC.
- filetree_create - Export controller instances to ``controller_instances.yaml`` (fixes redhat-cop/aap_configuration_extended#235).
- filetree_create - Export manually added hosts when an inventory has inventory sources (fixes redhat-cop/aap_configuration_extended#260).
- filetree_create - Export only instances with importable ``node_type`` (``execution``, ``hop``); omit ``node_state`` unless ``installed`` or ``deprovisioning``.
- filetree_create - Fix undefined ``current_organization_dir`` in ``controller_organizations.yml`` (use ``current_organization``; static task name to avoid template warnings when ``flatten_output`` skips the non-flatten block).
- filetree_create - Include every host in manually defined groups, including hosts created by inventory sources.
- filetree_create - Omit empty ``instances`` key from exported instance groups.
- filetree_create - Resolve instance ``peers`` to hostnames via receptor address and instance lookups instead of numeric IDs in exported CaC.
- filetree_create - Use ``is mapping`` / ``is string`` checks before ``from_yaml`` in export templates so ansible-core 2.23+ does not emit deprecation warnings for dict API values (for example schedule ``extra_data``).
- filetree_read - Honor ``--tags`` when including per-object task files (no longer forced by ``tags: always`` on the include loop).
- filetree_read - Load ``controller_instances`` from filetree YAML (tag ``instances``).
- fix CI workflow for Ansible Core devel version, that requires python >=3.13
- object_diff - skip object diff to mark imported hosts from a sourced inventory to be removed.
- restore a single pre-commit CI check for branch protection when using a Python matrix
- run sanity on Python 3.12, 3.13, and 3.14 in CI

v4.8.0
======

Minor Changes
-------------

- Adding a new python script that can be used to attempt to validate your configuration before attempting to apply it.

v4.7.0
======

Minor Changes
-------------

- README - Standardized collection links tables and added Support section for certification review.
- meta/runtime.yml - Updated minimum ansible-core version from 2.15 to 2.16.

Bugfixes
--------

- Fix the output of the format_yaml.py module to correctly format the output (Certificates mainly)
- Update the collection to support AAP 2.7

v4.5.0
======

Minor Changes
-------------

- Remove yq from the collection and add a new module to process the yaml files using ruamel.
- filetree_create - Add 'hub_ee_images' to the valid tags list.
- filetree_read - Add tasks to load EDA and automation hub variables from the file tree (credential types, credentials, decision environments, event streams, projects, rulebook activations; namespaces, collections, collection remotes and repositories, EE registries, repositories, and images), with defaults and argument_specs entries; document in README.

Bugfixes
--------

- CI and supply chain - Add Dependabot for pip, GitHub Actions, and pre-commit; pin ``actions-cool/issues-helper`` to a commit SHA; set top-level workflow permissions where appropriate.
- Fix documentation typos that had infra.aap_configuration_extended.dispatch instead of infra.aap_configuration.dispatch
- Repository hygiene - Ignore ``.env``, key material, and ``.pre-commit-cache/`` in ``.gitignore``; exclude ``.pre-commit-cache/`` from ansible-lint so local pre-commit caches do not break lint discovery.
- Use the Gateway users API endpoint (/api/gateway/v1/users) to retrieve AAP users list and the associated_authenticator attribute to determine if users are local or not
- filetree_create - Avoid job_templates and workflow_job_templates export failure if all their extra_vars are commented
- filetree_create - gateway_role_definitions.yml‎ - Fix no_log var undefined
- upgrade_config - Remove the development ``compare_upgrade_output.py`` helper and the compare task from ``tests/upgrade_config.yaml``; update the role README.

v4.2.0
======

Minor Changes
-------------

- Don't read the files if they don't contains the corresponding variable
- Moved the valid_tags from role vars to defaults
- No need to initialize the variables that have to be read from the input files

Bugfixes
--------

- Change decision_environment_id to organization_id in eda_rulebook_activations.yml to fix error when exporting rulebook activations
- Don't export hub roles (included into the role_definitions).
- Export only non-managed role_definitions.
- Fix organization query in EDA decision environments template, organizations endpoint was incorrect

v4.1.0
======

Minor Changes
-------------

- change the usage of '!unsafe' in favor of '{%- raw -%} ... {%- endraw -%}' blocks in the 'filetree_create' role

Bugfixes
--------

- Fix an issue with the notification templates output where an integer can't be concatenated to a string when forming the URL (ansible >= 4.20.1)
- Fix the output of the workflow job templates when a node have it's unified_job_template field not defined (the original JT has been deleted but the WF has not been updated accordingly)

v4.0.1
======

Bugfixes
--------

- infra.aap_configuration_extended.filetree_create now generates a dict instead of a list for controller_settings, so infra.aap_configuration.dispatch can use it directly

v4.0.0
======

Major Changes
-------------

- Remove `| default('$encrypted$')` when `secrets_as_variables` is `true`. This will cause `dispatch` to fail with `variable undefined` instead of accidentally changing the secret.
- Set `secrets_as_variables` to `true` in defaults/main.yml as this is safer instead of accidentally importing `''` or `'$encrypted$`

Minor Changes
-------------

- Added the ability to change the output folder names in `filetree_create`

Bugfixes
--------

- Added missing `gateway_*` var/yaml file reading tasks to `filetree_read`
- Adds a check for the PAH instance existence. If this is not available at the AAP target instance, it won't make the filetree_create role to fail
- Change the exported output from using 'rulebook_name' to 'rulebook', according to the input expected by infra.aap_configuration.eda_rulebook_activations role
- Fix a variable in the filetree_create role that was causing wrong output contents for controller_hosts
- Fix checking issues in the when clauses in `filetree_read` role
- Fix the exportation of the controller_settings that was failing when the parameter AUTOMATION_ANALYTICS_LAST_ENTRIES was empty
- Fixes one problem concatenating string and integer when building a URI
- If there's no content to be added to any file, create the file with the variable assigned to an empty list.
- Remove the default for aap_rules in aap_rules_validation role as it is a required field.
- fix global execution environments comparison and exportation. Update the filetree_create role acordingly.
- fix notification template output messages

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
