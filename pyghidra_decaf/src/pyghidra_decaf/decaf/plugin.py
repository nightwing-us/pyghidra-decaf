# Standard Libraries
import logging
import re
from typing import (
    Any,
    Callable,
    cast,
    List,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

# Third Party Libraries
from docking.action import DockingAction
from ghidra.framework.model import DomainObject
from ghidra.framework.options import SaveState
from ghidra.framework.plugintool import (  # type: ignore[attr-defined]
    PluginEvent,
    PluginTool,
)
from ghidra.framework.plugintool.util import PluginDescription
from ghidra.program.model.address import (
    Address,
    AddressSetView,
)
from ghidra.program.model.listing import (
    CodeUnit,
    Program,
)
from ghidra.program.util import (
    ProgramLocation,
    ProgramSelection,
)
from ghidra.util import Msg
from java.lang import (  # type: ignore[import-not-found]
    Runnable,
)
from java.util.function import (  # type: ignore[import-not-found]
    BiConsumer,
    BooleanSupplier,
    Consumer,
    Function,
    Predicate,
    Supplier,
)
from jpype import (  # type: ignore[import-untyped]
    JClass,
    JObject,
)

from ._jpype_utils import (
    _get_private_class,
    _set_field,
)


if TYPE_CHECKING:
    # Our Libraries
    from pyghidra_decaf.stubs.jplugin import DecafPlugin as JDecafPlugin
    from pyghidra_decaf.stubs.jplugin import DecafProgramPlugin as JDecafProgramPlugin


logger = logging.getLogger(__name__)


class DecafPlugin:
    """
    The Python side DecafPlugin
    """

    _WORD_PATTERN = re.compile(
        r'.*?([\w\.]+)\Z'
    )  # get the last word, including '.', from the right

    def __init__(
        self,
        plugin: 'JDecafPlugin',
        plugin_base: str = 'pyghidra_decaf.jplugin.DecafPlugin',
    ):
        if hasattr(self, '_plugin'):
            # this gets entered twice for some reason
            return
        self._plugin = plugin

        self._docking_actions: List[DockingAction] = []
        try:
            plugin_cls = _get_private_class(plugin_base)
        except Exception as e:
            Msg.error('DecafProgramPlugin', e)
            return

        _set_field(plugin_cls, 'finalizer', Runnable @ self.dispose, plugin)
        _set_field(
            plugin_cls, 'handle_processEvent', Consumer @ self.process_event, plugin
        )
        _set_field(
            plugin_cls,
            'handle_readConfigState',
            Consumer @ self.read_config_state,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_writeConfigState',
            Consumer @ self.write_config_state,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_writeDataState',
            Consumer @ self.write_data_state,
            plugin,
        )
        _set_field(
            plugin_cls, 'handle_readDataState', Consumer @ self.read_data_state, plugin
        )
        _set_field(
            plugin_cls, 'handle_serviceAdded', BiConsumer @ self.service_added, plugin
        )
        _set_field(
            plugin_cls,
            'handle_serviceRemoved',
            BiConsumer @ self.service_removed,
            plugin,
        )
        _set_field(
            plugin_cls, 'handle_canClose', BooleanSupplier @ self._can_close, plugin
        )
        _set_field(
            plugin_cls,
            'handle_canCloseDomainObject',
            Predicate @ self._can_close_domain_object,
            plugin,
        )
        _set_field(
            plugin_cls, 'handle_prepareToSave', Consumer @ self._prepare_to_save, plugin
        )
        _set_field(
            plugin_cls, 'handle_saveData', BooleanSupplier @ self._save_data, plugin
        )
        _set_field(
            plugin_cls,
            'handle_hasUnsaveData',
            BooleanSupplier @ self._has_unsaved_data,
            plugin,
        )
        _set_field(plugin_cls, 'handle_close', Runnable @ self._close, plugin)
        _set_field(
            plugin_cls,
            'handle_restoreTransientState',
            Consumer @ self.restore_transient_state,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_getTransientState',
            Supplier @ self.get_transient_state,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_dataStateRestoreCompleted',
            Runnable @ self.data_state_restore_completed,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_getUndoRedoState',
            Function @ self.get_undo_redo_state,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_restoreUndoRedoState',
            BiConsumer @ self.restore_undo_redo_state,
            plugin,
        )

    def dispose(self) -> None:
        """
        Release the plugin resources
        """
        if self._docking_actions is not None:
            for action in self._docking_actions:  # type: ignore[unreachable]
                action.dispose()

    def process_event(self, event: PluginEvent) -> None: ...

    def read_config_state(self, saveState: SaveState) -> None: ...

    def write_config_state(self, saveState: SaveState) -> None: ...

    def read_data_state(self, saveState: SaveState) -> None: ...

    def write_data_state(self, saveState: SaveState) -> None: ...

    def service_added(self, interface_Class: JClass, service: JObject) -> None: ...

    def service_removed(self, interface_Class: JClass, service: JObject) -> None: ...

    def _can_close(self) -> bool:
        return True

    def _can_close_domain_object(self, dObj: DomainObject) -> bool:
        return True

    def _prepare_to_save(self, obj: DomainObject) -> None: ...

    def _save_data(self) -> bool:
        return True

    def _has_unsaved_data(self) -> bool:
        return False

    def _close(self) -> None: ...

    def restore_transient_state(self, state: Any) -> None: ...

    def get_transient_state(self) -> Any:
        return None

    def data_state_restore_completed(self) -> None: ...

    def get_undo_redo_state(self, domain_object: DomainObject) -> Any: ...

    def restore_undo_redo_state(
        self, domain_object: DomainObject, state: Any
    ) -> None: ...

    @property
    def name(self) -> str:
        return str(self._plugin.getName())

    @property
    def tool(self) -> PluginTool:
        return self._plugin.getTool()

    @property
    def description(self) -> PluginDescription:
        return self._plugin.getPluginDescription()


class DecafProgramPlugin(DecafPlugin):
    def __init__(self, plugin: 'JDecafProgramPlugin'):
        super().__init__(plugin, 'pyghidra_decaf.jplugin.DecafProgramPlugin')

        plugin_cls = _get_private_class('pyghidra_decaf.jplugin.DecafProgramPlugin')

        # set programplugin handlers
        _set_field(
            plugin_cls,
            'handle_programActivated',
            Consumer @ self._program_activated,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_postProgramActivated',
            Consumer @ self._post_program_activated,
            plugin,
        )
        _set_field(
            plugin_cls, 'handle_programClosed', Consumer @ self._program_closed, plugin
        )
        _set_field(
            plugin_cls, 'handle_programOpened', Consumer @ self._program_opened, plugin
        )
        _set_field(
            plugin_cls,
            'handle_programDeactivated',
            Consumer @ self._program_deactivated,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_locationChanged',
            Consumer @ self._location_changed,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_selectionChanged',
            Consumer @ self._selection_changed,
            plugin,
        )
        _set_field(
            plugin_cls,
            'handle_highlightChanged',
            Consumer @ self._highlight_changed,
            plugin,
        )

    def _program_activated(self, program: Program) -> None: ...

    def _post_program_activated(self, program: Program) -> None: ...

    def _program_closed(self, program: Program) -> None: ...

    def _program_opened(self, program: Program) -> None: ...

    def _program_deactivated(self, program: Program) -> None: ...

    def _location_changed(self, loc: ProgramLocation) -> None: ...

    def _selection_changed(self, sel: ProgramSelection) -> None: ...

    def _highlight_changed(self, hl: ProgramSelection) -> None: ...

    def goto(self, addr: Union[int, Address]) -> bool:
        if isinstance(addr, int):
            addr = self.program.getAddressFactory().getAddress(str(hex(addr)))
        return cast(bool, self._plugin.goTo(addr))

    def goto_codeunit(self, codeunit: CodeUnit) -> bool:
        return self.goto(codeunit.getMinAddress())

    def set_selection(self, address_set: AddressSetView) -> None:
        self._plugin.setSelection(address_set)

    @property
    def program_location(self) -> ProgramLocation:
        return cast('JDecafProgramPlugin', self._plugin).getProgramLocation()

    @property
    def program(self) -> Program:
        return cast('JDecafProgramPlugin', self._plugin).getCurrentProgram()

    @property
    def program_selection(self) -> ProgramSelection:
        return cast('JDecafProgramPlugin', self._plugin).getProgramSelection()

    @property
    def program_highlight(self) -> ProgramSelection:
        return cast('JDecafProgramPlugin', self._plugin).getProgramHighlight()


DecafLoad = Callable[[], List[Tuple[str, Type[DecafPlugin]]]]
