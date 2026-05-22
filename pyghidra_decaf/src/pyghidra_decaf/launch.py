# Standard Libraries
from abc import (
    ABC,
    abstractmethod,
)
from enum import (
    auto,
    Enum,
)
from pathlib import Path
from typing import (
    Callable,
    List,
    NamedTuple,
    Tuple,
)


class DecafLauncher(ABC):
    @property
    @abstractmethod
    def extensions_path(self) -> Path: ...

    @property
    @abstractmethod
    def java_home(self) -> Path: ...

    @property
    @abstractmethod
    def ghidra_install_dir(self) -> Path: ...

    @abstractmethod
    def add_classpaths(self, *args: Path) -> None: ...


class PluginStatus(Enum):
    DEPRECATED = auto()
    HIDDEN = auto()
    RELEASED = auto()
    STABLE = auto()
    UNSTABLE = auto()


class PluginType(Enum):
    Plugin = auto()
    ProgramPlugin = auto()


class DecafPluginInfo(NamedTuple):
    type: PluginType
    qualname: str  # Fully qualified python class name (package.module.class_name)
    class_name: str  # Plugin class name
    status: PluginStatus  # Ghidra PluginInfo Plugin Status
    module_name: str  # Ghidra PluginInfo Package Name
    category: str  # Ghidra PluginInfo Category Name
    shortDescription: str  # Ghidra PluginInfo Short Description
    description: str  # Ghidra PluginInfo Description
    plugin_imports: Tuple[
        str, ...
    ] = ()  # Additional java imports needed (generally, for services/events)
    servicesProvided: List[str] = []
    servicesRequired: List[str] = []
    eventsConsumed: List[str] = []
    eventsProduced: List[str] = []
    isSlowInstallation: bool = False

    @property
    def python_fq_name(self) -> str:
        return f'{self.module_name}.{self.qualname}'


class DecafExtensionInfo(NamedTuple):
    name: str
    description: str
    author: str
    version: str  # Ghidra Version
    plugins: List[DecafPluginInfo]
    java_package: str = (
        ''  # prefix for java package. By default, python package will be used.
    )
    java_source: List[Path] = []


DecafSetup = Callable[[DecafLauncher], DecafExtensionInfo]
