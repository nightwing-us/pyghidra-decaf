# Third Party Libraries
# Explicit `as` re-exports (PEP 484) so consumers can
# `from pyghidra_decaf.stubs.docking import ComponentProvider`.
from docking import ComponentProvider as ComponentProvider
from docking import Tool as Tool

class DecafComponentProvider(ComponentProvider):
    def __init__(self, tool: Tool, name: str, owner: str) -> None: ...
