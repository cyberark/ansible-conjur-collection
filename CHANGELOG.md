# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.7] - 2020-08-20

### Changed
- Various improvements to code quality, documentation, and adherence to Ansible standards
  in preparation for the release of Ansible 2.10.
  [cyberark/ansible-conjur-collection#30](https://github.com/cyberark/ansible-conjur-collection/issues/30)

## [1.0.6] - 2020-07-01

### Added
- Plugin supports authenticating with Conjur access token (for example, if provided by authn-k8s).
  [cyberark/ansible-conjur-collection#23](https://github.com/cyberark/ansible-conjur-collection/issues/23)

## [1.0.5] - 2020-06-18

### Added
- Plugin supports validation of self-signed certificates provided in `CONJUR_CERT_FILE`
  or Conjur config file
  ([cyberark/ansible-conjur-collection#4](https://github.com/cyberark/ansible-conjur-collection/issues/4))

### Fixed
- Encode spaces to "%20" instead of "+". This encoding fixes an issue where Conjur
  variables that have spaces were not encoded correctly 
  ([cyberark/ansible-conjur-collection#12](https://github.com/cyberark/ansible-conjur-collection/issues/12))
- Allow users to set `validate_certs` to `false` without setting a value to `cert_file`
  ([cyberark/ansible-conjur-collection#13](https://github.com/cyberark/ansible-conjur-collection/issues/13))

## [1.0.3] - 2020-04-18
### Changed
- Updated documentation section to comply with sanity checks

## [1.0.2] - 2020-04-01
### Added
- Migrated code from Ansible conjur_variable lookup plugin
- Added support to configure the use of the plugin via environment variables

[Unreleased]: https://github.com/cyberark/ansible-conjur-collection/compare/v1.0.7...HEAD
[1.0.7]: https://github.com/cyberark/ansible-conjur-collection/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/cyberark/ansible-conjur-collection/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/cyberark/ansible-conjur-collection/compare/v1.0.3...v1.0.5
[1.0.3]: https://github.com/cyberark/ansible-conjur-collection/compare/v1.0.2...v1.0.3
