# ADR-001: Core Engine Architecture Choices

## Status

Accepted

## Context

Onecool OS needs a stable foundation for a personal asset operating system. The
project must support future modules such as Market, Funds, Cards, House,
Emergency, and Dashboard without coupling those modules directly to
infrastructure internals.

Milestone 1 established the Core Engine with SQLite persistence, Plugin
Architecture, an Event Bus, and a Service Registry.

## Decision

Onecool OS will use:

- Plugin Architecture for module extension.
- SQLite for local persistence.
- Event Bus for lifecycle and module events.
- Service Registry for composed service access.

## Rationale

### Plugin Architecture

Plugin Architecture keeps the Core Engine small while allowing future modules to
be added independently. Modules can be loaded, activated, and deactivated
through a consistent lifecycle without changing core startup logic.

This supports loose coupling and keeps business logic inside modules instead of
placing it in infrastructure code.

### SQLite

SQLite is appropriate for a local personal operating system because it is
embedded, durable, widely supported, and available through Python's standard
library. It keeps Milestone 1 executable without requiring external database
services.

SQLite also supports straightforward migrations and can remain stable as the
project grows.

### Event Bus

The Event Bus gives the system a simple way to publish lifecycle and module
events. Persisting events to `event_log` creates an audit trail that can support
future diagnostics, dashboard views, and module integrations.

The current Event Bus is intentionally in-process to keep the Core Engine small
and production-ready for local execution.

### Service Registry

The Service Registry gives plugins a controlled way to expose and consume
services by name. This keeps composition explicit while avoiding direct imports
between unrelated modules.

The registry is not a replacement for business module APIs. It is an
infrastructure-level composition mechanism.

## Consequences

Positive consequences:

- Future modules can be added without redesigning the Core Engine.
- The project remains executable with only Python and SQLite.
- Lifecycle events are observable and persisted.
- Shared services can be composed without tight module coupling.

Tradeoffs:

- Plugin boundaries require discipline to avoid hidden dependencies.
- SQLite keeps deployment simple but is not a distributed database.
- The in-process Event Bus is simple by design and does not replace external
  messaging systems.

## Compatibility

These choices are part of the Core Engine contract and should not be changed
without an explicit architecture decision and backward compatibility plan.
