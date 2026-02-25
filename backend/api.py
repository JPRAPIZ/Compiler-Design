from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from lexer.lexer import Lexer
from lexer.tokens import Token

from parser.parserV2 import Parser

from semantic.ast_builder import ASTBuilder
from semantic.semantic import SemanticAnalyzer


class LexRequest(BaseModel):
    source: str


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
    start_col: Optional[int] = None
    end_line: Optional[int] = None
    end_col: Optional[int] = None
    _kind: Optional[str] = None   # "lex" | "syntax" | "semantic" — for frontend

class LexResult(BaseModel):
    tokens: List[TokenResponse]
    errors: List[ErrorResponse]


class ParseResult(BaseModel):
    errors: List[ErrorResponse]


class SemanticResult(BaseModel):
    errors: List[ErrorResponse]

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_errors(raw: list, kind: str) -> List[dict]:
    """Attach a _kind tag to a list of raw error dicts."""
    out = []
    for e in raw:
        out.append({
            "message":    e.get("message", ""),
            "line":       e.get("line", 1),
            "col":        e.get("col", 1),
            "start_line": e.get("start_line"),
            "start_col":  e.get("start_col"),
            "end_line":   e.get("end_line"),
            "end_col":    e.get("end_col"),
            "_kind":      kind,
        })
    return out


# --------- FastAPI app ---------

app = FastAPI()

# --------- CORS (React/Vite) ---------

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


# ── /lex ──────────────────────────────────────────────────────────────────────

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
            _kind="lex",
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

    # Step 3: Build real AST
    builder = ASTBuilder(tokens)
    ast = builder.build_program()

    if ast is None:
        return {"errors": _make_errors([{
            "message": "Internal error: failed to build AST",
            "line": 1, "col": 1,
        }], "semantic")}

    # Step 4: Semantic analysis
    analyzer = SemanticAnalyzer(ast)
    semantic_errors = analyzer.analyze()

    return {"errors": _make_errors(semantic_errors, "semantic")}