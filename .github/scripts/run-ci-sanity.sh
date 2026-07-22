#!/usr/bin/env bash
# Run ansible-test sanity using the trusted CI collections cache directly.
#
# Layout required by ansible-test:
#   <tree>/ansible_collections/<namespace>/<collection>/
#
# Cached AH deps live in ~/.ansible/collections/ansible_collections/ and are
# symlinked in as siblings of the collection under test. No ade / Galaxy / AH
# token is needed in the untrusted test job.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

CACHE_COLLECTIONS="${HOME}/.ansible/collections/ansible_collections"
MATRIX_PYTHON="${MATRIX_PYTHON:-$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')}"
TREE="${ROOT}/.ci-ansible-collections"

if [[ ! -d "${CACHE_COLLECTIONS}/ansible/controller" ]]; then
  echo "::error::Cached ansible.controller missing at ${CACHE_COLLECTIONS}/ansible/controller"
  exit 1
fi

echo "::group::Build ansible_collections tree from cache + checkout"
rm -rf "${TREE}"
mkdir -p "${TREE}/ansible_collections/infra"

# Collection under test must be a real directory tree (ansible-test resolves paths).
rsync -a \
  --exclude '.git/' \
  --exclude '.tox/' \
  --exclude '.tox-ci-sanity/' \
  --exclude '.ci-ansible-collections/' \
  --exclude '.venv/' \
  --exclude 'tests/output/' \
  "${ROOT}/" "${TREE}/ansible_collections/infra/aap_configuration_extended/"

# Dependency collections: use the cache directly via symlinks (siblings).
shopt -s nullglob
for ns in "${CACHE_COLLECTIONS}"/*; do
  [[ -d "${ns}" ]] || continue
  name="$(basename "${ns}")"
  if [[ "${name}" == "infra" ]]; then
    mkdir -p "${TREE}/ansible_collections/infra"
    for coll in "${ns}"/*; do
      [[ -d "${coll}" ]] || continue
      cname="$(basename "${coll}")"
      if [[ "${cname}" == "aap_configuration_extended" ]]; then
        continue
      fi
      ln -sfn "${coll}" "${TREE}/ansible_collections/infra/${cname}"
    done
  else
    ln -sfn "${ns}" "${TREE}/ansible_collections/${name}"
  fi
done
shopt -u nullglob

test -d "${TREE}/ansible_collections/infra/aap_configuration_extended/plugins"
test -e "${TREE}/ansible_collections/ansible/controller"
test -e "${TREE}/ansible_collections/infra/aap_configuration"
echo "Collection tree ready at ${TREE}/ansible_collections"
echo "::endgroup::"

python3 -m pip install -q 'tox>=4' 'tox-ansible'

mapfile -t ENVS < <(
  python3 -m tox --ansible --conf tox-ansible.ini -l \
    | grep "^sanity-py${MATRIX_PYTHON}-" \
    || true
)

if [[ ${#ENVS[@]} -eq 0 ]]; then
  echo "::error::No sanity tox envs found for Python ${MATRIX_PYTHON}"
  exit 1
fi

install_ansible_core() {
  local acv="$1"
  case "${acv}" in
    devel)
      pip install -q "https://github.com/ansible/ansible/archive/devel.tar.gz"
      ;;
    milestone)
      pip install -q "https://github.com/ansible/ansible/archive/milestone.tar.gz"
      ;;
    *)
      local major minor next
      major="${acv%%.*}"
      minor="${acv#*.}"
      next="$((minor + 1))"
      pip install -q "ansible-core>=${major}.${minor}.0,<${major}.${next}.0"
      ;;
  esac
}

status=0
COLL_DIR="${TREE}/ansible_collections/infra/aap_configuration_extended"

for env in "${ENVS[@]}"; do
  py="$(sed -n 's/^sanity-py\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' <<<"${env}")"
  acv="$(sed -n 's/^sanity-py[0-9.]*-//p' <<<"${env}")"
  venv="${ROOT}/.tox-ci-sanity/${env}"

  echo "::group::Prepare ${env} (ansible-core ${acv}, python ${py})"
  rm -rf "${venv}"
  python3 -m venv "${venv}"
  # shellcheck disable=SC1091
  source "${venv}/bin/activate"
  pip install -q --upgrade pip
  if ! install_ansible_core "${acv}"; then
    echo "::error::Failed to install ansible-core ${acv}"
    deactivate || true
    status=1
    echo "::endgroup::"
    continue
  fi
  echo "ansible-core: $(python -c 'import ansible; print(ansible.__version__)')"
  echo "::endgroup::"

  echo "::group::ansible-test sanity (${env})"
  if ! (
    cd "${COLL_DIR}"
    # Sibling collections from the cache are visible via the ansible_collections parent.
    ansible-test sanity --local --requirements --python "${py}"
  ); then
    status=1
  fi
  deactivate || true
  echo "::endgroup::"
done

exit "${status}"
