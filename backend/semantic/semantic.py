# ===========================================================================
# semantic.py — Semantic Analysis Phase
# ===========================================================================
#
# ROLE IN THE PIPELINE
# --------------------
# The SemanticAnalyzer is the third phase of the arCh compiler, running after:
#   1. Lexer      — produces a token list
#   2. Parser     — validates syntax, produces a validated token list
#   3. ASTBuilder — builds a ProgramNode tree from the token list   ← input here
#   4. SemanticAnalyzer                                              ← THIS FILE
#   5. TAC Generator (future)                                        ← output consumed here
#
# The semantic analyzer walks the AST produced by ASTBuilder and:
#   (a) Registers all declarations into the SymbolTable.
#   (b) Resolves all identifier references (undeclared variable detection).
#   (c) Checks type compatibility for assignments and expressions.
#   (d) Validates control-flow correctness (break/continue outside loops,
#       return type matching, etc.)
#   (e) Annotates every ExprNode with its resolved expr_type so the future
#       TAC generator knows what type each subexpression produces.
#
# DEPENDENCIES
# ------------
#   Reads:   ProgramNode tree from ast_builder.py / ast.py
#   Owns:    SymbolTable instance from symbol_table.py
#   Writes:  expr_type fields on all ExprNode subclasses in the AST
#
# DATA FLOW
# ---------
#   ProgramNode (from ASTBuilder)
#       │
#       ▼ analyze(program_node)
#   SemanticAnalyzer
#       ├── SymbolTable  (mutable state: scopes, symbol definitions)
#       ├── errors list  (accumulated SemanticError objects)
#       └── annotated AST (expr_type fields filled in on ExprNodes)
#       │
#       ▼
#   list[str]  — human-readable error messages, or empty list on success
#
# TRAVERSAL ORDER
# ---------------
# The analyzer performs TWO passes over the global-scope declarations:
#
#   Pass 1 — Register all struct definitions and function signatures.
#             This allows forward references: a function can call another
#             function defined later in the file.
#
#   Pass 2 — Analyze function bodies.
#             By this point all global names are in the symbol table.
#
# Within each function body, declarations and statements are visited
# in order (single pass), which means variables must be declared before use
# (no forward references for local variables).
#
# SCOPE MANAGEMENT SUMMARY
# ------------------------
#   ProgramNode            — no new scope (global scope is pre-existing)
#   FunctionNode           — enter_scope(func_name) … exit_scope()
#   IfNode then/else body  — enter_scope("block") … exit_scope()
#   WhileNode body         — enter_scope("while") … exit_scope()
#   DoWhileNode body       — enter_scope("dowhile") … exit_scope()
#   ForNode                — enter_scope("for") … exit_scope()
#                            (init variable is declared in this scope)
#   SwitchNode body        — enter_scope("switch") … exit_scope()
#
# ERROR REPORTING
# ---------------
# Errors are accumulated in self.errors as SemanticError objects.
# The analyzer does NOT stop at the first error; it continues to collect
# all errors so the programmer sees a complete report.
# At the end, get_errors() returns the list of formatted error strings.
#
# TAC READINESS
# -------------
# After a successful semantic pass, every ExprNode in the AST has its
# expr_type field set.  A TAC generator can:
#   - Use expr_type to determine what temporary variable type to allocate.
#   - Walk FunctionNode.body lists sequentially to emit TAC instructions.
#   - Use SymbolTable.dump() to inspect what names are globally known.
#
# ===========================================================================

from typing import Optional, List, Dict
from semantic.ast import (
    ProgramNode, FunctionNode, ParamNode,
    GlobalDeclNode, VarDeclNode, StructDeclNode, StructMemberNode,
    StatementNode, AssignNode, IfNode, WhileNode, DoWhileNode,
    ForNode, SwitchNode, CaseNode, BreakNode, ContinueNode,
    ReturnNode, IONode,
    ExprNode, BinaryOpNode, UnaryOpNode, LiteralNode,
    IdNode, ArrayAccessNode, StructAccessNode, FunctionCallNode,
    WallConcatNode, ArrayInitNode,
    TypeInfo, TYPE_ORDER, _CASTABLE_TYPES,
)
from semantic.symbol_table import SymbolTable, Symbol


# ---------------------------------------------------------------------------
# SemanticError — structured error representation
# ---------------------------------------------------------------------------

class SemanticError:
    """Holds one semantic error with its source location and message.

    Attributes
    ----------
    line    — source line number where the error was detected.
    col     — source column number.
    message — human-readable description of the error.
    """

    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.message = message
        self.line = line
        self.col = col

    def __str__(self):
        return f"Semantic Error at line {self.line}, col {self.col}: {self.message}"


# ---------------------------------------------------------------------------
# Helper: build a TypeInfo from a Symbol
# ---------------------------------------------------------------------------

def _type_info_from_symbol(sym: Symbol) -> TypeInfo:
    """Convert a Symbol into a TypeInfo for type-compatibility checks.

    Handles the 'house StructName' compound type string by splitting it
    into base_type='house' and struct_name='StructName'.
    """
    base = sym.type
    struct_name = sym.struct_name

    # Parse compound 'house StructName' strings
    if isinstance(base, str) and base.startswith("house "):
        struct_name = base[6:].strip()
        base = "house"

    return TypeInfo(
        base_type=base,
        is_array=sym.is_array,
        array_dims=sym.array_dims,
        struct_name=struct_name,
        is_const=sym.is_const,
    )


# ---------------------------------------------------------------------------
# SemanticAnalyzer
# ---------------------------------------------------------------------------

class SemanticAnalyzer:
    """Traverses the AST, enforces semantic rules, and annotates expression types.

    Usage
    -----
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(program_node)
        if errors:
            for e in errors:
                print(e)
        else:
            # AST is fully annotated; proceed to TAC generation
            symbol_table = analyzer.symbol_table
    """

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticError] = []

    # ── error helpers ─────────────────────────────────────────────────────────

    def _error(self, message: str, line: int = 0, col: int = 0):
        """Append one semantic error to the error list."""
        self.errors.append(SemanticError(message, line, col))

    def get_errors(self) -> List[dict]:
        """Return all accumulated errors as dicts with line, col, and message."""
        return [
            {
                "line":    e.line if e.line else 1,
                "col":     e.col  if e.col  else 1,
                "message": e.message,
            }
            for e in self.errors
        ]

    # ── public entry point ────────────────────────────────────────────────────

    def analyze(self, program: ProgramNode) -> List[dict]:
        """Run the full semantic analysis over the program AST.

        Returns a list of error dicts (empty list on success).
        Each dict has keys: "line", "col", "message".
        TAC generation must NOT run if this returns a non-empty list.
        """
        self._analyze_program(program)
        return self.get_errors()

    # -----------------------------------------------------------------------
    # Program-level analysis (two-pass)
    # -----------------------------------------------------------------------

    def _analyze_program(self, program: ProgramNode):
        """Analyze the root ProgramNode.

        Pass 1: Register all global declarations (structs, global variables,
                function signatures) into the global scope.
        Pass 2: Analyze each function body with all globals already visible.
        """
        # Pass 1 — register global declarations
        for decl in program.globals:
            self._register_global_decl(decl)

        # Pass 1 continued — register function signatures
        for func in program.functions:
            self._register_function_signature(func)

        # Pass 2 — analyze function bodies
        for func in program.functions:
            self._analyze_function(func)

    # ── Pass 1: global registration ──────────────────────────────────────────

    def _register_global_decl(self, decl: GlobalDeclNode):
        """Register one global declaration into the global scope.

        Handles VarDeclNode (global variables and constants) and
        StructDeclNode (struct type definitions).
        """
        if isinstance(decl, StructDeclNode):
            self._register_struct(decl)
        elif isinstance(decl, VarDeclNode):
            self._register_var_decl(decl, is_global=True)

    def _register_struct(self, decl: StructDeclNode):
        """Register a struct type definition in the global scope.

        Each struct member is stored as a Symbol in the members dict so that
        StructAccessNode resolution can look up field types directly.
        """
        members: Dict[str, Symbol] = {}
        for member in decl.members:
            # Spec G.8: struct members cannot initialize a value
            if hasattr(member, 'init_value') and member.init_value is not None:
                self._error(
                    f"Struct member '{member.name}' cannot have an initializer "
                    f"(spec G.8)",
                    member.line, member.col
                )
            mem_sym = Symbol(
                name=member.name,
                type=member.type,
                kind='variable',
                is_array=member.is_array,
                array_dims=member.array_dims,
                initialized=True,   # struct members are always "accessible"
                line=member.line,
                col=member.col,
            )
            if member.name in members:
                self._error(
                    f"Duplicate member '{member.name}' in struct '{decl.name}'",
                    member.line, member.col
                )
            else:
                members[member.name] = mem_sym

        ok = self.symbol_table.define_struct(decl.name, members,
                                             decl.line, decl.col)
        if not ok:
            self._error(f"Struct '{decl.name}' already defined",
                        decl.line, decl.col)

    def _register_function_signature(self, func: FunctionNode):
        """Register a function's signature (name, return type, params) globally.

        Parameters are stored as Symbol objects on the function Symbol so
        that call-site argument count and type checking can compare against them.
        """
        param_symbols: List[Symbol] = []
        for p in func.params:
            param_symbols.append(Symbol(
                name=p.name,
                type=p.type,
                kind='parameter',
                initialized=True,
                line=p.line,
                col=p.col,
            ))

        func_sym = Symbol(
            name=func.name,
            type=func.return_type,
            kind='function',
            return_type=func.return_type,
            params=param_symbols,
            initialized=True,
            line=func.line,
            col=func.col,
        )
        ok = self.symbol_table.define_global(func_sym)
        if not ok:
            self._error(f"Function '{func.name}' already defined",
                        func.line, func.col)

    # ── Pass 2: function body analysis ───────────────────────────────────────

    def _analyze_function(self, func: FunctionNode):
        """Analyze one function definition.

        Opens a scope named after the function, registers parameters as local
        symbols, then visits each item in the body.
        """
        # Spec I.11: blueprint (main) must not accept parameters
        if func.name == 'blueprint' and func.params:
            self._error(
                "blueprint() must not accept parameters",
                func.line, func.col
            )

        self.symbol_table.enter_scope(func.name)

        # Register parameters in the function's own scope
        for p in func.params:
            param_sym = Symbol(
                name=p.name,
                type=p.type,
                kind='parameter',
                initialized=True,
                line=p.line,
                col=p.col,
            )
            ok = self.symbol_table.define(param_sym)
            if not ok:
                self._error(
                    f"Duplicate parameter '{p.name}' in function '{func.name}'",
                    p.line, p.col
                )

        # Visit body items (declarations interleaved with statements)
        for item in func.body:
            self._analyze_body_item(item, func.return_type)

        # Check that non-field functions guarantee a return statement.
        # Spec H.9: A non-field sub-program must guarantee exactly one home
        # statement executes along all possible control paths.
        # Spec H.10: A field sub-program shouldn't have a return statement.
        if func.return_type != 'field':
            if not self._body_guarantees_return(func.body):
                self._error(
                    f"Function '{func.name}' has return type '{func.return_type}' "
                    f"but not all code paths return a value (missing 'home')",
                    func.line, func.col
                )

        self.symbol_table.exit_scope()

    # -----------------------------------------------------------------------
    # Return-path analysis
    # -----------------------------------------------------------------------

    def _body_guarantees_return(self, body: list) -> bool:
        """Check whether a statement list guarantees a return on all paths.

        This uses a conservative structural analysis:
          - A ReturnNode at the top level of the body guarantees return.
          - An IfNode with both then_body and else_body, where BOTH branches
            guarantee return, counts as a guaranteed return.
          - Anything else does not guarantee return.

        This is simpler than a full CFG but catches the most common cases:
          - Missing return entirely
          - Return only inside one branch of an if/else
        """
        if not body:
            return False

        for stmt in body:
            if isinstance(stmt, ReturnNode):
                return True
            if isinstance(stmt, IfNode):
                # Both branches must guarantee return
                if stmt.else_body:
                    then_returns = self._body_guarantees_return(stmt.then_body)
                    else_returns = self._body_guarantees_return(stmt.else_body)
                    if then_returns and else_returns:
                        return True

        return False

    # -----------------------------------------------------------------------
    # Body item dispatch (declarations and statements)
    # -----------------------------------------------------------------------

    def _analyze_body_item(self, node, enclosing_return_type: str):
        """Dispatch one body item to the appropriate analysis method."""
        if isinstance(node, VarDeclNode):
            self._analyze_var_decl(node)
        elif isinstance(node, AssignNode):
            self._analyze_assign(node)
        elif isinstance(node, IfNode):
            self._analyze_if(node, enclosing_return_type)
        elif isinstance(node, WhileNode):
            self._analyze_while(node, enclosing_return_type)
        elif isinstance(node, DoWhileNode):
            self._analyze_dowhile(node, enclosing_return_type)
        elif isinstance(node, ForNode):
            self._analyze_for(node, enclosing_return_type)
        elif isinstance(node, SwitchNode):
            self._analyze_switch(node, enclosing_return_type)
        elif isinstance(node, BreakNode):
            self._analyze_break(node)
        elif isinstance(node, ContinueNode):
            self._analyze_continue(node)
        elif isinstance(node, ReturnNode):
            self._analyze_return(node, enclosing_return_type)
        elif isinstance(node, IONode):
            self._analyze_io(node)
        elif isinstance(node, FunctionCallNode):
            # Standalone function call statement (return value discarded)
            self._analyze_expr(node)
        elif isinstance(node, UnaryOpNode):
            # Postfix/prefix ++ or -- used as a statement
            self._analyze_expr(node)
        # Other node types are silently skipped (should not occur in valid ASTs)

    # -----------------------------------------------------------------------
    # Declaration analysis
    # -----------------------------------------------------------------------

    def _register_var_decl(self, decl: VarDeclNode, is_global: bool = False):
        """Register a VarDeclNode in the current (or global) scope.

        Used for both global and local variable/constant declarations.
        The 'initialized' flag on the Symbol is set to True only when
        an init_value expression is present, with two exceptions:

        Spec F.9/F.11 — Arrays with a fixed size receive default values
        automatically (tile=0, glass=0.0, wall="", brick=\\0, beam=fragile).
        They are always considered initialized even without an explicit
        brace initializer.

        Spec G.11 — Structure variables are implicitly initialized when
        declared.  Each member receives the default value for its type
        (tile=0, glass=0.0, etc.) so that member accesses like s1.x are
        valid even without an explicit = {...} initializer.  This matches
        the C behaviour where struct variables have indeterminate but
        accessible storage, and arCh always default-initializes.
        """
        # Determine initial initialization state
        has_init = decl.init_value is not None

        # Spec F.9/F.11: Arrays declared with a fixed size get default values
        # automatically (tile=0, glass=0.0, wall="", brick=\0, beam=fragile).
        # They are always considered initialized even without an explicit
        # brace initializer.
        if decl.is_array:
            has_init = True

        # Parse struct_name for house-typed variables
        struct_name = decl.struct_type_name
        base_type = decl.type
        if isinstance(base_type, str) and base_type.startswith("house "):
            struct_name = base_type[6:].strip()
            base_type = "house"

        # Spec G.11: Structure variables are implicitly initialized.
        # A declaration like `house Student s1;` creates s1 with all members
        # set to their type defaults.  The variable is therefore immediately
        # usable — accessing s1.scores[0] or s1.name is valid without an
        # explicit = {...} initializer.
        if base_type == "house":
            has_init = True

        sym = Symbol(
            name=decl.name,
            type=base_type,
            kind='constant' if decl.is_const else 'variable',
            is_const=decl.is_const,
            is_array=decl.is_array,
            array_dims=decl.array_dims,
            struct_name=struct_name,
            initialized=has_init,
            line=decl.line,
            col=decl.col,
        )

        if is_global:
            ok = self.symbol_table.define_global(sym)
        else:
            ok = self.symbol_table.define(sym)

        if not ok:
            self._error(f"Variable '{decl.name}' already declared in this scope",
                        decl.line, decl.col)

    def _analyze_var_decl(self, decl: VarDeclNode):
        """Analyze a local variable declaration.

        Steps:
          1. Analyze the initializer expression (if present) and check its type.
          2. Register the variable in the current scope.
        """
        init_type: Optional[str] = None

        if decl.init_value is not None:
            # Struct brace initializers use a sentinel — skip type-checking
            is_struct_type = (isinstance(decl.type, str) and
                              decl.type.startswith("house"))

            # Array brace initializers (ArrayInitNode) — analyze element
            # types but skip the scalar type-compatibility check
            is_array_init = isinstance(decl.init_value, ArrayInitNode)

            if is_struct_type:
                pass  # no type-checking for struct brace inits
            elif is_array_init:
                # Analyze each element for type errors, but don't compare
                # against the array's declared type since ArrayInitNode
                # carries multiple values, not a single scalar type
                self._analyze_expr(decl.init_value)
            else:
                init_type = self._analyze_expr(decl.init_value)

                # Type-check: initializer must be compatible with declared type
                if init_type is not None:
                    decl_ti = TypeInfo(
                        base_type=decl.type,
                        is_array=decl.is_array,
                        array_dims=decl.array_dims,
                        struct_name=decl.struct_type_name,
                    )
                    init_ti = TypeInfo(base_type=init_type)
                    if not init_ti.can_cast_to(decl_ti):
                        self._error(
                            f"Cannot initialise '{decl.name}' (type '{decl.type}') "
                            f"with value of type '{init_type}'",
                            decl.line, decl.col
                        )

        # Spec rule E.2 / E.11 / J.8: constant variables must always be initialized.
        if decl.is_const and decl.init_value is None:
            self._error(
                f"Constant '{decl.name}' must be initialized at declaration",
                decl.line, decl.col
            )

        self._register_var_decl(decl, is_global=False)

    # -----------------------------------------------------------------------
    # Statement analysis
    # -----------------------------------------------------------------------

    def _analyze_assign(self, node: AssignNode):
        """Analyze an assignment statement: target op= value.

        Steps:
          1. Validate that the LHS is a valid assignment target (spec K.3 §2).
          2. Resolve the target (LHS) to get its type.
          3. Check that the target is not a constant (cement).
          4. Analyze the RHS expression.
          5. Check type compatibility between LHS and RHS.
          6. Mark the target symbol as initialized.
        """
        # Spec K.3 §2: LHS must be a variable, array element, or struct member
        from semantic.ast import FunctionCallNode as _FCallNode, LiteralNode as _LitNode
        if isinstance(node.target, (_FCallNode, _LitNode)):
            self._error(
                "Invalid assignment target: left-hand side must be a variable, "
                "array element, or structure member",
                node.line, node.col
            )
            return

        lhs_type = self._resolve_lhs_type(node.target)
        rhs_type = self._analyze_expr(node.value)

        # Annotate target expr_type so TAC generator can emit conversion info
        if lhs_type is not None and hasattr(node.target, 'expr_type'):
            node.target.expr_type = lhs_type

        # Const-assignment check
        self._check_not_const(node.target, node.line, node.col)

        # Type compatibility
        if lhs_type is not None and rhs_type is not None:
            lhs_ti = TypeInfo(base_type=lhs_type)
            rhs_ti = TypeInfo(base_type=rhs_type)
            if not rhs_ti.can_cast_to(lhs_ti):
                self._error(
                    f"Cannot assign type '{rhs_type}' to type '{lhs_type}'",
                    node.line, node.col
                )

        # Mark the target variable as initialized
        self._mark_initialized(node.target)

    def _analyze_if(self, node: IfNode, return_type: str):
        """Analyze an if/else statement."""
        cond_type = self._analyze_expr(node.condition)
        # TODO: Warn if condition is not a beam (boolean) type.
        #       Currently, any numeric type is accepted silently.

        self.symbol_table.enter_scope("block")
        for item in node.then_body:
            self._analyze_body_item(item, return_type)
        self.symbol_table.exit_scope()

        if node.else_body is not None:
            self.symbol_table.enter_scope("block")
            for item in node.else_body:
                self._analyze_body_item(item, return_type)
            self.symbol_table.exit_scope()

    def _analyze_while(self, node: WhileNode, return_type: str):
        """Analyze a while loop."""
        self._analyze_expr(node.condition)
        # TODO: Warn if condition is not a beam type.

        self.symbol_table.enter_scope("while")
        for item in node.body:
            self._analyze_body_item(item, return_type)
        self.symbol_table.exit_scope()

    def _analyze_dowhile(self, node: DoWhileNode, return_type: str):
        """Analyze a do-while loop."""
        self.symbol_table.enter_scope("dowhile")
        for item in node.body:
            self._analyze_body_item(item, return_type)
        self.symbol_table.exit_scope()

        self._analyze_expr(node.condition)
        # TODO: Warn if condition is not a beam type.

    def _analyze_for(self, node: ForNode, return_type: str):
        """Analyze a for loop.

        The for-init variable is declared in the for scope so it does not
        leak into the enclosing scope.
        """
        self.symbol_table.enter_scope("for")

        if node.init is not None:
            if isinstance(node.init, VarDeclNode):
                self._analyze_var_decl(node.init)
            elif isinstance(node.init, AssignNode):
                self._analyze_assign(node.init)

        self._analyze_expr(node.condition)
        self._analyze_expr(node.increment)

        for item in node.body:
            self._analyze_body_item(item, return_type)

        self.symbol_table.exit_scope()

    def _analyze_switch(self, node: SwitchNode, return_type: str):
        """Analyze a switch (room) statement."""
        switch_type = self._analyze_expr(node.expr)

        self.symbol_table.enter_scope("switch")
        for case in node.cases:
            if case.value is not None:
                case_type = self._analyze_expr(case.value)
                # TODO: Check that case_type is compatible with switch_type.
            for item in case.body:
                self._analyze_body_item(item, return_type)
        self.symbol_table.exit_scope()

    def _analyze_break(self, node: BreakNode):
        """Validate that 'crack' (break) is inside a loop or switch."""
        if not self.symbol_table.in_loop():
            self._error("'crack' (break) used outside a loop or switch",
                        node.line, node.col)

    def _analyze_continue(self, node: ContinueNode):
        """Validate that 'mend' (continue) is inside a loop."""
        if not self.symbol_table.in_loop():
            self._error("'mend' (continue) used outside a loop",
                        node.line, node.col)

    def _analyze_return(self, node: ReturnNode, enclosing_return_type: str):
        """Validate a 'home' (return) statement against the enclosing function type.

        Rules (spec H.9, H.10):
          - 'home;' (no value) is only valid in field (void) functions.
          - 'home expr;' is NOT valid in field functions (they must not return a value).
          - 'home expr;' value type must be compatible with the function's
            declared return type.
        """
        if node.value is None:
            # Bare return: only valid for void (field) functions
            if enclosing_return_type != 'field':
                self._error(
                    f"Function with return type '{enclosing_return_type}' "
                    f"must return a value",
                    node.line, node.col
                )
        else:
            ret_type = self._analyze_expr(node.value)
            # Spec H.10: field (void) function must not return a value
            if enclosing_return_type == 'field':
                self._error(
                    "field (void) function must not return a value",
                    node.line, node.col
                )
            elif ret_type is not None:
                ret_ti = TypeInfo(base_type=ret_type)
                exp_ti = TypeInfo(base_type=enclosing_return_type)
                if not ret_ti.can_cast_to(exp_ti):
                    self._error(
                        f"Return type mismatch: expected '{enclosing_return_type}', "
                        f"got '{ret_type}'",
                        node.line, node.col
                    )

    # Format specifier → compatible arCh types (spec K.2 §3)
    _FMT_SPEC_TYPES = {
        '#d': {'tile', 'beam'},
        '%d': {'tile', 'beam'},
        '#c': {'brick'},
        '%c': {'brick'},
        '#f': {'glass'},
        '%f': {'glass'},
        '#s': {'wall'},
        '%s': {'wall'},
        '#b': {'tile', 'beam'},
        '%b': {'tile', 'beam'},
    }

    def _extract_specifiers(self, fmt: str):
        """Return ordered list of format specifiers found in a format string."""
        import re
        return re.findall(r'[#%][dfcsb]', fmt)

    def _analyze_io(self, node: IONode):
        """Analyze a view() or write() I/O statement.

        Spec K.2 rules enforced:
          - write() must have at least one format specifier (§2).
          - Format specifiers must be compatible with argument types (§3, §4).
          - write() arguments are marked initialized (they are filled by input).

        Special case — Spec K.2 §13 / F.9:
          A brick array is a valid argument for the #s format specifier in a
          write statement.  The array name already represents the address, so
          the address-of operator (&) is not needed.  At runtime the input
          string is stored character-by-character into the brick array elements
          (e.g. chars[0]='H', chars[1]='e', …).
        """
        fmt = node.format_string or ""
        # Strip surrounding quotes from the format string for specifier scanning
        clean_fmt = fmt
        if clean_fmt.startswith('"') and clean_fmt.endswith('"'):
            clean_fmt = clean_fmt[1:-1]

        specs = self._extract_specifiers(clean_fmt)

        if node.io_type == 'write':
            # Spec K.2 §2: format string must contain at least one specifier
            if not specs:
                self._error(
                    "write() format string must contain at least one format specifier "
                    "(#d, #f, #c, #s)",
                    node.line, node.col
                )

            # write() fills its arguments — mark them initialized, then type-check.
            # For each argument we also record whether it is a brick array, since
            # brick arrays have a special exemption for #s (Spec K.2 §13).
            arg_types = []
            arg_is_brick_array = []   # parallel list: True when arg is brick[]
            for arg in node.args:
                if isinstance(arg, IdNode):
                    sym = self.symbol_table.lookup(arg.name)
                    if sym is not None:
                        sym.initialized = True
                        arg.expr_type = sym.type
                        arg_types.append(sym.type)
                        # Spec K.2 §13 / F.9: a bare brick array name used as
                        # a write() argument is eligible for #s input.
                        arg_is_brick_array.append(
                            sym.type == 'brick' and sym.is_array
                        )
                    else:
                        self._analyze_expr(arg)
                        arg_types.append(None)
                        arg_is_brick_array.append(False)
                else:
                    t = self._analyze_expr(arg)
                    arg_types.append(t)
                    arg_is_brick_array.append(False)

            # Spec K.2 §4: check specifier/type compatibility
            for i, (spec, arg_type) in enumerate(zip(specs, arg_types)):
                if arg_type is None:
                    continue

                # Spec K.2 §13 / F.9 exemption: #s with a brick array argument
                # is valid.  The runtime will read a wall (string) and store each
                # character into sequential brick array elements as ord(char).
                if spec in ('#s', '%s') and i < len(arg_is_brick_array) and arg_is_brick_array[i]:
                    continue   # allowed — skip the normal type check

                allowed = self._FMT_SPEC_TYPES.get(spec)
                if allowed and arg_type not in allowed:
                    self._error(
                        f"write() format specifier '{spec}' is not compatible "
                        f"with argument type '{arg_type}'",
                        node.line, node.col
                    )
        else:
            # view() — analyze all args normally
            arg_types = [self._analyze_expr(arg) for arg in node.args]

            # Spec K.2 §3 (output): check specifier/type compatibility
            for i, (spec, arg_type) in enumerate(zip(specs, arg_types)):
                if arg_type is None:
                    continue
                allowed = self._FMT_SPEC_TYPES.get(spec)
                if allowed and arg_type not in allowed:
                    self._error(
                        f"view() format specifier '{spec}' is not compatible "
                        f"with argument type '{arg_type}'",
                        node.line, node.col
                    )

    # -----------------------------------------------------------------------
    # Expression analysis and type resolution
    # -----------------------------------------------------------------------
    # All expression analysis methods return the resolved type string
    # (e.g. 'tile', 'glass', 'beam') or None if the type cannot be determined.
    # They also WRITE the resolved type back to node.expr_type so the TAC
    # generator can read it without re-running the analyzer.

    def _analyze_expr(self, node: ExprNode) -> Optional[str]:
        """Dispatch expression analysis and return the resolved type string."""
        if isinstance(node, LiteralNode):
            return self._analyze_literal(node)
        elif isinstance(node, IdNode):
            return self._analyze_id(node)
        elif isinstance(node, BinaryOpNode):
            return self._analyze_binary(node)
        elif isinstance(node, UnaryOpNode):
            return self._analyze_unary(node)
        elif isinstance(node, FunctionCallNode):
            return self._analyze_call(node)
        elif isinstance(node, ArrayAccessNode):
            return self._analyze_array_access(node)
        elif isinstance(node, StructAccessNode):
            return self._analyze_struct_access(node)
        elif isinstance(node, WallConcatNode):
            return self._analyze_wall_concat(node)
        elif isinstance(node, ArrayInitNode):
            return self._analyze_array_init(node)
        return None

    def _analyze_literal(self, node: LiteralNode) -> Optional[str]:
        """Literals already carry their type; just copy it to expr_type."""
        node.expr_type = node.literal_type
        return node.expr_type

    def _analyze_id(self, node: IdNode) -> Optional[str]:
        """Resolve an identifier to its declared type.

        Checks:
          - The name must be declared in the current or an enclosing scope.
          - The variable must have been initialized before use.
            (Constants and parameters are always initialized.)
        """
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            self._error(f"Undeclared identifier '{node.name}'",
                        node.line, node.col)
            return None

        if not sym.initialized and sym.kind not in ('constant', 'parameter',
                                                      'function', 'struct'):
            self._error(
                f"Variable '{node.name}' may be used before being initialized",
                node.line, node.col
            )

        # Normalize 'house StructName' type string to plain 'house'
        base = sym.type
        if isinstance(base, str) and base.startswith("house "):
            base = "house"

        node.expr_type = base
        return node.expr_type

    def _analyze_binary(self, node: BinaryOpNode) -> Optional[str]:
        """Resolve the type of a binary expression.

        For arithmetic operators (+, -, *, /, %):
          - Both operands must be numeric (in TYPE_ORDER).
          - Result type is the wider of the two operand types.

        For relational operators (<, <=, >, >=, ==, !=):
          - Both operands must be compatible (numeric or same type).
          - Result type is always 'beam' (boolean).

        For logical operators (&& and ||):
          - Both operands should be beam or numeric.
          - Result type is 'beam'.

        Special case: '+' with wall operands → wall concatenation.
          (This is handled at the AST level by WallConcatNode for explicit
           wall literals, but may reach here for id + id when both are wall.)
        """
        left_type = self._analyze_expr(node.left)
        right_type = self._analyze_expr(node.right)

        if left_type is None or right_type is None:
            node.expr_type = None
            return None

        op = node.operator

        # Wall concatenation via '+'
        if op == '+' and (left_type == 'wall' or right_type == 'wall'):
            if left_type != 'wall' or right_type != 'wall':
                self._error(
                    f"Cannot use '+' between 'wall' and non-wall type",
                    node.line, node.col
                )
            node.expr_type = 'wall'
            return 'wall'

        # Logical operators → beam result
        if op in ('&&', '||'):
            # TODO: Warn if operands are not beam type.
            node.expr_type = 'beam'
            return 'beam'

        # Relational operators → beam result
        if op in ('<', '<=', '>', '>=', '==', '!='):
            left_ti = TypeInfo(base_type=left_type)
            right_ti = TypeInfo(base_type=right_type)
            if not left_ti.can_cast_to(right_ti) and not right_ti.can_cast_to(left_ti):
                self._error(
                    f"Incompatible types in relational expression: "
                    f"'{left_type}' and '{right_type}'",
                    node.line, node.col
                )
            node.expr_type = 'beam'
            return 'beam'

        # Arithmetic operators (+, -, *, /, %)
        if op in ('+', '-', '*', '/', '%'):
            # Spec N.1 §10: modulus (%) only works on tile, brick, and beam.
            if op == '%' and left_type not in ('tile', 'brick', 'beam'):
                self._error(
                    f"Modulus '%' cannot be applied to type '{left_type}' "
                    f"(only tile, brick, beam allowed)",
                    node.line, node.col
                )
                node.expr_type = None
                return None
            if op == '%' and right_type not in ('tile', 'brick', 'beam'):
                self._error(
                    f"Modulus '%' cannot be applied to type '{right_type}' "
                    f"(only tile, brick, beam allowed)",
                    node.line, node.col
                )
                node.expr_type = None
                return None
            left_ti = TypeInfo(base_type=left_type)
            right_ti = TypeInfo(base_type=right_type)
            wider = left_ti.wider_numeric(right_ti)
            if wider is None:
                self._error(
                    f"Arithmetic operator '{op}' cannot be applied to types "
                    f"'{left_type}' and '{right_type}'",
                    node.line, node.col
                )
                node.expr_type = None
                return None
            node.expr_type = wider.base_type
            return node.expr_type

        # Unknown operator — propagate left type as a best-effort fallback
        node.expr_type = left_type
        return left_type

    def _analyze_unary(self, node: UnaryOpNode) -> Optional[str]:
        """Resolve the type of a unary expression.

        '-' (negation) — operand must be numeric; result is same type.
        '!'  (logical not) — result is beam.
        '++' / '--'      — operand must be numeric; result is same type.
                           Operand must also be an lvalue (IdNode or array access).
        """
        operand_type = self._analyze_expr(node.operand)

        if operand_type is None:
            node.expr_type = None
            return None

        op = node.operator

        if op == '!':
            # TODO: Warn if operand is not beam.
            node.expr_type = 'beam'
            return 'beam'

        if op in ('-', '++', '--'):
            if operand_type not in TYPE_ORDER:
                self._error(
                    f"Operator '{op}' cannot be applied to type '{operand_type}'",
                    node.line, node.col
                )
                node.expr_type = None
                return None
            if op in ('++', '--') and not isinstance(node.operand, (IdNode, ArrayAccessNode)):
                self._error(
                    f"Operator '{op}' requires a variable (lvalue)",
                    node.line, node.col
                )
            # Spec N.2 §11: ++ and -- cannot be applied to constants
            if op in ('++', '--') and isinstance(node.operand, IdNode):
                sym = self.symbol_table.lookup(node.operand.name)
                if sym and sym.is_const:
                    self._error(
                        f"Operator '{op}' cannot be applied to constant "
                        f"'{node.operand.name}'",
                        node.line, node.col
                    )
            node.expr_type = operand_type
            return operand_type

        node.expr_type = operand_type
        return operand_type

    def _analyze_call(self, node: FunctionCallNode) -> Optional[str]:
        """Validate a function call and return its return type.

        Checks:
          1. The function name must be declared in the global scope.
          2. Argument count must match (unless the function is variadic,
             i.e. view/write which have an empty params list as a sentinel).
          3. Argument types must be compatible with parameter types.

        The return type is written to node.expr_type.
        """
        func_sym = self.symbol_table.get_function(node.func_name)
        if func_sym is None:
            self._error(f"Undeclared function '{node.func_name}'",
                        node.line, node.col)
            node.expr_type = None
            return None

        # Analyze each argument expression
        arg_types = [self._analyze_expr(arg) for arg in node.args]

        # Variadic I/O functions (view / write) skip count/type checks
        is_variadic = node.func_name in ('view', 'write')

        if not is_variadic:
            expected_params = func_sym.params or []
            if len(node.args) != len(expected_params):
                self._error(
                    f"Function '{node.func_name}' expects "
                    f"{len(expected_params)} argument(s), "
                    f"got {len(node.args)}",
                    node.line, node.col
                )
            else:
                for i, (arg_type, param) in enumerate(
                        zip(arg_types, expected_params)):
                    if arg_type is None:
                        continue
                    arg_ti = TypeInfo(base_type=arg_type)
                    param_ti = TypeInfo(base_type=param.type)
                    if not arg_ti.can_cast_to(param_ti):
                        self._error(
                            f"Argument {i + 1} to '{node.func_name}': "
                            f"cannot pass '{arg_type}' as '{param.type}'",
                            node.line, node.col
                        )

        node.expr_type = func_sym.return_type
        return node.expr_type

    def _analyze_array_access(self, node: ArrayAccessNode) -> Optional[str]:
        """Resolve the element type of an array access expression.

        Checks:
          - The base expression must refer to an array variable.
          - Each index must be an integer (tile or brick) type.
          - Index count must not exceed the declared dimensions.

        Returns the array's ELEMENT type:
          - wall[i]  → brick   (a wall is a sequence of brick characters)
          - T[i]     → T       (element type equals the declared array base type)
        """
        base_type = self._analyze_expr(node.array)

        for idx in node.indices:
            idx_type = self._analyze_expr(idx)
            if idx_type is not None and idx_type not in ('tile', 'brick', 'beam'):
                self._error(
                    f"Array index must be an integer type, got '{idx_type}'",
                    node.line, node.col
                )

        # A wall is a sequence of brick characters; wall[i] yields brick.
        # All other array types return their own base type as the element type.
        if base_type == 'wall':
            elem_type = 'brick'
        else:
            elem_type = base_type

        node.expr_type = elem_type
        return elem_type

    def _analyze_struct_access(self, node: StructAccessNode) -> Optional[str]:
        """Resolve the type of a struct member access expression: struct.member.

        Steps:
          1. Resolve the base expression type (must be 'house').
          2. Look up the struct definition to find the member's type.
          3. Set node.expr_type to the member's type.
        """
        # Step 1: resolve base expression
        base_type = self._analyze_expr(node.struct)

        if base_type != 'house' and (base_type is None or
                not (isinstance(base_type, str) and base_type.startswith('house'))):
            self._error(
                f"Member access '.' applied to non-struct type '{base_type}'",
                node.line, node.col
            )
            node.expr_type = None
            return None

        # Step 2: locate the struct definition via the base IdNode name
        struct_def = None
        if isinstance(node.struct, IdNode):
            struct_def = self.symbol_table.get_struct_for_var(node.struct.name)

        if struct_def is None or struct_def.members is None:
            # TODO: Handle chained access (struct.field.subfield)
            node.expr_type = None
            return None

        # Step 3: look up the member
        member_sym = struct_def.members.get(node.member)
        if member_sym is None:
            self._error(
                f"Struct has no member '{node.member}'",
                node.line, node.col
            )
            node.expr_type = None
            return None

        node.expr_type = member_sym.type
        return node.expr_type

    def _analyze_wall_concat(self, node: WallConcatNode) -> Optional[str]:
        """Validate that all parts of a wall concatenation are wall-typed.

        Spec N.5: only wall+wall is valid.
        wall+brick, brick+brick, and any non-wall type are errors.
        """
        for part in node.parts:
            part_type = self._analyze_expr(part)
            if part_type is not None and part_type != 'wall':
                if part_type == 'brick':
                    self._error(
                        f"Cannot concatenate 'wall' with 'brick' (spec N.5 §6)",
                        node.line, node.col
                    )
                else:
                    self._error(
                        f"Wall concatenation operand has non-wall type '{part_type}'",
                        node.line, node.col
                    )
        node.expr_type = 'wall'
        return 'wall'

    def _analyze_array_init(self, node: ArrayInitNode) -> Optional[str]:
        """Analyze a brace-enclosed array initializer {v1, v2, ...}.

        Walks each element, resolves its type, and returns the common
        element type. For 2-D arrays (nested ArrayInitNode), recurses.
        """
        elem_type = None
        for elem in node.elements:
            t = self._analyze_expr(elem)
            if t is not None and elem_type is None:
                elem_type = t
        node.expr_type = elem_type
        return elem_type

    # -----------------------------------------------------------------------
    # LHS resolution helpers
    # -----------------------------------------------------------------------
    # These helpers resolve the type of an assignment target without going
    # through the full expression analyzer (which would also check initialization,
    # which is not yet true for the target before the assignment).

    def _resolve_lhs_type(self, target: ExprNode) -> Optional[str]:
        """Determine the type of an assignment target expression."""
        if isinstance(target, IdNode):
            sym = self.symbol_table.lookup(target.name)
            if sym:
                base = sym.type
                if isinstance(base, str) and base.startswith("house "):
                    base = "house"
                return base
            return None
        elif isinstance(target, ArrayAccessNode):
            return self._resolve_lhs_type(target.array)
        elif isinstance(target, StructAccessNode):
            return self._analyze_struct_access(target)
        return None

    def _check_not_const(self, target: ExprNode, line: int, col: int):
        """Emit an error if the assignment target is a declared constant.

        Spec E.8: cement (const) variables cannot be modified after
        initialization.  This rule applies to the variable itself AND to
        individual array elements or struct members of a cement variable:
          - cement tile nums[3] = {1,2,3};  nums[0] = 99;    ← error
          - cement house Pt p = {3,7};      p.x = 10;        ← error

        The check recurses through ArrayAccessNode and StructAccessNode to
        find the base IdNode and verify its const status.
        """
        if isinstance(target, IdNode):
            sym = self.symbol_table.lookup(target.name)
            if sym and sym.is_const:
                self._error(
                    f"Cannot assign to constant '{target.name}'",
                    line, col
                )
        elif isinstance(target, ArrayAccessNode):
            # Spec E.8: assigning to an element of a cement array (e.g.
            # nums[0] = 99) is forbidden.  Recurse into the base expression
            # to find the underlying identifier.
            self._check_not_const(target.array, line, col)
        elif isinstance(target, StructAccessNode):
            # Spec E.8: assigning to a member of a cement struct variable
            # (e.g. p.x = 10) is forbidden.  Recurse into the struct base.
            self._check_not_const(target.struct, line, col)

    def _mark_initialized(self, target: ExprNode):
        """Mark the target variable as initialized after an assignment.

        Only IdNode targets are tracked; array element and struct field
        assignments do not update the symbol's initialized flag because
        the whole array/struct is considered initialized at declaration time.
        """
        if isinstance(target, IdNode):
            sym = self.symbol_table.lookup(target.name)
            if sym:
                sym.initialized = True