# AAP Instance Migration Guide

This guide provides comprehensive instructions for migrating resources from one Ansible Automation Platform (AAP) instance to another using the `migrate_aap_instance.yml` playbook.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Migration Phases](#migration-phases)
- [Configuration Options](#configuration-options)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Advanced Scenarios](#advanced-scenarios)

## Overview

The AAP migration playbook provides a complete, automated solution for migrating configurations between AAP instances. It supports:

- **Full instance migration**: All organizations, projects, credentials, inventories, job templates, workflows, and more
- **Selective migration**: Filter by organization or specific resources
- **Validation**: Post-migration drift detection and cleanup
- **Security**: Ansible Vault support for credential protection
- **Flexibility**: Structured or flattened export formats

### What Gets Migrated

The playbook migrates **46+ AAP resource types**, including:

#### Controller Resources
- Organizations, teams, and users
- Credentials and credential types
- Execution environments
- Projects and labels
- Inventories, hosts, groups, and inventory sources
- Job templates and workflow job templates
- Schedules and notifications
- Instance groups and settings

#### Event-Driven Automation (EDA)
- EDA credentials and credential types
- Decision environments
- Event streams
- Projects and rulebook activations

#### Gateway/Platform Resources
- Gateway organizations, users, and teams
- Applications and authenticators
- Services, routes, and HTTP ports
- Role assignments and settings

## Prerequisites

### Software Requirements

- Ansible Core >= 2.15.0
- Python >= 3.9
- Collections:
  - `infra.aap_configuration >= 3.4.0`
  - `infra.aap_configuration_extended >= 1.1.0`

### Install Collections

```bash
ansible-galaxy collection install infra.aap_configuration
ansible-galaxy collection install infra.aap_configuration_extended
```

### Access Requirements

You need admin-level access to both source and target AAP instances:

- Admin username and password
- Network connectivity to both instances
- Sufficient disk space for exported configuration (typically 10-100 MB per organization)

### AAP Version Compatibility

- **Recommended**: Same major.minor version on source and target
- **Supported**: Source AAP >= 2.4, Target AAP >= 2.4
- **Note**: Migrating from AAP 2.x to AAP 3.x may require additional testing

## Quick Start

### 1. Create Configuration File

```bash
cd playbooks
cp migration_vars.yml.example migration_vars.yml
```

### 2. Edit Configuration

Edit `migration_vars.yml` with your AAP instance details:

```yaml
---
source_aap_hostname: "old-aap.example.com"
source_aap_username: "admin"
source_aap_password: "source_password"

target_aap_hostname: "new-aap.example.com"
target_aap_username: "admin"
target_aap_password: "target_password"

migration_export_dir: "/tmp/aap_migration"
migration_validate_certs: false
```

### 3. Secure Your Credentials (Recommended)

```bash
ansible-vault encrypt migration_vars.yml
```

### 4. Run Migration

```bash
ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @migration_vars.yml \
  --ask-vault-pass
```

### 5. Verify Migration

Log into the target AAP instance and verify:
- Organizations and teams exist
- Projects have synced successfully
- Inventories contain expected hosts
- Job templates are configured correctly
- Credentials are present (values will need to be re-entered for sensitive fields)

## Migration Phases

The migration playbook operates in three distinct phases:

### Phase 1: Export from Source

**What happens:**
- Connects to source AAP instance
- Queries all configured resources via API
- Exports configuration to YAML files
- Organizes files by resource type and organization

**Output structure:**
```
/tmp/aap_migration/
├── current_credential_types.yaml
├── current_execution_environments.yaml
├── current_instance_groups.yaml
├── Default/                          # Organization name
│   ├── aap_organizations.d/
│   ├── aap_teams.d/
│   ├── controller_credentials.d/
│   ├── controller_inventories.d/
│   ├── controller_job_templates.d/
│   ├── controller_projects.d/
│   └── controller_workflow_job_templates.d/
└── ORGANIZATIONLESS/
    ├── controller_credentials.d/
    └── aap_user_accounts.d/
```

**Duration**: 2-10 minutes depending on instance size

### Phase 2: Import to Target

**What happens:**
- Reads exported YAML configuration
- Authenticates to target AAP instance
- Creates/updates resources in dependency order
- Handles resource relationships (parent/child dependencies)

**Important notes:**
- Credentials: Sensitive values (passwords, tokens) are exported as `$encrypted$` placeholders and must be updated manually
- Projects: Will trigger initial sync on target instance
- Resource IDs: New IDs will be assigned on target instance
- Schedules: Will be created but may need timezone adjustments

**Duration**: 5-30 minutes depending on instance size

### Phase 3: Validate (Optional)

**What happens:**
- Compares exported configuration against target instance state
- Identifies any drift or missing resources
- Optionally removes resources not in the export (if `migration_cleanup_drift: true`)

**Validation checks:**
- All exported resources exist on target
- No unexpected resources on target (drift)
- Resource configurations match export

**Duration**: 1-5 minutes

## Configuration Options

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `source_aap_hostname` | Source AAP hostname or IP | `old-aap.example.com` |
| `source_aap_username` | Source admin username | `admin` |
| `source_aap_password` | Source admin password | `password123` |
| `target_aap_hostname` | Target AAP hostname or IP | `new-aap.example.com` |
| `target_aap_username` | Target admin username | `admin` |
| `target_aap_password` | Target admin password | `password456` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `migration_export_dir` | `/tmp/aap_migration` | Directory for exported config |
| `migration_validate_certs` | `false` | Validate SSL certificates |
| `migration_export_flatten` | `false` | Use flattened directory structure |
| `migration_skip_validation` | `false` | Skip post-migration validation |
| `migration_cleanup_drift` | `false` | Remove drifted resources |
| `migration_export_organization` | (all) | Limit to specific organization |

### Advanced Export Filters

| Variable | Description | Example |
|----------|-------------|---------|
| `migration_export_project_id` | Export only specific project | `10` |
| `migration_export_job_template_id` | Export only specific job template | `25` |
| `migration_export_workflow_id` | Export only specific workflow | `5` |
| `migration_export_inventory_id` | Export only specific inventory | `3` |

### Export Control Options

| Variable | Default | Description |
|----------|---------|-------------|
| `filetree_create_skip_credentials` | `false` | Skip exporting credentials |
| `filetree_create_skip_users` | `false` | Skip exporting users |
| `filetree_create_skip_teams` | `false` | Skip exporting teams |
| `filetree_create_show_encrypted` | `false` | Show credential values (insecure!) |
| `filetree_create_omit_ids` | `false` | Omit resource IDs from export |

## Usage Examples

### Example 1: Full Instance Migration

Migrate everything from one instance to another:

```bash
# Create variables file
cat > full_migration.yml <<EOF
---
source_aap_hostname: "aap-prod-old.company.com"
source_aap_username: "admin"
source_aap_password: "OldPassword123!"

target_aap_hostname: "aap-prod-new.company.com"
target_aap_username: "admin"
target_aap_password: "NewPassword456!"

migration_export_dir: "/data/migrations/full_migration"
migration_validate_certs: true
migration_cleanup_drift: false  # Safe first run
EOF

# Encrypt sensitive data
ansible-vault encrypt full_migration.yml

# Run migration
ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @full_migration.yml \
  --ask-vault-pass
```

### Example 2: Single Organization Migration

Migrate only the "Engineering" organization:

```bash
cat > org_migration.yml <<EOF
---
source_aap_hostname: "aap.company.com"
source_aap_username: "admin"
source_aap_password: "password"

target_aap_hostname: "aap-dev.company.com"
target_aap_username: "admin"
target_aap_password: "devpassword"

migration_export_organization: "Engineering"
migration_export_dir: "/tmp/engineering_migration"
migration_skip_validation: true
EOF

ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @org_migration.yml
```

### Example 3: Dry-Run Migration with Validation

Run migration and check for drift without making destructive changes:

```bash
cat > dryrun_migration.yml <<EOF
---
source_aap_hostname: "source.example.com"
source_aap_username: "admin"
source_aap_password: "password"

target_aap_hostname: "target.example.com"
target_aap_username: "admin"
target_aap_password: "password"

migration_export_dir: "/tmp/dryrun"
migration_cleanup_drift: false  # Report only, don't delete
EOF

ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @dryrun_migration.yml
```

### Example 4: Migration with Aggressive Cleanup

Migrate and remove any resources on target not in the source:

```bash
cat > cleanup_migration.yml <<EOF
---
source_aap_hostname: "source.example.com"
source_aap_username: "admin"
source_aap_password: "password"

target_aap_hostname: "target.example.com"
target_aap_username: "admin"
target_aap_password: "password"

migration_cleanup_drift: true  # WARNING: Deletes unmanaged resources!
EOF

# Use with caution!
ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @cleanup_migration.yml
```

### Example 5: Using Separate Vault File

Keep unencrypted config separate from secrets:

```bash
# Create main config
cat > migration_config.yml <<EOF
---
source_aap_hostname: "old-aap.company.com"
target_aap_hostname: "new-aap.company.com"
migration_export_dir: "/tmp/migration"
EOF

# Create vault file with secrets
ansible-vault create migration_secrets.yml
# Add in editor:
# source_aap_username: "admin"
# source_aap_password: "password1"
# target_aap_username: "admin"
# target_aap_password: "password2"

# Run with both files
ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @migration_config.yml \
  -e @migration_secrets.yml \
  --ask-vault-pass
```

## Best Practices

### Before Migration

1. **Backup Source Instance**
   - Take full backup of source AAP database
   - Export configuration manually as backup
   - Document any customizations or integrations

2. **Prepare Target Instance**
   - Fresh AAP installation recommended
   - Ensure same or newer version than source
   - Configure basic networking and DNS
   - Install required execution environments

3. **Test in Non-Production**
   - Run migration to dev/test environment first
   - Verify all critical job templates work
   - Test workflows end-to-end
   - Validate schedules trigger correctly

4. **Review Exported Configuration**
   ```bash
   # After export, review files
   cd /tmp/aap_migration
   grep -r '$encrypted$' .  # Find credentials needing manual update
   find . -name '*.yml' -exec wc -l {} + | sort -n  # Check export completeness
   ```

### During Migration

1. **Use Ansible Vault**
   - Always encrypt credential files
   - Use separate vault files for each environment
   - Rotate vault passwords regularly

2. **Monitor Progress**
   ```bash
   # Watch migration in another terminal
   tail -f /tmp/aap_migration/*.log

   # Monitor target AAP API
   watch -n 5 'curl -k -u admin:password https://target-aap/api/v2/ping/'
   ```

3. **Handle Errors Gracefully**
   - Review error messages carefully
   - Check source/target connectivity
   - Verify API access permissions
   - Retry failed tasks manually if needed

### After Migration

1. **Update Credentials**
   - Re-enter sensitive credential values (passwords, tokens, SSH keys)
   - Test credentials against target systems
   - Update credential permissions if needed

2. **Verify Projects**
   - Check all projects have synced successfully
   - Update project SCM URLs if needed (e.g., repo moved)
   - Verify project permissions

3. **Test Job Templates**
   - Run each job template manually
   - Verify survey questions work correctly
   - Check extra_vars are preserved
   - Test credential bindings

4. **Validate Workflows**
   - Test workflow job templates end-to-end
   - Verify convergence nodes work correctly
   - Check workflow approval nodes
   - Test error handling paths

5. **Update External Integrations**
   - Update webhook URLs
   - Update API endpoint references
   - Reconfigure notification endpoints
   - Update SSO/LDAP if instance-specific

6. **Clean Up**
   ```bash
   # After successful migration and validation
   rm -rf /tmp/aap_migration  # or archive for reference
   ```

## Troubleshooting

### Common Issues

#### Issue: "Failed to authenticate to source AAP"

**Symptoms:**
```
FAILED! => {"msg": "Received HTTP error for https://source-aap/api/v2/: 401 Unauthorized"}
```

**Solutions:**
- Verify credentials are correct
- Check user has admin/superuser permissions
- Confirm AAP is accessible from Ansible control node
- Try accessing API manually: `curl -u admin:password https://source-aap/api/v2/ping/`

#### Issue: "SSL certificate verification failed"

**Symptoms:**
```
FAILED! => {"msg": "SSL: CERTIFICATE_VERIFY_FAILED"}
```

**Solutions:**
- Set `migration_validate_certs: false` for self-signed certificates
- Add CA certificate to system trust store
- Use IP address instead of hostname (if DNS issues)

#### Issue: "Resource already exists" errors during import

**Symptoms:**
```
FAILED! => {"msg": "Organization 'Default' already exists"}
```

**Solutions:**
- Target instance should ideally be fresh/empty
- Use `migration_cleanup_drift: true` to force overwrite
- Manually delete conflicting resources on target
- Use organization filter to avoid conflicts

#### Issue: "Credentials showing $encrypted$ after migration"

**Symptoms:**
Credentials exist but show placeholder values.

**Solutions:**
- This is expected behavior for security
- Manually update credential values via UI or API
- Use Ansible Vault in exported files for automation
- Consider using credential management tools (HashiCorp Vault, etc.)

#### Issue: "Projects failing to sync on target"

**Symptoms:**
Projects exist but show sync failures.

**Solutions:**
- Check target has connectivity to SCM (Git/SVN) servers
- Verify SCM credentials migrated correctly
- Update project SCM URLs if they changed
- Check firewall rules allow target to reach SCM

#### Issue: "Out of memory during export"

**Symptoms:**
```
FAILED! => {"msg": "Allocation failed - Python ran out of memory"}
```

**Solutions:**
- Export smaller subsets using organization filter
- Increase system memory
- Use `migration_export_flatten: true` to reduce nesting
- Export specific resources only (filter by project/template ID)

### Debug Mode

Enable verbose output for troubleshooting:

```bash
ansible-playbook infra.aap_configuration_extended.migrate_aap_instance.yml \
  -e @migration_vars.yml \
  -vvv
```

### Check Exported Files

```bash
# Count exported resources
cd /tmp/aap_migration
find . -name "*.yml" -exec echo {} \; -exec yq eval '. | length' {} \;

# Validate YAML syntax
find . -name "*.yml" -exec yamllint {} \;

# Search for specific resources
grep -r "name: MyJobTemplate" .
```

### Manual API Testing

```bash
# Test source connectivity
curl -k -u admin:password https://source-aap/api/v2/organizations/ | jq .

# Test target connectivity
curl -k -u admin:password https://target-aap/api/v2/ping/ | jq .

# Get OAuth token
curl -k -X POST -u admin:password https://target-aap/api/gateway/v1/tokens/
```

## Advanced Scenarios

### Scenario 1: Multi-Stage Migration

For very large instances, break migration into stages:

```bash
# Stage 1: Infrastructure
ansible-playbook migrate_aap_instance.yml -e @vars.yml \
  -e "filetree_create_skip_job_templates=true" \
  -e "filetree_create_skip_workflow_job_templates=true"

# Stage 2: Job Templates (after projects sync)
# Re-export with only templates
# Manually import templates

# Stage 3: Workflows (after templates exist)
# Re-export with only workflows
# Manually import workflows
```

### Scenario 2: Cross-Version Migration

Migrating from AAP 2.4 to AAP 3.0:

```bash
# 1. Export from AAP 2.4
ansible-playbook migrate_aap_instance.yml -e @vars.yml

# 2. Transform exported data (manual step)
# Review and update any deprecated fields
# Update execution environment references

# 3. Import to AAP 3.0
# Continue with normal import process
```

### Scenario 3: Continuous Sync

Set up regular syncs from development to staging:

```bash
# Create cron job for nightly sync
cat > /etc/cron.d/aap-sync <<EOF
0 2 * * * ansible ansible-playbook migrate_aap_instance.yml \
  -e @/secure/dev-to-staging.yml \
  -e migration_cleanup_drift=true
EOF
```

### Scenario 4: Selective Resource Migration

Migrate only specific resource types:

```bash
# Export only credentials and projects
cat > selective_export.yml <<EOF
---
source_aap_hostname: "source.example.com"
source_aap_username: "admin"
source_aap_password: "password"
target_aap_hostname: "target.example.com"
target_aap_username: "admin"
target_aap_password: "password"

# Skip everything except what we want
filetree_create_skip_job_templates: true
filetree_create_skip_workflow_job_templates: true
filetree_create_skip_inventories: true
filetree_create_skip_users: true
filetree_create_skip_teams: true
EOF

ansible-playbook migrate_aap_instance.yml -e @selective_export.yml
```

### Scenario 5: Migration with Data Transformation

Modify resources during migration:

```bash
# After export, transform data
cd /tmp/aap_migration

# Example: Change all inventory names
find . -name "*.yml" -exec sed -i 's/inventory-old/inventory-new/g' {} \;

# Example: Update project URLs
find . -name "*.yml" -exec sed -i 's|old-git-server|new-git-server|g' {} \;

# Then run import phase only
# (Requires manual play execution - see playbook)
```

## Additional Resources

- [Collection README](../README.md) - Main documentation
- [Export Feature Guide](../EXPORT_README.md) - Detailed export documentation
- [Conversion Guide](../docs/CONVERSION_GUIDE.md) - Variable name mappings
- [Contributing Standards](../docs/STANDARDS.md) - Development guidelines

## Support

- **Issues**: Report bugs at https://github.com/redhat-cop/aap_configuration_extended/issues
- **Discussions**: Join discussions at https://github.com/redhat-cop/aap_configuration_extended/discussions
- **Matrix Chat**: #aap-config-as-code:ansible.com

## License

GNU General Public License v3.0 or later

See [LICENSE](../LICENSE) for full text.
