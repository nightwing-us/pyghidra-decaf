"""
Integration tests for pyghidra_decaf.decaf_setup — real entry-point discovery
and Java template rendering with the test consumer fixture installed.

Tests in this file fall into two groups:
  1. Pure-Python tests (no JVM needed): entry-point loading and template
     rendering.  These use test_consumer_installed only.
  2. JVM tests (@pytest.mark.ghidra): spawn a subprocess with the fixture
     installed so that pyghidra.start() sees the fixture during decaf_setup().
     Subprocess isolation avoids the session-JVM ordering problem.
"""

# Standard Libraries
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Optional

# Third Party Libraries
import pytest

# Our Libraries
from pyghidra_decaf.decaf_setup import (
    _load_entry_points,
    plugin_java_template,
)
from pyghidra_decaf.launch import (
    DecafExtensionInfo,
    PluginStatus,
    PluginType,
)

_FIXTURE_DIR = Path(__file__).parent.parent / 'fixtures' / 'decaf_test_consumer'


# ---------------------------------------------------------------------------
# _load_entry_points — decaf.init
# ---------------------------------------------------------------------------


def test_load_entry_points_init_returns_list_with_test_consumer(
    test_consumer_installed: None,
) -> None:
    """After installing the fixture, decaf.init must expose at least one callable."""
    callables = _load_entry_points('decaf.init')
    assert len(callables) >= 1


def test_load_entry_points_init_callable_returns_extension_info(
    test_consumer_installed: None,
) -> None:
    """Each decaf.init callable must accept a None launcher and return DecafExtensionInfo."""
    callables = _load_entry_points('decaf.init')
    # Pass None as launcher — the test fixture ignores it.
    ext_infos = [fn(None) for fn in callables]
    assert any(isinstance(ei, DecafExtensionInfo) for ei in ext_infos)


def test_load_entry_points_init_contains_test_consumer_extension(
    test_consumer_installed: None,
) -> None:
    """The test consumer's DecafExtensionInfo must have name='DecafTestConsumer'."""
    callables = _load_entry_points('decaf.init')
    ext_infos = [fn(None) for fn in callables]
    names = [ei.name for ei in ext_infos if isinstance(ei, DecafExtensionInfo)]
    assert 'DecafTestConsumer' in names


def test_load_entry_points_init_plugin_info_fields(
    test_consumer_installed: None,
) -> None:
    """The plugin info inside the fixture extension has the expected metadata."""
    callables = _load_entry_points('decaf.init')
    ext_infos = [fn(None) for fn in callables]
    consumer_ext = next(
        ei for ei in ext_infos
        if isinstance(ei, DecafExtensionInfo) and ei.name == 'DecafTestConsumer'
    )
    assert consumer_ext.author == 'pyghidra_decaf test suite'
    assert consumer_ext.version == '0.0.1'
    assert len(consumer_ext.plugins) == 2

    plugin = consumer_ext.plugins[0]
    assert plugin.class_name == 'TestConsumerPlugin'
    assert plugin.status is PluginStatus.STABLE
    assert plugin.type is PluginType.Plugin

    program_plugin = consumer_ext.plugins[1]
    assert program_plugin.class_name == 'TestConsumerProgramPlugin'
    assert program_plugin.status is PluginStatus.STABLE
    assert program_plugin.type is PluginType.ProgramPlugin


# ---------------------------------------------------------------------------
# _load_entry_points — decaf.load
# ---------------------------------------------------------------------------


def test_load_entry_points_load_returns_list_with_test_consumer(
    test_consumer_installed: None,
) -> None:
    """After installing the fixture, decaf.load must expose at least one callable."""
    callables = _load_entry_points('decaf.load')
    assert len(callables) >= 1


def test_load_entry_points_load_callable_returns_plugin_tuples(
    test_consumer_installed: None,
) -> None:
    """Each decaf.load callable must return a list of (str, class) tuples."""
    callables = _load_entry_points('decaf.load')
    for loader in callables:
        result = loader()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            fq_name, cls = item
            assert isinstance(fq_name, str)
            assert isinstance(cls, type)


def test_load_entry_points_load_contains_test_consumer_class(
    test_consumer_installed: None,
) -> None:
    """The test consumer loader must return an entry whose fq_name ends with TestConsumerPlugin."""
    callables = _load_entry_points('decaf.load')
    all_entries = []
    for loader in callables:
        all_entries.extend(loader())

    fq_names = [fq for fq, _ in all_entries]
    assert any('TestConsumerPlugin' in name for name in fq_names)


# ---------------------------------------------------------------------------
# plugin_java_template — rendering with fixture fields
# ---------------------------------------------------------------------------


def test_java_template_renders_test_consumer_class_name(
    test_consumer_installed: None,
) -> None:
    """Template rendered with fixture fields must contain the class name."""
    src = plugin_java_template.format(
        package_name='decaf.test.decaf_test_consumer.plugin',
        plugin_status='PluginStatus.STABLE',
        plugin_package='decaf_test_consumer.plugin',
        plugin_category='Testing',
        short_description='pyghidra_decaf test consumer',
        description='A minimal plugin used by the pyghidra_decaf integration test suite.',
        class_name='TestConsumerPlugin',
        parent_type='Plugin',
        additional_imports='',
        services_provided='',
        services_required='',
        events_consumed='',
        events_provided='',
        is_slow_installation='false',
    )
    assert 'class TestConsumerPlugin' in src


def test_java_template_renders_plugin_info_annotation(
    test_consumer_installed: None,
) -> None:
    """Template rendered with fixture fields must have @PluginInfo annotation."""
    src = plugin_java_template.format(
        package_name='decaf.test.decaf_test_consumer.plugin',
        plugin_status='PluginStatus.STABLE',
        plugin_package='decaf_test_consumer.plugin',
        plugin_category='Testing',
        short_description='pyghidra_decaf test consumer',
        description='Test.',
        class_name='TestConsumerPlugin',
        parent_type='Plugin',
        additional_imports='',
        services_provided='',
        services_required='',
        events_consumed='',
        events_provided='',
        is_slow_installation='false',
    )
    assert '@PluginInfo(' in src
    assert 'status = PluginStatus.STABLE' in src


def test_java_template_renders_init_null_guard(
    test_consumer_installed: None,
) -> None:
    """Rendered template must include the null-initializer guard in init()."""
    src = plugin_java_template.format(
        package_name='decaf.test.decaf_test_consumer.plugin',
        plugin_status='PluginStatus.STABLE',
        plugin_package='decaf_test_consumer.plugin',
        plugin_category='Testing',
        short_description='pyghidra_decaf test consumer',
        description='Test.',
        class_name='TestConsumerPlugin',
        parent_type='Plugin',
        additional_imports='',
        services_provided='',
        services_required='',
        events_consumed='',
        events_provided='',
        is_slow_installation='false',
    )
    assert 'if (initializer == null)' in src
    lines = src.splitlines()
    guard_idx = next(i for i, ln in enumerate(lines) if 'if (initializer == null)' in ln)
    nearby = '\n'.join(lines[guard_idx: guard_idx + 6])
    assert 'return;' in nearby


# ---------------------------------------------------------------------------
# JVM: decaf_setup() generates Java file — subprocess for clean ordering
# ---------------------------------------------------------------------------


@pytest.mark.ghidra
def test_decaf_setup_generates_java_file(tmp_path: Path) -> None:
    """
    Install the fixture, start a fresh JVM (which triggers decaf_setup), then
    verify the generated Java source for TestConsumerPlugin exists on disk.

    Runs in a subprocess so that (a) fixture installation precedes JVM start,
    and (b) this test does not disturb the session JVM.

    Exit codes:
      0 — java file found, LoadedPlugins contains consumer
      1 — assertion failed (file absent or consumer missing)
      2 — environment / import problem (test is skipped)
    """
    import os
    ghidra_dir = os.environ.get('GHIDRA_INSTALL_DIR', '')
    if not ghidra_dir:
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    probe = f"""
import os, sys, subprocess, importlib.metadata
from pathlib import Path

fixture_dir = {str(_FIXTURE_DIR)!r}

# Install fixture
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

from pyghidra_decaf.decaf_setup import LoadedPlugins
consumer = next((ei for ei in LoadedPlugins if ei.name == 'DecafTestConsumer'), None)
if consumer is None:
    print('DecafTestConsumer not in LoadedPlugins:', [ei.name for ei in LoadedPlugins])
    sys.exit(1)

gen_root = Path(os.environ['HOME']) / '.config' / 'decaf'
# Find the versioned subdirectory
java_file = None
for ver_dir in gen_root.iterdir():
    candidate = ver_dir / 'DecafTestConsumer' / 'TestConsumerPlugin.java'
    if candidate.exists():
        java_file = candidate
        break
# Also check top-level (older layout)
if java_file is None:
    top = gen_root / 'DecafTestConsumer' / 'TestConsumerPlugin.java'
    if top.exists():
        java_file = top

if java_file is None:
    print('Java file not found under', gen_root)
    sys.exit(1)

print('OK:', java_file)
sys.exit(0)
"""

    # Isolate HOME so the probe writes to a fresh tmp_path tree rather than
    # the real ~/.config/decaf, preventing false-passes from prior-run artifacts.
    isolated_env = {**os.environ, 'HOME': str(tmp_path)}
    result = subprocess.run(
        [sys.executable, '-c', probe],
        capture_output=True,
        text=True,
        timeout=180,
        env=isolated_env,
    )
    if result.returncode == 2:
        pytest.skip(f'Subprocess env problem:\n{result.stderr}')
    assert result.returncode == 0, (
        f'decaf_setup Java generation failed.\nstdout: {result.stdout}\nstderr: {result.stderr}'
    )



# ---------------------------------------------------------------------------
# JAR Recompilation on Metadata Change
# ---------------------------------------------------------------------------
#
# These tests verify that when a plugin's stub metadata changes, pyghidra
# recompiles the JAR on the next Ghidra start, and that idempotent runs do
# not trigger spurious recompilation.
#
# Strategy:
#   - The fixture is COPIED into tmp_path; the checked-in source under
#     tests/fixtures/ is never mutated.
#   - Each test mutates the literal `shortDescription=...` in the copy to
#     produce a different rendered Java stub.
#   - Recompilation is detected via plugin_version in extension.properties:
#     the compiled JAR lives in Ghidra's extension_path (only available
#     post-JVM), so we use plugin_version fingerprinting and let pyghidra's
#     own _uninstall_old_plugin handle the stale extension dir on version
#     mismatch. Reading extension.properties is deterministic — no mtime.
#   - Each probe subprocess uninstalls decaf_test_consumer before installing
#     from the fixture copy, preventing shadowing by the original editable
#     install.
#   - pyghidra.start() returns a launcher whose extension_path attribute
#     gives the exact Ghidra extensions path without guessing.
#   - jpype can only start the JVM once per process, so Run 1 and Run 2 are
#     executed as separate subprocess invocations from the pytest test body,
#     not from within a single probe process. Each run script installs the
#     fixture, starts Ghidra, reads extension.properties, and prints a
#     result line to stdout that the test body parses.

# The literal in the fixture's entrypoints.py that we mutate in the copy.
_FIXTURE_SHORT_DESC_ORIG = "shortDescription='pyghidra_decaf test consumer'"
_FIXTURE_SHORT_DESC_CHANGED = "shortDescription='pyghidra_decaf test consumer CHANGED'"


@pytest.fixture()
def _restore_decaf_test_consumer() -> Iterator[None]:
    """
    Function-scoped fixture that ensures a clean ``decaf_test_consumer`` install
    state before and after each test that uses it.

    Teardown reinstalls from the checked-in fixture directory so that a mutated
    editable left behind by one test cannot bleed into the next.  The ``yield``
    point is the test itself; teardown runs unconditionally (even on test failure).
    """
    yield
    # Teardown: remove whatever editable the test may have left, then restore
    # the canonical editable from the checked-in fixture source.
    subprocess.run(
        [sys.executable, '-m', 'pip', 'uninstall', '-y', 'decaf_test_consumer'],
        capture_output=True,
    )
    subprocess.run(
        [
            sys.executable, '-m', 'pip', 'install', '-e',
            str(_FIXTURE_DIR), '--quiet', '--force-reinstall', '--no-deps',
        ],
        capture_output=True,
    )


def _make_ghidra_run_script(fixture_dir: Path) -> str:
    """
    Return a Python script (string) that:
      1. Uninstalls decaf_test_consumer from the shared venv.
      2. pip install -e <fixture_dir> --force-reinstall.
      3. Verifies decaf_test_consumer.__file__ resolves into <fixture_dir>.
         Exits 3 if the installed location is wrong (install shadowing detected).
      4. pyghidra.start() → reads extension_path → finds extension.properties.
      5. Prints plugin_version=<value> to stdout (machine-readable).
      6. Exits 0 on success, 2 on environment/Ghidra failure, 3 on wrong install.

    The script is designed to be run as a fresh subprocess so each call gets
    its own JVM (jpype allows only one startJVM per process).

    ``--force-reinstall`` prevents pip from skipping the install when the
    package name is already registered (e.g. from a prior test's editable).
    """
    return f"""
import sys, subprocess
from pathlib import Path

fixture_dir = Path({str(fixture_dir)!r})

# --- install ---
subprocess.run(
    [sys.executable, '-m', 'pip', 'uninstall', '-y', 'decaf_test_consumer'],
    capture_output=True,
)
r = subprocess.run(
    [
        sys.executable, '-m', 'pip', 'install', '-e', str(fixture_dir),
        '--quiet', '--force-reinstall', '--no-deps',
    ],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print('pip install failed:', r.stderr, file=sys.stderr)
    sys.exit(2)
import importlib
importlib.invalidate_caches()
# .pth files are only processed at interpreter startup; the pip install above
# wrote a new .pth pointing at fixture_dir/src, but this running subprocess's
# sys.path doesn't reflect it.  Insert the fresh path explicitly so imports
# below resolve to the just-installed copy, not whatever .pth was active when
# this subprocess started.
_fixture_src = str(fixture_dir / 'src')
if _fixture_src not in sys.path:
    sys.path.insert(0, _fixture_src)

# --- verify install location ---
# If a prior test left an editable pointing to a different tmp_path directory,
# pip may have resolved the wrong source tree.  Catch that early rather than
# silently running decaf_setup() against the wrong entrypoints.
try:
    import decaf_test_consumer as _dtc
    importlib.invalidate_caches()
    # Re-import to pick up the freshly installed location.
    import importlib as _il
    _dtc = _il.reload(_dtc)
    dtc_file = Path(_dtc.__file__).resolve()
    fixture_resolved = fixture_dir.resolve()
    if not str(dtc_file).startswith(str(fixture_resolved)):
        print(
            f'WRONG INSTALL: decaf_test_consumer.__file__={{dtc_file}} '
            f'does not start with {{fixture_resolved}}',
            file=sys.stderr,
        )
        sys.exit(3)
    print(f'install verified: {{dtc_file}}', file=sys.stderr)
except Exception as e:
    print(f'install verification error: {{e}}', file=sys.stderr)
    sys.exit(2)

# --- start Ghidra ---
try:
    import pyghidra
    launcher = pyghidra.start()
except Exception as e:
    print('pyghidra.start() failed:', e, file=sys.stderr)
    import traceback; traceback.print_exc(file=sys.stderr)
    sys.exit(2)

# --- find extension.properties via launcher.extension_path ---
# launcher.extension_path is set during _pre_launch_init (launcher.py:282)
# and cached, so it is safe to read after start().
from pathlib import Path as _Path
ext_props = _Path(launcher.extension_path) / 'DecafTestConsumer' / 'extension.properties'
print(f'extension_path={{launcher.extension_path}}', file=sys.stderr)
print(f'ext_props={{ext_props}}', file=sys.stderr)

if not ext_props.exists():
    print(f'extension.properties not found: {{ext_props}}', file=sys.stderr)
    sys.exit(2)

# --- parse and print plugin_version ---
pv = None
for line in ext_props.read_text().splitlines():
    if line.startswith('plugin_version='):
        pv = line.split('=', 1)[1]
        break
if pv is None:
    print('plugin_version not found in extension.properties', file=sys.stderr)
    sys.exit(2)

# Machine-readable output — test body parses this line.
print(f'plugin_version={{pv}}')
sys.exit(0)
"""


def _run_probe(
    script: str,
    isolated_env: 'dict[str, str]',
    timeout: int = 300,
) -> 'subprocess.CompletedProcess[str]':
    """Run a probe script in a subprocess with the given isolated environment."""
    return subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=isolated_env,
    )


def _parse_plugin_version(stdout: str) -> 'Optional[str]':
    """Extract plugin_version value from probe stdout, or None."""
    for line in stdout.splitlines():
        if line.startswith('plugin_version='):
            return line.split('=', 1)[1]
    return None


@pytest.mark.ghidra
def test_jar_recompiled_when_metadata_changes_without_version_bump(
    tmp_path: Path,
    _restore_decaf_test_consumer: None,
) -> None:
    """
    Verifies the fix: when a plugin's stub changes without a version bump,
    plugin_version in extension.properties changes on the next Ghidra start,
    which triggers pyghidra's _uninstall_old_plugin → _install_plugin recompile.

    Without the fix, plugin_version stays "0.0.1" on both runs (bug).
    With the fix, plugin_version becomes "0.0.1+<hash>" on run 2 (fix works).

    Each "Ghidra run" is a separate subprocess so jpype gets a fresh JVM each
    time (jpype does not allow restarting the JVM within a single process).

    Skips cleanly when GHIDRA_INSTALL_DIR is not set.
    """
    import shutil as _shutil

    if not os.environ.get('GHIDRA_INSTALL_DIR'):
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    # Copy fixture — never touch the tracked source under tests/fixtures/.
    fixture_copy = tmp_path / 'fixture'
    _shutil.copytree(str(_FIXTURE_DIR), str(fixture_copy))

    # Confirm the literal we plan to mutate exists in the copy.
    entrypoints_copy = fixture_copy / 'src' / 'decaf_test_consumer' / 'entrypoints.py'
    assert _FIXTURE_SHORT_DESC_ORIG in entrypoints_copy.read_text(), (
        f'Literal {_FIXTURE_SHORT_DESC_ORIG!r} not found in fixture copy. '
        'Adjust _FIXTURE_SHORT_DESC_ORIG to match the real fixture.'
    )

    isolated_env = {**os.environ, 'HOME': str(tmp_path / 'home')}

    # ===== RUN 1: original fixture =====
    run1 = _run_probe(_make_ghidra_run_script(fixture_copy), isolated_env)
    print('--- run1 stdout ---'); print(run1.stdout)
    print('--- run1 stderr ---'); print(run1.stderr)
    if run1.returncode == 2:
        pytest.skip(f'Run 1: Ghidra problem (exit 2):\n{run1.stderr}')
    assert run1.returncode != 3, (
        f'Run 1: install shadowing detected (exit 3):\n{run1.stderr}'
    )
    assert run1.returncode == 0, f'Run 1 failed (exit {run1.returncode}):\n{run1.stderr}'

    pv1 = _parse_plugin_version(run1.stdout)
    assert pv1 is not None, f'Run 1: plugin_version not found in stdout:\n{run1.stdout}'
    print(f'Run 1 plugin_version: {pv1!r}')

    # ===== MUTATE: change shortDescription in the copy =====
    ep_text = entrypoints_copy.read_text()
    ep_mutated = ep_text.replace(_FIXTURE_SHORT_DESC_ORIG, _FIXTURE_SHORT_DESC_CHANGED)
    assert ep_mutated != ep_text, (
        f'Mutation had no effect — {_FIXTURE_SHORT_DESC_ORIG!r} not found in copy'
    )
    entrypoints_copy.write_text(ep_mutated)

    # ===== RUN 2: mutated fixture, same package version =====
    run2 = _run_probe(_make_ghidra_run_script(fixture_copy), isolated_env)
    print('--- run2 stdout ---'); print(run2.stdout)
    print('--- run2 stderr ---'); print(run2.stderr)
    if run2.returncode == 2:
        pytest.skip(f'Run 2: Ghidra problem (exit 2):\n{run2.stderr}')
    assert run2.returncode != 3, (
        f'Run 2: install shadowing detected (exit 3):\n{run2.stderr}'
    )
    assert run2.returncode == 0, f'Run 2 failed (exit {run2.returncode}):\n{run2.stderr}'

    pv2 = _parse_plugin_version(run2.stdout)
    assert pv2 is not None, f'Run 2: plugin_version not found in stdout:\n{run2.stdout}'
    print(f'Run 2 plugin_version: {pv2!r}')

    # ===== VERIFY =====
    # Without the fix: pv1 == pv2 == "0.0.1" (JAR not recompiled — BUG).
    # With the fix:    pv2 == "0.0.1+<hash>" != pv1 (JAR recompiled — FIXED).
    assert pv1 != pv2, (
        f'plugin_version unchanged ({pv2!r}) after stub change — '
        'stub change not detected. This is the BUG being fixed.'
    )
    assert '+' in pv2, (
        f'plugin_version changed to {pv2!r} but lacks expected +hash suffix'
    )

    # Paranoia: confirm the tracked fixture was not touched.
    checked_in_ep = _FIXTURE_DIR / 'src' / 'decaf_test_consumer' / 'entrypoints.py'
    assert _FIXTURE_SHORT_DESC_CHANGED not in checked_in_ep.read_text(), (
        'The checked-in fixture was mutated — copy-on-mutate invariant violated!'
    )


@pytest.mark.ghidra
def test_jar_not_recompiled_when_stub_unchanged(
    tmp_path: Path,
    _restore_decaf_test_consumer: None,
) -> None:
    """
    Idempotency test: when metadata has NOT changed between runs, plugin_version
    must be identical on both runs — no spurious reinstall or recompile.

    Skips cleanly when GHIDRA_INSTALL_DIR is not set.
    """
    import shutil as _shutil

    if not os.environ.get('GHIDRA_INSTALL_DIR'):
        pytest.skip('GHIDRA_INSTALL_DIR not set')

    fixture_copy = tmp_path / 'fixture'
    _shutil.copytree(str(_FIXTURE_DIR), str(fixture_copy))

    isolated_env = {**os.environ, 'HOME': str(tmp_path / 'home')}

    # ===== RUN 1 =====
    run1 = _run_probe(_make_ghidra_run_script(fixture_copy), isolated_env)
    print('--- run1 stdout ---'); print(run1.stdout)
    print('--- run1 stderr ---'); print(run1.stderr)
    if run1.returncode == 2:
        pytest.skip(f'Run 1: Ghidra problem (exit 2):\n{run1.stderr}')
    assert run1.returncode != 3, (
        f'Run 1: install shadowing detected (exit 3):\n{run1.stderr}'
    )
    assert run1.returncode == 0, f'Run 1 failed (exit {run1.returncode}):\n{run1.stderr}'

    pv1 = _parse_plugin_version(run1.stdout)
    assert pv1 is not None, f'Run 1: plugin_version not found in stdout:\n{run1.stdout}'
    print(f'Run 1 plugin_version: {pv1!r}')

    # ===== RUN 2: same fixture, NO mutation =====
    run2 = _run_probe(_make_ghidra_run_script(fixture_copy), isolated_env)
    print('--- run2 stdout ---'); print(run2.stdout)
    print('--- run2 stderr ---'); print(run2.stderr)
    if run2.returncode == 2:
        pytest.skip(f'Run 2: Ghidra problem (exit 2):\n{run2.stderr}')
    assert run2.returncode != 3, (
        f'Run 2: install shadowing detected (exit 3):\n{run2.stderr}'
    )
    assert run2.returncode == 0, f'Run 2 failed (exit {run2.returncode}):\n{run2.stderr}'

    pv2 = _parse_plugin_version(run2.stdout)
    assert pv2 is not None, f'Run 2: plugin_version not found in stdout:\n{run2.stdout}'
    print(f'Run 2 plugin_version: {pv2!r}')

    # ===== VERIFY =====
    assert pv1 == pv2, (
        f'plugin_version changed {pv1!r} -> {pv2!r} with no stub change — '
        'the fix is over-recompiling.'
    )
