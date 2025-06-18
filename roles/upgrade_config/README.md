# Upgrade Config Role

This role is designed to automatically convert the configuration files used for AAP <= 2.4 CaC collections to the new format supported by the AAP >= 2.5 CaC collections.

The following conversions are implemented:

<!-- markdownlint-disable-line MD033 --><table>
<!-- markdownlint-disable-line MD033 -->    <thead>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <th>Component</th>
<!-- markdownlint-disable-line MD033 -->            <th>AAP <= 2.4</th>
<!-- markdownlint-disable-line MD033 -->            <th>AAP >= 2.5</th>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->    </thead>
<!-- markdownlint-disable-line MD033 -->    <tbody>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td rowspan=2>LDAP Configuration</td>
<!-- markdownlint-disable-line MD033 -->            <td>Connection variables</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticators</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td>User and group mappings</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticator Maps</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td rowspan=2>SAML Configuration</td>
<!-- markdownlint-disable-line MD033 -->            <td>Connection variables</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticators</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->        <tr>
<!-- markdownlint-disable-line MD033 -->            <td>User and group mappings</td>
<!-- markdownlint-disable-line MD033 -->            <td>Gateway Authenticator Maps</td>
<!-- markdownlint-disable-line MD033 -->        </tr>
<!-- markdownlint-disable-line MD033 -->    </tbody>
<!-- markdownlint-disable-line MD033 --></table>

## Role Variables

| Variable          |  Required  |  Type  | Description                                    |
| ----------------- | :--------: | :----: | :--------------------------------------------- |
| aap24_configs_dir | Yes        | Path   | Path tha contains the CaC files for AAP <= 2.4 |
| aap25_configs_dir | Yes        | Path   | Path tha contains the CaC files for AAP >= 2.5 |

## Known problems

* After the conversion, the generated file `gateway_authenticators.yaml` must be updated by, at least, the following two fields:
  * SAML:
    * configuration -> CALLBACK_URL: This field must be set to the correct URL
    * configuration -> SP_PRIVATE_KEY: This field must be set to the correct private key, having the following format:

      ```yaml
      SP_PRIVATE_KEY: |
        -----BEGIN PRIVATE KEY-----
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXX
        -----END PRIVATE KEY-----

      ```

## Example Playbook

```yaml
---
#
# ansible-playbook -i localhost, playbooks/upgrade_config.yaml -e '{sanitize: true}'
#
- name: "Playbook to upgrade CaC from AAP <= 2.4 to AAP >= 2.5 format"
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: "Call upgrade_config role"
      ansible.builtin.include_role:
        name: infra.aap_configuration_extended.upgrade_config
      vars:
        input_authenticator_name: "IDM LDAP"
...
```

## License

GPLv3+

## Author Information

* [ivarmu](https://github.com/ivarmu)
