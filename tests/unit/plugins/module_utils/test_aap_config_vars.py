# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat Automation Community of Practice
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Tests for aap_config_vars module_utils."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml  # noqa: F401

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from ansible_collections.infra.aap_configuration_extended.plugins.module_utils import aap_config_vars as diff
except ImportError:
    ROOT = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(ROOT / 'plugins' / 'module_utils'))
    import aap_config_vars as diff  # noqa: E402


def _git(repo, *args):
    subprocess.run(
        ['git', '-c', 'safe.directory=*', '-C', repo, *args],
        check=True,
        capture_output=True,
        text=True,
    )


class IdentityTest(unittest.TestCase):
    def test_named_object_uses_name_and_org(self):
        left = {'name': 'aap_config', 'organization': 'config_as_code', 'playbook': 'a.yml'}
        right = {'name': 'aap_config', 'organization': 'config_as_code', 'playbook': 'b.yml'}
        self.assertEqual(diff.object_identity(left), diff.object_identity(right))

    def test_different_names_are_different_objects(self):
        left = {'name': 'aap_config'}
        right = {'name': 'build_ee'}
        self.assertNotEqual(diff.object_identity(left), diff.object_identity(right))

    def test_role_assignment_identity(self):
        execute = {'team': 'admins', 'organization': 'config_as_code', 'role': 'execute'}
        admin = {'team': 'admins', 'organization': 'config_as_code', 'role': 'admin'}
        self.assertNotEqual(diff.object_identity(execute), diff.object_identity(admin))
        self.assertEqual(
            diff.object_identity(execute),
            diff.object_identity(dict(execute, extra='ignored-for-identity')),
        )

    def test_identity_label_prefers_name(self):
        self.assertEqual(
            diff.identity_label({'name': 'jt', 'organization': 'org', 'extra_vars': {'p': 'secret'}}),
            {'name': 'jt', 'organization': 'org'},
        )


class ObjectListDiffTest(unittest.TestCase):
    def test_added_modified_unchanged(self):
        old = [
            {'name': 'keep', 'verbosity': 0},
            {'name': 'edit', 'verbosity': 0},
        ]
        new = [
            {'name': 'keep', 'verbosity': 0},
            {'name': 'edit', 'verbosity': 1},
            {'name': 'add', 'verbosity': 0},
        ]
        changed, summary = diff.diff_object_list(old, new)
        names = [item['name'] for item in changed]
        self.assertEqual(names, ['edit', 'add'])
        actions = [item['action'] for item in summary]
        self.assertEqual(actions, ['modified', 'added'])

    def test_removed_omitted_by_default(self):
        old = [{'name': 'gone'}, {'name': 'stay'}]
        new = [{'name': 'stay'}]
        changed, summary = diff.diff_object_list(old, new)
        self.assertEqual(changed, [])
        self.assertEqual(summary, [])

    def test_removed_emits_absent(self):
        old = [{'name': 'gone', 'project': 'p'}, {'name': 'stay'}]
        new = [{'name': 'stay'}]
        changed, summary = diff.diff_object_list(old, new, include_absent=True)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]['name'], 'gone')
        self.assertEqual(changed[0]['state'], 'absent')
        self.assertEqual(summary[0]['action'], 'removed')


class VarDictDiffTest(unittest.TestCase):
    def test_omits_unchanged_object_list(self):
        projects = [{'name': 'config_as_code', 'scm_url': 'https://example.com'}]
        old = {'controller_projects_all': projects, 'controller_templates_all': [{'name': 'a'}]}
        new = {'controller_projects_all': projects, 'controller_templates_all': [{'name': 'a', 'verbosity': 1}]}
        result, summary = diff.diff_var_dicts(old, new)
        self.assertNotIn('controller_projects_all', result)
        self.assertEqual(result['controller_templates_all'][0]['name'], 'a')
        self.assertEqual(summary['controller_templates_all'][0]['action'], 'modified')

    def test_always_keys_copied_even_when_unchanged(self):
        old = {'console_token': 'a', 'controller_templates_all': [{'name': 'a'}]}
        new = {'console_token': 'a', 'controller_templates_all': [{'name': 'a'}]}
        result, summary = diff.diff_var_dicts(old, new, always_keys={'console_token'})
        self.assertEqual(result['console_token'], 'a')
        self.assertNotIn('controller_templates_all', result)
        self.assertEqual(summary['console_token'][0]['action'], 'always_loaded')

    def test_settings_dict_included_when_changed(self):
        old = {'controller_settings_all': {'settings': {'GALAXY_IGNORE_CERTS': True}}}
        new = {'controller_settings_all': {'settings': {'GALAXY_IGNORE_CERTS': False}}}
        result, _summary = diff.diff_var_dicts(old, new)
        self.assertEqual(
            result['controller_settings_all']['settings']['GALAXY_IGNORE_CERTS'],
            False,
        )

    def test_settings_dict_omitted_when_unchanged(self):
        settings = {'controller_settings_all': {'settings': {'GALAXY_IGNORE_CERTS': True}}}
        result, summary = diff.diff_var_dicts(settings, settings)
        self.assertEqual(result, {})
        self.assertEqual(summary, {})

    def test_empty_object_list_omitted(self):
        result, _summary = diff.diff_var_dicts(
            {'controller_schedules_all': []},
            {'controller_schedules_all': []},
        )
        self.assertEqual(result, {})


class MergeFilesTest(unittest.TestCase):
    def test_later_file_wins_and_always_keys_tracked(self):
        loaded = [
            {'path': '/config/all/controller_license.yml', 'data': {'controller_license': {}}},
            {'path': '/config/dev/secrets.yml', 'data': {'console_token': 'enc', 'aap_pass': 'x'}},
            {'path': '/config/dev/controller_license.yml', 'data': {'controller_license': {'pool': '1'}}},
        ]
        merged, always_keys = diff.merge_loaded_files(loaded, {'secrets.yml'})
        self.assertEqual(merged['controller_license'], {'pool': '1'})
        self.assertEqual(always_keys, {'console_token', 'aap_pass'})


class GitHelpersTest(unittest.TestCase):
    def test_show_and_list_and_incremental_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = tmp
            _git(repo, 'init', '-b', 'main')
            _git(repo, 'config', 'user.email', 'test@example.com')
            _git(repo, 'config', 'user.name', 'test')

            all_dir = Path(repo) / 'config' / 'all'
            env_dir = Path(repo) / 'config' / 'dev'
            all_dir.mkdir(parents=True)
            env_dir.mkdir(parents=True)

            (all_dir / 'controller_job_templates.yml').write_text(
                'controller_templates_all:\n'
                '  - name: keep\n'
                '    verbosity: 0\n'
                '  - name: edit\n'
                '    verbosity: 0\n',
                encoding='utf-8',
            )
            (env_dir / 'secrets.yml').write_text('console_token: old\n', encoding='utf-8')
            _git(repo, 'add', '.')
            _git(repo, 'commit', '-m', 'base')

            (all_dir / 'controller_job_templates.yml').write_text(
                'controller_templates_all:\n'
                '  - name: keep\n'
                '    verbosity: 0\n'
                '  - name: edit\n'
                '    verbosity: 1\n'
                '  - name: added\n'
                '    verbosity: 0\n',
                encoding='utf-8',
            )
            (env_dir / 'secrets.yml').write_text('console_token: new\n', encoding='utf-8')

            files = diff.git_list_files(repo, 'HEAD', 'config/all', ['yml'])
            self.assertEqual(files, ['config/all/controller_job_templates.yml'])

            old_content = diff.git_show_file(repo, 'HEAD', 'config/all/controller_job_templates.yml')
            self.assertIn('verbosity: 0', old_content)
            self.assertNotIn('added', old_content)

            old_vars = {
                'controller_templates_all': [
                    {'name': 'keep', 'verbosity': 0},
                    {'name': 'edit', 'verbosity': 0},
                ],
                'console_token': 'old',
            }
            new_vars = {
                'controller_templates_all': [
                    {'name': 'keep', 'verbosity': 0},
                    {'name': 'edit', 'verbosity': 1},
                    {'name': 'added', 'verbosity': 0},
                ],
                'console_token': 'new',
            }
            result, summary = diff.diff_var_dicts(old_vars, new_vars, always_keys={'console_token'})
            self.assertEqual(result['console_token'], 'new')
            names = [item['name'] for item in result['controller_templates_all']]
            self.assertEqual(names, ['edit', 'added'])
            self.assertEqual(
                [item['action'] for item in summary['controller_templates_all']],
                ['modified', 'added'],
            )

            self.assertEqual(diff.git_toplevel(str(all_dir)), os.path.realpath(repo))
            sha = diff.git_verify_ref(repo, 'HEAD')
            self.assertEqual(len(sha), 40)


@unittest.skipUnless(HAS_YAML, 'PyYAML is required')
class ParseYamlTest(unittest.TestCase):
    def test_unsafe_and_vault_tags(self):
        data = diff.parse_yaml(
            'name: !unsafe "{{ password }}"\n'
            'token: !vault |\n'
            '  $ANSIBLE_VAULT;1.1;AES256\n'
            '  616263\n'
        )
        self.assertEqual(data['name'], '{{ password }}')
        self.assertIn('ANSIBLE_VAULT', data['token'])

    def test_empty_is_dict(self):
        self.assertEqual(diff.parse_yaml(''), {})
        self.assertEqual(diff.parse_yaml('---\n'), {})


@unittest.skipUnless(HAS_YAML, 'PyYAML is required')
class LoadAapConfigTest(unittest.TestCase):
    def test_incremental_load_keeps_changed_objects_and_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = tmp
            _git(repo, 'init', '-b', 'main')
            _git(repo, 'config', 'user.email', 'test@example.com')
            _git(repo, 'config', 'user.name', 'test')

            all_dir = Path(repo) / 'config' / 'all'
            env_dir = Path(repo) / 'config' / 'dev'
            all_dir.mkdir(parents=True)
            env_dir.mkdir(parents=True)
            (all_dir / 'controller_job_templates.yml').write_text(
                'controller_templates_all:\n'
                '  - name: keep\n    verbosity: 0\n'
                '  - name: edit\n    verbosity: 0\n',
                encoding='utf-8',
            )
            (all_dir / 'controller_projects.yml').write_text(
                'controller_projects_all:\n  - name: config_as_code\n    scm_url: https://example.com\n',
                encoding='utf-8',
            )
            (env_dir / 'secrets.yml').write_text('console_token: old\n', encoding='utf-8')
            _git(repo, 'add', '.')
            _git(repo, 'commit', '-m', 'base')

            (all_dir / 'controller_job_templates.yml').write_text(
                'controller_templates_all:\n'
                '  - name: keep\n    verbosity: 0\n'
                '  - name: edit\n    verbosity: 1\n'
                '  - name: added\n    verbosity: 0\n',
                encoding='utf-8',
            )
            (env_dir / 'secrets.yml').write_text('console_token: new\n', encoding='utf-8')

            full = diff.load_aap_config(str(Path(repo) / 'config'), 'dev', changed_only=False)
            self.assertEqual(full['aap_config_mode'], 'full')
            self.assertEqual(len(full['ansible_facts']['controller_templates_all']), 3)
            self.assertIn('controller_projects_all', full['ansible_facts'])

            incremental = diff.load_aap_config(str(Path(repo) / 'config'), 'dev', changed_only=True, git_base='HEAD')
            self.assertEqual(incremental['aap_config_mode'], 'incremental')
            names = [item['name'] for item in incremental['ansible_facts']['controller_templates_all']]
            self.assertEqual(names, ['edit', 'added'])
            self.assertEqual(incremental['ansible_facts']['console_token'], 'new')
            self.assertNotIn('controller_projects_all', incremental['ansible_facts'])


if __name__ == '__main__':
    unittest.main()
