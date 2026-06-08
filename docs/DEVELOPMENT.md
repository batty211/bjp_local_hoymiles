# Development Guide

## Current Phase

The project is a Home Assistant custom integration installed through HACS.

## Prerequisites

- Git
- Python 3.12 or the Python version used by the target Home Assistant release
- `pytest` for unit tests
- Home Assistant test dependencies for full config-flow/platform tests
- A Hoymiles DTU-Pro-S on the local network for live validation

## Commands

| Task | Command |
| --- | --- |
| Install runtime dependency | Managed by Home Assistant from `manifest.json` |
| Run parser and safety tests | `python3 -m pytest -q` |
| Run syntax check | `python3 -m compileall -q custom_components tests` |
| Run lint checks | `python3 -m ruff check .` |
| Run type/static checks | `python3 -m mypy custom_components/bjp_local_hoymiles` |
| Build release | Tag a GitHub release for HACS users |

Do not merge implementation work while its required command remains undocumented.

## Recommended Workflow

1. Select one user story or acceptance criterion.
2. Confirm its inputs, outputs, failure behavior, and test approach.
3. Add fixtures using synthetic or sanitized DTU payload data.
4. Implement the smallest complete vertical behavior.
5. Run relevant automated checks.
6. Update spec, architecture, operations, and ADRs when affected.

## Local Configuration

- Keep real IP addresses and serial numbers out of committed fixtures.
- Do not add YAML setup; setup must remain UI based through Config Flow.
- Document each setting, default, valid range, and whether reload is required.

## Test Data

Test fixtures should cover:

- normal daytime production
- valid zero production
- missing meter, inverter or MPPT blocks
- device timeout and reconnect
- malformed and unexpected payloads
- duplicate timestamps
- counter reset or device restart
- grid import and grid export sign behavior
- timezone behavior for DTU timestamps

## Pull Request Checklist

- Scope and acceptance criterion are identified.
- `manifest.json` has an appropriate Semantic Versioning update.
- `CHANGELOG.md` has a matching dated release entry.
- A Git commit summary and short description are prepared, without committing
  unless explicitly requested.
- Tests cover normal and important failure paths.
- No secret, IP address or real serial number is included.
- Setup and operator-facing changes are documented.
- Architecture changes include an ADR.
- Logs and diagnostics redact sensitive values.
- No write-capable platform, service or DTU command is added.

## Release and Operations

Before a HACS release:

- confirm `manifest.json` and `CHANGELOG.md` use the same version
- create a tag using `vX.Y.Z`
- publish a full GitHub Release, not only a tag
- copy the matching `CHANGELOG.md` section into the release description so
  HACS can display it
- verify HACS can install from `custom_components/bjp_local_hoymiles`
- test Config Flow against a real DTU
- test Home Assistant restart, unload and reload
- review diagnostics for redaction
