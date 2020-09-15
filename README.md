![](https://img.shields.io/badge/Certification%20Level-Community-28A745?link=https://github.com/cyberark/community/blob/master/Conjur/conventions/certification-levels.md)

# CyberArk Ansible Conjur Collection

This collection contains plugins to be used for CyberArk Conjur & DAP (Dynamic Access Provider) hosted in [ansible galaxy](https://galaxy.ansible.com/cyberark/conjur).

## Table of Contents
- [CyberArk Ansible Conjur Collection](#cyberark-ansible-conjur-collection)
  * [Requirements](#requirements)
  * [conjur_variable Lookup Plugin](#conjur_variable-lookup-plugin)
    + [Role Variables](#role-variables)
    + [Dependencies](#dependencies)
    + [Example Playbook](#example-playbook)
  * [Conjur Ansible Role](#conjur-ansible-role)
    + [Usage](#usage)
    + [Role Variables](#role-variables-1)
    + [Dependencies](#dependencies)
    + [Example Playbook](#example-playbook-1)
    + [Summon & Service Managers](#summon---service-managers)
    + [Recommendations](#recommendations)
  * [Contributing](#contributing)
  * [License](#license)

<!-- Table of contents generated with markdown-toc
http://ecotrust-canada.github.io/markdown-toc/ -->

## Requirements

- conjur_variable Lookup Plugin
  - [CyberArk Conjur Open Source](https://www.conjur.org) v1.x+ or
  - [CyberArk Dynamic Access Provider](https://docs.cyberark.com/Product-Doc/OnlineHelp/AAM-DAP/Latest/en/Content/Resources/_TopNav/cc_Home.htm) v10.x+
  - Ansible >= 2.9

- Conjur Role
  - A running Conjur service that is accessible from the target nodes.
  - Ansible >= 2.3.0.0

## Installation 
From terminal, run the following command:
```sh
ansible-galaxy collection install cyberark.conjur
```

## conjur_variable Lookup Plugin
Fetch credentials from CyberArk Conjur using the controlling host's Conjur identity or environment variables.

- The controlling host running Ansible has a Conjur identity. [More Information here](https://docs.conjur.org/latest/en/Content/Get%20Started/key_concepts/machine_identity.html) and here in [Conjur Ansible role project](https://github.com/cyberark/ansible-conjur-host-identity/)

- Environment variables could be `CONJUR_ACCOUNT`, `CONJUR_APPLIANCE_URL`, `CONJUR_CERT_FILE`, `CONJUR_AUTHN_LOGIN`, `CONJUR_AUTHN_API_KEY`, `CONJUR_AUTHN_TOKEN_FILE`

### Role Variables

None.
<br>

### Example Playbook

```yaml
---
- hosts: localhost
  tasks:
  - name: Lookup variable in Conjur
    debug:
      msg: "{{ lookup('cyberark.conjur.conjur_variable', '/path/to/secret') }}"
```

## Conjur Ansible Role
This Ansible role provides the ability to grant Conjur machine identity to a host. Based on that identity, secrets can then be retrieved securely using the [Summon](https://github.com/cyberark/summon) tool (installed on hosts with identities created by this role).

### Usage
The Conjur role provides a method to "Conjurize" or establish the Conjur identity of a remote node with Ansible. The node can then be granted least-privilege access to retrieve the secrets it needs in a secure manner.

### Role Variables

* `conjur_appliance_url` `*`: URL of the running Conjur service
* `conjur_account` `*`: Conjur account name
* `conjur_host_factory_token` `*`: [Host Factory](https://developer.conjur.net/reference/services/host_factory/) token for
layer enrollment. This should be specified in the environment on the Ansible controlling host.
* `conjur_host_name` `*`: Name of the host being conjurized.
* `conjur_ssl_certificate`: Public SSL certificate of the Conjur endpoint
* `conjur_validate_certs`: Boolean value to indicate if the Conjur endpoint should validate certificates
* `summon.version`: version of Summon to install. Default is `0.6.6`.
* `summon_conjur.version`: version of Summon-Conjur provider to install. Default is `0.5.0`.

The variables marked with `*` are required fields. The other variables are required for running with an HTTPS Conjur endpoint, but are not required if you run with an HTTP Conjur endpoint.

### Dependencies

None.
<br/>

### Example Playbook

Configure a remote node with a Conjur identity and Summon:
```yml
- hosts: servers
  roles:
    - role: cyberark.conjur-host-identity
      conjur_appliance_url: 'https://conjur.myorg.com/api',
      conjur_account: 'myorg',
      conjur_host_factory_token: "{{lookup('env', 'HFTOKEN')}}",
      conjur_host_name: "{{inventory_hostname}}"
```

This example:
- Registers the host with Conjur, adding it into the layer specific to the provided host factory token.
- Installs Summon with the Summon Conjur provider for secret retrieval from Conjur.

### Summon & Service Managers
With Summon installed, using Conjur with a Service Manager (like SystemD) becomes a snap.  Here's a simple example of a SystemD file connecting to Conjur:
```ini
[Unit]
Description=DemoApp
After=network-online.target

[Service]
User=DemoUser
#Environment=CONJUR_MAJOR_VERSION=4
ExecStart=/usr/local/bin/summon --yaml 'DB_PASSWORD: !var staging/demoapp/database/password' /usr/local/bin/myapp
```
> Note:
When connecting to Conjur 4 (Conjur Enterprise), Summon requires the environment variable `CONJUR_MAJOR_VERSION` set to `4`. You can provide it by uncommenting the relevant line above.

The above example uses Summon to retrieve the password stored in `staging/myapp/database/password`, set it to an environment variable `DB_PASSWORD`, and provide it to the demo application process. Using Summon, the secret is kept off disk. If the service is restarted, Summon retrieves the password as the application is started.

### Recommendations

- Add `no_log: true` to each play that uses sensitive data, otherwise that data can be printed to the logs.

- Set the Ansible files to minimum permissions. Ansible uses the permissions of the user that runs it.

## Contributing

We welcome contributions of all kinds to this repository. For instructions on how to get started and descriptions of our development workflows, please see our [contributing
guide][contrib].

[contrib]: https://github.com/cyberark/ansible-conjur-collection/blob/master/CONTRIBUTING.md

## License

This repository is licensed under Apache License 2.0 - see [`LICENSE`](LICENSE) for more details.
