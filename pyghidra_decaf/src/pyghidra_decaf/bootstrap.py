"""Bootstrap pyghidra_decaf and dependent plugins.

Runs pyghidra.start() in a fresh subprocess up to N times. Each
subprocess gets its own JVM, which is required for two reasons:

1. JPype cannot restart the JVM in-process. After the first
   pyghidra.start() in a Python process, subsequent start() calls
   are no-ops on the JVM side — the classpath stays frozen.

2. The whole point of the multi-iteration loop is to let Ghidra's
   plugin loader pick up jars produced by an EARLIER iteration when
   the next JVM starts. That requires a fresh JVM each time, which
   only happens with separate processes.

Without this, downstream plugins that depend on decaf classes (i.e.
plugins that import classes from pyghidra_decaf.jplugin) cannot be
compiled on a clean system: iteration 1 produces "PyGhidra Decaf.jar",
but iteration 2 in the same process is a JVM no-op so the dependent
plugin's compile still doesn't see decaf classes on the classpath.

The loop terminates when an iteration produces no new extension
directories under ~/.config/ghidra/<version>/Extensions/ — at that
point cross-extension dependencies have settled. The bootstrap does
not need to know which plugins it is compiling; it simply watches
the Extensions directory for new entries.
"""

# Standard Libraries
import os
import subprocess
import sys
from pathlib import Path


def find_ghidra_extensions_dir() -> Path | None:
    """Find the Ghidra extensions directory for the current GHIDRA_INSTALL_DIR."""
    ghidra_install = os.environ.get('GHIDRA_INSTALL_DIR', '')
    if not ghidra_install:
        return None

    # Extract version dir name from install dir (e.g., ghidra_12.0.4_PUBLIC)
    ghidra_dir_name = Path(ghidra_install).name

    # Search ~/.config/ghidra/ for matching version directory
    config_ghidra = Path.home() / '.config' / 'ghidra'
    if not config_ghidra.exists():
        # Also check ~/.ghidra/ (older convention)
        config_ghidra = Path.home() / '.ghidra'
    if not config_ghidra.exists():
        return None

    for entry in config_ghidra.iterdir():
        if entry.is_dir() and ghidra_dir_name in entry.name:
            return entry / 'Extensions'

    return None


def get_extension_dirs() -> set[str]:
    """Return the names of currently-present Ghidra extension directories."""
    extensions_dir = find_ghidra_extensions_dir()
    if extensions_dir is None or not extensions_dir.exists():
        return set()
    return {entry.name for entry in extensions_dir.iterdir() if entry.is_dir()}


def bootstrap() -> int:
    """Run pyghidra.start() up to N times to compile extension Java code.

    The loop terminates when an iteration produces no new extension
    directories. This is the natural convergence signal for the
    cross-extension dependency chain: once a round adds nothing, the
    classpath has settled.

    Returns 0 on success or "nothing to compile"; 1 on configuration error.
    """
    ghidra_install = os.environ.get('GHIDRA_INSTALL_DIR', '')
    if not ghidra_install:
        print(
            'Error: GHIDRA_INSTALL_DIR environment variable is not set.',
            file=sys.stderr,
        )
        return 1

    if not Path(ghidra_install).is_dir():
        print(
            f'Error: GHIDRA_INSTALL_DIR does not exist: {ghidra_install}',
            file=sys.stderr,
        )
        return 1

    baseline = get_extension_dirs()
    print(f'Ghidra install:      {ghidra_install}')
    print(
        f'Existing extensions: {", ".join(sorted(baseline)) if baseline else "(none)"}',
    )

    # Each "run" is a fresh subprocess so the JVM (and its classpath)
    # starts from scratch. Subsequent runs see jars produced by earlier
    # runs because Ghidra scans Extensions/ at JVM startup.
    runner_code = (
        'import sys\n'
        'try:\n'
        '    import pyghidra\n'
        '    pyghidra.start()\n'
        'except SystemExit:\n'
        '    raise\n'
        'except BaseException as e:\n'
        '    # Compile failures are expected during bootstrap iterations\n'
        '    # — the next run fixes them once jars from this run land.\n'
        '    print(f"  (run reported: {type(e).__name__}: {e})", file=sys.stderr)\n'
    )

    max_runs = 3
    for i in range(1, max_runs + 1):
        print(f'\nBootstrap run {i}/{max_runs}...')
        before = get_extension_dirs()
        proc = subprocess.run(
            [sys.executable, '-c', runner_code],
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )
        after = get_extension_dirs()
        new = after - before

        if proc.returncode != 0:
            # Surface the last few lines of stderr so users see why a
            # run failed (typically a compile error before all jars
            # have landed).
            tail = '\n'.join(proc.stderr.strip().splitlines()[-8:])
            if tail:
                print(f'  (subprocess exit {proc.returncode}; stderr tail:)')
                for line in tail.splitlines():
                    print(f'    {line}')

        if new:
            print(f'  Newly compiled this run: {", ".join(sorted(new))}')
        else:
            print('  No new extensions compiled this run.')

        # Converged: no new extensions appeared this round and we've
        # given the chain at least one chance to grow past the first
        # iteration.
        if not new and i > 1:
            break

    final = get_extension_dirs()
    compiled = sorted(final - baseline)
    if compiled:
        print(f'\nBootstrap complete. Compiled: {", ".join(compiled)}')
    else:
        print('\nBootstrap complete. No new extensions compiled.')

    return 0


def main() -> None:
    sys.exit(bootstrap())


if __name__ == '__main__':
    main()
