# Onecool OS

Onecool OS is a Python-based personal asset operating system. Milestone 1
delivers the Core Engine: SQLite persistence, plugin loading, event publishing,
service registration, and a command-line entry point.

## Requirements

- Python 3.11+
- SQLite, included with Python

Install development dependencies:

```bash
python -m pip install -r requirements.txt
```

## Quick Start

Initialize the local database:

```bash
python -m onecool_os init
```

Check engine status:

```bash
python -m onecool_os status
```

List loaded plugins:

```bash
python -m onecool_os plugins
```

Run tests:

```bash
python -m pytest
```

## Configuration

Environment variables:

- `ONECOOL_OS_DB_PATH`: SQLite database path. Defaults to
  `data/onecool_os.sqlite3`.
- `ONECOOL_OS_PLUGIN_PATHS`: Additional plugin directories separated by the OS
  path separator.

## Architecture

Milestone 1 keeps the architecture intentionally small and modular:

- `onecool_os.core.engine`: Starts and stops the Core Engine.
- `onecool_os.core.database`: Manages SQLite connections and schema migrations.
- `onecool_os.core.plugins`: Loads built-in and external plugins.
- `onecool_os.core.events`: Publishes in-process events and persists them.
- `onecool_os.core.registry`: Registers shared services for plugins.

Future modules such as Market, Funds, Cards, House, Emergency, and Dashboard
should be added as plugins that depend on the public Core Engine interfaces.

## Plugin Contract

A plugin exposes a callable named `create_plugin` that returns an object with:

- `manifest`: a `PluginManifest`
- `activate(context)`: called when the engine starts
- `deactivate(context)`: called when the engine stops

External plugin directories may contain Python modules or packages. Plugin
packages can include a `plugin.json` file:

```json
{
  "module": "my_plugin",
  "enabled": true
}
```

The module still owns its runtime manifest through `create_plugin`.
