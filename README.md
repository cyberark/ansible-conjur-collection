# CyberArk Ansible Conjur Collection

This collection contains components to be used with CyberArk Conjur & Conjur Enterprise
hosted in [Ansible Galaxy](https://galaxy.ansible.com/cyberark/conjur).

## Table of Contents

* [Certification Level](#certification-level)
* [Requirements](#requirements)
* [Installation](#installation)
* [Conjur Ansible Role](#conjur-ansible-role)
  + [Usage](#usage)
  + [Role Variables](#role-variables)
  + [Example Playbook](#example-playbook)
  + [Summon & Service Managers](#summon---service-managers)
  + [Recommendations](#recommendations)
* [Conjur Ansible Lookup Plugin](#conjur-ansible-lookup-plugin)
  + [Environment variables](#environment-variables)
  + [Role Variables](#role-variables-1)
  + [Examples](#examples)
    - [Retrieve a secret in a Playbook](#retrieve-a-secret-in-a-playbook)
    - [Retrieve a private key in an Inventory file](#retrieve-a-private-key-in-an-inventory-file)
* [Conjur Ansible Collection Dev Environment](#set-up-a-development-environment)
  + [Setup a Conjur OSS Environment](#setup-a-conjur-oss-environment)
  + [Setup Conjur identity on managed host](#setup-conjur-identity-on-managed-host)
    - [Check Conjur identity](#check-conjur-identity)
    - [Set up Conjur identity](#set-up-conjur-identity)
    - [Set up Summon-Conjur](#set-up-summon-conjur)
* [Contributing](#contributing)
* [License](#license)

<!-- Table of contents generated with markdown-toc
http://ecotrust-canada.github.io/markdown-toc/ -->


## Certification Level

![](https://img.shields.io/badge/Certification%20Level-Community-28A745?link=https://github.com/cyberark/community/blob/main/Conjur/conventions/certification-levels.md)

This repo is a **Community** level project. It's a community contributed project that **is not reviewed or supported
by CyberArk**. For more detailed information on our certification levels, see [our community guidelines](https://github.com/cyberark/community/blob/main/Conjur/conventions/certification-levels.md#community).

## Requirements

- An instance of [CyberArk Conjur Open Source](https://www.conjur.org) v1.x+ or [CyberArk
  Conjur Enterprise](https://docs.cyberark.com/Product-Doc/OnlineHelp/AAM-DAP/Latest/en/Content/Resources/_TopNav/cc_Home.htm)
  (formerly DAP) v10.x+ accessible from the target node
- Ansible >= 2.9

## Using ansible-conjur-collection with Conjur Open Source

Are you using this project with [Conjur Open Source](https://github.com/cyberark/conjur)? Then we
**strongly** recommend choosing the version of this project to use from the latest [Conjur OSS
suite release](https://docs.conjur.org/Latest/en/Content/Overview/Conjur-OSS-Suite-Overview.html).
Conjur maintainers perform additional testing on the suite release versions to ensure
compatibility. When possible, upgrade your Conjur version to match the
[latest suite release](https://docs.conjur.org/Latest/en/Content/ReleaseNotes/ConjurOSS-suite-RN.htm);
when using integrations, choose the latest suite release that matches your Conjur version. For any
questions, please contact us on [Discourse](https://discuss.cyberarkcommons.org/c/conjur/5).
## Installation

From terminal, run the following command:
```sh
ansible-galaxy collection install cyberark.conjur
```

## Conjur Ansible Role

This Ansible role provides the ability to grant Conjur machine identity to a host. Based on that
identity, secrets can then be retrieved securely using the [Conjur Lookup
Plugin](#conjur-ansible-lookup-plugin) or using the [Summon](https://github.com/cyberark/summon)
tool (installed on hosts with identities created by this role).

### Usage

The Conjur role provides a method to establish the Conjur identity of a remote node with Ansible.
The node can then be granted least-privilege access to retrieve the secrets it needs in a secure
manner.

### Role Variables

* `conjur_appliance_url` _(Optional)_: URL of the running Conjur service
* `conjur_account` _(Optional)_: Conjur account name
* `conjur_host_factory_token` _(Optional)_: [Host
  Factory](https://developer.conjur.net/reference/services/host_factory/) token for layer
  enrollment. This should be specified in the environment on the Ansible controlling host.
* `conjur_host_name` _(Optional)_: Name of the host to be created.
* `conjur_ssl_certificate`: Public SSL certificate of the Conjur endpoint
* `conjur_validate_certs`: Boolean value to indicate if the Conjur endpoint should validate
  certificates
* `summon.version`: version of Summon to install. Default is `0.8.2`.
* `summon_conjur.version`: version of Summon-Conjur provider to install. Default is `0.5.3`.

The variables marked with _`(Optional)`_ are not required fields. All other variables are required
for running with an HTTPS Conjur endpoint.

### Example Playbook

Configure a remote node with a Conjur identity and Summon:
```yml
- hosts: servers
  roles:
    - role: cyberark.conjur.conjur-host-identity
      conjur_appliance_url: 'https://conjur.myorg.com'
      conjur_account: 'myorg'
      conjur_host_factory_token: "{{ lookup('env', 'HFTOKEN') }}"
      conjur_host_name: "{{ inventory_hostname }}"
      conjur_ssl_certificate: "{{ lookup('file', '/path/to/conjur.pem') }}"
      conjur_validate_certs: yes
```

This example:
- Registers the host `{{ inventory_hostname }}` with Conjur, adding it into the Conjur policy layer
  defined for the provided host factory token.
- Installs Summon with the Summon Conjur provider for secret retrieval from Conjur.

### Summon & Service Managers

With Summon installed, using Conjur with a Service Manager (like systemd) becomes a snap. Here's a
simple example of a `systemd` file connecting to Conjur:

```ini
[Unit]
Description=DemoApp
After=network-online.target

[Service]
User=DemoUser
#Environment=CONJUR_MAJOR_VERSION=4
ExecStart=/usr/local/bin/summon --yaml 'DB_PASSWORD: !var staging/demoapp/database/password' /usr/local/bin/myapp
```

> Note: When connecting to Conjur 4 (Conjur Enterprise), Summon requires the environment variable
`CONJUR_MAJOR_VERSION` set to `4`. You can provide it by uncommenting the relevant line above.

The above example uses Summon to retrieve the password stored in `staging/myapp/database/password`,
set it to an environment variable `DB_PASSWORD`, and provide it to the demo application process.
Using Summon, the secret is kept off disk. If the service is restarted, Summon retrieves the
password as the application is started.

### Recommendations

- Add `no_log: true` to each play that uses sensitive data, otherwise that data can be printed to
  the logs.

- Set the Ansible files to minimum permissions. Ansible uses the permissions of the user that runs
  it.

## Conjur Ansible Lookup Plugin

Fetch credentials from CyberArk Conjur using the controlling host's Conjur identity or environment
variables.

The controlling host running Ansible must have a Conjur identity, provided for example by the
[ConjurAnsible role](#conjur-ansible-role).

### Environment variables

The following environment variables will be used by the lookup plugin to authenticate with the
Conjur host, if they are present on the system running the lookup plugin.

- `CONJUR_ACCOUNT` : The Conjur account name
- `CONJUR_APPLIANCE_URL` : URL of the running Conjur service
- `CONJUR_CERT_FILE` : Path to the Conjur certificate file
- `CONJUR_AUTHN_LOGIN` : A valid Conjur host username
- `CONJUR_AUTHN_API_KEY` : The api key that corresponds to the Conjur host username
- `CONJUR_AUTHN_TOKEN_FILE` : Path to a file containing a valid Conjur auth token

### Role Variables

None.

### Examples

#### Retrieve a secret in a Playbook
```yaml
---
- hosts: localhost
  tasks:
  - name: Lookup variable in Conjur
    debug:
      msg: "{{ lookup('cyberark.conjur.conjur_variable', '/path/to/secret') }}"
```

#### Retrieve a private key in an Inventory file

```yaml
---
ansible_host: <host>
ansible_ssh_private_key_file: "{{ lookup('cyberark.conjur.conjur_variable', 'path/to/secret-id', as_file=True) }}"
```
**Note:** Using the `as_file=True` condition, the private key is stored in a temporary file and its path is written
in `ansible_ssh_private_key_file`.

## Set up a development environment

**Note**: If you are going to debug Conjur using [RubyMine IDE](https://www.jetbrains.com/ruby/) or [Visual Studio Code IDE](https://code.visualstudio.com),
see [RubyMine IDE Debugging](#rubymine-ide-debugging) or [Visual Studio Code IDE debugging](#visual-studio-code-ide-debugging) respectively before setting up the development environment.

The `dev` directory contains a `docker-compose` file which creates a development
environment with a database container (`pg`, short for *postgres*), and a
`conjur` server container with source code mounted into the directory
`/cyberark/dev/`.

To use it:

1. Install dependencies (as above)

2. Start the container (and optional extensions):

  ```sh-session
   $ cd dev
   $ ./start.sh
   ...
   root@f75015718049:/cyberark/dev/#
  ```

   Once the `start` script finishes, you're in a Bash shell inside the Conjur
   server container.  To

   After starting Conjur, your instance will be configured with the following:
   * Account: `cucumber`
   * User: `admin`
   * Password: Run `cat conjur.identity` inside the container shell to display the current logged-in identity (which is also the password)

3. Debug the server

  ```sh-session
   root@f39015718062:docker-compose exec <container-service-name> bash
   <various startup messages, then finally:>
   Use exit to stop
   ```

## Setup a Conjur OSS Environment

- Build, create, and start containers for OSS Conjur service
- Use .j2 template to generate inventory prepended with COMPOSE_PROJECT_NAME
- Deploy Conjur Lookup Plugin for Ansible
- Prepare and run Conjur Policy as [root.yml](#conjur-policy-example)
```sh
 docker exec conjur_client conjur policy load root /policy/root.yml
```
- Centralise the secrets

## Setup Conjur identity on managed host

- [Check Conjur identity](#check-conjur-identity)
- [Set up Conjur identity](#set-up-conjur-identity)
- [Set up Summon-Conjur](#set-up-summon-conjur)

## Check Conjur identity

- Set variable "Conjurized" ,if /etc/Conjur.identity already exists
- Ensure all required variables are set-
    - Conjur_account
    - Conjur_appliance_url
    - Conjur_host_name
- Set variable "ssl_configuration"
- Ensure all required ssl variables are set-
    - Conjur_ssl_certificate
    - Conjur_validate_certs
 - Set variable "ssl file path" at a path like "/etc/Conjur.pem"
 - Set variable when non ssl configuration
    - Conjur_ssl_certificate_path: ""
    - Conjur_validate_certs: no
- Ensure "Conjur_host_factory_token" is set (if node is not already Conjurized)

## Set up Conjur identity

- Install "ca-certificates" ,in case of any issue it retries 10 times on every 2 seconds of delay
- Place Conjur public SSL certificate
- Symlink Conjur public SSL certificate into /etc/ssl/certs
- Install openssl-perl Package when ansible_os_family is ‘RedHat’, in case of any issue it retries 10 times on every 2 seconds of delay
- copy files from the Ansible to the hosts  into /etc/Conjur.conf
- Request identity from Conjur
- Place identity file /etc/Conjur.identity when not Conjurized .

## Set up Summon-Conjur

- Download and unpack Summon
- Create folder for Summon-Conjur to be installed into
- Download and unpack Summon-Conjur

## Running the source

```sh
 ./start.sh
```

## Conjur Policy example

```sh
- !policy
  id: ansible
  annotations:
    description: Policy for Ansible master and remote hosts
  body:

  - !host
    id: ansible-master
    annotations:
      description: Host for running Ansible on remote targets

  - !layer &remote_hosts_layer
    id: remote_hosts
    annotations:
      description: Layer for Ansible remote hosts

  - !host-factory
    id: ansible-factory
    annotations:
      description: Factory to create new hosts for ansible
    layer: [ *remote_hosts_layer ]

  - !variable
    id: target-password
    annotations:
      description: Password needed by the Ansible remote machine

  - !permit
    role: *remote_hosts_layer
    privileges: [ execute ]
    resources: [ !variable target-password ]
```

## Useful links

| Source  | URLs |
| ------ | ------ |
| CyberArk Conjur |https://docs.conjur.org/Latest/en/Content/Integrations/ansible.html|
| GitHub | https://github.com/cyberark/ansible-conjur-collection|
| Ansible Galaxy | https://galaxy.ansible.com/cyberark/conjur_collection|
| Ansible Doc| https://docs.ansible.com/ansible/latest/collections/cyberark/conjur/index.html|

## Contributing

We welcome contributions of all kinds to this repository. For instructions on how to get started and
descriptions of our development workflows, please see our [contributing guide][contrib].

[contrib]: https://github.com/cyberark/ansible-conjur-collection/blob/main/CONTRIBUTING.md

## License

Copyright (c) 2020 CyberArk Software Ltd. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing permissions and limitations under the
License.

For the full license text see [`LICENSE`](LICENSE).
