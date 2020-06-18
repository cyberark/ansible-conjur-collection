# Contributing to the Ansible Conjur Collection

Thanks for your interest in the Ansible Conjur collection.

## Pull Request Workflow

Currently, this repository is source-available and not open to contributions.  Please continue to follow this repository for updates and open-source availability

## Releasing

To release a new version of this plugin:

- Make the appropriate changes
- Update the version number in [`galaxy.yml`](galaxy.yml) and [`CHANGELOG.md`](CHANGELOG.md)
- Tag the git history with `v##.##.##` version
- Create the release on GitHub for that tag
- Build the release package with `ansible-galaxy collection build`
- Upload that package to:
  - GitHub release
  - https://galaxy.ansible.com/cyberark/conjur
