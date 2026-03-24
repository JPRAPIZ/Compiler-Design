from typing import List, Optional
from semantic.ast import (
    ProgramNode, FunctionNode, ParamNode,
    VarDeclNode, StructDeclNode,
    AssignNode, IfNode, WhileNode, DoWhileNode, ForNode,
    SwitchNode, CaseNode, BreakNode, ContinueNode, ReturnNode, IONode,
    BinaryOpNode, UnaryOpNode, LiteralNode, IdNode,
    ArrayAccessNode, StructAccessNode, FunctionCallNode, WallConcatNode,
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

    # ── function definitions ──────────────────────────────────────────────────

    def _gen_function(self, func: FunctionNode):
        """Emit TAC for one function definition.

        Structure emitted:
            func_begin  name  params=[...]
            <body instructions>
            func_end    name

        Parameters are listed in func_begin so the runtime can bind them
        when the function is called.
        """
        param_names = [p.name for p in func.params]

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
            # Standalone call statement — return value is discarded
            self._gen_expr(node)
        elif isinstance(node, UnaryOpNode):
            # Standalone postfix/prefix ++ or -- used as a statement
            self._gen_expr(node)
        # Other node types are silently skipped

    # ── declarations ─────────────────────────────────────────────────────────

    def _gen_var_decl(self, node: VarDeclNode):
        """Emit TAC for a local variable declaration.

        tile x = expr;   →   <emit expr into t1>   x = t1
        tile x;          →   x = 0          (zero-init)
        wall s = "hi";   →   s = "hi"
        """
        if node.init_value is not None:
            src = self._gen_expr(node.init_value)
        else:
            src = '""' if node.type == "wall" else "0"

        self._emit({
            "op": "assign",
            "dest": node.name,
            "src": src,
        })

    # ── assignment ────────────────────────────────────────────────────────────

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

        if node.operator == "=":
            self._emit({
                "op": "assign",
                "dest": dest,
                "src": rhs_operand,
            })
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
            self._emit({
                "op": "assign",
                "dest": dest,
                "src": tmp,
            })

    def _lhs_name(self, target) -> str:
        """Compute the string name for an LHS target.

        IdNode            → "x"
        ArrayAccessNode   → "arr[i]"  or  "arr[i][j]"
        StructAccessNode  → "s.field"
        """
        if isinstance(target, IdNode):
            return target.name

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
        """Emit TAC for an if / else-if / else statement.

        Pattern:
            <eval condition → cond_t>
            if_false cond_t goto L_else
            <then body>
            goto L_end
            L_else:
            <else body>        (omitted if no else)
            L_end:
        """
        cond_t = self._gen_expr(node.condition)

        if node.else_body:
            l_else = self._new_label()
            l_end = self._new_label()

            self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_else})

            for stmt in node.then_body:
                self._gen_stmt(stmt)

            self._emit({"op": "jump", "target": l_end})
            self._emit({"op": "label", "name": l_else})

            for stmt in node.else_body:
                self._gen_stmt(stmt)

            self._emit({"op": "label", "name": l_end})

        else:
            l_end = self._new_label()
            self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_end})

            for stmt in node.then_body:
                self._gen_stmt(stmt)

            self._emit({"op": "label", "name": l_end})

    def _gen_while(self, node: WhileNode):
        """Emit TAC for a while loop.

        Pattern:
            L_start:
            <eval condition → cond_t>
            if_false cond_t goto L_end
            <body>
            goto L_start
            L_end:
        """
        l_start = self._new_label()
        l_end = self._new_label()

        self._break_stack.append(l_end)
        self._continue_stack.append(l_start)

        self._emit({"op": "label", "name": l_start})
        cond_t = self._gen_expr(node.condition)
        self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_end})

        for stmt in node.body:
            self._gen_stmt(stmt)

        self._emit({"op": "jump", "target": l_start})
        self._emit({"op": "label", "name": l_end})

        self._break_stack.pop()
        self._continue_stack.pop()

    def _gen_dowhile(self, node: DoWhileNode):
        """Emit TAC for a do-while loop.

        Pattern:
            L_start:
            <body>
            L_cond:
            <eval condition → cond_t>
            if cond_t goto L_start
            L_end:
        """
        l_start = self._new_label()
        l_cond = self._new_label()
        l_end = self._new_label()

        self._break_stack.append(l_end)
        self._continue_stack.append(l_cond)

        self._emit({"op": "label", "name": l_start})

        for stmt in node.body:
            self._gen_stmt(stmt)

        self._emit({"op": "label", "name": l_cond})
        cond_t = self._gen_expr(node.condition)
        self._emit({"op": "jump_if", "cond": cond_t, "target": l_start})
        self._emit({"op": "label", "name": l_end})

        self._break_stack.pop()
        self._continue_stack.pop()

    def _gen_for(self, node: ForNode):
        """Emit TAC for a for loop.

        Pattern:
            <init>
            L_start:
            <eval condition → cond_t>
            if_false cond_t goto L_end
            <body>
            L_incr:
            <increment>
            goto L_start
            L_end:

        L_incr is the continue target so 'mend' skips to the increment.
        """
        l_start = self._new_label()
        l_incr = self._new_label()
        l_end = self._new_label()

        self._break_stack.append(l_end)
        self._continue_stack.append(l_incr)

        # Init (may be VarDeclNode or AssignNode or None)
        if node.init is not None:
            self._gen_stmt(node.init)

        self._emit({"op": "label", "name": l_start})
        cond_t = self._gen_expr(node.condition)
        self._emit({"op": "jump_if_false", "cond": cond_t, "target": l_end})

        for stmt in node.body:
            self._gen_stmt(stmt)

        self._emit({"op": "label", "name": l_incr})
        # Increment is an expression node (typically a UnaryOpNode)
        self._gen_expr(node.increment)

        self._emit({"op": "jump", "target": l_start})
        self._emit({"op": "label", "name": l_end})

        self._break_stack.pop()
        self._continue_stack.pop()

    def _gen_switch(self, node: SwitchNode):
        """Emit TAC for a switch (room) statement.

        Pattern for each non-default case:
            <eval switch expr → sw_t>
            t_cmp = sw_t == case_val
            if t_cmp goto L_case_N
            ...
            goto L_default   (or L_end if no default)
            L_case_N:
            <case body>
            goto L_end        (implicit fall-through prevention)
            ...
            L_default:
            <default body>
            L_end:
        """
        sw_t = self._gen_expr(node.expr)
        l_end = self._new_label()

        self._break_stack.append(l_end)

        # Pre-allocate labels for each case body
        case_labels = [self._new_label() for _ in node.cases]
        default_label = None
        for i, case in enumerate(node.cases):
            if case.is_default:
                default_label = case_labels[i]

        # Emit comparison jumps
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

        # Jump to default or end
        if default_label:
            self._emit({"op": "jump", "target": default_label})
        else:
            self._emit({"op": "jump", "target": l_end})

        # Emit case bodies
        # Spec K.5 §12: without crack (break), execution falls through to the
        # next case. Only emit an unconditional jump to l_end when the case body
        # has no BreakNode at the end (i.e. break was explicit).
        for i, case in enumerate(node.cases):
            self._emit({"op": "label", "name": case_labels[i]})
            for stmt in case.body:
                self._gen_stmt(stmt)
            # Only jump to end if the last statement was NOT a break
            # (break itself already emits a jump to l_end via _gen_break)
            last = case.body[-1] if case.body else None
            if last is None or not isinstance(last, BreakNode):
                # Fall through: jump to NEXT case label (or l_end if last case)
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

        Each argument expression is evaluated into an operand string first.
        """
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
        """Return the identifier name directly — no instruction needed."""
        return node.name

    def _gen_binary(self, node: BinaryOpNode) -> str:
        """Emit one binop instruction and return the result temporary.

        t_N = left_operand  operator  right_operand
        """
        left_op = self._gen_expr(node.left)
        right_op = self._gen_expr(node.right)
        tmp = self._new_temp()
        self._emit({
            "op": "binop",
            "dest": tmp,
            "left": left_op,
            "operator": node.operator,
            "right": right_op,
        })
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