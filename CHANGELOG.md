# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- Encode spaces to "%20" instead of "+". This encoding fixes an issue where Conjur
  variables that have spaces were not encoded correctly 
  ([cyberark/ansible-conjur-collection#12](https://github.com/cyberark/ansible-conjur-collection/issues/12))
- Allow users to set `validate_certs` to `false` without setting a value to `cert_file`
  ([https://github.com/cyberark/ansible-conjur-collection#13](https://github.com/cyberark/ansible-conjur-collection/issues/13))

## [1.0.3] - 2020-04-18
### Changed
- Updated documentation section to comply with sanity checks

## [1.0.2] - 2020-04-01
### Added
- Migrated code from Ansible conjur_variable lookup plugin
- Added support to configure the use of the plugin via environment variables
