# PyGhidra Decaf

PyGhidra Decaf is a Ghidra plugin that provides the glue and minimal wrapper code generation
to enable Ghidra plugin development in Python

# Pre-Requisites

A recent Ghidra with PyGhidra bundled

# Development Guide

PyGhidra Decaf plugins mirror their Java Ghidra counterparts and relies on JPype to bridge the
divide between Java and Python. Decaf will generate a small java stub class for your plugin placed
in a namespace that mirrors your python package structure.

## Plugin Entrypoints

Your Decaf plugin wheel will need to publish two entrypoints:

1. Decaf Init

    This is called before JPype initialization and is how your plugin is published and installed
    in Ghidra. 
    
    #### `pyproject.toml`:
    ```toml
    [project.entry-points."decaf.init"]
    decaf_setup = "myplugin.decaf_init:decaf_init"
    ```
    The initialization function needs to return your extension info. This is called before JPype 
    is initialized so you cannot import any Java libraries from this module.
    #### `decaf_init.py`:
    ```python
    # Standard Libraries
    from importlib.metadata import version
    
    # Third Party Libraries
    from pyghidra_decaf.launch import (
        DecafExtensionInfo,
        DecafLauncher,
        DecafPluginInfo,
        PluginStatus,
        PluginType,
    )
    
    def decaf_init(launcher: DecafLauncher) -> DecafExtensionInfo:
        lib_version = version("myplugin")
        return DecafExtensionInfo(
            name="MyPlugin",
            description="My Ghidra plugin",
            author="Your Name",
            version=lib_version,
            plugins=[
                DecafPluginInfo(
                    type=PluginType.ProgramPlugin,
                    qualname="MyPlugin",
                    class_name="MyPlugin",
                    status=PluginStatus.STABLE,
                    module_name="myplugin.myplugin",
                    category="Analysis",
                    shortDescription="My Ghidra plugin",
                    description="My Ghidra plugin",
                )
            ],
            java_package='',
        )
    ```
  
2. Decaf Load
    
    This is called after JPype loads but before Ghidra starts to load plugins. 

    #### `pyproject.toml`:
    ```toml
    [project.entry-points."decaf.load"]
    decaf_load = "myplugin.myplugin:decaf_load"
    ```
    The load function needs the full namespace of your plugin class and type. 
    This is called after JPype so the module containing this function can import java
    libraries.
    #### `myplugin/myplugin.py`:
    ```python
    def decaf_load() -> List[Tuple[str, Type[DecafPlugin]]]:
        return [
            ('myplugin.myplugin.MyPlugin', MyPlugin)
        ]
    ```

## Base Classses

The base classes DecafPlugin and DecafProgramPlugin are provided that mirror the Ghidra 
Plugin and ProgramPlugin classes.
