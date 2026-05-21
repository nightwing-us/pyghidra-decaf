"""
Entry point implementations for decaf.init and decaf.load groups.

These callables are discovered by pyghidra_decaf via importlib.metadata.
"""

# Standard Libraries
from typing import (
    List,
    Tuple,
    Type,
)

# Our Libraries
from pyghidra_decaf.launch import (
    DecafExtensionInfo,
    DecafLauncher,
    DecafPluginInfo,
    PluginStatus,
    PluginType,
)

from .plugin import TestConsumerPlugin


def init(launcher: DecafLauncher) -> DecafExtensionInfo:
    """
    decaf.init entry point.

    Returns extension metadata plus a single DecafPluginInfo describing
    TestConsumerPlugin.  The launcher argument is accepted but not used —
    the fixture has no extra Java sources or classpath requirements.
    """
    plugin_info = DecafPluginInfo(
        type=PluginType.Plugin,
        qualname='TestConsumerPlugin',
        class_name='TestConsumerPlugin',
        status=PluginStatus.STABLE,
        module_name='decaf_test_consumer.plugin',
        category='Testing',
        shortDescription='pyghidra_decaf test consumer',
        description='A minimal plugin used by the pyghidra_decaf integration test suite.',
    )
    return DecafExtensionInfo(
        name='DecafTestConsumer',
        description='pyghidra_decaf test fixture extension',
        author='pyghidra_decaf test suite',
        version='0.0.1',
        plugins=[plugin_info],
        java_package='decaf.test',
    )


def load() -> List[Tuple[str, Type[TestConsumerPlugin]]]:
    """
    decaf.load entry point.

    Returns a list of (fully_qualified_name, plugin_class) tuples that
    decaf_load() will pass to decaf_register().
    """
    return [('decaf_test_consumer.plugin.TestConsumerPlugin', TestConsumerPlugin)]
