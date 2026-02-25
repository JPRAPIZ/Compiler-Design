"""
Symbol Table for arCh Semantic Analyzer
Manages scopes, variable declarations, function signatures, and struct definitions
"""

from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class Symbol:
    """Represents a symbol in the symbol table"""
    name: str
    type: str  # 'tile', 'glass', 'brick', 'beam', 'wall', 'field', 'house'
    kind: str  # 'variable', 'constant', 'parameter', 'function', 'struct'
    is_const: bool = False
    is_array: bool = False
    array_dims: List[int] = None
    struct_name: Optional[str] = None  # For house types
    scope_level: int = 0
    line: int = 0
    col: int = 0

    # Function-specific
    return_type: Optional[str] = None
    params: Optional[List['Symbol']] = None

    # Struct-specific
    members: Optional[Dict[str, 'Symbol']] = None


class Scope:
    """Represents a single scope (global, function, block)"""

    def __init__(self, name: str, level: int, parent: Optional['Scope'] = None):
        self.name = name
        self.level = level
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Define a symbol in this scope. Returns False if already defined."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up symbol in this scope only"""
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up symbol in this scope and parent scopes"""
        symbol = self.symbols.get(name)
        if symbol:
            return symbol
        if self.parent:
            return self.parent.lookup(name)
        return None


class SymbolTable:
    """Manages all scopes and symbol lookups"""

    def __init__(self):
        self.global_scope = Scope("global", 0)
        self.current_scope = self.global_scope
        self.scope_stack: List[Scope] = [self.global_scope]

        # Built-in types and special functions
        self._init_builtins()

    def _init_builtins(self):
        """Initialize built-in types and functions"""
        # Built-in constants
        self.global_scope.define(Symbol(
            name="solid",
            type="beam",
            kind="constant",
            is_const=True,
            scope_level=0
        ))

        self.global_scope.define(Symbol(
            name="fragile",
            type="beam",
            kind="constant",
            is_const=True,
            scope_level=0
        ))

        # Built-in I/O functions
        self.global_scope.define(Symbol(
            name="view",
            type="field",
            kind="function",
            return_type="field",
            params=[],  # Varargs
            scope_level=0
        ))

        self.global_scope.define(Symbol(
            name="write",
            type="field",
            kind="function",
            return_type="field",
            params=[],  # Varargs
            scope_level=0
        ))

    def enter_scope(self, name: str):
        """Enter a new scope"""
        new_scope = Scope(name, self.current_scope.level + 1, self.current_scope)
        self.scope_stack.append(new_scope)
        self.current_scope = new_scope

    def exit_scope(self):
        """Exit current scope"""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]

    def define(self, symbol: Symbol) -> bool:
        """Define symbol in current scope"""
        symbol.scope_level = self.current_scope.level
        return self.current_scope.define(symbol)

    def define_global(self, symbol: Symbol) -> bool:
        """Define symbol in global scope"""
        symbol.scope_level = 0
        return self.global_scope.define(symbol)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up symbol in current and parent scopes"""
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up symbol in current scope only"""
        return self.current_scope.lookup_local(name)

    def is_global_scope(self) -> bool:
        """Check if we're in global scope"""
        return self.current_scope == self.global_scope

    def get_function(self, name: str) -> Optional[Symbol]:
        """Get function symbol by name"""
        symbol = self.global_scope.lookup_local(name)
        if symbol and symbol.kind == "function":
            return symbol
        return None

    def get_struct(self, name: str) -> Optional[Symbol]:
        """Get struct definition by name"""
        symbol = self.global_scope.lookup_local(name)
        if symbol and symbol.kind == "struct":
            return symbol
        return None

    def define_struct(self, name: str, members: Dict[str, Symbol], line: int, col: int) -> bool:
        """Define a struct type in global scope"""
        struct_symbol = Symbol(
            name=name,
            type="house",
            kind="struct",
            members=members,
            scope_level=0,
            line=line,
            col=col
        )
        return self.global_scope.define(struct_symbol)

    def get_current_function(self) -> Optional[str]:
        """Get name of current function scope"""
        for scope in reversed(self.scope_stack):
            if scope.name != "global" and scope.name != "block":
                return scope.name
        return None

    def in_loop(self) -> bool:
        """Check if we're inside a loop scope"""
        for scope in reversed(self.scope_stack):
            if scope.name in ("for", "while", "dowhile", "switch"):
                return True
        return False

    def dump(self) -> str:
        """Dump symbol table for debugging"""
        lines = ["=== Symbol Table ==="]

        def dump_scope(scope: Scope, indent: int = 0):
            prefix = "  " * indent
            lines.append(f"{prefix}Scope: {scope.name} (level {scope.level})")
            for name, symbol in scope.symbols.items():
                lines.append(f"{prefix}  {name}: {symbol.type} ({symbol.kind})")

        dump_scope(self.global_scope)
        return "\n".join(lines)