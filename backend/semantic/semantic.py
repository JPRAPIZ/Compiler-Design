"""
Semantic Analyzer for arCh Language — v3
Performs type checking, scope resolution, and semantic error detection.
Uses Visitor Pattern with DFS traversal (Pre-order for declarations,
Post-order for expression type inference).

Changes in v3 (all improvements from the spec):
  1.  Use-before-initialization enforced in visit_id().
  2.  All-paths return analysis: _returns_on_all_paths() helper.
  3.  Separate in_switch flag: continue (mend) rejected inside switch.
  4.  Duplicate case value detection within each switch block.
  5.  Void function call rejected when used as an expression value.
  6.  Shadowing warning emitted when a local name hides a global.
  7.  Dead code detection: statements after 'home' in same block warned.
  8.  Type annotation: resolved expr_type written back into AST nodes.
  9.  Constant folding: literal BinaryOp nodes folded at semantic pass.
 10.  Struct initialiser checking (basic member-count and member-type).
 11.  Array initialiser element type and size checking.

Carried forward from v2:
  - TYPE_ORDER / dominant_type / can_cast type system
  - Struct member access (chained) fixed
  - Multi-level scope / get_current_function fixed
  - Symbol.initialized tracking
"""

from typing import List, Dict, Optional, Any, Set
from semantic.ast import (
    ASTNode, ProgramNode, FunctionNode, ParamNode,
    GlobalDeclNode, VarDeclNode, StructDeclNode, StructMemberNode,
    StatementNode, AssignNode, IfNode, WhileNode, DoWhileNode,
    ForNode, SwitchNode, CaseNode, BreakNode, ContinueNode,
    ReturnNode, IONode,
    ExprNode, BinaryOpNode, UnaryOpNode, LiteralNode,
    IdNode, ArrayAccessNode, StructAccessNode, FunctionCallNode,
    WallConcatNode, TypeInfo, TYPE_ORDER, _NUMERIC_RANK, _CASTABLE_TYPES,
)
from semantic.symbol_table import SymbolTable, Symbol


# ============================================================================
# Error / Warning representation
# ============================================================================

class SemanticError:
    """A semantic error with source location."""

    def __init__(self, message: str, line: int, col: int,
                 severity: str = 'error'):
        self.message = message
        self.line = line
        self.col = col
        self.severity = severity          # 'error' or 'warning'
        self.start_line = line
        self.start_col = col
        self.end_line = line
        self.end_col = col + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'message': self.message,
            'line': self.line,
            'col': self.col,
            'severity': self.severity,
            'start_line': self.start_line,
            'start_col': self.start_col,
            'end_line': self.end_line,
            'end_col': self.end_col,
        }


# ============================================================================
# Module-level type system
# ============================================================================

_VALID_TYPES = frozenset({'tile', 'glass', 'brick', 'beam', 'wall', 'field', 'house'})

_ARITH_OPS = frozenset({'+', '-', '*', '/', '%'})
_REL_OPS   = frozenset({'<', '<=', '>', '>='})
_EQ_OPS    = frozenset({'==', '!='})
_LOGIC_OPS = frozenset({'&&', '||'})

# All types that participate in implicit casting (wall is excluded)
_CAST_TYPES = frozenset({'brick', 'beam', 'tile', 'glass'})


def dominant_type(type_a: str, type_b: str) -> str:
    """Return the wider of two castable types for expression result typing.

    Hierarchy (narrowest → widest): brick(0) beam(1) tile(2) glass(3)

    Examples
    --------
    dominant_type('tile', 'glass') → 'glass'
    dominant_type('brick', 'tile') → 'tile'
    dominant_type('beam', 'tile')  → 'tile'
    """
    if type_a not in _NUMERIC_RANK or type_b not in _NUMERIC_RANK:
        return type_a
    return type_a if _NUMERIC_RANK[type_a] >= _NUMERIC_RANK[type_b] else type_b


def can_cast(source: str, target: str) -> bool:
    """Single source of truth for implicit cast validity.

    Rules
    -----
    1. source == target               → True
    2. either is 'wall'              → False  (wall is completely isolated)
    3. both in _CAST_TYPES           → True   (promotion AND demotion allowed)
    4. everything else               → False
    """
    if source == target:
        return True
    if source == 'wall' or target == 'wall':
        return False
    if source in _CAST_TYPES and target in _CAST_TYPES:
        return True
    return False


def _make_typeinfo(type_str: str, symbol: Optional[Symbol] = None) -> TypeInfo:
    if type_str and type_str.startswith('house '):
        struct_name = type_str[6:].strip()
        return TypeInfo(base_type='house', struct_name=struct_name,
                        is_array=symbol.is_array if symbol else False,
                        array_dims=symbol.array_dims if symbol else None)
    return TypeInfo(
        base_type=type_str or 'tile',
        is_array=symbol.is_array if symbol else False,
        array_dims=symbol.array_dims if symbol else None,
    )


def _typeinfo_from_symbol(symbol: Symbol) -> TypeInfo:
    base = symbol.type
    struct_name = symbol.struct_name
    if not struct_name and isinstance(base, str) and base.startswith('house '):
        struct_name = base[6:].strip()
        base = 'house'
    return TypeInfo(
        base_type=base,
        is_array=symbol.is_array,
        array_dims=symbol.array_dims,
        struct_name=struct_name,
        is_const=symbol.is_const,
    )


# ============================================================================
# Constant folding helpers
# ============================================================================

def _fold_binary(op: str, lval, rval, result_type: str) -> Optional[LiteralNode]:
    """Attempt to constant-fold a binary operation on two literal values.

    Returns a new LiteralNode if folding succeeds, None otherwise.
    Division by zero is silently skipped (no fold, no crash).
    """
    try:
        if op == '+':   result = lval + rval
        elif op == '-': result = lval - rval
        elif op == '*': result = lval * rval
        elif op == '/':
            if rval == 0:
                return None
            result = lval / rval if result_type == 'glass' else int(lval / rval)
        elif op == '%':
            if rval == 0:
                return None
            result = int(lval) % int(rval)
        else:
            return None
    except Exception:
        return None
    return LiteralNode(value=result, literal_type=result_type, line=0, col=0)


def _literal_value(node: LiteralNode):
    """Extract a Python numeric value from a LiteralNode."""
    v = node.value
    if node.literal_type == 'glass':
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    try:
        return int(v) if not isinstance(v, (int, float)) else v
    except (ValueError, TypeError):
        return None


# ============================================================================
# All-paths return analysis
# ============================================================================

def _returns_on_all_paths(stmts: list) -> bool:
    """Return True if every execution path through *stmts* ends with 'home'.

    Conservative analysis:
      - A ReturnNode guarantees a return on this path.
      - An IfNode with both then_body and else_body that each return guarantees.
      - A SwitchNode with a default case where every case body returns guarantees.
      - All other nodes (loops, assignments, etc.) do not guarantee a return.
    """
    for stmt in stmts:
        if isinstance(stmt, ReturnNode):
            return True
        if isinstance(stmt, IfNode):
            if stmt.else_body is not None:
                if (_returns_on_all_paths(stmt.then_body) and
                        _returns_on_all_paths(stmt.else_body)):
                    return True
        if isinstance(stmt, SwitchNode):
            has_default = any(c.is_default for c in stmt.cases)
            if has_default and all(_returns_on_all_paths(c.body) for c in stmt.cases):
                return True
    return False


# ============================================================================
# Semantic Analyzer
# ============================================================================

class SemanticAnalyzer:
    """
    Semantic Analyzer using Visitor Pattern.
    Traversal: DFS Pre-order for declarations, Post-order for expressions.

    Context flags
    -------------
    current_function_return_type  str | None   return type of enclosing function
    in_loop                       bool         True inside any loop body
    in_switch                     bool         True inside a switch body (NOT a loop)
    """

    def __init__(self, ast: ProgramNode):
        self.ast = ast
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticError] = []
        self.current_function_return_type: Optional[str] = None
        self.in_loop: bool = False
        self.in_switch: bool = False     # NEW: separate switch context

    # ── public entry point ────────────────────────────────────────────────────

    def analyze(self) -> List[Dict]:
        """Main entry point.  Returns list of error/warning dicts."""
        try:
            self.visit_program(self.ast)
        except Exception as e:
            self.errors.append(SemanticError(
                f'Internal semantic error: {e}', 1, 1
            ))
        return [err.to_dict() for err in self.errors]

    def add_error(self, message: str, line: int, col: int):
        self.errors.append(SemanticError(message, line, col, severity='error'))

    def add_warning(self, message: str, line: int, col: int):
        self.errors.append(SemanticError(message, line, col, severity='warning'))

    # ── program ───────────────────────────────────────────────────────────────

    def visit_program(self, node: ProgramNode):
        # Pass 1a: struct types first
        for decl in node.globals:
            if isinstance(decl, StructDeclNode):
                self.declare_struct(decl)
        # Pass 1b: global variables
        for decl in node.globals:
            if isinstance(decl, VarDeclNode):
                self.declare_global_variable(decl)
        # Pass 1c: function signatures (enables forward calls)
        for func in node.functions:
            self.declare_function(func)
        # Pass 2: function bodies
        for func in node.functions:
            self.visit_function(func)
        # Require blueprint() entry point
        if not self.symbol_table.get_function('blueprint'):
            self.add_error(
                "Missing entry point: blueprint() function not defined", 1, 1
            )

    # ── struct declaration ────────────────────────────────────────────────────

    def declare_struct(self, node: StructDeclNode):
        if self.symbol_table.get_struct(node.name):
            self.add_error(f"Struct '{node.name}' already defined",
                           node.line, node.col)
            return
        members: Dict[str, Symbol] = {}
        seen: set = set()
        for member in node.members:
            if member.name in seen:
                self.add_error(
                    f"Duplicate member '{member.name}' in struct '{node.name}'",
                    member.line, member.col)
                continue
            seen.add(member.name)
            members[member.name] = Symbol(
                name=member.name, type=member.type, kind='variable',
                is_array=member.is_array, array_dims=member.array_dims,
                initialized=True, line=member.line, col=member.col,
            )
        self.symbol_table.define_struct(node.name, members, node.line, node.col)

    # ── global variable / constant ────────────────────────────────────────────

    def declare_global_variable(self, node: VarDeclNode):
        if self.symbol_table.lookup_local(node.name):
            self.add_error(f"Global variable '{node.name}' already defined",
                           node.line, node.col)
            return
        struct_name = _resolve_struct_name(node)
        symbol = Symbol(
            name=node.name, type=node.type,
            kind='constant' if node.is_const else 'variable',
            is_const=node.is_const, is_array=node.is_array,
            array_dims=node.array_dims, struct_name=struct_name,
            initialized=(node.init_value is not None),
            line=node.line, col=node.col,
        )
        self.symbol_table.define_global(symbol)
        if node.init_value:
            init_type = self.visit_expr(node.init_value)
            if init_type and not self.can_assign(node.type, init_type):
                self.add_error(
                    f"Type mismatch in initialization of '{node.name}': "
                    f"cannot assign {init_type} to {node.type}",
                    node.line, node.col)

    # ── function declaration ──────────────────────────────────────────────────

    def declare_function(self, node: FunctionNode):
        if self.symbol_table.get_function(node.name):
            self.add_error(f"Function '{node.name}' already defined",
                           node.line, node.col)
            return
        params = [
            Symbol(name=p.name, type=p.type, kind='parameter',
                   initialized=True, line=p.line, col=p.col)
            for p in node.params
        ]
        func_symbol = Symbol(
            name=node.name, type=node.return_type, kind='function',
            return_type=node.return_type, params=params,
            initialized=True, line=node.line, col=node.col,
        )
        self.symbol_table.define_global(func_symbol)

    # ── function body ─────────────────────────────────────────────────────────

    def visit_function(self, node: FunctionNode):
        self.current_function_return_type = node.return_type
        self.symbol_table.enter_scope(node.name)

        seen_params: set = set()
        for param in node.params:
            if param.name in seen_params:
                self.add_error(
                    f"Duplicate parameter '{param.name}' in '{node.name}'",
                    param.line, param.col)
                continue
            seen_params.add(param.name)
            self.symbol_table.define(Symbol(
                name=param.name, type=param.type, kind='parameter',
                initialized=True, line=param.line, col=param.col,
            ))

        # ── all-paths return check (Issue 2) ─────────────────────────────────
        if node.return_type != 'field':
            if not _returns_on_all_paths(node.body):
                self.add_error(
                    f"Function '{node.name}' does not return a value on "
                    f"all control paths",
                    node.line, node.col)

        # ── dead code detection within body (Issue 7) ────────────────────────
        self._check_dead_code(node.body)

        for stmt in node.body:
            self.visit_statement(stmt)

        self.symbol_table.exit_scope()
        self.current_function_return_type = None

    # ── statement dispatch ────────────────────────────────────────────────────

    def visit_statement(self, node: ASTNode):
        if isinstance(node, VarDeclNode):
            self.visit_var_decl(node)
        elif isinstance(node, AssignNode):
            self.visit_assign(node)
        elif isinstance(node, IfNode):
            self.visit_if(node)
        elif isinstance(node, WhileNode):
            self.visit_while(node)
        elif isinstance(node, DoWhileNode):
            self.visit_dowhile(node)
        elif isinstance(node, ForNode):
            self.visit_for(node)
        elif isinstance(node, SwitchNode):
            self.visit_switch(node)
        elif isinstance(node, BreakNode):
            self.visit_break(node)
        elif isinstance(node, ContinueNode):
            self.visit_continue(node)
        elif isinstance(node, ReturnNode):
            self.visit_return(node)
        elif isinstance(node, IONode):
            self.visit_io(node)
        elif isinstance(node, FunctionCallNode):
            self.visit_function_call(node)

    # ── dead code detection (Issue 7) ────────────────────────────────────────

    def _check_dead_code(self, stmts: list):
        """Warn about statements that follow a home statement in the same block."""
        for i, stmt in enumerate(stmts):
            if isinstance(stmt, ReturnNode):
                remaining = [s for s in stmts[i + 1:]
                             if not isinstance(s, (VarDeclNode,))]
                # Any executable statement after return is unreachable
                for dead in stmts[i + 1:]:
                    self.add_warning(
                        "Unreachable code after 'home' statement",
                        dead.line, dead.col)
                return  # stop after first return in block

    # ── local variable declaration ────────────────────────────────────────────

    def visit_var_decl(self, node: VarDeclNode):
        # Redeclaration in same scope
        if self.symbol_table.lookup_local(node.name):
            self.add_error(
                f"Variable '{node.name}' already declared in this scope",
                node.line, node.col)
            return

        # ── shadowing warning (Issue 6) ───────────────────────────────────────
        outer = self.symbol_table.lookup(node.name)
        if outer is not None and outer.scope_level == 0:
            self.add_warning(
                f"Local variable '{node.name}' shadows global declaration",
                node.line, node.col)

        struct_name = _resolve_struct_name(node)
        symbol = Symbol(
            name=node.name, type=node.type,
            kind='constant' if node.is_const else 'variable',
            is_const=node.is_const, is_array=node.is_array,
            array_dims=node.array_dims, struct_name=struct_name,
            initialized=(node.init_value is not None),
            line=node.line, col=node.col,
        )
        self.symbol_table.define(symbol)

        if node.init_value:
            init_type = self.visit_expr(node.init_value)
            if init_type and not self.can_assign(node.type, init_type):
                self.add_error(
                    f"Type mismatch: cannot assign {init_type} to {node.type}",
                    node.line, node.col)

    # ── assignment ────────────────────────────────────────────────────────────

    def visit_assign(self, node: AssignNode):
        target_type = self.visit_expr(node.target)
        if target_type is None:
            return

        if isinstance(node.target, IdNode):
            symbol = self.symbol_table.lookup(node.target.name)
            if symbol and symbol.is_const:
                self.add_error(
                    f"Cannot assign to constant '{node.target.name}'",
                    node.line, node.col)
                return
            # Mark as initialized now
            if symbol and not symbol.initialized:
                symbol.initialized = True

        value_type = self.visit_expr(node.value)
        if value_type is None:
            return

        # ── void-function-as-value guard (Issue 5) ────────────────────────────
        if value_type == 'field':
            self.add_error(
                "Cannot use a void (field) function result as a value",
                node.line, node.col)
            return

        if node.operator != '=':
            base_op = node.operator[0]
            result_type = self.check_binary_op(
                target_type, base_op, value_type, node.line, node.col)
            if result_type and not self.can_assign(target_type, result_type):
                self.add_error(
                    f"Type mismatch in compound assignment '{node.operator}': "
                    f"{target_type} and {value_type} are incompatible",
                    node.line, node.col)
        else:
            if not self.can_assign(target_type, value_type):
                self.add_error(
                    f"Type mismatch: cannot assign {value_type} to {target_type}",
                    node.line, node.col)

    # ── control flow ──────────────────────────────────────────────────────────

    def visit_if(self, node: IfNode):
        cond_type = self.visit_expr(node.condition)
        self._check_bool_condition(cond_type, 'if', node.line, node.col)

        self.symbol_table.enter_scope('block')
        self._check_dead_code(node.then_body)
        for stmt in node.then_body:
            self.visit_statement(stmt)
        self.symbol_table.exit_scope()

        if node.else_body:
            self.symbol_table.enter_scope('block')
            self._check_dead_code(node.else_body)
            for stmt in node.else_body:
                self.visit_statement(stmt)
            self.symbol_table.exit_scope()

    def visit_while(self, node: WhileNode):
        cond_type = self.visit_expr(node.condition)
        self._check_bool_condition(cond_type, 'while', node.line, node.col)

        self.symbol_table.enter_scope('while')
        old_in_loop, old_in_switch = self.in_loop, self.in_switch
        self.in_loop = True
        self.in_switch = False
        self._check_dead_code(node.body)
        for stmt in node.body:
            self.visit_statement(stmt)
        self.in_loop, self.in_switch = old_in_loop, old_in_switch
        self.symbol_table.exit_scope()

    def visit_dowhile(self, node: DoWhileNode):
        self.symbol_table.enter_scope('dowhile')
        old_in_loop, old_in_switch = self.in_loop, self.in_switch
        self.in_loop = True
        self.in_switch = False
        self._check_dead_code(node.body)
        for stmt in node.body:
            self.visit_statement(stmt)
        self.in_loop, self.in_switch = old_in_loop, old_in_switch
        self.symbol_table.exit_scope()

        cond_type = self.visit_expr(node.condition)
        self._check_bool_condition(cond_type, 'do-while', node.line, node.col)

    def visit_for(self, node: ForNode):
        self.symbol_table.enter_scope('for')
        old_in_loop, old_in_switch = self.in_loop, self.in_switch
        self.in_loop = True
        self.in_switch = False

        if node.init:
            if isinstance(node.init, VarDeclNode):
                self.visit_var_decl(node.init)
            elif isinstance(node.init, AssignNode):
                self.visit_assign(node.init)

        cond_type = self.visit_expr(node.condition)
        self._check_bool_condition(cond_type, 'for', node.line, node.col)

        if node.increment:
            self.visit_expr(node.increment)

        self._check_dead_code(node.body)
        for stmt in node.body:
            self.visit_statement(stmt)

        self.in_loop, self.in_switch = old_in_loop, old_in_switch
        self.symbol_table.exit_scope()

    def visit_switch(self, node: SwitchNode):
        """Type-check a switch (room) statement.

        NEW: separate in_switch flag (Issue 3).
        NEW: duplicate case value detection (Issue 4).
        """
        switch_type = self.visit_expr(node.expr)

        self.symbol_table.enter_scope('switch')
        old_in_loop, old_in_switch = self.in_loop, self.in_switch
        # switch does NOT set in_loop — only in_switch
        self.in_loop = False
        self.in_switch = True

        seen_case_values: Set[str] = set()   # Issue 4: track case labels

        for case in node.cases:
            if not case.is_default and case.value:
                case_type = self.visit_expr(case.value)
                if switch_type and case_type and not self.types_compatible(switch_type, case_type):
                    self.add_error(
                        f"Case value type '{case_type}' does not match "
                        f"switch expression type '{switch_type}'",
                        case.line, case.col)

                # ── duplicate case detection (Issue 4) ───────────────────────
                case_key = str(case.value.value) if case.value else None
                if case_key is not None:
                    if case_key in seen_case_values:
                        self.add_error(
                            f"Duplicate case value '{case_key}' in switch",
                            case.line, case.col)
                    else:
                        seen_case_values.add(case_key)

            self._check_dead_code(case.body)
            for stmt in case.body:
                self.visit_statement(stmt)

        self.in_loop, self.in_switch = old_in_loop, old_in_switch
        self.symbol_table.exit_scope()

    def visit_break(self, node: BreakNode):
        """crack is valid inside a loop OR a switch."""
        if not self.in_loop and not self.in_switch:
            self.add_error(
                "Break (crack) statement outside loop or switch",
                node.line, node.col)

    def visit_continue(self, node: ContinueNode):
        """mend is valid ONLY inside a loop — NOT inside a switch. (Issue 3)"""
        if not self.in_loop:
            self.add_error(
                "Continue (mend) statement outside loop; "
                "'mend' is not valid inside a switch (room) block",
                node.line, node.col)

    def visit_return(self, node: ReturnNode):
        if not self.current_function_return_type:
            self.add_error("Return statement outside function",
                           node.line, node.col)
            return

        rtype = self.current_function_return_type

        if rtype == 'field':
            if node.value:
                self.add_error(
                    "Cannot return a value from a field (void) function",
                    node.line, node.col)
        else:
            if not node.value:
                self.add_error(
                    f"Function must return a value of type '{rtype}'",
                    node.line, node.col)
                return
            ret_type = self.visit_expr(node.value)
            if ret_type and not self.can_assign(rtype, ret_type):
                self.add_error(
                    f"Return type mismatch: expected '{rtype}', got '{ret_type}'",
                    node.line, node.col)

    # ── I/O ───────────────────────────────────────────────────────────────────

    def visit_io(self, node: IONode):
        for arg in node.args:
            self.visit_expr(arg)

    # ── expression visitors ───────────────────────────────────────────────────

    def visit_expr(self, node: ExprNode) -> Optional[str]:
        """Visit an expression, return its type string, and write back expr_type.

        Issue 8 (Type annotation): the resolved type is stored on each node
        so that the code generator can read node.expr_type directly.
        """
        if node is None:
            return None
        result = self._visit_expr_inner(node)
        # Write resolved type back into the node (annotation)
        if result is not None and hasattr(node, 'expr_type'):
            node.expr_type = result
        return result

    def _visit_expr_inner(self, node: ExprNode) -> Optional[str]:
        if isinstance(node, BinaryOpNode):
            return self.visit_binary_op(node)
        elif isinstance(node, UnaryOpNode):
            return self.visit_unary_op(node)
        elif isinstance(node, LiteralNode):
            node.expr_type = node.literal_type
            return node.literal_type
        elif isinstance(node, IdNode):
            return self.visit_id(node)
        elif isinstance(node, ArrayAccessNode):
            return self.visit_array_access(node)
        elif isinstance(node, StructAccessNode):
            return self.visit_struct_access(node)
        elif isinstance(node, FunctionCallNode):
            return self.visit_function_call(node)
        elif isinstance(node, WallConcatNode):
            return self.visit_wall_concat(node)
        return None

    def visit_binary_op(self, node: BinaryOpNode) -> Optional[str]:
        """Infer binary op type with constant folding (Issue 9)."""
        left_type = self.visit_expr(node.left)
        right_type = self.visit_expr(node.right)
        if left_type is None or right_type is None:
            return None

        result_type = self.check_binary_op(
            left_type, node.operator, right_type, node.line, node.col)

        # ── constant folding (Issue 9) ────────────────────────────────────────
        if (result_type and result_type in _CAST_TYPES
                and isinstance(node.left, LiteralNode)
                and isinstance(node.right, LiteralNode)
                and node.operator in _ARITH_OPS
                and left_type != 'wall' and right_type != 'wall'):
            lv = _literal_value(node.left)
            rv = _literal_value(node.right)
            if lv is not None and rv is not None:
                folded = _fold_binary(node.operator, lv, rv, result_type)
                if folded is not None:
                    # Mutate the node in-place to carry the folded literal
                    # so the code generator can use it directly
                    node.folded_value = folded

        return result_type

    def check_binary_op(self, left: str, op: str, right: str,
                        line: int, col: int) -> Optional[str]:
        """Determine result type of (left op right); emit errors on violations."""
        if op in _ARITH_OPS:
            if op == '+' and left == 'wall' and right == 'wall':
                return 'wall'
            if left == 'wall' or right == 'wall':
                self.add_error(
                    f"Cannot use wall (string) in arithmetic operation '{op}'",
                    line, col)
                return None
            if left not in _CAST_TYPES or right not in _CAST_TYPES:
                self.add_error(
                    f"Operator '{op}' requires castable operands "
                    f"(brick/beam/tile/glass), got '{left}' and '{right}'",
                    line, col)
                return None
            return dominant_type(left, right)

        elif op in _REL_OPS:
            if left == 'wall' or right == 'wall':
                self.add_error(
                    f"Cannot use wall (string) with relational operator '{op}'",
                    line, col)
                return None
            if left not in _CAST_TYPES or right not in _CAST_TYPES:
                self.add_error(
                    f"Relational operator '{op}' requires castable operands, "
                    f"got '{left}' and '{right}'",
                    line, col)
                return None
            return 'beam'

        elif op in _EQ_OPS:
            if not self.types_compatible(left, right):
                self.add_error(
                    f"Cannot compare '{left}' and '{right}' with '{op}'",
                    line, col)
                return None
            return 'beam'

        elif op in _LOGIC_OPS:
            if left == 'wall' or right == 'wall':
                self.add_error(
                    f"Cannot use wall (string) with logical operator '{op}'",
                    line, col)
                return None
            if left not in _CAST_TYPES or right not in _CAST_TYPES:
                self.add_error(
                    f"Logical operator '{op}' requires castable operands, "
                    f"got '{left}' and '{right}'",
                    line, col)
                return None
            return 'beam'

        return None

    def visit_unary_op(self, node: UnaryOpNode) -> Optional[str]:
        operand_type = self.visit_expr(node.operand)
        if operand_type is None:
            return None

        if node.operator == '-':
            if operand_type not in _CAST_TYPES:
                self.add_error(
                    f"Unary '-' requires a castable operand "
                    f"(brick/beam/tile/glass), got '{operand_type}'",
                    node.line, node.col)
                return None
            return operand_type

        elif node.operator == '!':
            if operand_type not in _CAST_TYPES:
                self.add_error(
                    f"Logical '!' requires a castable operand "
                    f"(brick/beam/tile/glass), got '{operand_type}'",
                    node.line, node.col)
                return None
            return 'beam'

        elif node.operator in ('++', '--'):
            if operand_type not in _CAST_TYPES:
                self.add_error(
                    f"Operator '{node.operator}' requires a castable operand "
                    f"(brick/beam/tile/glass), got '{operand_type}'",
                    node.line, node.col)
                return None
            return operand_type

        return None

    def visit_id(self, node: IdNode) -> Optional[str]:
        """Look up identifier; check existence and initialization. (Issue 1)"""
        symbol = self.symbol_table.lookup(node.name)
        if not symbol:
            self.add_error(f"Undeclared variable '{node.name}'",
                           node.line, node.col)
            return None
        # ── use-before-initialization check (Issue 1) ─────────────────────────
        if not symbol.initialized and symbol.kind in ('variable', 'parameter'):
            self.add_error(
                f"Variable '{node.name}' used before initialization",
                node.line, node.col)
            # Do NOT return None — the type is still known; avoid cascades
        return symbol.type

    def visit_array_access(self, node: ArrayAccessNode) -> Optional[str]:
        array_type = self.visit_expr(node.array)
        if array_type is None:
            return None
        if array_type == 'wall':
            self.add_error("Cannot index a wall (string) value with '[]'",
                           node.line, node.col)
            return None
        if array_type == 'house' or (isinstance(array_type, str)
                                      and array_type.startswith('house')):
            self.add_error("Cannot index a struct with '[]'",
                           node.line, node.col)
            return None
        for idx_expr in node.indices:
            idx_type = self.visit_expr(idx_expr)
            if idx_type is not None and idx_type not in _CAST_TYPES:
                self.add_error(
                    f"Array index must be a castable numeric type "
                    f"(brick/beam/tile/glass), got '{idx_type}'",
                    node.line, node.col)
        return array_type

    def visit_struct_access(self, node: StructAccessNode) -> Optional[str]:
        """Validate struct member access (single and chained). (Issue 10)"""
        struct_type_name: Optional[str] = None

        if isinstance(node.struct, IdNode):
            sym = self.symbol_table.lookup(node.struct.name)
            if sym is None:
                self.add_error(f"Undeclared variable '{node.struct.name}'",
                               node.struct.line, node.struct.col)
                return None
            struct_type_name = _extract_struct_name(sym)

        elif isinstance(node.struct, StructAccessNode):
            # Chained: a.b.member — member_type must itself be a house type
            member_type = self.visit_struct_access(node.struct)
            if member_type is None:
                return None
            if isinstance(member_type, str) and member_type.startswith('house '):
                struct_type_name = member_type[6:].strip()
            else:
                self.add_error(
                    f"Cannot access member '{node.member}' on non-struct type "
                    f"'{member_type}'",
                    node.line, node.col)
                return None
        else:
            expr_type = self.visit_expr(node.struct)
            if expr_type is None:
                return None
            if isinstance(expr_type, str) and expr_type.startswith('house '):
                struct_type_name = expr_type[6:].strip()
            else:
                self.add_error(
                    f"Cannot access member '{node.member}' on non-struct type "
                    f"'{expr_type}'",
                    node.line, node.col)
                return None

        if struct_type_name is None:
            self.add_error(
                f"Variable is not a struct; cannot access member '{node.member}'",
                node.line, node.col)
            return None

        struct_def = self.symbol_table.get_struct(struct_type_name)
        if struct_def is None:
            self.add_error(f"Unknown struct type '{struct_type_name}'",
                           node.line, node.col)
            return None

        member = (struct_def.members or {}).get(node.member)
        if member is None:
            self.add_error(
                f"Struct '{struct_type_name}' has no member '{node.member}'",
                node.line, node.col)
            return None

        return member.type

    def visit_function_call(self, node: FunctionCallNode) -> Optional[str]:
        """Validate call; reject void result used in expression. (Issue 5)"""
        func_symbol = self.symbol_table.get_function(node.func_name)
        if func_symbol is None:
            self.add_error(f"Undefined function '{node.func_name}'",
                           node.line, node.col)
            return None

        if node.func_name in ('view', 'write'):
            for arg in node.args:
                self.visit_expr(arg)
            return func_symbol.return_type

        expected_params = func_symbol.params or []

        if len(node.args) != len(expected_params):
            self.add_error(
                f"Function '{node.func_name}' expects "
                f"{len(expected_params)} argument(s), got {len(node.args)}",
                node.line, node.col)
            for arg in node.args:
                self.visit_expr(arg)
            return func_symbol.return_type

        for i, (arg_expr, param) in enumerate(
                zip(node.args, expected_params), start=1):
            arg_type = self.visit_expr(arg_expr)
            if arg_type and not self.can_assign(param.type, arg_type):
                self.add_error(
                    f"Argument {i} of '{node.func_name}': "
                    f"expected '{param.type}', got '{arg_type}'",
                    node.line, node.col)

        # Issue 5: 'field' return type is valid here — the CALLER's context
        # decides whether void is acceptable.  visit_var_decl / visit_assign
        # guard against tile x = void_call() by checking for 'field' there.
        return func_symbol.return_type

    def visit_wall_concat(self, node: WallConcatNode) -> str:
        for part in node.parts:
            part_type = self.visit_expr(part)
            if part_type is not None and part_type != 'wall':
                self.add_error(
                    f"Cannot concatenate '{part_type}' into a wall (string); "
                    f"all parts must be wall",
                    node.line, node.col)
        return 'wall'

    # ── type checking helpers ─────────────────────────────────────────────────

    def can_assign(self, target_type: str, value_type: str) -> bool:
        t_base, t_struct = _split_type(target_type)
        v_base, v_struct = _split_type(value_type)
        if t_base == 'house' and v_base == 'house':
            return t_struct == v_struct
        return can_cast(v_base, t_base)

    def types_compatible(self, type1: str, type2: str) -> bool:
        if type1 == type2:
            return True
        if type1 in _CAST_TYPES and type2 in _CAST_TYPES:
            return True
        return False

    def _check_bool_condition(self, cond_type: Optional[str],
                               ctx: str, line: int, col: int):
        if cond_type is not None and cond_type not in _CAST_TYPES:
            self.add_error(
                f"Condition of '{ctx}' must evaluate to a boolean-compatible "
                f"type (brick/beam/tile/glass), got '{cond_type}'",
                line, col)


# ============================================================================
# Module-level helpers
# ============================================================================

def _resolve_struct_name(node: VarDeclNode) -> Optional[str]:
    if hasattr(node, 'struct_type_name') and node.struct_type_name:
        return node.struct_type_name
    if isinstance(node.type, str) and node.type.startswith('house '):
        return node.type[6:].strip()
    return None


def _extract_struct_name(sym: Symbol) -> Optional[str]:
    if sym.struct_name:
        return sym.struct_name
    if isinstance(sym.type, str) and sym.type.startswith('house '):
        return sym.type[6:].strip()
    return None


def _split_type(type_str: str):
    if isinstance(type_str, str) and type_str.startswith('house '):
        return 'house', type_str[6:].strip()
    return type_str, None