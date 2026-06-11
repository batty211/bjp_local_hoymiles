# ADR-0007: Preserve Inverter and MPPT Lifetime Values Across Live Zero Snapshots

- Status: Accepted
- Date: 2026-06-11
- Owners: Project maintainers

## Context

Inverter lifetime energy is derived from the MPPT lifetime totals reported by
the DTU. In practice, the live snapshot can briefly report `0` or `None` for
those values around polling gaps or day-boundary transitions, which causes the
published inverter lifetime totals and their derived cumulative values to
appear to reset.

This behavior is distinct from the persisted meter lifetime cache problem:
inverter lifetime totals do not need restart persistence for the current fix,
but they do need to remain stable within the live coordinator session.

## Decision

The integration will preserve the last known non-zero MPPT lifetime values and
recompute inverter lifetime totals from the restored MPPT values before
publishing the snapshot.

If a current snapshot reports `0` or `None` for a live-session inverter or
MPPT lifetime value, the coordinator will restore the previous non-zero value
from the immediately prior snapshot when available.

## Alternatives Considered

- Leave inverter and MPPT lifetime values unchanged: rejected because the
  zero snapshot would still leak into Home Assistant statistics.
- Add persistent restart cache for inverter and MPPT lifetime totals:
  rejected for the current fix because the observed problem is a live polling
  anomaly rather than a restart gap.
- Rebuild the values from history: rejected because the integration is
  intentionally local-first and should not depend on recorder history at
  runtime.

## Consequences

- Inverter lifetime energy stays monotonic across transient zero snapshots in
  the live coordinator session.
- Derived cumulative values that depend on inverter lifetime data remain
  aligned after restoration.
- The behavior remains read-only and local-first.

## Validation

- Confirm a transient zero snapshot for MPPT lifetime energy restores the
  previous non-zero values.
- Confirm inverter lifetime totals are recomputed from the restored MPPT
  values.
- Confirm derived cumulative sensors do not publish a false reset when the
  zero snapshot occurs near midnight.
