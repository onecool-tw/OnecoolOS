# Architecture

Onecool OS is a Python-based personal asset operating system. The current
architecture is centered on a small Core Engine that owns infrastructure
concerns and exposes stable extension points for business modules.

## Core Engine

The Core Engine coordinates startup, shutdown, persistence, events, services,
and plugin lifecycle. It is implemented in `onecool_os.core.engine`.

Responsibilities:

- Open the SQLite database connection.
- Apply schema migrations.
- Create the event bus.
- Create the service registry.
- Load and activate plugins.
- Deactivate plugins and release resources on shutdown.

The Core Engine does not contain business logic. Future business areas such as
Market, Funds, Cards, House, Emergency, and Dashboard should be implemented as
plugins or module packages that depend on public core interfaces.

## Persistence

SQLite is the default persistence layer. The database layer is implemented in
`onecool_os.core.database` and applies SQL migrations from `migrations/`.

The first schema creates:

- `schema_migrations`
- `system_settings`
- `plugins`
- `event_log`

The database layer is infrastructure and must remain independent of business
modules.

## Plugin System

Plugins are loaded through `onecool_os.core.plugins`. A plugin exposes a
`create_plugin` callable that returns an object with a manifest and lifecycle
methods.

Required plugin interface:

- `manifest`
- `activate(context)`
- `deactivate(context)`

The `PluginContext` gives plugins access to:

- SQLite connection
- Event bus
- Service registry

The built-in `core.health` plugin verifies that the engine can load plugins and
register services.

## Event Bus

The event bus is implemented in `onecool_os.core.events`. It supports in-process
event subscriptions and persists all published events to `event_log`.

Events are used for lifecycle visibility and future module communication. Event
payloads should remain serializable dictionaries so they can be stored and
audited consistently.

## Service Registry

The service registry is implemented in `onecool_os.core.registry`. It provides a
small named registry for infrastructure services and plugin-provided services.

The registry should be used for composition between modules. It should not
become a container for hidden global state or business workflows.

## Command Line Interface

The CLI is implemented in `onecool_os.__main__`.

Current commands:

- `init`
- `status`
- `plugins`

Each command starts the Core Engine so every milestone remains executable.
