#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2024, Ivan Aragonés (@ivarmu)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: format_yaml
short_description: Format YAML files with PyYAML (ansible-core dependency only)
description:
  - Reformats a YAML file in place using PyYAML (same stack as ansible-core).
  - With I(preserve_comments=true) (default), only adjusts indentation of block sequences that YAML parsed as
    "indentless" (using C(yaml.compose) line marks). Comments and overall structure are kept.
  - If flow-style collections are found (e.g. C([{a: 1}])), the module canonicalizes them to block style to ensure
    readable YAML output.
  - With I(preserve_comments=false), performs a full load and dump (comments are lost). Enables I(auto_block_scalars),
    PEM-in-one-line repair, Ansible C(!unsafe) round-trip (scalars keep the tag; multiline unsafe uses a literal block),
    block-style lists,     C(null) emitted as an empty value (no C(null) keyword), optional normalization of Python boolean spellings to
    lowercase in plain scalars when preserving comments, and double-quoted scalars for slash-delimited regex strings that
    contain backslashes (in the file, C(\\.) before the dot encodes a single backslash plus a literal dot in the value).
options:
  path:
    description: Path to the YAML file to read and optionally rewrite.
    required: true
    type: str
  preserve_comments:
    description:
      - If V(true), indent fix only (comments preserved).
      - If V(false), full round-trip; see main description for dump-side behaviour.
    default: true
    type: bool
  explicit_start:
    description: Emit document begin marker C(---). Used when I(preserve_comments=false), or when I(fix_document_markers=true) with I(preserve_comments=true).
    default: true
    type: bool
  explicit_end:
    description: Emit document end marker C(...). Used when I(preserve_comments=false), or when I(fix_document_markers=true) with I(preserve_comments=true).
    default: true
    type: bool
  fix_document_markers:
    description:
      - When I(preserve_comments=true), also enforce C(---) and C(...) at the document boundaries when I(explicit_start) / I(explicit_end) are true.
    default: true
    type: bool
  auto_block_scalars:
    description:
      - Emit multiline strings as literal block scalars (C(|)) when possible.
      - With I(preserve_comments=true), conversion is applied in-place for quoted single-line values that decode
        to multiline content (comments and layout stay untouched).
    default: false
    type: bool
notes:
  - Requires PyYAML on the target (bundled with the controller for ansible-core; use python3-yaml on remotes if the module runs there).
author:
  - Ivan Aragonés (@ivarmu)
"""

EXAMPLES = r"""
- name: Fix indentless block lists while keeping comments
  infra.aap_configuration_extended.format_yaml:
    path: /srv/controller/config/settings.yaml

- name: Full round-trip for readable CaC (comments removed)
  infra.aap_configuration_extended.format_yaml:
    path: /srv/controller/config/gateway_authenticator_maps.yaml
    preserve_comments: false
    explicit_start: true
    explicit_end: true
    fix_document_markers: true
    auto_block_scalars: true
...
"""

RETURN = r"""
changed:
  description: Whether the file content was updated.
  type: bool
  returned: always
  sample: true
msg:
  description: Human-readable status.
  type: str
  returned: always
  sample: "YAML formatted."
...
"""

import io
import os
import re
import traceback

from ansible.module_utils.basic import AnsibleModule

try:
    import yaml
    from yaml import SafeDumper as PySafeDumper
    from yaml.constructor import ConstructorError
    from yaml.nodes import MappingNode, ScalarNode, SequenceNode
    from yaml.representer import SafeRepresenter

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None  # type: ignore
    PySafeDumper = None
    SafeRepresenter = None  # type: ignore

# Ansible CaC / PyYAML tag names (avoid duplicated string literals for static analysis).
UNSAFE_YAML_TAG = "!unsafe"
YAML_NULL_TAG = "tag:yaml.org,2002:null"
YAML_STR_TAG = "tag:yaml.org,2002:str"


class AnsibleUnsafeTaggedString(str):
    """Scalar loaded from !unsafe; dumped with the same tag (multiline as literal |)."""


class MultilineLiteralBlockString(str):
    """Plain string to emit as a literal block scalar (|)."""


def construct_unsafe_tag(loader, node):
    """Ansible CaC uses !unsafe for Jinja; scalars keep the tag on round-trip."""
    if isinstance(node, ScalarNode):
        return AnsibleUnsafeTaggedString(loader.construct_scalar(node))
    if isinstance(node, SequenceNode):
        return loader.construct_sequence(node, deep=True)
    if isinstance(node, MappingNode):
        return loader.construct_mapping(node, deep=True)
    raise ConstructorError(None, None, "unsupported !unsafe node", node.start_mark)


if HAS_YAML:
    yaml.SafeLoader.add_constructor(UNSAFE_YAML_TAG, construct_unsafe_tag)


def count_leading_spaces(line):
    count = 0
    for char in line:
        if char not in " \t":
            break
        count += 1
    return count


def prepend_leading_spaces(line, extra_spaces):
    if line.endswith("\r\n"):
        body, newline = line[:-2], "\r\n"
    elif line.endswith("\n"):
        body, newline = line[:-1], "\n"
    else:
        body, newline = line, ""
    return (" " * extra_spaces) + body + newline


def compose_node_line_span(node):
    if isinstance(node, ScalarNode):
        return (node.start_mark.line, node.end_mark.line)
    if isinstance(node, SequenceNode):
        if not node.value:
            return (node.start_mark.line, node.end_mark.line)
        child_spans = [compose_node_line_span(child) for child in node.value]
        return (min(s for s, _e in child_spans), max(e for _s, e in child_spans))
    if isinstance(node, MappingNode):
        if not node.value:
            return (node.start_mark.line, node.end_mark.line)
        child_spans = []
        for key_node, value_node in node.value:
            child_spans.append(compose_node_line_span(key_node))
            child_spans.append(compose_node_line_span(value_node))
        return (min(s for s, _e in child_spans), max(e for _s, e in child_spans))
    return (node.start_mark.line, node.end_mark.line)


def compose_node_children(node):
    if isinstance(node, MappingNode):
        children = []
        for key_node, value_node in node.value:
            children.extend((key_node, value_node))
        return children
    if isinstance(node, SequenceNode):
        return list(node.value)
    return []


def tree_has_flow_style_collections(node):
    if not isinstance(node, (MappingNode, SequenceNode)):
        return False
    if node.flow_style:
        return True
    return any(tree_has_flow_style_collections(child) for child in compose_node_children(node))


def text_has_flow_style_collections(text):
    root = yaml.compose(io.StringIO(text), Loader=yaml.SafeLoader)
    if root is None:
        return False
    return tree_has_flow_style_collections(root)


def bump_indentless_block_list_items(key_node, value_node, lines, line_deltas, step, line_count):
    if not (isinstance(value_node, SequenceNode) and not value_node.flow_style and value_node.value):
        return
    key_line_index = key_node.start_mark.line
    if key_line_index >= line_count:
        return
    key_indent = count_leading_spaces(lines[key_line_index])
    for sequence_item in value_node.value:
        item_line = sequence_item.start_mark.line
        if item_line >= line_count or count_leading_spaces(lines[item_line]) != key_indent:
            continue
        span_start, span_end = compose_node_line_span(sequence_item)
        span_start = max(0, span_start)
        span_end = min(line_count - 1, span_end)
        for line_index in range(span_start, span_end + 1):
            line_deltas[line_index] += step


def walk_compose_tree_for_indent_fix(node, lines, line_deltas, step, line_count):
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            bump_indentless_block_list_items(key_node, value_node, lines, line_deltas, step, line_count)
            if isinstance(value_node, MappingNode):
                walk_compose_tree_for_indent_fix(value_node, lines, line_deltas, step, line_count)
            elif isinstance(value_node, SequenceNode):
                for child in value_node.value:
                    walk_compose_tree_for_indent_fix(child, lines, line_deltas, step, line_count)
    elif isinstance(node, SequenceNode):
        for child in node.value:
            walk_compose_tree_for_indent_fix(child, lines, line_deltas, step, line_count)


def fix_indent_preserve_comments(text, indent_step):
    lines = text.splitlines(True)
    line_count = len(lines)
    if not line_count:
        return text
    root = yaml.compose(io.StringIO(text), Loader=yaml.SafeLoader)
    if root is None:
        return text
    line_deltas = [0] * line_count
    walk_compose_tree_for_indent_fix(root, lines, line_deltas, indent_step, line_count)
    return "".join(prepend_leading_spaces(lines[index], line_deltas[index]) if line_deltas[index] else lines[index] for index in range(line_count))


def strip_trailing_whitespace(text):
    result_lines = []
    for line in text.splitlines(True):
        if line.endswith("\r\n"):
            result_lines.append(line[:-2].rstrip(" \t") + "\r\n")
        elif line.endswith("\n"):
            result_lines.append(line[:-1].rstrip(" \t") + "\n")
        else:
            result_lines.append(line.rstrip(" \t"))
    return "".join(result_lines)


# Ansible-lint yaml[truthy]: prefer true/false over Python True/False in plain scalars.
_TRUTHY_LINE_PATTERN = re.compile(r"^(\s*[^:]+:\s*)(True|False)(\s*(?:#.*)?)$")
_QUOTED_MAPPING_VALUE_PATTERN = re.compile(r'^(\s*[^:\n]+:\s*)"((?:[^"\\]|\\.)*)"(\s*(?:#.*)?)$')
_QUOTED_SEQUENCE_ITEM_PATTERN = re.compile(r'^(\s*-\s*)"((?:[^"\\]|\\.)*)"(\s*(?:#.*)?)$')


def fix_truthy_capital_bool_on_line(line_body):
    match = _TRUTHY_LINE_PATTERN.match(line_body)
    if not match:
        return line_body
    return match.group(1) + match.group(2).lower() + match.group(3)


def fix_truthy_capital_bools_in_text(text):
    result_lines = []
    for line in text.splitlines(True):
        if line.endswith("\r\n"):
            core, newline = line[:-2], "\r\n"
        elif line.endswith("\n"):
            core, newline = line[:-1], "\n"
        else:
            core, newline = line, ""
        result_lines.append(fix_truthy_capital_bool_on_line(core) + newline)
    return "".join(result_lines)


def split_line_body_and_newline(line):
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def match_quoted_scalar_candidate(line_body):
    match = _QUOTED_MAPPING_VALUE_PATTERN.match(line_body)
    if match:
        return (False,) + match.groups()
    match = _QUOTED_SEQUENCE_ITEM_PATTERN.match(line_body)
    if match:
        return (True,) + match.groups()
    return None


def decode_quoted_yaml_scalar(encoded_value):
    yaml_fragment = 'value: "{0}"'.format(encoded_value)
    try:
        decoded_value = yaml.safe_load(yaml_fragment)["value"]
    except Exception:
        return None
    return decoded_value if isinstance(decoded_value, str) else None


def build_literal_block_replacement(prefix, trailing_comment, repaired_value, is_sequence, line_break):
    effective_break = line_break or "\n"
    block_header = "{0}|-{1}".format(prefix, trailing_comment)
    if is_sequence:
        block_indent_size = len(prefix)
    else:
        block_indent_size = count_leading_spaces(prefix) + 2
        if prefix.lstrip().startswith("- "):
            # Mapping value inside a sequence item (`- key: |`), requires one more indent level.
            block_indent_size += 2
    block_indent = " " * block_indent_size
    rebuilt = [block_header + effective_break]
    for block_line in repaired_value.split("\n"):
        rebuilt.append("{0}{1}{2}".format(block_indent, block_line, effective_break))
    return "".join(rebuilt)


def convert_quoted_multiline_scalars_to_literal_blocks(text):
    """Convert one-line double-quoted scalars that decode to multiline into block scalars, preserving comments."""
    output_lines = []
    for line in text.splitlines(True):
        line_body, line_break = split_line_body_and_newline(line)
        scalar_candidate = match_quoted_scalar_candidate(line_body)
        if not scalar_candidate:
            output_lines.append(line)
            continue

        is_sequence, prefix, encoded_value, trailing_comment = scalar_candidate
        decoded_value = decode_quoted_yaml_scalar(encoded_value)
        if decoded_value is None:
            output_lines.append(line)
            continue

        repaired_value = repair_single_line_pem_certificate(decoded_value)
        if "\n" not in repaired_value:
            output_lines.append(line)
            continue

        output_lines.append(build_literal_block_replacement(prefix, trailing_comment, repaired_value, is_sequence, line_break))
    return "".join(output_lines)


def ensure_yaml_document_markers(text, want_start_marker, want_end_marker):
    stripped_bom = text.lstrip("\ufeff")
    if want_start_marker and not stripped_bom.lstrip().startswith("---"):
        stripped_bom = "---\n" + stripped_bom
    if want_end_marker:
        trimmed = stripped_bom.rstrip("\n\r")
        if not trimmed.endswith("..."):
            stripped_bom = trimmed + "\n...\n"
    return stripped_bom


def repair_single_line_pem_certificate(text):
    if "-----BEGIN" in text and "-----END" in text and "\n" not in text:
        match = re.search(r"(-----BEGIN.*?-----)\s+(.*?)\s+(-----END.*?-----)", text)
        if match:
            return "{0}\n{1}\n{2}".format(match.group(1), match.group(2).replace(" ", "\n"), match.group(3))
    return text


def normalize_escaped_multiline_string(text):
    """Convert unescaped '\\n' / '\\r\\n' sequences to real newlines for multiline payloads."""
    if "\n" in text or "\\n" not in text:
        return text
    normalized = re.sub(r"(?<!\\)\\r\\n", "\n", text)
    normalized = re.sub(r"(?<!\\)\\n", "\n", normalized)
    return normalized


def normalize_for_literal_block(text):
    """PyYAML refuses block style for multiline scalars containing tab chars."""
    return text.replace("\t", "  ")


def represent_literal_block_string(dumper, data):
    return dumper.represent_scalar(YAML_STR_TAG, str(data), style="|")


def represent_ansible_unsafe_string(dumper, data):
    scalar = str(data)
    if "\n" in scalar:
        return dumper.represent_scalar(UNSAFE_YAML_TAG, scalar, style="|")
    return dumper.represent_scalar(UNSAFE_YAML_TAG, scalar)


def represent_none_as_empty_yaml_scalar(dumper, data):
    # Empty scalar keeps YAML null semantics without the literal "null" token (Ansible-friendly).
    return dumper.represent_scalar(YAML_NULL_TAG, "")


def represent_string_for_format_dump(dumper, data):
    # Regex-in-slashes with backslashes: double-quoted YAML so escapes match common CaC style
    # (e.g. "\\." in file → one "\" + "." in value — same as unquoted "\\." or single-quoted "\.").
    if isinstance(data, str) and len(data) >= 3 and data.startswith("/") and data.endswith("/") and "\\" in data:
        return dumper.represent_scalar(YAML_STR_TAG, data, style='"')
    return SafeRepresenter.represent_str(dumper, data)


def prepare_tree_for_round_trip_dump(node, auto_block_scalars):
    """Deep-transform dict/list tree: PEM repair, optional multiline → literal block wrappers."""
    if isinstance(node, dict):
        return {key: prepare_tree_for_round_trip_dump(value, auto_block_scalars) for key, value in node.items()}
    if isinstance(node, list):
        return [prepare_tree_for_round_trip_dump(item, auto_block_scalars) for item in node]
    if isinstance(node, AnsibleUnsafeTaggedString):
        return node
    if isinstance(node, str):
        repaired = normalize_escaped_multiline_string(node)
        repaired = repair_single_line_pem_certificate(repaired)
        if auto_block_scalars and "\n" in repaired:
            return MultilineLiteralBlockString(normalize_for_literal_block(repaired))
        return repaired
    return node


def clean_yaml_tree(tree, auto_block=False):
    """Backward-compatible mutating wrapper kept for legacy unit tests."""
    cleaned = prepare_tree_for_round_trip_dump(tree, auto_block)
    if isinstance(tree, dict):
        tree.clear()
        tree.update(cleaned)
    elif isinstance(tree, list):
        tree[:] = cleaned
    return tree


def build_format_yaml_dumper_class():
    """SafeDumper subclass: block flow_style lists + custom representers."""

    class FormatYamlDumper(PySafeDumper):
        def expect_block_sequence(self):
            self.increase_indent(flow=False, indentless=False)
            self.state = self.expect_first_block_sequence_item

    FormatYamlDumper.add_representer(type(None), represent_none_as_empty_yaml_scalar)
    FormatYamlDumper.add_representer(AnsibleUnsafeTaggedString, represent_ansible_unsafe_string)
    FormatYamlDumper.add_representer(str, represent_string_for_format_dump)
    FormatYamlDumper.add_representer(MultilineLiteralBlockString, represent_literal_block_string)
    return FormatYamlDumper


def try_yaml_dump_with_fallback_options(data_tree, explicit_start, explicit_end, dumper_class):
    output_buffer = io.StringIO()
    base_kwargs = {
        "default_flow_style": False,
        "allow_unicode": True,
        "explicit_start": explicit_start,
        "explicit_end": explicit_end,
        "Dumper": dumper_class,
    }
    option_variants = (
        {"sort_keys": False, "width": 4096, "indent": 2},
        {"sort_keys": False, "width": 4096},
        {"sort_keys": False},
    )
    last_type_error = None
    for extra_kwargs in option_variants:
        dump_kwargs = dict(base_kwargs, **extra_kwargs)
        try:
            yaml.dump(data_tree, output_buffer, **dump_kwargs)
            return output_buffer.getvalue()
        except TypeError as exc:
            last_type_error = exc
            output_buffer.seek(0)
            output_buffer.truncate(0)
    if last_type_error:
        raise last_type_error
    yaml.dump(data_tree, output_buffer, **dict(base_kwargs, sort_keys=False))
    return output_buffer.getvalue()


def dump_round_trip_tree(data, explicit_start, explicit_end, auto_block_scalars):
    prepared_tree = prepare_tree_for_round_trip_dump(data, auto_block_scalars)
    dumper_class = build_format_yaml_dumper_class()
    return try_yaml_dump_with_fallback_options(prepared_tree, explicit_start, explicit_end, dumper_class)


def format_yaml_content(original_text, preserve_comments, explicit_start, explicit_end, fix_markers, auto_block_scalars):
    yaml.safe_load(original_text)
    if preserve_comments:
        formatted = fix_indent_preserve_comments(original_text, 2)
        formatted = strip_trailing_whitespace(formatted)
        formatted = fix_truthy_capital_bools_in_text(formatted)
        if auto_block_scalars:
            formatted = convert_quoted_multiline_scalars_to_literal_blocks(formatted)
        if text_has_flow_style_collections(formatted):
            parsed = yaml.safe_load(formatted)
            if parsed is None:
                parsed = {}
            formatted = dump_round_trip_tree(parsed, explicit_start, explicit_end, auto_block_scalars)
            return strip_trailing_whitespace(formatted)
        if fix_markers:
            formatted = ensure_yaml_document_markers(formatted, explicit_start, explicit_end)
        yaml.safe_load(formatted)
        return formatted
    parsed = yaml.safe_load(original_text)
    if parsed is None:
        parsed = {}
    formatted = dump_round_trip_tree(parsed, explicit_start, explicit_end, auto_block_scalars)
    return strip_trailing_whitespace(formatted)


def run_module():
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "str", "required": True},
            "preserve_comments": {"type": "bool", "default": True},
            "explicit_start": {"type": "bool", "default": True},
            "explicit_end": {"type": "bool", "default": True},
            "fix_document_markers": {"type": "bool", "default": True},
            "auto_block_scalars": {"type": "bool", "default": False},
        },
        supports_check_mode=True,
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML (python3-yaml) is required on the target.")

    params = module.params
    path = params["path"]
    if not os.path.exists(path):
        module.fail_json(msg="File not found: {0}".format(path))

    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            original_text = file_handle.read()

        formatted_text = format_yaml_content(
            original_text,
            params["preserve_comments"],
            params["explicit_start"],
            params["explicit_end"],
            params["fix_document_markers"],
            params["auto_block_scalars"],
        )

        if formatted_text != original_text:
            if not module.check_mode:
                with open(path, "w", encoding="utf-8") as file_handle:
                    file_handle.write(formatted_text)
            module.exit_json(changed=True, msg="YAML formatted.")
        module.exit_json(changed=False, msg="No changes.")

    except yaml.YAMLError as exc:
        module.fail_json(msg="YAML parse error: {0}".format(exc), exception=traceback.format_exc())
    except Exception as exc:
        module.fail_json(msg="Error: {0}".format(exc), exception=traceback.format_exc())


if __name__ == "__main__":
    run_module()
