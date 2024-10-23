# aap_rules_validation

An ansible role which audit the declared AAP configuration and validate it against a set of user-defined rules. 

At the end of the role's execution, a structured data list and human readable report are generated containing the detected violations.

The actual version of the role supports only the controller component

## Requirements

n/a

## Role Input Variables

| Variable Name | Default Value | Required | Description |
| :------------ | :-----------: | :------: | :---------- |
| `aap_rules` | `[]`     | yes      | The list of rules to enforce on the declared configuration |
| `fail_if_violations_found` | `true` | no  | Force the role to fails if if it finds violations  |
| `print_rules_violations_data` | `true` | no  | Print the detailed violation data before printing the violation messages  |
| `audited_objects` | a list of all the objet types | no  | The objects to be audited. See the roles defaults main.yml file for the complete list  |
| `warn_about_audited_types_not_in_rules_objects` | `false` | no | Treat the objects to be audited but are not in any rule as a violation |
| `warn_about_rules_objects_not_in_audited_types` | `false` | no | Treat the objects that are defined in rules are not in the audited objects list as a violation  |

## Role Output Variables

| Variable Name |  Description |
| :------------ |  :---------- |
| `rules_violations_data`  | a list of dictionaries containing all the found rules violation details    |
| `rules_violations_msgs`  | a list of all the found rules violation messages |


### rules_violations_msgs format

Each `rules_violations_msgs` list element has the following syntax :

```
Rule ID | Object Type | Object Scope | Object Name | Violation message related to this specific object"
```

Example of `rules_violations_msgs` :

```json
fatal: [localhost]: FAILED! => {
    "rules_violations_msgs | unique": [
        "Rule n°1 | organizations | global | Satellite | max_hosts is not set",
        "Rule n°2 | organizations | global | Default | The EE (Automation Hub Default Execution Environment) is forbidden.",
        "Rule n°3 | projects | Default | Test Project 3 | The value of the field name (Test Project 3) do not respect the regex (^\\[Default\\].*)",
        "Rule n°4 | groups | global | group3 | The mandatory field 'description' is not defined"
    ]
}
```

### rules_violations_data structure

Each `rules_violations_data` list element contains the following elements :

| Sub-element Name |  Description |
| :------------ |  :---------- |
| `msg`  | The violation message relative to this object. Same format as in `rules_violations_msgs` |
| `object_name`  | Name of the non-compliant object |
| `object_organization`  | Name of the organization to which belong the affected object if available. |
| `object_scope`  | Scope of the non-compliant object, one of two values : `global` or `organization` |
| `object_type`  | Type of the non-compliant object |
| `rule_broken`  | The rule not respected by the non-compliant object |
| `rule_id`  | Rule name if available otherwise the rule order (index + 1) |
| `rule_index`  | Index of rule (starting from 0) |

Example of `rules_violations_data` :

```json
"rules_violations_data | unique": [
    {
        "msg": "Rule n°1 | organizations | global | Satellite | max_hosts is not set",
        "object_name": "Satellite",
        "object_organization": "__undefined_org__",
        "object_scope": "global",
        "object_type": "organizations",
        "rule_broken": "max_hosts_per_organization",
        "rule_id": "n°1",
        "rule_index": 0
    },
    ...
```

## Rules

The rules should be defined as a list in the variable `aap_rules`

Each element of the list is a rule that is audited seperately

There is generic rules fields which are object-type-agnostic and other fields that are applicable to specific object type

### Generic Rules

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `rule_name`   |  string   | A descriptive string set by the user to better identify the rule  |
| `organizations` | list     | Limit the audit to the objects belonging to the organizations specified in this list. Not applicable to every rule. See the rules below for mor details.  |
| `objects`   | list   | The object types to be audited  |
| `exceptions` | dictionary   | The specific objects to be discarded from the audit. Applicable only to specific rules. See specific rules details below.  |
| `mandatory_fields`  | list   | The fields that are mandatory. It is a violation if they are empty or undefined. At the moment, `organizations` is ineffective with this rule. |
| `minimum_defined_globally`  | integer   | The minimum objects count allowed to be defined globally for the objects specified in `objects` |
| `maximum_defined_globally`  | integer   | The maximum objects count allowed to be defined globally for the objects specified in `objects` |
| `minimum_defined_per_org`  | integer   | The minimum objects count allowed to be defined in the organizations specified in `organizations` for the objects specified in `objects` |
| `maximum_defined_per_org`  | integer   | The maximum objects count allowed to be defined in the organizations specified in `organizations` for the objects specified in `objects` |
| `fields_regex`  | dictionary  | control if the fields of the objects defined in `objects` respect the declared regular expression. The dictionary keys are the fields to be monitored and the values are the corresponding regex. See examples below. |

#### Generic Rule Examples

Here's examples of generic rules 

```yaml
aap_rules:

  # ------- Rule n°1  # Generic - Make 'description' a mandatory fields for the listed objects
  - objects:
      - credentials
      - inventories
      - inventory_sources
      - job_templates
      - projects
      - teams
      - users
      - instances
    mandatory_fields:
      - description  # the field 'description' must be defined and non-empty for each of the object types listed in 'objects'

  # ------- Rule n°2 # Generic - Minimum and Maximum
  - rule_name: Minimum and Maximum
    organizations:
      - Satellite
      - Default
    objects:
      - credentials
      - groups
      - inventories
      - inventory_sources
      - job_templates
      - projects
      - teams
      - users
      - credential_types
      - instances
    minimum_defined_globally: 3  # each object type listed in 'objects' must be defined at least 3 times in all of AAP
    maximum_defined_globally: 5
    minimum_defined_per_org: 2  # each object type listed in 'objects' must be defined at least 2 times in each organization
    maximum_defined_per_org: 4

  # ------- Rule n°3  # Generic - Check if 'projects' and 'credentials' of the 'Default' org respect the regex
  - organizations:
      - Default
    objects:
      - projects
      - credentials
    fields_regex:
      name: '^\[Default\].*'       # name must start with '[Default]'
      description: "^DESC - .*"  # description must start with 'DESC - '
      scm_type: ^git$            # accept only git scm
      scm_branch: ^main$         # branch naming rule : accept only main branch
```

### Object specific Rules

#### Organizations

The following rules are specific to organizations and are ineffective for other type of objects.

The organizations specific rules are compatible with the `exceptions` field

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `max_hosts_per_organization`   |  integer   | The maximum hosts count allowed for the organization  |
| `allowed_organization_default_environments`   |  list   | The only possible EEs to be used in the organization  |
| `forbidden_organization_default_environments` |  integer  | The maximum hosts count allowed for the organization  |

##### Organizations specific rules examples :

```yaml
aap_rules:

  # # ------- Rule n°4 # Organizations - Allow only the following EEs for the organizations 'Satellite' and 'Default'
  - objects:
      - organizations
    organizations:
      - Satellite
      - Default
    max_hosts_per_organization: 100
    allowed_organization_default_environments:
      - Automation Hub Default Execution Environment
      - Custom EE

  # # ------- Rule n°5 # Organizations - Allow all EEs except the listed forbidden EEs for all organizations except the org 'Satellite'
  - objects:
      - organizations
    max_hosts_per_organization: 10
    forbidden_organization_default_environments:
      - Automation Hub Default Execution Environment
    exceptions:
      organizations:
        - Satellite
```

#### Inventories

The following rule is specific to the inventories. However it needs both `controller_hosts` and `controller_inventories` to be defined to work correctly.

The inventories specific rules are compatible with the `exceptions` field

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `max_hosts_per_inventory`   |  integer   | The maximum hosts count allowed for the organization  |

##### Inventories specific rules examples :

```yaml
aap_rules:

  # ------- Rule n°6  # inventories - The static hosts maximum count of each inventories of the organization 'Satellite' and 'Default' should not exceed 10 except the 'localhost' inventory

  - organizations:
      - Satellite
      - Default
    objects:
      - inventories
    max_hosts_per_inventory: 10  # needs 'controller_hosts' and 'controller_inventories' to be defined
    exceptions:
      inventories:
        - localhost
```

#### Hosts

The following rule is specific to hosts. However it needs both `controller_groups` and `controller_hosts` to be defined to work correctly.

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `allow_ungrouped_hosts`|  boolean | Set to `true` to flag ungrouped hosts as violations  |

##### Hosts specific rules examples

```yaml
aap_rules:

  # ------- Rule n°7 # Hosts
  - objects:
      - hosts
    allow_ungrouped_hosts: false  # needs 'controller_groups' and 'controller_hosts' to be defined
```

#### Credentials

The following rules are specific to credentials.

The sensitive data encryption check **will not work** if the credentials transit through intermediary variables, like when the `filetree_read` role is used.

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `encrypt_credentials_sensitive_data`  |  boolean   | Set to `true` to activate sensitive data encryption check |
| `credential_sensitive_data`   |  dictionary   | The credential types and the lists of the sensitive fields to check. The dictionary keys are the credential type to check and the values are the list of the input sub-fields. See the example below.   |

##### Credentials specific rules examples


```yaml
aap_rules:

  # ------- Rule n°8  # Credentials
  - encrypt_credentials_sensitive_data: true              # DO NOT WORK with intermediary variables (filetree_read)
    organizations:
      - Default
      - Satellite
    objects:
      - credentials
    credential_sensitive_data:
      Source Control:
        - password
      Red Hat Virtualization:
        - password
      Vault:
        - vault_password
```

#### Users

The following rules are specific to users.

The users rules are compatible with the `exceptions` option.

The `encrypt_user_passwords` option **will not work** if the users transit through intermediary variables, like when the `filetree_read` role is used.

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `allow_superusers`|  boolean | Set to `false` to flag superusers as a violation  |
| `allow_system_auditors`|  boolean | Set to `false` to flag system auditors as a violation  |
| `encrypt_user_passwords`|  boolean | Set to `true` to flag unvaulted users passwords as a violation  |

##### Users specific rules examples

```yaml
aap_rules:

  # ------- Rule n°9  # Users - do not allow system auditors or super-admins except the 'controller-admin' and 'admin' users
  - objects:
      - users
    allow_superusers: false
    allow_system_auditors: false
    encrypt_user_passwords: true
    exceptions:
      users:
        - controller_admin
        - admin
```

#### Roles

The following rules are specific to roles.

| Variable Name | Type     | Description |
| :------------ | :------: | :---------- |
| `allowed_roles`|  dictionary   | The allowed objects roles. Any role not explicitly listed in this dictionary will be flagged as a violation. The dictionary keys are the object types and the values are the list of the allowed roles. See the example below.   |
| `forbidden_roles`|  dictionary   | The forbidden objects roles. The roles listed in this dictionary will be considered as a violation. Any other role not specified in this dictionary is allowed. The dictionary keys are the object types and the values are the list of the forbidden roles. See the example below. |

##### Roles specific rules examples

```yaml
aap_rules:

  # ------- Rule n°10  # Roles - Allow ONLY 'read' on projects, 'member' on organizations and 'admin' on teams
  - objects:
      - roles
    allowed_roles:
      projects:
        - update
        - read
      organizations:
        - member
      target_teams:
        - member

  # ------- Rule n°11  # Roles - Do not allow 'admin' on projects, 'admin' on organizations and 'admin' on teams, allow everything else.
  - objects:
      - roles
    forbidden_roles:
      projects:
        - admin
      organizations:
        - admin
      target_teams:
        - admin
```

## License

[GPLv3+](https://github.com/ansible/galaxy_collection#licensing)

## Author

[Hamza Bouabdallah](https://github.com/w4hf)
