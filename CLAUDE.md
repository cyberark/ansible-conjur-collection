# CLAUDE.md

## Overview

This is the **`cyberark.conjur` Ansible Collection** (published to Ansible Galaxy),
the official Ansible integration for **CyberArk Conjur Open Source** and **CyberArk
Secrets Manager, Self-Hosted** (formerly Conjur Enterprise). It lets Ansible
playbooks retrieve secrets from Conjur/Secrets Manager and lets managed nodes be
provisioned with a Conjur machine identity. It provides two main components:

- A **lookup plugin** (`conjur_variable`) that fetches secrets at playbook-run time
  using API Key, AWS IAM, Azure Managed Identity, GCP, JWT/OIDC, or certificate
  authentication.
- A **role** (`conjur_host_identity`) that enrolls a host with a Conjur identity
  (via Host Factory) and installs [Summon](https://github.com/cyberark/summon) +
  the `summon-conjur` provider for secret injection into processes.

This repo is a **Certified** CyberArk project (see README "Certification Level").

## Tech stack

- Ansible Collection layout (`galaxy.yml`, `plugins/`, `roles/`), namespace
  `cyberark`, name `conjur`.
- Language: Python (lookup plugin) + YAML (role tasks/templates).
- Requires `ansible-core >= 2.17`; Python dependency: `PyYAML` (`requirements.txt`).
- Linting: `pylint` (see `pylintrc`, max line length 140) and `ansible-lint`.
- Dev/test tooling is Docker- and Docker Compose-based (`dev/`, `ci/`, `tests/`).
- CI defined in `Jenkinsfile` (CyberArk internal Jenkins pipeline) plus GitHub
  workflows under `.github/`.

## Install

```sh
ansible-galaxy collection install cyberark.conjur
```

To build a release artifact from source, see `ci/build_release`.

## Testing / Linting

All test scripts use Docker, so a working Docker/Docker Compose install is required.

- **Unit tests** (lookup plugin only):
  ```sh
  ./dev/test_unit.sh            # -a <ansible ver> -p <python ver> -r (coverage)
  ```
  Runs `ansible-test units` inside a container built from `tests/unit/Dockerfile`.
  Test source: `tests/unit/plugins/lookup/test_conjur_variable.py`.

- **Sanity tests**:
  ```sh
  ./dev/test_sanity.sh          # -a <ansible ver> -p <python ver> -r (coverage)
  ```
  Runs `ansible-test sanity`; per-version ignore files live in `tests/sanity/`.

- **Integration tests** (lookup plugin + role, against live Conjur/Ansible containers):
  ```sh
  ./ci/test.sh -a                     # run everything
  ./ci/test.sh -d <role_or_plugin>    # run tests for one component
  ./ci/test.sh -e -a                  # run against Secrets Manager, Self-Hosted (Enterprise)
  ```
  Integration test cases live under `tests/conjur_variable/test_cases/` (per auth
  method: `api_key`, `azure`, `gcp`, `iam`, `authn_cert`, `jwt-oidc`) and
  `roles/conjur_host_identity/tests/test_cases/`.

- **Lint**:
  ```sh
  ./dev/lint.sh   # runs ansible-lint and pylint (on plugins/lookup) via Docker
  ```

- **Full local dev environment** (Conjur OSS + Ansible control node + managed
  nodes via `dev/docker-compose.yml`):
  ```sh
  echo <major>.<minor>.<patch> > VERSION   # e.g. from latest CHANGELOG.md entry
  cd dev && ./start.sh   # ./stop.sh to tear down
  ```

## Repo structure

- `plugins/lookup/conjur_variable.py` — the lookup plugin implementation (the core
  Python code in this repo).
- `roles/conjur_host_identity/` — the identity/Summon-install role: `tasks/`,
  `templates/` (conjur.conf, identity files), `defaults/main.yml` (role variables),
  own `tests/`.
- `tests/unit/` — pytest-based unit tests + Dockerfile for the lookup plugin.
- `tests/sanity/` — `ansible-test sanity` Dockerfile and per-Ansible-version ignore
  lists.
- `tests/conjur_variable/` — integration test cases per authentication method.
- `dev/` — local development environment (docker-compose, policies, test apps,
  helper scripts); excluded from the published collection artifact.
- `ci/` — build/release/publish/test scripts used by the Jenkins pipeline;
  excluded from the published artifact.
- `examples/test.yml` — example playbook.
- `galaxy.yml` — collection metadata/version; `build_ignore` lists paths (e.g.
  `dev`, `ci`, `secrets.yml`, `Jenkinsfile`) excluded when building the artifact.
- `CHANGELOG.md` — must be updated (with the version bumped in `galaxy.yml`) as
  part of any release; the release pipeline derives the artifact version from it.

## Conventions / gotchas

- Collection FQCN is `cyberark.conjur`; role/plugin usage in playbooks is
  `cyberark.conjur.conjur_host_identity` / `lookup('cyberark.conjur.conjur_variable', ...)`.
  Preserve this namespace when referencing the plugin/role in docs or examples.
- The lookup plugin's `DOCUMENTATION`/`options` block in `conjur_variable.py` is the
  source of truth for supported environment variables (`CONJUR_*`) and extra-vars
  (`conjur_*`) — keep it in sync with any behavior changes.
- Do not URL-encode secret paths passed to the lookup plugin; it handles encoding
  internally (documented directly in the plugin's docstring).
- `pylintrc` disables several checks (e.g. `missing-function-docstring`,
  `missing-class-docstring`); don't assume standard pylint defaults apply.
- `secrets.yml` in the repo root is a real filename used by the project (likely
  Ansible Vault/test fixtures) — treat it as sensitive-looking but check contents
  before assuming it holds live secrets; it is excluded from the build artifact.
- Releases are triggered by merging to `main`/`master` via the Jenkins pipeline
  (`Jenkinsfile`); do not manually publish to Galaxy — see `CONTRIBUTING.md`
  "Releasing" section.
- Contributions require a signed CyberArk Contributor Agreement (see
  `CONTRIBUTING.md`).
