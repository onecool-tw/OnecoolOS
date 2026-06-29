# Changelog

All notable changes to Onecool OS will be documented in this file.

The format follows Keep a Changelog principles, and commits follow Conventional
Commits.

## [Unreleased]

### Added

- Project documentation under `docs/`.
- Architecture Decision Record for Core Engine architecture choices.
- Contributing workflow documentation.

## [0.2.1] - 2026-06-29

### Added

- Centralized logging system with system and module-specific loggers.
- Rotating file log support with console output.
- Logging CLI status command.
- Logging tests.

## [0.2.0] - 2026-06-29

### Added

- Centralized configuration files under `config/`.
- Configuration loader with default settings, user overrides, environment
  overrides, validation, and safe handling of missing optional files.
- Sanitized `python -m onecool_os config` CLI output.
- Config System tests.

## [0.1.0] - 2026-06-28

### Added

- Core Engine lifecycle.
- SQLite persistence and migrations.
- Plugin Architecture.
- Event Bus with persistent event log.
- Service Registry.
- Built-in `core.health` plugin.
- CLI commands for initialization, status, and plugin listing.
- Test coverage for database migrations, engine lifecycle, and plugins.
