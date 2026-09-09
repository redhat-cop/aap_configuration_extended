---
name: pr-test-plan
description: >-
  Run a pull request's test plan against the local workspace on latest devel,
  report results, and optionally post a PR comment after user approval. Use when
  the user says "run the test plan", "PR test", "test PR", or provides a PR
  link/number for manual validation.
---

# PR test plan (local)

Execute the PR author's **How should this be tested?** section using this clone, then restore the workspace to latest `devel`.

## Trigger (short forms)

Any of these mean the same workflow:

- `Run the test plan of PR <URL or #number>`
- `PR test plan: <URL or #number>`
- `Test PR <number>`

Always parse the PR with `gh` (body, changed files, checks). Do not invent steps that are not in the PR test plan unless listed under **Additional checks** below.

## Preconditions

- `gh` authenticated for the repo (`origin` = fork, `upstream` = redhat-cop when present).
- AAP vault/extra-vars available for integration playbooks (`tests/vault-aap-controller.yaml` or env vars).
- `pre-commit` hooks installed in this clone (`pre-commit install`).

## Workspace setup (latest devel + PR code)

Goal: tests run against **PR changes** while the base is **current `origin/devel`**. When finished, the checkout must be **latest `devel`** (no leftover test branch).

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
PR_REF="<number-or-URL>"   # e.g. 42 or https://github.com/.../pull/42
TEST_BRANCH="pr-test-${PR_NUM}"

# Remember dirty state
git status --porcelain
# If dirty: git stash push -u -m "pr-test-plan-${PR_NUM}"

git fetch origin devel
git checkout devel
git pull --ff-only origin devel

gh pr checkout "${PR_REF}" --branch "${TEST_BRANCH}"
git merge origin/devel --no-edit   # skip if already up to date

export ANSIBLE_COLLECTIONS_PATH="${REPO_ROOT}/../../.."
cd "${REPO_ROOT}/tests"
```

**After all tests (mandatory cleanup):**

```bash
git checkout devel
git pull --ff-only origin devel
git branch -D "${TEST_BRANCH}"    # safe if branch gone
# If stashed: git stash pop
```

Never leave the repo on `pr-test-*` or with unmerged test branches.

## Execution order

1. **Read the PR** — `gh pr view <ref> --json title,body,baseRefName,headRefName,files,url`
   - Extract **How should this be tested?** (PR template section).
   - Note `baseRefName` must be `devel`; warn if not.
2. **Map changed paths** — decide extra suites (table below).
3. **Run PR test plan** — execute commands from the PR body literally; save logs under `/tmp/pr_test_${PR_NUM}/`.
4. **Additional checks** — run applicable items from the next section; skip what the PR scope does not touch.
5. **Summarize** — pass/fail per step, environment notes, log paths.
6. **Ask the user** — "Post this summary as a PR comment?" Do **not** comment until they confirm.
7. **Post comment** (only after approval) — see [PR comment template](#pr-comment-template).
8. **Cleanup** — run workspace setup **After all tests** block.

### PR comment template

```bash
gh pr comment <number> --body "$(cat <<'EOF'
## Local test results

**Base:** `origin/devel` @ `<short-sha>`
**Test branch:** `pr-test-<N>` merged with latest devel
**Tester:** local workspace (`ANSIBLE_COLLECTIONS_PATH` = this clone)

### PR test plan
| Step | Result | Notes |
| ---- | ------ | ----- |
| … | pass / fail / skip | … |

### Additional checks
| Check | Result | Notes |
| ----- | ------ | ----- |
| … | … | … |

### CI status (at test time)
<output of `gh pr checks` or "not checked">

Logs: `/tmp/pr_test_<N>/`
EOF
)"
```

## Additional checks (beyond the PR body)

Run only what matches the diff; mention skipped checks in the summary.

| If PR touches | Also run |
| ------------- | -------- |
| `roles/filetree_create/**`, `roles/filetree_read/**`, `tests/configs/roundtrip/**` | Full roundtrip per [filetree-roundtrip-test/SKILL.md](../filetree-roundtrip-test/SKILL.md) when the PR test plan does not already specify a narrower run |
| New/changed filetree entity | Scoped verify commands in [skills/add-filetree-entity/SKILL.md](../../../skills/add-filetree-entity/SKILL.md) § Verify |
| `plugins/**/aap_config_vars*` or `tests/**/aap_config_vars*` | `python -m unittest discover -s tests/unit/plugins/module_utils -p test_aap_config_vars.py -v` and `tests/scripts/run_aap_config_vars_integration.sh --template` |
| Any Ansible/YAML under `roles/`, `plugins/`, `tests/` | `pre-commit run --files <changed files>` (or full `pre-commit run` if many files) |
| User-facing behavior change | Confirm `changelogs/fragments/` entry exists |
| Export/template changes | Spot-check generated YAML uses **names, never IDs**; settings use native YAML types where relevant |

**CI mirror (optional, no AAP):** `gh pr checks <number>` — record status; do not treat green CI as a substitute for the PR's manual/integration steps.

**Regression signals for filetree work:**

- Step 3 re-import: `changed=0` (or only benign async retries).
- No `id` / `*_id` fields in exported fixtures under test output dirs.

## What not to do

- Do not commit, push, merge, or change PR labels/workflows.
- Do not post PR comments without explicit user approval after showing the draft summary.
- Do not use `--no-verify` on pre-commit.
- Do not filter filetree object types when the PR test plan or roundtrip skill calls for a **full** run.

## Related skills

- [filetree-roundtrip-test](../filetree-roundtrip-test/SKILL.md) — full import → export → re-import
- [add-filetree-entity](../../../skills/add-filetree-entity/SKILL.md) — scoped entity verify
- Autopilot (personal skill) — CI/comments/merge conflicts on the PR branch, not local integration testing
