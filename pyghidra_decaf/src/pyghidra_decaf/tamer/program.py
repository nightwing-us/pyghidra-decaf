# Standard Libraries
from abc import (
    ABC,
    abstractmethod,
)
from types import TracebackType
from typing import (
    Dict,
    List,
    Optional,
    Type,
)

# Third Party Libraries
from ghidra.app.decompiler import (
    ClangLine,
    DecompileOptions,
    DecompInterface,
)
from ghidra.app.decompiler.component import DecompilerUtils
from ghidra.program.database.data import DataTypeUtilities
from ghidra.program.database.symbol import CodeSymbol
from ghidra.program.flatapi import FlatProgramAPI
from ghidra.program.model.address import Address
from ghidra.program.model.data import (
    ArrayDataType,
    DataType,
    PointerDataType,
    CategoryPath,
)
from ghidra.program.model.listing import (
    CodeUnit,
    Function,
    Program,
    Variable,
)
from ghidra.program.model.pcode import (
    HighFunction,
    HighFunctionDBUtil,
    HighSymbol,
)
from ghidra.program.model.symbol import SourceType
from ghidra.util import Msg
from ghidra.util.task import DummyCancellableTaskMonitor
from pydantic import (
    BaseModel,
    Field,
)

# Our Libraries
from pyghidra_decaf.util import AtomicCounter


class GhidraTransactionContext:
    def __init__(self, program: Program, description: str):
        self._program = program
        self._description = description
        self._ref_count = AtomicCounter()
        self._txid: int | None = None
        self._error = False

    def _start_transaction(self) -> None:
        if self._txid is None:
            self._error = False
            self._ref_count.reset()
            self._txid = self._program.startTransaction(self._description)

    def _end_transaction(self) -> None:
        if self._txid is not None:
            self._program.endTransaction(self._txid, not self._error)
            self._txid = None

    def flag_error(self) -> None:
        self._error = True

    def acquire(self) -> None:
        if self._ref_count == 0:
            self._start_transaction()
        self._ref_count += 1

    def release(self) -> None:
        if self._ref_count == 0:
            raise RuntimeError('Release called more times than acquire')
        self._ref_count -= 1
        if self._ref_count == 0:
            self._end_transaction()

    def __enter__(self) -> 'Program':
        self.acquire()
        return self._program  # or self, if you prefer

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.release()


class GhidraNamedEntity(ABC):
    @abstractmethod
    def update(
        self, new_name: str, new_type: str = '', source_type: 'SourceType | None' = None
    ) -> None: ...


class GhidraVariable(GhidraNamedEntity):
    def __init__(
        self,
        function: 'DecompiledFunction',
        symbol: HighSymbol,
        var: Variable | None,
    ) -> None:
        # `var` is the low-level Variable that backs this high-level symbol.
        # It can be None when the decompiler created the symbol without a
        # matching entry in the function's variable table — common for
        # synthesized locals. Callers that need it must check has_variable
        # or handle the AttributeError raised by .source.
        self._function = function
        self._symbol = symbol
        self._variable: Variable | None = var

    def _get_data_type(self, type_name: str) -> 'DataType':
        if '[' in type_name and ']' in type_name:
            c_type, rem = type_name.split('[', 1)
            is_array = True
        else:
            c_type = type_name
            rem = ''
            is_array = False

        # Check for pointer types
        is_pointer = c_type.rstrip().endswith('*')
        if is_pointer:
            base_type_name = c_type.rstrip().rstrip('*').rstrip()
        else:
            base_type_name = c_type

        # Try primitive type first
        sugg_type = DataTypeUtilities.getCPrimitiveDataType(
            base_type_name if is_pointer else c_type
        )

        # If not a primitive, look up in DataTypeManager
        if sugg_type is None:
            dtm = self._function.program.currentProgram.getDataTypeManager()
            # Try root category
            sugg_type = dtm.getDataType(CategoryPath('/'), base_type_name)
            # Try with leading slash
            if sugg_type is None:
                sugg_type = dtm.getDataType('/' + base_type_name)

        # Wrap in pointer if needed - use program's default pointer size
        if is_pointer and sugg_type is not None:
            dtm = self._function.program.currentProgram.getDataTypeManager()
            ptr_size = dtm.getDataOrganization().getPointerSize()
            sugg_type = PointerDataType(sugg_type, ptr_size)
        if is_array:
            count_str = rem.split(']', 1)[0]
            try:
                count = int(count_str)
            except ValueError:
                raise ValueError(
                    f'[LM]: Error parsing array length from type: {type_name}',
                )
            else:
                sugg_type = ArrayDataType(
                    sugg_type,
                    count,
                    self._function.program.currentProgram.getDataTypeManager(),
                )
        # Note: we intentionally do NOT check if sizes match. The Ghidra
        # decompiler handles size-mismatched type changes (e.g., int -> SomeStruct*)
        # through HighFunctionDBUtil.updateDBVariable. A strict size check here
        # would block legitimate operations like changing a local int to a
        # struct pointer (4 bytes -> 8 bytes on x64).
        return sugg_type

    @property
    def comment(self) -> str:
        db_var = self._function._ghidra_vars.get(self.name, None)
        if db_var:
            return db_var.getComment()
        return ''

    @property
    def name(self) -> str:
        return self._symbol.getName()

    @property
    def type(self) -> DataType:
        return self._symbol.getDataType()

    @property
    def size(self) -> int:
        return self._symbol.getSize()

    @property
    def has_variable(self) -> bool:
        """True if this symbol has a backing low-level Variable."""
        return self._variable is not None

    @property
    def source(self) -> SourceType:
        if self._variable is None:
            raise AttributeError(
                f'GhidraVariable {self.name!r} has no backing low-level '
                'Variable; SourceType is unavailable. Check has_variable first.'
            )
        return self._variable.getSource()

    def update(
        self, new_name: str, new_type: str = '', source_type: SourceType | None = None
    ) -> None:
        HighFunctionDBUtil.updateDBVariable(
            self._symbol,
            new_name,
            self._get_data_type(new_type) if new_type else None,  # type: ignore[arg-type]
            source_type if source_type is not None else SourceType.USER_DEFINED,
        )


class GhidraParameter(GhidraVariable):
    def __init__(
        self,
        function: 'DecompiledFunction',
        index: int,
        parameter: HighSymbol,
        var: Variable | None,
    ) -> None:
        super().__init__(function, parameter, var)
        self._index = index

    @property
    def index(self) -> int:
        return self._index


class GhidraString(BaseModel):
    address: int = Field(...)
    content: str


class CodeLabel(GhidraNamedEntity):
    def __init__(self, symbol: CodeSymbol, index: int) -> None:
        self._symbol = symbol
        self._index = index

    @property
    def name(self) -> str:
        return str(self._symbol.getName())

    @property
    def source(self) -> SourceType:
        return self._symbol.getSource()

    @property
    def comment(self) -> str:
        cu = self._symbol.program.getListing().getCodeUnitAt(self._symbol.address)
        return str(cu.getComment(CodeUnit.PRE_COMMENT))  # type: ignore[call-overload, arg-type]

    @comment.setter
    def comment(self, comment: str) -> None:
        cu = self._symbol.program.getListing().getCodeUnitAt(self._symbol.address)
        cu.setComment(CodeUnit.PRE_COMMENT, comment)  # type: ignore[call-overload, arg-type]

    @property
    def symbol(self) -> CodeSymbol:
        return self._symbol

    @property
    def offset(self) -> int:
        return int(self._symbol.address.offset)

    @property
    def index(self) -> int:
        return int(self._index)

    def update(
        self, new_name: str, new_type: str = '', source_type: SourceType | None = None
    ) -> None:
        self._symbol.setName(
            new_name,
            source_type if source_type is not None else SourceType.USER_DEFINED,
        )


class DecompiledFunction:
    def __init__(self, program: FlatProgramAPI, function: Function) -> None:
        self._program = program
        self.function = function
        self._decompiler = DecompInterface()  # type: ignore[no-untyped-call]
        self._decompiler.setOptions(DecompileOptions())  # type: ignore[no-untyped-call]
        self._decompiler.openProgram(function.program)
        self._dec_result = self._decompiler.decompileFunction(
            function,
            30,
            DummyCancellableTaskMonitor(),  # type: ignore[no-untyped-call]
        )
        self._dec_func = self._dec_result.getDecompiledFunction()
        self._vars_loaded = False
        self._ghidra_vars: Dict[str, Variable] = {}
        self._labels: Dict[str, CodeLabel] = {}
        self._params: Dict[str, GhidraParameter] = {}
        self._locals: Dict[str, GhidraVariable] = {}
        self._globals: Dict[str, GhidraVariable] = {}
        self._strings: Dict[str, GhidraString] = {}

    @property
    def program(self) -> FlatProgramAPI:
        return self._program

    @property
    def name(self) -> str:
        return str(self.function.name)

    @property
    def entrypoint(self) -> str:
        return f'{self.function.entryPoint.offset:#x}'

    @property
    def signature(self) -> str:
        return str(self._dec_func.getSignature())

    @property
    def c_code(self) -> str:
        return str(self._dec_func.getC())

    @property
    def high_function(self) -> HighFunction:
        return self._dec_result.getHighFunction()

    def get_parameter(self, name: str) -> Optional[GhidraParameter]:
        if not self._vars_loaded:
            self._load_vars()

        return self._params.get(name, None)

    def get_local_variable(self, name: str) -> Optional[GhidraVariable]:
        if not self._vars_loaded:
            self._load_vars()

        return self._locals.get(name, None)

    def get_global_variable(self, name: str) -> Optional[GhidraVariable]:
        if not self._vars_loaded:
            self._load_vars()

        return self._globals.get(name, None)

    def get_symbol(self, name: str) -> GhidraNamedEntity | None:
        """Look up a named entity in this function's symbol scope.

        Searches params, locals, globals, then labels. Returns None when
        no matching symbol exists in any scope — callers must handle that
        case (e.g. a rename target that doesn't yet exist).
        """
        if not self._vars_loaded:
            self._load_vars()

        symbol: GhidraNamedEntity | None = self._params.get(name, None)
        if symbol is None:
            symbol = self._locals.get(name, None)
        if symbol is None:
            symbol = self._globals.get(name, None)
        if symbol is None:
            symbol = self._labels.get(name, None)
        return symbol

    def _load_vars(self) -> None:
        if self._vars_loaded:
            return
        high_func = self._dec_result.getHighFunction()
        func_proto = high_func.getFunctionPrototype()

        self._ghidra_vars = {
            var.getName(): var for var in self.function.getAllVariables()
        }

        for idx in range(0, func_proto.getNumParams()):
            param = func_proto.getParam(idx)
            param_name = param.getName()
            self._params[param_name] = GhidraParameter(
                self, idx, param, self._ghidra_vars.get(param_name, None)
            )
        for sym in list(high_func.localSymbolMap.symbols):
            if sym.getName() not in self._params:
                self._locals[sym.getName()] = GhidraVariable(
                    self, sym, self._ghidra_vars.get(sym.getName(), None)
                )
        for sym in list(high_func.globalSymbolMap.symbols):
            self._globals[sym.getName()] = GhidraVariable(
                self, sym, self._ghidra_vars.get(sym.getName(), None)
            )

        end_addr = self.function.getBody().getMaxAddress()
        pos = self.function.getBody().getMinAddress()
        c_code = self._dec_func.getC()

        while pos <= end_addr:
            sym = self.function.program.getSymbolTable().getPrimarySymbol(pos)
            if isinstance(sym, CodeSymbol) and sym.getName() in c_code:
                lbl = CodeLabel(sym, len(self._labels) - 1)
                self._labels[str(sym.getName())] = lbl

            pos = pos.next()

        self._vars_loaded = True

    def add_pre_comment_at_c_line(self, c_line_number: int, text: str) -> int:
        root = self._dec_result.getCCodeMarkup()
        lines: List[ClangLine] = DecompilerUtils.toLines(root)
        if c_line_number - 1 < 0 or c_line_number >= len(lines):
            # If c_line_number outside of the range of 1-len(lines) we force it to line 1
            c_line_number = 1
        addr: Address | None = None
        commented_line = 1
        for idx, line in enumerate(lines):
            if line.getLineNumber() >= c_line_number - 1:
                addr = self._addr_for_line(line)
                if addr:
                    commented_line = line.getLineNumber() + 1
                    break
                # if the line doesn't map to an address, we continue to the next line until one resolves to an address

        if not addr:
            Msg.info(
                'add_pre_comment_at_c_line',
                'Could not find line, falling back to function address',
            )
            addr = self.function.getEntryPoint()
            commented_line = 1
        self._program.currentProgram.getListing().setComment(
            addr,
            CodeUnit.PRE_COMMENT,  # type: ignore[arg-type]
            text,
        )
        return commented_line

    def _addr_for_line(self, line: ClangLine) -> Address | None:
        # Prefer a token that already maps to an instruction address
        Msg.info(self.function, f'Getting address for line {line}')
        for tok in line.getAllTokens():
            Msg.info(self.function, f'Examining token {tok}')
            a = tok.getMinAddress()
            if a is not None:
                return a
            op = tok.getPcodeOp()
            if op is not None:
                seq = op.getSeqnum()
                if seq is not None:
                    a2 = seq.getTarget()  # Address (not int)
                    if a2 is not None:
                        return a2
        # As a last resort, ask for the closest address around any token
        for tok in line.getAllTokens():
            a3 = DecompilerUtils.getClosestAddress(self._program.currentProgram, tok)
            if a3 is not None:
                return a3
        return None
