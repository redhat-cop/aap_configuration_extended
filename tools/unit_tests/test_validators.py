"""Tests for the validation engine."""

from __future__ import annotations

import pytest

from aap_config_validate.models import Severity
from aap_config_validate.validators import (
    is_wildcard_var,
    merge_wildcard_vars,
    validate,
)


class TestVariableNameCheck:
    def test_known_var_no_warning(self):
        config = {"controller_projects": [{"name": "P1", "scm_type": "git"}]}
        issues = validate(config)
        assert not any(i.severity is Severity.WARNING and "unknown variable" in i.message for i in issues)

    def test_unknown_var_warns(self):
        config = {"controller_projet": [{"name": "P1"}]}
        issues = validate(config)
        warnings = [i for i in issues if "unknown variable" in i.message]
        assert len(warnings) == 1
        assert warnings[0].suggestion and "controller_projects" in warnings[0].suggestion

    def test_legacy_alias_accepted(self):
        config = {"job_templates": [{"name": "JT1"}]}
        issues = validate(config)
        assert not any(i.severity is Severity.WARNING and "unknown variable" in i.message for i in issues)

    def test_global_vars_accepted(self):
        config = {
            "aap_hostname": "https://aap.example.com",
            "platform_state": "present",
        }
        issues = validate(config)
        assert not issues


class TestStructuralCheck:
    def test_list_expected_but_got_string(self):
        config = {"controller_projects": "not a list"}
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR and "expected a list" in i.message]
        assert len(errors) == 1

    def test_dict_items_expected(self):
        config = {"controller_projects": ["not a dict"]}
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR and "expected a dict" in i.message]
        assert len(errors) == 1

    def test_settings_dict_accepted(self):
        config = {"controller_settings": {"AWX_TASK_ENV": {"FOO": "bar"}}}
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors


class TestRequiredFields:
    def test_missing_name(self):
        config = {"controller_projects": [{"scm_type": "git"}]}
        issues = validate(config)
        errors = [i for i in issues if "missing required field" in i.message and '"name"' in i.message]
        assert len(errors) == 1

    def test_missing_credential_type(self):
        config = {"controller_credentials": [{"name": "cred1"}]}
        issues = validate(config)
        errors = [i for i in issues if "missing required field" in i.message and '"credential_type"' in i.message]
        assert len(errors) == 1

    def test_all_required_present(self):
        config = {"controller_credentials": [{"name": "cred1", "credential_type": "Machine"}]}
        issues = validate(config)
        errors = [i for i in issues if "missing required field" in i.message]
        assert not errors


class TestTypeCheck:
    def test_wrong_type_warns(self):
        config = {"controller_instances": [{"hostname": "h1", "enabled": ["not", "a", "bool"]}]}
        issues = validate(config)
        warnings = [i for i in issues if "expected type" in i.message]
        assert len(warnings) == 1

    def test_jinja_skipped(self):
        config = {"controller_instances": [{"hostname": "h1", "enabled": "{{ my_bool }}"}]}
        issues = validate(config)
        assert not any(i.severity is Severity.WARNING and "expected type" in i.message for i in issues)
        info = [i for i in issues if i.severity is Severity.INFO and "Jinja" in i.message]
        assert len(info) == 1

    def test_str_or_dict_accepted(self):
        config = {"controller_templates": [{"name": "JT1", "organization": {"name": "Org1"}}]}
        issues = validate(config)
        assert not any(i.severity is Severity.WARNING and "expected type" in i.message for i in issues)


class TestUnknownFields:
    def test_typo_detected(self):
        config = {"controller_projects": [{"name": "P1", "scm_tpe": "git"}]}
        issues = validate(config)
        warnings = [i for i in issues if "not recognised" in i.message and "scm_tpe" in i.message]
        assert len(warnings) == 1
        assert warnings[0].suggestion and "scm_type" in warnings[0].suggestion

    def test_known_field_no_warning(self):
        config = {"controller_projects": [{"name": "P1", "scm_type": "git"}]}
        issues = validate(config)
        assert not any("not recognised" in i.message for i in issues)


class TestStateValidation:
    def test_invalid_state(self):
        config = {"controller_projects": [{"name": "P1", "state": "invalid"}]}
        issues = validate(config)
        errors = [i for i in issues if "invalid state" in i.message]
        assert len(errors) == 1

    def test_valid_state(self):
        config = {"controller_projects": [{"name": "P1", "state": "present"}]}
        issues = validate(config)
        assert not any("invalid state" in i.message for i in issues)


class TestChoiceValidation:
    def test_invalid_job_type(self):
        config = {"controller_templates": [{"name": "JT1", "job_type": "invalid"}]}
        issues = validate(config)
        errors = [i for i in issues if "not in allowed choices" in i.message]
        assert len(errors) == 1

    def test_valid_job_type(self):
        config = {"controller_templates": [{"name": "JT1", "job_type": "run"}]}
        issues = validate(config)
        assert not any("not in allowed choices" in i.message for i in issues)

    def test_valid_verbosity(self):
        config = {"controller_templates": [{"name": "JT1", "verbosity": 3}]}
        issues = validate(config)
        assert not any("not in allowed choices" in i.message for i in issues)

    def test_invalid_verbosity(self):
        config = {"controller_templates": [{"name": "JT1", "verbosity": 9}]}
        issues = validate(config)
        errors = [i for i in issues if "not in allowed choices" in i.message]
        assert len(errors) == 1


class TestCrossReferences:
    def test_xref_found(self):
        config = {
            "controller_projects": [{"name": "My Project", "organization": "Org1"}],
            "aap_organizations": [{"name": "Org1"}],
        }
        issues = validate(config)
        assert not any("not found in" in i.message for i in issues)

    def test_xref_missing(self):
        config = {
            "controller_projects": [{"name": "My Project", "organization": "Missing Org"}],
            "aap_organizations": [{"name": "Org1"}],
        }
        issues = validate(config)
        warnings = [i for i in issues if "not found in" in i.message]
        assert len(warnings) == 1
        assert "Missing Org" in warnings[0].message

    def test_xref_target_undefined_is_info(self):
        config = {
            "controller_projects": [{"name": "My Project", "organization": "Some Org"}],
        }
        issues = validate(config)
        info = [i for i in issues if i.severity is Severity.INFO and "not defined in config" in i.message]
        assert len(info) == 1

    def test_xref_with_dict_value(self):
        config = {
            "controller_templates": [{"name": "JT1", "organization": {"name": "Org1"}}],
            "aap_organizations": [{"name": "Org1"}],
        }
        issues = validate(config)
        assert not any("not found in" in i.message for i in issues)


class TestComponentFilter:
    def test_only_controller(self):
        config = {
            "controller_projects": [{"name": "P1"}],
            "eda_projects": [{}],  # missing name — should NOT error when filtered
        }
        issues = validate(config, components=["controller"])
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors

    def test_only_eda(self):
        config = {
            "controller_projects": [{}],  # missing name
            "eda_projects": [{"name": "EP1"}],
        }
        issues = validate(config, components=["eda"])
        errors = [i for i in issues if i.severity is Severity.ERROR and "missing required" in i.message]
        assert not errors


class TestWildcardVarDetection:
    def test_suffixed_var_detected(self):
        assert is_wildcard_var("controller_templates_production") == "controller_templates"

    def test_base_var_not_wildcard(self):
        assert is_wildcard_var("controller_templates") is None

    def test_secure_logging_excluded(self):
        assert is_wildcard_var("controller_templates_secure_logging") is None

    def test_known_global_not_wildcard(self):
        assert is_wildcard_var("controller_settings_individuale") is None

    def test_empty_list_overlay_on_dict_settings(self):
        config = {
            "controller_settings": {"settings": {"FOO": True}},
            "controller_settings_dev": [],
        }
        merged, issues = merge_wildcard_vars(config)
        assert not any(i.severity is Severity.ERROR for i in issues)
        assert merged["controller_settings"]["settings"]["FOO"] is True
        assert "controller_settings_dev" not in merged

    def test_longer_base_preferred(self):
        # controller_inventory_sources should match before controller_inventories
        assert is_wildcard_var("controller_inventory_sources_extra") == "controller_inventory_sources"

    def test_gateway_var(self):
        assert is_wildcard_var("aap_organizations_emea") == "aap_organizations"

    def test_eda_var(self):
        assert is_wildcard_var("eda_projects_team_a") == "eda_projects"

    def test_hub_var(self):
        assert is_wildcard_var("hub_ee_registries_internal") == "hub_ee_registries"


class TestWildcardVarMerging:
    def test_lists_merged(self):
        config = {
            "controller_templates": [{"name": "JT1"}],
            "controller_templates_prod": [{"name": "JT2"}],
            "controller_templates_staging": [{"name": "JT3"}],
        }
        merged, issues = merge_wildcard_vars(config)
        assert not any(i.severity is Severity.ERROR for i in issues)
        assert "controller_templates_prod" not in merged
        assert "controller_templates_staging" not in merged
        names = [item["name"] for item in merged["controller_templates"]]
        assert "JT1" in names
        assert "JT2" in names
        assert "JT3" in names

    def test_creates_base_if_missing(self):
        config = {
            "controller_projects_team_a": [{"name": "P1"}],
            "controller_projects_team_b": [{"name": "P2"}],
        }
        merged, issues = merge_wildcard_vars(config)
        assert not any(i.severity is Severity.ERROR for i in issues)
        assert "controller_projects" in merged
        assert len(merged["controller_projects"]) == 2

    def test_dict_merging(self):
        config = {
            "controller_settings": {"AWX_PROOT_ENABLED": True},
            "controller_settings_extra": {"AWX_TASK_ENV": {"FOO": "bar"}},
        }
        merged, issues = merge_wildcard_vars(config)
        assert not any(i.severity is Severity.ERROR for i in issues)
        assert "AWX_PROOT_ENABLED" in merged["controller_settings"]
        assert "AWX_TASK_ENV" in merged["controller_settings"]

    def test_type_mismatch_errors(self):
        config = {
            "controller_templates": [{"name": "JT1"}],
            "controller_templates_bad": {"not": "a list"},
        }
        merged, issues = merge_wildcard_vars(config)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert len(errors) == 1
        assert "list" in errors[0].message

    def test_merged_items_validated(self):
        config = {
            "controller_credentials_extra": [{"name": "cred1"}],
        }
        merged, merge_issues = merge_wildcard_vars(config)
        issues = validate(merged)
        # cred1 is missing credential_type — should be caught
        errors = [i for i in issues if "missing required field" in i.message and '"credential_type"' in i.message]
        assert len(errors) == 1

    def test_wildcard_var_no_unknown_warning(self):
        config = {
            "controller_templates_production": [{"name": "JT1"}],
        }
        issues = validate(config)
        assert not any(i.severity is Severity.WARNING and "unknown variable" in i.message for i in issues)

    def test_xrefs_work_across_wildcard_merged_data(self):
        config = {
            "dispatch_include_wildcard_vars": True,
            "aap_organizations_emea": [{"name": "EMEA Org"}],
            "controller_projects_emea": [{"name": "EMEA Project", "organization": "EMEA Org"}],
        }
        merged, merge_issues = merge_wildcard_vars(config)
        issues = validate(merged)
        # The xref from project -> org should resolve after merging
        assert not any(i.severity is Severity.WARNING and "not found in" in i.message and "EMEA Org" in i.message for i in issues)


class TestRepoConfigs:
    """Smoke test: run validator against this collection's filetree/roundtrip configs."""

    @pytest.fixture()
    def repo_root(self):
        from pathlib import Path

        return Path(__file__).resolve().parents[2]

    def test_roundtrip_configs_no_errors(self, repo_root):
        from aap_config_validate.loader import load_paths

        roundtrip = repo_root / "tests" / "configs" / "roundtrip"
        if not roundtrip.is_dir():
            pytest.skip("roundtrip configs not present")
        config, load_errors, sources = load_paths([str(roundtrip)])
        assert not load_errors
        merged, merge_issues = merge_wildcard_vars(config, sources=sources)
        issues = list(merge_issues) + validate(merged, sources=sources)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors, [f"{e.source}: {e.path}: {e.message}" for e in errors]


class TestScalarCoercion:
    def test_quoted_int_accepted(self):
        config = {"controller_instances": [{"hostname": "h1", "listener_port": "27199"}]}
        issues = validate(config)
        assert not any("expected type" in i.message for i in issues)

    def test_quoted_bool_accepted(self):
        config = {"controller_instances": [{"hostname": "h1", "enabled": "False"}]}
        issues = validate(config)
        assert not any("expected type" in i.message for i in issues)

    def test_json_object_string_accepted_as_dict(self):
        config = {"gateway_authenticators": [{"name": "local", "configuration": "{}"}]}
        issues = validate(config)
        assert not any("expected type" in i.message for i in issues)

    def test_empty_string_skips_choice(self):
        config = {"controller_execution_environments": [{"name": "EE", "image": "img", "pull": ""}]}
        issues = validate(config)
        assert not any("not in allowed choices" in i.message for i in issues)

    def test_bool_not_accepted_as_int(self):
        config = {"controller_templates": [{"name": "JT1", "verbosity": True}]}
        issues = validate(config)
        assert any("expected type" in i.message for i in issues)

    def test_empty_string_required_field_is_missing(self):
        config = {"controller_projects": [{"name": ""}]}
        issues = validate(config)
        assert any("missing required field" in i.message and '"name"' in i.message for i in issues)


class TestAliasesAndXref:
    def test_gateway_organizations_alias(self):
        config = {
            "gateway_organizations": [{"name": "Org1"}],
            "controller_projects": [{"name": "P1", "organization": "Org1"}],
        }
        issues = validate(config)
        assert not any("unknown variable" in i.message for i in issues)
        assert not any("not found in" in i.message for i in issues)
        assert not any("missing required" in i.message for i in issues)

    def test_component_filter_still_indexes_orgs(self):
        config = {
            "aap_organizations": [{"name": "Org1"}],
            "controller_projects": [{"name": "P1", "organization": "Org1"}],
        }
        issues = validate(config, components=["controller"])
        assert not any("not found in" in i.message for i in issues)
        assert not any("not defined in config" in i.message for i in issues)

    def test_state_absent_skips_other_required(self):
        config = {"controller_credentials": [{"name": "old", "state": "absent"}]}
        issues = validate(config)
        assert not any("missing required field" in i.message and "credential_type" in i.message for i in issues)

    def test_duplicate_names_warn(self):
        config = {"controller_projects": [{"name": "P1"}, {"name": "P1"}]}
        issues = validate(config)
        assert any("duplicate" in i.message for i in issues)

    def test_role_assignments_not_flagged_as_duplicate_names(self):
        config = {
            "controller_roles": [
                {"role": "use", "inventory": "inv1"},
                {"role": "use", "inventory": "inv2"},
            ]
        }
        issues = validate(config)
        assert not any("duplicate" in i.message for i in issues)

    def test_wildcard_maps_alias_suffix_to_canonical(self):
        from aap_config_validate.validators import is_wildcard_var

        assert is_wildcard_var("controller_notification_templates_dev") == "controller_notifications"
        assert is_wildcard_var("http_ports_dev") == "gateway_http_ports"
        assert is_wildcard_var("aap_organizations_all") == "aap_organizations"


class TestWildcardAuto:
    def test_suffixed_vars_merged_without_flag(self):
        from aap_config_validate.validators import config_has_wildcard_vars

        config = {
            "controller_templates_all": [{"name": "JT1"}],
        }
        assert config_has_wildcard_vars(config)
        merged, issues = merge_wildcard_vars(config)
        assert not any(i.severity is Severity.ERROR for i in issues)
        assert "controller_templates" in merged
        assert merged["controller_templates"][0]["name"] == "JT1"
        assert "controller_templates_all" not in merged


class TestRealConfigs:
    """Smoke test: run validator against the repo's own test configs."""

    @pytest.fixture()
    def repo_root(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        if not (root / "roles" / "dispatch").is_dir():
            pytest.skip("Not running inside the infra.aap_configuration repo")
        return root

    def test_controller_configs_no_errors(self, repo_root):
        from aap_config_validate.loader import load_paths

        config, load_errors, _sources = load_paths([str(repo_root / "tests" / "configs" / "controller")])
        assert not load_errors
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors, [f"{e.path}: {e.message}" for e in errors]

    def test_gateway_configs_no_errors(self, repo_root):
        from aap_config_validate.loader import load_paths

        config, load_errors, _sources = load_paths([str(repo_root / "tests" / "configs" / "gateway")])
        assert not load_errors
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors, [f"{e.path}: {e.message}" for e in errors]

    def test_eda_configs_no_errors(self, repo_root):
        from aap_config_validate.loader import load_paths

        config, load_errors, _sources = load_paths([str(repo_root / "tests" / "configs" / "eda")])
        assert not load_errors
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors, [f"{e.path}: {e.message}" for e in errors]

    def test_hub_configs_no_errors(self, repo_root):
        from aap_config_validate.loader import load_paths

        config, load_errors, _sources = load_paths([str(repo_root / "tests" / "configs" / "hub")])
        issues = validate(config)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert not errors, [f"{e.path}: {e.message}" for e in errors]
