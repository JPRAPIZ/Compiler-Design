# =============================================================================
# tac/tac_codegen.py  —  Phase 6: Target Code Generation (Educational Simulation)
# =============================================================================
#
# ROLE IN THE PIPELINE
# --------------------
#   Phase 1 — Lexical Analysis      (lexer/)
#   Phase 2 — Syntax Analysis       (parser/)
#   Phase 3 — Semantic Analysis     (semantic/)
#   Phase 4 — Intermediate Code Gen (tac/tac_generator.py)
#   Phase 5 — Code Optimization     (tac/tac_optimizer.py)
#   Phase 6 — Target Code Gen       ← THIS FILE
#   Runtime  — TAC Interpreter      (tac/tac_runtime.py)  [demo only]
#
# PURPOSE
# -------
# This module simulates the final compiler phase: translating TAC instructions
# into a simple pseudo-machine code (pseudo-assembly).
#
# This is an EDUCATIONAL SIMULATION.  It does not generate real x86, ARM, or
# any other real ISA.  The goal is to demonstrate how a real code generator
# would map TAC operations to load/store/arithmetic/branch instructions.
#
# REGISTER MODEL
# --------------
# We simulate a small register file of N_REGISTERS general-purpose registers:
#   R0, R1, R2, …, R(N_REGISTERS-1)
#
# A simple "next available" allocator is used.  When all registers are in use,
# a simulated "spill" error is reported (register pressure exceeded).
# For the simple programs targeted by this course this should never occur.
#
# PSEUDO-INSTRUCTION SET
# ----------------------
#   LOAD   <reg>, <name|literal>   — load value into register
#   STORE  <name>, <reg>           — store register value to named variable
#   ADD    <dst>, <src1>, <src2>   — arithmetic
#   SUB    <dst>, <src1>, <src2>
#   MUL    <dst>, <src1>, <src2>
#   DIV    <dst>, <src1>, <src2>
#   MOD    <dst>, <src1>, <src2>
#   CMP    <src1>, <src2>          — compare (sets implicit condition flag)
#   JMP    <label>                 — unconditional branch
#   JEQ    <label>                 — jump if equal
#   JNE    <label>                 — jump if not equal
#   JLT    <label>                 — jump if less than
#   JLE    <label>                 — jump if less than or equal
#   JGT    <label>                 — jump if greater than
#   JGE    <label>                 — jump if greater than or equal
#   JFALSE <label>                 — jump if condition is false
#   PRINT  <reg>                   — output (view)
#   READ   <name>                  — input (write)
#   RET    <reg|"">                — return
#   LABEL  <name>:                 — branch target
#   BEGIN  <name>                  — function entry
#   END    <name>                  — function exit
#
# TAC → PSEUDO-ASSEMBLY MAPPING
# ------------------------------
#   TAC                         Pseudo-assembly
#   ─────────────────────────   ────────────────────────────────────────
#   assign  x = y               LOAD  Rn, y
#                               STORE x,  Rn
#   binop   t1 = a + b          LOAD  Rn, a
#                               LOAD  Rm, b
#                               ADD   Rk, Rn, Rm
#                               STORE t1, Rk
#   jump    goto L1             JMP   L1
#   jump_if_false t goto L      JFALSE Rn, L  (after LOAD Rn, t)
#   label   L1:                 LABEL L1:
#   view    "#d", x             LOAD  Rn, x
#                               PRINT Rn
#   write   "#d", &x            READ  x
#   return  0                   LOAD  Rn, 0
#                               RET   Rn
#
# USAGE
# -----
#   codegen = TACCodeGen(optimized_instructions)
#   result  = codegen.generate()
#
#   result["code"]    — list of pseudo-assembly instruction strings
#   result["errors"]  — list of error dicts (e.g. register spill warnings)
#
# =============================================================================

from typing import List, Dict, Optional, Any


N_REGISTERS = 8   # simulated register count: R0 … R7


class TACCodeGen:
    """Translates optimized TAC instructions into pseudo-assembly code.

    The generated code is not executable — it is a human-readable simulation
    of what a real code generator would produce for a simple stack machine.
    """

    def __init__(self, instructions: List[dict]):
        self.instructions = instructions
        self.code: List[str] = []
        self.errors: List[dict] = []

        # Register allocator state
        self._next_reg: int = 0               # index of next free register
        self._var_to_reg: Dict[str, str] = {} # current variable → register mapping

    # ── public entry point ────────────────────────────────────────────────────

    def generate(self) -> dict:
        """Translate each TAC instruction to one or more pseudo-assembly lines."""
        try:
            for instr in self.instructions:
                self._emit_instr(instr)
        except Exception as exc:
            self.errors.append({
                "line":    1,
                "col":     1,
                "message": f"Code generation error: {exc}",
            })

        return {
            "code":   self.code,
            "errors": self.errors,
        }

    # ── register allocation (trivial next-available allocator) ────────────────

    def _alloc_reg(self) -> str:
        """Allocate the next available register.  Wraps around (circular)."""
        if self._next_reg >= N_REGISTERS:
            # Simulated register spill: report but continue by wrapping
            self.errors.append({
                "line":    1,
                "col":     1,
                "message": (
                    f"Code generation warning: register pressure exceeded "
                    f"(>{N_REGISTERS} registers in use). "
                    "Simulating spill by reusing R0."
                ),
            })
            self._next_reg = 0

        reg = f"R{self._next_reg}"
        self._next_reg += 1
        return reg

    def _reset_regs(self):
        """Reset register allocator (called at function boundaries)."""
        self._next_reg = 0
        self._var_to_reg = {}

    def _load(self, operand: str) -> str:
        """Emit a LOAD instruction and return the register used."""
        reg = self._alloc_reg()
        self.code.append(f"    LOAD   {reg}, {operand}")
        return reg

    # ── instruction translation ───────────────────────────────────────────────

    def _emit_instr(self, instr: dict):
        op = instr.get("op", "")

        if op == "func_begin":
            self._reset_regs()
            self.code.append(f"BEGIN  {instr['name']}:")

        elif op == "func_end":
            self.code.append(f"END    {instr.get('name', '?')}")
            self.code.append("")   # blank separator

        elif op == "label":
            self.code.append(f"LABEL  {instr['name']}:")

        elif op == "assign":
            reg = self._load(instr["src"])
            self.code.append(f"    STORE  {instr['dest']}, {reg}")

        elif op == "binop":
            r_left  = self._load(instr["left"])
            r_right = self._load(instr["right"])
            r_dst   = self._alloc_reg()
            mnemonic = self._binop_mnemonic(instr["operator"])
            self.code.append(f"    {mnemonic:<6} {r_dst}, {r_left}, {r_right}")
            self.code.append(f"    STORE  {instr['dest']}, {r_dst}")

        elif op == "unary":
            r_op  = self._load(instr["operand"])
            r_dst = self._alloc_reg()
            if instr["operator"] == "-":
                self.code.append(f"    NEG    {r_dst}, {r_op}")
            else:
                self.code.append(f"    NOT    {r_dst}, {r_op}")
            self.code.append(f"    STORE  {instr['dest']}, {r_dst}")

        elif op == "jump":
            self.code.append(f"    JMP    {instr['target']}")

        elif op == "jump_if":
            reg = self._load(instr["cond"])
            self.code.append(f"    JTRUE  {reg}, {instr['target']}")

        elif op == "jump_if_false":
            reg = self._load(instr["cond"])
            self.code.append(f"    JFALSE {reg}, {instr['target']}")

        elif op == "view":
            fmt      = instr.get("fmt", "")
            raw_args = instr.get("args", [])
            if raw_args:
                for arg in raw_args:
                    reg = self._load(arg)
                    self.code.append(f"    PRINT  {reg}   ; format={fmt}")
            else:
                # view with no args: print the format string itself
                self.code.append(f"    PRINTS {fmt}")

        elif op == "write":
            raw_args = instr.get("args", [])
            fmt      = instr.get("fmt", "")
            for arg in raw_args:
                self.code.append(f"    READ   {arg}   ; format={fmt}")

        elif op == "return":
            val = instr.get("value")
            if val is not None:
                reg = self._load(str(val))
                self.code.append(f"    RET    {reg}")
            else:
                self.code.append(f"    RET")

        elif op in ("array_read", "struct_read"):
            reg = self._load(instr["src"])
            self.code.append(f"    STORE  {instr['dest']}, {reg}")

        # call, func_begin params etc. — simplified representation
        elif op == "call":
            args = instr.get("args", [])
            for a in args:
                reg = self._load(a)
                self.code.append(f"    PARAM  {reg}")
            self.code.append(f"    CALL   {instr.get('func', '?')}")
            if instr.get("dest"):
                self.code.append(f"    STORE  {instr['dest']}, R0  ; return value")

    def _binop_mnemonic(self, operator: str) -> str:
        """Map a TAC binary operator string to a pseudo-assembly mnemonic."""
        return {
            "+":  "ADD",
            "-":  "SUB",
            "*":  "MUL",
            "/":  "DIV",
            "%":  "MOD",
            "<":  "CLT",   # Compare Less Than  → result is bool in reg
            "<=": "CLE",
            ">":  "CGT",
            ">=": "CGE",
            "==": "CEQ",
            "!=": "CNE",
            "&&": "AND",
            "||": "OR",
        }.get(operator, "OP?")