# PyGhidra Decaf

A Python package for developing plugins for Ghidra without requiring Java development

## Documentation Overview

- [Quick Start](#quick-start) — Write your first plugin in 5 minutes
- [Plugin Development Guide](docs/index.md) — Full API reference and examples
- [Architecture & Comparison](docs/gap-analysis-ghidra-pyghidra-decaf.md) — Why Decaf exists and how it compares to PyGhidra
- [Contributing](CONTRIBUTING.md) — How to submit patches
- [Security](SECURITY.md) — How to report vulnerabilities

## Prerequisites

You'll need:
- **Ghidra 11.0 or later** with PyGhidra bundled (PyGhidra is included in the Ghidra distribution by default)
- **Python 3.10+**

Decaf wraps PyGhidra and provides Python-native plugin development. See [PyGhidra installation docs](https://github.com/NationalSecurityAgency/ghidra/tree/master/GhidraDocs) for setup details.

## The Problem: Ghidra's Plugin Discovery

Ghidra discovers plugins at JVM startup by scanning the classpath for `.class` files annotated with `@PluginInfo`. This bytecode-level scan happens before any Python code runs, so PyGhidra's JPype proxies—which are pure Python objects with no compiled form on disk—are invisible to Ghidra's plugin system. You can use PyGhidra to *script* Ghidra, but you cannot register Python code as a *plugin*, service, or analyzer without hand-written Java boilerplate.

**Decaf solves this** by generating minimal Java stub classes from your Python metadata at setup time, making your Python plugins discoverable by Ghidra's bytecode scanner. At runtime, Decaf binds those stubs to your Python code via JPype reflection. The result: full plugin lifecycle (init, dispose, events, service registration, state persistence) with zero Java development.

## Installation

```bash
uv pip install pyghidra_decaf
```

## Quick Start: Your First Plugin

### 1. Create a minimal plugin package

```bash
mkdir my-ghidra-plugin && cd my-ghidra-plugin
mkdir -p src/my_plugin
touch src/my_plugin/__init__.py
```

### 2. Write `src/my_plugin/decaf_init.py`

```python
from importlib.metadata import version
from pyghidra_decaf.launch import (
    DecafExtensionInfo, DecafPluginInfo, PluginType, PluginStatus
)

def decaf_init(launcher):
    return DecafExtensionInfo(
        name="My Plugin",
        description="My first Ghidra plugin",
        author="You",
        version=version("my-plugin"),
        plugins=[
            DecafPluginInfo(
                type=PluginType.ProgramPlugin,
                qualname="MyPlugin",
                class_name="MyPlugin",
                status=PluginStatus.STABLE,
                module_name="my_plugin.plugin",
                category="Analysis",
                shortDescription="My first plugin",
                description="My first Ghidra plugin in pure Python",
            )
        ],
        java_package="",
    )
```

### 3. Write `src/my_plugin/plugin.py`

```python
from typing import List, Tuple, Type
from pyghidra_decaf.decaf.plugin import DecafProgramPlugin

class MyPlugin(DecafProgramPlugin):
    def init(self):
        self.tool.setStatusInfo("MyPlugin loaded!")

def decaf_load() -> List[Tuple[str, Type[DecafProgramPlugin]]]:
    return [("my_plugin.plugin.MyPlugin", MyPlugin)]
```

### 4. Create `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-plugin"
version = "0.1.0"
description = "My first Ghidra plugin"

[project.entry-points."decaf.init"]
my_plugin = "my_plugin.decaf_init:decaf_init"

[project.entry-points."decaf.load"]
my_plugin = "my_plugin.plugin:decaf_load"
```

### 5. Install and bootstrap

```bash
pip install -e .
pyghidra_decaf_bootstrap
```

### 6. Launch Ghidra and enable the plugin

```bash
pyghidra --gui --install-dir ~/ghidra/ghidra_11_3_2_PUBLIC
```

When prompted, enable "My Plugin" in File → Install Extensions. You'll see "MyPlugin loaded!" in Ghidra's status bar.

For a complete walkthrough, see [Plugin Development Guide](docs/index.md).

## Development

This project uses `uv` for Python environment and package management.

### Setup Development Environment

```bash
# Install uv if you haven't already
curl -sSf https://astral.sh/uv/install.sh | bash

# Create a virtual environment and install dev dependencies
uv venv
uv pip install -e ".[dev]"
```

### Running Tests

```bash
uv run pytest
```

### Type Checking

```bash
uv run mypy
```

### Linting and Formatting

```bash
uv run ruff check src tests
uv run ruff format src tests
```

### Building the Package

```bash
uv build
```

## What's Not Yet Supported

Decaf currently supports `Plugin` and `ProgramPlugin` extension points, enabling you to write:
- Dockable UI panels (via `ComponentProvider` interface)
- Plugin lifecycle hooks (init, dispose, events, state persistence)
- Service registration and event subscriptions

**Not yet supported (patches welcome):**
- `Analyzer` (auto-analysis participation)
- `Loader` (file format support)
- `Exporter` (custom export formats)
- `FieldFactory` (custom Listing columns)
- Custom `PluginEvent` subclasses

For use cases outside these scope, consider hand-written Java plugins or vanilla PyGhidra scripting. See the [Architecture Guide](docs/gap-analysis-ghidra-pyghidra-decaf.md) for detailed feature comparison.

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.

Copyright © 2026 Nightwing Group, LLC.
