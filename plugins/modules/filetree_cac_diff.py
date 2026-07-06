#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: filetree_cac_diff
short_description: Compare live filetree export files against repository CaC files
description:
  - Exports from C(filetree_create) and repository CaC are compared at file level on disk.
  - Matching is done per object identity extracted from YAML files, not by in-memory lists.
  - Writes only differing objects as YAML files under C(diff_path), each tagged with
    C(state=present) or C(state=absent), ready for C(filetree_read) and C(dispatch).
  - Repository CaC files may contain Jinja expressions; render them with C(template_vars)
    before comparison (for example C(orgs) or vault variables).
options:
  live_path:
    description: Directory containing the live C(filetree_create) export.
    required: true
    type: str
  cac_paths:
    description: List of repository CaC directories (same paths used by C(filetree_read)).
    required: true
    type: list
    elements: str
  diff_path:
    description: Output directory where difference YAML files are written.
    required: true
    type: str
  template_vars:
    description: Variables used to render Jinja expressions in repository CaC files before comparison.
    default: {}
    type: dict
  ignore_keys:
    description: Top-level object keys ignored during content comparison.
    default:
      - state
      - type
      - password
      - token
      - oauth_token
      - secret
      - client_secret
      - ssh_key_data
      - vault_password
      - become_password
      - passphrase
      - inputs
    type: list
    elements: str
  set_absent:
    description: Write C(state=absent) files for objects only present in the live export.
    default: true
    type: bool
  root_keys_filter:
    description: Limit comparison to these YAML root keys (for example C(controller_inventories)).
    type: list
    elements: str
  organization_filter:
    description: >-
      Limit comparison to objects assigned to this organization name.
      Defaults to C(template_vars.orgs) when set.
    type: str
author:
  - Ivan Aragonés (@ivarmu)
...
"""

EXAMPLES = r"""
- name: Compare live export against repository CaC on disk
  infra.aap_configuration_extended.filetree_cac_diff:
    live_path: /tmp/filetree_object_diff_live
    cac_paths:
      - /srv/cac/orgs/Default/env/common/controller_inventories.d/
      - /srv/cac/orgs/Default/env/common/controller_projects.d/
    diff_path: /tmp/filetree_object_diff_delta
    template_vars:
      orgs: Default
      env: common
    root_keys_filter:
      - controller_inventories
      - controller_projects
  register: filetree_diff
...
"""

RETURN = r"""
diff_files:
  description: Paths of generated difference YAML files.
  type: list
  returned: always
present_count:
  description: Number of C(state=present) objects written.
  type: int
  returned: always
absent_count:
  description: Number of C(state=absent) objects written.
  type: int
  returned: always
unchanged_count:
  description: Number of objects identical on both sides.
  type: int
  returned: always
changed:
  description: Whether any difference files were written.
  type: bool
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.infra.aap_configuration_extended.plugins.module_utils.filetree_cac_diff import (
    HAS_YAML,
    compare_filetrees,
)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            live_path=dict(type="str", required=True),
            cac_paths=dict(type="list", elements="str", required=True),
            diff_path=dict(type="str", required=True),
            template_vars=dict(type="dict", default={}),
            ignore_keys=dict(type="list", elements="str", default=None),
            set_absent=dict(type="bool", default=True),
            root_keys_filter=dict(type="list", elements="str", default=None),
            organization_filter=dict(type="str", default=None),
        ),
        supports_check_mode=True,
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML is required to run filetree_cac_diff (install python3-PyYAML on the target host).")

    result = compare_filetrees(
        live_paths=[module.params["live_path"]],
        cac_paths=module.params["cac_paths"],
        diff_path=module.params["diff_path"],
        ignore_keys=module.params["ignore_keys"],
        template_vars=module.params["template_vars"],
        set_absent=module.params["set_absent"],
        root_keys_filter=module.params["root_keys_filter"],
        organization_filter=module.params["organization_filter"],
    )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
