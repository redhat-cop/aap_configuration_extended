#!/usr/bin/env bash
# Rebuild tests/configs/roundtrip from fcf (export baseline) + custom-only files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
FCF="$ROOT/../fcf"
CUSTOM="$ROOT/../custom"

python3 - "$ROOT" "$FCF" "$CUSTOM" <<'PY'
import re, shutil, sys
from pathlib import Path

roundtrip, fcf_dir, custom_dir = map(Path, sys.argv[1:4])

def all_keys(path: Path) -> set[str]:
    return set(re.findall(r'^([a-zA-Z0-9_]+):', path.read_text(), re.M))

fcf_keys: set[str] = set()
for f in fcf_dir.glob('*.yaml'):
    fcf_keys |= all_keys(f)

extras_dir = roundtrip.parent / 'roundtrip_extra_vars'
extras = {e.name: e.read_text() for e in extras_dir.glob('extra_vars*.yml')} if extras_dir.is_dir() else {}
shutil.rmtree(roundtrip)
roundtrip.mkdir()

for f in fcf_dir.glob('*.yaml'):
    shutil.copy2(f, roundtrip / f.name)

added = []
for f in sorted(custom_dir.glob('*.yml')):
    keys = all_keys(f)
    if keys & fcf_keys:
        continue
    shutil.copy2(f, roundtrip / f.name)
    added.append(f.name)

for name, content in extras.items():
    extras_dir.mkdir(parents=True, exist_ok=True)
    (extras_dir / name).write_text(content)

# Portable overrides (fcf exports may contain environment-specific numeric IDs).
(roundtrip / 'gateway_role_user_assignments.yaml').write_text(
    '---\n'
    'gateway_role_user_assignments:\n'
    '  - role_definition: "Organization Member"\n'
    '    object_ids:\n'
    '      - Default\n'
    '    user: admin\n'
    '  - role_definition: "Credential Admin"\n'
    '    object_ids:\n'
    '      - roundtrip-rbac-credential\n'
    '    user: admin\n'
    '...\n'
)

cred_file = roundtrip / 'controller_credentials.yaml'
cred_text = cred_file.read_text()
if 'roundtrip-rbac-credential' not in cred_text:
    cred_text = cred_text.replace(
        '...\n',
        '  - name: "roundtrip-rbac-credential"\n'
        '    credential_type: "Machine"\n'
        '    organization: "Default"\n'
        '    description: Credential for roundtrip gateway role user assignment tests\n'
        '    inputs:\n'
        '      username: roundtrip\n'
        '      password: "{{ vaulted_controller_credentials_roundtrip_rbac_credential_password | default(\'roundtrip\') }}"\n'
        '...\n',
        1,
    )
cred_file.write_text(cred_text)

(roundtrip / 'eda_credential_types.yaml').write_text(
    '---\n'
    '# Platform-managed EDA credential types (managed: true) are excluded from filetree export.\n'
    'eda_credential_types: []\n'
    '...\n'
)

(roundtrip / 'eda_credentials.yaml').write_text(
    '---\n'
    'eda_credentials: []\n'
    '...\n'
)

(roundtrip / 'eda_decision_environments.yaml').write_text(
    '---\n'
    '# EDA API unavailable or async polling 404 on this environment; skip DE seed.\n'
    'eda_decision_environments: []\n'
    '...\n'
)

(roundtrip / 'credential_input_sources.yml').write_text(
    '---\n'
    'controller_credential_input_sources: []\n'
    '...\n'
)

(roundtrip / 'inventory_sources.yml').write_text(
    '---\n'
    'controller_inventory_sources:\n'
    '  - name: RHVM-01-scm\n'
    '    source: scm\n'
    '    source_project: Test Inventory source project\n'
    '    source_path: phillips_hue/hosts\n'
    '    inventory: RHVM-01\n'
    '    organization: Satellite\n'
    '    overwrite: true\n'
    '    update_on_launch: false\n'
    '    wait: false\n'
    '...\n'
)

(roundtrip / 'hub_ee_repositories.yaml').write_text(
    '---\n'
    'hub_ee_repositories:\n'
    '  - name: ansible-automation-platform-26/ee-supported-rhel9\n'
    '  - name: ansible-automation-platform-25/ee-supported-rhel9\n'
    '...\n'
)

(roundtrip / 'hub_ee_images.yaml').write_text(
    '---\n'
    '# EE image tag management requires images that exist in Hub (name must include :tag).\n'
    'hub_ee_images: []\n'
    '...\n'
)

(roundtrip / 'hub_collection_remotes.yaml').write_text(
    '---\n'
    'hub_collection_remotes:\n'
    '  - name: rh-certified\n'
    '    url: https://console.redhat.com/api/automation-hub/content/published/\n'
    '    auth_url: https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token\n'
    '    policy: immediate\n'
    '    sync_dependencies: true\n'
    '    tls_validation: true\n'
    '  - name: community\n'
    '    url: https://galaxy.ansible.com/api/\n'
    '    policy: immediate\n'
    '    sync_dependencies: true\n'
    '    tls_validation: true\n'
    '    rate_limit: 8\n'
    '...\n'
)

(roundtrip / 'hub_collection_repositories.yaml').write_text(
    '---\n'
    'hub_collection_repositories:\n'
    '  - name: validated\n'
    '    sync: false\n'
    '  - name: rh-certified\n'
    '    sync: false\n'
    '  - name: community\n'
    '    sync: false\n'
    '  - name: published\n'
    '    sync: false\n'
    '  - name: rejected\n'
    '    sync: false\n'
    '  - name: staging\n'
    '    sync: false\n'
    '...\n'
)

print(f"roundtrip: {len(list(roundtrip.glob('*')))} files")
print("custom-only:", ", ".join(added))
PY
