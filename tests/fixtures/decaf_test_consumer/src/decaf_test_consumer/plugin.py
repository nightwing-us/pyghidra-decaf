"""
Test consumer plugin implementation.

TestConsumerPlugin.init() records a call by writing to the file path given in
the DECAF_TEST_CONSUMER_LOG environment variable (if set).  This file-based
side-channel survives the JVM boundary: the Java-side initializer.accept(this)
call crosses into Python and writes the flag before returning.
"""

# Standard Libraries
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # pyghidra_decaf.decaf.plugin is only importable after the JVM starts,
    # so we reference it for type hints only.
    from pyghidra_decaf.decaf.plugin import DecafPlugin as JDecafPlugin


# Module-level flag set when init() is called (works for in-process tests).
init_called: bool = False


class TestConsumerPlugin:
    """Minimal DecafPlugin subclass used exclusively by the test suite.

    Intentionally NOT a DecafPlugin subclass to avoid requiring a live JVM
    for the common-path test; the framework does not runtime-enforce the type.
    """

    # Safety belt against future pre-instantiation name access; no longer
    # strictly required after decaf_load.py:78 fix.
    name: str = 'TestConsumerPlugin'

    def __init__(self, plugin_tool: 'JDecafPlugin') -> None:
        global init_called
        init_called = True

        log_path = os.environ.get('DECAF_TEST_CONSUMER_LOG')
        if log_path:
            with open(log_path, 'a') as fh:
                fh.write('init_called\n')
