
from .token_types import TokenType

# Exact lowercase keywords
KEYWORDS = {
    "tile": TokenType.TOK_TILE,
    "glass": TokenType.TOK_GLASS,
    "brick": TokenType.TOK_BRICK,
    "wall": TokenType.TOK_WALL,
    "beam": TokenType.TOK_BEAM,
    "field": TokenType.TOK_FIELD,
    "house": TokenType.TOK_HOUSE,
    "roof": TokenType.TOK_ROOF,
    "cement": TokenType.TOK_CEMENT,
    "if": TokenType.TOK_IF,
    "else": TokenType.TOK_ELSE,
    "for": TokenType.TOK_FOR,
    "while": TokenType.TOK_WHILE,
    "do": TokenType.TOK_DO,
    "crack": TokenType.TOK_CRACK,
    "mend": TokenType.TOK_MEND,
    "room": TokenType.TOK_ROOM,
    "door": TokenType.TOK_DOOR,
    "ground": TokenType.TOK_GROUND,
    "blueprint": TokenType.TOK_BLUEPRINT,
    "home": TokenType.TOK_HOME,
    "view": TokenType.TOK_VIEW,
    "write": TokenType.TOK_WRITE,
    "solid": TokenType.TOK_SOLID,
    "fragile": TokenType.TOK_FRAGILE,
}
