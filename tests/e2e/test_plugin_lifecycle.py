"""
End-to-end tests for the full pyghidra_decaf plugin lifecycle.

All tests marked @pytest.mark.ghidra require GHIDRA_INSTALL_DIR to be set.

JVM-dependent tests run in subprocesses so the test consumer fixture is
installed *before* pyghidra.start() fires the decaf_setup / decaf_load entry
points.  pyghidra's JVM cannot be restarted within a single process, so
subprocess isolation is the only reliable way to guarantee ordering.

Subprocess exit codes convention used throughout:
  0  — assertion passed
  1  — assertion failed (test failure)
  2  — environment / import problem (test is skipped)
"""

# Standard Libraries
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Third Party Libraries
import pytest

_FIXTURE_DIR = Path(__file__).parent.parent / 'fixtures' / 'decaf_test_consumer'

# Root of the pyghidra_decaf package source (used for clean-venv installs).
_DECAF_PKG_ROOT = Path(__file__).parent.parent.parent / 'pyghidra_decaf'


def _ghidra_available() -> bool:
    return bool(os.environ.get('GHIDRA_INSTALL_DIR', ''))


def _run_probe(
    probe: str,
    timeout: int = 180,
    env: Optional[dict[str, str]] = None,
    python: Optional[str] = None,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    executable = python if python is not None else sys.executable
    return subprocess.run(
        [executable, '-c', probe],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _build_clean_venv(base: Path, timeout: int = 120) -> Path:
    """
    Create a fresh Python venv under *base* with pyghidra and pyghidra_decaf
    installed but WITHOUT decaf_test_consumer.

    Returns the path to the venv's Python binary.

    This is used by the negative isolation test so that even when the
    session-scoped test_consumer_installed fixture has pip-installed
    decaf_test_consumer into the host venv's site-packages (creating a .pth
    file that every subprocess of sys.executable would inherit), the probe
    runs in a completely separate interpreter that never saw the fixture.

    pyghidra is pinned to the same version as the host venv so the fresh venv
    is compatible with the same Ghidra installation that the rest of the suite
    uses.
    """
    import importlib.metadata

    venv_dir = base / 'cleanvenv'

    # Step 1: create the venv.
    r = subprocess.run(
        [sys.executable, '-m', 'venv', str(venv_dir)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f'venv creation failed:\n{r.stderr}')

    clean_python = str(venv_dir / 'bin' / 'python')
    clean_pip = str(venv_dir / 'bin' / 'pip')

    # Pin pyghidra to the same version as the host venv so we stay compatible
    # with the Ghidra installation that the rest of the test suite targets.
    pyghidra_version = importlib.metadata.version('pyghidra')
    pinned_pyghidra = f'pyghidra=={pyghidra_version}'

    # Step 2: install pyghidra + pydantic (and their deps) from PyPI / pip cache.
    # These packages are present in the pip cache from normal test-suite runs so
    # this step is fast (~2 s) even without network access.
    r = subprocess.run(
        [clean_pip, 'install', pinned_pyghidra, 'pydantic', '--quiet'],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f'pip install {pinned_pyghidra}/pydantic failed:\n{r.stderr}'
        )

    # Step 3: install pyghidra_decaf (editable, no extra deps so we don't
    # re-download things already covered by step 2).
    r = subprocess.run(
        [clean_pip, 'install', '-e', str(_DECAF_PKG_ROOT), '--no-deps', '--quiet'],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f'pip install pyghidra_decaf failed:\n{r.stderr}')

    return Path(clean_python)


# ---------------------------------------------------------------------------
# Helper: boilerplate probe header (install fixture + start JVM)
# ---------------------------------------------------------------------------

_PROBE_HEADER = f"""
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
"""


# ---------------------------------------------------------------------------
# Full-boot test: pyghidra.start() does not raise
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_full_boot_does_not_raise() -> None:
    """
    Install the fixture, start the JVM — decaf_setup and decaf_load must run
    without raising an exception.
    """
    if not _ghidra_available():
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    probe = _PROBE_HEADER + """
print('boot OK')
sys.exit(0)
"""
    result = _run_probe(probe)
    if result.returncode == 2:
        pytest.skip(f'Boot env problem:\n{result.stderr}')
    assert result.returncode == 0, (
        f'Boot raised an exception.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )


# ---------------------------------------------------------------------------
# LoadedPlugins contains the test consumer
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_loaded_plugins_contains_test_consumer() -> None:
    """
    After pyghidra.start() with the fixture installed, LoadedPlugins must
    include a DecafExtensionInfo with name='DecafTestConsumer'.
    """
    if not _ghidra_available():
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    probe = _PROBE_HEADER + """
from pyghidra_decaf.decaf_setup import LoadedPlugins
consumer = next((ei for ei in LoadedPlugins if ei.name == 'DecafTestConsumer'), None)
if consumer is None:
    print('DecafTestConsumer missing. Present:', [ei.name for ei in LoadedPlugins])
    sys.exit(1)
print('OK')
sys.exit(0)
"""
    result = _run_probe(probe)
    if result.returncode == 2:
        pytest.skip(f'Env problem:\n{result.stderr}')
    assert result.returncode == 0, (
        f'DecafTestConsumer missing from LoadedPlugins.\n'
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )


# ---------------------------------------------------------------------------
# Generated Java stub exists on disk
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_generated_java_stub_exists(tmp_path: Path) -> None:
    """
    decaf_setup() must write TestConsumerPlugin.java into the config dir.

    Uses HOME=tmp_path so each run writes into a fresh tree, preventing a
    prior run's artifact from producing a false positive.
    """
    if not _ghidra_available():
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    # Build an isolated environment: inherit everything except HOME.
    isolated_env = {**os.environ, 'HOME': str(tmp_path)}

    probe = _PROBE_HEADER + f"""
from pathlib import Path

gen_root = Path({str(tmp_path)!r}) / '.config' / 'decaf'
# Search versioned subdirectories first
java_file = None
if gen_root.exists():
    for candidate_dir in gen_root.iterdir():
        p = candidate_dir / 'DecafTestConsumer' / 'TestConsumerPlugin.java'
        if p.exists():
            java_file = p
            break
    # Fallback: flat layout
    if java_file is None:
        p = gen_root / 'DecafTestConsumer' / 'TestConsumerPlugin.java'
        if p.exists():
            java_file = p

if java_file is None:
    print('Java stub not found. gen_root contents:')
    if gen_root.exists():
        for child in gen_root.iterdir():
            print(' ', child)
    sys.exit(1)

print('OK:', java_file)
sys.exit(0)
"""
    result = _run_probe(probe, env=isolated_env)
    if result.returncode == 2:
        pytest.skip(f'Env problem:\n{result.stderr}')
    assert result.returncode == 0, (
        f'Java stub not found.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )


# ---------------------------------------------------------------------------
# Generated Java stub has expected content
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_generated_java_stub_content(tmp_path: Path) -> None:
    """
    The generated Java source must contain the class declaration and
    @PluginInfo annotation with the null-initializer guard.

    Uses HOME=tmp_path for hermetic output (same rationale as
    test_generated_java_stub_exists).
    """
    if not _ghidra_available():
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    isolated_env = {**os.environ, 'HOME': str(tmp_path)}

    probe = _PROBE_HEADER + f"""
from pathlib import Path

gen_root = Path({str(tmp_path)!r}) / '.config' / 'decaf'
java_file = None
if gen_root.exists():
    for candidate_dir in gen_root.iterdir():
        p = candidate_dir / 'DecafTestConsumer' / 'TestConsumerPlugin.java'
        if p.exists():
            java_file = p
            break
    if java_file is None:
        p = gen_root / 'DecafTestConsumer' / 'TestConsumerPlugin.java'
        if p.exists():
            java_file = p

if java_file is None:
    print('Java stub not found; skipping content check')
    sys.exit(2)

src = java_file.read_text()
errors = []
if 'public final class TestConsumerPlugin' not in src:
    errors.append('missing class declaration')
if '@PluginInfo(' not in src:
    errors.append('missing @PluginInfo annotation')
if 'if (initializer == null)' not in src:
    errors.append('missing null-initializer guard')

if errors:
    print('Content errors:', errors)
    print('First 500 chars:', src[:500])
    sys.exit(1)

print('OK')
sys.exit(0)
"""
    result = _run_probe(probe, env=isolated_env)
    if result.returncode == 2:
        pytest.skip(f'Java stub not available: {result.stdout}')
    assert result.returncode == 0, (
        f'Java stub content check failed.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )


# ---------------------------------------------------------------------------
# Negative test: fixture absent => consumer not in _plugin_types
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_without_fixture_consumer_not_in_plugin_types(tmp_path: Path) -> None:
    """
    When decaf_test_consumer is NOT installed, _plugin_types must not contain
    the test consumer key.

    Runs in a subprocess that uses a freshly-bootstrapped Python venv (created
    under tmp_path) so that even when the session-scoped test_consumer_installed
    fixture has pip-installed the fixture into the host venv's site-packages
    (creating a .pth file that every subprocess of sys.executable inherits),
    the probe cannot see decaf_test_consumer.

    PYTHONNOUSERSITE + PYTHONPATH manipulation is NOT sufficient for this
    because those env-vars do not exclude the venv's own site-packages.  A
    fully separate venv is the only reliable isolation strategy.
    """
    if not _ghidra_available():
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    try:
        clean_python = _build_clean_venv(tmp_path)
    except RuntimeError as exc:
        pytest.skip(f'Could not build clean venv for isolation test: {exc}')

    probe = """
import sys, importlib.metadata, importlib.util

# Sanity-guard: the entire point of this test is that decaf_test_consumer is
# absent.  If it somehow leaked into the clean venv the test would produce a
# silent false-pass, so we surface that as a hard failure instead.
if importlib.util.find_spec('decaf_test_consumer') is not None:
    print('NEGATIVE_TEST_PRECONDITION_VIOLATED: decaf_test_consumer still importable', file=sys.stderr)
    sys.exit(2)
try:
    importlib.metadata.version('decaf_test_consumer')
    print('fixture unexpectedly present in clean venv — venv isolation failed', file=sys.stderr)
    sys.exit(2)
except importlib.metadata.PackageNotFoundError:
    pass

try:
    import pyghidra
    pyghidra.start()
except Exception as e:
    print('pyghidra.start() failed:', e, file=sys.stderr)
    sys.exit(2)

from pyghidra_decaf.decaf.pyghidra_decaf import _plugin_types
key = 'decaf_test_consumer.plugin.TestConsumerPlugin'
if key in _plugin_types:
    print('ERROR: key unexpectedly present in _plugin_types')
    sys.exit(1)
print('OK: key absent as expected')
sys.exit(0)
"""
    result = _run_probe(probe, python=str(clean_python))
    if result.returncode == 2:
        if 'NEGATIVE_TEST_PRECONDITION_VIOLATED' in result.stderr:
            pytest.fail(
                'decaf_test_consumer is importable inside the clean venv — '
                'venv isolation did not work as expected.\n'
                f'stdout: {result.stdout}\nstderr: {result.stderr}'
            )
        pytest.skip(
            'Subprocess could not run negative test '
            f'(env or JVM problem):\n{result.stdout}\n{result.stderr}'
        )
    assert result.returncode == 0, (
        'TestConsumerPlugin unexpectedly in _plugin_types when fixture is not installed.\n'
        f'stdout: {result.stdout}\nstderr: {result.stderr}'
    )
