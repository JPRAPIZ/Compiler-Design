from typing import List, Dict, Any, Optional
import re
import math


# ---------------------------------------------------------------------------
# ActivationRecord  —  one stack frame for a function call
# ---------------------------------------------------------------------------

class ActivationRecord:
    """Holds the local state for one active function call.

    Attributes
    ----------
    func_name    — name of the function being executed.
    local_memory — local variable/temporary dict for this call.
    return_addr  — instruction index to resume after this call returns.
    return_dest  — name of the caller's temporary to store the return value.
    return_value — the value produced by 'home' (return), or None.
    """

    def __init__(self, func_name: str, return_addr: int, return_dest: Optional[str]):
        self.func_name = func_name
        self.local_memory: Dict[str, Any] = {}
        self.return_addr = return_addr
        self.return_dest = return_dest
        self.return_value = None


# ---------------------------------------------------------------------------
# TACInterpreter
# ---------------------------------------------------------------------------

class TACInterpreter:
    """Executes a list of TAC instruction dicts produced by TACGenerator.

    Usage
    -----
        interp = TACInterpreter(instructions)
        result = interp.run()
        print(result["output"])   # list of output lines
        print(result["memory"])   # final global memory state
    """

    # Maximum loop iterations before the interpreter aborts (infinite loop guard)
    MAX_ITERATIONS = 10_000_000

    def __init__(self, instructions: List[dict], stdin: List[str] = []):
        self.instructions = instructions

        # ── runtime state ─────────────────────────────────────────────────
        self.global_memory: Dict[str, Any] = {}   # global variables
        self.call_stack: List[ActivationRecord] = []  # function call stack
        self.output: List[str] = []               # accumulated view() output
        self.runtime_errors: List[str] = []       # non-fatal runtime errors
        self._stdin: List[str] = list(stdin)          # pre-supplied input values (queue)

        # ── control flow ──────────────────────────────────────────────────
        self.pc: int = 0                          # program counter (index into instructions)
        self._iteration_count: int = 0

        # Pre-build a label → pc index map for O(1) jump resolution
        self._label_map: Dict[str, int] = {}
        for idx, instr in enumerate(instructions):
            if instr.get("op") == "label":
                self._label_map[instr["name"]] = idx

        # Pre-build a func_name → pc index map for O(1) function lookup
        self._func_map: Dict[str, int] = {}
        for idx, instr in enumerate(instructions):
            if instr.get("op") == "func_begin":
                self._func_map[instr["name"]] = idx

        # Format string cache — pre-processed (unquoted + unescaped) fmt strings
        # avoids repeating strip/replace work on every view() call in a loop.
        self._fmt_cache: Dict[str, str] = {}

        # Compiled regex for format specifier detection (used in _format_view)
        # Supports: #d, #f, #c, #s, #b, and #.Nf (precision, e.g. #.2f)
        # arCh uses # exclusively — % is not a valid format prefix
        self._spec_re = re.compile(r'#(?:\.\d+)?[dfcsb]')

        # Literal value cache — avoids re-parsing "123", "3.14", "True", etc.
        # on every instruction execution inside tight loops.
        self._literal_cache: Dict[str, Any] = {}

    # ── public entry point ────────────────────────────────────────────────────

    def run(self) -> dict:
        """Execute all instructions and return the result dict.

        Returns
        -------
        {
            "output":  list[str]   — lines printed by view()
            "memory":  dict        — final global memory state
            "errors":  list[str]   — runtime error messages
        }
        """
        self.pc = 0
        self._iteration_count = 0

        # Execute globals first (instructions before any func_begin)
        # Then look for blueprint() and call it as the entry point.
        self._execute_globals()
        self._call_blueprint()

        # If runtime errors occurred, discard the output — it is incomplete
        # or produced from invalid state and would mislead the user.
        final_output = [] if self.runtime_errors else list(self.output)

        return {
            "output": final_output,
            "memory": {k: self._serialize(v)
                       for k, v in self.global_memory.items()
                       if not k.startswith("t")},   # hide temporaries
            "errors": list(self.runtime_errors),
        }

    # ── global initialisation ─────────────────────────────────────────────────

    def _execute_globals(self):
        """Execute all instructions that appear BEFORE the first func_begin.

        These are global variable initialisations emitted by TACGenerator
        for the 'roof' declarations.
        """
        for idx, instr in enumerate(self.instructions):
            if instr.get("op") == "func_begin":
                break
            self._execute_one(instr, self.global_memory)

    def _call_blueprint(self):
        """Find and call the blueprint() entry point, if it exists."""
        if "blueprint" not in self._func_map:
            return
        self._call_function("blueprint", [], dest=None, return_addr=len(self.instructions))

    # ── main execution loop ───────────────────────────────────────────────────

    def _call_function(self, func_name: str, args: List[Any],
                       dest: Optional[str], return_addr: int):
        """Set up an activation record and run the function body.

        This is a direct (non-recursive) interpreter loop — function bodies
        are executed inline by manipulating self.pc, not by recursing in Python.
        We push an ActivationRecord and then continue the main loop.
        """
        if func_name not in self._func_map:
            self.runtime_errors.append(f"Runtime error: undefined function '{func_name}'")
            return

        func_pc = self._func_map[func_name]
        func_instr = self.instructions[func_pc]
        param_names = func_instr.get("params", [])

        record = ActivationRecord(func_name, return_addr, dest)
        # Bind arguments to parameter names
        for i, pname in enumerate(param_names):
            record.local_memory[pname] = args[i] if i < len(args) else 0

        self.call_stack.append(record)
        self.pc = func_pc + 1  # start executing just after func_begin

        # Run until the call stack is back to its pre-call depth
        depth = len(self.call_stack)
        while self.pc < len(self.instructions) and len(self.call_stack) >= depth:
            self._iteration_count += 1
            if self._iteration_count > self.MAX_ITERATIONS:
                self.runtime_errors.append(
                    "Infinite loop detected"
                )
                break
            instr = self.instructions[self.pc]
            self.pc += 1
            self._execute_one(instr, self._current_memory())

    def _current_memory(self) -> Dict[str, Any]:
        """Return the local memory dict of the current activation record."""
        if self.call_stack:
            return self.call_stack[-1].local_memory
        return self.global_memory

    # ── single instruction execution ─────────────────────────────────────────

    def _execute_one(self, instr: dict, mem: Dict[str, Any]):
        """Execute one TAC instruction dict in the context of `mem`."""
        op = instr.get("op", "")

        # ── data movement ─────────────────────────────────────────────────
        if op == "assign":
            dest = instr["dest"]
            val = self._resolve(instr["src"], mem)
            # If dest contains subscripts with variable indices (e.g. "arr[i]"),
            # resolve the index variables to build the correct flat key.
            if "[" in dest:
                dest = self._resolve_dest_key(dest, mem)
            mem[dest] = val

        elif op == "binop":
            left  = self._resolve(instr["left"],  mem)
            right = self._resolve(instr["right"], mem)
            result = self._apply_binop(instr["operator"], left, right)
            mem[instr["dest"]] = result

        elif op == "unary":
            operand = self._resolve(instr["operand"], mem)
            result  = self._apply_unary(instr["operator"], operand)
            mem[instr["dest"]] = result

        # ── control flow ──────────────────────────────────────────────────
        elif op == "label":
            pass  # labels are no-ops during execution

        elif op == "jump":
            self._jump_to(instr["target"])

        elif op == "jump_if":
            cond = self._resolve(instr["cond"], mem)
            if self._is_truthy(cond):
                self._jump_to(instr["target"])

        elif op == "jump_if_false":
            cond = self._resolve(instr["cond"], mem)
            if not self._is_truthy(cond):
                self._jump_to(instr["target"])

        # ── function call ─────────────────────────────────────────────────
        elif op == "call":
            func_name = instr["func"]
            raw_args  = instr.get("args", [])
            arg_vals  = [self._resolve(a, mem) for a in raw_args]
            dest      = instr.get("dest")

            result = self._try_builtin(func_name, arg_vals, mem)
            if result is not None:
                # Built-in returned a value
                if dest:
                    mem[dest] = result
            else:
                # User-defined function — save current pc as return address
                return_addr = self.pc
                self._call_function(func_name, arg_vals, dest=dest,
                                    return_addr=return_addr)

        # ── I/O ───────────────────────────────────────────────────────────
        elif op == "view":
            fmt      = instr.get("fmt", "")
            raw_args = instr.get("args", [])
            arg_vals = [self._resolve(a, mem) for a in raw_args]
            line     = self._format_view(fmt, arg_vals)
            self.output.append(line)

        elif op == "write":
            # Consume one value from the stdin queue per argument.
            # If the queue is exhausted, fall back to defaults.
            raw_args = instr.get("args", [])
            fmt = instr.get("fmt", "")
            # Parse format specifiers to match each arg to its expected type
            specs = self._spec_re.findall(fmt)
            for i, arg in enumerate(raw_args):
                spec = specs[i] if i < len(specs) else specs[0] if specs else "#d"
                kind = spec[-1]  # d, f, c, s, b
                if self._stdin:
                    raw = self._stdin.pop(0)
                    try:
                        if kind == "s":
                            mem[arg] = raw           # wall: store as string
                        elif kind == "c":
                            mem[arg] = raw[0] if raw else '\0'  # brick: single char
                        elif kind == "f":
                            mem[arg] = float(raw)    # glass: float
                        elif kind == "b":
                            mem[arg] = raw.strip().lower() in ("solid", "true", "1")
                        else:
                            mem[arg] = int(raw)      # tile: integer (default)
                    except (ValueError, TypeError, IndexError):
                        if kind == "s":
                            mem[arg] = ""
                        elif kind == "f":
                            mem[arg] = 0.0
                        elif kind == "c":
                            mem[arg] = '\0'
                        else:
                            mem[arg] = 0
                else:
                    # No more stdin — use type-appropriate default
                    if kind == "s":
                        mem[arg] = ""
                    elif kind == "f":
                        mem[arg] = 0.0
                    elif kind == "c":
                        mem[arg] = '\0'
                    else:
                        mem[arg] = 0

        # ── return ────────────────────────────────────────────────────────
        elif op == "return":
            val = instr.get("value")
            ret_val = self._resolve(val, mem) if val is not None else None

            if self.call_stack:
                record = self.call_stack.pop()
                record.return_value = ret_val
                # Write return value into the caller's destination temp
                if record.return_dest is not None:
                    caller_mem = self._current_memory()
                    caller_mem[record.return_dest] = ret_val
                # Resume at return address
                self.pc = record.return_addr

        # ── array / struct reads ─────────────────────────────────────────
        elif op == "array_read":
            src = instr["src"]
            val = self._resolve_complex(src, mem)
            mem[instr["dest"]] = val

        elif op == "struct_read":
            src = instr["src"]
            val = self._resolve_complex(src, mem)
            mem[instr["dest"]] = val

        # ── function begin / end ─────────────────────────────────────────
        elif op == "func_begin":
            pass  # handled by _call_function setup

        elif op == "func_end":
            # Implicit void return if we fall off the end
            if self.call_stack:
                record = self.call_stack.pop()
                if record.return_dest is not None:
                    caller_mem = self._current_memory()
                    caller_mem[record.return_dest] = None
                self.pc = record.return_addr

    # ── value resolution ──────────────────────────────────────────────────────

    def _resolve(self, operand: Any, mem: Dict[str, Any]) -> Any:
        """Resolve a TAC operand string to its runtime value.

        Resolution order:
          1. None or already a non-string Python value → return as-is.
          2. "True" / "False" string literals → Python bool.
          3. Quoted string "..." → strip quotes, return Python str.
          4. Integer literal → Python int.
          5. Float literal → Python float.
          6. Name found in local memory → return that value.
          7. Name found in global memory → return that value.
          8. Unknown → emit a runtime error, return 0.
        """
        if operand is None:
            return None
        if not isinstance(operand, str):
            return operand

        # Fast path: variable lookup first (most common case in tight loops)
        if operand in mem:
            return mem[operand]
        if mem is not self.global_memory and operand in self.global_memory:
            return self.global_memory[operand]

        # Check literal cache before re-parsing
        if operand in self._literal_cache:
            return self._literal_cache[operand]

        # Boolean literals
        if operand == "True":
            self._literal_cache[operand] = True
            return True
        if operand == "False":
            self._literal_cache[operand] = False
            return False

        # Quoted wall (string) literal
        if operand.startswith('"') and operand.endswith('"'):
            val = operand[1:-1]
            self._literal_cache[operand] = val
            return val

        # Single-quoted brick (char) literal: 'A' → ord('A'), '\n' → 10
        if operand.startswith("'") and operand.endswith("'"):
            inner = operand[1:-1]
            if inner.startswith("\\") and len(inner) == 2:
                # Escape sequence
                esc_map = {'n': 10, 't': 9, '\\': 92, "'": 39, '"': 34, '0': 0}
                val = esc_map.get(inner[1], ord(inner[1]))
            elif len(inner) == 1:
                val = ord(inner)
            else:
                val = 0
            self._literal_cache[operand] = val
            return val

        # Numeric literals
        try:
            if "." in operand:
                val = float(operand)
            else:
                val = int(operand)
            self._literal_cache[operand] = val
            return val
        except ValueError:
            pass

        # Unresolved name
        self.runtime_errors.append(
            f"Runtime error: undefined variable '{operand}'"
        )
        return 0

    def _resolve_dest_key(self, dest: str, mem: Dict[str, Any]) -> str:
        """Resolve variable indices in an assignment destination key.

        "arr[0]"  → "arr[0]"  (literal index, no change)
        "arr[i]"  → "arr[3]"  (resolve i to its runtime value)
        "arr[i][j]" → "arr[3][1]"
        """
        match = re.match(r'^(\w+)((?:\[[^\]]+\])+)$', dest)
        if not match:
            return dest
        base = match.group(1)
        indices_str = match.group(2)
        index_exprs = re.findall(r'\[([^\]]+)\]', indices_str)
        resolved = []
        for idx_expr in index_exprs:
            idx = self._resolve(idx_expr.strip(), mem)
            resolved.append(str(int(idx)) if isinstance(idx, (int, float)) else str(idx))
        return base + "".join(f"[{r}]" for r in resolved)

    def _resolve_complex(self, src: str, mem: Dict[str, Any]) -> Any:
        """Resolve array subscript or struct member access strings.

        "arr[2]"      → mem["arr"][2]   (or dict key if arr is a dict)
        "arr[i]"      → mem["arr"][resolve("i")]
        "arr[i][j]"   → nested access
        "s.field"     → mem["s"]["field"]  or  mem["s.field"]
        """
        # Struct access: name.member
        if "." in src and "[" not in src:
            parts = src.split(".", 1)
            struct_val = self._resolve(parts[0], mem)
            if isinstance(struct_val, dict):
                return struct_val.get(parts[1], 0)
            # Fall back to flat key "s.field"
            key = src
            if key in mem:
                return mem[key]
            return 0

        # Array access: name[idx] or name[i][j]
        match = re.match(r'^(\w+)((?:\[[^\]]+\])+)$', src)
        if match:
            base_name = match.group(1)
            indices_str = match.group(2)
            index_exprs = re.findall(r'\[([^\]]+)\]', indices_str)

            # First try: resolve indices and build a flat key for lookup.
            # TAC stores array elements as flat keys like "arr[0]" or "arr[1][2]".
            resolved_indices = []
            for idx_expr in index_exprs:
                idx = self._resolve(idx_expr.strip(), mem)
                resolved_indices.append(idx)

            flat_key = base_name + "".join(f"[{i}]" for i in resolved_indices)
            # Check flat key in local memory, then global
            if flat_key in mem:
                return mem[flat_key]
            if mem is not self.global_memory and flat_key in self.global_memory:
                return self.global_memory[flat_key]

            # Second try: base is an actual list/dict object in memory
            base_val = self._resolve(base_name, mem)
            if isinstance(base_val, (list, dict)):
                for idx in resolved_indices:
                    try:
                        if isinstance(base_val, dict):
                            base_val = base_val[idx]
                        elif isinstance(base_val, list):
                            base_val = base_val[int(idx)]
                        else:
                            return 0
                    except (KeyError, IndexError, TypeError):
                        return 0
                return base_val

            return 0

        # Plain name
        return self._resolve(src, mem)

    # ── arithmetic and logic ──────────────────────────────────────────────────

    def _apply_binop(self, operator: str, left: Any, right: Any) -> Any:
        """Apply a binary operator to two resolved Python values.

        Mirrors the arCh type hierarchy:
          - Numeric operations use Python int/float naturally.
          - String '+' concatenates wall values.
          - Comparison operators return Python bool (beam).
        """
        try:
            if operator == "+":
                # String concatenation if either operand is a str
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return left + right
            if operator == "-":
                return left - right
            if operator == "*":
                return left * right
            if operator == "/":
                if right == 0:
                    self.runtime_errors.append(
                        "Runtime error: division by zero"
                    )
                    return 0
                # Integer division when both operands are int (tile behaviour)
                # Use math.trunc for C-style truncation toward zero
                if isinstance(left, int) and isinstance(right, int):
                    return math.trunc(left / right)
                return left / right
            if operator == "%":
                if right == 0:
                    self.runtime_errors.append(
                        "Runtime error: modulo by zero"
                    )
                    return 0
                # C-style truncated modulo (sign follows dividend, not divisor)
                # Python's % uses floor semantics which differs for negative numbers
                if isinstance(left, int) and isinstance(right, int):
                    return int(math.fmod(left, right))
                return math.fmod(left, right)
            if operator == "<":
                return left < right
            if operator == "<=":
                return left <= right
            if operator == ">":
                return left > right
            if operator == ">=":
                return left >= right
            if operator == "==":
                return left == right
            if operator == "!=":
                return left != right
            if operator == "&&":
                return bool(left) and bool(right)
            if operator == "||":
                return bool(left) or bool(right)
        except (TypeError, ValueError) as exc:
            self.runtime_errors.append(f"Runtime error in '{operator}': {exc}")
            return 0
        return 0

    def _apply_unary(self, operator: str, operand: Any) -> Any:
        """Apply a unary operator to a resolved Python value."""
        try:
            if operator == "-":
                return -operand
            if operator == "!":
                return not bool(operand)
        except TypeError as exc:
            self.runtime_errors.append(f"Runtime error in unary '{operator}': {exc}")
            return 0
        return operand

    def _is_truthy(self, value: Any) -> bool:
        """Evaluate a runtime value as a boolean condition."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        return bool(value)

    # ── control flow helpers ──────────────────────────────────────────────────

    def _jump_to(self, label: str):
        """Set the program counter to the instruction after the named label."""
        if label in self._label_map:
            # pc will be incremented by the caller's loop, so point TO the label
            # instruction (which is a no-op) — the next iteration will advance past it
            self.pc = self._label_map[label]
        else:
            self.runtime_errors.append(f"Runtime error: undefined label '{label}'")

    # ── built-in function dispatch ────────────────────────────────────────────

    def _try_builtin(self, func_name: str, args: List[Any],
                     mem: Dict[str, Any]) -> Optional[Any]:
        """Handle calls to language built-ins that have no TAC body.

        Returns the result value if the function was handled, or None to
        signal that the caller should look up a user-defined function.
        """
        # view and write are emitted as dedicated op="view"/"write" instructions,
        # not as call instructions, so they should not normally appear here.
        # However, if they do (e.g. from a FunctionCallNode), handle them.
        if func_name == "view":
            fmt = str(args[0]) if args else ""
            line = self._format_view(fmt, args[1:])
            self.output.append(line)
            return None  # void

        if func_name == "write":
            return None  # void

        return None  # not a built-in; caller will look up user function

    # ── view() format string processing ──────────────────────────────────────

    def _format_view(self, fmt: str, args: List[Any]) -> str:
        """Produce a formatted output string from a view() call.

        Strips surrounding quotes from the format string, then substitutes
        each format specifier with the corresponding argument value.

        Supported specifiers (arCh uses # as the format prefix):
            #d   → integer          (tile)
            #f   → float            (glass)
            #c   → character        (brick)
            #s   → string           (wall)
            #b   → boolean          (beam)
            \\n  → newline
            \\t  → tab

        arCh uses # as the format prefix exclusively (e.g. #d, #f, #.2f).

        If there are NO format specifiers and there are arguments, all
        argument values are joined with spaces and returned.  This handles
        the common case  view(x)  where the user just wants to print a value.
        """
        # Use cached pre-processed format string to avoid redundant work
        # on repeated calls to the same view() inside a loop.
        if fmt in self._fmt_cache:
            clean = self._fmt_cache[fmt]
        else:
            clean = fmt
            if clean.startswith('"') and clean.endswith('"'):
                clean = clean[1:-1]
            # Process all arCh escape sequences (spec B.3 §5-11)
            # Use single-pass replacement to avoid double-processing
            # (e.g. \\n should become \n-literal-chars, not backslash+newline)
            result = []
            i = 0
            while i < len(clean):
                if clean[i] == '\\' and i + 1 < len(clean):
                    nxt = clean[i + 1]
                    if   nxt == 'n':  result.append('\n')
                    elif nxt == 't':  result.append('\t')
                    elif nxt == '\\': result.append('\\')
                    elif nxt == "'":  result.append("'")
                    elif nxt == '"':  result.append('"')
                    elif nxt == '0':  result.append('\0')
                    else:             result.append(clean[i]); result.append(nxt)
                    i += 2
                else:
                    result.append(clean[i])
                    i += 1
            clean = ''.join(result)
            self._fmt_cache[fmt] = clean

        # Count format specifiers
        specifiers = self._spec_re.findall(clean)

        if not specifiers:
            # No format specifiers: just print the format string itself,
            # plus any extra arguments space-separated
            if args:
                # Likely a plain view(x) or view("text", x) call
                all_vals = [self._display_value(a) for a in args]
                if clean:
                    return clean + " " + " ".join(all_vals)
                return " ".join(all_vals)
            return clean

        # Substitute specifiers with argument values
        result = clean
        for i, spec in enumerate(specifiers):
            if i >= len(args):
                break
            replacement = self._format_specifier(spec, args[i])
            result = result.replace(spec, replacement, 1)

        return result

    def _format_specifier(self, spec: str, value: Any) -> str:
        """Format one value according to a single format specifier.

        arCh uses # as the format prefix exclusively.
        Supports: #d, #f, #c, #s, #b, and #.Nf (precision specifier).
        Example: #.2f formats a float to 2 decimal places.
        """
        kind = spec[-1]   # the letter: d / f / c / s / b
        # Extract precision for #.Nf patterns (e.g. "#.2f" → precision=2)
        precision = None
        if '.' in spec:
            try:
                precision = int(spec[spec.index('.') + 1:-1])
            except (ValueError, IndexError):
                pass
        try:
            if kind == "d":
                return str(int(value))
            if kind == "f":
                prec = precision if precision is not None else 7
                return f"{float(value):.{prec}f}"
            if kind == "c":
                if isinstance(value, int):
                    return chr(value)
                return str(value)
            if kind == "s":
                return str(value)
            if kind == "b":
                return "solid" if bool(value) else "fragile"
        except (ValueError, TypeError):
            return str(value)
        return str(value)

    def _display_value(self, value: Any) -> str:
        """Format a value for display without a format specifier."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "solid" if value else "fragile"
        if isinstance(value, float):
            # Trim unnecessary trailing zeros (e.g. 3.0 → "3", 3.14 → "3.14")
            formatted = f"{value:.6f}".rstrip("0").rstrip(".")
            return formatted
        return str(value)

    # ── serialisation for the API response ───────────────────────────────────

    def _serialize(self, value: Any) -> Any:
        """Convert a Python runtime value to a JSON-serialisable form."""
        if isinstance(value, bool):
            return "solid" if value else "fragile"
        if isinstance(value, (int, float, str)) or value is None:
            return value
        if isinstance(value, list):
            return [self._serialize(v) for v in value]
        if isinstance(value, dict):
            return {str(k): self._serialize(v) for k, v in value.items()}
        return str(value)