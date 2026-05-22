package pyghidra_decaf.jplugin;

import java.net.URL;

import java.util.function.BiConsumer;
import java.util.function.BiFunction;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.function.Supplier;

import ghidra.MiscellaneousPluginPackage;
import ghidra.app.events.ProgramActivatedPluginEvent;
import ghidra.app.plugin.PluginCategoryNames;
import ghidra.app.script.GhidraState;
import ghidra.app.services.ProgramManager;
import ghidra.framework.model.DomainFile;
import ghidra.framework.model.DomainObject;
import ghidra.framework.options.SaveState;
import ghidra.framework.plugintool.Plugin;
import ghidra.framework.plugintool.PluginEvent;
import ghidra.framework.plugintool.PluginInfo;
import ghidra.framework.plugintool.PluginTool;
import ghidra.framework.plugintool.util.PluginStatus;
import ghidra.program.model.listing.Program;
import ghidra.program.util.ProgramLocation;
import ghidra.program.util.ProgramSelection;
import ghidra.util.exception.AssertException;


public abstract class DecafPlugin extends Plugin {

	// Stores the python plugin dispose function
	private Supplier<Class<?>[]> handle_getSupportedDataTypes = () -> null;
	private Predicate<DomainFile[]> handle_acceptData = (DomainFile[] data) -> false;
	private Predicate<URL> handle_accept = (URL url) -> false;
	private Supplier<DomainFile[]> handle_getData = () -> null;

	private Runnable finalizer = () -> {};
	private Consumer<PluginEvent> handle_processEvent = (PluginEvent event) -> {};
	private Consumer<SaveState> handle_readConfigState = (SaveState saveState) -> {};
	private Consumer<SaveState> handle_writeConfigState = (SaveState saveState) -> {};
	private Consumer<SaveState> handle_writeDataState = (SaveState saveState) -> {};
	private Consumer<SaveState> handle_readDataState = (SaveState saveState) -> {};
	private BiConsumer<Class<?>, Object> handle_serviceAdded = (Class<?> interfaceClass, Object service) -> {};
	private BiConsumer<Class<?>, Object> handle_serviceRemoved = (Class<?> interfaceClass, Object service) -> {};
	private BooleanSupplier handle_canClose = () -> true;
	private Predicate<DomainObject> handle_canCloseDomainObject = (DomainObject dObj) -> true;
	private Consumer<DomainObject> handle_prepareToSave = (DomainObject dObj) -> {};
	private BooleanSupplier handle_saveData = () -> true;
	private BooleanSupplier handle_hasUnsaveData = () -> false;
	private Runnable handle_close = () -> {};
	private Consumer<Object> handle_restoreTransientState = (Object state) -> {};
	private Supplier<Object> handle_getTransientState = () -> null;
	private Runnable handle_dataStateRestoreCompleted = () -> {};
	private Function<DomainObject, Object> handle_getUndoRedoState = (DomainObject domainObject) -> null;
	private BiConsumer<DomainObject, Object> handle_restoreUndoRedoState = (DomainObject domainObject, Object state) -> {};

	public DecafPlugin(PluginTool tool) {
		super(tool);
	}

	/**
	 * Return classes of data types that this plugin can support.
	 * @return classes of data types that this plugin can support
	 */
	@Override
	public Class<?>[] getSupportedDataTypes() {
	    Class<?>[] retData = handle_getSupportedDataTypes.get();
		if (retData != null) {
		    return retData;
		}
        return super.getSupportedDataTypes();
	}

	/**
	 * Method called if the plugin supports this domain file.
	 *
	 * @param data array of {@link DomainFile}s
	 * @return boolean true if can accept
	 */
	@Override
	public boolean acceptData(DomainFile[] data) {
		return handle_acceptData.test(data);
	}

	/**
	 * Request plugin to process URL if supported.  Actual processing may be delayed and
	 * interaction with user may occur (e.g., authentication, approval, etc.).
	 *
	 * @param url data URL
	 * @return boolean true if this plugin can process URL.
	 */
	public boolean accept(URL url) {
		return handle_accept.test(url);
	}

	/**
	 * Get the domain files that this plugin has open.
	 *
	 * @return array of {@link DomainFile}s that are open by this Plugin.
	 */
	public DomainFile[] getData() {
		DomainFile[] retData = handle_getData.get();
		if (retData != null)
		{
		    return retData;
		}
		return super.getData();
	}

	/**
	 * Tells a plugin that it is no longer needed.  The plugin should release
	 * any resources that it has.  All actions, components, services will automatically
	 * be cleaned up.
	 */
	protected void dispose() {
		finalizer.run();
		super.dispose();
	}

	/**
	 * Method called to process a plugin event.  Plugins should override this method
	 * if the plugin processes PluginEvents;
	 * @param event plugin to process
	 */
	@Override
	public void processEvent(PluginEvent event) {
		this.handle_processEvent.accept(event);
	}

	/**
	 * Tells the Plugin to read its data-independent (preferences)
	 * properties from the input stream.
	 * @param saveState object that holds primitives for state information
	 */
	public void readConfigState(SaveState saveState) {
		handle_readConfigState.accept(saveState);
	}

	/**
	 * Tells a Plugin to write any data-independent (preferences)
	 * properties to the output stream.
	 * @param saveState object that holds primitives for state information
	 */
	public void writeConfigState(SaveState saveState) {
		handle_writeConfigState.accept(saveState);
	}

	/**
	 * Tells the Plugin to write any data-dependent state to the
	 * output stream.
	 * @param saveState object that holds primitives for state information
	 */
	public void writeDataState(SaveState saveState) {
		handle_writeDataState.accept(saveState);
	}

	/**
	 * Tells the Plugin to read its data-dependent state from the
	 * given SaveState object.
	 * @param saveState object that holds primitives for state information
	 */
	public void readDataState(SaveState saveState) {
		handle_readDataState.accept(saveState);
	}

	/**
	 * Notifies this plugin that a service has been added to
	 *   the plugin tool.
	 * Plugins should override this method if they update their state
	 * when a particular service is added.
	 *
	 * @param interfaceClass The <b>interface</b> of the added service
	 * @param service service that is being added
	 */
	@Override
	public void serviceAdded(Class<?> interfaceClass, Object service) {
		handle_serviceAdded.accept(interfaceClass, service);
	}

	/**
	 * Notifies this plugin that service has been removed from the
	 *   plugin tool.
	 * Plugins should override this method if they update their state
	 * when a particular service is removed.
	 *
	 * @param interfaceClass The <b>interface</b> of the added service
	 * @param service that is being removed.
	 */
	@Override
	public void serviceRemoved(Class<?> interfaceClass, Object service) {
		handle_serviceRemoved.accept(interfaceClass, service);
	}

	/**
	 * Called to force this plugin to terminate any tasks it has running and
	 * apply any unsaved data to domain objects or files. If it can't do
	 * this or the user cancels then this returns false.
	 * @return true if this plugin can close.
	 */
	protected boolean canClose() {
		return handle_canClose.getAsBoolean();
	}

	/**
	 * Override this method if the plugin needs to cancel the closing of the domain object
	 * @param dObj the domain object
	 * @return false if the domain object should NOT be closed
	 */
	protected boolean canCloseDomainObject(DomainObject dObj) {
		return handle_canCloseDomainObject.test(dObj);
	}

	/**
	 * Called to allow this plugin to flush any caches to the domain object before it is
	 * saved.
	 * @param dObj domain object about to be saved
	 */
	protected void prepareToSave(DomainObject dObj) {
		handle_prepareToSave.accept(dObj);
	}

	/**
	 * Called to force this plugin to save any domain object data it is controlling.
	 * @return false if this plugin controls a domain object, but couldn't
	 * save its data or the user canceled the save.
	 */
	protected boolean saveData() {
		return handle_saveData.getAsBoolean();
	}

	/**
	 * Returns true if this plugin has data that needs saving;
	 * @return true if this plugin has data that needs saving;
	 */
	protected boolean hasUnsaveData() {
		return handle_hasUnsaveData.getAsBoolean();
	}

	/**
	 * Close the plugin.   This is when the plugin should release resources, such as those from
	 * other services.  This method should not close resources being used by others (that should
	 * happen in dispose()).
	 *
	 * <p>This method will be called before {@link #dispose()}.
	 */
	protected void close() {
		super.close();
		handle_close.run();
	}

	/**
	 * Provides the transient state object that was returned in the corresponding getTransientState()
	 * call.  Plugins should override this method if they have state that needs to be saved as domain objects
	 * get switched between active and inactive.
	 * @param state the state object that was generated by this plugin's getTransientState() method.
	 */
	public void restoreTransientState(Object state) {
		handle_restoreTransientState.accept(state);
	}

	/**
	 * Returns an object containing the plugins state.  Plugins should override this method if
	 * they have state that they want to maintain between domain object state transitions (i.e. when the
	 * user tabs to a different domain object and back) Whatever object is returned will be fed back to
	 * the plugin after the tool state is switch back to the domain object that was active when the this
	 * method was called.
	 * @return Object to be return in the restoreTransientState() method.
	 */
	public Object getTransientState() {
		return handle_getTransientState.get();
	}

	/**
	 * Notification that all plugins have had their data states restored.
	 */
	public void dataStateRestoreCompleted() {
		handle_dataStateRestoreCompleted.run();
	}

	/**
	 * Returns an object containing the plugin's state as needed to restore itself after an undo
	 * or redo operation.  Plugins should override this method if they have special undo/redo handling.
	 * @param domainObject the object that is about to or has had undoable changes made to it.
	 * @return the state object
	 */
	public Object getUndoRedoState(DomainObject domainObject) {
		// do nothing by default; subclasses should override as needed
		return handle_getUndoRedoState.apply(domainObject);
	}

	/**
	 * Updates the plugin's state based on the data stored in the state object.  The state object
	 * is the object that was returned by this plugin in the {@link #getUndoRedoState(DomainObject)}
	 * @param domainObject the domain object that has had an undo or redo operation applied to it.
	 * @param state the state that was recorded before the undo or redo operation.
	 */
	public void restoreUndoRedoState(DomainObject domainObject, Object state) {
		handle_restoreUndoRedoState.accept(domainObject, state);
	}
}
