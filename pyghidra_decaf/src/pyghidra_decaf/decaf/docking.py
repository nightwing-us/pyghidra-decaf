# Standard Libraries
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Our Libraries
    from pyghidra_decaf.stubs.docking import ComponentProvider as JComponentProvider


class ComponentProvider:
    def __init__(self, component: 'JComponentProvider'): ...
