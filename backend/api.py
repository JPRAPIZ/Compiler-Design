from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from lexer.lexer import Lexer
from lexer.tokens import Token

# change this for another file
from parser.parserV5_LL1_pure_latest import Parser
# from parser.predict_set import PREDICT_SET

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
    start_line: int | None = None
    start_col: int | None = None
    end_line: int | None = None
    end_col: int | None = None




class LexResult(BaseModel):
    tokens: List[TokenResponse]
    errors: List[ErrorResponse]

# ------------------------------------------------------------------------
class ParseResult(BaseModel):
    errors: List[ErrorResponse]
# added ------------------------------------------------------------------------

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


# --------- /lex endpoint ---------

@app.post("/lex", response_model=LexResult)
def lex_source(body: LexRequest):
    # function calls to backend
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
        )
        for e in lexer.errors
    ]

    return LexResult(
        tokens=token_responses,
        errors=error_responses
    )

# New -------------------------------------------------------------------
@app.post("/parse", response_model=ParseResult)
def parse_source(body: LexRequest):
    lexer = Lexer(body.source)
    tokens = lexer.scanTokens()

    # If lexer has errors, return them immediately
    if lexer.errors:
        return {"errors": lexer.errors}

    parser = Parser(tokens)
    parser.parse()  # fills parser.errors

    return {"errors": parser.errors}

# ------------------------------------------------------------------------