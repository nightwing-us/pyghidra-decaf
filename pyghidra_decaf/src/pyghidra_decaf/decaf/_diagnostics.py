"""Load-failure diagnostics for decaf plugins.

Kept JVM-free at import time (the ``ghidra.util.Msg`` and ``pyghidra.javac``
imports are deferred into the function body) so this module — and therefore its
tests — load without a started JVM. See the design doc
``docs/plans/2026-06-03-bugfix-tests-ci-bootstrap-design.md`` (WS6).
"""

# Standard Libraries
import tempfile
from pathlib import Path

# Our Libraries
from pyghidra_decaf import decaf_setup


class DecafLoadException(Exception): ...


def _diagnose_plugin_load_failure(
    ext_name: str, plugin_class_name: str, load_err: Exception
) -> 'DecafLoadException':
    """Turn an opaque class-load failure into an actionable, visible error.

    A decaf plugin's Java class is missing almost exclusively because its
    generated stub failed to compile. pyghidra reports compile failures only via
    ``logger.warning`` and a GUI launch discards stdout/stderr, so the real javac
    diagnostic (e.g. "cannot find symbol: class DecafProgramPlugin") never
    reaches the user — they see only ``ClassNotFoundException``.

    We re-run the compiler on the plugin's generated stub (the JVM is up by now)
    to recover the exact diagnostic, log it via Ghidra ``Msg.error`` so it is
    visible in the GUI console, and return a :class:`DecafLoadException` carrying
    it so the propagated error names the true cause.
    """
    # Third Party Libraries (deferred — require a started JVM)
    from ghidra.util import Msg  # type: ignore[import-not-found]

    gen_dir = decaf_setup.GENERATED_STUB_DIRS.get(ext_name)

    diagnostic = None
    if gen_dir is not None and gen_dir.exists():
        try:
            # Third Party Libraries
            from pyghidra.javac import java_compile  # type: ignore[import-untyped]

            with tempfile.TemporaryDirectory() as tmp:
                java_compile(gen_dir, Path(tmp) / 'decaf_compile_check')
            # Compiled cleanly now — the load failure was not a compile error.
        except Exception as compile_err:
            diagnostic = str(compile_err)

    lines = [
        f"decaf plugin '{plugin_class_name}' failed to load — its generated "
        f'Java stub did not compile.',
    ]
    if gen_dir is not None:
        lines.append(f'Generated source: {gen_dir}')
    if diagnostic:
        lines.append(f'Compiler diagnostic:\n{diagnostic}')
    else:
        lines.append(f'Underlying load error: {load_err}')
    message = '\n'.join(lines)

    Msg.error('decaf', message)
    return DecafLoadException(message)
