# ===========================================================================
# symbol_table.py — Symbol Table and Scope Management
# ===========================================================================
#
# ROLE IN THE PIPELINE
# --------------------
# This file is the memory system of the semantic phase.  It answers three
# kinds of questions:
#   1. "Is this name defined in the current (or any enclosing) scope?"
#   2. "What type, kind, and attributes does this name have?"
#   3. "Are we inside a function?  Inside a loop?  At global scope?"
#
# The symbol table is created once at the start of SemanticAnalyzer.__init__
# and mutated throughout the traversal as scopes are opened and closed.
#
# DEPENDENCIES
# ------------
#   - Created and owned exclusively by semantic.py (SemanticAnalyzer).
#   - Does NOT import from ast.py or ast_builder.py.
#   - ast_builder.py has no knowledge of the symbol table; all registration
#     happens in semantic.py when it visits declaration nodes.
#
# SCOPE MODEL
# -----------
# Scopes are arranged in a parent-linked tree rooted at `global_scope`.
# The symbol table also maintains a `scope_stack` list for fast iteration
# (used by get_current_function and in_loop).
#
#   global_scope  (level 0)
#   └── function scope  (level 1, named after the function)
#       ├── block scope / for scope / while scope ...  (level 2+)
#       └── nested block scopes  (level 3+)
#
# Lookup walks up the parent chain; definition only touches the current scope.
#
# BUILT-IN SYMBOLS
# ----------------
# _init_builtins() pre-populates the global scope with:
#   solid, fragile — beam (boolean) constants.
#   view, write    — variadic void I/O functions (validated specially in
#                    semantic.py because their argument counts are flexible).
#
# ===========================================================================

from typing import Optional, Dict, List
from dataclasses import dataclass, field as dc_field


# ---------------------------------------------------------------------------
# Symbol — a single named entity in the program
# ---------------------------------------------------------------------------
# A Symbol is created whenever the semantic analyzer visits a declaration node
# (VarDeclNode, FunctionNode, ParamNode, StructDeclNode) and registers it via
# SymbolTable.define() or SymbolTable.define_global().

@dataclass
class Symbol:
    """Represents one declared name in the symbol table.

    Core attributes (set for all kinds)
    ------------------------------------
    name        — the identifier string.
    type        — the arCh type keyword: 'tile', 'glass', 'brick', 'beam',
                  'wall', 'field', or 'house'.  For struct-typed variables
                  this may be 'house StructName' (a compound string).
    kind        — one of: 'variable', 'constant', 'parameter', 'function',
                  'struct'.
    is_const    — True when declared with 'cement'.
    is_array    — True when an array declaration was seen.
    array_dims  — dimension sizes list, or None.
    struct_name — for 'house'-typed variables: the bare struct type name.
    scope_level — nesting depth (0 = global).
    line, col   — source location of the declaration.
    initialized — False means "declared but never assigned".  Checked by
                  the semantic analyzer before a variable is read.

    Function-specific (kind == 'function')
    ---------------------------------------
    return_type — the function's declared return type string.
    params      — ordered list of Symbol objects for each parameter.

    Struct-specific (kind == 'struct')
    ------------------------------------
    members     — dict mapping member_name → Symbol for each field.
                  Used by the semantic analyzer when resolving 'struct.member'
                  access expressions.
    """

    name: str
    type: str       # 'tile', 'glass', 'brick', 'beam', 'wall', 'field', 'house'
    kind: str       # 'variable', 'constant', 'parameter', 'function', 'struct'

    is_const: bool = False
    is_array: bool = False
    array_dims: Optional[List[int]] = None
    struct_name: Optional[str] = None

    scope_level: int = 0
    line: int = 0
    col: int = 0

    # Tracks whether an initial value was provided at declaration.
    # False means "declared but not yet assigned a value."
    # The semantic analyzer sets this to True when it processes the init_value
    # of a VarDeclNode, or when it sees an AssignNode targeting this variable.
    initialized: bool = False

    # Function-specific fields
    return_type: Optional[str] = None
    params: Optional[List['Symbol']] = None

    # Struct-specific field: maps member_name → Symbol for each struct field.
    members: Optional[Dict[str, 'Symbol']] = None


# ---------------------------------------------------------------------------
# Scope — one lexical scope in the nesting hierarchy
# ---------------------------------------------------------------------------
# A Scope is a dictionary of Symbol objects plus a reference to its parent.
# The SymbolTable manages the stack of active scopes; individual Scope objects
# do not know about the stack.

class Scope:
    """Represents a single lexical scope (global, function, block, for, …).

    Attributes
    ----------
    name    — human-readable label used for debugging and for get_current_function().
              Standard names: 'global', '<func_name>', 'block', 'for',
              'while', 'dowhile', 'switch'.
    level   — nesting depth (parent.level + 1).
    parent  — enclosing Scope, or None for the global scope.
    symbols — dict mapping identifier name → Symbol for this scope only.
    """

    def __init__(self, name: str, level: int, parent: Optional['Scope'] = None):
        self.name = name
        self.level = level
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Register symbol in this scope.

        Returns False (and does NOT overwrite) if the name is already defined
        in this same scope.  Duplicate detection is per-scope: shadowing an
        outer scope is allowed.
        """
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up name in THIS scope only (no parent traversal)."""
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up name in this scope and all parent scopes (chain walk).

        Returns the first Symbol found, which is the innermost definition.
        Returns None if the name is not defined anywhere in the chain.
        """
        symbol = self.symbols.get(name)
        if symbol:
            return symbol
        if self.parent:
            return self.parent.lookup(name)
        return None


# ---------------------------------------------------------------------------
# Non-function scope names — used by get_current_function()
# ---------------------------------------------------------------------------
# When searching the scope stack for the current function name, we skip any
# scope whose name appears in this set.  This ensures that a loop or block
# inside a function does not incorrectly masquerade as a function scope.

_NON_FUNCTION_SCOPES = frozenset({
    'global', 'block', 'for', 'while', 'dowhile', 'switch'
})


# ---------------------------------------------------------------------------
# SymbolTable — the main interface for the semantic analyzer
# ---------------------------------------------------------------------------
# The SymbolTable owns all Scope objects and exposes a clean API so the
# semantic analyzer never has to manipulate Scope objects directly.
#
# Typical usage pattern during semantic analysis:
#
#   symbol_table.enter_scope("my_function")
#       # visit parameter declarations → symbol_table.define(param_symbol)
#       # visit body statements        → symbol_table.define(local_symbol)
#       #                              → symbol_table.lookup(name)
#   symbol_table.exit_scope()

class SymbolTable:
    """Manages all lexical scopes and provides the SemanticAnalyzer's API.

    The global scope is pre-populated with built-in symbols by _init_builtins().
    """

    def __init__(self):
        self.global_scope = Scope("global", 0)
        self.current_scope = self.global_scope
        self.scope_stack: List[Scope] = [self.global_scope]

        self._init_builtins()

    # ── built-in symbol initialization ───────────────────────────────────────
    # Called once in __init__.  Inserts language-level constants and I/O
    # functions so the semantic analyzer can resolve them without special cases.

    def _init_builtins(self):
        """Pre-populate the global scope with built-in constants and I/O functions.

        Built-in constants
        ------------------
        solid, fragile — beam (boolean) literals.  Marked is_const=True and
                         initialized=True so they pass all semantic checks.

        Built-in I/O functions
        ----------------------
        view  — output function (like printf).  Declared with empty params list
                because it is variadic; the semantic analyzer validates argument
                types separately rather than checking against a fixed signature.
        write — input function (like scanf).  Same variadic treatment.
        Both have return_type='field' (void).
        """
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
                params=[],           # variadic — validated specially in semantic.py
                initialized=True,
                scope_level=0,
            ))

    # ── scope management ──────────────────────────────────────────────────────
    # The semantic analyzer calls enter_scope() at the start of every block
    # that introduces a new scope (functions, if-bodies, for-loops, etc.)
    # and exit_scope() when it finishes visiting that block.

    def enter_scope(self, name: str):
        """Push a new child scope named `name` onto the scope stack.

        The new scope's parent is the current scope so that lookup() can
        walk up the chain.
        """
        new_scope = Scope(name, self.current_scope.level + 1, self.current_scope)
        self.scope_stack.append(new_scope)
        self.current_scope = new_scope

    def exit_scope(self):
        """Pop the current scope and restore the parent as current.

        The global scope (index 0) is never popped.
        """
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]

    # ── symbol definition helpers ────────────────────────────────────────────
    # These are thin wrappers around Scope.define() that also set scope_level.

    def define(self, symbol: Symbol) -> bool:
        """Define symbol in the CURRENT scope.

        Returns False if the name is already defined in the current scope,
        which the semantic analyzer treats as a redefinition error.
        """
        symbol.scope_level = self.current_scope.level
        return self.current_scope.define(symbol)

    def define_global(self, symbol: Symbol) -> bool:
        """Define symbol in the GLOBAL scope.

        Used for function definitions and struct type registrations, which
        are always global regardless of where they lexically appear.
        """
        symbol.scope_level = 0
        return self.global_scope.define(symbol)

    # ── symbol lookup helpers ────────────────────────────────────────────────

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up name in the current scope and all enclosing scopes.

        Returns the innermost (most local) definition, or None.
        """
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up name in the CURRENT scope only.

        Used to detect duplicate declarations within the same scope.
        """
        return self.current_scope.lookup_local(name)

    def is_global_scope(self) -> bool:
        """Return True when no function scope has been entered.

        Used by the semantic analyzer to distinguish global-level statements
        (which are not allowed in most languages) from function-body statements.
        """
        return self.current_scope is self.global_scope

    # ── named entity retrieval ───────────────────────────────────────────────
    # These helpers provide type-safe access to specific kinds of symbols.
    # They always query the global scope because functions and struct types
    # are always defined globally.

    def get_function(self, name: str) -> Optional[Symbol]:
        """Return the Symbol for function `name`, or None if not a function."""
        symbol = self.global_scope.lookup_local(name)
        if symbol and symbol.kind == 'function':
            return symbol
        return None

    def get_struct(self, name: str) -> Optional[Symbol]:
        """Return the struct-definition Symbol for `name`, or None."""
        symbol = self.global_scope.lookup_local(name)
        if symbol and symbol.kind == 'struct':
            return symbol
        return None

    def define_struct(self, name: str, members: Dict[str, Symbol],
                      line: int, col: int) -> bool:
        """Register a struct type in the global scope.

        Creates a Symbol with kind='struct' and members dict, then inserts
        it into the global scope.  Returns False if the struct name is already
        defined (redefinition error).
        """
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

    def get_struct_for_var(self, var_name: str) -> Optional[Symbol]:
        """Resolve the struct-definition Symbol for a house-typed variable.

        Convenience helper used when visiting StructAccessNode:
          1. Look up the variable by name.
          2. Read its struct_name field (or parse it from the type string).
          3. Fetch the matching struct definition from the global scope.
        Returns None if the variable is not house-typed or the struct is
        not defined.
        """
        var_sym = self.lookup(var_name)
        if var_sym is None:
            return None
        sname = var_sym.struct_name
        if not sname:
            # Fallback: parse 'house StructName' from the type string
            if isinstance(var_sym.type, str) and var_sym.type.startswith('house '):
                sname = var_sym.type[6:].strip()
        if not sname:
            return None
        return self.get_struct(sname)

    # ── context query helpers ────────────────────────────────────────────────
    # These helpers let the semantic analyzer ask structural questions about
    # the current position in the scope stack without walking it manually.

    def get_current_function(self) -> Optional[str]:
        """Return the name of the innermost enclosing function scope.

        Walks the scope stack from innermost to outermost and returns the
        first scope name that is NOT in _NON_FUNCTION_SCOPES.
        This correctly handles loops and blocks nested inside functions:
        they do not interrupt the search for the enclosing function name.

        Returns None if no function scope is active (e.g., at global scope).

        Used by the semantic analyzer to check that a 'home' (return) statement
        returns the right type for the enclosing function.
        """
        for scope in reversed(self.scope_stack):
            if scope.name not in _NON_FUNCTION_SCOPES:
                return scope.name
        return None

    def in_loop(self) -> bool:
        """Return True if any enclosing scope is a loop or switch.

        Used to validate that 'crack' (break) and 'mend' (continue) only
        appear inside loops or switch statements.
        """
        for scope in reversed(self.scope_stack):
            if scope.name in ('for', 'while', 'dowhile', 'switch'):
                return True
        return False

    # ── debugging ─────────────────────────────────────────────────────────────

    def dump(self) -> str:
        """Return a human-readable dump of the global scope for debugging.

        Shows every symbol registered in the global scope with its type,
        kind, const flag, and initialization state.
        """
        lines = ['=== Symbol Table ===']

        def dump_scope(scope: Scope, indent: int = 0):
            prefix = '  ' * indent
            lines.append(f'{prefix}Scope: {scope.name} (level {scope.level})')
            for sym_name, symbol in scope.symbols.items():
                init_flag  = '' if symbol.initialized else ' [uninit]'
                const_flag = ' [const]' if symbol.is_const else ''
                arr_flag   = f' {symbol.array_dims}' if symbol.is_array else ''
                lines.append(
                    f'{prefix}  {sym_name}: {symbol.type}{arr_flag} '
                    f'({symbol.kind}){const_flag}{init_flag}'
                )

        dump_scope(self.global_scope)
        return '\n'.join(lines)