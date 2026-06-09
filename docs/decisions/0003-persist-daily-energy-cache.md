# ADR-0003: Persist Same-Day Daily Energy Cache in Home Assistant Storage

- Status: Accepted
- Date: 2026-06-09
- Owners: Project maintainers

## Context

Daily energy sensors can temporarily report `0` or `None` when the DTU or an
inverter is offline, sleeping, or the integration restarts before the first
fresh non-zero snapshot arrives. If the integration only preserves values from
the previous in-memory coordinator snapshot, a Home Assistant restart or
integration reload can cause today’s visible daily energy to collapse back to
zero.

## Decision

The integration will persist same-day daily energy values in Home Assistant
`Store` storage on a per-config-entry basis.

The cache will keep the last non-zero daily energy observed for the current
local day for:

- DTU daily solar energy
- inverter daily energy by serial
- MPPT daily energy by inverter serial and port number

When a new snapshot for the same local day reports `None` or `0`, the
integration will restore the cached non-zero value. When the local day changes,
the cache will reset and begin collecting values for the new day.

## Alternatives Considered

- Keep only the previous coordinator snapshot in memory: rejected because the
  value is lost on HA restart or reload.
- Use long-term statistics as the source of truth for daily energy: rejected
  because the DTU already reports daily values directly and the requirement is
  to preserve the same-day live sensor state, not rebuild it from history.

## Consequences

- Daily energy sensors become resilient to restart/reload and temporary zero
  snapshots without changing entity IDs.
- Storage is local to Home Assistant and scoped to the config entry.
- The integration must load and save storage as part of coordinator setup and
  refresh.

## Validation

- Restart Home Assistant after a valid non-zero daily reading and confirm the
  same-day sensor does not fall back to zero.
- Reload the config entry after a valid non-zero daily reading and confirm the
  cached value is restored.
- Cross midnight and confirm the cache resets to the new local day.
