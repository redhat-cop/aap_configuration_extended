"""Tests for the config module."""

from __future__ import annotations

import textwrap

import pytest

from aap_config_validate.config import ValidatorConfig, load_config


class TestValidatorConfig:
    def test_should_exclude_file_glob(self):
        cfg = ValidatorConfig(exclude_files=["*.bak", "secrets.yml"])
        assert cfg.should_exclude_file("data/secrets.yml")
        assert cfg.should_exclude_file("something.bak")
        assert not cfg.should_exclude_file("data/valid.yml")

    def test_should_exclude_dir_glob(self):
        cfg = ValidatorConfig(exclude_dirs=["scratch", ".git"])
        assert cfg.should_exclude_dir("scratch")
        assert cfg.should_exclude_dir("project/scratch")
        assert not cfg.should_exclude_dir("production")

    def test_is_var_ignored_exact(self):
        cfg = ValidatorConfig(ignore_vars=["my_custom_var"])
        assert cfg.is_var_ignored("my_custom_var")
        assert not cfg.is_var_ignored("other_var")

    def test_is_var_ignored_glob(self):
        cfg = ValidatorConfig(ignore_vars=["env_*", "ansible_*"])
        assert cfg.is_var_ignored("env_production")
        assert cfg.is_var_ignored("ansible_host")
        assert not cfg.is_var_ignored("controller_projects")

    def test_is_field_ignored_specific_var(self):
        cfg = ValidatorConfig(ignore_fields={"controller_templates": ["custom_field"]})
        assert cfg.is_field_ignored("controller_templates", "custom_field")
        assert not cfg.is_field_ignored("controller_templates", "name")
        assert not cfg.is_field_ignored("controller_projects", "custom_field")

    def test_is_field_ignored_wildcard_var(self):
        cfg = ValidatorConfig(ignore_fields={"*": ["_internal"]})
        assert cfg.is_field_ignored("controller_templates", "_internal")
        assert cfg.is_field_ignored("hub_namespaces", "_internal")

    def test_is_field_ignored_glob_pattern(self):
        cfg = ValidatorConfig(ignore_fields={"controller_templates": ["my_*"]})
        assert cfg.is_field_ignored("controller_templates", "my_field")
        assert not cfg.is_field_ignored("controller_templates", "name")

    def test_is_check_disabled(self):
        cfg = ValidatorConfig(disable_checks=["xref", "types"])
        assert cfg.is_check_disabled("xref")
        assert cfg.is_check_disabled("types")
        assert not cfg.is_check_disabled("var_names")

    def test_defaults(self):
        cfg = ValidatorConfig()
        assert cfg.exclude_files == []
        assert cfg.ignore_vars == []
        assert cfg.ignore_fields == {}
        assert cfg.disable_checks == []
        assert cfg.strict is None
        assert cfg.wildcard_vars is None


class TestLoadConfig:
    def test_load_from_explicit_path(self, tmp_path):
        p = tmp_path / "my-config.yml"
        p.write_text(
            textwrap.dedent("""\
                ignore_vars:
                  - my_var
                strict: true
            """),
            encoding="utf-8",
        )
        cfg = load_config(path=str(p))
        assert cfg.ignore_vars == ["my_var"]
        assert cfg.strict is True

    def test_auto_detect_config_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        p = tmp_path / ".aap-validate.yml"
        p.write_text(
            textwrap.dedent("""\
                exclude_dirs:
                  - scratch
            """),
            encoding="utf-8",
        )
        cfg = load_config()
        assert cfg.exclude_dirs == ["scratch"]

    def test_auto_detect_yaml_extension(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        p = tmp_path / ".aap-validate.yaml"
        p.write_text(
            textwrap.dedent("""\
                show_info: true
            """),
            encoding="utf-8",
        )
        cfg = load_config()
        assert cfg.show_info is True

    def test_no_config_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.exclude_files == []
        assert cfg.ignore_vars == []

    def test_missing_explicit_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(path=str(tmp_path / "nonexistent.yml"))

    def test_full_config(self, tmp_path):
        p = tmp_path / "config.yml"
        p.write_text(
            textwrap.dedent("""\
                exclude_files:
                  - "*.bak"
                exclude_dirs:
                  - scratch
                ignore_vars:
                  - my_custom_*
                ignore_fields:
                  controller_templates:
                    - custom_field
                  "*":
                    - _internal
                disable_checks:
                  - xref
                extra_known_vars:
                  - deployment_env
                strict: true
                show_info: false
                wildcard_vars: always
                output_format: json
                components:
                  - controller
            """),
            encoding="utf-8",
        )
        cfg = load_config(path=str(p))
        assert cfg.exclude_files == ["*.bak"]
        assert cfg.exclude_dirs == ["scratch"]
        assert cfg.ignore_vars == ["my_custom_*"]
        assert cfg.ignore_fields == {"controller_templates": ["custom_field"], "*": ["_internal"]}
        assert cfg.disable_checks == ["xref"]
        assert cfg.extra_known_vars == ["deployment_env"]
        assert cfg.strict is True
        assert cfg.show_info is False
        assert cfg.wildcard_vars == "always"
        assert cfg.output_format == "json"
        assert cfg.components == ["controller"]

    def test_invalid_disable_checks(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text(
            textwrap.dedent("""\
                disable_checks:
                  - bogus_check
            """),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unknown check"):
            load_config(path=str(p))

    def test_invalid_wildcard_vars_value(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text(
            textwrap.dedent("""\
                wildcard_vars: maybe
            """),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="must be auto, always, or never"):
            load_config(path=str(p))

    def test_invalid_output_format_value(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text(
            textwrap.dedent("""\
                output_format: xml
            """),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="must be text or json"):
            load_config(path=str(p))

    def test_string_coerced_to_list(self, tmp_path):
        p = tmp_path / "config.yml"
        p.write_text(
            textwrap.dedent("""\
                ignore_vars: single_var
                exclude_files: single_file.yml
            """),
            encoding="utf-8",
        )
        cfg = load_config(path=str(p))
        assert cfg.ignore_vars == ["single_var"]
        assert cfg.exclude_files == ["single_file.yml"]

    def test_empty_config_file(self, tmp_path):
        p = tmp_path / "empty.yml"
        p.write_text("", encoding="utf-8")
        cfg = load_config(path=str(p))
        assert cfg.exclude_files == []

    def test_non_mapping_raises(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(ValueError, match="expected a YAML mapping"):
            load_config(path=str(p))

    def test_search_dir_parameter(self, tmp_path):
        p = tmp_path / ".aap-validate.yml"
        p.write_text("strict: true\n", encoding="utf-8")
        cfg = load_config(search_dir=tmp_path)
        assert cfg.strict is True


class TestConfigIntegrationWithCLI:
    """Test that config file settings flow through to the CLI."""

    def test_config_ignore_vars_suppresses_warnings(self, tmp_path):
        (tmp_path / ".aap-validate.yml").write_text(
            textwrap.dedent("""\
                ignore_vars:
                  - my_custom_var
            """),
            encoding="utf-8",
        )
        (tmp_path / "data.yml").write_text(
            textwrap.dedent("""\
                my_custom_var: something
            """),
            encoding="utf-8",
        )
        from aap_config_validate.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path / "data.yml"), "--config", str(tmp_path / ".aap-validate.yml"), "--no-color"])
        assert exc_info.value.code == 0

    def test_config_exclude_files(self, tmp_path):
        (tmp_path / ".aap-validate.yml").write_text(
            textwrap.dedent("""\
                exclude_files:
                  - bad.yml
            """),
            encoding="utf-8",
        )
        (tmp_path / "good.yml").write_text(
            textwrap.dedent("""\
                controller_projects:
                  - name: Valid
                    scm_type: git
            """),
            encoding="utf-8",
        )
        (tmp_path / "bad.yml").write_text("this is: not: valid: yaml: {{", encoding="utf-8")
        from aap_config_validate.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path), "--config", str(tmp_path / ".aap-validate.yml"), "--no-color"])
        assert exc_info.value.code == 0

    def test_config_disable_checks(self, tmp_path):
        (tmp_path / ".aap-validate.yml").write_text(
            textwrap.dedent("""\
                disable_checks:
                  - required_fields
            """),
            encoding="utf-8",
        )
        (tmp_path / "data.yml").write_text(
            textwrap.dedent("""\
                controller_credentials:
                  - description: "missing name and credential_type"
            """),
            encoding="utf-8",
        )
        from aap_config_validate.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path / "data.yml"), "--config", str(tmp_path / ".aap-validate.yml"), "--no-color"])
        assert exc_info.value.code == 0

    def test_config_extra_known_vars(self, tmp_path):
        (tmp_path / ".aap-validate.yml").write_text(
            textwrap.dedent("""\
                extra_known_vars:
                  - deployment_environment
            """),
            encoding="utf-8",
        )
        (tmp_path / "data.yml").write_text(
            textwrap.dedent("""\
                deployment_environment: production
            """),
            encoding="utf-8",
        )
        from aap_config_validate.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path / "data.yml"), "--config", str(tmp_path / ".aap-validate.yml"), "--no-color"])
        assert exc_info.value.code == 0
