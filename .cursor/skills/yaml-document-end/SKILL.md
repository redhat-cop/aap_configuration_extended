---
name: yaml-document-end
description: >-
  Enforce YAML document end markers (...) on every Ansible/YAML file in this
  collection. Use when creating or editing .yml/.yaml playbooks, tasks, vars,
  defaults, meta, configs, changelogs fragments that are YAML, or any other
  YAML content that ansible-lint yaml[document-end] will check.
---

# YAML document end (`...`)

This repository's ansible-lint profile requires **`yaml[document-end]`**.

## Rule

Every new or edited YAML file (`.yml` / `.yaml`) **must** end with a document
end marker on its own last line:

```yaml
---
key: value
...
```

## Checklist (before finishing an edit)

1. File starts with `---` (document start) when it is a standalone YAML document.
2. File ends with a line that is exactly `...` (no trailing spaces).
3. There is a newline after `...` (end-of-file fixer / POSIX text file).
4. Do **not** leave the file ending on the last key/list item without `...`.

## Exceptions

- Do not add `...` inside Jinja templates that emit YAML unless the **rendered**
  output (or the template's intentional trailer) already follows the collection
  pattern (many `filetree_create` templates already emit `...`).
- Files listed in `.ansible-lint-ignore` for `yaml[document-end]` are legacy
  exceptions; do not add new ignores for new files.

## Verification

ansible-lint reports missing markers as:

```text
yaml[document-end]: Missing document end "..."
```

Fix by appending `...` as the final line, then re-run pre-commit / ansible-lint
on the changed files.
