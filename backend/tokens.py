from dataclasses import dataclass

@dataclass
class Token:
    tokenType: str
    lexeme: str
    line: int
    column: int


def formatToken(token: Token) -> str:
    return f"{token.tokenType} : {token.lexeme!r} (line {token.line}, col {token.column})"
