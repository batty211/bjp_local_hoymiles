# ADR-0004: Preserve Meter Lifetime Energy Across Transient Zero Snapshots

- Status: Accepted
- Date: 2026-06-09
- Owners: Project maintainers

## Context

Hoymiles meter lifetime import/export values can briefly return `0.0` during
temporary read failures, while the meter serial number remains stable. If the
integration forwards that transient zero directly into Home Assistant, Energy
Dashboard statistics and Utility Meter helpers can see an artificial reset.

## Decision

The integration will preserve the last known non-zero meter lifetime import
and export values for the same meter serial during a live coordinator session.

When a new snapshot reports `None` or `0.0` for a meter lifetime total, the
integration will restore the previous non-zero value for that serial if one is
available. The integration will not preserve values across different meter
serial numbers.

Derived cumulative energy values that depend on meter lifetime import/export
will be recalculated after the preservation step.

## Alternatives Considered

- Forward raw meter lifetime zeros unchanged: rejected because it creates false
  resets in Home Assistant cumulative statistics.
- Add persistent storage for meter lifetime totals: deferred because the live
  snapshot already carries the correct value once the DTU responds again, and
  the current problem is transient during polling.

## Consequences

- Meter lifetime sensors become resilient to brief zero snapshots within the
  same coordinator session.
- The fix remains local and read-only, matching the existing integration
  boundary.
- First snapshot after a restart can still be zero if no previous non-zero
  value is available yet.

## Validation

- Confirm that a transient `0.0` on the same meter serial is replaced by the
  last valid non-zero value.
- Confirm that a new non-zero reading replaces the preserved value.
- Confirm that a different meter serial is not affected by another meter's
  cached value.
