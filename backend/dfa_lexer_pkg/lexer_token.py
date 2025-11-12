
from dataclasses import dataclass
from typing import Any, List, Tuple
from .token_types import TokenType

@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int
    value: Any = None
    trace: List[Tuple[str, str]] = None  # [(state_label, char_consumed)]
