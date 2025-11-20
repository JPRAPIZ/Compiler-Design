from enum import Enum, auto
from dataclasses import dataclass
import sys
import re

# ==============================================================================
# 1. TOKEN DEFINITIONS
# ==============================================================================
class TokenType(Enum):
    # KEYWORDS
    tile = auto()
    glass = auto()
    brick = auto()
    field = auto()
    wall = auto()
    beam = auto()
    if_ = auto()
    else_ = auto()
    room = auto()
    door = auto()
    ground = auto()
    for_ = auto()
    while_ = auto()
    do = auto()
    crack = auto()
    mend = auto()
    blueprint = auto()
    house = auto()
    view = auto()
    write = auto()
    home = auto()
    solid = auto()
    fragile = auto()
    cement = auto()
    roof = auto()

    # ID
    IDENTIFIER = auto()

    # LITERALS
    tile_lit = auto()
    glass_lit = auto()
    brick_lit = auto()
    wall_lit = auto()

    # OPERATORS
    plus = auto()
    minus = auto()
    multiply = auto()
    divide = auto()
    modulo = auto()
    increment = auto()
    decrement = auto()
    assign = auto()
    add_assign = auto()
    sub_assign = auto()
    mul_assign = auto()
    div_assign = auto()
    mod_assign = auto()
    greater_than = auto()
    less_than = auto()
    equal = auto()
    not_equal = auto()
    gt_equal = auto()
    lt_equal = auto()
    and_ = auto()
    or_ = auto()
    not_ = auto()

    # DELIMITERS 
    semicolon = auto()
    colon = auto()
    comma = auto()
    period = auto()
    ampersand = auto()
    op_brace = auto()
    cl_brace = auto()
    op_bracket = auto()
    cl_bracket = auto()
    op_parentheses = auto()
    cl_parentheses = auto()
    space = auto()
    tab = auto()
    newline = auto()
    single_line_comment = auto()
    multi_line_comment = auto()

    # SPECIAL
    EOF = auto()

# ==============================================================================
# 2. KEYWORD MAPPING
# ==============================================================================
KEYWORDS = {
    "tile": TokenType.tile, "glass": TokenType.glass, "brick": TokenType.brick,
    "field": TokenType.field, "wall": TokenType.wall, "beam": TokenType.beam,  
    "if": TokenType.if_, "else": TokenType.else_, "room": TokenType.room,
    "door": TokenType.door, "ground": TokenType.ground, "for": TokenType.for_,
    "while": TokenType.while_, "do": TokenType.do, "crack": TokenType.crack,
    "mend": TokenType.mend, "blueprint": TokenType.blueprint, "house": TokenType.house,
    "view": TokenType.view, "write": TokenType.write, "home": TokenType.home, 
    "solid": TokenType.solid, "fragile": TokenType.fragile, "cement": TokenType.cement, 
    "roof": TokenType.roof,
}

# ==============================================================================
# 3. REGULAR DEFINITIONS AND EXPRESSIONS
# ==============================================================================
class FormalPatterns:
    # Regular Definitions
    numbers = r'[0-9]'
    alpha_id = r'[a-zA-Z_]'
    alpha_num = r'[a-zA-Z0-9_]'
    
    # Regular Expressions
    IDENTIFIER = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]{0,19}')  # (alpha_id)(alpha_num/λ)19
    TILE_LIT = re.compile(r'-?[0-9]{1,15}')  # (-/λ)(numbers)(numbers/λ)14
    GLASS_LIT = re.compile(r'-?[0-9]{1,15}\.[0-9]{1,7}')  # (-/λ)(numbers)(numbers/λ)14(.)(numbers)(numbers/λ)6
    BRICK_LIT = re.compile(r"'([^'\\]|\\.)'")  # (‘)(ascii)(’)
    WALL_LIT = re.compile(r'"([^"\\]|\\.)*"')  # (“)(ascii/λ)*(”)
    
    # Comment patterns
    SINGLE_LINE_COMMENT = re.compile(r'//.*')  # (/)(/)(ascii)*
    MULTI_LINE_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)  # (/)(*)(ascii)*(*)(/)

# ==============================================================================
# 4. TOKEN DATA STRUCTURE
# ==============================================================================
@dataclass
class Token:
    type: any
    lexeme: str
    line: int
    col: int
    value: any = None

    def __repr__(self):
        return (
            f"Token(type={self.type if isinstance(self.type, str) else self.type.name}, "
            f"lexeme='{self.lexeme}', "
            f"value={self.value!r}, "
            f"line={self.line}, "
            f"col={self.col})"
        )

# ==============================================================================
# 5. LEXER CLASS
# ==============================================================================
class Lexer:
    def __init__(self, src: str):
        self.src: str = src
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.errors: list[dict] = []
        self._expecting_identifier = False
        self.identifier_counter = 1
        self.identifier_map = {}
        self.patterns = FormalPatterns()

        self.escape_sequences = {
            'n': '\n', 't': '\t', '\\': '\\', 
            "'": "'", '"': '"', '0': '\0'
        }

    def _get_identifier_token_name(self, identifier: str) -> str:
        """Convert identifier to id1, id2, etc."""
        if identifier not in self.identifier_map:
            self.identifier_map[identifier] = self.identifier_counter
            self.identifier_counter += 1
        return f"id{self.identifier_map[identifier]}"
    
    def _make_token(self, type: TokenType, lexeme: str, value: any = None, col: int = 0) -> Token:
        if value is None: 
            value = lexeme
        
        # Convert IDENTIFIER type to id1, id2 for display
        display_type = type
        if type == TokenType.IDENTIFIER:
            display_type = self._get_identifier_token_name(lexeme)

        display_lexeme = lexeme
        if type == TokenType.space:
            display_lexeme = "˽" 
        elif type == TokenType.tab:
            display_lexeme = "\\t"
        elif type == TokenType.newline:
            display_lexeme = "\\n"
        
        start_col = col if col > 0 else (self.column - len(lexeme))
        return Token(display_type, display_lexeme, self.line, start_col, value)

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
    
        if char == '\n':
            self.line += 1
            self.column = 1
        elif char == '\t':
            self.column += 4 - ((self.column - 1) % 4)
        else:
            self.column += 1
        
        return char

    def _report_error(self, message: str, char: str = None, col: int = 0):
        """Logs an error and does not stop lexing."""
        if char is None: char = self._peek() or "EOF"
        if col == 0: col = self.column
            
        error_details = {
            "line": self.line,
            "col": col,
            "character": char,
            "message": message
        }
        self.errors.append(error_details)
        print(f"[Lexical Error] Line {self.line}:{col}: {message} ('{char}')", file=sys.stderr)

    def _match_pattern(self, pattern) -> tuple[str, int] | None:
        """Try to match a regex pattern at current position"""
        match = pattern.match(self.src, self.pos)
        if match:
            lexeme = match.group(0)
            return lexeme, len(lexeme)
        return None

    def _handle_whitespace_and_comments(self) -> Token | None:
        """Handle whitespace and comments"""
        if self._is_at_end():
            return None
        
        char = self._peek()
    
        # Handle individual whitespace characters
        if char == ' ' or char == '\t':
            self._advance()
            return self._make_token(TokenType.space, " ", col=self.column-1)
        elif char == '\n':
            self._advance()
            return self._make_token(TokenType.newline, "\\n", col=self.column-1)
        elif char == '/':
            if self._peek_next() == '/':  # Single-line comment
                start_pos = self.pos
                start_col = self.column
                self._advance()  # Skip '/'
                self._advance()  # Skip '/'
            
                # Collect comment content
                comment_content = ""
                while not self._is_at_end() and self._peek() != '\n':
                    comment_content += self._advance()
            
                lexeme = self.src[start_pos:self.pos]
                return self._make_token(TokenType.single_line_comment, lexeme, comment_content, start_col)
            
            elif self._peek_next() == '*':  # Multi-line comment
                start_pos = self.pos
                start_col = self.column
                self._advance()  # Skip '/'
                self._advance()  # Skip '*'
            
                # Collect comment content
                comment_content = ""
                while not self._is_at_end():
                    if self._peek() == '*' and self._peek_next() == '/':
                        self._advance()  # Skip '*'
                        self._advance()  # Skip '/'
                        break
                    comment_content += self._advance()
                else: 
                    self._report_error("Unterminated multi-line comment", col=start_col)
            
                lexeme = self.src[start_pos:self.pos]
                return self._make_token(TokenType.multi_line_comment, lexeme, comment_content, start_col)
    
        return None

    def _handle_invalid_identifier_patterns(self) -> Token | None:
        """Handle cases where identifiers start with digits or contain invalid patterns"""
        start_pos = self.pos
        start_col = self.column
        
        # Case 1: Identifier starting with digit followed by letters or other invalid patterns
        if not self._is_at_end() and self._peek().isdigit():
            # Check if this is actually an invalid identifier pattern
            temp_pos = self.pos
            has_invalid_chars_after = False
            digit_part = ""
            
            # Collect digits
            while temp_pos < len(self.src) and self.src[temp_pos].isdigit():
                digit_part += self.src[temp_pos]
                temp_pos += 1
            
            # Check if there are letters, multiple dots, or other invalid patterns after digits
            if (temp_pos < len(self.src) and 
                (self.src[temp_pos].isalpha() or 
                self.src[temp_pos] == '_' or
                (self.src[temp_pos] == '.' and temp_pos + 1 < len(self.src) and self.src[temp_pos + 1] == '.'))):
                has_invalid_chars_after = True
            
            if has_invalid_chars_after:
                # Determine the specific error
                if temp_pos < len(self.src) and self.src[temp_pos].isalpha():
                    error_msg = "Identifier cannot start with a digit"
                elif (temp_pos < len(self.src) and self.src[temp_pos] == '.' and 
                    temp_pos + 1 < len(self.src) and self.src[temp_pos + 1] == '.'):
                    error_msg = "Invalid number format with multiple decimal points"
                else:
                    error_msg = "Invalid identifier starting with digit"
                
                self._report_error(error_msg, col=start_col)
                # Consume the entire invalid pattern
                while (not self._is_at_end() and self._peek() and 
                    (self._peek().isalnum() or self._peek() in '._')):
                    self._advance()
                lexeme = self.src[start_pos:self.pos]
                return self._make_token(TokenType.IDENTIFIER, lexeme, col=start_col)
        
        # Case 2: Identifiers with hyphens (existing code)
        if not self._is_at_end() and (self._peek().isalpha() or self._peek() == '_'):
            temp_pos = self.pos
            # Check if identifier contains hyphens
            while (temp_pos < len(self.src) and 
                (self.src[temp_pos].isalnum() or self.src[temp_pos] in '_-')):
                if self.src[temp_pos] == '-':
                    # Found a hyphen in identifier
                    self._report_error("Identifier cannot contain hyphens", col=start_col)
                    # Consume up to the hyphen
                    while (not self._is_at_end() and self._peek() and 
                        (self._peek().isalnum() or self._peek() in '_-')):
                        self._advance()
                    lexeme = self.src[start_pos:self.pos]
                    return self._make_token(TokenType.IDENTIFIER, lexeme, col=start_col)
                temp_pos += 1
        
        return None

    def _handle_identifier(self) -> Token | None:
        """Handle identifiers according to RE: (alpha_id)(alpha_num/λ)19"""
        start_pos = self.pos
        start_col = self.column
        
        # Check if first character is valid (letter or underscore)
        if self._is_at_end() or not (self._peek().isalpha() or self._peek() == '_'):
            return None
        
        # Try formal pattern first
        if match := self._match_pattern(self.patterns.IDENTIFIER):
            lexeme, length = match
            
            # Check for invalid identifier patterns
            # Case 1: Identifier starting with digit (should be caught by pattern, but double-check)
            if lexeme[0].isdigit():
                self._report_error("Identifier cannot start with a digit", col=start_col)
                # Consume the invalid identifier
                while (not self._is_at_end() and self._peek() and 
                      (self._peek().isalnum() or self._peek() == '_')):
                    self._advance()
                lexeme = self.src[start_pos:self.pos]
                return self._make_token(TokenType.IDENTIFIER, lexeme, col=start_col)
            
            # Case 2: Check for invalid characters like hyphens in identifiers
            if '-' in lexeme:
                self._report_error("Identifier cannot contain hyphens", col=start_col)
                # Still return as identifier but mark as invalid
            
            # Check length limit
            if len(lexeme) > 20:
                self._report_error("Identifier exceeds 20 character limit", col=start_col)
                lexeme = lexeme[:20]
                length = 20
            
            self.pos = start_pos + length
            self.column = start_col + length
            
            token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
            
            if token_type in [TokenType.tile, TokenType.glass, TokenType.brick, 
                              TokenType.wall, TokenType.beam, TokenType.field]:
                self._expecting_identifier = True
                
            return self._make_token(token_type, lexeme, col=start_col)
        
        return None

    def _handle_number(self) -> Token | None:
        """Handle numbers (both tile and glass literals)"""
        # Try glass literal first (more specific)
        if token := self._handle_glass_literal():
            return token
        
        # Try tile literal
        if token := self._handle_tile_literal():
            return token
        
        return None

    def _handle_tile_literal(self) -> Token | None:
        """Handle tile literals according to RE: (-/λ)(numbers)(numbers/λ)14"""
        start_pos = self.pos
        start_col = self.column
        
        # Check for negative sign
        has_sign = False
        if not self._is_at_end() and self._peek() == '-':
            has_sign = True
            self._advance()
        
        # If we have a sign but no digits, it's not a number
        if has_sign and (self._is_at_end() or not self._peek().isdigit()):
            self.pos = start_pos
            self.column = start_col
            return None
        
        # Build number character by character to enforce strict limits
        lexeme = '-' if has_sign else ''
        digit_count = 0
        max_digits = 15
        
        # Consume digits up to limit
        while not self._is_at_end() and self._peek() and self._peek().isdigit() and digit_count < max_digits:
            char = self._advance()
            lexeme += char
            digit_count += 1
        
        # Check for excess digits - THIS IS THE KEY FIX
        if not self._is_at_end() and self._peek() and self._peek().isdigit():
            self._report_error("Tile literal exceeds 15-digit limit", col=start_col)
            # Mark as error but continue with truncated value
            excess_digits = ""
            while not self._is_at_end() and self._peek() and self._peek().isdigit():
                excess_digits += self._advance()
        
        # If no digits were consumed, it's not a number
        if digit_count == 0:
            if has_sign:
                self.pos = start_pos
                self.column = start_col
            return None
        
        try:
            value = int(lexeme)
            if value > 999999999999999:
                value = 999999999999999
                self._report_error("Tile literal exceeds maximum value", col=start_col)
            elif value < -999999999999999:
                value = -999999999999999  
                self._report_error("Tile literal exceeds minimum value", col=start_col)
        except ValueError:
            value = 0
            self._report_error("Invalid tile literal", col=start_col)
        
        return self._make_token(TokenType.tile_lit, lexeme, value, start_col)

    def _handle_glass_literal(self) -> Token | None:
        """Handle glass literals with strict validation"""
        start_pos = self.pos
        start_col = self.column
        
        # Check for negative sign
        has_sign = False
        if not self._is_at_end() and self._peek() == '-':
            has_sign = True
            self._advance()
        
        # Build number manually to enforce strict rules
        lexeme = '-' if has_sign else ''
        int_digits = 0
        max_int_digits = 15
        decimal_found = False
        dec_digits = 0
        max_dec_digits = 7
        
        # Integer part
        while not self._is_at_end() and self._peek() and self._peek().isdigit() and int_digits < max_int_digits:
            char = self._advance()
            lexeme += char
            int_digits += 1
        
        # Check for excess integer digits
        if not self._is_at_end() and self._peek() and self._peek().isdigit() and not decimal_found:
            self._report_error("Glass literal integer part exceeds 15-digit limit", col=start_col)
            while not self._is_at_end() and self._peek() and self._peek().isdigit() and not decimal_found:
                self._advance()
        
        # Decimal point
        if not self._is_at_end() and self._peek() == '.':
            char = self._advance()
            lexeme += char
            decimal_found = True
            
            # Decimal part
            while not self._is_at_end() and self._peek() and self._peek().isdigit() and dec_digits < max_dec_digits:
                char = self._advance()
                lexeme += char
                dec_digits += 1
            
            # Check for excess decimal digits
            if not self._is_at_end() and self._peek() and self._peek().isdigit():
                self._report_error("Glass literal decimal part exceeds 7-digit limit", col=start_col)
                while not self._is_at_end() and self._peek() and self._peek().isdigit():
                    self._advance()
        
        # Must have at least one digit after decimal point if decimal found
        if decimal_found and dec_digits == 0:
            self._report_error("Glass literal must have digits after decimal point", col=start_col)
        
        # Must have digits to be a valid number
        if int_digits == 0 and dec_digits == 0:
            if has_sign:
                self.pos = start_pos
                self.column = start_col
            return None
        
        # Check for multiple decimal points
        if not self._is_at_end() and self._peek() == '.':
            self._report_error("Multiple decimal points in glass literal", col=start_col)
            while not self._is_at_end() and self._peek() == '.':
                self._advance()
        
        try:
            value = float(lexeme)
            max_val = 999999999999999.9999999
            min_val = -999999999999999.9999999
            if value > max_val:
                value = max_val
                self._report_error("Glass literal exceeds maximum value", col=start_col)
            elif value < min_val:
                value = min_val
                self._report_error("Glass literal exceeds minimum value", col=start_col)
        except ValueError:
            value = 0.0
            self._report_error("Invalid glass literal", col=start_col)
        
        return self._make_token(TokenType.glass_lit, lexeme, value, start_col)

    def _handle_char_literal(self) -> Token | None:
        """Handle character literals according to RE: (‘)(ascii)(’)"""
        if self._peek() != "'":
            return None
            
        start_pos = self.pos
        start_col = self.column
        
        # Try formal pattern first
        if match := self._match_pattern(self.patterns.BRICK_LIT):
            lexeme, length = match
            self.pos = start_pos + length
            self.column = start_col + length
            
            # Extract character value
            char_content = lexeme[1:-1]  # Remove quotes
            if char_content.startswith('\\'):
                escape_char = char_content[1]
                char_val = self.escape_sequences.get(escape_char, escape_char)
            else:
                char_val = char_content
                
            return self._make_token(TokenType.brick_lit, lexeme, char_val, start_col)
        
        return None

    def _handle_string_literal(self) -> Token | None:
        """Handle string literals with better error recovery"""
        if self._peek() != '"':
            return None
            
        start_pos = self.pos
        start_col = self.column
        self._advance()  # Skip opening quote
        
        value = ""
        while not self._is_at_end() and self._peek() != '"' and self._peek() != '\n':
            char = self._advance()
            
            if char == '\\':
                if self._is_at_end():
                    self._report_error("Unterminated string literal (escape sequence)", col=start_col)
                    # Don't return None - create an error token to prevent bad state
                    lexeme = self.src[start_pos:self.pos]
                    return self._make_token(TokenType.wall_lit, lexeme, value, start_col)
                escape_char = self._advance()
                if escape_char in self.escape_sequences:
                    value += self.escape_sequences[escape_char]
                else:
                    self._report_error(f"Invalid escape sequence '\\{escape_char}'", col=self.column-2)
                    value += escape_char
            else:
                value += char

        if self._is_at_end():
            self._report_error("Unterminated string literal (end of file)", col=start_col)
            lexeme = self.src[start_pos:self.pos]
            return self._make_token(TokenType.wall_lit, lexeme, value, start_col)
        elif self._peek() == '\n':
            self._report_error("Unterminated string literal (newline found)", col=start_col)
            lexeme = self.src[start_pos:self.pos]
            return self._make_token(TokenType.wall_lit, lexeme, value, start_col)
        else:  # Found closing quote
            self._advance()  # Skip closing quote
            lexeme = self.src[start_pos:self.pos]
            return self._make_token(TokenType.wall_lit, lexeme, value, start_col)

    def _validate_operator_combination(self, current_char: str, next_char: str, col: int) -> bool:
        """Validate operator combinations based on RD delimiter rules"""
        invalid_combinations = {
            '=<': "assignment operator '=' cannot be directly followed by '<'",
            '=>': "assignment operator '=' cannot be directly followed by '>'", 
            '=!': "assignment operator '=' cannot be directly followed by '!'",
            '=&': "assignment operator '=' cannot be directly followed by '&'",
            '=|': "assignment operator '=' cannot be directly followed by '|'",
            '=+': "assignment operator '=' cannot be directly followed by '+' - use '+='",
            '=-': "assignment operator '=' cannot be directly followed by '-' - use '-='",
            '=*': "assignment operator '=' cannot be directly followed by '*' - use '*='",
            '=/': "assignment operator '=' cannot be directly followed by '/' - use '/='",
            '=%': "assignment operator '=' cannot be directly followed by '%' - use '%='",
            '===': "invalid operator '===' - use '==' for equality",
            '!=': "invalid operator '!=' - use '! =' with space or '!=' as single operator",
            '&&&': "invalid operator '&&&'",
            '|||': "invalid operator '|||'",
            '+++': "invalid operator '+++'",
            '---': "invalid operator '---'",
            '**': "invalid operator '**' - exponentiation not supported",
            '//': "invalid operator '//' - comments use '//' but operators cannot",
            '/*': "invalid operator '/*' - comment start, not operator",
            '*/': "invalid operator '*/' - comment end, not operator",
        }
        
        two_char = current_char + next_char
        if two_char in invalid_combinations:
            self._report_error(f"Invalid operator combination '{two_char}' - {invalid_combinations[two_char]}", char=two_char, col=col)
            return True
        
        # Check for three-character invalid combinations
        if not self._is_at_end() and self._peek_next() is not None:
            three_char = current_char + next_char + self._peek_next()
            if three_char in invalid_combinations:
                self._report_error(f"Invalid operator combination '{three_char}' - {invalid_combinations[three_char]}", char=three_char, col=col)
                return True
        
        return False

    def _get_single_operator_type(self, char: str) -> TokenType:
        """Map single character to its token type"""
        operator_map = {
            '=': TokenType.assign,
            '+': TokenType.plus,
            '-': TokenType.minus,
            '*': TokenType.multiply,
            '/': TokenType.divide,
            '%': TokenType.modulo,
            '<': TokenType.less_than,
            '>': TokenType.greater_than,
            '!': TokenType.not_,
            '&': TokenType.ampersand,
            '|': TokenType.or_,
            '(': TokenType.op_parentheses,
            ')': TokenType.cl_parentheses,
            '{': TokenType.op_brace,
            '}': TokenType.cl_brace,
            '[': TokenType.op_bracket,
            ']': TokenType.cl_bracket,
            ';': TokenType.semicolon,
            ':': TokenType.colon,
            ',': TokenType.comma,
            '.': TokenType.period,
        }
        return operator_map.get(char, TokenType.IDENTIFIER)

    def get_next_token(self) -> Token | None:
        # Handle whitespace and comments first
        token = self._handle_whitespace_and_comments()
        if token:
            return token

        if self._is_at_end():
            return self._make_token(TokenType.EOF, "EOF")

        start_col = self.column
        
        # Check for invalid identifier patterns FIRST (before ANY number handling)
        if token := self._handle_invalid_identifier_patterns():
            return token
        
        # Handle identifiers
        if token := self._handle_identifier():
            return token

        # Handle numbers
        if token := self._handle_number():
            return token

        # Handle character and string literals  
        if token := self._handle_char_literal():
            return token
        if token := self._handle_string_literal():
            return token

        # Handle operators and delimiters
        char = self._advance()
        
        # Check for invalid operator combinations BEFORE processing individual operators
        if not self._is_at_end():
            if self._validate_operator_combination(char, self._peek(), start_col):
                # For invalid combinations, return the first character as a token
                # and let the next call handle the remaining characters
                return self._make_token(self._get_single_operator_type(char), char, col=start_col)
        
        # Enhanced operator validation
        if char == '=' and not self._is_at_end() and self._peek() == '=':
            self._advance()
            if not self._is_at_end() and self._peek() == '=':
                self._advance()
                self._report_error("Invalid operator '==='", col=start_col)
                return self._make_token(TokenType.equal, "==", col=start_col)
            return self._make_token(TokenType.equal, "==", col=start_col)

        match char:
            case '(': return self._make_token(TokenType.op_parentheses, "(", col=start_col)
            case ')': return self._make_token(TokenType.cl_parentheses, ")", col=start_col)
            case '{': return self._make_token(TokenType.op_brace, "{", col=start_col)
            case '}': return self._make_token(TokenType.cl_brace, "}", col=start_col)
            case '[': return self._make_token(TokenType.op_bracket, "[", col=start_col)
            case ']': return self._make_token(TokenType.cl_bracket, "]", col=start_col)
            case ';': return self._make_token(TokenType.semicolon, ";", col=start_col)
            case ':': return self._make_token(TokenType.colon, ":", col=start_col)
            case ',': return self._make_token(TokenType.comma, ",", col=start_col)
            case '.': return self._make_token(TokenType.period, ".", col=start_col)

            case '+':
                if not self._is_at_end() and self._peek() == '+':
                    self._advance()
                    return self._make_token(TokenType.increment, "++", col=start_col)
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.add_assign, "+=", col=start_col)
                return self._make_token(TokenType.plus, "+", col=start_col)

            case '-':
                if not self._is_at_end() and self._peek() == '-':
                    self._advance()
                    return self._make_token(TokenType.decrement, "--", col=start_col)
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.sub_assign, "-=", col=start_col)
                return self._make_token(TokenType.minus, "-", col=start_col)

            case '*':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.mul_assign, "*=", col=start_col)
                if not self._is_at_end() and self._peek() == '*':
                    self._advance()
                    self._report_error("Invalid operator '**'", col=start_col)
                    return self._make_token(TokenType.multiply, "*", col=start_col)
                return self._make_token(TokenType.multiply, "*", col=start_col)

            case '/':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.div_assign, "/=", col=start_col)
                return self._make_token(TokenType.divide, "/", col=start_col)

            case '%':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.mod_assign, "%=", col=start_col)
                return self._make_token(TokenType.modulo, "%", col=start_col)

            case '>':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.gt_equal, ">=", col=start_col)
                return self._make_token(TokenType.greater_than, ">", col=start_col)

            case '<':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.lt_equal, "<=", col=start_col)
                if not self._is_at_end() and self._peek() == '>':
                    self._advance()
                    self._report_error("Invalid operator '<>'", col=start_col)
                    return self._make_token(TokenType.less_than, "<", col=start_col)
                return self._make_token(TokenType.less_than, "<", col=start_col)

            case '=':
                return self._make_token(TokenType.assign, "=", col=start_col)

            case '!':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.not_equal, "!=", col=start_col)
                return self._make_token(TokenType.not_, "!", col=start_col)
            
            case '&':
                if not self._is_at_end() and self._peek() == '&':
                    self._advance()
                    return self._make_token(TokenType.and_, "&&", col=start_col)
                return self._make_token(TokenType.ampersand, "&", col=start_col)

            case '|':
                if not self._is_at_end() and self._peek() == '|':
                    self._advance()
                    return self._make_token(TokenType.or_, "||", col=start_col)
                self._report_error("Unknown character or incomplete operator '|'", char, start_col)
                return None
            
            case _:
                # Check for non-ASCII characters
                if ord(char) > 127:
                    self._report_error(f"Non-ASCII character '{char}' not allowed", char, start_col)
                else:
                    self._report_error("Unknown character", char, start_col)
                return None

    def tokenize_all(self) -> list[Token]:
        tokens = []
        while True:
            token = self.get_next_token()
            if token is None:
                continue
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens