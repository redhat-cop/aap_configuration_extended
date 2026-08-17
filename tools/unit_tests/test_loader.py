"""Tests for the YAML loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aap_config_validate.loader import is_jinja, load_paths, load_yaml_file


@pytest.fixture()
def tmp_yaml(tmp_path):
    """Write a YAML file and return its path."""

    def _write(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p

    _write.dir = tmp_path
    return _write


class TestIsJinja:
    def test_plain_string(self):
        assert not is_jinja("hello")

    def test_jinja_expression(self):
        assert is_jinja("{{ foo }}")

    def test_jinja_embedded(self):
        assert is_jinja("prefix-{{ bar }}-suffix")

    def test_lookup(self):
        assert is_jinja("lookup('env', 'HOME')")

    def test_non_string(self):
        assert not is_jinja(42)
        assert not is_jinja(None)


class TestLoadYamlFile:
    def test_simple_file(self, tmp_yaml):
        p = tmp_yaml(
            "test.yml",
            """\
            controller_projects:
              - name: My Project
                scm_type: git
            ...
        """,
        )
        data = load_yaml_file(p)
        assert "controller_projects" in data
        assert data["controller_projects"][0]["name"] == "My Project"

    def test_jinja_values_preserved(self, tmp_yaml):
        p = tmp_yaml(
            "jinja.yml",
            """\
            controller_credentials:
              - name: cred1
                credential_type: Machine
                inputs:
                  password: "{{ vault_password }}"
            ...
        """,
        )
        data = load_yaml_file(p)
        assert data["controller_credentials"][0]["inputs"]["password"] == "{{ vault_password }}"

    def test_unsafe_tag(self, tmp_yaml):
        p = tmp_yaml(
            "unsafe.yml",
            """\
            controller_credentials:
              - name: cred1
                credential_type: Machine
                inputs:
                  password: !unsafe "s3cret{{"
            ...
        """,
        )
        data = load_yaml_file(p)
        assert data["controller_credentials"][0]["inputs"]["password"] == "s3cret{{"

    def test_empty_file(self, tmp_yaml):
        p = tmp_yaml("empty.yml", "---\n...\n")
        data = load_yaml_file(p)
        assert data == {}

    def test_bad_yaml(self, tmp_yaml):
        p = tmp_yaml("bad.yml", "{{{\n")
        with pytest.raises(ValueError, match="Failed to parse"):
            load_yaml_file(p)

    def test_vault_block_scalar(self, tmp_yaml):
        p = tmp_yaml(
            "vault.yml",
            """\
            controller_credentials:
              - name: cred1
                credential_type: Machine
                inputs:
                  password: !vault |
                    $ANSIBLE_VAULT;1.1;AES256
                    6632643864386130
            ...
        """,
        )
        data = load_yaml_file(p)
        assert "ANSIBLE_VAULT" in data["controller_credentials"][0]["inputs"]["password"]

    def test_list_sources_tracked(self, tmp_yaml):
        tmp_yaml(
            "a.yml",
            """\
            controller_projects:
              - name: P1
        """,
        )
        tmp_yaml(
            "b.yml",
            """\
            controller_projects:
              - name: P2
        """,
        )
        config, errors, sources = load_paths([str(tmp_yaml.dir)])
        assert not errors
        assert sources["controller_projects"][0].endswith("a.yml")
        assert sources["controller_projects"][1].endswith("b.yml")

    def test_dict_deep_merge(self, tmp_yaml):
        tmp_yaml(
            "a.yml",
            """\
            controller_settings:
              settings:
                KEY_A: 1
                NESTED:
                  X: 1
        """,
        )
        tmp_yaml(
            "b.yml",
            """\
            controller_settings:
              settings:
                KEY_B: 2
                NESTED:
                  Y: 2
        """,
        )
        config, errors, _sources = load_paths([str(tmp_yaml.dir)])
        assert not errors
        settings = config["controller_settings"]["settings"]
        assert settings["KEY_A"] == 1
        assert settings["KEY_B"] == 2
        assert settings["NESTED"]["X"] == 1
        assert settings["NESTED"]["Y"] == 2

    def test_dir_scan_skips_secrets_by_default(self, tmp_yaml):
        tmp_yaml(
            "good.yml",
            """\
            controller_projects:
              - name: P1
        """,
        )
        tmp_yaml(
            "secrets.yml",
            """\
            super_secret: !vault |
              $ANSIBLE_VAULT;1.1;AES256
              abc
        """,
        )
        config, errors, _sources = load_paths([str(tmp_yaml.dir)])
        assert not errors
        assert "controller_projects" in config
        assert "super_secret" not in config

    def test_nested_exclude_dirs(self, tmp_yaml):
        from aap_config_validate.config import ValidatorConfig

        nested = tmp_yaml.dir / "tests" / "fixtures"
        nested.mkdir(parents=True)
        (nested / "bad.yml").write_text("controller_projects: not-a-list\n", encoding="utf-8")
        tmp_yaml(
            "ok.yml",
            """\
            controller_projects:
              - name: P1
        """,
        )
        cfg = ValidatorConfig(exclude_dirs=["tests/fixtures"])
        config, errors, _sources = load_paths([str(tmp_yaml.dir)], cfg=cfg)
        assert not errors
        assert len(config["controller_projects"]) == 1

    def test_directory(self, tmp_yaml):
        tmp_yaml(
            "a.yml",
            """\
            controller_projects:
              - name: P1
        """,
        )
        tmp_yaml(
            "b.yml",
            """\
            controller_inventories:
              - name: I1
                organization: Default
        """,
        )
        config, errors, _sources = load_paths([str(tmp_yaml.dir)])
        assert not errors
        assert "controller_projects" in config
        assert "controller_inventories" in config

    def test_list_merging(self, tmp_yaml):
        tmp_yaml(
            "a.yml",
            """\
            controller_projects:
              - name: P1
        """,
        )
        tmp_yaml(
            "b.yml",
            """\
            controller_projects:
              - name: P2
        """,
        )
        config, errors, _sources = load_paths([str(tmp_yaml.dir)])
        assert not errors
        assert len(config["controller_projects"]) == 2

    def test_nonexistent_path(self):
        config, errors, _sources = load_paths(["/nonexistent/path"])
        assert config == {}
        assert len(errors) == 1
        assert "not found" in errors[0]
