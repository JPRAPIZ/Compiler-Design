from enum import Enum, auto
from dataclasses import dataclass
import sys

# ==============================================================================
# 1. TOKEN DEFINITIONS
# ==============================================================================
class TokenType(Enum):
    # --- Operators ---
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

    # --- Delimiters / Symbols ---
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
    TOK_SPACE = auto()

    # --- Literals ---
    NUMBER = auto()
    TOK_BRICK_LITERAL = auto()
    TOK_WALL_LITERAL = auto()
    IDENTIFIER = auto()

    # --- Reserved Words ---
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

    # --- EOF ---
    TOK_EOF = auto()

# ==============================================================================
# 2. KEYWORD MAP
# ==============================================================================
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

# ==============================================================================
# 3. TOKEN STRUCTURE
# ==============================================================================
@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int
    value: any = None

# ==============================================================================
# 4. LEXER CLASS
# ==============================================================================
class Lexer:
    DELIMITERS = set(' \t\n(){}[];:,+-*/%<>=!&|.')

    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.line = 1
        self.column = 1
        self.errors = []

    # --- Basic Helpers ---
    def _is_at_end(self):
        return self.pos >= len(self.src)

    def _peek(self):
        return None if self._is_at_end() else self.src[self.pos]

    def _peek_next(self):
        return None if self.pos + 1 >= len(self.src) else self.src[self.pos + 1]

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        self.column += 1
        return ch

    def _make_token(self, ttype, lexeme, value=None, col=None):
        if value is None:
            value = lexeme
        if col is None:
            col = self.column - len(lexeme)
        return Token(ttype, lexeme, self.line, col, value)

    def _report_error(self, message, char=None, col=None):
        if char is None:
            char = self._peek() or "EOF"
        if col is None:
            col = self.column
        err = {"line": self.line, "col": col, "character": char, "message": message}
        self.errors.append(err)
        print(f"[Lexical Error] Line {self.line}:{col}: {message} ('{char}')", file=sys.stderr)

    # --- Comments and Whitespace ---
    def _skip_comments(self):
        if self._peek() == '/' and self._peek_next() == '/':
            while not self._is_at_end() and self._peek() != '\n':
                self._advance()
            return True
        if self._peek() == '/' and self._peek_next() == '*':
            self._advance(); self._advance()
            while not self._is_at_end():
                if self._peek() == '*' and self._peek_next() == '/':
                    self._advance(); self._advance()
                    return True
                elif self._peek() == '\n':
                    self.line += 1; self.column = 1
                else:
                    self._advance()
            self._report_error("Unterminated multi-line comment")
            return True
        return False

    def _handle_whitespace(self):
        start_col = self.column
        ch = self._advance()
        if ch == '\n':
            self.line += 1
            self.column = 1
        return self._make_token(TokenType.TOK_SPACE, ch, col=start_col)

    # --- Literals ---
    def _handle_char_literal(self, start_col):
        value = ''
        if self._peek() == "'":
            self._advance()
        while not self._is_at_end() and self._peek() != "'":
            ch = self._advance()
            if ch == '\\':
                if self._is_at_end():
                    self._report_error("Unterminated character literal", col=start_col)
                    return None
                esc = self._advance()
                escapes = {'n': '\n', 't': '\t', '\\': '\\', "'": "'"}
                value += escapes.get(esc, esc)
            else:
                value += ch
        if self._is_at_end():
            self._report_error("Unterminated character literal", col=start_col)
            return None
        self._advance()
        lexeme = f"'{value}'"
        return self._make_token(TokenType.TOK_BRICK_LITERAL, lexeme, value, col=start_col)

    def _handle_string_literal(self, start_col):
        value = ''
        if self._peek() == '"':
            self._advance()
        while not self._is_at_end() and self._peek() != '"':
            ch = self._advance()
            if ch == '\\':
                if self._is_at_end():
                    self._report_error("Unterminated string literal", col=start_col)
                    return None
                esc = self._advance()
                escapes = {'n': '\n', 't': '\t', '\\': '\\', '"': '"'}
                value += escapes.get(esc, esc)
            else:
                value += ch
        if self._is_at_end():
            self._report_error("Unterminated string literal", col=start_col)
            return None
        self._advance()
        lexeme = f"\"{value}\""
        return self._make_token(TokenType.TOK_WALL_LITERAL, lexeme, value, col=start_col)

    # --- Core Tokenizer ---
    def get_next_token(self):
        while not self._is_at_end():
            if self._skip_comments():
                continue

            ch = self._peek()
            if ch.isspace():
                return self._handle_whitespace()

            start = self.pos
            start_col = self.column
            ch = self._advance()

            # Identifier or Keyword
            if ch.isalpha() or ch == '_':
                while not self._is_at_end() and self._peek() not in self.DELIMITERS:
                    self._advance()
                lexeme = self.src[start:self.pos]
                token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
                return self._make_token(token_type, lexeme, col=start_col)

            # Number Literal
            elif ch.isdigit():
                while not self._is_at_end() and self._peek().isdigit():
                    self._advance()
                if self._peek() == '.' and self._peek_next() and self._peek_next().isdigit():
                    self._advance()
                    while not self._is_at_end() and self._peek().isdigit():
                        self._advance()
                lexeme = self.src[start:self.pos]
                return self._make_token(TokenType.NUMBER, lexeme, col=start_col)

            # Char Literal
            elif ch == "'":
                tok = self._handle_char_literal(start_col)
                if tok: return tok
                else: continue

            # String Literal
            elif ch == '"':
                tok = self._handle_string_literal(start_col)
                if tok: return tok
                else: continue

            # Operators and Delimiters
            elif ch == '+':
                if self._peek() == '+':
                    self._advance()
                    return self._make_token(TokenType.TOK_INCREMENT, "++", col=start_col)
                elif self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_ADD_ASSIGN, "+=", col=start_col)
                return self._make_token(TokenType.TOK_PLUS, "+", col=start_col)

            elif ch == '-':
                if self._peek() == '-':
                    self._advance()
                    return self._make_token(TokenType.TOK_DECREMENT, "--", col=start_col)
                elif self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_SUB_ASSIGN, "-=", col=start_col)
                return self._make_token(TokenType.TOK_MINUS, "-", col=start_col)

            elif ch == '*':
                if self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_MUL_ASSIGN, "*=", col=start_col)
                return self._make_token(TokenType.TOK_MULTIPLY, "*", col=start_col)

            elif ch == '/':
                if self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_DIV_ASSIGN, "/=", col=start_col)
                return self._make_token(TokenType.TOK_DIVIDE, "/", col=start_col)

            elif ch == '%':
                return self._make_token(TokenType.TOK_MODULO, "%", col=start_col)

            elif ch == '=':
                if self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_EQUALS, "==", col=start_col)
                return self._make_token(TokenType.TOK_ASSIGN, "=", col=start_col)

            elif ch == '!':
                if self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_NOT_EQUAL, "!=", col=start_col)
                return self._make_token(TokenType.TOK_NOT, "!", col=start_col)

            elif ch == '<':
                if self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_LT_EQUAL, "<=", col=start_col)
                return self._make_token(TokenType.TOK_LESS_THAN, "<", col=start_col)

            elif ch == '>':
                if self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_GT_EQUAL, ">=", col=start_col)
                return self._make_token(TokenType.TOK_GREATER_THAN, ">", col=start_col)

            elif ch == '&':
                if self._peek() == '&':
                    self._advance()
                    return self._make_token(TokenType.TOK_AND, "&&", col=start_col)

            elif ch == '|':
                if self._peek() == '|':
                    self._advance()
                    return self._make_token(TokenType.TOK_OR, "||", col=start_col)

            elif ch == ';':
                return self._make_token(TokenType.TOK_SEMICOLON, ";", col=start_col)
            elif ch == ':':
                return self._make_token(TokenType.TOK_COLON, ":", col=start_col)
            elif ch == ',':
                return self._make_token(TokenType.TOK_COMMA, ",", col=start_col)
            elif ch == '.':
                return self._make_token(TokenType.TOK_PERIOD, ".", col=start_col)
            elif ch == '(':
                return self._make_token(TokenType.TOK_OP_PARENTHESES, "(", col=start_col)
            elif ch == ')':
                return self._make_token(TokenType.TOK_CL_PARENTHESES, ")", col=start_col)
            elif ch == '{':
                return self._make_token(TokenType.TOK_OP_BRACE, "{", col=start_col)
            elif ch == '}':
                return self._make_token(TokenType.TOK_CL_BRACE, "}", col=start_col)
            elif ch == '[':
                return self._make_token(TokenType.TOK_OP_BRACKET, "[", col=start_col)
            elif ch == ']':
                return self._make_token(TokenType.TOK_CL_BRACKET, "]", col=start_col)

            else:
                self._report_error("Unknown character", ch, start_col)
                continue

        return self._make_token(TokenType.TOK_EOF, "EOF")

    # --- Tokenize Entire Input ---
    def tokenize_all(self):
        tokens = []
        while True:
            tok = self.get_next_token()
            if tok:
                tokens.append(tok)
                if tok.type == TokenType.TOK_EOF:
                    break
        return tokens

# ==============================================================================
# 5. DRIVER
# ==============================================================================
if __name__ == "__main__":
    input_code = '''
    tile x = 10;
    wall s = "Hello\\nWorld";
    brick c = 'A';
    if (solid) {
        view("#d", x);
    }
    '''
    lexer = Lexer(input_code)
    print("--- Lexing Input ---")
    tokens = lexer.tokenize_all()
    for t in tokens:
        print(t)
    if lexer.errors:
        print("\nErrors:")
        for e in lexer.errors:
            print(e)
