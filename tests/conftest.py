"""
Shared pytest fixtures for pyghidra_decaf tests.

Session-scoped fixtures:
  test_consumer_installed  — pip-installs the decaf_test_consumer fixture package.

Marker:
  ghidra  — mark tests that require a live Ghidra JVM.
             Run without them: pytest -m "not ghidra"
"""

# Standard Libraries
import importlib.metadata
import subprocess
import sys
from pathlib import Path
from typing import Iterator

# Third Party Libraries
import pytest

# ---------------------------------------------------------------------------
# Prevent pytest from descending into the fixtures source tree.
# ---------------------------------------------------------------------------

collect_ignore = ['fixtures']

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_FIXTURE_DIR = Path(__file__).parent / 'fixtures' / 'decaf_test_consumer'


# ---------------------------------------------------------------------------
# test_consumer_installed
# ---------------------------------------------------------------------------


@pytest.fixture(scope='session')
def test_consumer_installed(request: pytest.FixtureRequest) -> Iterator[None]:
    """
    Pip-install the decaf_test_consumer fixture package in editable mode for
    the duration of the session, then uninstall on teardown.

    Fails (not skips) if the install step fails, so CI is not silently green.
    Teardown (uninstall + sys.path cleanup) runs via a finalizer, guaranteeing
    it executes even if setup or a dependent test raises or fails.
    """
    fixture_src = str(_FIXTURE_DIR / 'src')

    def _teardown() -> None:
        if fixture_src in sys.path:
            sys.path.remove(fixture_src)
        subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', '-y', 'decaf_test_consumer', '--quiet'],
            capture_output=True,
        )

    request.addfinalizer(_teardown)

    install_result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-e', str(_FIXTURE_DIR), '--quiet'],
        capture_output=True,
        text=True,
    )
    if install_result.returncode != 0:
        pytest.fail(
            f'decaf_test_consumer install failed (rc={install_result.returncode}):\n'
            f'{install_result.stderr}'
        )

    # pip install -e writes a .pth file that is only processed at interpreter
    # startup, so the source directory will NOT be on sys.path for in-process
    # imports that happen later in the same session.  Add it explicitly here.
    if fixture_src not in sys.path:
        sys.path.insert(0, fixture_src)

    # Invalidate cached entry-point lookups so the new package is visible.
    importlib.invalidate_caches()

    # Verify the package is importable after install.
    try:
        importlib.metadata.version('decaf_test_consumer')
    except importlib.metadata.PackageNotFoundError:
        pytest.fail('decaf_test_consumer not discoverable after install')

    yield
