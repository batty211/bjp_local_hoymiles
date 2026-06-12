# ADR-0008: Persist Inverter and MPPT Lifetime Cache Across Restarts

- Status: Accepted
- Date: 2026-06-13
- Owners: Project maintainers

## Context

`home_consumption_energy` depends on `solar_self_consumed_energy`, which in turn
depends on inverter and MPPT lifetime totals. The live-session preservation
added in ADR-0007 protects against transient zero snapshots only when the
coordinator already has a previous non-zero snapshot in memory.

In practice, the DTU can still return `0` for MPPT lifetime totals after Home
Assistant restart, integration reload, or several consecutive bad polls. When
that happens before a good in-memory snapshot exists, the derived cumulative
energy sensors can drop to the grid-import baseline until the DTU recovers.

## Decision

The integration will persist the last known non-zero MPPT lifetime totals per
config entry and per inverter/port combination.

When a collected snapshot reports `0` or `None` for MPPT lifetime energy, the
integration will restore the cached non-zero values before rebuilding inverter
lifetime totals and the cumulative derived energy sensors.

## Alternatives Considered

- Keep only live-session preservation: rejected because restart/reload gaps can
  still leak false resets into cumulative sensors.
- Persist only inverter aggregate totals: rejected because MPPT totals are the
  canonical inputs already used to rebuild inverter lifetime energy.

## Consequences

- Inverter lifetime, solar self-consumed energy, and home consumption energy
  stay monotonic across restart/reload gaps and consecutive zero snapshots.
- The cache remains local to the Home Assistant config entry and stays
  read-only with respect to the DTU.

## Validation

- Confirm a restart followed by zero MPPT lifetime snapshots restores the last
  positive cached values.
- Confirm restored MPPT values rebuild inverter lifetime totals and cumulative
  derived energy consistently.
- Confirm newer positive MPPT values replace the cached values.
