# PyGhidra Decaf

A Python package for developing plugins for Ghidra without requiring Java development

## Installation

```bash
uv pip install pyghidra_decaf
```

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

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.

Copyright © 2026 Nightwing Group, LLC.
