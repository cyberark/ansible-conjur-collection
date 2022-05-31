# Contributing to the Ansible Conjur Collection

Thanks for your interest in Conjur. Before contributing, please take a moment to
read and sign our <a href="https://github.com/cyberark/community/blob/master/documents/CyberArk_Open_Source_Contributor_Agreement.pdf" download="conjur_contributor_agreement">Contributor Agreement</a>.
This provides patent protection for all Conjur users and allows CyberArk to enforce
its license terms. Please email a signed copy to <a href="oss@cyberark.com">oss@cyberark.com</a>.
For general contribution and community guidelines, please see the [community repo](https://github.com/cyberark/community).

- Contributing to the Ansible Conjur Collection
  - [Prerequisites](#prerequisites)
  - [Set up a development environment](#set-up-a-development-environment)
  - [Testing](#testing)
  - [Releasing](#releasing)
- Ansible Conjur Collection Quick Start
    1. [Set up Conjur Open Source and Ansible control node](#set-up-conjur-open-source-and-ansible-control-node)
    2. [Load policy to set up Conjur Ansible integration](#load-policy-to-set-up-conjur-ansible-integration)
    3. [Create Ansible managed nodes](#create-ansible-managed-nodes)
    4. [Use `conjur_host_identity` to set up Conjur identity on managed nodes](#use-conjur-host-identity-to-set-up-conjur-identity-on-managed-nodes)
    5. [Use `conjur_variable` lookup plugin to provide secrets to Ansible Playbooks](#use-conjur-variable-lookup-plugin-to-provide-secrets-to-ansible-playbooks)


 ## Prerequisites

To start developing and testing using our development scripts ,
the following tools need to be installed:

1. [Git][get-git] to manage source code
2. [Docker][get-docker] to manage dependencies and runtime environments
3. [Docker Compose][get-docker-compose] to orchestrate Docker environments

[get-docker]: https://docs.docker.com/engine/installation
[get-docker-compose]: https://docs.docker.com/compose/install
[get-git]: https://git-scm.com/downloads

## Set up a development environment

The `dev` directory contains a `docker-compose` file which creates a development
environment :
-  A Conjur Open Source instance
-  An Ansible control node
-  Managed nodes to push tasks to

To use it:

    Install dependencies (as above)

To setup the dev environment, you first need to clone the GitHub repository [cyberark/ansible-conjur-collection](https://github.com/cyberark/ansible-conjur-collection) repository in your directory and then run start.sh script


 ```sh-session
 $ git clone https://github.com/cyberark/ansible-conjur-collection.git
 $ cd ansible-conjur-collection/dev
 $ ./start.sh

 ```
### Verification

  When start.sh script has successfully setup Conjur environment along with the inventory machines, the terminal returns the following:

   ```sh-session
   ...
   PLAY RECAP *********************************************************************
   ansibleplugingtestingconjurhostidentity-test_app_centos-1 : ok=17 ...
   ansibleplugingtestingconjurhostidentity-test_app_centos-2 : ok=17 ...
   ansibleplugingtestingconjurhostidentity-test_app_ubuntu-1 : ok=16 ...
   ansibleplugingtestingconjurhostidentity-test_app_ubuntu-2 : ok=16 ...

   ```

   After starting Conjur, your instance will be configured with the following:
   * Account: `cucumber`
   * User: `admin`
   * Password: Run `conjurctl role retrieve-key cucumber:user:admin` inside the Conjur container shell to retrieve the admin user API key (which is also the  password)

### Useful links

- [Official documentation for Conjur's Ansible integration](https://docs.conjur.org/Latest/en/Content/Integrations/ansible.html)
- [Conjur Collection on Ansible Galaxy](https://galaxy.ansible.com/cyberark/conjur)
- [Ansible documentation for the Conjur collection](https://docs.ansible.com/ansible/latest/collections/cyberark/conjur/index.html)

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
    - This will kick off an automated script which will publish the release to
      [Ansible Galaxy](https://galaxy.ansible.com/cyberark/conjur)

- Create the release on GitHub for that tag
    - Build the release package with `./ci/build_release`
    - Attach package to Github Release

## Set up Conjur Open Source and Ansible control node
  -  Setup a conjur OSS Environment
      - Pull the Docker image

          ```sh-session
          docker-compose pull
          ```

      - Generate the master key

          ```sh-session
          docker-compose run --no-deps --rm conjur data-key generate > data_key
          ```

      - Load master key as an environment variable

          ```sh-session
          export CONJUR_DATA_KEY="$(< data_key)"
          ```

      - Start the Conjur OSS environment

          ```sh-session
          docker-compose up -d
          ```

      - Create admin account

          ```sh-session
          docker-compose exec conjur conjurctl account create myConjurAccount > admin_data
          ```

      - Connect the Conjur client to the Conjur server

          ```sh-session
          docker-compose exec client conjur init -u conjur -a myConjurAccount
          ```

 -  Granting a Conjur identity to Ansible hosts
     - To grant your Ansible host a Conjur identity, you first must install the Conjur Ansible Role in your     playbook directly

          ```sh-session
          ansible-galaxy install cyberark.conjur-host-identity
          ```
     - Once you've done this, you can configure each Ansible node with a Conjur identity by including a section like the example below in your Ansible playbook:

          ```sh-session
          - hosts: servers
            roles:
              - role: cyberark.conjur-host-identity
                conjur_appliance_url: 'https://conjur.myorg.com',
                conjur_account: 'myorg',
                conjur_host_factory_token: "{{lookup('env', 'HFTOKEN')}}",
                conjur_host_name: "{{inventory_hostname}}"
          ```
     - First we register the host with Conjur, adding it into the layer specific to the provided host factory token, and then installs Summon with the Summon Conjur provider for secret retrieval from Conjur.

##  Load policy to set up Conjur Ansible integration

  Conjur policy assigns roles to your organization's users, groups, machines, and web services, and uses those roles to control access to your secrets.
  To load policy into conjur :-

  ```sh
  docker exec conjur_client conjur policy load root /policy/root.yml
  ```
  [Conjur policy example](https://github.com/cyberark/ansible-conjur-collection/blob/main/dev/policy/root.yml)

##  Create Ansible managed nodes

  On Ansible managed nodees ,ensure `Conjur_host_factory_token` and all required variables are set . Install `ca-certificates` and place Conjur public SSL certificate. Symlink Conjur public SSL certificate into /etc/ssl/certs .

  [Github code reference](https://github.com/cyberark/ansible-conjur-collection/blob/main/roles/conjur_host_identity/tasks/identity.yml)

##  Use conjur host identity to set up Conjur identity on managed nodes
ß
  Copy files from Ansible to the managed hosts into /etc/Conjur.conf and request identity from Conjur and place Conjur identity  file into /etc/.

  [Github code reference](https://github.com/cyberark/ansible-conjur-collection/blob/main/roles/conjur_host_identity/tasks/identity.yml)

##  Use conjur variable lookup plugin to provide secrets to Ansible Playbooks

  The lookup plugin uses the identity of the control node to retrieve secrets from Conjur and provide them to the relevant playbook. The control node has execute permission on all relevant variables. It retrieves values from Conjur at runtime. The retrieved secrets are inserted by the playbook where needed before the playbook is passed to the remote nodes.

  The control node simply passes the values onto the remote nodes in a playbook through SSH, and the secrets disappear along with the playbook at the end of execution.

  ```sh-session
  vars:
  database_url: "{{ lookup('cyberark.conjur.conjur_variable', '/path/to/secret') }}"
  ```
