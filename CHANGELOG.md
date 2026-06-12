# Changelog

All notable changes to BJP Local Hoymiles are documented here.

The project follows Semantic Versioning. For each GitHub release, copy the
matching version section into the GitHub Release description so HACS can show
the release notes to users.

## [0.3.10] - 2026-06-13

### Fixed

- Persisted inverter and MPPT lifetime cache values across restart and reload
  gaps so `lifetime_solar_energy`, `solar_self_consumed_energy`, and
  `home_consumption_energy` no longer drop to the grid-import baseline when the
  DTU reports transient zero lifetime totals.

### Changed

- Rebuilt inverter lifetime totals and cumulative derived energy after applying
  the persisted MPPT lifetime cache, keeping Energy Dashboard statistics
  aligned with the restored values.

## [0.3.9] - 2026-06-11

### Fixed

- Preserved inverter lifetime and MPPT lifetime values across transient zero
  snapshots in the live coordinator session so midnight polling gaps no longer
  create false resets in inverter-derived long-term statistics.

### Changed

- Recomputed inverter lifetime totals from restored MPPT values before
  publishing snapshots, keeping lifetime solar energy, solar self-consumed
  energy, and home consumption aligned through the transient gap.

## [0.3.8] - 2026-06-10

### Added

- Added a post-setup billing cycle wizard in the integration options flow that
  generates the exact `utility_meter` helper settings for `From Grid` and
  `To Grid` without auto-creating helpers.

### Changed

- Stored billing-cycle preferences in integration options so each Home
  Assistant installation can keep its own reset day, reset time, or advanced
  cron schedule.
- Documented why Utility Meter helpers stay user-managed after HACS install or
  update, plus how to map the wizard output into Home Assistant helper fields.

## [0.3.7] - 2026-06-10

### Fixed

- Corrected DDSU666 lifetime grid import/export normalization from a `1 Wh`
  assumption to the observed `10 Wh` raw unit, so cumulative meter energy now
  aligns with S-Miles Cloud totals and Utility Meter deltas.
- Migrated persisted meter lifetime cache values from the previous scale once,
  preventing a zero first poll after upgrade from restoring an incorrect total.

### Changed

- Recomputed solar self-consumption and total home consumption from the
  corrected meter lifetime values.
- Documented the one-time Home Assistant statistics and Utility Meter cleanup
  required when upgrading existing installations.

## [0.3.6] - 2026-06-09

### Fixed

- Preserved meter lifetime import/export values across restart and reload
  gaps by persisting the last non-zero reading per meter serial, preventing a
  transient first-poll `0.0` from leaking into Home Assistant cumulative
  statistics.

### Changed

- Recomputed meter-derived cumulative energy after restoring the persisted
  meter lifetime cache so solar self-consumed energy and home consumption stay
  aligned with the restored meter totals.

## [0.3.5] - 2026-06-09

### Fixed

- Preserved meter lifetime import/export values for the same meter serial when
  the DTU briefly reports `0.0` or `None`, preventing Home Assistant Energy
  Dashboard and Utility Meter statistics from seeing a false reset.

### Changed

- Recalculated derived cumulative energy after meter lifetime preservation so
  solar self-consumed energy and home consumption stay aligned with the
  restored meter totals.
- Refreshed the dashboard example to show realtime, daily, billing, yearly,
  meter status, summary, and selected-range graph sections aligned with the new
  meter and derived energy entities.

## [0.3.4] - 2026-06-09

### Fixed

- Preserved same-day daily energy values in a per-entry Home Assistant store
  so DTU, inverter, and MPPT daily energy sensors no longer fall back to `0`
  after HA restart, integration reload, or a temporary offline snapshot.

### Changed

- Restored daily energy from persistent cache when a snapshot for the same day
  reports `None` or `0`, while still resetting the cache when the local day
  changes.

## [0.3.3] - 2026-06-09

### Fixed

- Replaced the custom graph card in the dashboard example with core
  `statistics-graph` cards so the selected-day and selected-range views render
  against Home Assistant statistics without depending on an extra frontend
  plugin.

### Changed

- Kept the date picker, selected-period summary cards, and app-like layout, but
  simplified the graph layer to the native card that matches the data model
  used by this integration.

## [0.3.2] - 2026-06-09

### Added

- Upgraded the dashboard example to use the Energy date selection card plus a
  custom graph card so users can choose a day or time range and have the
  charts follow that selection.

### Changed

- Reworked the selected-period summary cards so the dashboard now reflects the
  active date range instead of only showing fixed live history.
- Documented the custom frontend resource required for the app-like graph
  experience.

## [0.3.1] - 2026-06-09

### Added

- Added an app-inspired Lovelace dashboard example under `docs/examples/`
  that organizes live solar power, home load, meter details, and 24-hour
  history graphs into a layout closer to the Hoymiles app.

### Changed

- Documented the dashboard example in the README and bumped the release version
  to match the new docs asset.

## [0.3.0] - 2026-06-09

### Added

- Added cumulative energy sensors for solar self-consumption and total home
  consumption so Home Assistant Energy Dashboard can show grid import, solar
  production, and source split without requiring manual helper entities.

### Changed

- Marked lifetime energy entities as `total` state class where appropriate so
  Home Assistant can treat long-term values as cumulative totals.
- Documented the recommended Energy Dashboard entity mapping in the README.

## [0.2.3] - 2026-06-08

### Fixed

- Preserve the latest non-zero daily solar energy values for the same local day
  when inverters sleep or report zero real-time daily energy, preventing daily
  energy sensors from dropping back to `0 kWh` before the next day.

## [0.2.2] - 2026-06-08

### Fixed

- Use the sum of MPPT daily energy when the DTU daily solar energy aggregate is
  missing or reported as zero, so the DTU-level daily solar energy sensor shows
  the day's accumulated production.

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

[0.3.8]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.7...v0.3.8
[0.3.9]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.8...v0.3.9
[0.3.7]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.5...v0.3.6
[0.3.3]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.2...v0.3.3
[0.3.5]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.3...v0.3.4
[0.3.2]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/bordin/bjp_local_hoymiles/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bordin/bjp_local_hoymiles/releases/tag/v0.1.0
