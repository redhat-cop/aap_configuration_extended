# aap-config-validate

Offline configuration validator for the [infra.aap_configuration](https://github.com/redhat-cop/infra.aap_configuration) Ansible Collection. It checks your AAP configuration YAML files against the collection's schemas **before** you apply them, catching errors like typos, missing required fields, invalid values, and broken cross-references without needing a live AAP instance.

## Features

- **Variable name validation** &mdash; flags unknown variables with "did you mean?" suggestions
- **Structure validation** &mdash; ensures resource variables are lists of dicts as expected
- **Required field checking** &mdash; catches missing fields like `name` or `credential_type`
- **Type checking** &mdash; warns when a field value doesn't match the expected type
- **Unknown field detection** &mdash; spots typos in field names with suggestions
- **State validation** &mdash; verifies `state` values are `present`, `absent`, `exists`, etc.
- **Choice validation** &mdash; checks enum fields like `job_type`, `verbosity`, `scm_type`
- **Cross-reference validation** &mdash; verifies that referenced resources (projects, credentials, inventories) exist in your config
- **Wildcard variable merging** &mdash; emulates the collection's `dispatch_include_wildcard_vars` behavior
- **Legacy alias support** &mdash; recognises old-style variable names like `job_templates` alongside `controller_templates`
- **Jinja-aware** &mdash; gracefully skips values containing `{{ }}` or `lookup()` expressions
- **Ansible tag-aware** &mdash; handles `!unsafe`, `!vault`, and `!vault-encrypted` YAML tags
- **Ansible scalar coercion** &mdash; accepts quoted values like `"0"`, `"false"`, `"False"`, and `"{}"` that Ansible would coerce at apply time
- **Source locations** &mdash; issues include the YAML file they came from
- **Filetree and dispatch layouts** &mdash; works on flat `infra.aap_configuration` var files and on `filetree_create` / hierarchical `.d/` trees

## Supported Components

Schemas are provided for **53 resource types** across all four AAP components:

| Component | Count | Examples |
| :--- | :--- | :--- |
| **Controller** | 21 | `controller_templates`, `controller_projects`, `controller_credentials`, `controller_workflows`, `controller_inventories`, ... |
| **Gateway** | 16 | `aap_organizations`, `aap_teams`, `aap_user_accounts`, `gateway_authenticators`, `gateway_settings`, ... |
| **Hub** | 8 | `hub_namespaces`, `hub_collections`, `hub_ee_registries`, `hub_ee_repositories`, ... |
| **EDA** | 8 | `eda_projects`, `eda_rulebook_activations`, `eda_credentials`, `eda_decision_environments`, ... |

## Installation

Requires Python 3.10+.

```bash
# From the tools/ directory in the collection repo
cd tools
pip install .

# Or install in editable/development mode
pip install -e .
```

This registers the `aap-config-validate` command on your PATH.

You can also run it without installing:

```bash
cd tools
python -m aap_config_validate /path/to/configs/
```

## Quick Start

```bash
# Validate a directory of config files
aap-config-validate /path/to/my/aap/configs/

# Validate specific files
aap-config-validate configs/controller.yml configs/hub.yml

# Validate only controller resources
aap-config-validate --component controller configs/

# Strict mode — treat warnings as errors
aap-config-validate --strict configs/

# JSON output for CI/CD pipelines
aap-config-validate --format json configs/
```

## CLI Reference

```text
usage: aap-config-validate [-h] [--config FILE] [--format {text,json}]
                           [--strict] [--no-strict]
                           [--component {controller,gateway,hub,eda}]
                           [--no-color] [--show-info]
                           [--wildcard-vars {auto,always,never}] [--version]
                           paths [paths ...]
```

| Flag | Description |
| :--- | :--- |
| `paths` | One or more YAML files or directories to validate (required) |
| `--config FILE`, `-c FILE` | Path to a `.aap-validate.yml` config file (default: auto-detect from cwd) |
| `--format {text,json}` | Output format (default: `text`) |
| `--strict` | Treat warnings as errors (exit code 1) |
| `--no-strict` | Do not treat warnings as errors (overrides `strict: true` in the config file) |
| `--component COMP` | Limit validation to a component; may be repeated (e.g. `--component controller --component eda`) |
| `--no-color` | Disable coloured terminal output (also honours `NO_COLOR` and non-TTY stdout) |
| `--show-info` | Include INFO-level messages (Jinja skips, unresolvable xrefs) |
| `--wildcard-vars {auto,always,never}` | Control wildcard variable merging (see below) |
| `--version` | Print the tool version and exit |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | No errors (warnings may be present) |
| `1` | One or more errors found |

## Issue Severity Levels

| Level | Meaning | Example |
| :--- | :--- | :--- |
| **ERROR** | Definite problem that will cause a failure | Missing required field, invalid state, malformed YAML |
| **WARNING** | Likely problem worth investigating | Unknown variable name, typo in field name, broken cross-reference |
| **INFO** | Informational, hidden by default | Jinja expression skipped, xref target not in config (may exist on server) |

## Output Formats

### Text (default)

```text
ERROR: configs/credentials.yml: controller_credentials[0] ("My Cred"): missing required field "credential_type"
WARNING: configs/templates.yml: controller_templates[1] ("Deploy"): field "projet" not recognised (did you mean "project"?)

Found 1 error(s), 1 warning(s). Config is NOT valid.
```

### JSON (`--format json`)

```json
{
  "issues": [
    {
      "severity": "ERROR",
      "path": "controller_credentials[0] (\"My Cred\")",
      "message": "missing required field \"credential_type\"",
      "suggestion": null,
      "file": "configs/credentials.yml"
    }
  ],
  "summary": {
    "errors": 1,
    "warnings": 0,
    "info": 0
  }
}
```

## Wildcard Variable Merging

The `infra.aap_configuration` collection supports wildcard variables, where suffixed variables like `controller_templates_production` are merged into the base `controller_templates` list. The validator emulates this behavior:

| Mode | Behavior |
| :--- | :--- |
| `auto` (default) | Merges when `dispatch_include_wildcard_vars: true` is set **or** when suffixed vars like `controller_templates_all` are present (as in [aap_configuration_template](https://github.com/redhat-cop/aap_configuration_template)) |
| `always` | Always merges wildcard-suffixed variables |
| `never` | Never merges; suffixed variables are silently ignored |

```bash
# Force wildcard merging even without the dispatch flag
aap-config-validate --wildcard-vars always configs/
```

Example config using wildcard variables:

```yaml
# base.yml
dispatch_include_wildcard_vars: true
controller_templates:
  - name: Base Template
    project: Common

# production.yml
controller_templates_production:
  - name: Prod Deploy
    project: Production
```

With `auto` or `always`, both templates are validated together as a single merged list.

Empty overlays such as `controller_settings_dev: []` next to a dict-form `controller_settings_all` are ignored (they do not produce a type-mismatch error).

## Config layouts

### Dispatch / template style

Flat YAML files whose top-level keys are dispatch variables (`controller_templates`, `aap_organizations`, …), including env-suffixed names (`controller_templates_all`, `controller_templates_dev`) as used by [aap_configuration_template](https://github.com/redhat-cop/aap_configuration_template):

```bash
aap-config-validate config/all config/dev
```

Directory scans skip `secrets.yml` / `secrets.yaml` by default (vaulted extra vars). Pass a secrets file explicitly if you want it parsed.

### Filetree style

Per-object files under `*.d/` directories produced by `filetree_create` / consumed by `filetree_read`. Validate **one environment at a time** so objects that exist in both `dev` and `prod` are not reported as duplicates:

```bash
aap-config-validate orgs_vars/ExampleOrg/env/common orgs_vars/ExampleOrg/env/prod
```

Aliases such as `gateway_organizations`, `controller_organizations`, `controller_user_accounts`, and `controller_notification_templates` are recognised and checked against the canonical dispatch schemas.

## Configuration File

Create a `.aap-validate.yml` (or `.aap-validate.yaml`) in your project root to customize validator behavior. The file is auto-detected from the current working directory, or you can specify it explicitly with `--config`.

An annotated example is provided at `tools/.aap-validate.example.yml`.

### All Options

```yaml
# ── File/directory exclusions ────────────────────────────────
# Glob patterns matched against relative paths within the scanned directory.
# Nested paths such as tests/fixtures are matched as a whole, not only
# by the last path component. Directory scans also skip secrets.yml,
# .git, .github, .svn, __pycache__, and .tox by default.

exclude_files:
  - "*.bak"
  - "secrets.yml"

exclude_dirs:
  - ".git"
  - "scratch"
  - "tests/fixtures"

# ── Variable ignoring ───────────────────────────────────────
# Suppress "unknown variable name" warnings.
# Supports glob patterns.

ignore_vars:
  - my_custom_var
  - env_*
  - ansible_*

# ── Per-variable field ignoring ─────────────────────────────
# Suppress "field not recognised" warnings for specific fields
# on specific resource types. Use "*" to apply to all resource types.

ignore_fields:
  controller_templates:
    - custom_field
    - my_extra_*
  "*":
    - _internal_field

# ── Disable entire checks ──────────────────────────────────
# Completely turn off specific validation checks.

disable_checks:
  - xref
  - unknown_fields

# Valid check names:
#   var_names, structure, required_fields, types,
#   unknown_fields, state, choices, xref, duplicates

# ── Extra known variables ──────────────────────────────────
# Additional variable names to register as valid.
# Unlike ignore_vars, these are exact names (no globs).

extra_known_vars:
  - my_org_base_url
  - deployment_environment

# ── CLI defaults ───────────────────────────────────────────
# All of these can be overridden by the corresponding CLI flag.

strict: false
show_info: false
wildcard_vars: auto          # auto | always | never
output_format: text          # text | json
components:                  # limit to specific component(s)
  - controller
  - gateway
```

### Option Precedence

CLI flags always take precedence over config file values, which take precedence over built-in defaults:

```text
CLI flag  >  .aap-validate.yml  >  built-in default
```

### `ignore_vars` vs `extra_known_vars`

Both suppress "unknown variable" warnings, but they work differently:

| | `ignore_vars` | `extra_known_vars` |
| :--- | :--- | :--- |
| Glob patterns | Yes (`env_*`) | No (exact names only) |
| Purpose | Silently skip variables you don't want checked | Register variables as legitimately known |

Use `extra_known_vars` for variables that are genuinely part of your workflow. Use `ignore_vars` for broader pattern-based suppression.

## Validation Checks in Detail

### Variable Name Check (`var_names`)

Every top-level key in your YAML is checked against the dispatch registry. Unknown names produce a WARNING with a fuzzy-match suggestion when possible. The following are automatically recognised:

- All dispatch variable names (`controller_templates`, `eda_projects`, etc.)
- Legacy aliases (`job_templates`, `credentials`, etc.)
- Global authentication/configuration variables (`aap_hostname`, `aap_password`, etc.)
- Per-role override suffixes (`*_async_delay`, `*_async_retries`, `*_secure_logging`, etc.)
- Wildcard-suffixed variables (`controller_templates_production`)
- Private/internal variables (prefixed with `_` or `__`)

### Structure Check (`structure`)

Verifies that resource variables have the expected shape. Most resources expect a list of dicts. `controller_settings` and `gateway_settings` also accept a plain dict.

### Required Fields (`required_fields`)

Each resource schema defines which fields are mandatory (e.g. `name` for most resources, `credential_type` for credentials). Missing required fields produce an ERROR. Empty strings are treated as unset. When `state` is `absent`, only the identity field (`name` / `username` / `hostname`) is required.

### Type Check (`types`)

Warns when a field value doesn't match the expected type (e.g. a list where a string is expected). Jinja expressions are always skipped. Union types like `str|dict` and `str|list` are supported. Quoted Ansible scalars (`"0"`, `"false"`, `"False"`, `"{}"`) are accepted when they coerce to the expected type. Empty strings are treated as unset, not as a type error.

### Unknown Fields (`unknown_fields`)

Fields not in the schema produce a WARNING with a fuzzy suggestion. This catches typos like `projet` instead of `project`.

### State Validation (`state`)

Checks that `state` values are valid. Most resources accept `present` and `absent`. Some also accept `exists`, `enabled`, or `disabled`.

### Choice Validation (`choices`)

Enum fields like `job_type` (`run`, `check`), `verbosity` (0-5), and `scm_type` (`git`, `svn`, etc.) are validated against their allowed values.

### Cross-Reference Validation (`xref`)

When a field references another resource by name (e.g. a job template's `project` field referencing `controller_projects`), the validator checks that the referenced name exists in your config. If the target resource type isn't defined at all, it produces an INFO (the resource may already exist on the server). `--component` still builds the cross-reference index from **all** loaded resources, so filtering to controller still resolves `aap_organizations`.

### Duplicate names (`duplicates`)

Warns when the same `name` / `username` / `hostname` appears twice in one resource list. Role assignments are skipped (many items share `role: use` with different targets).

## CI/CD Integration

### GitHub Actions

```yaml
- name: Validate AAP config
  run: |
    pip install ./tools
    aap-config-validate --strict --format text configs/
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: aap-config-validate
        name: Validate AAP configuration
        entry: aap-config-validate --strict
        language: python
        additional_dependencies: ['./tools']
        files: 'config/.*\.(yml|yaml)$'
        pass_filenames: true
```

### GitLab CI

```yaml
validate-config:
  stage: lint
  script:
    - pip install ./tools
    - aap-config-validate --strict --format json configs/ > validation-report.json
  artifacts:
    when: always
    paths:
      - validation-report.json
```

## Running Tests

```bash
cd tools
pip install -e .
pip install pytest

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test module
pytest unit_tests/test_config.py -v
```

## Project Structure

```text
tools/
├── pyproject.toml                          # Package metadata and dependencies
├── .aap-validate.example.yml              # Annotated example config file
├── README.md                               # This file
├── aap_config_validate/
│   ├── __init__.py                        # Package version
│   ├── __main__.py                        # python -m entry point
│   ├── cli.py                             # CLI argument parsing and orchestration
│   ├── config.py                          # Config file loading (.aap-validate.yml)
│   ├── loader.py                          # YAML loading with Jinja/Ansible tag handling
│   ├── models.py                          # Core data structures (Issue, Field, ResourceSchema)
│   ├── registry.py                        # Dispatch variable registry and legacy aliases
│   ├── reporter.py                        # Text and JSON output formatters
│   ├── validators.py                      # Validation engine and wildcard merging
│   └── schemas/
│       ├── __init__.py                    # Schema aggregation
│       ├── controller.py                  # 21 Automation Controller schemas
│       ├── eda.py                         # 8 Event-Driven Ansible schemas
│       ├── gateway.py                     # 16 AAP Gateway schemas
│       └── hub.py                         # 8 Automation Hub schemas
└── unit_tests/
    ├── test_cli.py                        # CLI integration tests
    ├── test_config.py                     # Config file tests
    ├── test_loader.py                     # YAML loader tests
    ├── test_reporter.py                   # Reporter tests
    └── test_validators.py                 # Validator engine tests
```

## License

GPL-3.0-or-later &mdash; same as the `infra.aap_configuration` collection.
