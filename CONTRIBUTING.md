# Contributing to the Ansible Conjur Collection
Thanks for your interest in Conjur. Before contributing, please take a moment to
read and sign our <a href="https://github.com/cyberark/community/blob/master/documents/CyberArk_Open_Source_Contributor_Agreement.pdf" download="conjur_contributor_agreement">Contributor Agreement</a>.
This provides patent protection for all Conjur users and allows CyberArk to enforce
its license terms. Please email a signed copy to <a href="oss@cyberark.com">oss@cyberark.com</a>.
For general contribution and community guidelines, please see the [community repo](https://github.com/cyberark/community).

- [Contributing to the Ansible Conjur Collection](#contributing-to-the-ansible-conjur-collection)
  - [Prerequisites](#prerequisites)
  - [Set up a development environment](#set-up-a-development-environment)
      + [Setup a Conjur OSS Environment](#setup-a-conjur-oss-environment)
      + [Setup Conjur identity on managed host](#setup-conjur-identity-on-managed-host)
          - [Check Conjur identity](#check-conjur-identity)
          - [Set up Conjur identity](#set-up-conjur-identity)
          - [Set up Summon-Conjur](#set-up-summon-conjur)
   - [Testing](#testing)
   - [Releasing](#releasing)
  
  
 ## Prerequisites

Before getting started, you should install some developer tools. These are not
required to deploy Conjur but they will let you develop using a standardized,
expertly configured environment.

1. [git][get-git] to manage source code
2. [Docker][get-docker] to manage dependencies and runtime environments
3. [Docker Compose][get-docker-compose] to orchestrate Docker environments
4. [Ruby version 3 or higher installed][install-ruby-3] - native installation or using [RVM][install-rvm].

[get-docker]: https://docs.docker.com/engine/installation
[get-git]: https://git-scm.com/downloads
[get-docker-compose]: https://docs.docker.com/compose/install
[install-ruby-3]: https://www.ruby-lang.org/en/documentation/installation/
[install-rvm]: https://rvm.io/rvm/install


## Set up a development environment

**Note**: If you are going to debug Conjur using [RubyMine IDE](https://www.jetbrains.com/ruby/) or [Visual Studio Code IDE](https://code.visualstudio.com),
see [RubyMine IDE Debugging](#rubymine-ide-debugging) or [Visual Studio Code IDE debugging](#visual-studio-code-ide-debugging) respectively before setting up the development environment.

The `dev` directory contains a `docker-compose` file which creates a development
environment with a database container (`pg`, short for *postgres*), and a
`conjur` server container with source code mounted into the directory
`/cyberark/dev/`.

To use it:

1. Install dependencies (as above)

1. Start the container (and optional extensions):

   ```sh-session
   $ cd dev
   $ ./start
   ...
   root@f75015718049:/cyberark/dev/#
   ```

   Once the `start` script finishes, you're in a Bash shell inside the Conjur
   server container.  To

   After starting Conjur, your instance will be configured with the following:
   * Account: `cucumber`
   * User: `admin`
   * Password: Run `cat conjur.identity` inside the container shell to display the current logged-in identity (which is also the password)

1. Debug the server

   ```sh-session
   root@f39015718062:docker-compose exec <server-image-name> bash
   <various startup messages, then finally:>
   Use exit to stop
   ```

1. Cleanup

    ```sh-session
    $ ./stop
    ```
    Running `stop` removes the running Docker Compose containers and the data key.


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

- Check if /etc/Conjur.identity already exists
- Set variable "Conjurized"
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


## Testing

To run a specific set of tests:

```sh-session
$ cd tests
$ ./test.sh -d <role or plugin name>
```
To run all tests:

```sh-session
$ cd tests
$ ./test.sh -a
```

## Releasing

From a clean instance of main, perform the following actions to release a new version 
of this plugin:

- Update the version number in [`galaxy.yml`](galaxy.yml) and [`CHANGELOG.md`](CHANGELOG.md)
    - Verify that all changes for this version in `CHANGELOG.md` are clear and accurate, 
      and are followed by a link to their respective issue
    - Create a PR with these changes

- Create an annotated tag with the new version, formatted as `v##.##.##`
    - This will kick off an automated script which publish the release to 
      [Ansible Galaxy](https://galaxy.ansible.com/cyberark/conjur)
    
- Create the release on GitHub for that tag
    - Build the release package with `./ci/build_release`
    - Attach package to Github Release


