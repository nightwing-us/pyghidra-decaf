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
from typing import Dict, Optional


def _parse_reported_paths(stdout: str) -> Dict[str, str]:
    """Extract sentinel-reported paths from a bootstrap subprocess's stdout.

    The runner prints lines of the form ``__DECAF_EXT_PATH__=<path>`` and
    ``__DECAF_VERSION__=<version>``. Returns a dict with keys ``ext_path`` /
    ``version`` for whichever sentinels were present (last occurrence wins).
    """
    result: Dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith('__DECAF_EXT_PATH__='):
            result['ext_path'] = line.split('=', 1)[1].strip()
        elif line.startswith('__DECAF_VERSION__='):
            result['version'] = line.split('=', 1)[1].strip()
    return result


def _resolve_extensions_dir(reported: Dict[str, str]) -> Optional[Path]:
    """Resolve the Ghidra Extensions dir to watch.

    Prefer the path pyghidra itself reported (authoritative on multi-version
    hosts); fall back to the GHIDRA_INSTALL_DIR name-matching heuristic only
    when no sentinel was captured (older pyghidra without the reporting hook).
    """
    ext = reported.get('ext_path')
    if ext:
        return Path(ext)
    return find_ghidra_extensions_dir()


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


def get_extension_dirs(extensions_dir: Optional[Path]) -> set[str]:
    """Return the names of extension directories under *extensions_dir*."""
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

    # Best-effort initial guess; upgraded to pyghidra's authoritative
    # extension_path as soon as the first run reports it.
    ext_dir = find_ghidra_extensions_dir()
    baseline = get_extension_dirs(ext_dir)
    baseline_dir = ext_dir
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
        '    launcher = pyghidra.start()\n'
        '    try:\n'
        '        print(f"__DECAF_EXT_PATH__={launcher.extension_path}")\n'
        '        print(f"__DECAF_VERSION__={launcher.app_info.version}")\n'
        '    except Exception as report_err:\n'
        '        print(f"  (could not report paths: {report_err})", file=sys.stderr)\n'
        'except SystemExit:\n'
        '    raise\n'
        'except BaseException as e:\n'
        '    # Compile failures are expected during bootstrap iterations\n'
        '    # — the next run fixes them once jars from this run land.\n'
        '    print(f"  (run reported: {type(e).__name__}: {e})", file=sys.stderr)\n'
    )

    max_runs = 3
    reported_ext_seen = False
    version_reported = False
    for i in range(1, max_runs + 1):
        print(f'\nBootstrap run {i}/{max_runs}...')
        before = get_extension_dirs(ext_dir)
        proc = subprocess.run(
            [sys.executable, '-c', runner_code],
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )

        # Adopt pyghidra's authoritative Extensions dir (robust to multiple
        # co-installed Ghidra versions, where the GHIDRA_INSTALL_DIR name-match
        # heuristic can resolve to the wrong tree or none).
        reported = _parse_reported_paths(proc.stdout)
        if not version_reported and 'version' in reported:
            print(f'  Ghidra (pyghidra-reported) version: {reported["version"]}')
            version_reported = True
        resolved = _resolve_extensions_dir(reported)
        if 'ext_path' in reported:
            reported_ext_seen = True
        if resolved is not None and resolved != ext_dir:
            print(f'  Using Ghidra-reported extensions dir: {resolved}')
            ext_dir = resolved
            # Re-baseline against the authoritative dir so the final
            # "Compiled" summary is a same-dir diff. Extensions already present
            # here (including any this run compiled before the dir was known)
            # count as baseline, not as newly compiled.
            if baseline_dir != ext_dir:
                baseline = get_extension_dirs(ext_dir)
                baseline_dir = ext_dir
                before = baseline

        after = get_extension_dirs(ext_dir)
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

    # If we never learned a real Extensions dir — neither pyghidra's report nor
    # the heuristic — convergence detection was meaningless. Fail loudly rather
    # than claim success while having watched nothing.
    if not reported_ext_seen and (ext_dir is None or not ext_dir.exists()):
        print(
            'Error: could not determine the Ghidra Extensions directory.\n'
            f'  GHIDRA_INSTALL_DIR={ghidra_install}\n'
            '  pyghidra did not report an extension_path and no matching '
            'directory was found under ~/.config/ghidra or ~/.ghidra.\n'
            '  On a host with multiple Ghidra versions, ensure pyghidra and '
            'GHIDRA_INSTALL_DIR point at the same installation.',
            file=sys.stderr,
        )
        return 1

    final = get_extension_dirs(ext_dir)
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
