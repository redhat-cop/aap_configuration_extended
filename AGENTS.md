# Agent instructions

When adding or changing **filetree_create** / **filetree_read** object support, follow [skills/add-filetree-entity/SKILL.md](skills/add-filetree-entity/SKILL.md) (tool-agnostic; same layout works for Cursor, Claude Code, Codex, etc.).

For Job Template or Workflow Job Template PRE→PRO migration (related export + env variables stub), follow [skills/export-jt-related-pre-pro/SKILL.md](skills/export-jt-related-pre-pro/SKILL.md).

Collection conventions: [.cursor/rules/aap_configuration_extended-general.mdc](.cursor/rules/aap_configuration_extended-general.mdc).

## Configuration as Code baseline

- **Names, never IDs.** CaC YAML, playbook extra vars, and docs must identify objects by name (`job_template_name`, `organization_filter`, `project_name`, …). Do not recommend or document numeric `*_id` selectors for new work.
- Exported related-object references must be names (already the default in Jinja templates via `summary_fields.*.name`).
- Prefer `omit_id: true` so generated filenames do not prefix numeric IDs.
