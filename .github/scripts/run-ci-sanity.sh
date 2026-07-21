#!/usr/bin/env bash
# Run tox-ansible sanity using Automation Hub collections from the CI cache.
# Clears galaxy.yml deps so ade does not contact Galaxy/AH, then copies cached
# dependency collections into each tox env before ansible-test.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

CACHE_COLLECTIONS="${HOME}/.ansible/collections/ansible_collections"
MATRIX_PYTHON="${MATRIX_PYTHON:-$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')}"

python3 - <<'PY'
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML"])
    import yaml

path = Path("galaxy.yml")
data = yaml.safe_load(path.read_text()) or {}
data["dependencies"] = {}
path.write_text(
    yaml.safe_dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        explicit_start=True,
        explicit_end=True,
    )
)
print("Cleared galaxy.yml dependencies for ade; deps come from CI collections cache")
PY

link_cached_deps() {
  local site_packages="$1"
  local root="${site_packages}/ansible_collections"
  mkdir -p "${root}"
  if [[ ! -d "${CACHE_COLLECTIONS}" ]]; then
    echo "::error::Missing cached collections at ${CACHE_COLLECTIONS}"
    return 1
  fi
  local ns name coll cname
  for ns in "${CACHE_COLLECTIONS}"/*; do
    [[ -d "${ns}" ]] || continue
    name="$(basename "${ns}")"
    if [[ "${name}" == "infra" ]]; then
      mkdir -p "${root}/infra"
      for coll in "${ns}"/*; do
        [[ -d "${coll}" ]] || continue
        cname="$(basename "${coll}")"
        # Keep the collection under test from ade; seed sibling infra.* deps from cache.
        if [[ "${cname}" == "aap_configuration_extended" ]]; then
          continue
        fi
        rm -rf "${root}/infra/${cname}"
        cp -a "${coll}" "${root}/infra/${cname}"
      done
    else
      rm -rf "${root}/${name}"
      cp -a "${ns}" "${root}/${name}"
    fi
  done
  test -d "${root}/ansible/controller"
  echo "Linked cached collection deps into ${root}"
}

python3 -m pip install -q 'tox>=4' 'tox-ansible' 'ansible-dev-environment>=26.2.0'

mapfile -t ENVS < <(
  python3 -m tox --ansible --conf tox-ansible.ini -l \
    | grep "^sanity-py${MATRIX_PYTHON}-" \
    || true
)

if [[ ${#ENVS[@]} -eq 0 ]]; then
  echo "::error::No sanity tox envs found for Python ${MATRIX_PYTHON}"
  git checkout -- galaxy.yml
  exit 1
fi

status=0
for env in "${ENVS[@]}"; do
  py="$(sed -n 's/^sanity-py\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' <<<"${env}")"
  site="${ROOT}/.tox/${env}/lib/python${py}/site-packages"
  coll_dir="${site}/ansible_collections/infra/aap_configuration_extended"
  venv_bin="${ROOT}/.tox/${env}/bin"

  echo "::group::tox ${env} (create + ade install)"
  if ! python3 -m tox --ansible --conf tox-ansible.ini -e "${env}" --notest; then
    echo "::endgroup::"
    status=1
    continue
  fi
  echo "::endgroup::"

  if [[ ! -d "${site}" ]]; then
    echo "::error::Expected tox site-packages missing: ${site}"
    status=1
    continue
  fi

  echo "::group::Seed cached deps into ${env}"
  if ! link_cached_deps "${site}"; then
    echo "::endgroup::"
    status=1
    continue
  fi
  echo "::endgroup::"

  echo "::group::ansible-test sanity (${env}, python ${py})"
  if ! (
    cd "${coll_dir}"
    # Prefer the env's ansible-test so collections resolve from this venv.
    if [[ -x "${venv_bin}/ansible-test" ]]; then
      "${venv_bin}/ansible-test" sanity --local --requirements --python "${py}"
    else
      PATH="${venv_bin}:${PATH}" ansible-test sanity --local --requirements --python "${py}"
    fi
  ); then
    status=1
  fi
  echo "::endgroup::"
done

git checkout -- galaxy.yml
exit "${status}"
