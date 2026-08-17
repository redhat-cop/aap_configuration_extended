"""Tests for the CLI entry point."""

from __future__ import annotations

import textwrap

import pytest

from aap_config_validate.cli import main


@pytest.fixture()
def config_dir(tmp_path):
    """Create a temp config directory with a simple valid config."""
    p = tmp_path / "valid.yml"
    p.write_text(
        textwrap.dedent("""\
            controller_projects:
              - name: Test Project
                scm_type: git
        """),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def bad_config_dir(tmp_path):
    """Create a temp config directory with invalid config."""
    p = tmp_path / "bad.yml"
    p.write_text(
        textwrap.dedent("""\
            controller_credentials:
              - description: "missing name and credential_type"
        """),
        encoding="utf-8",
    )
    return tmp_path


class TestCLI:
    def test_valid_config_exit_0(self, config_dir):
        with pytest.raises(SystemExit) as exc_info:
            main([str(config_dir), "--no-color"])
        assert exc_info.value.code == 0

    def test_invalid_config_exit_1(self, bad_config_dir):
        with pytest.raises(SystemExit) as exc_info:
            main([str(bad_config_dir), "--no-color"])
        assert exc_info.value.code == 1

    def test_strict_mode(self, config_dir):
        # config_dir has no org defined, so xref to org is an INFO, not a warning
        # add a config that generates a warning
        (config_dir / "warn.yml").write_text(
            textwrap.dedent("""\
                controller_templates:
                  - name: JT1
                    projet: Typo
            """),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            main([str(config_dir), "--strict", "--no-color"])
        assert exc_info.value.code == 1

    def test_json_format(self, config_dir, capsys):
        with pytest.raises(SystemExit):
            main([str(config_dir), "--format", "json"])
        import json

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "summary" in data

    def test_component_filter(self, bad_config_dir):
        # The bad config only has controller_credentials with errors.
        # Filtering to EDA should skip those.
        with pytest.raises(SystemExit) as exc_info:
            main([str(bad_config_dir), "--component", "eda", "--no-color"])
        assert exc_info.value.code == 0

    def test_wildcard_vars_always(self, tmp_path):
        (tmp_path / "wildcard.yml").write_text(
            textwrap.dedent("""\
                controller_templates:
                  - name: JT-base
                controller_templates_extra:
                  - name: JT-extra
            """),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path), "--wildcard-vars", "always", "--no-color"])
        assert exc_info.value.code == 0

    def test_wildcard_vars_auto_enabled(self, tmp_path):
        (tmp_path / "wildcard.yml").write_text(
            textwrap.dedent("""\
                dispatch_include_wildcard_vars: true
                controller_credentials_extra:
                  - name: cred1
                    credential_type: Machine
            """),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path), "--no-color"])
        assert exc_info.value.code == 0

    def test_wildcard_vars_auto_merges_without_flag(self, tmp_path):
        (tmp_path / "wildcard.yml").write_text(
            textwrap.dedent("""\
                controller_credentials_all:
                  - name: cred1
                    credential_type: Machine
            """),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path), "--no-color"])
        assert exc_info.value.code == 0

    def test_source_file_in_output(self, bad_config_dir, capsys):
        with pytest.raises(SystemExit):
            main([str(bad_config_dir), "--no-color"])
        captured = capsys.readouterr()
        assert "bad.yml" in captured.out

    def test_missing_config_file_exit_1(self, config_dir, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([str(config_dir), "--config", "/no/such/aap-validate.yml", "--no-color"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "not found" in captured.out.lower()

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "0.2.0" in captured.out

    def test_wildcard_vars_never(self, tmp_path):
        (tmp_path / "wildcard.yml").write_text(
            textwrap.dedent("""\
                controller_templates_extra:
                  - name: JT-extra
            """),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path), "--wildcard-vars", "never", "--no-color"])
        assert exc_info.value.code == 0
