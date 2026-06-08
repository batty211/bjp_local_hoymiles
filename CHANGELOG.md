# Changelog

All notable changes to BJP Local Hoymiles are documented here.

The project follows Semantic Versioning. For each GitHub release, copy the
matching version section into the GitHub Release description so HACS can show
the release notes to users.

## [0.2.1] - 2026-06-08

### Added

- Added a reproducible Miniconda environment with Python 3.12,
  `hoymiles-wifi`, pytest, Ruff, and mypy.
- Documented Miniconda commands for lightweight checks, fixture tests, and
  direct live DTU monitoring.

### Verified

- Completed a read-only live test against a DTU-Pro-S on TCP port `10081`.
- Confirmed meter, two inverter, and eight MPPT records are normalized and
  displayed without running Home Assistant.

## [0.2.0] - 2026-06-08

### Added

- Added a standalone read-only DTU terminal monitor for testing normalized
  sensor values without running Home Assistant.
- Added fixture and live DTU modes, JSON output, and a 35-second watch mode.
- Added a lightweight check runner that does not require pytest or Home
  Assistant dependencies.

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

[0.2.1]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bordin/bjp_local_hoymiles/releases/tag/v0.1.0
