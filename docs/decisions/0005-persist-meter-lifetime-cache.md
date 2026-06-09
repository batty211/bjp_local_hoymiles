# ADR-0005: Persist Meter Lifetime Energy Cache Across Restarts

- Status: Accepted
- Date: 2026-06-09
- Owners: Project maintainers

## Context

Hoymiles meter lifetime import/export values are cumulative totals that should
stay monotonic for Energy Dashboard and long-term statistics. In practice, the
DTU can briefly return `0.0` on the first successful poll after integration
reload or restart, before the next good reading arrives.

The existing in-memory preservation logic protects only against transient zero
snapshots within the same coordinator session. That leaves a gap at startup
because no previous snapshot exists yet.

## Decision

The integration will persist the last known non-zero meter lifetime import and
export values per config entry and meter serial.

When a newly collected snapshot reports `None` or `0.0` for a meter lifetime
total, the integration will restore the cached non-zero value if one exists for
that meter serial. The cached value remains local to the config entry and is
updated whenever a newer positive reading arrives.

Derived cumulative values that depend on meter lifetime import/export will be
recomputed after restoration so the published snapshot stays internally
consistent.

## Alternatives Considered

- Keep only in-memory preservation: rejected because it still allows a zero
  value to leak through on the first poll after restart.
- Persist the entire raw snapshot history: rejected because the issue is only
  about a small set of cumulative totals and the rest of the snapshot remains
  read-only telemetry.

## Consequences

- Meter lifetime totals survive restart and reload gaps when the DTU briefly
  reports zero.
- The integration stays read-only and local-first.
- If the cache has never seen a positive value for a meter serial, the first
  snapshot for that serial can still be zero.

## Validation

- Confirm that a restart followed by a zero meter lifetime snapshot restores
  the last positive cached value.
- Confirm that a newer positive reading replaces the cached value.
- Confirm that cache entries stay isolated by config entry and meter serial.
