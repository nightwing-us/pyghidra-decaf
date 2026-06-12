"""Unit tests for decaf load-failure diagnostics (no JVM required)."""

# Standard Libraries
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.decaf._diagnostics import (
    DecafLoadException,
    _diagnose_plugin_load_failure,
)


@pytest.fixture
def fake_msg(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub `ghidra.util.Msg` so the lazy import inside the function resolves
    without a JVM."""
    msg = MagicMock()
    ghidra = types.ModuleType('ghidra')
    ghidra_util = types.ModuleType('ghidra.util')
    ghidra_util.Msg = msg
    ghidra.util = ghidra_util
    monkeypatch.setitem(sys.modules, 'ghidra', ghidra)
    monkeypatch.setitem(sys.modules, 'ghidra.util', ghidra_util)
    return msg


def _stub_pyghidra_javac(monkeypatch: pytest.MonkeyPatch, raises) -> None:
    """Stub `pyghidra.javac.java_compile` to either raise or succeed.

    Injects only the `pyghidra.javac` submodule into sys.modules (monkeypatch
    restores/removes it on teardown). Does NOT mutate the real `pyghidra`
    module object, so nothing leaks into other tests.
    """
    javac = types.ModuleType('pyghidra.javac')

    def _compile(src, dest):
        if raises is not None:
            raise raises

    javac.java_compile = _compile
    monkeypatch.setitem(sys.modules, 'pyghidra.javac', javac)


def test_returns_decaf_load_exception_with_compiler_diagnostic(
    fake_msg: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gen_dir = tmp_path / 'MyExt'
    gen_dir.mkdir()
    monkeypatch.setattr(
        'pyghidra_decaf.decaf._diagnostics.decaf_setup.GENERATED_STUB_DIRS',
        {'MyExt': gen_dir},
        raising=False,
    )
    _stub_pyghidra_javac(monkeypatch, RuntimeError('cannot find symbol: DecafPlugin'))

    err = _diagnose_plugin_load_failure('MyExt', 'FooPlugin', Exception('ClassNotFound'))

    assert isinstance(err, DecafLoadException)
    assert 'cannot find symbol: DecafPlugin' in str(err)
    assert fake_msg.error.called


def test_falls_back_to_load_error_when_recompile_succeeds(
    fake_msg: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gen_dir = tmp_path / 'MyExt'
    gen_dir.mkdir()
    monkeypatch.setattr(
        'pyghidra_decaf.decaf._diagnostics.decaf_setup.GENERATED_STUB_DIRS',
        {'MyExt': gen_dir},
        raising=False,
    )
    _stub_pyghidra_javac(monkeypatch, None)  # compiles cleanly now

    err = _diagnose_plugin_load_failure('MyExt', 'FooPlugin', Exception('opaque load'))

    assert isinstance(err, DecafLoadException)
    assert 'opaque load' in str(err)


def test_unknown_extension_falls_back_to_load_error(
    fake_msg: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Extension not in GENERATED_STUB_DIRS -> gen_dir is None: no recompile, no
    # "Generated source" line, message carries the underlying load error.
    monkeypatch.setattr(
        'pyghidra_decaf.decaf._diagnostics.decaf_setup.GENERATED_STUB_DIRS',
        {},
        raising=False,
    )
    err = _diagnose_plugin_load_failure('Nope', 'FooPlugin', Exception('opaque load'))
    assert isinstance(err, DecafLoadException)
    assert 'opaque load' in str(err)
    assert 'Generated source' not in str(err)
    assert fake_msg.error.called
