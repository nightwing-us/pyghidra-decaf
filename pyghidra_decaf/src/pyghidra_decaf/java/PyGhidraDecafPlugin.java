package pyghidra_decaf.jplugin;

import java.util.function.Consumer;

import ghidra.MiscellaneousPluginPackage;
import ghidra.app.plugin.PluginCategoryNames;
import ghidra.app.script.GhidraState;
import ghidra.framework.plugintool.PluginInfo;
import ghidra.framework.plugintool.PluginTool;
import ghidra.framework.plugintool.util.PluginStatus;
import ghidra.util.exception.AssertException;


@PluginInfo(
	status = PluginStatus.RELEASED,
	packageName = MiscellaneousPluginPackage.NAME,
	category = PluginCategoryNames.COMMON,
	shortDescription = "Enables python ghidra plugins",
	description = "Python Ghidra plugin implementation to be loaded via pyghidra"
)
public final class PyGhidraDecafPlugin extends DecafPlugin {

	// set via reflection
	// Stores the python plugin constructor
	private static Consumer<PyGhidraDecafPlugin> initializer = null;

	public PyGhidraDecafPlugin(PluginTool tool) {
		super(tool);
	}

	/**
	 * Sets the plugin's Python side initializer.<p>
	 *
     * This method is for <b>internal use only</b> and is only public so it can be
     * called from Python.
	 *
	 * @param initializer the Python side initializer
	 * @throws AssertException if the code completer has already been set
	 */
	public static void setInitializer(Consumer<PyGhidraDecafPlugin> init_handler) {
		if (initializer != null) {
			throw new AssertException("PyGhidraDecafPlugin initializer has already been set");
		}
		initializer = init_handler;
	}

	/**
	 * Initialization method; override to add initialization for this plugin.
	 * This is where a plugin should acquire its services. When this method
	 * is called, all plugins have been instantiated in the tool.
	 */
	protected void init() {
		// Calls the python constructor
		initializer.accept(this);
	}
}
