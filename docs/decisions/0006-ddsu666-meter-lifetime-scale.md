# ADR-0006: Normalize DDSU666 Lifetime Energy as 10 Wh Units

- Status: Accepted
- Date: 2026-06-10
- Owners: Project maintainers

## Context

The local `RealDataNew` payload exposes DDSU666 cumulative grid energy as
`energyTotalConsumed` and `energyTotalPower`. The upstream protobuf comments
describe these values as watt-hours, so the initial parser divided them by
`1000` to publish kWh.

Live comparison showed that this scale was incorrect for the supported
DDSU666 setup:

- raw import near `1,878,897` corresponds to approximately `18.79 MWh`
- raw export near `536,840` corresponds to approximately `5.37 MWh`
- S-Miles Cloud reported approximately `18.59 MWh` imported and `5.37 MWh`
  exported
- a raw increase of `164` during an hour corresponds to `1.64 kWh`, consistent
  with the observed grid power, rather than `0.164 kWh`

The upstream project also records that these fields represent energy imported
from and exported to the grid, but its unit comments were not validated against
this meter model.

## Decision

The integration will interpret DDSU666 `energyTotalConsumed` and
`energyTotalPower` as counters with `10 Wh` per raw unit and divide them by
`100` when publishing kWh.

This decision applies only to meter lifetime import/export values. DTU daily
energy and inverter/MPPT daily and lifetime energy remain divided by `1000`.

Persisted meter lifetime cache values written before this decision will be
migrated once by multiplying them by `10`. The cache serialization includes a
format version so migrated values are not multiplied again.

## Alternatives Considered

- Keep the `1 Wh` interpretation from the protobuf comments: rejected because
  both import and export totals are approximately ten times too small.
- Use S-Miles Cloud as the runtime source of truth: rejected because it would
  break the local-first and offline runtime requirements.
- Create new corrected entity IDs: rejected because existing Energy Dashboard
  configuration can be preserved with a documented one-time statistics cleanup.

## Consequences

- Meter lifetime import/export, solar self-consumption, and home consumption
  totals increase to the corrected scale while entity IDs remain unchanged.
- Existing Home Assistant long-term statistics may record the scale correction
  as a large one-time increase and require manual correction.
- Existing Utility Meter helpers must be reset or calibrated after upgrade and
  must treat the lifetime source as an absolute cumulative value.

## Validation

- Confirm raw import and export totals divided by `100` remain close to the
  corresponding S-Miles Cloud totals.
- Confirm a raw meter delta of `164` produces a `1.64 kWh` sensor delta.
- Confirm legacy cache values are multiplied by `10` exactly once.
- Confirm DTU, inverter, and MPPT energy scaling remains unchanged.

## References

- `hoymiles-wifi` meter field discussion:
  https://github.com/suaveolent/hoymiles-wifi/issues/46
- `hoymiles-wifi` unit conversion discussion:
  https://github.com/suaveolent/hoymiles-wifi/issues/41
- Hoymiles Cloud Home Assistant integration:
  https://github.com/Philra94/homeassistant-hoymiles-cloud
