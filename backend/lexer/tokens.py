from dataclasses import dataclass

@dataclass
class Token:
    lexeme: str  
    tokenType: str      
    line: int
    column: int

def formatToken(token: Token) -> str:
    return f"{token.lexeme!r} : {token.tokenType} (line {token.line}, col {token.column})"
