# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat Automation Community of Practice
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Controller-side wrapper for aap_config_vars.

Resolves playbook_dir and decrypts vault with DataLoader, then runs the same
load_aap_config() implementation as the module.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

from ansible.errors import AnsibleActionFail
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.action import ActionBase

try:
    from ansible_collections.infra.aap_configuration_extended.plugins.module_utils.aap_config_vars import (
        GitError,
        load_aap_config,
    )
except ImportError:
    try:
        from ansible.module_utils.aap_config_vars import GitError, load_aap_config
    except ImportError:
        import importlib.util
        from pathlib import Path

        _utils = Path(__file__).resolve().parent.parent / 'module_utils' / 'aap_config_vars.py'
        _spec = importlib.util.spec_from_file_location('aap_config_vars', _utils)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        GitError = _mod.GitError
        load_aap_config = _mod.load_aap_config


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _requires_connection = False
    _VALID_ARGS = frozenset((
        'config_dir',
        'playbook_dir',
        'env',
        'extensions',
        'changed_only',
        'git_base',
        'git_repo',
        'include_absent',
        'always_load',
    ))

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}

        result = super(ActionModule, self).run(tmp, task_vars)
        self._supports_check_mode = True
        self._supports_async = False

        playbook_dir = self._get_arg('playbook_dir') or task_vars.get('playbook_dir') or os.getcwd()
        config_dir = self._get_arg('config_dir', os.path.join(playbook_dir, '..', 'config'))
        if not os.path.isabs(config_dir):
            config_dir = os.path.abspath(os.path.join(playbook_dir, config_dir))
        else:
            config_dir = os.path.abspath(config_dir)

        env = self._get_arg('env', required=True)

        try:
            payload = load_aap_config(
                config_dir=config_dir,
                env=env,
                extensions=self._as_list(self._get_arg('extensions')),
                changed_only=boolean(self._get_arg('changed_only', False)),
                git_base=self._get_arg('git_base', 'HEAD'),
                git_repo=self._get_arg('git_repo'),
                include_absent=boolean(self._get_arg('include_absent', False)),
                always_load=self._as_list(self._get_arg('always_load')),
                load_file=self._load_file,
                load_string=self._load_string,
            )
        except AnsibleActionFail:
            raise
        except GitError as exc:
            raise AnsibleActionFail(
                'changed_only requires git ({0}). '
                'Set changed_only=false for a full load, or pass a valid git_base.'.format(exc)
            )
        except (OSError, ValueError) as exc:
            raise AnsibleActionFail(str(exc))

        result.update(payload)
        result['_ansible_facts_cacheable'] = False
        return result

    def _get_arg(self, name, default=None, required=False):
        if name not in self._task.args:
            if required:
                raise AnsibleActionFail('missing required argument: {0}'.format(name))
            return default
        value = self._task.args.get(name)
        if value is None:
            if required:
                raise AnsibleActionFail('missing required argument: {0}'.format(name))
            return default
        if isinstance(value, (str, list, dict)):
            return self._templar.template(value)
        return value

    def _as_list(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        if isinstance(value, list):
            return value
        raise AnsibleActionFail('expected a list, got {0}'.format(type(value).__name__))

    def _load_file(self, path):
        try:
            try:
                data = self._loader.load_from_file(
                    path, cache='none', trusted_as_template=True
                )
            except TypeError:
                data = self._loader.load_from_file(path, cache=False)
        except Exception as exc:
            raise AnsibleActionFail('failed to load {0}: {1}'.format(path, exc))
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise AnsibleActionFail(
                '{0} must contain a YAML mapping at the top level'.format(path)
            )
        return data

    def _load_string(self, content, filename):
        try:
            content = self._trust_text(content)
            data = self._loader.load(content, file_name=filename)
        except Exception as exc:
            raise AnsibleActionFail(
                'failed to parse git version of {0}: {1}'.format(filename, exc)
            )
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise AnsibleActionFail(
                'git version of {0} must contain a YAML mapping'.format(filename)
            )
        return data

    @staticmethod
    def _trust_text(content):
        try:
            from ansible._internal._datatag._tags import TrustedAsTemplate
        except ImportError:
            return content
        return TrustedAsTemplate().tag(content)
