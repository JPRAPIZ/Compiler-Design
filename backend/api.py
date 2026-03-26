import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any

# Phase 9 — logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("arCh")

from lexer.lexer import Lexer
from lexer.tokens import Token

from parser.parserV2 import Parser

from semantic.ast_builder import ASTBuilder
from semantic.semantic import SemanticAnalyzer

from tac.tac_generator import TACGenerator, tac_instruction_to_str
from tac.tac_optimizer import TACOptimizer, optimization_summary
from tac.tac_codegen   import TACCodeGen
from tac.tac_runtime   import TACInterpreter


# =============================================================================
# Request / Response models
# =============================================================================

class LexRequest(BaseModel):
    source: str
    stdin: List[str] = []   # pre-supplied input lines, one value per write() call


class TokenResponse(BaseModel):
    tokenType: str
    lexeme: str
    line: int
    column: int


class ErrorResponse(BaseModel):
    message: str
    line: int
    col: int
    start_line: Optional[int] = None
    start_col:  Optional[int] = None
    end_line:   Optional[int] = None
    end_col:    Optional[int] = None
    kind:       Optional[str] = None   # "lex" | "syntax" | "semantic" | "runtime"


class LexResult(BaseModel):
    tokens: List[TokenResponse]
    errors: List[ErrorResponse]


class ParseResult(BaseModel):
    errors: List[ErrorResponse]


class SemanticResult(BaseModel):
    errors: List[ErrorResponse]


class RunResult(BaseModel):
    """
    Response model for the /run endpoint (full pipeline).

    Fields
    ------
    errors          — non-empty only when the pipeline was halted by an error.
    tac             — list of human-readable TAC instruction strings (Phase 4).
    optimized_tac   — TAC after optimization (Phase 5).
    pseudo_code     — pseudo-assembly output (Phase 6).
    opt_summary     — one-line summary of optimizations applied.
    output          — list of lines printed by the program's view() calls.
    memory          — final global variable values (temporaries excluded).
    runtime_errors  — non-fatal errors detected during interpretation.
    """
    errors:         List[ErrorResponse]   = []
    tac:            List[str]             = []
    optimized_tac:  List[str]             = []
    pseudo_code:    List[str]             = []
    opt_summary:    str                   = ""
    output:         List[str]             = []
    memory:         dict                  = {}
    runtime_errors: List[str]             = []


# =============================================================================
# Helpers
# =============================================================================

def _make_errors(raw: list, kind: str) -> List[dict]:
    """Attach a kind tag to every raw error from the compiler phases.

    All phases return dicts with at minimum "message", "line"/"col".
    Plain strings are accepted as a safety fallback.
    """
    out = []
    for e in raw:
        if isinstance(e, str):
            # Safety fallback only — should not normally occur
            out.append({
                "message":    e,
                "line":       1,
                "col":        1,
                "start_line": None,
                "start_col":  None,
                "end_line":   None,
                "end_col":    None,
                "kind":      kind,
            })
        else:
            # All phases (lex, parse, semantic) return dicts
            # Semantic uses "col", lex/parse may use "start_col" etc.
            line = e.get("line") or e.get("start_line") or 1
            col  = e.get("col")  or e.get("start_col")  or 1
            out.append({
                "message":    e.get("message", ""),
                "line":       line,
                "col":        col,
                "start_line": e.get("start_line", line),
                "start_col":  e.get("start_col",  col),
                "end_line":   e.get("end_line"),
                "end_col":    e.get("end_col"),
                "kind":      kind,
            })
    return out


# =============================================================================
# FastAPI app
# =============================================================================

app = FastAPI()

# Phase 9 — log every incoming request with timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    ms = (time.time() - start) * 1000
    logger.info(f"← {request.url.path} {response.status_code} ({ms:.1f}ms)")
    return response

# ── CORS (React / Vite dev server) ───────────────────────────────────────────

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Existing endpoints — untouched
# =============================================================================

# ── /lex ─────────────────────────────────────────────────────────────────────

@app.post("/lex", response_model=LexResult)
def lex_source(body: LexRequest):
    lexer = Lexer(body.source)
    tokens: list[Token] = lexer.scanTokens()

    token_responses = [
        TokenResponse(
            tokenType=t.tokenType,
            lexeme=t.lexeme,
            line=t.line,
            column=t.column,
        )
        for t in tokens
    ]

    error_responses = [
        ErrorResponse(
            message=e["message"],
            line=e["line"],
            col=e["col"],
            start_line=e.get("start_line"),
            start_col=e.get("start_col"),
            end_line=e.get("end_line"),
            end_col=e.get("end_col"),
            kind="lex",
        )
        for e in lexer.errors
    ]

    return LexResult(tokens=token_responses, errors=error_responses)


# ── /parse ────────────────────────────────────────────────────────────────────

@app.post("/parse", response_model=ParseResult)
def parse_source(body: LexRequest):
    lexer = Lexer(body.source)
    tokens = lexer.scanTokens()

    if lexer.errors:
        return {"errors": _make_errors(lexer.errors, "lex")}

    parser = Parser(tokens)
    parser.parse()

    return {"errors": _make_errors(parser.errors, "syntax")}


# ── /semantic ─────────────────────────────────────────────────────────────────

@app.post("/semantic", response_model=SemanticResult)
def semantic_analyze(body: LexRequest):
    # Step 1: Lex
    lexer = Lexer(body.source)
    tokens = lexer.scanTokens()

    if lexer.errors:
        return {"errors": _make_errors(lexer.errors, "lex")}

    # Step 2: Parse
    parser = Parser(tokens)
    parser.parse()

    if parser.errors:
        return {"errors": _make_errors(parser.errors, "syntax")}

    # Step 3: Build AST
    builder = ASTBuilder(tokens)
    ast = builder.build_program()

    if ast is None:
        return {"errors": _make_errors([{
            "message": "Internal error: failed to build AST",
            "line": 1, "col": 1,
        }], "semantic")}

    # Step 4: Semantic analysis
    analyzer = SemanticAnalyzer()
    semantic_errors = analyzer.analyze(ast)

    return {"errors": _make_errors(semantic_errors, "semantic")}


# =============================================================================
# NEW: /run  —  full pipeline endpoint
# =============================================================================
#
# Pipeline
# --------
#  1. Lex                 → stop and return errors on failure
#  2. Parse               → stop and return errors on failure
#  3. Build AST           → stop and return errors on failure
#  4. Semantic Analysis   → stop and return errors on failure
#  5. TAC Generation      → produces instruction list
#  6. Code Optimization   → constant folding, dead code, temp elimination
#  7. Code Generation     → pseudo-assembly (educational simulation)
#  8. Runtime Execution   → executes optimized TAC, collects output
#
# =============================================================================

@app.post("/run", response_model=RunResult)
def run_program(body: LexRequest):
    """Execute the full compiler pipeline and return TAC + program output."""

    try:
        # ── Phase 1: Lex ─────────────────────────────────────────────────────
        lexer = Lexer(body.source)
        tokens = lexer.scanTokens()

        if lexer.errors:
            return RunResult(errors=_make_errors(lexer.errors, "lex"))

        # ── Phase 2: Parse ───────────────────────────────────────────────────
        parser = Parser(tokens)
        parser.parse()

        if parser.errors:
            return RunResult(errors=_make_errors(parser.errors, "syntax"))

        # ── Phase 3: Build AST ───────────────────────────────────────────────
        builder = ASTBuilder(tokens)
        ast = builder.build_program()

        if ast is None:
            return RunResult(errors=_make_errors([{
                "message": "Internal error: failed to build AST",
                "line": 1, "col": 1,
            }], "semantic"))

        # ── Phase 4: Semantic analysis ───────────────────────────────────────
        analyzer = SemanticAnalyzer()
        semantic_errors = analyzer.analyze(ast)

        if semantic_errors:
            return RunResult(errors=_make_errors(semantic_errors, "semantic"))

    except Exception as exc:
        return RunResult(errors=_make_errors([{
            "message": f"Compiler error: {exc}",
            "line": 1, "col": 1,
        }], "semantic"))

    # ── Phase 5: TAC Generation ──────────────────────────────────────────────
    try:
        gen = TACGenerator()
        instructions = gen.generate(ast)
        tac_lines = [tac_instruction_to_str(i) for i in instructions]
    except Exception as exc:
        return RunResult(errors=_make_errors([{
            "message": f"TAC generation error: {exc}",
            "line": 1, "col": 1,
        }], "semantic"))

    # ── Phase 6: Code Optimization ───────────────────────────────────────────
    try:
        optimizer = TACOptimizer(instructions)
        opt_result = optimizer.optimize()
        opt_instructions = opt_result["instructions"]
        opt_tac_lines = [tac_instruction_to_str(i) for i in opt_instructions]
        opt_summary = optimization_summary(opt_result)
        # Report any optimizer errors as warnings (do not stop compilation)
        opt_errors = opt_result.get("errors", [])
    except Exception as exc:
        # Optimization failure is non-fatal: fall back to unoptimized TAC
        opt_instructions = instructions
        opt_tac_lines = tac_lines
        opt_summary = f"Optimization skipped: {exc}"
        opt_errors = []

    # ── Phase 7: Code Generation ─────────────────────────────────────────────
    try:
        codegen = TACCodeGen(opt_instructions)
        cg_result = codegen.generate()
        pseudo_code = cg_result["code"]
        cg_errors = cg_result.get("errors", [])
    except Exception as exc:
        pseudo_code = [f"; Code generation error: {exc}"]
        cg_errors = []

    # ── Phase 8: Runtime Execution ────────────────────────────────────────────
    # Execute the OPTIMIZED instruction list for correct output.
    try:
        interp = TACInterpreter(opt_instructions, stdin=list(body.stdin))
        result = interp.run()
    except Exception as exc:
        return RunResult(
            tac=tac_lines,
            optimized_tac=opt_tac_lines,
            pseudo_code=pseudo_code,
            opt_summary=opt_summary,
            errors=_make_errors([{
                "message": f"Runtime error: {exc}",
                "line": 1, "col": 1,
            }], "runtime"),
        )

    # ── Return results ────────────────────────────────────────────────────────
    # Only true runtime errors (from the interpreter) stop execution.
    # Code generation warnings (register pressure, etc.) are purely
    # educational/informational and must never block program output.
    true_runtime_errors = list(result["errors"])

    if true_runtime_errors:
        phase_errors = _make_errors(
            [{"message": msg, "line": 1, "col": 1} for msg in true_runtime_errors],
            "runtime"
        )
        return RunResult(
            errors=phase_errors,
            tac=tac_lines,
            optimized_tac=opt_tac_lines,
            pseudo_code=pseudo_code,
            opt_summary=opt_summary,
            output=[],          # cleared — output from errored run is unreliable
            memory=result["memory"],
            runtime_errors=true_runtime_errors,
        )

    return RunResult(
        errors=[],
        tac=tac_lines,
        optimized_tac=opt_tac_lines,
        pseudo_code=pseudo_code,
        opt_summary=opt_summary,
        output=result["output"],
        memory=result["memory"],
        runtime_errors=[],
    )


# =============================================================================
# /compile  —  compile only, return raw TAC instructions for JS interpreter
# =============================================================================

class CompileResult(BaseModel):
    errors:       List[ErrorResponse] = []
    instructions: List[dict]          = []   # optimized TAC instruction dicts


@app.post("/compile", response_model=CompileResult)
def compile_program(body: LexRequest):
    """Run Phases 1-6, return optimized TAC instructions as JSON.

    The frontend JS interpreter executes these instead of the Python runtime,
    enabling interactive stdin (the interpreter pauses at write() and waits
    for the user to type, exactly like Programiz).
    """
    try:
        logger.info("  Phase 1: Lexical analysis")
        lexer = Lexer(body.source)
        tokens = lexer.scanTokens()
        if lexer.errors:
            logger.warning(f"  Phase 1 errors: {len(lexer.errors)}")
            return CompileResult(errors=_make_errors(lexer.errors, "lex"))

        logger.info("  Phase 2: Syntax analysis")
        parser = Parser(tokens)
        parser.parse()
        if parser.errors:
            logger.warning(f"  Phase 2 errors: {len(parser.errors)}")
            return CompileResult(errors=_make_errors(parser.errors, "syntax"))

        logger.info("  Phase 3: AST construction")
        builder = ASTBuilder(tokens)
        ast = builder.build_program()
        if ast is None:
            logger.error("  Phase 3: failed to build AST")
            return CompileResult(errors=_make_errors([{
                "message": "Internal error: failed to build AST", "line": 1, "col": 1}], "semantic"))

        logger.info("  Phase 4: Semantic analysis")
        analyzer = SemanticAnalyzer()
        semantic_errors = analyzer.analyze(ast)
        if semantic_errors:
            logger.warning(f"  Phase 4 errors: {len(semantic_errors)}")
            return CompileResult(errors=_make_errors(semantic_errors, "semantic"))

    except Exception as exc:
        logger.exception(f"  Compiler phase error: {exc}")
        return CompileResult(errors=_make_errors([{
            "message": f"Compiler error: {exc}", "line": 1, "col": 1}], "semantic"))

    try:
        logger.info("  Phase 5: TAC generation")
        gen = TACGenerator()
        instructions = gen.generate(ast)
    except Exception as exc:
        logger.exception(f"  TAC generation error: {exc}")
        return CompileResult(errors=_make_errors([{
            "message": f"TAC generation error: {exc}", "line": 1, "col": 1}], "semantic"))

    try:
        logger.info("  Phase 6: Code optimization")
        optimizer = TACOptimizer(instructions)
        opt_result = optimizer.optimize()
        opt_instructions = opt_result["instructions"]
        logger.info(f"  Phase 6: {opt_result.get('stats', {})}")
    except Exception as exc:
        logger.warning(f"  Phase 6 skipped: {exc}")
        opt_instructions = instructions

    logger.info(f"  Compile OK — {len(opt_instructions)} instructions")
    return CompileResult(instructions=opt_instructions)