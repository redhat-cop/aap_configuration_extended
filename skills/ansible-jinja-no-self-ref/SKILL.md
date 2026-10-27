---
name: ansible-jinja-no-self-ref
description: >-
  Prevent Ansible Jinja recursive-loop bugs from self-referential task vars
  (issue #430). Use when editing role tasks, filetree_create templates/vars,
  or reviewing YAML that sets key: "{{ key | default(...) }}".
---

# No self-referential Jinja in task `vars:`

## Forbidden pattern

```yaml
vars:
  referenced_global_ee_names: "{{ referenced_global_ee_names | default([]) }}"
```

Ansible evaluates the RHS while defining the same key →
`Recursive loop detected in template: maximum recursion depth exceeded`.

## What to do instead

1. **Omit the task var** when a template/filter already does `| default([])`.
2. **Set a fact earlier** with `set_fact` when a value must exist for later tasks.
3. **Use a different name** on the RHS if you must bridge scopes:
   `ee_names_for_template: "{{ referenced_global_ee_names | default([]) }}"`.

## Allowed (not the same bug)

`set_fact` accumulation is fine:

```yaml
ansible.builtin.set_fact:
  items: "{{ items | default([]) + [new_item] }}"
```

Role parameter passthrough in playbooks (`aap_hostname: "{{ aap_hostname }}"`)
is a different pattern; still avoid `key: "{{ key | default(...) }}"` under
**task** `vars:`.

## Mandatory checks when touching role tasks

1. Search new/changed task `vars:` for `name: "{{ name | default("`.
2. Run:
   `python -m unittest tests.unit.test_no_jinja_self_ref_task_vars -v`
3. Prefer a 10-second Ansible smoke render of any new `template:` task that
   introduces optional facts (undefined vs defined).

## Related

- Bug: [issue #430](https://github.com/redhat-cop/aap_configuration_extended/issues/430)
- Guard test: `tests/unit/test_no_jinja_self_ref_task_vars.py`
- Filetree entity skill: [add-filetree-entity/SKILL.md](../add-filetree-entity/SKILL.md)
