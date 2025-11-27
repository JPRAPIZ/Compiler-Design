from dataclasses import dataclass

# FIX THIS BEFORE PRESENTATION BAKA MADALE

@dataclass
class Token:
    lexeme: str  
    tokenType: str      
    line: int
    column: int

def formatToken(token: Token) -> str:
    return f"{token.lexeme!r} : {token.tokenType} (line {token.line}, col {token.column})"
