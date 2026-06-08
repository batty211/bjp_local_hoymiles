# AGENTS.md

This file defines the working agreement for coding agents in this repository.

## Start Here

Before changing code:

1. Read `README.md`.
2. Read `docs/SPEC.md` for product scope and acceptance criteria.
3. Read `docs/ARCHITECTURE.md` for system boundaries and constraints.
4. Read relevant records in `docs/decisions/`.
5. Check the worktree and preserve unrelated user changes.

## Current State

The repository is in the initialization and requirements-discovery phase.
The implementation stack and Hoymiles integration protocol are not yet selected.
Do not silently turn assumptions into requirements.

## Working Rules

- Keep changes small, focused, and consistent with existing patterns.
- Prefer local-first behavior and graceful operation without internet access.
- Treat device communication as read-only until write operations are explicitly approved.
- Keep credentials, tokens, serial numbers, IP addresses, and site-specific data out of git.
- Validate all data received from devices or external processes.
- Use structured parsers for structured protocols and formats.
- Add or update tests when behavior changes.
- Update documentation when public behavior, setup, architecture, or operations change.
- Record significant technical decisions as ADRs in `docs/decisions/`.
- Mark unresolved matters as `TBD`; do not invent product requirements.

## Definition of Done

A change is complete when:

- The requested behavior is implemented.
- The version in `custom_components/bjp_local_hoymiles/manifest.json` is
  reviewed and updated using Semantic Versioning.
- `CHANGELOG.md` contains a dated entry for the resulting version.
- The final response includes a proposed Git commit summary and a short
  description, but the agent does not commit unless explicitly asked.
- Relevant tests pass.
- Formatting, linting, and type checks pass when those tools exist.
- Errors are actionable and do not expose secrets.
- Documentation and examples reflect the new behavior.
- No unrelated files or user changes are reverted.

## Expected Commands

These commands must be documented in `docs/DEVELOPMENT.md` after the stack is
selected:

- Install dependencies
- Start development mode
- Run tests
- Run lint and formatting checks
- Run type or static analysis
- Build a release artifact

## Architecture Guardrails

- Separate device adapters from domain logic.
- Keep storage behind an interface owned by the application layer.
- Do not couple the UI directly to a device protocol.
- Make timestamps timezone-aware and store canonical timestamps in UTC.
- Make polling idempotent and resilient to temporary device unavailability.
- Prefer migrations over manual database edits.
- Use explicit configuration with documented defaults.

## Commit Guidance

- Use imperative, descriptive commit messages.
- Always propose a one-line Git commit summary and a short description after
  making changes.
- Do not create a commit unless the user explicitly requests it.
- Keep generated files out of commits unless they are required artifacts.
- Never commit `.env` files, credentials, production data, or device identifiers.

## Version and Release Notes

- Use Semantic Versioning: patch for fixes/docs/internal improvements, minor for
  backward-compatible features, and major for breaking changes.
- Treat the version in `manifest.json` as the release version source of truth.
- Every project change must update the version and add the matching
  `CHANGELOG.md` section.
- Use a release heading in the form `## [X.Y.Z] - YYYY-MM-DD`.
- Copy the matching changelog section into the GitHub Release description.
  HACS displays release versions and release notes from published GitHub
  Releases; a tag by itself is not sufficient.
