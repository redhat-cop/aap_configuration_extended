# Agent instructions

When adding or changing **filetree_create** / **filetree_read** object support, follow [skills/add-filetree-entity/SKILL.md](skills/add-filetree-entity/SKILL.md) (tool-agnostic; same layout works for Cursor, Claude Code, Codex, etc.).

Collection conventions: [.cursor/rules/aap_configuration_extended-general.mdc](.cursor/rules/aap_configuration_extended-general.mdc).

Test and example playbooks: use `ansible.platform.token` for OAuth; see the **Test playbooks — authentication** section in the skill above (no `__aap_*` staging vars; single `when` for token creation).
