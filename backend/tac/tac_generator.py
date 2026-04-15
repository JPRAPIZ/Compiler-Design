from typing import List, Optional
from semantic.ast import (
    ProgramNode, FunctionNode, ParamNode,
    VarDeclNode, StructDeclNode,
    AssignNode, IfNode, WhileNode, DoWhileNode, ForNode,
    SwitchNode, CaseNode, BreakNode, ContinueNode, ReturnNode, IONode,
    BinaryOpNode, UnaryOpNode, LiteralNode, IdNode,
    ArrayAccessNode, StructAccessNode, FunctionCallNode, WallConcatNode, ArrayInitNode,
    ASTNode, ExprNode,
)


# ---------------------------------------------------------------------------
# TACGenerator
# ---------------------------------------------------------------------------

class TACGenerator:
    """Traverses a ProgramNode AST and produces a list of TAC instruction dicts.

    Usage
    -----
        gen = TACGenerator()
        instructions = gen.generate(program_node)
        lines = [tac_instruction_to_str(i) for i in instructions]
    """

    def __init__(self):
        self._instructions: List[dict] = []
        self._temp_count: int = 0      # counter for t1, t2, …
        self._label_count: int = 0     # counter for L1, L2, …

        # Break/continue target stacks — pushed/popped around loop bodies
        self._break_stack: List[str] = []
        self._continue_stack: List[str] = []

        # Scope-aware name mangling for inner-scope variable shadowing.
        # Each entry is a dict mapping original_name → mangled_name.
        # Outermost scope (function level) maps name → name (identity).
        self._scope_stack: List[dict] = []
        self._scope_counter: int = 0   # monotonic counter for unique suffixes

    # ── public entry point ────────────────────────────────────────────────────

    def generate(self, program: ProgramNode) -> List[dict]:
        """Generate TAC for the entire program.

        Order of emission:
          1. Global variable declarations  (initialised at program start)
          2. Each function definition      (including blueprint / main)

        Returns the flat instruction list.
        """
        self._instructions = []
        self._temp_count = 0
        self._label_count = 0

        # Collect struct definitions for member-order lookup during struct init.
        # Maps struct_name → [member_name_1, member_name_2, ...]
        self._struct_defs: dict = {}
        for decl in program.globals:
            if isinstance(decl, StructDeclNode):
                self._struct_defs[decl.name] = [m.name for m in decl.members]

        # 1. Global initialisations
        for decl in program.globals:
            self._gen_global(decl)

        # 2. Function definitions
        for func in program.functions:
            self._gen_function(func)

        return list(self._instructions)

    # ── instruction emission helpers ──────────────────────────────────────────

    def _emit(self, instr: dict):
        """Append one instruction dict to the instruction list."""
        self._instructions.append(instr)

    def _new_temp(self) -> str:
        """Allocate a new temporary variable name: t1, t2, …"""
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _new_label(self) -> str:
        """Allocate a new label name: L1, L2, …"""
        self._label_count += 1
        return f"L{self._label_count}"

    # ── global declarations ───────────────────────────────────────────────────

    def _gen_global(self, decl):
        """Emit TAC for a global declaration.

        StructDeclNode — no runtime code needed; the type is purely static.
        VarDeclNode    — emit an assignment if an initialiser is present,
                         otherwise emit  name = 0  (default zero-init).
        """
        if isinstance(decl, StructDeclNode):
            # Struct type definitions have no runtime representation.
            return

        if isinstance(decl, VarDeclNode):
            if isinstance(decl.init_value, ArrayInitNode):
                # Check if this is a struct brace init (house-typed variable)
                struct_type_name = decl.struct_type_name
                if struct_type_name and struct_type_name in self._struct_defs:
                    member_names = self._struct_defs[struct_type_name]
                    for i, elem in enumerate(decl.init_value.elements):
                        if i < len(member_names):
                            val = self._gen_expr(elem)
                            self._emit({
                                "op": "assign",
                                "dest": f"{decl.name}.{member_names[i]}",
                                "src": val,
                            })
                    return

                # Global array with brace init
                self._gen_array_init(decl.name, decl.init_value)
                return

            # Array without brace init — emit per-element default values
            if decl.is_array and decl.array_dims:
                self._gen_array_default(decl.name, decl.type, decl.array_dims)
                return

            if decl.init_value is not None:
                src = self._gen_expr(decl.init_value)
            else:
                # Default initialisation: 0 for numerics, "" for wall
                src = '""' if decl.type == "wall" else "0"

            self._emit({
                "op": "assign",
                "dest": decl.name,
                "src": src,
            })

    # ── scope management for name mangling ──────────────────────────────────

    def _enter_scope(self):
        """Push a new inner scope for variable name mangling."""
        self._scope_stack.append({})

    def _exit_scope(self):
        """Pop the innermost scope."""
        if self._scope_stack:
            self._scope_stack.pop()

    def _declare_name(self, name: str) -> str:
        """Register a variable declaration in the current scope.

        If a variable with the same name exists in an outer scope, the inner
        declaration gets a mangled name (e.g. x__s2) to avoid collision.
        Function-level (depth 1) declarations keep their bare name.
        """
        if len(self._scope_stack) <= 1:
            # Function-level scope — no mangling needed
            if self._scope_stack:
                self._scope_stack[-1][name] = name
            return name

        # Inner scope — check if name exists in any outer scope
        for scope in self._scope_stack[:-1]:
            if name in scope:
                # Name collision — mangle the inner declaration
                self._scope_counter += 1
                mangled = f"{name}__s{self._scope_counter}"
                self._scope_stack[-1][name] = mangled
                return mangled

        # No collision — use bare name
        if self._scope_stack:
            self._scope_stack[-1][name] = name
        return name

    def _resolve_name(self, name: str) -> str:
        """Look up a variable name in the scope stack (innermost first).

        Returns the mangled name if the variable was shadowed, or the
        original name if not found in any scope (e.g. globals).
        """
        for scope in reversed(self._scope_stack):
            if name in scope:
                return scope[name]
        return name  # global or unknown — use as-is

    # ── function definitions ──────────────────────────────────────────────────

    def _gen_function(self, func: FunctionNode):
        """Emit TAC for one function definition."""
        param_names = [p.name for p in func.params]

        # Push function-level scope and register parameters
        self._scope_stack = []
        self._enter_scope()
        for pname in param_names:
            self._scope_stack[-1][pname] = pname

        self._emit({
            "op": "func_begin",
            "name": func.name,
            "params": param_names,
        })

        for item in func.body:
            self._gen_stmt(item)

        self._emit({
            "op": "func_end",
            "name": func.name,
        })

        self._exit_scope()

    # ── statement dispatch ────────────────────────────────────────────────────

    def _gen_stmt(self, node):
        """Dispatch one AST statement or declaration node to its generator."""
        if isinstance(node, VarDeclNode):
            self._gen_var_decl(node)
        elif isinstance(node, AssignNode):
            self._gen_assign(node)
        elif isinstance(node, IfNode):
            self._gen_if(node)
        elif isinstance(node, WhileNode):
            self._gen_while(node)
        elif isinstance(node, DoWhileNode):
            self._gen_dowhile(node)
        elif isinstance(node, ForNode):
            self._gen_for(node)
        elif isinstance(node, SwitchNode):
            self._gen_switch(node)
        elif isinstance(node, BreakNode):
            self._gen_break(node)
        elif isinstance(node, ContinueNode):
            self._gen_continue(node)
        elif isinstance(node, ReturnNode):
            self._gen_return(node)
        elif isinstance(node, IONode):
            self._gen_io(node)
        elif isinstance(node, FunctionCallNode):
            self._gen_expr(node)
        elif isinstance(node, UnaryOpNode):
            self._gen_expr(node)

    # ── declarations ─────────────────────────────────────────────────────────

    def _gen_var_decl(self, node: VarDeclNode):
        """Emit TAC for a local variable declaration with scope-aware naming.

        For arrays with brace initializers (ArrayInitNode), emits per-element
        assignment instructions: arr[0] = val0, arr[1] = val1, ...

        For struct variables with brace initializers (house Point p = {3, 7}),
        emits per-member assignments: p.x = 3, p.y = 7
        """
        mangled = self._declare_name(node.name)

        if isinstance(node.init_value, ArrayInitNode):
            # Check if this is a struct brace init (house-typed variable)
            struct_type_name = node.struct_type_name
            if struct_type_name and struct_type_name in self._struct_defs:
                # Struct brace init: emit per-member assignments
                member_names = self._struct_defs[struct_type_name]
                for i, elem in enumerate(node.init_value.elements):
                    if i < len(member_names):
                        val = self._gen_expr(elem)
                        self._emit({
                            "op": "assign",
                            "dest": f"{mangled}.{member_names[i]}",
                            "src": val,
                        })
                return

            # Array brace initializer: {v1, v2, ...} or {{r1}, {r2}}
            self._gen_array_init(mangled, node.init_value)
            return

        # Array without brace init — emit per-element default values
        if node.is_array and node.array_dims:
            self._gen_array_default(mangled, node.type, node.array_dims)
            return

        if node.init_value is not None:
            src = self._gen_expr(node.init_value)
        else:
            if node.type == "wall":
                src = '""'
            elif node.type == "glass" or (isinstance(node.type, str) and
                                           node.type.startswith("glass")):
                src = "0.0"
            else:
                src = "0"

        instr = {
            "op": "assign",
            "dest": mangled,
            "src": src,
        }
        # Annotate with destination type for implicit conversion at runtime.
        # Only needed for numeric types (brick/beam/tile/glass) where the
        # source expression type differs from the declared variable type.
        decl_type = node.type
        if decl_type in ("brick", "beam", "tile", "glass"):
            src_type = getattr(node.init_value, 'expr_type', None) if node.init_value else None
            if src_type and src_type != decl_type and src_type in ("brick", "beam", "tile", "glass"):
                instr["dest_type"] = decl_type
        self._emit(instr)

    def _gen_array_init(self, arr_name: str, init_node: 'ArrayInitNode'):
        """Emit per-element assignments for an array brace initializer.

        1-D: tile arr[3] = {10, 20, 30};
             → arr[0] = 10, arr[1] = 20, arr[2] = 30

        2-D: tile mat[2][3] = {{1,2,3},{4,5,6}};
             → mat[0][0] = 1, mat[0][1] = 2, ..., mat[1][2] = 6
        """
        for i, elem in enumerate(init_node.elements):
            if isinstance(elem, ArrayInitNode):
                # 2-D: elem is a nested ArrayInitNode for one row
                for j, inner_elem in enumerate(elem.elements):
                    val = self._gen_expr(inner_elem)
                    self._emit({
                        "op": "assign",
                        "dest": f"{arr_name}[{i}][{j}]",
                        "src": val,
                    })
            else:
                # 1-D: elem is a plain expression
                val = self._gen_expr(elem)
                self._emit({
                    "op": "assign",
                    "dest": f"{arr_name}[{i}]",
                    "src": val,
                })

    # ── assignment ────────────────────────────────────────────────────────────

    def _gen_array_default(self, arr_name: str, elem_type: str, dims: list):
        """Emit per-element default value assignments for an uninitialized array.

        Spec F.11: arrays with fixed size get default values:
          tile=0, glass=0.0, wall="", brick=0 (\\0), beam=False

        1-D: tile arr[3]  →  arr[0]=0, arr[1]=0, arr[2]=0
        2-D: tile mat[2][3]  →  mat[0][0]=0 ... mat[1][2]=0
        """
        default_val = '""' if elem_type == "wall" else "0.0" if elem_type == "glass" else "0"
        valid_dims = [d for d in dims if isinstance(d, int) and d > 0]
        if len(valid_dims) == 1:
            for i in range(valid_dims[0]):
                self._emit({"op": "assign", "dest": f"{arr_name}[{i}]", "src": default_val})
        elif len(valid_dims) == 2:
            for i in range(valid_dims[0]):
                for j in range(valid_dims[1]):
                    self._emit({"op": "assign", "dest": f"{arr_name}[{i}][{j}]", "src": default_val})

    def _gen_assign(self, node: AssignNode):
        """Emit TAC for an assignment statement.

        Simple assignment (=)
            x = expr   →  <expr → t1>   x = t1

        Compound assignment (+=, -=, *=, /=, %=)
            x += expr  is lowered to:
                <expr → t1>
                t2 = x + t1
                x = t2

        LHS may be a plain IdNode, an ArrayAccessNode, or a StructAccessNode.
        """
        dest = self._lhs_name(node.target)
        rhs_operand = self._gen_expr(node.value)

        # Determine if implicit conversion annotation is needed
        dest_type = getattr(node.target, 'expr_type', None)
        src_type = getattr(node.value, 'expr_type', None)
        _NUMERIC = ("brick", "beam", "tile", "glass")
        need_cast = (dest_type and src_type
                     and dest_type != src_type
                     and dest_type in _NUMERIC
                     and src_type in _NUMERIC)

        if node.operator == "=":
            instr = {
                "op": "assign",
                "dest": dest,
                "src": rhs_operand,
            }
            if need_cast:
                instr["dest_type"] = dest_type
            self._emit(instr)
        else:
            # Compound: lower  x op= rhs  into  x = x op rhs
            raw_op = node.operator[:-1]   # "+=" → "+"
            tmp = self._new_temp()
            self._emit({
                "op": "binop",
                "dest": tmp,
                "left": dest,
                "operator": raw_op,
                "right": rhs_operand,
            })
            instr = {
                "op": "assign",
                "dest": dest,
                "src": tmp,
            }
            if need_cast:
                instr["dest_type"] = dest_type
            self._emit(instr)

    def _lhs_name(self, target) -> str:
        """Compute the string name for an LHS target.

        IdNode            → "x"
        ArrayAccessNode   → "arr[i]"  or  "arr[i][j]"
        StructAccessNode  → "s.field"
        """
        if isinstance(target, IdNode):
            return self._resolve_name(target.name)

        if isinstance(target, ArrayAccessNode):
            base = self._lhs_name(target.array)
            idx_strs = [self._gen_expr(i) for i in target.indices]
            subscript = "".join(f"[{s}]" for s in idx_strs)
            return f"{base}{subscript}"

        if isinstance(target, StructAccessNode):
            base = self._lhs_name(target.struct)
            return f"{base}.{target.member}"

        # Fallback: treat as expression and return whatever operand it resolves to
        return self._gen_expr(target)

    # ── control flow ─────────────────────────────────────────────────────────

    def _gen_if(self, node: IfNode):
        """Emit TAC for an if / else-if / else statement."""
        cond_t = self._gen_expr(node.condition)

        if node.else_body:
            l_else = self._new_label()
            l_end = self._new_label()

            self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_else})

            self._enter_scope()
            for stmt in node.then_body:
                self._gen_stmt(stmt)
            self._exit_scope()

            self._emit({"op": "jump", "target": l_end})
            self._emit({"op": "label", "name": l_else})

            self._enter_scope()
            for stmt in node.else_body:
                self._gen_stmt(stmt)
            self._exit_scope()

            self._emit({"op": "label", "name": l_end})

        else:
            l_end = self._new_label()
            self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_end})

            self._enter_scope()
            for stmt in node.then_body:
                self._gen_stmt(stmt)
            self._exit_scope()

            self._emit({"op": "label", "name": l_end})

    def _gen_while(self, node: WhileNode):
        """Emit TAC for a while loop."""
        l_start = self._new_label()
        l_end = self._new_label()

        self._break_stack.append(l_end)
        self._continue_stack.append(l_start)

        self._emit({"op": "label", "name": l_start})
        cond_t = self._gen_expr(node.condition)
        self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_end})

        self._enter_scope()
        for stmt in node.body:
            self._gen_stmt(stmt)
        self._exit_scope()

        self._emit({"op": "jump", "target": l_start})
        self._emit({"op": "label", "name": l_end})

        self._break_stack.pop()
        self._continue_stack.pop()

    def _gen_dowhile(self, node: DoWhileNode):
        """Emit TAC for a do-while loop."""
        l_start = self._new_label()
        l_cond = self._new_label()
        l_end = self._new_label()

        self._break_stack.append(l_end)
        self._continue_stack.append(l_cond)

        self._emit({"op": "label", "name": l_start})

        self._enter_scope()
        for stmt in node.body:
            self._gen_stmt(stmt)
        self._exit_scope()

        self._emit({"op": "label", "name": l_cond})
        cond_t = self._gen_expr(node.condition)
        self._emit({"op": "jump_if", "cond": cond_t, "target": l_start})
        self._emit({"op": "label", "name": l_end})

        self._break_stack.pop()
        self._continue_stack.pop()

    def _gen_for(self, node: ForNode):
        """Emit TAC for a for loop."""
        l_start = self._new_label()
        l_incr = self._new_label()
        l_end = self._new_label()

        self._break_stack.append(l_end)
        self._continue_stack.append(l_incr)

        # For loop gets its own scope (init var lives here)
        self._enter_scope()

        if node.init is not None:
            self._gen_stmt(node.init)

        self._emit({"op": "label", "name": l_start})
        cond_t = self._gen_expr(node.condition)
        self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_end})

        for stmt in node.body:
            self._gen_stmt(stmt)

        self._emit({"op": "label", "name": l_incr})
        self._gen_expr(node.increment)

        self._emit({"op": "jump", "target": l_start})
        self._emit({"op": "label", "name": l_end})

        self._exit_scope()

        self._break_stack.pop()
        self._continue_stack.pop()

    def _gen_switch(self, node: SwitchNode):
        """Emit TAC for a switch (room) statement."""
        sw_t = self._gen_expr(node.expr)
        l_end = self._new_label()

        self._break_stack.append(l_end)

        case_labels = [self._new_label() for _ in node.cases]
        default_label = None
        for i, case in enumerate(node.cases):
            if case.is_default:
                default_label = case_labels[i]

        for i, case in enumerate(node.cases):
            if case.is_default:
                continue
            cmp_t = self._new_temp()
            case_val = self._gen_expr(case.value)
            self._emit({
                "op": "binop",
                "dest": cmp_t,
                "left": sw_t,
                "operator": "==",
                "right": case_val,
            })
            self._emit({"op": "jump_if", "cond": cmp_t, "target": case_labels[i]})

        if default_label:
            self._emit({"op": "jump", "target": default_label})
        else:
            self._emit({"op": "jump", "target": l_end})

        for i, case in enumerate(node.cases):
            self._emit({"op": "label", "name": case_labels[i]})
            self._enter_scope()
            for stmt in case.body:
                self._gen_stmt(stmt)
            self._exit_scope()
            last = case.body[-1] if case.body else None
            if last is None or not isinstance(last, BreakNode):
                if i + 1 < len(node.cases):
                    self._emit({"op": "jump", "target": case_labels[i + 1]})
                else:
                    self._emit({"op": "jump", "target": l_end})

        self._emit({"op": "label", "name": l_end})
        self._break_stack.pop()

    def _gen_break(self, node: BreakNode):
        """Emit an unconditional jump to the nearest enclosing loop/switch end."""
        if self._break_stack:
            self._emit({"op": "jump", "target": self._break_stack[-1]})

    def _gen_continue(self, node: ContinueNode):
        """Emit an unconditional jump to the nearest enclosing loop increment/start."""
        if self._continue_stack:
            self._emit({"op": "jump", "target": self._continue_stack[-1]})

    def _gen_return(self, node: ReturnNode):
        """Emit a return instruction, with or without a value."""
        if node.value is not None:
            val = self._gen_expr(node.value)
            self._emit({"op": "return", "value": val})
        else:
            self._emit({"op": "return", "value": None})

    # ── I/O statements ────────────────────────────────────────────────────────

    def _gen_io(self, node: IONode):
        """Emit TAC for view() or write() I/O statements.

        view(fmt, arg1, arg2, ...)  →  { op: "view", fmt: "...", args: [...] }
        write(fmt, &var1, ...)      →  { op: "write", fmt: "...", args: [...] }

        For view(), arguments are evaluated as expressions (their values matter).
        For write(), arguments are DESTINATIONS — we need their flat key names
        (e.g. "A[i]") so the runtime can store the input value into them.
        """
        if node.io_type == "write":
            arg_operands = [self._lhs_name(a) for a in node.args]
        else:
            arg_operands = [self._gen_expr(a) for a in node.args]
        self._emit({
            "op": node.io_type,          # "view" or "write"
            "fmt": node.format_string,
            "args": arg_operands,
        })

    # ── expression generation ─────────────────────────────────────────────────
    #
    # Every _gen_expr variant returns a single OPERAND STRING.
    #
    # Rules:
    #   - A LiteralNode or IdNode returns its value/name directly with NO
    #     instruction emitted (the operand is already atomic).
    #   - Any compound expression emits one or more instructions and returns
    #     the name of the temporary that holds the result.

    def _gen_expr(self, node) -> str:
        """Dispatch expression generation; return the resulting operand string."""
        if isinstance(node, LiteralNode):
            return self._gen_literal(node)
        if isinstance(node, IdNode):
            return self._gen_id(node)
        if isinstance(node, BinaryOpNode):
            return self._gen_binary(node)
        if isinstance(node, UnaryOpNode):
            return self._gen_unary(node)
        if isinstance(node, FunctionCallNode):
            return self._gen_call(node)
        if isinstance(node, ArrayAccessNode):
            return self._gen_array_access(node)
        if isinstance(node, StructAccessNode):
            return self._gen_struct_access(node)
        if isinstance(node, WallConcatNode):
            return self._gen_wall_concat(node)
        if isinstance(node, ArrayInitNode):
            # ArrayInitNode should not appear as a standalone expression —
            # it is handled specially in _gen_var_decl. If we get here,
            # return "0" as a fallback.
            return "0"
        # Fallback: return a literal "0" so the pipeline never crashes
        return "0"

    def _gen_literal(self, node: LiteralNode) -> str:
        """Return the literal's value as a string operand.

        wall (string) literals are returned with their quotes preserved
        so the runtime can distinguish them from variable names.
        brick (char) literals are returned as single-quoted strings.
        """
        if node.literal_type == "wall":
            # Preserve surrounding quotes for runtime string detection
            val = str(node.value)
            if not (val.startswith('"') and val.endswith('"')):
                val = f'"{val}"'
            return val
        if node.literal_type == "brick":
            val = str(node.value)
            return val
        if node.literal_type == "beam":
            # solid → True, fragile → False (Python bool strings for runtime)
            return "True" if str(node.value).lower() == "solid" else "False"
        # tile / glass: return the raw lexeme.
        # For glass (float) we must ensure the string contains a decimal point
        # so the runtime's _resolve() parses it back as float, not int.
        # If the lexer stored "6" instead of "6.0", this guards against that.
        val_str = str(node.value)
        if node.literal_type == "glass" and "." not in val_str:
            val_str = val_str + ".0"
        return val_str

    def _gen_id(self, node: IdNode) -> str:
        """Return the scope-resolved identifier name."""
        return self._resolve_name(node.name)

    def _gen_binary(self, node: BinaryOpNode) -> str:
        """Emit one binop instruction and return the result temporary.

        t_N = left_operand  operator  right_operand

        Special handling for short-circuit logical operators (Spec N.1):
          ||  — if the left operand is truthy, skip evaluating the right operand
                and set the result to True immediately.  This prevents side effects
                in the right operand (e.g. arr[index] when index is out of range).
          &&  — if the left operand is falsy, skip evaluating the right operand
                and set the result to False immediately.

        This matches C's short-circuit evaluation semantics and is critical for
        patterns like:  if (index < 0 || arr[index] <= value)
        where arr[index] must NOT be evaluated when index is negative.
        """
        op = node.operator

        # ── Short-circuit || ────────────────────────────────────────────────
        if op == "||":
            left_op = self._gen_expr(node.left)
            result_tmp = self._new_temp()
            l_short = self._new_label()   # jump here if left is true
            l_end   = self._new_label()   # end of || expression

            # If left is truthy → result is True, skip right side
            self._emit({"op": "jump_if", "cond": left_op, "target": l_short})

            # Left was falsy → evaluate right side, result = right
            right_op = self._gen_expr(node.right)
            self._emit({"op": "assign", "dest": result_tmp, "src": right_op})
            self._emit({"op": "jump", "target": l_end})

            # Short-circuit path: result = True
            self._emit({"op": "label", "name": l_short})
            self._emit({"op": "assign", "dest": result_tmp, "src": "True"})

            self._emit({"op": "label", "name": l_end})
            return result_tmp

        # ── Short-circuit && ────────────────────────────────────────────────
        if op == "&&":
            left_op = self._gen_expr(node.left)
            result_tmp = self._new_temp()
            l_short = self._new_label()   # jump here if left is false
            l_end   = self._new_label()   # end of && expression

            # If left is falsy → result is False, skip right side
            self._emit({"op": "jump_if_false", "cond": left_op, "target": l_short})

            # Left was truthy → evaluate right side, result = right
            right_op = self._gen_expr(node.right)
            self._emit({"op": "assign", "dest": result_tmp, "src": right_op})
            self._emit({"op": "jump", "target": l_end})

            # Short-circuit path: result = False
            self._emit({"op": "label", "name": l_short})
            self._emit({"op": "assign", "dest": result_tmp, "src": "False"})

            self._emit({"op": "label", "name": l_end})
            return result_tmp

        # ── All other binary operators: eager evaluation ────────────────────
        left_op = self._gen_expr(node.left)
        right_op = self._gen_expr(node.right)
        tmp = self._new_temp()
        instr = {
            "op": "binop",
            "dest": tmp,
            "left": left_op,
            "operator": op,
            "right": right_op,
        }
        # For division and modulo, annotate the result type from the semantic
        # analyzer so the runtime can distinguish tile/tile division (truncates)
        # from glass division (preserves fractional part).
        #
        # This is critical for the JS frontend interpreter where JavaScript
        # does not distinguish int and float (5.0 === 5).  Without this
        # annotation, glass 5.0 / glass 2.0 would be treated as integer
        # division because Number.isInteger(5) is true in JS.
        #
        # The Python runtime does not need this because Python's isinstance()
        # correctly distinguishes int from float.
        if op in ("/", "%"):
            expr_type = getattr(node, "expr_type", None)
            if expr_type:
                instr["result_type"] = expr_type
        self._emit(instr)
        return tmp

    def _gen_unary(self, node: UnaryOpNode) -> str:
        """Emit TAC for a unary operation and return the result operand.

        Prefix negation / logical-not:
            t1 = - operand

        Prefix/postfix ++ and --:
            Pre:   operand = operand + 1   (or -1),  return operand
            Post:  t_old = operand
                   operand = operand + 1
                   return t_old           (original value)
        """
        op = node.operator

        if op == "-":
            operand = self._gen_expr(node.operand)
            tmp = self._new_temp()
            self._emit({"op": "unary", "dest": tmp, "operator": "-", "operand": operand})
            return tmp

        if op == "!":
            operand = self._gen_expr(node.operand)
            tmp = self._new_temp()
            self._emit({"op": "unary", "dest": tmp, "operator": "!", "operand": operand})
            return tmp

        if op in ("++", "--"):
            var_name = self._lhs_name(node.operand)
            delta = "1"
            arith_op = "+" if op == "++" else "-"

            if node.is_prefix:
                # ++x  →  x = x + 1,  return x
                tmp = self._new_temp()
                self._emit({
                    "op": "binop",
                    "dest": tmp,
                    "left": var_name,
                    "operator": arith_op,
                    "right": delta,
                })
                self._emit({"op": "assign", "dest": var_name, "src": tmp})
                return var_name
            else:
                # x++  →  t_old = x,  x = x + 1,  return t_old
                t_old = self._new_temp()
                self._emit({"op": "assign", "dest": t_old, "src": var_name})
                tmp = self._new_temp()
                self._emit({
                    "op": "binop",
                    "dest": tmp,
                    "left": var_name,
                    "operator": arith_op,
                    "right": delta,
                })
                self._emit({"op": "assign", "dest": var_name, "src": tmp})
                return t_old

        # Unknown operator — return operand unchanged
        return self._gen_expr(node.operand)

    def _gen_call(self, node: FunctionCallNode) -> str:
        """Emit TAC for a function call and return the result temporary.

        Each argument is evaluated and placed into an arg list.
        The call instruction stores its return value in a new temporary.

        t1 = call func_name(arg1, arg2, ...)
        """
        arg_operands = [self._gen_expr(a) for a in node.args]
        tmp = self._new_temp()
        self._emit({
            "op": "call",
            "dest": tmp,
            "func": node.func_name,
            "args": arg_operands,
        })
        return tmp

    def _gen_array_access(self, node: ArrayAccessNode) -> str:
        """Emit TAC for an array element access and return the result temporary.

        arr[i]      →  t1 = arr[i]
        arr[i][j]   →  t1 = arr[i][j]
        """
        base = self._lhs_name(node.array)
        idx_strs = [self._gen_expr(i) for i in node.indices]
        subscript = "".join(f"[{s}]" for s in idx_strs)
        tmp = self._new_temp()
        self._emit({
            "op": "array_read",
            "dest": tmp,
            "src": f"{base}{subscript}",
        })
        return tmp

    def _gen_struct_access(self, node: StructAccessNode) -> str:
        """Emit TAC for a struct member read and return the result temporary.

        s.field  →  t1 = s.field
        """
        base = self._lhs_name(node.struct)
        tmp = self._new_temp()
        self._emit({
            "op": "struct_read",
            "dest": tmp,
            "src": f"{base}.{node.member}",
        })
        return tmp

    def _gen_wall_concat(self, node: WallConcatNode) -> str:
        """Emit TAC for a wall (string) concatenation chain.

        "hello" + name + "!"
            →   t1 = "hello" + name
                t2 = t1 + "!"
                return t2
        """
        if not node.parts:
            return '""'

        result = self._gen_expr(node.parts[0])
        for part in node.parts[1:]:
            right = self._gen_expr(part)
            tmp = self._new_temp()
            self._emit({
                "op": "binop",
                "dest": tmp,
                "left": result,
                "operator": "+",
                "right": right,
            })
            result = tmp
        return result


# ---------------------------------------------------------------------------
# tac_instruction_to_str  —  human-readable display of one instruction
# ---------------------------------------------------------------------------

def tac_instruction_to_str(instr: dict) -> str:
    """Convert one TAC instruction dict to a readable one-line string.

    This is used by the frontend to display the Intermediate Code panel.
    """
    op = instr.get("op", "")

    if op == "assign":
        return f"{instr['dest']} = {instr['src']}"

    if op == "binop":
        return f"{instr['dest']} = {instr['left']} {instr['operator']} {instr['right']}"

    if op == "unary":
        return f"{instr['dest']} = {instr['operator']}{instr['operand']}"

    if op == "label":
        return f"{instr['name']}:"

    if op == "jump":
        return f"goto {instr['target']}"

    if op == "jump_if":
        return f"if {instr['cond']} goto {instr['target']}"

    if op == "jump_if_false":
        return f"if_false {instr['cond']} goto {instr['target']}"

    if op == "call":
        args = ", ".join(instr.get("args", []))
        return f"{instr['dest']} = call {instr['func']}({args})"

    if op == "view":
        fmt = instr.get("fmt", "")
        args = ", ".join(instr.get("args", []))
        if args:
            return f'view {fmt}, {args}'
        return f'view {fmt}'

    if op == "write":
        fmt = instr.get("fmt", "")
        args = ", ".join(instr.get("args", []))
        if args:
            return f'write {fmt}, {args}'
        return f'write {fmt}'

    if op == "return":
        val = instr.get("value")
        return f"return {val}" if val is not None else "return"

    if op == "array_read":
        return f"{instr['dest']} = {instr['src']}"

    if op == "struct_read":
        return f"{instr['dest']} = {instr['src']}"

    if op == "func_begin":
        params = ", ".join(instr.get("params", []))
        return f"---- begin {instr['name']}({params}) ----"

    if op == "func_end":
        return f"---- end {instr['name']} ----"

    # Fallback: repr the whole dict
    return str(instr)