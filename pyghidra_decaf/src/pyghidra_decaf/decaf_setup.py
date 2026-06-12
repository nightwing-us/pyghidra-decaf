# This is invoked by pyghidra before jpype is configured. Allows
# the plugin to install itself into the Ghidra environment.
# Standard Libraries
import hashlib
import importlib.metadata
import logging
from pathlib import Path
import shutil
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    TypeVar,
)

# Our Libraries
from pyghidra_decaf.launch import (
    DecafExtensionInfo,
    DecafLauncher,
    DecafPluginInfo,
    DecafSetup,
    PluginType,
)


try:
    # Third Party Libraries
    from pyghidra import ExtensionDetails  # type: ignore[import-untyped]
    from pyghidra import HeadlessPyGhidraLauncher as HeadlessLauncher
except ImportError:
    try:
        # Third Party Libraries
        from pyhidra import ExtensionDetails  # type: ignore[import-not-found, no-redef]
        from pyhidra import HeadlessPyhidraLauncher as HeadlessLauncher  # type: ignore[no-redef]
    except ImportError:
        raise ImportError('Either pyhidra or pyghidra must be installed')


logger = logging.getLogger(__name__)


TEntryCallable = TypeVar('TEntryCallable', bound=Callable[..., Any])


LoadedPlugins: List[DecafExtensionInfo] = []

# Maps a decaf extension name to the directory holding its generated Java stub(s).
# Populated during decaf_setup() so the loader (decaf_register) can recover the
# javac diagnostic when a plugin fails to load — pyghidra logs compile errors
# only at WARNING and a GUI launch discards them, so the real "cannot find
# symbol" cause is otherwise invisible. See _diagnose_plugin_load_failure.
GENERATED_STUB_DIRS: Dict[str, Path] = {}


def _load_entry_points(group: str) -> List[TEntryCallable]:
    """
    Loads any entry point callbacks registered by external python packages.
    """
    try:
        entries: Optional[importlib.metadata.EntryPoints] = (
            importlib.metadata.entry_points(group=group)
        )
    except TypeError:
        # this is deprecated but the above doesn't work for 3.9
        metadata_entry_points = importlib.metadata.entry_points()
        if hasattr(metadata_entry_points, 'select'):
            entries = metadata_entry_points.select(group=group)
        else:
            # Pre-3.10 dict-shaped EntryPoints fallback; modern stub
            # types EntryPoints as a Selectable, hence the ignore.
            entries = metadata_entry_points.get(group, None)  # type: ignore[attr-defined]
            if entries is None:
                return []
    entry_points: List[TEntryCallable] = []
    if entries:
        for entry in entries:
            name = entry.name
            try:
                # Give launcher to callback so they can edit vmargs, install plugins, etc.
                callback = cast(TEntryCallable, entry.load())
                logger.debug(f'Calling {group} entry point: {name}')
                entry_points.append(callback)
            except Exception as e:
                logger.error(
                    f'Failed to run {group} entry point {name} with error: {e}'
                )
    return entry_points


class DecafLauncherWrapper(DecafLauncher):
    def __init__(self, launcher: HeadlessLauncher):
        super().__init__()
        self._launcher = launcher
        self._source_paths: List[Path] = []

    @property
    def extensions_path(self) -> Path:
        return cast(Path, self._launcher.extension_path)

    @property
    def java_home(self) -> Path:
        return cast(Path, self._launcher.java_home)

    @property
    def ghidra_install_dir(self) -> Path:
        return cast(Path, self._launcher.install_dir)

    def add_classpaths(self, *args: Path) -> None:
        self._launcher.add_classpaths(*[str(path) for path in args])


def _stub_needs_rebuild(stub_file_path: Path, rendered_src: str) -> bool:
    """
    Return True when the on-disk Java stub differs from the freshly-rendered
    source, meaning the compiled JAR is stale and must be recompiled.

    Returns True if:
      - The stub file does not exist (new plugin), OR
      - The rendered stub differs from the on-disk stub (metadata changed).

    Returns False when the on-disk stub is byte-for-byte identical to the
    rendered source, meaning no recompilation is needed.

    The renderer (plugin_java_template) is fully deterministic — no timestamps
    or UUIDs — so a byte-for-byte comparison is correct and has no false
    positives.

    Args:
        stub_file_path: Path to the on-disk .java stub file.
        rendered_src:   Freshly-rendered Java stub source code.

    Returns:
        True if recompilation is needed, False otherwise.
    """
    if not stub_file_path.exists():
        return True
    return stub_file_path.read_text() != rendered_src


plugin_java_template = """package {package_name};

import java.util.function.Consumer;

import ghidra.app.script.GhidraState;
import ghidra.framework.plugintool.PluginInfo;
import ghidra.framework.plugintool.PluginTool;
import ghidra.framework.plugintool.util.PluginStatus;
import ghidra.util.exception.AssertException;
{additional_imports}
import ghidra.util.Msg;

@PluginInfo(
	status = {plugin_status},
	packageName = "{plugin_package}",
	category = "{plugin_category}",
	shortDescription = "{short_description}",
	description = "{description}",
	servicesProvided = {{ {services_provided} }},
	servicesRequired = {{ {services_required} }},
	eventsConsumed = {{ {events_consumed} }},
	eventsProduced = {{ {events_provided} }},
	isSlowInstallation = {is_slow_installation}
)
public final class {class_name} extends Decaf{parent_type} {{

	// set via reflection
	// Stores the python plugin constructor
	private static Consumer<{class_name}> initializer = null;

	public {class_name}(PluginTool tool) {{
		super(tool);
	    Msg.info("J: {class_name}", "Constructor");
	}}

	/**
	 * Sets the plugin's Python side initializer.<p>
	 *
     * This method is for <b>internal use only</b> and is only public so it can be
     * called from Python.
	 *
	 * @param initializer the Python side initializer
	 * @throws AssertException if the code completer has already been set
	 */
	public static void setInitializer(Consumer<{class_name}> init_handler) {{
	    Msg.info("J: {class_name}", "J{class_name}: Setting Initializer");
		if (initializer != null) {{
			throw new AssertException("{class_name} initializer has already been set");
		}}
		initializer = init_handler;
	}}

	/**
	 * Initialization method; override to add initialization for this plugin.
	 * This is where a plugin should acquire its services. When this method
	 * is called, all plugins have been instantiated in the tool.
	 */
	@Override
	protected void init() {{
	    Msg.info("J: {class_name}", "init() start");
		if (initializer == null) {{
			Msg.warn("J: {class_name}", "{class_name}: Python initializer not set — skipping plugin init");
			return;
		}}
		// Calls the python constructor
        initializer.accept(this);
		Msg.info("J: {class_name}", "init() complete");
	}}
}}
"""


def _build_additional_imports(plugin: 'DecafPluginInfo') -> str:
    """Render the Java ``import …;`` block for a plugin's generated stub.

    Always includes the mandatory Decaf base-class import for the plugin's
    type, in addition to any imports the plugin itself declares. The block is
    gated on this combined list — never on ``plugin.plugin_imports`` alone — so
    the base class the generated ``extends Decaf*`` clause needs is present even
    when the plugin declares no imports of its own. (Gating on plugin_imports
    dropped that base import and caused "cannot find symbol: class
    DecafProgramPlugin" for import-less plugins.)
    """
    addl_imports = list(plugin.plugin_imports)
    if plugin.type == PluginType.ProgramPlugin:
        addl_imports.append('pyghidra_decaf.jplugin.DecafProgramPlugin')
    elif plugin.type == PluginType.Plugin:
        addl_imports.append('pyghidra_decaf.jplugin.DecafPlugin')
    else:
        raise ValueError(f'Invalid plugin type ({plugin.type})')

    if not addl_imports:
        return ''
    return 'import ' + ';\nimport '.join(addl_imports) + ';'


def decaf_setup(launcher: HeadlessLauncher) -> None:
    logged_messages = ''
    logged_messages += '[decaf] -> decaf_setup()\n'
    logger.warning('[decaf] -> decaf_setup()')

    try:
        # Start by installing pyghidra_decaf
        source_path = Path(__file__).parent / 'java'
        decaf_version = importlib.metadata.version('pyghidra_decaf')
        details = ExtensionDetails(
            name='PyGhidra Decaf',
            description='Enables pure-python Ghidra plugins to be loaded',
            author='Nightwing Group, LLC.',
            version=decaf_version,
        )

        launcher.install_plugin(
            source_path, details
        )  # registers plugin to be compiled and installed

        decaf_gen_path = Path.home() / '.config' / 'decaf' / launcher.app_info.version
        decaf_gen_path.mkdir(parents=True, exist_ok=True)

        decaf_launcher = DecafLauncherWrapper(launcher=launcher)

        # Next search for python modules that have advertised a pyghidra_decaf plugin
        # Each should return enough info to populate PluginInfo to generate java plugin code
        plugin_setups: List[DecafSetup] = _load_entry_points(group='decaf.init')
        for plugin_setup in plugin_setups:
            ext_info = plugin_setup(decaf_launcher)
            ext_gen_path = decaf_gen_path / ext_info.name
            ext_gen_path.mkdir(exist_ok=True)
            GENERATED_STUB_DIRS[ext_info.name] = ext_gen_path

            details = ExtensionDetails(
                name=ext_info.name,
                description=ext_info.description,
                author=ext_info.author,
                version=ext_info.version,
            )

            # Generate java plugin code; detect stub changes to decide whether
            # the compiled JAR needs to be invalidated.
            any_stub_changed = False
            all_rendered_srcs: List[str] = []
            for plugin in ext_info.plugins:
                plugin_java_pkg = (
                    f'{ext_info.java_package}.' if ext_info.java_package else ''
                )
                plugin_java_pkg = f'{plugin_java_pkg}{plugin.module_name}'
                plugin_src = plugin_java_template.format(
                    package_name=plugin_java_pkg,
                    plugin_status=plugin.status,
                    plugin_package=plugin.module_name,
                    plugin_category=plugin.category,
                    short_description=plugin.shortDescription,
                    description=plugin.description,
                    class_name=plugin.class_name,
                    parent_type=plugin.type.name,
                    additional_imports=_build_additional_imports(plugin),
                    services_provided=(
                        ', '.join(
                            f'{svc_name}.class' for svc_name in plugin.servicesProvided
                        )
                    ),
                    services_required=(
                        ', '.join(
                            f'{svc_name}.class' for svc_name in plugin.servicesRequired
                        )
                    ),
                    events_consumed=(
                        ', '.join(
                            f'{evt_name}.class' for evt_name in plugin.eventsConsumed
                        )
                    ),
                    events_provided=(
                        ', '.join(
                            f'{evt_name}.class' for evt_name in plugin.eventsProduced
                        )
                    ),
                    is_slow_installation=str(plugin.isSlowInstallation).lower(),
                )
                stub_file_path = ext_gen_path / f'{plugin.class_name}.java'
                if _stub_needs_rebuild(stub_file_path, plugin_src):
                    any_stub_changed = True
                    logger.debug(
                        f'[decaf] stub changed for {plugin.class_name}; '
                        'JAR will be invalidated'
                    )
                # Always write the stub — it is the authoritative cache state.
                with open(stub_file_path, 'w') as f:
                    f.write(plugin_src)
                all_rendered_srcs.append(plugin_src)

            # Embed a content hash of all rendered stubs into plugin_version.
            # pyghidra's _uninstall_old_plugin (launcher.py:512) compares the
            # stored plugin_version in extension.properties against the value we
            # supply here; any mismatch causes it to rmtree the extension dir
            # (including the JAR) so _install_plugin recompiles from scratch.
            #
            # The hash must be UNCONDITIONAL so that plugin_version is stable
            # across launches whenever the stubs are unchanged:
            #
            #   First install (stub missing → any_stub_changed=True):
            #     stored plugin_version = "0.0.1+hashA"
            #   Unchanged re-run (byte-identical stubs → any_stub_changed=False):
            #     new plugin_version   = "0.0.1+hashA"  ← same hash, no reinstall ✓
            #   Metadata change (stubs differ → any_stub_changed=True):
            #     new plugin_version   = "0.0.1+hashB"  ← different hash, reinstall ✓
            #
            # A conditional assignment would produce "0.0.1" on unchanged runs,
            # mismatching the stored "0.0.1+hashA" and triggering a reinstall on
            # every launch after the first — the exact bug this fixes.
            #
            # We cannot delete the JAR directly here because extension_path is
            # only available after the JVM starts (launcher.py:282 requires
            # self._layout, which is set in _pre_launch_init, called after us).
            combined = ''.join(all_rendered_srcs)
            stub_hash = hashlib.md5(combined.encode()).hexdigest()[:8]
            details.plugin_version = f'{ext_info.version}+{stub_hash}'
            logger.debug(
                '[decaf] plugin_version=%r for %s (stub_changed=%s)',
                details.plugin_version,
                ext_info.name,
                any_stub_changed,
            )

            for src_path in ext_info.java_source:
                if src_path.exists():
                    if src_path.is_file():
                        shutil.copy2(src_path, ext_gen_path)
                    elif src_path.is_dir():
                        shutil.copytree(src_path, ext_gen_path)
            launcher.install_plugin(ext_gen_path, details)

            LoadedPlugins.append(ext_info)
    except Exception as e:
        raise Exception(logged_messages + str(e)) from e
