# Roadmap

This roadmap keeps Onecool OS incremental and executable at every milestone.
Milestone dates are intentionally not fixed until release planning is complete.

## Milestone 1: Core Engine

Status: Complete

Delivered:

- Python project structure
- SQLite migrations and schema
- Core Engine lifecycle
- Plugin Architecture
- Event Bus
- Service Registry
- CLI entry points
- Tests and README

## Milestone 1.5: Project Documentation

Status: Complete

Delivered:

- Architecture documentation
- Roadmap
- Coding standard
- Architecture Decision Record for Core Engine choices
- Changelog
- Contributing workflow

## Milestone 2: Module Foundation

Planned scope:

- Define module packaging conventions.
- Add module-level configuration boundaries.
- Add fixtures or factories for module tests.
- Keep infrastructure independent from business modules.

## Milestone 3: Dashboard Module

Planned scope:

- Add Dashboard as a plugin-backed module.
- Surface system status and module health.
- Keep dashboard business logic outside core infrastructure.

## Future Modules

Planned modules:

- Market
- Funds
- Cards
- House
- Emergency

Each module should be added independently, with its own tests, migrations where
needed, and README updates when behavior changes.
