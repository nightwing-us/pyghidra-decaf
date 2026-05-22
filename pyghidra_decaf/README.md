# PyGhidra Decaf

Java-free Python plugin loading for Ghidra

Enables pure Python Ghidra plugins to be implemented by handling the boilerplate JPype glue code to connect the Java and Python side plugin implementations.

## Prerequisites

- **Ghidra 11.0+** with PyGhidra installed (PyGhidra is included in the Ghidra distribution by default)
- **Python 3.10+**

## Installation

1. Activate (or create) the venv that will be used to run ghidra
2. Install `pyghidra_decaf` (`pip install pyghidra_decaf`)
3. Run ghidra `pyghidra --gui --install-dir /path/to/ghidra/install` (for example ~/ghidra/ghidra_11_3_2_PUBLIC)
4. You'll be prompted to enable a new plugin, confirm that. If not, open File -> Install Extensions and enable "Pyghidra Decaf"

# Installing Decaf plugins

1. Activate the venv you previously set up with pyghidra_decaf
2. Install the python module for the Decaf plugin (e.g. `pip install <your-decaf-plugin>`)
3. Run ghidra `pyghidra --gui --install-dir /path/to/ghidra/install` (for example ~/ghidra/ghidra_11_3_2_PUBLIC)
4. You'll be prompted to enable a new plugin, confirm that. If not, open File -> Install Extensions and enable "Pyghidra Decaf"

## Troubleshooting

**Plugin doesn't appear in Ghidra after installation**
- Verify you're using **Ghidra 11.0 or later**. Older versions may not have PyGhidra bundled.
- Rerun `pyghidra --gui --install-dir /path/to/ghidra/install` to trigger the bootstrap process.
- Check that extension files were created: `ls -la ~/.config/ghidra/*/Extensions/`

**ImportError: jpype not found**
- Ensure you're using the same Python virtual environment that Ghidra runs from. PyGhidra bundles JPype, but it must be loaded in the same venv context.
- Verify venv activation: `which python` should point to your plugin venv, not system Python.

**Java class not found: myplugin.plugin.MyPlugin**
- Verify the `decaf.load` entry point name matches your actual plugin class name.
- The fully qualified name in the error message must match the first element of the tuple returned by your `decaf_load()` function.

For more detailed help, see the [Plugin Development Guide](docs/index.md) and [Architecture Guide](docs/gap-analysis-ghidra-pyghidra-decaf.md) in the main repository.
