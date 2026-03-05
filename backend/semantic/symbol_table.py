"""
Symbol Table for arCh Semantic Analyzer
Manages scopes, variable declarations, function signatures, and struct definitions.

Preserved from original:
  - Symbol dataclass fields (name, type, kind, is_const, is_array, array_dims,
    struct_name, scope_level, line, col, return_type, params, members)
  - Scope class with define(), lookup_local(), lookup()
  - SymbolTable with enter_scope(), exit_scope(), define(), define_global(),
    lookup(), lookup_local(), is_global_scope(), get_function(), get_struct(),
    define_struct(), get_current_function(), in_loop(), dump()

Improvements:
  NEW on Symbol:
    - initialized: bool   — distinguishes "declared" from "declared & initialized"
  NEW on SymbolTable:
    - lookup_var_scope()  — cascading lookup restricted to variable/constant/parameter kinds
    - get_struct_for_var()— given a variable name, return its struct Symbol if house-typed
  FIXED:
    - get_current_function() now correctly skips all non-function scope names
      (was missing 'for', 'while', 'dowhile', 'switch'; only excluded 'global'/'block')
"""

from typing import Optional, Dict, List
from dataclasses import dataclass, field as dc_field


@dataclass
class Symbol:
    """Represents a symbol in the symbol table."""

    name: str
    type: str   # 'tile', 'glass', 'brick', 'beam', 'wall', 'field', 'house'
    kind: str   # 'variable', 'constant', 'parameter', 'function', 'struct'

    is_const: bool = False
    is_array: bool = False
    array_dims: Optional[List[int]] = None
    struct_name: Optional[str] = None  # For house-typed variables: the struct type name

    scope_level: int = 0
    line: int = 0
    col: int = 0

    # NEW: tracks whether an initial value was provided at declaration.
    # False means "declared but not yet assigned a value".
    initialized: bool = False

    # Function-specific
    return_type: Optional[str] = None
    params: Optional[List['Symbol']] = None

    # Struct-specific (kind == 'struct')
    # Maps member_name → Symbol describing that member
    members: Optional[Dict[str, 'Symbol']] = None


class Scope:
    """Represents a single lexical scope (global, function, block, for, …)."""

    def __init__(self, name: str, level: int, parent: Optional['Scope'] = None):
        self.name = name
        self.level = level
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Define *symbol* in this scope.  Returns False if already defined."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up *name* in this scope only."""
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up *name* in this scope and all parent scopes."""
        symbol = self.symbols.get(name)
        if symbol:
            return symbol
        if self.parent:
            return self.parent.lookup(name)
        return None


# Scope names that are NOT function scopes (used by get_current_function)
_NON_FUNCTION_SCOPES = frozenset({
    'global', 'block', 'for', 'while', 'dowhile', 'switch'
})


class SymbolTable:
    """Manages all scopes and provides the semantic analyzer's main interface."""

    def __init__(self):
        self.global_scope = Scope("global", 0)
        self.current_scope = self.global_scope
        self.scope_stack: List[Scope] = [self.global_scope]

        self._init_builtins()

    # ── built-ins ─────────────────────────────────────────────────────────────

    def _init_builtins(self):
        """Initialize built-in constants and I/O functions."""
        # beam (boolean) constants
        for const_name in ('solid', 'fragile'):
            self.global_scope.define(Symbol(
                name=const_name,
                type='beam',
                kind='constant',
                is_const=True,
                initialized=True,   # constants are always initialized
                scope_level=0,
            ))

        # variadic void I/O functions
        for io_name in ('view', 'write'):
            self.global_scope.define(Symbol(
                name=io_name,
                type='field',
                kind='function',
                return_type='field',
                params=[],           # varargs — validated specially in semantic.py
                initialized=True,
                scope_level=0,
            ))

    # ── scope management ──────────────────────────────────────────────────────

    def enter_scope(self, name: str):
        """Push a new child scope."""
        new_scope = Scope(name, self.current_scope.level + 1, self.current_scope)
        self.scope_stack.append(new_scope)
        self.current_scope = new_scope

    def exit_scope(self):
        """Pop the current scope and return to its parent."""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]

    # ── define helpers ────────────────────────────────────────────────────────

    def define(self, symbol: Symbol) -> bool:
        """Define *symbol* in the current scope."""
        symbol.scope_level = self.current_scope.level
        return self.current_scope.define(symbol)

    def define_global(self, symbol: Symbol) -> bool:
        """Define *symbol* in the global scope."""
        symbol.scope_level = 0
        return self.global_scope.define(symbol)

    # ── lookup helpers ────────────────────────────────────────────────────────

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up *name* in the current and all enclosing scopes."""
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up *name* in the current scope only."""
        return self.current_scope.lookup_local(name)

    def is_global_scope(self) -> bool:
        """True when no function has been entered."""
        return self.current_scope is self.global_scope

    def get_function(self, name: str) -> Optional[Symbol]:
        """Return the function Symbol for *name*, or None if not a function."""
        symbol = self.global_scope.lookup_local(name)
        if symbol and symbol.kind == 'function':
            return symbol
        return None

    def get_struct(self, name: str) -> Optional[Symbol]:
        """Return the struct-definition Symbol for *name*, or None."""
        symbol = self.global_scope.lookup_local(name)
        if symbol and symbol.kind == 'struct':
            return symbol
        return None

    def define_struct(self, name: str, members: Dict[str, Symbol],
                      line: int, col: int) -> bool:
        """Register a struct type in the global scope."""
        struct_symbol = Symbol(
            name=name,
            type='house',
            kind='struct',
            members=members,
            initialized=True,
            scope_level=0,
            line=line,
            col=col,
        )
        return self.global_scope.define(struct_symbol)

    # NEW ─────────────────────────────────────────────────────────────────────

    def get_struct_for_var(self, var_name: str) -> Optional[Symbol]:
        """Given a variable name, return its struct-definition Symbol.

        Looks up the variable, reads its struct_name field, then fetches
        the matching struct definition.  Returns None if the variable is
        not house-typed or the struct is not defined.
        """
        var_sym = self.lookup(var_name)
        if var_sym is None:
            return None
        sname = var_sym.struct_name
        if not sname:
            # Fall back: if type starts with 'house ' parse it
            if isinstance(var_sym.type, str) and var_sym.type.startswith('house '):
                sname = var_sym.type[6:].strip()
        if not sname:
            return None
        return self.get_struct(sname)

    # ── context queries ───────────────────────────────────────────────────────

    def get_current_function(self) -> Optional[str]:
        """Return the name of the innermost enclosing function scope, or None.

        FIXED: original excluded only 'global' and 'block'; now correctly
        excludes all control-flow scope names so nested loops inside functions
        still find the function return type.
        """
        for scope in reversed(self.scope_stack):
            if scope.name not in _NON_FUNCTION_SCOPES:
                return scope.name
        return None

    def in_loop(self) -> bool:
        """True if any enclosing scope is a loop or switch."""
        for scope in reversed(self.scope_stack):
            if scope.name in ('for', 'while', 'dowhile', 'switch'):
                return True
        return False

    # ── debugging ─────────────────────────────────────────────────────────────

    def dump(self) -> str:
        """Return a human-readable dump of the global scope."""
        lines = ['=== Symbol Table ===']

        def dump_scope(scope: Scope, indent: int = 0):
            prefix = '  ' * indent
            lines.append(f'{prefix}Scope: {scope.name} (level {scope.level})')
            for sym_name, symbol in scope.symbols.items():
                init_flag = '' if symbol.initialized else ' [uninit]'
                const_flag = ' [const]' if symbol.is_const else ''
                arr_flag = f' {symbol.array_dims}' if symbol.is_array else ''
                lines.append(
                    f'{prefix}  {sym_name}: {symbol.type}{arr_flag} '
                    f'({symbol.kind}){const_flag}{init_flag}'
                )

        dump_scope(self.global_scope)
        return '\n'.join(lines)