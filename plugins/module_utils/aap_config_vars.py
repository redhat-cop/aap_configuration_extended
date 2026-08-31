# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat Automation Community of Practice
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Load and diff AAP configuration-as-code variables.

Shared by the aap_config_vars module and action plugin.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

# Fields used to identify a list item when it has no ``name``.
# Order matters: the tuple of present keys is the identity.
IDENTITY_KEYS = (
    'name',
    'organization',
    'user',
    'team',
    'role',
    'role_definition',
    'inventory',
    'job_template',
    'workflow',
    'workflow_job_template',
    'credential',
    'credential_type',
    'source_credential',
    'target_credential',
    'input_field_name',
    'hostname',
    'host',
    'username',
    'group',
    'groups',
    'instance_group',
    'execution_environment',
    'project',
    'application',
    'label',
    'notification_template',
    'instance',
    'ansible_id',
    'object_id',
    'object_ansible_id',
    'content_type',
    'target',
)

_MISSING = object()


class GitError(Exception):
    """Raised when a git command needed for incremental load fails."""


def to_native(value: Any) -> Any:
    """Reduce Ansible-specific types so object comparison is stable."""
    if isinstance(value, dict):
        return {to_native(key): to_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_native(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    data = getattr(value, 'data', None)
    if data is not None and not isinstance(value, (str, bytes)):
        return to_native(data)
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return str(value)


def _freeze(value: Any) -> Any:
    native = to_native(value)
    if isinstance(native, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in native.items()))
    if isinstance(native, list):
        return tuple(_freeze(item) for item in native)
    return native


def object_identity(obj: Any) -> tuple:
    """Return a hashable identity for a YAML list item."""
    if not isinstance(obj, dict):
        return ('__value__', _freeze(obj))

    parts = []
    for key in IDENTITY_KEYS:
        if key in obj:
            parts.append((key, _freeze(obj[key])))
    if parts:
        return tuple(parts)

    rest = {key: item for key, item in obj.items() if key != 'state'}
    return ('__full__', _freeze(rest))


def identity_label(obj: Any) -> Any:
    """Short identity for task results / logs (no secrets)."""
    if not isinstance(obj, dict):
        return to_native(obj)
    if obj.get('name') is not None:
        label = {'name': obj['name']}
        if obj.get('organization') is not None:
            label['organization'] = obj['organization']
        return label
    label = {}
    for key in IDENTITY_KEYS:
        if key in obj and key != 'groups':
            value = obj[key]
            if not isinstance(value, (dict, list)):
                label[key] = value
    return label or {'identity': 'unnamed'}


def is_list_of_dicts(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return all(isinstance(item, dict) for item in value)


def diff_object_list(
    old_list: list | None,
    new_list: list | None,
    include_absent: bool = False,
) -> tuple[list, list]:
    """Return changed items and a summary of what happened to each.

    Removed objects are included with ``state: absent`` when *include_absent*
    is true.
    """
    old_list = old_list or []
    new_list = new_list or []

    old_by_id = {}
    for item in old_list:
        old_by_id[object_identity(item)] = item

    result = []
    summary = []
    seen = set()

    for item in new_list:
        ident = object_identity(item)
        seen.add(ident)
        old_item = old_by_id.get(ident, _MISSING)
        if old_item is _MISSING:
            result.append(item)
            summary.append({'action': 'added', 'object': identity_label(item)})
        elif to_native(old_item) != to_native(item):
            result.append(item)
            summary.append({'action': 'modified', 'object': identity_label(item)})

    if include_absent:
        for ident, old_item in old_by_id.items():
            if ident in seen:
                continue
            absent = dict(old_item)
            absent['state'] = 'absent'
            result.append(absent)
            summary.append({'action': 'removed', 'object': identity_label(old_item)})

    return result, summary


def diff_var_dicts(
    old_vars: dict,
    new_vars: dict,
    always_keys: set | None = None,
    include_absent: bool = False,
) -> tuple[dict, dict]:
    """Diff two include_vars-style dicts. Omit unchanged object lists."""
    always_keys = set(always_keys or [])
    result = {}
    summary = {}

    for key in always_keys:
        if key in new_vars:
            result[key] = new_vars[key]
            summary[key] = [{'action': 'always_loaded'}]

    keys = set(old_vars) | set(new_vars)
    for key in sorted(keys):
        if key in always_keys:
            continue
        old_val = old_vars.get(key, _MISSING)
        new_val = new_vars.get(key, _MISSING)

        old_is_objects = old_val is not _MISSING and is_list_of_dicts(old_val)
        new_is_objects = new_val is not _MISSING and is_list_of_dicts(new_val)

        if old_is_objects or new_is_objects:
            old_list = old_val if isinstance(old_val, list) else []
            new_list = new_val if isinstance(new_val, list) else []
            changed_items, changes = diff_object_list(
                old_list, new_list, include_absent=include_absent
            )
            if changed_items:
                result[key] = changed_items
                summary[key] = changes
            continue

        if new_val is _MISSING:
            continue
        if old_val is _MISSING or to_native(old_val) != to_native(new_val):
            result[key] = new_val
            summary[key] = [{'action': 'updated'}]

    return result, summary


def merge_loaded_files(
    loaded: list[dict],
    always_load_names: set | None = None,
) -> tuple[dict, set]:
    """Merge file dicts in order (later files win), tracking always-load keys.

    Each item is ``{'path': str, 'data': dict}``.
    """
    always_load_names = set(always_load_names or [])
    merged = {}
    always_keys = set()
    for item in loaded:
        data = item.get('data') or {}
        if not isinstance(data, dict):
            continue
        path = item.get('path') or ''
        if os.path.basename(path) in always_load_names:
            always_keys.update(data.keys())
        merged.update(data)
    return merged, always_keys


def list_yaml_files(directory: str, extensions: list[str]) -> list[str]:
    """Return sorted YAML file paths in a single directory (not recursive)."""
    if not os.path.isdir(directory):
        return []
    files = []
    ext_dot = tuple(f'.{ext.lstrip(".")}' for ext in extensions)
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isfile(path) and name.endswith(ext_dot):
            files.append(path)
    return files


def _git(repo: str, *args: str, check: bool = True) -> str:
    command = ['git', '-c', 'safe.directory=*', '-C', repo, *args]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GitError('git is not installed or not on PATH') from exc
    if check and completed.returncode != 0:
        error = (completed.stderr or completed.stdout or '').strip()
        raise GitError(error or f'git {" ".join(args)} failed')
    if completed.returncode != 0:
        return ''
    return completed.stdout


def git_toplevel(path: str) -> str:
    path = os.path.abspath(path)
    start = path if os.path.isdir(path) else os.path.dirname(path)
    output = _git(start, 'rev-parse', '--show-toplevel')
    return output.strip()


def git_verify_ref(repo: str, ref: str) -> str:
    output = _git(repo, 'rev-parse', '--verify', f'{ref}^{{commit}}')
    sha = output.strip()
    if not sha:
        raise GitError(f'git ref {ref!r} was not found')
    return sha


def git_show_file(repo: str, ref: str, rel_path: str) -> str | None:
    completed = subprocess.run(
        ['git', '-c', 'safe.directory=*', '-C', repo, 'show', f'{ref}:{rel_path}'],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def git_list_files(repo: str, ref: str, rel_dir: str, extensions: list[str]) -> list[str]:
    output = _git(repo, 'ls-tree', '-r', '--name-only', ref, '--', rel_dir, check=False)
    ext_dot = tuple(f'.{ext.lstrip(".")}' for ext in extensions)
    files = [
        line for line in output.splitlines()
        if line.endswith(ext_dot)
    ]
    return sorted(files)


DEFAULT_EXTENSIONS = ['yml', 'yaml']
DEFAULT_ALWAYS_LOAD = ['secrets.yml', 'aap_install.yml']

_YAML_LOADER = None


def _yaml_loader():
    """SafeLoader with Ansible !unsafe and !vault tags (ciphertext if not decrypted)."""
    global _YAML_LOADER
    if _YAML_LOADER is not None:
        return _YAML_LOADER
    try:
        import yaml
    except ImportError as exc:
        raise ValueError('PyYAML is required to parse configuration files') from exc

    class CaCLoader(yaml.SafeLoader):
        pass

    def construct_unsafe(loader, node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        return loader.construct_mapping(node)

    def construct_vault(loader, node):
        return loader.construct_scalar(node)

    CaCLoader.add_constructor('!unsafe', construct_unsafe)
    CaCLoader.add_constructor('!vault', construct_vault)
    _YAML_LOADER = CaCLoader
    return CaCLoader


def parse_yaml(content, filename='<string>'):
    """Parse a YAML mapping from a string. Empty content becomes {}."""
    if content is None or not str(content).strip():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise ValueError('PyYAML is required to parse configuration files') from exc
    try:
        data = yaml.load(content, Loader=_yaml_loader())
    except yaml.YAMLError as exc:
        raise ValueError('failed to parse {0}: {1}'.format(filename, exc)) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError('{0} must contain a YAML mapping at the top level'.format(filename))
    return data


def parse_yaml_file(path):
    with open(path, encoding='utf-8') as handle:
        return parse_yaml(handle.read(), path)


def load_aap_config(
    config_dir,
    env,
    extensions=None,
    changed_only=False,
    git_base='HEAD',
    git_repo=None,
    include_absent=False,
    always_load=None,
    load_file=None,
    load_string=None,
):
    """Load config/all + config/<env> and optionally keep only git-changed objects.

    *load_file* and *load_string* default to PyYAML. The action plugin passes
    Ansible DataLoader callables so vault secrets decrypt the same as include_vars.

    Returns a dict suitable for module exit_json / action plugin result
    (ansible_facts, ansible_included_var_files, aap_config_* keys).
    """
    extensions = list(extensions or DEFAULT_EXTENSIONS)
    always_load = set(always_load if always_load is not None else DEFAULT_ALWAYS_LOAD)
    load_file = load_file or parse_yaml_file
    load_string = load_string or (lambda content, filename: parse_yaml(content, filename))

    config_dir = os.path.abspath(config_dir)
    all_dir = os.path.join(config_dir, 'all')
    env_dir = os.path.join(config_dir, str(env))

    if not os.path.isdir(config_dir):
        raise ValueError('config_dir does not exist: {0}'.format(config_dir))
    if not os.path.isdir(all_dir):
        raise ValueError('common config directory does not exist: {0}'.format(all_dir))
    if not os.path.isdir(env_dir):
        raise ValueError('environment config directory does not exist: {0}'.format(env_dir))

    current_files = list_yaml_files(all_dir, extensions) + list_yaml_files(env_dir, extensions)
    if not current_files:
        raise ValueError('no YAML files found in {0} or {1}'.format(all_dir, env_dir))

    loaded_new = []
    included_files = []
    for path in current_files:
        data = load_file(path)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError('{0} must contain a YAML mapping at the top level'.format(path))
        loaded_new.append({'path': path, 'data': data})
        included_files.append(path)

    new_vars, always_keys = merge_loaded_files(loaded_new, always_load)

    result = {
        'changed': False,
        'ansible_facts': new_vars,
        'ansible_included_var_files': included_files,
        'aap_config_mode': 'full',
        'aap_config_changed_vars': {},
    }

    if not changed_only:
        return result

    repo = os.path.abspath(git_repo or git_toplevel(config_dir))
    resolved_base = git_verify_ref(repo, git_base)

    old_rel_files = git_list_files(
        repo, git_base, os.path.relpath(all_dir, repo), extensions
    ) + git_list_files(
        repo, git_base, os.path.relpath(env_dir, repo), extensions
    )

    loaded_old = []
    for rel_path in old_rel_files:
        content = git_show_file(repo, git_base, rel_path)
        if content is None:
            continue
        data = load_string(content, os.path.join(repo, rel_path))
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(
                'git version of {0} must contain a YAML mapping'.format(rel_path)
            )
        loaded_old.append({'path': rel_path, 'data': data})

    old_vars, _unused = merge_loaded_files(loaded_old, always_load)
    filtered, summary = diff_var_dicts(
        old_vars,
        new_vars,
        always_keys=always_keys,
        include_absent=include_absent,
    )

    result.update({
        'ansible_facts': filtered,
        'aap_config_mode': 'incremental',
        'aap_config_git_base': git_base,
        'aap_config_git_base_sha': resolved_base,
        'aap_config_changed_vars': summary,
    })
    return result
