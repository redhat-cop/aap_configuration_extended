#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: format_yaml
short_description: Formats a YAML file while preserving comments and markers.
description:
  - Uses ruamel.yaml to pretty-print a YAML file.
  - Preserves comments, disables line-wrapping for long keys, and can convert multiline strings to block scalars.
options:
  path:
    description: Absolute path to the YAML file to format.
    required: true
    type: str
  explicit_start:
    description: Enforce the '---' marker at the top of the file.
    default: true
    type: bool
  explicit_end:
    description: Enforce the '...' marker at the bottom of the file.
    default: true
    type: bool
  auto_block_scalars:
    description: Automatically convert strings with newlines into literal blocks (|).
    default: false
    type: bool
"""

import os
import io
import re
import traceback
from ansible.module_utils.basic import AnsibleModule

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import PreservedScalarString

    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False


def repair_flattened_crypto_keys(text):
    if "-----BEGIN" in text and "-----END" in text and "\n" not in text:
        match = re.search(r"(-----BEGIN.*?-----)\s+(.*?)\s+(-----END.*?-----)", text)
        if match:
            header = match.group(1)
            body = match.group(2).replace(" ", "\n")
            footer = match.group(3)
            return f"{header}\n{body}\n{footer}"
    return text


def clean_yaml_tree(node, auto_block):
    """
    Recursively wipe out 'flow style' memory from ruamel,
    and optionally convert strings with newlines to literal blocks (|).
    """
    # 1. The Secret Trick: Force Block Style on this specific node
    if hasattr(node, "fa"):
        node.fa.set_block_style()

    # 2. Walk the tree to apply to children and handle strings
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                v = repair_flattened_crypto_keys(v)
                # If auto_block is true and there are newlines, force the | block
                if auto_block and "\n" in v:
                    node[k] = PreservedScalarString(v)
            else:
                clean_yaml_tree(v, auto_block)

    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str):
                v = repair_flattened_crypto_keys(v)
                if auto_block and "\n" in v:
                    node[i] = PreservedScalarString(v)
            else:
                clean_yaml_tree(v, auto_block)


def run_module():
    module_args = dict(
        path=dict(type="str", required=True),
        explicit_start=dict(type="bool", default=True),
        explicit_end=dict(type="bool", default=True),
        auto_block_scalars=dict(type="bool", default=False),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if not HAS_RUAMEL:
        module.fail_json(msg="The Python 'ruamel.yaml' library is required.")

    path = module.params["path"]
    if not os.path.exists(path):
        module.fail_json(msg=f"File not found: {path}")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.explicit_start = module.params["explicit_start"]
    yaml.explicit_end = module.params["explicit_end"]
    yaml.default_flow_style = False
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        with open(path, "r") as f:
            original_content = f.read()

        with open(path, "r") as f:
            data = yaml.load(f)

        # Apply our heavy-duty cleaner to the data
        clean_yaml_tree(data, module.params["auto_block_scalars"])

        out = io.StringIO()
        yaml.dump(data, out)
        new_content = out.getvalue()

        if original_content != new_content:
            if not module.check_mode:
                with open(path, "w") as f:
                    f.write(new_content)
            module.exit_json(changed=True, msg="YAML file formatted successfully.")
        else:
            module.exit_json(changed=False, msg="YAML file is already perfectly formatted.")

    except Exception as e:
        module.fail_json(msg=f"Failed to process YAML: {str(e)}", exception=traceback.format_exc())


if __name__ == "__main__":
    run_module()
