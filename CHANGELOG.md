# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## Unreleased
### Fixed
- Encode spaces to "%20" instead of "+". This encoding fixes an issue where Conjur
  variables that have spaces were not encoded correctly 
  ([cyberark/ansible-conjur-collection#5](https://github.com/cyberark/ansible-conjur-collection/pull/5))

## v1.0.3
### Changed
- Updated documentation section to comply with sanity checks

## v1.0.2
### Added
- Migrated code from Ansible conjur_variable lookup plugin
- Added support to configure the use of the plugin via environment variables
