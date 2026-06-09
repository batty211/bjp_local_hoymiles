# Architecture

## Status

Implemented baseline for a Home Assistant custom integration.

## Context

```text
Hoymiles DTU-Pro-S
           |
           | TCP 10081 via hoymiles-wifi
           v
    Read-only Adapter
           |
           v
 DataUpdateCoordinator -----> Diagnostics
           |
           v
      Sensor Entities
            |
            v
 Home Assistant Recorder / Energy Dashboard
```

S-Miles Cloud is not used for runtime data collection.

## Logical Components

### Device Adapter

- Encapsulates `hoymiles-wifi`.
- Converts vendor payloads into canonical domain records.
- Applies timeouts, bounded retries, and payload validation.
- Exposes only read-only methods to the Home Assistant integration layer.

### DataUpdateCoordinator

- Polls at the configured scan interval.
- Defaults to 35 seconds and rejects values below 35 seconds.
- Continues running through temporary device and network failures.
- Persists same-day daily energy cache per config entry so a restart or reload
  does not collapse daily energy sensors back to zero when the DTU reports a
  temporary zero snapshot.

### Application

- Applies domain rules and unit normalization.
- Provides latest status and historical queries.
- Does not depend on transport-specific device payloads.

### Home Assistant Sensors

- Shows current production, daily energy, lifetime energy, grid power, load,
  device state, and last update.
- Exposes cumulative grid import, grid export, solar production, solar
  self-consumption, and total home consumption sensors for Energy Dashboard
  selection.
- Distinguishes zero production from missing or stale data.
- Uses explicit units and local timezone.

## Canonical Data Model

The exact schema is `TBD`, but the domain should distinguish:

| Entity | Minimum fields |
| --- | --- |
| DTU | serial, timestamp, power, daily energy, lifetime solar energy |
| Meter | serial, net/import/export power, voltage, current, PF, energy totals |
| Inverter | serial, power, voltage, current, PF, temperature, status, energy totals |
| MPPT | inverter serial, port number, power, voltage, current, energy totals |

Vendor-specific fields should be retained only when they have a defined use.

## Data Flow

1. Collector requests or receives data through a device adapter.
2. Adapter validates and maps the payload into canonical records.
3. Application normalizes units and determines freshness/status.
4. Sensor entities expose native Home Assistant values.
5. Recorder, Utility Meter and Integration Sensor provide history and derived totals.

## Failure Handling

- Network timeout: record the attempt, apply bounded retry/backoff, keep serving old data as stale.
- Invalid payload: reject or quarantine it; do not silently store misleading values.
- Home Assistant Recorder unavailable: live sensors continue to update, history is handled by Home Assistant.
- Clock issue: preserve received time and mark questionable observed timestamps.
- Restart: resume collection without requiring manual cleanup.
- Temporary zero daily-energy snapshots must not overwrite same-day cached
  values once the integration has seen a valid non-zero reading for that day.

## Security Boundaries

- Bind to loopback or the private LAN by default.
- No credentials are required for the tested local TCP API.
- Treat device responses as untrusted input.
- Avoid logging credentials, full authorization headers, and site identifiers.
- Diagnostics redact IP addresses and serial numbers.

## Configuration

Configuration should be explicit, validated at startup, and separate from code.
Expected categories:

- host and port
- polling interval and timeouts
- Home Assistant options flow stores scan interval

## Deployment

Deployment target is Home Assistant with installation via HACS.

## Testing Strategy

- Unit tests for payload mapping, unit conversion, grid sign and home load
- Contract tests using sanitized device payload fixtures
- Config Flow tests for success, connection failure, invalid payload and duplicates
- Safety tests ensuring no write-capable platform/service or DTU write call is present
- Diagnostics tests ensuring IP and serial redaction

## Architecture Constraints

- Home Assistant modules must use the read-only adapter instead of importing DTU directly.
- Device failure must not make historical data unavailable.
- Internet access must not be required for the main workflow.
- All timestamps must have defined timezone semantics.
- A significant change to boundaries, storage, protocol, or deployment requires an ADR.
