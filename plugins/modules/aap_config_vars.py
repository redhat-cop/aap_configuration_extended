#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat Automation Community of Practice
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: aap_config_vars
short_description: Load AAP configuration-as-code vars (optionally only changed objects)
version_added: "4.10.0"
description:
  - Loads YAML from C(config/all/) then C(config/<env>/) and sets those keys as
    facts for C(infra.aap_configuration.dispatch), replacing
    C(ansible.builtin.include_vars) for that layout.
  - When O(changed_only) is V(true), compares the merged vars to the git revision
    in O(git_base) and keeps only objects (list items) whose content changed.
  - Unchanged object-type vars are omitted so dispatch skips those roles.
  - Files listed in O(always_load) (secrets and installer vars by default) are
    always included in full.
  - Use a full load (O(changed_only) is V(false), the default) for the first
    apply or when the cluster may have drifted.
options:
  config_dir:
    description:
      - Path to the C(config/) directory that contains C(all/) and environment
        subdirectories.
      - Relative paths are resolved from O(playbook_dir) when that is set,
        otherwise from the current working directory.
    type: path
    default: "../config"
  playbook_dir:
    description:
      - Directory used to resolve a relative O(config_dir).
      - The action plugin sets this from the playbook directory automatically.
    type: path
  env:
    description:
      - Environment subdirectory under C(config/) (for example C(dev), C(qa),
        C(prod)).
    type: str
    required: true
  extensions:
    description:
      - File extensions to load, without a leading dot.
    type: list
    elements: str
    default:
      - yml
      - yaml
  changed_only:
    description:
      - If C(true), load only objects that differ from O(git_base).
      - If C(false), load every file like C(include_vars) (full apply).
    type: bool
    default: false
  git_base:
    description:
      - Git revision to compare against when O(changed_only=true).
      - C(HEAD) compares the working tree (including uncommitted changes) to the
        last commit. Use C(origin/main) (or another branch) in CI to apply
        everything that changed on the branch.
    type: str
    default: "HEAD"
  git_repo:
    description:
      - Git repository root. Detected from O(config_dir) when omitted.
    type: path
  include_absent:
    description:
      - If V(true), objects present at O(git_base) but missing now are added
        with C(state=absent) so dispatch can delete them.
      - Off by default because not every AAP configuration role treats absent
        the same way.
    type: bool
    default: false
  always_load:
    description:
      - Basenames that are always merged in full, even during an incremental
        load. Used for vault secrets and installer settings.
    type: list
    elements: str
    default:
      - secrets.yml
      - aap_install.yml
author:
  - Red Hat Automation Community of Practice
notes:
  - Runs on the controller. Prefer C(connection=local) / C(delegate_to=localhost).
  - When an action plugin with this name is present, it resolves O(playbook_dir)
    and decrypts vault with the same DataLoader as C(include_vars), then calls
    this module's shared implementation.
  - Incremental mode is a semantic compare of parsed YAML objects, not a raw
    line diff. Comment-only or formatting-only edits do not mark an object as
    changed.
  - Identity for list items is C(name) (plus C(organization) when present).
    Assignment objects without a name use fields such as C(user), C(team), and
    C(role).
seealso:
  - module: ansible.builtin.include_vars
'''

EXAMPLES = r'''
- name: Load all AAP config vars (same as include_vars)
  infra.aap_configuration_extended.aap_config_vars:
    config_dir: "{{ playbook_dir }}/../config"
    env: "{{ env }}"

- name: Load only objects that changed since HEAD
  infra.aap_configuration_extended.aap_config_vars:
    config_dir: "{{ playbook_dir }}/../config"
    env: "{{ env }}"
    changed_only: true

- name: Load objects that changed on this branch vs origin/main
  infra.aap_configuration_extended.aap_config_vars:
    config_dir: "{{ playbook_dir }}/../config"
    env: "{{ env }}"
    changed_only: true
    git_base: origin/main
    include_absent: true

- name: Dispatch the loaded vars
  ansible.builtin.include_role:
    name: infra.aap_configuration.dispatch
  vars:
    dispatch_include_wildcard_vars: true
'''

RETURN = r'''
ansible_facts:
  description: Variables loaded from config files (filtered when incremental).
  returned: always
  type: dict
ansible_included_var_files:
  description: Current config files that were read from disk.
  returned: always
  type: list
  elements: str
aap_config_mode:
  description: C(full) or C(incremental).
  returned: always
  type: str
aap_config_git_base:
  description: Git ref used for comparison.
  returned: when incremental
  type: str
aap_config_git_base_sha:
  description: Resolved commit SHA of O(git_base).
  returned: when incremental
  type: str
aap_config_changed_vars:
  description:
    - Map of variable name to a list of added, modified, or removed objects.
    - Object labels use name/identity fields only (not secret inputs).
  returned: when incremental
  type: dict
'''

import os
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

try:
    from ansible_collections.infra.aap_configuration_extended.plugins.module_utils.aap_config_vars import (
        GitError,
        load_aap_config,
    )
except ImportError:
    try:
        from ansible.module_utils.aap_config_vars import GitError, load_aap_config
    except ImportError:
        GitError = Exception  # type: ignore[misc,assignment]
        load_aap_config = None  # type: ignore[assignment]
        IMPORT_ERROR = traceback.format_exc()
    else:
        IMPORT_ERROR = None
else:
    IMPORT_ERROR = None


def _resolve_config_dir(config_dir, playbook_dir):
    if os.path.isabs(config_dir):
        return os.path.abspath(config_dir)
    base = playbook_dir or os.getcwd()
    return os.path.abspath(os.path.join(base, config_dir))


def run_module(module):
    if load_aap_config is None:
        module.fail_json(
            msg=missing_required_lib('aap_config_vars module_utils'),
            exception=IMPORT_ERROR,
        )

    params = module.params
    config_dir = _resolve_config_dir(params['config_dir'], params.get('playbook_dir'))

    try:
        result = load_aap_config(
            config_dir=config_dir,
            env=params['env'],
            extensions=params['extensions'],
            changed_only=params['changed_only'],
            git_base=params['git_base'],
            git_repo=params.get('git_repo'),
            include_absent=params['include_absent'],
            always_load=params['always_load'],
        )
    except GitError as exc:
        module.fail_json(
            msg=(
                'changed_only requires git ({0}). '
                'Set changed_only=false for a full load, or pass a valid git_base.'
            ).format(exc)
        )
    except (OSError, ValueError) as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(**result)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            config_dir=dict(type='path', default='../config'),
            playbook_dir=dict(type='path'),
            env=dict(type='str', required=True),
            extensions=dict(type='list', elements='str', default=['yml', 'yaml']),
            changed_only=dict(type='bool', default=False),
            git_base=dict(type='str', default='HEAD'),
            git_repo=dict(type='path'),
            include_absent=dict(type='bool', default=False),
            always_load=dict(
                type='list',
                elements='str',
                default=['secrets.yml', 'aap_install.yml'],
            ),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
