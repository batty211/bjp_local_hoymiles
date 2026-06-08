# Changelog

All notable changes to BJP Local Hoymiles are documented here.

The project follows Semantic Versioning. For each GitHub release, copy the
matching version section into the GitHub Release description so HACS can show
the release notes to users.

## [0.1.1] - 2026-06-08

### Added

- Added a permanent release workflow requiring a version update, changelog
  entry, and proposed Git commit message for every project change.
- Documented how to publish GitHub Release notes for display in HACS.

### Changed

- Bumped the integration version to `0.1.1`.

## [0.1.0] - 2026-06-08

### Added

- Initial HACS-compatible Home Assistant custom integration.
- UI setup through Config Flow with configurable host, TCP port, and scan
  interval.
- Local polling of Hoymiles DTU-Pro-S through `hoymiles-wifi`.
- Sensors for the DTU, DDSU666 meter, inverters, and individual MPPT ports.
- Grid import/export and home load calculations.
- English and Thai translations.
- Read-only adapter, diagnostics redaction, parser tests, and safety tests.

### Security

- No control entities, custom services, or write-capable DTU operations.

[0.1.1]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bordin/bjp_local_hoymiles/releases/tag/v0.1.0
