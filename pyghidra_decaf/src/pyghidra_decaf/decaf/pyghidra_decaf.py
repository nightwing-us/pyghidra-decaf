"""
Core functionality for pyghidra_decaf.
"""

# Standard Libraries
from typing import (
    Dict,
    List,
    Type,
    TYPE_CHECKING,
)

# Third Party Libraries
from java.util.function import Consumer  # type: ignore[import-not-found]
from jpype import JClass  # type: ignore[import-untyped]


if TYPE_CHECKING:
    from pyghidra_decaf.stubs.jplugin import PyGhidraDecafPlugin as JPyGhidraDecafPlugin

# Third Party Libraries
from ghidra.util import Msg

# Our Libraries
from pyghidra_decaf import decaf_setup
from pyghidra_decaf.decaf_setup import _load_entry_points

from ..launch import PluginType
from ._jpype_utils import _get_private_class
from .plugin import (
    DecafLoad,
    DecafPlugin,
)


class DecafLoadException(Exception): ...


def _get_plugin_class() -> JClass:
    return _get_private_class('pyghidra_decaf.jplugin.PyGhidraDecafPlugin')


class DecafGhidraPlugin(DecafPlugin):
    """Base class for Ghidra plugins."""

    def __init__(self, plugin: 'JPyGhidraDecafPlugin') -> None:
        """
        Initialize a new Ghidra plugin.
        """
        super().__init__(plugin)


_plugin_types: Dict[str, Type[DecafPlugin]] = {}
_plugin_instances: Dict[str, DecafPlugin] = {}


def decaf_load() -> None:
    # Called by pyhidra/pyghidra before the tool fully launches (and presumably begin loading plugins)
    global _plugin_types

    Msg.info('decaf.py', 'decaf_load() started')
    Msg.info('decaf.py', 'Loading Java Decaf class')

    decaf_plugin = _get_plugin_class()
    Msg.info('decaf.py', 'Setting decaf initializer')
    decaf_plugin.setInitializer(Consumer @ DecafGhidraPlugin)

    Msg.info('decaf.py', 'Searching for decaf plugins')

    Msg.info('decaf.py', 'Loading entry points')
    plugin_loaders: List[DecafLoad] = _load_entry_points(group='decaf.load')

    Msg.info('decaf.py', 'Registering plugins...')
    for plugin_loader in plugin_loaders:
        Msg.info('decaf.py', 'loading plugin')
        plugin_infos = plugin_loader()
        for plugin_info in plugin_infos:
            Msg.info('decaf.py', f'Registering plugin {plugin_info[0]}')
            decaf_register(*plugin_info)

    Msg.info('decaf.py', 'decaf_load() ended')


def decaf_register(plugin_fq_name: str, plugin_class: Type[DecafPlugin]) -> None:
    global _plugin_types, _plugin_instances
    Msg.info('decaf.py', f'decaf_register({plugin_fq_name}, {plugin_class})')

    _plugin_types[plugin_fq_name] = plugin_class

    for ext_info in decaf_setup.LoadedPlugins:
        Msg.info(
            'decaf_load.decaf_register()',
            f'Looking at {ext_info.name} ({len(ext_info.plugins)} plugins)',
        )
        for plugin_entry in ext_info.plugins:
            Msg.info(
                'decaf_load.decaf_register()',
                f'Looking at {plugin_entry.python_fq_name}',
            )
            if plugin_entry.python_fq_name == plugin_fq_name:
                plugin_class_name = (
                    f'{ext_info.java_package}.' if ext_info.java_package else ''
                )
                plugin_class_name = f'{plugin_class_name}{plugin_entry.python_fq_name}'
                Msg.info('decaf_register()', f'Trying to load {plugin_class_name}')
                java_class = _get_private_class(plugin_class_name)
                Msg.info(
                    'decaf_load.decaf_register()',
                    f'Checking {plugin_entry.type.name} in (ProgramPlugin, Plugin)',
                )
                if plugin_entry.type in (PluginType.ProgramPlugin, PluginType.Plugin):
                    Msg.info(
                        'decaf_load.decaf_register()',
                        'decaf.py: decaf_register() - Setting initializer',
                    )
                    java_class.setInitializer(Consumer @ plugin_class)
                    return

    raise DecafLoadException(
        f'Could not find matching Java plugin class for {plugin_fq_name} ({plugin_class})'
    )
