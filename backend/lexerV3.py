from enum import Enum, auto
from dataclasses import dataclass
import sys

# ==============================================================================
# 1. TOKEN DEFINITIONS (Unchanged)
# ==============================================================================
class TokenType(Enum):
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
    TOK_TILE = auto()
    TOK_GLASS = auto()
    TOK_BRICK = auto()
    TOK_BEAM = auto()
    TOK_SPACE = auto()
    TOK_WALL = auto()
    TOK_HOUSE = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    TOK_BRICK_LITERAL = auto()
    TOK_WALL_LITERAL = auto()
    TOK_IF = auto()
    TOK_ELSE = auto()
    TOK_ROOM = auto()
    TOK_DOOR = auto()
    TOK_GROUND = auto()
    TOK_FOR = auto()
    TOK_WHILE = auto()
    TOK_DO = auto()
    TOK_CRACK = auto()
    TOK_BLUEPRINT = auto()
    TOK_VIEW = auto()
    TOK_WRITE = auto()
    TOK_HOME = auto()
    TOK_SOLID = auto()
    TOK_FRAGILE = auto()
    TOK_CEMENT = auto()
    TOK_ROOF = auto()
    TOK_SEMICOLON = auto()
    TOK_COLON = auto()
    TOK_COMMA = auto()
    TOK_PERIOD = auto()
    TOK_AMPERSAND = auto()
    TOK_OP_BRACE = auto()
    TOK_CL_BRACE = auto()
    TOK_OP_BRACKET = auto()
    TOK_CL_BRACKET = auto()
    TOK_OP_PARENTHESES = auto()
    TOK_CL_PARENTHESES = auto()
    TOK_EOF = auto()

# ==============================================================================
# 2. KEYWORD MAPPING (Unchanged)
# ==============================================================================
KEYWORDS = {
    "tile": TokenType.TOK_TILE, "glass": TokenType.TOK_GLASS, "brick": TokenType.TOK_BRICK,
    "beam": TokenType.TOK_BEAM, "space": TokenType.TOK_SPACE, "wall": TokenType.TOK_WALL,
    "house": TokenType.TOK_HOUSE, "if": TokenType.TOK_IF, "else": TokenType.TOK_ELSE,
    "room": TokenType.TOK_ROOM, "door": TokenType.TOK_DOOR, "ground": TokenType.TOK_GROUND,
    "for": TokenType.TOK_FOR, "while": TokenType.TOK_WHILE, "do": TokenType.TOK_DO,
    "crack": TokenType.TOK_CRACK, "blueprint": TokenType.TOK_BLUEPRINT, "view": TokenType.TOK_VIEW,
    "write": TokenType.TOK_WRITE, "home": TokenType.TOK_HOME, "solid": TokenType.TOK_SOLID,
    "fragile": TokenType.TOK_FRAGILE, "cement": TokenType.TOK_CEMENT, "roof": TokenType.TOK_ROOF,
}

# ==============================================================================
# 3. TOKEN DATA STRUCTURE (UPGRADED)
# ==============================================================================
@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int  # <-- NEW: Added column
    value: any = None 

    def __repr__(self):
        return (
            f"Token(type={self.type.name}, "
            f"lexeme='{self.lexeme}', "
            f"value={self.value!r}, "
            f"line={self.line}, "
            f"col={self.col})" # <-- NEW
        )

# ==============================================================================
# 4. LEXER CLASS (UPGRADED)
# ==============================================================================
class Lexer:
    def __init__(self, src: str):
        self.src: str = src
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1  # <-- NEW: Track column
        self.errors: list[dict] = []
        
    def _is_at_end(self) -> bool:
        return self.pos >= len(self.src)
        
    def _peek(self) -> str | None:
        if self._is_at_end(): return None
        return self.src[self.pos]

    def _peek_next(self) -> str | None:
        if self.pos + 1 >= len(self.src): return None
        return self.src[self.pos + 1]
        
    def _advance(self) -> str:
        """Consumes the current character and moves position"""
        char = self.src[self.pos]
        self.pos += 1
        self.column += 1  # <-- NEW: Increment column on every advance
        return char

    def _make_token(self, type: TokenType, lexeme: str, value: any = None, col: int = 0) -> Token:
        if value is None: value = lexeme
        # Use the provided column, or the column at the *start* of the token
        start_col = col if col > 0 else (self.column - len(lexeme))
        return Token(type, lexeme, self.line, start_col, value)

    def _report_error(self, message: str, char: str = None, col: int = 0):
        """Logs an error and does not stop lexing."""
        if char is None: char = self._peek() or "EOF"
        if col == 0: col = self.column
            
        error_details = {
            "line": self.line,
            "col": col, # <-- NEW
            "character": char,
            "message": message
        }
        self.errors.append(error_details)
        print(f"[Lexical Error] Line {self.line}:{col}: {message} ('{char}')", file=sys.stderr)

    def _skip_whitespace_and_comments(self):
        while not self._is_at_end():
            char = self._peek()
            
            if char in (' ', '\r', '\t'):
                self._advance()
            elif char == '\n':
                self._advance()
                self.line += 1
                self.column = 1  # <-- NEW: Reset column on newline
            elif char == '/':
                if self._peek_next() == '/':  # Single-line comment
                    while not self._is_at_end() and self._peek() != '\n':
                        self._advance()
                elif self._peek_next() == '*':  # Multi-line comment
                    self._advance()  # Skip '/'
                    self._advance()  # Skip '*'
                    start_line = self.line
                    start_col = self.column - 2
                    while not self._is_at_end():
                        if self._peek() == '*' and self._peek_next() == '/':
                            self._advance()  # Skip '*'
                            self._advance()  # Skip '/'
                            break
                        if self._peek() == '\n':
                            self.line += 1
                            self.column = 1 # <-- NEW
                        else:
                            self._advance()
                    else: 
                        self._report_error(f"Unterminated multi-line comment (started on line {start_line})", col=start_col)
                else:
                    return
            else:
                return

    # --- (Helper functions for literals are unchanged, but errors now get columns) ---
    def _handle_string_literal(self) -> Token | None:
        start_pos = self.pos - 1
        start_col = self.column - 1
        value = ""
        while not self._is_at_end() and self._peek() != '"':
            char = self._advance()
            
            if char == '\\':
                if self._is_at_end(): break
                escape = self._advance()
                if escape == 'n': value += '\n'
                elif escape == 't': value += '\t'
                elif escape == '\\': value += '\\'
                elif escape == '"': value += '"'
                else:
                    self._report_error(f"Unknown escape sequence '\\{escape}'", col=self.column-1)
            elif char == '\n':
                self._report_error("Unterminated string literal (newline found)", col=start_col)
                return None
            else:
                value += char

        if self._is_at_end():
            self._report_error("Unterminated string literal", col=start_col)
            return None

        self._advance() # Consume the closing "
        lexeme = self.src[start_pos:self.pos]
        return self._make_token(TokenType.TOK_WALL_LITERAL, lexeme, value, start_col)

    def _handle_char_literal(self) -> Token | None:
        start_pos = self.pos - 1
        start_col = self.column - 1
        char_val = 0
        
        if self._is_at_end():
            self._report_error("Unterminated character literal", col=start_col)
            return None

        char = self._advance()
        
        if char == '\\':
            if self._is_at_end():
                self._report_error("Unterminated character literal", col=start_col)
                return None
            escape = self._advance()
            if escape == 'n': char_val = ord('\n')
            elif escape == 't': char_val = ord('\t')
            elif escape == '\\': char_val = ord('\\')
            elif escape == '\'': char_val = ord('\'')
            else:
                self._report_error(f"Unknown escape sequence '\\{escape}'", col=self.column-1)
                char_val = ord(escape)
        elif char == '\'':
             self._report_error("Empty character literal", col=start_col)
             return None
        else:
            char_val = ord(char)

        if self._is_at_end() or self._peek() != '\'':
            self._report_error("Unterminated or multi-character literal", col=start_col)
            while not self._is_at_end() and self._peek() != '\'':
                self._advance()
            if self._is_at_end(): return None
        
        self._advance() # Consume the closing '
        lexeme = self.src[start_pos:self.pos]
        return self._make_token(TokenType.TOK_BRICK_LITERAL, lexeme, char_val, start_col)

    def _handle_number_literal(self, start: int, start_col: int) -> Token:
        while not self._is_at_end() and self._peek() and self._peek().isdigit():
            self._advance()
        
        if (not self._is_at_end() and self._peek() == '.' and
            self._peek_next() and self._peek_next().isdigit()):
            self._advance() # Consume '.'
            while not self._is_at_end() and self._peek() and self._peek().isdigit():
                self._advance()
            lexeme = self.src[start:self.pos]
            return self._make_token(TokenType.NUMBER, lexeme, float(lexeme), start_col)
        else:
            lexeme = self.src[start:self.pos]
            return self._make_token(TokenType.NUMBER, lexeme, int(lexeme), start_col)

    def get_next_token(self) -> Token | None:
        self._skip_whitespace_and_comments()

        if self._is_at_end():
            return self._make_token(TokenType.TOK_EOF, "EOF")

        start = self.pos
        start_col = self.column # <-- NEW: Mark column at token start
        char = self._advance()

        if char.isalpha() or char == '_':
            while not self._is_at_end() and self._peek() and (self._peek().isalnum() or self._peek() == '_'):
                self._advance()
            lexeme = self.src[start:self.pos]
            token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
            return self._make_token(token_type, lexeme, col=start_col)

        if char.isdigit():
            return self._handle_number_literal(start, start_col)

        if char == "'":
            return self._handle_char_literal()
        if char == '"':
            return self._handle_string_literal()

        # (All operators now pass their start_col)
        match char:
            case '(': return self._make_token(TokenType.TOK_OP_PARENTHESES, "(", col=start_col)
            case ')': return self._make_token(TokenType.TOK_CL_PARENTHESES, ")", col=start_col)
            case '{': return self._make_token(TokenType.TOK_OP_BRACE, "{", col=start_col)
            case '}': return self._make_token(TokenType.TOK_CL_BRACE, "}", col=start_col)
            case '[': return self._make_token(TokenType.TOK_OP_BRACKET, "[", col=start_col)
            case ']': return self._make_token(TokenType.TOK_CL_BRACKET, "]", col=start_col)
            case ';': return self._make_token(TokenType.TOK_SEMICOLON, ";", col=start_col)
            case ':': return self._make_token(TokenType.TOK_COLON, ":", col=start_col)
            case ',': return self._make_token(TokenType.TOK_COMMA, ",", col=start_col)
            case '.': return self._make_token(TokenType.TOK_PERIOD, ".", col=start_col)
            case '%': return self._make_token(TokenType.TOK_MODULO, "%", col=start_col)

            case '!':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_NOT_EQUAL, "!=", col=start_col)
                return self._make_token(TokenType.TOK_NOT, "!", col=start_col)
            
            case '=':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_EQUALS, "==", col=start_col)
                return self._make_token(TokenType.TOK_ASSIGN, "=", col=start_col)

            case '+':
                if not self._is_at_end() and self._peek() == '+':
                    self._advance()
                    return self._make_token(TokenType.TOK_INCREMENT, "++", col=start_col)
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_ADD_ASSIGN, "+=", col=start_col)
                return self._make_token(TokenType.TOK_PLUS, "+", col=start_col)

            case '-':
                if not self._is_at_end() and self._peek() == '-':
                    self._advance()
                    return self._make_token(TokenType.TOK_DECREMENT, "--", col=start_col)
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_SUB_ASSIGN, "-=", col=start_col)
                return self._make_token(TokenType.TOK_MINUS, "-", col=start_col)

            case '*':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_MUL_ASSIGN, "*=", col=start_col)
                return self._make_token(TokenType.TOK_MULTIPLY, "*", col=start_col)

            case '/':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_DIV_ASSIGN, "/=", col=start_col)
                return self._make_token(TokenType.TOK_DIVIDE, "/", col=start_col)

            case '<':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_LT_EQUAL, "<=", col=start_col)
                return self._make_token(TokenType.TOK_LESS_THAN, "<", col=start_col)

            case '>':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.TOK_GT_EQUAL, ">=", col=start_col)
                return self._make_token(TokenType.TOK_GREATER_THAN, ">", col=start_col)

            case '&':
                if not self._is_at_end() and self._peek() == '&':
                    self._advance()
                    return self._make_token(TokenType.TOK_AND, "&&", col=start_col)
                return self._make_token(TokenType.TOK_AMPERSAND, "&", col=start_col)

            case '|':
                if not self._is_at_end() and self._peek() == '|':
                    self._advance()
                    return self._make_token(TokenType.TOK_OR, "||", col=start_col)
                self._report_error("Unknown character or incomplete operator '|'", char, start_col)
                return None
            
            case _:
                self._report_error("Unknown character", char, start_col)
                return None

    def tokenize_all(self) -> list[Token]:
        # (This function is unchanged)
        tokens = []
        while True:
            token = self.get_next_token()
            if token is None:
                continue
            tokens.append(token)
            if token.type == TokenType.TOK_EOF:
                break
        return tokens

# =CM_e_s_t_d_r_i_v_e_r_>
# 5. TEST DRIVER (Unchanged)
# ==============================================================================
if __name__ == "__main__":
    
    input_code = (
        "tile result = 50 - 10;\n"
        "glass g_val = 123.45;\n"
        "tile neg_val = -25;\n" 
        "\n"
        "brick my_char = 'a';\n"
        "brick newline = '\\n';\n"
        "wall greeting = \"hello\\tworld\";\n"
        "\n"
        "/* Test errors */\n"
        "brick bad_char = 'abc';\n"
        "tile err = 4 @ 5;\n"
        "wall bad_str = \"unterminated\n"
    )

    lexer = Lexer(input_code)
    print(f"--- Lexing Input ---\n{input_code}\n--------------------")
    valid_tokens = lexer.tokenize_all()
    lexical_errors = lexer.errors

    if lexical_errors:
        print("\n--- LEXICAL ERRORS DETECTED ---")
        for error in lexical_errors:
            print(f"  Line {error['line']}:{error['col']}: {error['message']}")
        print("-------------------------------")
    else:
        print("\n--- NO LEXICAL ERRORS ---")

    print("\n--- VALID TOKEN STREAM (for Parser) ---")
    for token in valid_tokens:
        print(f"  {token!r}")