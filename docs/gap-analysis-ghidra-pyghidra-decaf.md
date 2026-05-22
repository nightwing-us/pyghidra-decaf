# Gap Analysis: Ghidra Java Plugins vs PyGhidra vs PyGhidra Decaf

**Scope:** Extension point coverage and capability comparison across three plugin development approaches.

---

## Executive Summary

**The Core Problem:** Ghidra discovers plugins at startup via bytecode scanning (`ClassSearcher`), not runtime reflection. Vanilla PyGhidra's JPype proxies are invisible to this discovery mechanism—you cannot register Python classes as plugins, analyzers, loaders, or exporters.

**Decaf's Solution:** A two-phase system that (1) **generates minimal Java stub classes** from Python metadata during setup, and (2) **injects Python callables** into those stubs at runtime via JPype reflection. This allows pure-Python wheel distributions to provide full plugin lifecycle callbacks (`init()`, `disposed()`, `programActivated()`, etc.), service registration, event filtering, and lifecycle state persistence—all without authoring a line of Java.

**Outcome:** Decaf closes the gap for `Plugin` and `ProgramPlugin` extension points, enabling production-ready Python-based plugins with lifecycle semantics equivalent to hand-written Java. However, it does **not** extend to `Analyzer`, `Loader`, `Exporter`, `GFileSystem`, and other extension points that require different discovery mechanisms or custom Java shims per type.

---

## The Fundamental Constraint

**Why PyGhidra Alone Cannot Register Plugins:**

Ghidra's plugin discovery (`ghidra.util.classfinder.ClassSearcher`) operates at JVM startup by scanning the classpath for `.class` bytecode files annotated with `@PluginInfo`. The scanner reads annotations from compiled bytecode—a static, filesystem-based operation that completes before any Python code runs. JPype runtime proxies (created by `pyghidra.start()` or `pyhidra.start()`) are pure Python objects with zero bytecode presence on disk. `ClassSearcher` cannot see them because:

1. **No `.class` artifact:** JPype proxies are Python callables wrapping JVM object references; they have no compiled form on the filesystem.
2. **Annotation scanning is bytecode-level:** The discovery mechanism uses bytecode introspection (Java reflection on `.class` files), not runtime method/class inspection.
3. **Startup ordering:** Plugin discovery runs in Ghidra's bootstrap sequence, before any Python code or `pyghidra.start()` invocation.

---

## How PyGhidra Decaf Closes the Gap

### Phase 1: Java Code Generation (Setup Time)

**File:** `decaf_setup.py:177–280`

When a user installs a Decaf plugin wheel, the `decaf_setup()` function is invoked as a pyghidra entry point (`pyghidra.setup`). This function:

1. **Discovers plugin metadata** by loading all `decaf.init` entry points from installed wheels. Each returns a `DecafExtensionInfo` containing `DecafPluginInfo` entries.
2. **Renders Java source code** using a template (`plugin_java_template`, lines 105–174) that generates a minimal Java stub class extending `DecafPlugin` or `DecafProgramPlugin`.
3. **Emits bytecode** by invoking Ghidra's in-process Java compiler (`javax.tools.JavaCompiler`) on the generated source.
4. **Registers as extension** by creating `extension.properties` and `Module.manifest` in `~/.config/ghidra/<version>/Extensions/`, making the compiled jar discoverable by `ClassSearcher` on the next JVM iteration.

**Template mechanics:** The generated stub contains:
- Full `@PluginInfo` annotation with all user-supplied metadata (status, category, services, events).
- A static `initializer` field of type `Consumer<PluginClass>` (a Java functional interface).
- An `init()` method that invokes `initializer.accept(this)`, passing the Java stub instance to Python.
- No actual plugin logic—only a bridge to Python.

### Phase 2: Reflection-Based Runtime Binding (Load Time)

**File:** `decaf/pyghidra_decaf.py:57–122`

After the JVM starts and Ghidra's plugin system instantiates the generated stub classes, the `decaf_load()` function is invoked as a pyghidra entry point (`pyghidra.pre_launch`). This function:

1. **Discovers plugin classes** by loading all `decaf.load` entry points from installed wheels. Each returns a list of `(fully_qualified_name, DecafPlugin_subclass)` tuples.
2. **Binds Python callables to Java stubs** by:
   - Locating the compiled Java class (e.g., `myghidra_plugin.plugin.MyProgramPlugin`) via JPype class lookup.
   - Wrapping the Python class as a `Consumer<PluginClass>` via JPype's `@` operator (`@` creates a Java-compatible callable from a Python function).
   - Invoking the stub's static `setInitializer(Consumer)` method via reflection, storing the Python class as the initializer.

3. **Triggers instantiation** when Ghidra's plugin loader calls `init()` on the stub:
   - Stub's `init()` invokes `initializer.accept(java_stub)`.
   - JPype's `Consumer @` wrapper forwards the Java stub instance to the Python class constructor.
   - Python plugin instance is created with a reference to the Java stub.

### Phase 3: Lifecycle Delegation

**Files:** `java/DecafPlugin.java`, `java/DecafProgramPlugin.java`

The base Java classes define handler fields for every Ghidra plugin lifecycle method. When the Ghidra plugin system calls a hook (e.g., `init()`, `processEvent()`, `programActivated()`), the stub's override checks if a handler is set and delegates to Python. The Python `DecafPlugin` and `DecafProgramPlugin` base classes provide:

- **Plugin lifecycle:** `dispose()`, `processEvent()`, `readConfigState()`, `writeConfigState()`, `readDataState()`, `writeDataState()`, `canClose()`, `prepareToSave()`, `saveData()`, `service_added()`, `service_removed()`.
- **Program-specific lifecycle:** `_program_activated()`, `_program_closed()`, `_location_changed()`, `_selection_changed()`, `_highlight_changed()`.
- **State persistence:** config state (tool-scoped), data state (program-scoped), transient state (per-program UI state), undo/redo state.

---

## The Big Comparison Matrix

| **Capability / Extension Point** | **Ghidra (Java)** | **Vanilla PyGhidra** | **PyGhidra Decaf** | **Notes** |
|---|---|---|---|---|
| **Plugin** (base class) | ✅ Full | ❌ No | ✅ Full | Decaf: generated Java stub + Python base class |
| **ProgramPlugin** (program events) | ✅ Full | ❌ No | ✅ Full | Decaf: 8 callbacks (`programActivated`, `locationChanged`, etc.) |
| **Plugin Lifecycle Hooks** (`init`, `dispose`, `processEvent`, service callbacks) | ✅ All 20+ | ❌ No | ✅ All 20+ | Decaf: reflection-delegated through Java stubs |
| **@PluginInfo Metadata** (status, category, description, services, events, isSlowInstallation) | ✅ All fields | ❌ No | ✅ All fields | Decaf: embedded in generated Java template |
| **Service Registration** (`servicesProvided`, `servicesRequired`) | ✅ Full | ❌ No | ✅ Full | Decaf: metadata declares, reflection injects handlers |
| **Event Filtering** (`eventsConsumed`, `eventsProduced`) | ✅ Full | ❌ No | ✅ Full | Decaf: metadata declares, Ghidra router filters |
| **Custom PluginEvent Subclasses** | ✅ Java | ⚠️ `@JImplements` only | ⚠️ Needs Java shim | Decaf could codegen shim, not currently implemented |
| **Analyzer** (auto-analysis participation) | ✅ Full | ❌ No | ❌ No | Requires `AbstractAnalyzer` discovery; not yet supported by Decaf |
| **Loader** (new file formats) | ✅ Full | ❌ No | ❌ No | Requires `AbstractLibrarySupportLoader` discovery; not yet supported |
| **GFileSystem** (container/archive) | ✅ Full | ❌ No | ❌ No | Requires `AbstractFileSystem` discovery; not yet supported |
| **Exporter** | ✅ Full | ❌ No | ❌ No | Requires `AbstractExporter` discovery; not yet supported |
| **LanguageProvider** (SLEIGH injection) | ✅ Full | ❌ No | ❌ No | Requires `LanguageProvider` discovery; not yet supported |
| **Custom Java Code** in extension | ✅ Native | ⚠️ Via JPype | ✅ Full | Decaf: `java_source: List[Path]` in `DecafExtensionInfo` compiles alongside stubs |
| **ComponentProvider** (dockable panels) | ✅ Full | ⚠️ Possible via JPype | ⚠️ Stub only | `decaf/docking.py` is a placeholder; full implementation incomplete |
| **DockingAction** (menus, toolbars, key bindings) | ✅ Full | ⚠️ Via JPype `@JImplements` | ⚠️ Partial | Can instantiate via JPype; no dedicated Python wrapper yet |
| **FieldFactory** (custom listing columns) | ✅ Full | ❌ No | ❌ No | Requires `FieldFactory` discovery; not yet supported |
| **Tool Options** (persistent user preferences) | ✅ Full | ❌ No | ⚠️ Partial | Available via stub's `tool.getOptions()`; no Python convenience layer |
| **Background Tasks** (`Task`, `TaskMonitor`) | ✅ Full | ✅ Via JPype | ✅ Via JPype | All can instantiate; Decaf provides no wrapper |
| **Headless Mode** | ✅ Plugins work | ✅ Scripts work | ✅ Plugins work | Decaf plugins load in headless Ghidra via pyghidra startup |
| **Extension `.zip` Distribution** | ✅ Java jar + manifest | ❌ No | ✅ Pure-Python wheel | Decaf: stubs auto-generated; distribute as pip package |
| **GhidraScript** (one-off scripts) | ✅ Java/Jython/Python 3 | ✅ Python 3 | ⚠️ Out of scope | Scripts are separate from plugins; Decaf is plugin-focused |
| **REPL Access to Live Program** | ✅ Via console | ✅ Via `pyghidra.open_program()` | ✅ Via `pyghidra.open_program()` | Decaf doesn't restrict REPL; same as vanilla PyGhidra |
| **Subscribe to PluginEvent** (from within plugin) | ✅ `processEvent()` | ❌ No | ✅ `process_event()` | Decaf: declared in `@PluginInfo.eventsConsumed`, routed to Python method |
| **`@JImplements` Callback Interfaces** | n/a (Java) | ✅ Yes | ✅ Yes | Both can implement listener/callback interfaces |
| **Decompiler Integration** (p-code injection, callbacks) | ✅ Full | ⚠️ Via JPype | ✅ Via JPype | Can instantiate `InjectPayload` subclasses; Decaf provides no wrapper |
| **DataType Managers, FunctionID, BSim** | ✅ Full | ✅ Via JPype | ✅ Via JPype | Accessible via `program` API; Decaf provides no wrapper |

---

## Gaps PyGhidra Decaf Closes

**For pure-Python plugin development, Decaf enables:**

1. **Plugin lifecycle management** — Write a Python class inheriting from `DecafPlugin` or `DecafProgramPlugin`; all lifecycle callbacks (`init()`, `disposed()`, `programActivated()`, state persistence) are automatically wired via Java stubs. See `decaf/plugin.py` for the full callback hierarchy and `decaf_setup.py` for the generator template.
2. **Service and event metadata** — Declare services and events via `DecafPluginInfo` constructor arguments (`launch.py`); the generated Java `@PluginInfo` annotation automatically registers them with Ghidra.
3. **State persistence across tool session** — `readConfigState()` / `writeConfigState()` (tool-scoped) and `readDataState()` / `writeDataState()` (program-scoped) are hooked to Java's `SaveState` mechanism automatically via handler fields on `DecafPlugin.java`.
4. **Plugin distribution as pure-Python wheels** — No Java development; install via pip; `decaf_setup()` auto-generates bytecode on first launch (`bootstrap.py`, `decaf_setup.py`).
5. **Transient state (per-program UI state)** — `getTransientState()` / `restoreTransientState()` allow saving/restoring UI state when the user switches between programs.
6. **Undo/redo integration** — Python plugins can participate in Ghidra's undo/redo system via `getUndoRedoState()` / `restoreUndoRedoState()`.
7. **Docking action registration** — Can instantiate `DockingAction` via JPype and register it with the tool; `decaf/docking.py` provides a stub module and plugins can call `self.tool.addAction(action)` directly.
8. **Custom Java source shipping** — Include additional `.java` files in `DecafExtensionInfo.java_source`; `decaf_setup.py` copies them alongside generated stubs for compilation.
9. **Headless plugin execution** — Decaf plugins load and run during `analyzeHeadless` invocations via pyghidra's startup hooks.

---

## Gaps That Remain Open

### Architecturally Feasible (Codegen Pattern Extends)

1. **Analyzer** (`ghidra.app.services.Analyzer`)
   - **Why needed:** Participate in auto-analysis (fires when bytes/instructions/functions change).
   - **Current blocker:** No `DecafAnalyzer` base class or codegen template.
   - **Path to closure:** Generate `AbstractAnalyzer` subclass per Python class, following the same pattern as `DecafPlugin` → `DecafProgramPlugin`.

2. **Loader** (`ghidra.app.util.opinion.Loader`)
   - **Why needed:** Support new executable formats; participate in file import.
   - **Current blocker:** No `DecafLoader` base class or codegen template.
   - **Path to closure:** Generate `AbstractLibrarySupportLoader` subclass, template similar to plugin stubs.

3. **Exporter** (`ghidra.app.util.exporter.Exporter`)
   - **Why needed:** Export programs to custom file formats.
   - **Current blocker:** No `DecafExporter` base class or codegen template.
   - **Path to closure:** Generate `AbstractExporter` subclass.

4. **GFileSystem** (`ghidra.formats.gfilesystem.GFileSystem`)
   - **Why needed:** Support container/archive virtual filesystems.
   - **Current blocker:** No `DecafGFileSystem` base class; requires factory pattern.
   - **Path to closure:** Generate `AbstractFileSystem<T>` subclass + factory.

5. **FieldFactory** (`ghidra.app.util.viewer.field.FieldFactory`)
   - **Why needed:** Add custom columns to the Listing view.
   - **Current blocker:** No `DecafFieldFactory` base class or codegen template.
   - **Path to closure:** Codegen `FieldFactory` subclass; template must wire all abstract methods.

6. **Custom PluginEvent Subclasses**
   - **Why needed:** Publish/subscribe domain-specific events between plugins.
   - **Current blocker:** Codegen does not emit `PluginEvent` subclasses.
   - **Path to closure:** Add template for `PluginEvent` subclass generation in `decaf_setup.py`.

7. **ComponentProvider** (Dockable Panels)
   - **Why needed:** Create persistent dockable UI panels (e.g., analysis results, custom views).
   - **Current blocker:** `decaf/docking.py` is a stub; no Python base class or codegen.
   - **Path to closure:** Create `DecafComponentProvider` base class; codegen template similar to `DecafPlugin`.

### Hard Limits (JVM-Level Constraints)

1. **Single JVM per Process**
   - **Why it matters:** JPype cannot tear down and restart the JVM in-process. Once started, it stays running.
   - **Impact:** Each Decaf bootstrap iteration spawns a fresh subprocess (see `bootstrap.py`). This is by design.
   - **Mitigation:** Not fixable without replacing JPype; acceptable for plugin development (you don't restart JVM per use).

2. **Swing Thread Discipline**
   - **Why it matters:** All GUI code must run on Ghidra's event-dispatch thread; plugin code must not block.
   - **Impact:** Python code runs on EDT when called from plugin callbacks. Long operations must delegate to `tool.executeBackgroundCommand()` or spawn threads.
   - **Mitigation:** None required; same discipline as Java plugins. Decaf provides `GhidraTransactionContext` for safe program modification.

3. **JDK Pinning to Ghidra Version**
   - **Why it matters:** Ghidra 11.x targets JDK 17+. Extensions are compiled for specific Ghidra versions.
   - **Impact:** A Decaf plugin wheel built for Ghidra 11.2 will not load in Ghidra 11.3. Must rebuild per Ghidra release.
   - **Mitigation:** Ship `version=` in `extension.properties` matching the Ghidra install. Decaf does this automatically.

4. **Closed Extension Points**
   - The Ghidra Server protocol (`ghidraSvr`), headless analyzer command-line parser, and SLA file format are not pluggable.
   - **Impact:** Cannot extend these surfaces from Python or Decaf.

---

## Practical Recommendations

### Headless Reverse-Engineering Automation

**Best choice:** Vanilla PyGhidra with `pyghidra.open_program()` scripts.

- **Why:** No plugin lifecycle needed; one-off analysis in CPython.
- **Example:** Batch import + auto-analyze + extract function names → CSV.
- **Decaf overhead:** Unnecessary; a simple script is faster.

### One-Off Analysis Scripts in CPython

**Best choice:** PyGhidraScript (Python 3 via `PyGhidraScriptProvider`).

- **Why:** Tight integration with Ghidra GUI; access to `currentProgram`, `currentAddress`, `state` objects.
- **Decaf overhead:** Not needed; scripts have their own mechanism.

### Building a Redistributable Plugin with Menus/UI

**Best choice:** PyGhidra Decaf.

- **Why:** Full plugin lifecycle, persistent service registration, docking panel support (when ComponentProvider is complete), event subscriptions.
- **Example:** A custom analysis dashboard that shows results across multiple programs, persists window position, registers a menu item.
- **Distribution:** Ship as pip wheel; users run `pyghidra_decaf_bootstrap` once, then load Ghidra normally.

### Adding Support for a New File Format / ISA

**Best choice for loaders/exporters:** Decaf (once Loader/Exporter codegen is added) or hand-written Java.

- **Current:** Decaf does not yet support `Loader` codegen. You must write a Java `AbstractLibrarySupportLoader` subclass or wait for Decaf to extend the template.
- **Processor modules (SLEIGH):** Pure data-driven; ship `.slaspec`, `.cspec`, `.pspec` files; no plugin required. Decaf extensions can include these in `data/languages/`.

### Writing Analyzers Participating in Auto-Analysis

**Best choice:** Hand-written Java (for now) or wait for Decaf `Analyzer` support.

- **Current:** Decaf does not yet support `Analyzer` codegen.
- **Path:** Write a Java `AbstractAnalyzer` subclass. If you must use Python, instantiate it via JPype within a hand-written Java plugin that runs the Python analyzer.
- **Future:** Decaf will likely extend to `Analyzer` before `Loader`/`Exporter` (simpler discovery pattern).

---

## Open Questions / Future Work for PyGhidra Decaf

1. **Which extension point has highest ROI for codegen?** Analyzer? Loader? ComponentProvider? Survey users.
2. **Can Decaf emit PluginEvent subclass stubs?** Adding a second template to `decaf_setup.py` would unblock custom event types.
3. **Should Decaf provide Python wrappers for common Ghidra patterns?** E.g., `DockingAction` builder, `ComponentProvider` convenience class, `Task` runner.
4. **Can the bootstrap model be optimized?** The current multi-iteration loop works but is observable. Could one compilation pass handle all plugins?
5. **Should Decaf validate `@PluginInfo` metadata at setup time?** E.g., check that listed services/events are valid Java classes.
6. **How to version Decaf plugins against Ghidra releases?** Document the strategy; consider `extension.properties` version inference.
