# Agent instructions

When adding or changing **filetree_create** / **filetree_read** object support, follow [skills/add-filetree-entity/SKILL.md](skills/add-filetree-entity/SKILL.md) (tool-agnostic; same layout works for Cursor, Claude Code, Codex, etc.).

For Job Template or Workflow Job Template PRE→PRO migration (related export + env variables stub), follow [skills/export-jt-related-pre-pro/SKILL.md](skills/export-jt-related-pre-pro/SKILL.md).

Collection conventions: [.cursor/rules/aap_configuration_extended-general.mdc](.cursor/rules/aap_configuration_extended-general.mdc).

Test and example playbooks: use `ansible.platform.token` for OAuth; see the **Test playbooks — authentication** section in the skill above (no `__aap_*` staging vars; single `when` for token creation).

## Commits and pre-commit

- Ensure hooks are installed once per clone: `pre-commit install` (without this, `git commit` will not run the suite and CI/reviewers will catch failures later).
- **Never commit** unless local pre-commit hooks pass on the changed files (`pre-commit run --files …` or `pre-commit run`).
- That includes ansible-lint, changelog validation, galaxy-importer, and the other hooks in `.pre-commit-config.yaml`.
- If ansible-lint cannot reach Galaxy (proxy/tunnel errors), re-run with `--offline` and a local `ANSIBLE_COLLECTIONS_PATH` that already has the required collections — do not skip the hook or use `--no-verify`.
- Fix lint/hook failures in a new commit attempt; do not amend around a failed hook unless the user explicitly requests amend and the amend rules in the user git protocol are met.

## Configuration as Code baseline

- **Names, never IDs.** CaC YAML, playbook extra vars, and docs must identify objects by name (`job_template_name`, `organization_filter`, `project_name`, …). Do not recommend or document numeric `*_id` selectors for new work.
- Exported related-object references must be names (already the default in Jinja templates via `summary_fields.*.name`).
- Prefer `omit_id: true` so generated filenames do not prefix numeric IDs.
