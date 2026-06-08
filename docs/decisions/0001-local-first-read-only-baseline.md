# ADR-0001: Local-First and Read-Only Baseline

- Status: Accepted
- Date: 2026-06-08
- Owners: Project maintainers

## Context

The project is intended to provide dependable visibility into a local Hoymiles
installation. Cloud availability and device write operations introduce failure
and safety risks that are not needed to validate the initial product.

## Decision

Core data collection, storage, and viewing will work inside the local network
without requiring internet access.

Initial device integration will be read-only. Any operation that changes device
state or configuration requires a separate specification, safety review, and ADR.

## Alternatives Considered

- Cloud-first integration: rejected as a core dependency because it conflicts
  with offline operation and local data ownership.
- Read/write integration from the first release: deferred because control
  operations have a larger safety and authorization surface.

## Consequences

- The selected protocol must provide local access or support a local gateway.
- Cloud integrations may be added only as optional adapters.
- The adapter interface should not expose write operations during the MVP.
- Product copy must not imply that the system is an electrical safety controller.

## Validation

- Complete the MVP workflow with internet access disabled.
- Confirm that no device state-changing request is sent during integration tests.
