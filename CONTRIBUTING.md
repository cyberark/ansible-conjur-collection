# Contributing to the Ansible Conjur Collection

Thanks for your interest in the Ansible Conjur collection.

## Pull Request Workflow

Currently, this repository is source-available and not open to contributions.  
Please continue to follow this repository for updates and open-source availability

## Releasing

From a clean instance of master, perform the following actions to release a new version 
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
