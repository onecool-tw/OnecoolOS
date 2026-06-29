# Coding Standard

Onecool OS follows Python best practices and PEP8. The codebase should remain
small, explicit, and easy to extend through plugins.

## Python

- Use Python 3.11 or newer.
- Prefer standard-library functionality unless a dependency is justified.
- Keep functions and classes focused.
- Use type hints for public interfaces and core boundaries.
- Keep line lengths within PEP8-friendly limits.

## Architecture

- Do not redesign the architecture unless explicitly instructed.
- Follow the existing repository structure.
- Keep infrastructure independent from business modules.
- Keep business logic inside modules.
- Prefer composition over inheritance.
- Keep modules loosely coupled.
- Do not break backward compatibility unless requested.

## Plugins

- Plugins must expose `create_plugin`.
- Plugins must provide a `PluginManifest`.
- Plugins should register services through `PluginContext.services`.
- Plugins should publish lifecycle or domain events through
  `PluginContext.events`.
- Plugins should clean up registered resources during `deactivate`.

## Persistence

- Use SQLite for local persistence.
- Add schema changes through migration files in `migrations/`.
- Keep migrations idempotent where practical.
- Do not embed business workflows in migration code.

## Tests

- Every milestone must include tests.
- Run the full test suite before finishing a milestone.
- Add focused tests for lifecycle, persistence, and plugin behavior when those
  areas change.

## Documentation

- Update README when behavior changes.
- Add architecture notes to `docs/architecture.md`.
- Record durable architecture decisions in `docs/decision-records/`.
- Keep documentation aligned with executable behavior.

## Commits

Use Conventional Commits.

Examples:

- `feat(core): add plugin loading`
- `fix(core): clean service registry on shutdown`
- `docs: initialize project documentation`
- `test(core): cover engine restart`
