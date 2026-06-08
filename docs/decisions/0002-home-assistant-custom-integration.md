# ADR-0002: Home Assistant Custom Integration via HACS

- Status: Accepted
- Date: 2026-06-08
- Owners: Project maintainers

## Context

The target workflow is Home Assistant. Users should install the integration
through HACS, add a DTU from the Home Assistant UI, and use standard Home
Assistant history, dashboard, automation, Utility Meter and Integration Sensor
features.

## Decision

The project will be a Home Assistant custom integration with domain
`bjp_local_hoymiles`, installed through HACS.

The integration will use `hoymiles-wifi==0.5.6` for local TCP communication and
will expose only read-only adapter methods to the Home Assistant layer.

## Alternatives Considered

- Standalone dashboard: rejected because Home Assistant already provides
  dashboards, automation, recorder and energy tooling.
- Forking `ha-hoymiles-wifi`: rejected because its public surface includes
  controls that conflict with the read-only requirement.

## Consequences

- Home Assistant handles history and derived energy calculations.
- HACS repository structure and Home Assistant manifest requirements must be
  maintained.
- Config Flow and translation files are required for a polished UI setup.
- Runtime behavior remains local-only after installation.

## Validation

- Config Flow can add a DTU using host, port and scan interval.
- Sensor entities are created for DTU, meter, inverter and MPPT data.
- Safety tests reject write-capable platforms and forbidden DTU method calls.
