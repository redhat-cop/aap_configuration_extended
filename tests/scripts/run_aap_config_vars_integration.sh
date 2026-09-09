#!/usr/bin/env bash
# Run aap_config_vars integration tests against the local collection checkout.
#
# Usage:
#   tests/scripts/run_aap_config_vars_integration.sh
#   tests/scripts/run_aap_config_vars_integration.sh --template
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLAYBOOK="${REPO_ROOT}/tests/test_aap_config_vars.yaml"
COLLECTIONS_TMP="$(mktemp -d)"
TEMPLATE_TEST=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template)
      TEMPLATE_TEST=1
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--template]"
      echo "  --template  Also run against a shallow clone of aap_configuration_template"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

cleanup() {
  rm -rf "${COLLECTIONS_TMP}"
}
trap cleanup EXIT

mkdir -p "${COLLECTIONS_TMP}/ansible_collections/infra"
ln -sfn "${REPO_ROOT}" "${COLLECTIONS_TMP}/ansible_collections/infra/aap_configuration_extended"
export ANSIBLE_COLLECTIONS_PATH="${COLLECTIONS_TMP}${ANSIBLE_COLLECTIONS_PATH:+:${ANSIBLE_COLLECTIONS_PATH}}"

echo "==> Running fixture integration test"
ansible-playbook "${PLAYBOOK}"

run_template_test() {
  local template_dir
  template_dir="$(mktemp -d)"
  trap 'rm -rf "${template_dir}"' RETURN

  echo "==> Cloning aap_configuration_template (shallow)"
  git clone --depth 1 https://github.com/redhat-cop/aap_configuration_template.git "${template_dir}"

  local test_env_dir="${template_dir}/config/integration_test"
  mkdir -p "${test_env_dir}"
  cp -a "${REPO_ROOT}/tests/configs/aap_config_vars/all" "${template_dir}/config/"
  cp -a "${REPO_ROOT}/tests/configs/aap_config_vars/dev/secrets.yml" "${test_env_dir}/secrets.yml"
  cp "${REPO_ROOT}/tests/configs/aap_config_vars/all/controller_projects.yml" "${test_env_dir}/controller_projects.yml"

  cat >"${template_dir}/playbooks/test_aap_config_vars.yml" <<'EOF'
---
- name: Smoke test aap_config_vars against template-style config layout
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    env: integration_test
  tasks:
    - name: Full load from template config tree
      infra.aap_configuration_extended.aap_config_vars:
        config_dir: "{{ playbook_dir }}/../config"
        env: "{{ env }}"
      register: loaded

    - name: Assert template layout loads
      ansible.builtin.assert:
        that:
          - loaded.aap_config_mode == 'full'
          - loaded.ansible_facts.controller_templates_all | length == 2
          - loaded.ansible_facts.controller_projects_all | length == 1
          - loaded.ansible_facts.console_token == 'initial-token'
EOF

  echo "==> Running template-layout smoke test"
  ansible-playbook "${template_dir}/playbooks/test_aap_config_vars.yml"
}

if [[ "${TEMPLATE_TEST}" -eq 1 ]]; then
  run_template_test
fi

echo "All aap_config_vars integration tests passed."
