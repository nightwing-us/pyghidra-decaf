"""
Integration tests for pyghidra_decaf.decaf.pyghidra_decaf (decaf_load path).

The non-JVM tests verify entry-point discovery for 'decaf.load'.  The
@pytest.mark.ghidra test verifies decaf_register() behaviour once the JVM is up.

Because pyghidra's JVM starts only once per process and must see the fixture
before start(), the JVM-dependent test runs in a subprocess.
"""

# Standard Libraries
import os
import subprocess
import sys
from pathlib import Path
from typing import Type

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.decaf_setup import _load_entry_points

_FIXTURE_DIR = Path(__file__).parent.parent / 'fixtures' / 'decaf_test_consumer'


# ---------------------------------------------------------------------------
# Pure-Python: entry-point discovery for decaf.load
# ---------------------------------------------------------------------------


def test_decaf_load_entry_points_present(test_consumer_installed: None) -> None:
    """At least one decaf.load loader must be discoverable."""
    loaders = _load_entry_points('decaf.load')
    assert len(loaders) >= 1


def test_decaf_load_loader_is_callable(test_consumer_installed: None) -> None:
    """Every discovered decaf.load entry point must be callable."""
    loaders = _load_entry_points('decaf.load')
    for loader in loaders:
        assert callable(loader)


def test_decaf_load_loader_returns_list(test_consumer_installed: None) -> None:
    """Every loader must return a list (possibly empty)."""
    loaders = _load_entry_points('decaf.load')
    for loader in loaders:
        result = loader()
        assert isinstance(result, list)


def test_decaf_load_loader_tuple_fq_name_is_string(test_consumer_installed: None) -> None:
    """The fully-qualified name in each tuple must be a non-empty string."""
    loaders = _load_entry_points('decaf.load')
    for loader in loaders:
        for fq_name, _cls in loader():
            assert isinstance(fq_name, str) and fq_name


def test_decaf_load_loader_tuple_class_is_type(test_consumer_installed: None) -> None:
    """The class in each tuple must be an actual type."""
    loaders = _load_entry_points('decaf.load')
    for loader in loaders:
        for _fq_name, cls in loader():
            assert isinstance(cls, type)


def test_decaf_load_consumer_fq_name(test_consumer_installed: None) -> None:
    """The test consumer loader returns the expected fully-qualified class name."""
    loaders = _load_entry_points('decaf.load')
    fq_names = []
    for loader in loaders:
        fq_names.extend(fq for fq, _ in loader())
    assert 'decaf_test_consumer.plugin.TestConsumerPlugin' in fq_names


def test_decaf_load_consumer_class_matches_import(test_consumer_installed: None) -> None:
    """
    The plugin class returned by the loader must be the same object as the
    class imported directly from the fixture module.
    """
    # Third Party Libraries
    from decaf_test_consumer.plugin import TestConsumerPlugin  # type: ignore[import]

    loaders = _load_entry_points('decaf.load')
    returned_classes: list[Type[object]] = []
    for loader in loaders:
        returned_classes.extend(cls for _, cls in loader())
    assert TestConsumerPlugin in returned_classes


# ---------------------------------------------------------------------------
# JVM-gated: decaf_load() populates _plugin_types — subprocess
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_decaf_load_plugin_types_contains_consumer() -> None:
    """
    After pyghidra.start() (which fires decaf_setup + decaf_load via
    pyghidra entry points), the internal _plugin_types registry must contain
    the test consumer's fully-qualified name.

    Runs in a subprocess so the fixture is installed before the JVM starts.

    Exit codes: 0 = key present (pass), 1 = key absent (fail), 2 = env problem (skip).
    """
    ghidra_dir = os.environ.get('GHIDRA_INSTALL_DIR', '')
    if not ghidra_dir:
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    probe = f"""
import sys, subprocess
fixture_dir = {str(_FIXTURE_DIR)!r}

r = subprocess.run(
    [sys.executable, '-m', 'pip', 'install', '-e', fixture_dir, '--quiet'],
    capture_output=True, text=True
)
if r.returncode != 0:
    print('install failed:', r.stderr, file=sys.stderr)
    sys.exit(2)

try:
    import pyghidra
    pyghidra.start()
except Exception as e:
    print('pyghidra.start() failed:', e, file=sys.stderr)
    sys.exit(2)

from pyghidra_decaf.decaf.pyghidra_decaf import _plugin_types
key = 'decaf_test_consumer.plugin.TestConsumerPlugin'
if key not in _plugin_types:
    print('key absent; registered:', list(_plugin_types.keys()))
    sys.exit(1)
print('OK: key present')
sys.exit(0)
"""

    result = subprocess.run(
        [sys.executable, '-c', probe],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode == 2:
        pytest.skip(f'Subprocess env problem:\n{result.stderr}')
    assert result.returncode == 0, (
        f'TestConsumerPlugin not in _plugin_types after decaf_load().\n'
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )
