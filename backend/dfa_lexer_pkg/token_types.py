
from enum import Enum, auto

class TokenType(Enum):
    # Operators
    TOK_PLUS = auto()
    TOK_MINUS = auto()
    TOK_MULTIPLY = auto()
    TOK_DIVIDE = auto()
    TOK_MODULO = auto()
    TOK_INCREMENT = auto()
    TOK_DECREMENT = auto()
    TOK_ASSIGN = auto()
    TOK_ADD_ASSIGN = auto()
    TOK_SUB_ASSIGN = auto()
    TOK_MUL_ASSIGN = auto()
    TOK_DIV_ASSIGN = auto()
    TOK_MOD_ASSIGN = auto()
    TOK_GREATER_THAN = auto()
    TOK_LESS_THAN = auto()
    TOK_EQUALS = auto()
    TOK_NOT_EQUAL = auto()
    TOK_LT_EQUAL = auto()
    TOK_GT_EQUAL = auto()
    TOK_AND = auto()
    TOK_OR = auto()
    TOK_NOT = auto()

    # Symbols
    TOK_SEMICOLON = auto()
    TOK_COLON = auto()
    TOK_COMMA = auto()
    TOK_PERIOD = auto()
    TOK_OP_BRACE = auto()
    TOK_CL_BRACE = auto()
    TOK_OP_BRACKET = auto()
    TOK_CL_BRACKET = auto()
    TOK_OP_PARENTHESES = auto()
    TOK_CL_PARENTHESES = auto()

    # Whitespace (distinct)
    TOK_SPACE = auto()
    TOK_TAB = auto()
    TOK_NEWLINE = auto()

    # Literals & identifiers
    NUMBER = auto()            # integer
    GLASS_NUMBER = auto()      # float
    TOK_BRICK_LITERAL = auto() # 'x' or '\n'
    TOK_WALL_LITERAL = auto()  # "..."
    IDENTIFIER = auto()

    # Reserved words (lowercase only)
    TOK_TILE = auto()
    TOK_GLASS = auto()
    TOK_BRICK = auto()
    TOK_WALL = auto()
    TOK_BEAM = auto()
    TOK_FIELD = auto()
    TOK_HOUSE = auto()
    TOK_ROOF = auto()
    TOK_CEMENT = auto()
    TOK_IF = auto()
    TOK_ELSE = auto()
    TOK_FOR = auto()
    TOK_WHILE = auto()
    TOK_DO = auto()
    TOK_CRACK = auto()
    TOK_MEND = auto()
    TOK_ROOM = auto()
    TOK_DOOR = auto()
    TOK_GROUND = auto()
    TOK_BLUEPRINT = auto()
    TOK_HOME = auto()
    TOK_VIEW = auto()
    TOK_WRITE = auto()
    TOK_SOLID = auto()
    TOK_FRAGILE = auto()

    TOK_EOF = auto()
