# Ansible Conjur Collection Certified Effort - Spike

Figure out what we'll need to do to get
[cyberark/ansible-conjur-collection](https://github.com/cyberark/ansible-conjur-collection)
to Certified level based on our
[community guidelines](https://github.com/cyberark/community/blob/main/Conjur/conventions/certification-levels.md#certified).

CyberArk internal issue link:
[ONYX-14258](https://ca-il-jira.il.cyber-ark.com:8443/browse/ONYX-14258)

### What is Ansible?

> Ansible is a radically simple IT automation engine that automates cloud
> provisioning, configuration management, application deployment, intra-service
> orchestration, and many other IT needs.

> Ansible works by connecting to your nodes and pushing out scripts called
> "Ansible modules" to them. Most modules accept parameters that describe the
> desired state of the system. Ansible then executes these modules, and removes
> them when finished.

> Plugins augment Ansible's core functionality. While modules execute on the
> target system in separate processes, plugins execute on the control node
> within the `/usr/bin/ansible` process. Plugins offer options and extensions
> for the core features of Ansible - transforming data, logging output,
> connecting to inventory, and more.

> Playbooks can finely orchestrate multiple multiple slices of your
> infrastructure topology, with very detailed control over how many machines

### What does the Ansible Conjur Collection provide?

The Ansible Conjur Collection makes the use and consumption of Conjur much
easier. The Collection has two components:

- Role: `conjur_host_identity`
  - Allows users to establish machine identities for Nodes
  - Uses the
    [Host Factory](https://docs.conjur.org/Latest/en/Content/Operations/Services/host_factory.html?tocpath=Fundamentals%7CAuthentication%7C_____11)
    pattern to create identities and configuration files on a Node's file system
- Plugin: `conjur_variable`
  - When running Playbooks, this lookup plugin retrieves Conjur secrets and
    writes them to a Node's file system
  - Seamless way to consume Conjur secrets in Playbooks

## Review: Certification Level Requirements

### :white_check_mark: Community

Characteristics of a Community Level feature:

- [x] Feature/Product has a name.
- [x] Feature can be demonstrated with a single use case.
- [x] Feature has value to our customers.
- [x] Feature is available in a tagged version.
  - [x] For CyberArk-maintained software, GitHub tags will be used. If the
        feature is part of a larger project, it must be feature-flagged off by
        default.
  - [ ] For non-CyberArk maintained software, versioned release artifacts will
        be uploaded to CyberArk Marketplace with the "Community" Certification
        Level. A software license should be specified.
- [x] Basic documentation (e.g. a README.md file) has been written for the
      feature, and includes:
  - [x] A clear indication of its Community Certification Level.
  - [x] Description of covered use case.
  - [x] Supported versions of relevant components
        (eg tools that it integrates with, etc).
  - [x] Known limitations.

### :no_entry_sign: Trusted

Taking a feature from the Community certification level to the Trusted level
involves a development, documentation, and testing effort to meet the following
criteria:

- [ ] Feature implementation is largely complete
  - [ ] Majority of edge cases for the key feature use case have been
        implemented.
  - [ ] No known bugs of Critical or High severity exist.
- [x] Feature is available in a tagged version:
  - [x] For CyberArk-maintained software, GitHub tags will be used.
  - [ ] For non-CyberArk maintained software, versioned release artifacts will
        be uploaded to CyberArk Marketplace with the "Trusted" Certification
        Level.
- [ ] Feature has been fully documented and includes:
  - [x] Supported versions of relevant components
        (eg tools that it integrates with, etc).
  - [x] Known limitations.
  - [ ] Basic troubleshooting information.
  - [x] API documentation updates
        (if relevant, e.g. for updates to the Conjur API).
- [ ] Feature has comprehensive tests
  - [ ] Automated unit and integration test suite has been implemented for use
        case.
    - [x] All main positive tests exist.
    - [ ] Many negative tests exist.
    - [ ] Might be some edge cases remaining to test, but the covered edge cases
          should be tested.
- [ ] Feature passed a basic security review and follows security best practices
      (e.g. STRIDE, OWASP Top 10, GDPR).

In addition, if the feature is maintained by CyberArk, the following conditions
must be met:

- [x] Documentation is published on appropriate CyberArk documentation site(s)
- [ ] Feature is clearly labeled as Trusted Certification Level.
- [ ] Feature has automated vulnerability scanning integrated into its pipeline
      which runs with no Critical or High vulnerabilities.
- [ ] Project has an up-to-date acknowledgements file and all dependencies use
      approved licenses (MIT, Apache 2.0, BSD) or have been individually
      approved.

### :no_entry_sign: Certified

In order for a "Trusted" feature to become "Certified" for CyberArk Conjur Enterprise, the following additional criteria must be met:

- [ ] Feature implementation is complete when used with CyberArk Conjur
      Enterprise.
  - [ ] All identified edge cases have been implemented.
  - [ ] No known bugs of Critical or High severity exist.
- [ ] Feature includes automated tests to validate functional workflows with
      CyberArk Conjur Enterprise.
  - [ ] Feature has been load-tested at expected Enterprise production loads.
  - [ ] Performance goals for feature working with CyberArk Conjur Enterprise
        have been met and confirmed by testing/usage data.
  - [ ] Code coverage meets targets for Enterprise-level products.
- [ ] Feature documentation is complete.
  - [ ] Documentation for using the feature with CyberArk Conjur Enterprise
        exists on the appropriate documentation site(s), and includes:
    - [x] Supported versions of relevant components
          (eg tools that it integrates with, etc).
    - [x] Known limitations.
    - [ ] Comprehensive troubleshooting information.
    - [x] Updated API documentation
          (if relevant, e.g. for updates to the Conjur API).
- [ ] Feature passed a comprehensive security review, ensuring it complies with
      the CyberArk Conjur Enterprise security requirements.

---

## Review: Test Cases and Coverage

- `conjur_variable`
  - retrieve Conjur variable...
    - successfully...
      - standard
      - into file
      - from secret path including spaces
      - with authn token
      - after disabling certificate verification
    - unsuccessfully...
      - with bad certificate
      - with bad certificate path
      - with no certificate provided
      - with authn token & bad certificate
- `conjur_host_identity`
  - successfully configure Conjur identity

---

## Path to Trusted

For cyberark/ansible-conjur-collection to be upgraded to Trusted level, there
are additions that need to be made in three areas: documentation, testing, and
CI automation.

#### Documentation

The main achievement here would be thoroughly documenting an intended use-case
for the Collection. Establishing a development environment and using it as part
of a quick-start guide would go a long way to clearly demonstrate a
use-case, and document how developers can use the Collection themselves.

- [ ] Repurpose existing test environments into a local development environment,
      and add set-up details in CONTRIBUTING.md.
- [ ] Add quick-start environment and instructions.
- [ ] Document basic troubleshooting information - investigate common failure
      states and their resolutions.
- [ ] Feature is clearly labeled as Trusted Certification Level.

#### Testing

- [ ] Currently, the repo's test suite is almost exclusively end-to-end tests -
      the modules are tested against a live Conjur server, creating hosts or
      fetching secrets for a live deployment node.
  - [ ] The `lookup` module could be unit-tested.
    - [Ansible documentation on adding unit testing](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections_testing.html#adding-unit-tests)
    - [Example unit testing for `community.general` Ansible Collection](https://github.com/ansible-collections/community.general/tree/main/tests/unit)
  - [ ] The `conjur_host_identity` and `lookup` modules should probably be
        tested together - ensuring that a user can seamlessly use both services
        together.
- [ ] `conjur_host_identity` only has one test case, which asserts that a Conjur
      identity is successfully configured. This module should include some
      negative test cases, that confirm identity creation will fail under
      certain conditions.

#### CI Automation

- [ ] Implement vulnerability scanning in CI.
  - Not too sure about how to apply vulnerability scanning to Ansible
    Collections. There don't seem to be many tools for this particular use-case.
- [ ] Implement code coverage reporting in CI.
  - This can probably be addressed with tools that CyberArk uses across many
    repositories.

#### General

- [ ] `Role Variables` marked as `(Optional)` in the
      [`Conjur Ansible Role` section](https://github.com/cyberark/ansible-conjur-collection#role-variables)
      of README.md should be marked `(Required)` instead.
- [ ] Feature passed a basic security review and follows security best practice

## Path to Certified

Once the Collection is officially Trusted, upgrading to Certified requires that
the Collection be tested against Conjur Enterprise, and benchmarked to ensure
production-grade performance.

#### Testing

- [ ] Run existing tests against Conjur Enterprise in CI.
- [ ] Feature has been load-tested at expected Enterprise production loads, and
      feature performance are confirmed by testing/usage data.
  - This requirement will need a spike of its own, to identify which
    aspects of the collection could bottleneck performance, and at what loads.

#### General

- [ ] Feature passed a comprehensive security review, ensuring it complies with
      the CyberArk Conjur Enterprise security requirements.

## Other

- [ ] Improve visibility of failing cases.
  - [ ] Input validation would help the plugins fail fast & provide more
        representative error messages. For example, the below playbook should
        be set to fail before even attempting to retrieve a secret from Conjur,
        thanks to the empty string for Conjur variable path:

        ```
        ---
        - name: Retrieve Conjur variable
          hosts: localhost
          connection: local
          tasks:
            - name: Clean artifact path
              file:
                state: absent
                path: /conjur_secrets.txt

            - name: Retrieve Conjur variable
              vars:
                super_secret_key: "{{lookup('conjur_variable', '')}}"
              shell: echo "{{super_secret_key}}" > /conjur_secrets.txt
        ```

  - [ ] Unexpected errors are not handled well - error messages are generic and
        vague. For example, if the `lookup` function is not given a Conjur
        variable path, the error is not very helpful. The module should define
        custom error messages explaining why certain failures occur.

        ```
        fatal: [localhost]: FAILED! => {"msg": "An unhandled exception occurred while templating '{{lookup('conjur_variable')}}'. Error was a <class 'ansible.errors.AnsibleError'>, original message: An unhandled exception occurred while running the lookup plugin 'conjur_variable'. Error was a <class 'IndexError'>, original message: list index out of range"}
        ```
