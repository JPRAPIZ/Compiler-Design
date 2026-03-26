# =============================================================================
# tac/tac_optimizer.py  —  Phase 5: Code Optimization
# =============================================================================
#
# ROLE IN THE PIPELINE
# --------------------
#   Phase 1 — Lexical Analysis      (lexer/)
#   Phase 2 — Syntax Analysis       (parser/)
#   Phase 3 — Semantic Analysis     (semantic/)
#   Phase 4 — Intermediate Code Gen (tac/tac_generator.py)
#   Phase 5 — Code Optimization     ← THIS FILE
#   Phase 6 — Code Generation       (tac/tac_codegen.py)
#   Runtime  — TAC Interpreter      (tac/tac_runtime.py)  [demo only]
#
# WHAT THIS MODULE DOES
# ---------------------
# Receives the flat TAC instruction list from TACGenerator and applies a
# series of safe, meaning-preserving transformations to produce a shorter
# and faster instruction list.
#
# OPTIMIZATIONS APPLIED (in order)
# ---------------------------------
#   1. Constant Folding
#      If both operands of a binop are numeric literals, compute the result
#      at compile time and replace the binop with a single assign.
#      Example:
#        t1 = 2 * 3     →   t1 = 6
#        t2 = 10 - 4    →   t2 = 6
#
#   2. Redundant Temporary Elimination
#      If a temporary is assigned a value and then immediately copied to
#      another variable without being used anywhere else, remove the
#      temporary and use the source value directly.
#      Example:
#        t1 = a + b
#        sum = t1        →   sum = a + b   (t1 eliminated)
#
#   3. Dead Code Elimination
#      Remove instructions that appear after an unconditional jump (goto)
#      and before the next label.  These instructions can never be reached.
#      Example:
#        goto L2
#        x = 5           ← unreachable, removed
#        y = 10          ← unreachable, removed
#        L2:
#
# WHAT THIS MODULE DOES NOT DO
# ----------------------------
#   - Loop optimizations (hoisting, unrolling)
#   - Register allocation
#   - Global value numbering
#   - Inlining
#   These are Phase 5 extensions beyond the scope of this course.
#
# USAGE
# -----
#   optimizer = TACOptimizer(instructions)
#   result    = optimizer.optimize()
#
#   result["instructions"]  — optimized TAC instruction list
#   result["stats"]         — dict of counts per optimization applied
#   result["log"]           — list of human-readable descriptions of changes
#   result["errors"]        — list of error dicts (normally empty)
#
# =============================================================================

from typing import List, Dict, Any, Optional


class TACOptimizer:
    """Applies safe peephole optimizations to a TAC instruction list.

    All optimizations are meaning-preserving: the observable output of the
    program is identical before and after optimization.
    """

    def __init__(self, instructions: List[dict]):
        self.instructions: List[dict] = [dict(i) for i in instructions]  # work on a copy
        self.log: List[str] = []
        self.errors: List[dict] = []
        self.stats: Dict[str, int] = {
            "constant_folds":           0,
            "redundant_temps_removed":  0,
            "dead_instructions_removed": 0,
        }

    # ── public entry point ────────────────────────────────────────────────────

    def optimize(self) -> dict:
        """Run all optimization passes and return the result dict."""
        try:
            self._pass_constant_folding()
            self._pass_redundant_temp_elimination()
            self._pass_dead_code_elimination()
        except Exception as exc:
            self.errors.append({
                "line":    1,
                "col":     1,
                "message": f"Optimization error: {exc}",
            })

        return {
            "instructions": self.instructions,
            "stats":        self.stats,
            "log":          self.log,
            "errors":       self.errors,
        }

    # ── Pass 1: Constant Folding ──────────────────────────────────────────────

    def _pass_constant_folding(self):
        """Replace binop instructions where both operands are literals.

        Only applies to numeric (tile / glass) arithmetic and comparisons.
        String concatenation is intentionally left alone.
        """
        for i, instr in enumerate(self.instructions):
            if instr.get("op") != "binop":
                continue

            left_val  = self._as_number(instr.get("left",  ""))
            right_val = self._as_number(instr.get("right", ""))

            if left_val is None or right_val is None:
                continue  # one or both operands are not literals

            operator = instr.get("operator", "")
            result   = self._fold(operator, left_val, right_val)

            if result is None:
                continue  # operator not foldable (e.g. division by zero)

            # Replace the binop with a plain assign
            dest = instr["dest"]
            self.instructions[i] = {"op": "assign", "dest": dest, "src": str(result)}
            self.stats["constant_folds"] += 1
            self.log.append(
                f"Constant fold: {dest} = {left_val} {operator} {right_val}  →  {dest} = {result}"
            )

    def _as_number(self, operand: str) -> Optional[Any]:
        """Return operand as a Python number if it is a numeric literal, else None.

        Returns float if the literal contains a decimal point (glass),
        int otherwise (tile).  This preserves type so the folded result
        is serialized back to the correct string form.
        """
        if not isinstance(operand, str):
            return None
        try:
            if "." in operand:
                return float(operand)    # glass literal  e.g. "6.0" → 6.0
            return int(operand)          # tile  literal  e.g. "6"   → 6
        except (ValueError, TypeError):
            return None

    def _fold(self, operator: str, left: float, right: float) -> Optional[Any]:
        """Compute the result of a constant binary expression.

        Returns None if the operation cannot be safely folded.
        """
        try:
            if operator == "+":
                result = left + right
            elif operator == "-":
                result = left - right
            elif operator == "*":
                result = left * right
            elif operator == "/":
                if right == 0:
                    return None  # do not fold division by zero
                # C-style: truncate toward zero for integer operands
                import math
                result = left / right
                if isinstance(left, int) and isinstance(right, int):
                    result = math.trunc(result)
            elif operator == "%":
                if right == 0:
                    return None
                # C-style truncated modulo (sign follows dividend)
                import math
                result = math.fmod(left, right)
                if isinstance(left, int) and isinstance(right, int):
                    result = int(result)
            elif operator == "<":
                return "True" if left < right else "False"
            elif operator == "<=":
                return "True" if left <= right else "False"
            elif operator == ">":
                return "True" if left > right else "False"
            elif operator == ">=":
                return "True" if left >= right else "False"
            elif operator == "==":
                return "True" if left == right else "False"
            elif operator == "!=":
                return "True" if left != right else "False"
            else:
                return None
        except (TypeError, ZeroDivisionError):
            return None

        # Preserve numeric type in the serialized string:
        #   - If either operand was float (glass), keep decimal point
        #   - Only use int string when both operands were int (tile)
        if isinstance(left, float) or isinstance(right, float):
            # glass result: always include decimal point so runtime
            # parses it back as float, not int
            if isinstance(result, float):
                # Format to reasonable precision, strip trailing zeros
                # but always keep at least one decimal place: 6.0 not 6
                formatted = f"{result:.7f}".rstrip("0")
                if formatted.endswith("."):
                    formatted += "0"   # ensure "6." → "6.0"
                return formatted
        # Pure integer result
        if isinstance(result, float) and result == int(result):
            return str(int(result))
        return str(result)

    # ── Pass 2: Redundant Temporary Elimination ───────────────────────────────

    def _pass_redundant_temp_elimination(self):
        """Remove temporaries that are assigned and then immediately copied.

        Pattern:
            t1 = <expr>      (binop or unary)
            x  = t1          (assign from the temp)

        Condition for elimination:
            - t1 is a temporary (starts with 't' followed by digits)
            - t1 is used exactly once in the whole instruction list (this copy)
            - The two instructions are consecutive (no label/jump between them)

        Transformation: replace the binop/unary dest with x directly,
        and remove the assign instruction.
        """
        # Count uses of every name as a SOURCE across the instruction list
        use_count: Dict[str, int] = {}
        for instr in self.instructions:
            for field in ("src", "left", "right", "operand", "cond"):
                val = instr.get(field)
                if isinstance(val, str):
                    use_count[val] = use_count.get(val, 0) + 1
            # Also count uses in view/write args
            for a in instr.get("args", []):
                if isinstance(a, str):
                    use_count[a] = use_count.get(a, 0) + 1

        to_remove: set = set()

        for i in range(len(self.instructions) - 1):
            instr      = self.instructions[i]
            next_instr = self.instructions[i + 1]

            # First instruction must be a binop or unary into a temp
            if instr.get("op") not in ("binop", "unary", "assign"):
                continue
            dest = instr.get("dest", "")
            if not self._is_temp(dest):
                continue

            # Next instruction must be:  <name> = <temp>
            if next_instr.get("op") != "assign":
                continue
            if next_instr.get("src") != dest:
                continue

            # The temp must be used exactly once (only this copy)
            if use_count.get(dest, 0) != 1:
                continue

            # Safe to eliminate: redirect the first instruction's dest
            target = next_instr["dest"]
            self.instructions[i] = dict(instr)
            self.instructions[i]["dest"] = target
            to_remove.add(i + 1)
            self.stats["redundant_temps_removed"] += 1
            self.log.append(
                f"Redundant temp eliminated: '{dest}' replaced by '{target}'"
            )

        # Remove marked instructions (in reverse order to preserve indices)
        for idx in sorted(to_remove, reverse=True):
            del self.instructions[idx]

    def _is_temp(self, name: str) -> bool:
        """Return True if name looks like a TAC temporary (t1, t2, …)."""
        if not name or name[0] != "t":
            return False
        return name[1:].isdigit()

    # ── Pass 3: Dead Code Elimination ────────────────────────────────────────

    def _pass_dead_code_elimination(self):
        """Remove instructions that follow an unconditional jump.

        Any instruction between a 'goto' and the next 'label' is unreachable.
        func_begin, func_end, and label instructions are never removed.
        """
        to_remove: set = set()
        in_dead_zone = False

        for i, instr in enumerate(self.instructions):
            op = instr.get("op", "")

            if op == "label":
                in_dead_zone = False   # a label makes the next instructions reachable

            if in_dead_zone and op not in ("label", "func_begin", "func_end"):
                to_remove.add(i)
                self.stats["dead_instructions_removed"] += 1
                self.log.append(
                    f"Dead code removed at index {i}: {instr}"
                )

            if op == "jump":
                in_dead_zone = True    # unconditional jump → what follows is dead

        for idx in sorted(to_remove, reverse=True):
            del self.instructions[idx]


# =============================================================================
# Helpers
# =============================================================================

def optimization_summary(result: dict) -> str:
    """Return a short human-readable summary of what the optimizer did."""
    stats = result["stats"]
    parts = []
    if stats["constant_folds"] > 0:
        parts.append(f"{stats['constant_folds']} constant fold(s)")
    if stats["redundant_temps_removed"] > 0:
        parts.append(f"{stats['redundant_temps_removed']} redundant temp(s) removed")
    if stats["dead_instructions_removed"] > 0:
        parts.append(f"{stats['dead_instructions_removed']} dead instruction(s) removed")
    if not parts:
        return "No optimizations applied."
    return "Optimizations: " + ", ".join(parts) + "."