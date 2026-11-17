#!/usr/bin/env bash
# Run offline lookup tests and optional live integration tests for filetree_object_diff.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTION_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${COLLECTION_ROOT}"

echo "=== On-disk filetree_cac_diff module tests ==="
ansible-playbook tests/test_filetree_cac_diff.yaml "$@"

echo "=== Offline controller_filetree_diff lookup tests ==="
ansible-playbook tests/test_filetree_object_diff_lookup.yaml "$@"

if [[ "${RUN_LIVE_TESTS:-}" == "1" ]]; then
  echo "=== Live filetree_object_diff integration tests ==="
  ansible-playbook tests/test_filetree_object_diff_full.yml "$@"
else
  echo "Skipping live tests. Set RUN_LIVE_TESTS=1 to run integration tests against AAP."
fi
