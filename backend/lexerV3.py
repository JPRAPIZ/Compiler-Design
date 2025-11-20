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
    
    # ASCII ranges (simplified)
    ascii1 = r'[ -~]'  # ASCII 32-126 excluding \ and ' (handled in brick_lit)
    ascii2 = r'[ -~]'  # ASCII 32-126 excluding \ and " (handled in wall_lit)   
    ascii3 = r'[ -~]'  # ASCII 32-126 (for multi-line comments)
    ascii4 = r'[ -~]'  # ASCII 32-126 excluding * (handled in comment logic)
    ascii5 = r'[ -~]'  # ASCII 32-126 excluding / (handled in comment logic)
    
    # Regular Definition (Others)
    escape_seq = r'\\[nt\'"\\0]'
    whitespace = r'[ \t\n]'
    operators = r'[\+\-\*/%<>=!&|]'
    newline = r'\n'

    # Regular Definition (Delims)
    delim1 = r'[(\s]'           # { ( , whitespace }
    delim2 = r'[;\s]'           # { ; , whitespace }
    delim3 = r'[{\s]'           # { { , whitespace }
    delim4 = r'[\+\-\*/%<>=!&|{}\];:,.\s]'  # { operators , } , ) , ] , : , ; , , ,  whitespace }
    delim5 = r'[:\s]'           # { : , whitespace }
    delim6 = r'[a-zA-Z0-9_\+\-!{(\'\"\s]'  # { alpha_num , + , - , ! , { , ( , ' , " , whitespace }
    delim7 = r'[a-zA-Z0-9_\+\-!(\'\"\s]'   # { alpha_num , + , - , ! , ( , ' , " , whitespace }
    delim8 = r'[a-zA-Z0-9_\-\!(\'\"\s]'    # { alpha_num , - , ! , ( , ' , " , whitespace }
    delim9 = r'[a-zA-Z_)\],;\s]'           # { alpha_id , ) , ] , , , ; , whitespace }
    delim10 = r'[a-zA-Z0-9_\+\-!\'\s]'     # { alpha_num , + , - , ! , ' , whitespace }
    delim11 = r'[a-zA-Z_\+!(\'\s]'         # { alpha_id , + , ! , ( , ' , whitespace }
    delim12 = r'[a-zA-Z0-9_\-{\'\"\s]'     # { alpha_num , - , { , ' , " , whitespace }
    delim13 = r'[a-zA-Z_},;\s]'            # { alpha_id, } , ; , , , whitespace }
    delim14 = r'[a-zA-Z0-9_\+\-!()\'\"\s]' # { alpha_num , - , + , ! , ( , ) , ' , " , whitespace }
    delim15 = r'[\+\-\*/%<>=!&|{)\];\s]'   # { operators , { , ) , ] , ; , whitespace }
    delim16 = r'[a-zA-Z0-9_\+\-!(]\'\s]'   # { alpha_num , + , - , ! , ( , ] , ' , whitespace }
    delim17 = r'[\+\-\*/%<>=!&|)\[;\s]'    # { operators , ) , [ , ; , whitespace }
    delim18 = r'[a-zA-Z0-9_\-&\'\"\s]'     # { alpha_num , - , & , ' , " , whitespace }
    delim19 = r'[a-zA-Z0-9_\+\-\s]'        # { alpha_num , + , - , whitespace }
    delim20 = r'[\+\-\*/%<>=!&|()\[\].,;\s]' # { operators , ( , ) , [ , ] , . , , , ; , whitespace }
    delim21 = r'[\+\-\*/%<>=!&|)\]}.,:;\s]' # { operators, ) , ] , } , , , : , ; , whitespace }
    delim22 = r'[\+\-\*/%<>=!&|)\]}.,;\s]'  # { operators, ) , ] , } , , , ; , whitespace }
    delim23 = r'[\+\-\*/%<>=!&|)\]}.,:;\s]' # { operators , ) , ] , } , , , : , ; , whitespace }
    delim24 = r'[\+\-<>=!&|),;\s]'         # { + , > , < , = , ! , & , | , ) , , , ; , whitespace }
    delim25 = r'[ -~\\s]'                   # { ascii3 , whitespace }

    # Regular Expression (Reserved Symbols)
    INCREMENT = re.compile(r'\+\+')  # (+)(+)
    DECREMENT = re.compile(r'--')    # (-)(-)
    ASSIGN_OPS = re.compile(r'[\+\-\*/%]?=')  # =, +=, -=, *=, /=, %=
    COMPARISON_OPS = re.compile(r'==|!=|>=|<=|>|<')  # ==, !=, >=, <=, >, <
    LOGICAL_OPS = re.compile(r'&&|\|\|')  # &&, ||
    ARITHMETIC_OPS = re.compile(r'[\+\-\*/%]')  # +, -, *, /, %

    # Regular Expression (Delims)
    DELIMITERS = re.compile(r'[{}()\[\];:,.&]')  # {, }, (, ), [, ], ;, :, ,, ., &
    
    # Regular Expression (Whitespace)
    SPACE = re.compile(r' ')      # (˽)
    TAB = re.compile(r'\t')       # (\t)
    NEWLINE = re.compile(r'\n')   # (\n)

    # Regular Expression (Others)
    IDENTIFIER = re.compile(f'{alpha_id}{{1}}{alpha_num}{{0,19}}')  # (alpha_id)(alpha_num/λ)19
    TILE_LIT = re.compile(f'-?{numbers}{{1,15}}')  # (-/λ)(numbers)(numbers/λ)14
    GLASS_LIT = re.compile(f'-?{numbers}{{1,15}}\\.{numbers}{{1,7}}')  # (-/λ)(numbers)(numbers/λ)14(.)(numbers)(numbers/λ)6
    BRICK_LIT = re.compile(r"'([^'\\]|\\.)'")  # (‘)(ascii)(’)
    WALL_LIT = re.compile(r'"([^"\\]|\\.)*"')  # (“)(ascii/λ)*(”)
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
# 4. LEXER CLASS
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
        
        start_col = col if col > 0 else (self.column - len(lexeme))
        return Token(display_type, lexeme, self.line, start_col, value)

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

    def _handle_identifier(self) -> Token | None:
        """Handle identifiers according to RE: (alpha_id)(alpha_num/λ)19"""
        start_pos = self.pos
        start_col = self.column
        
        # Try formal pattern first
        if match := self._match_pattern(self.patterns.IDENTIFIER):
            lexeme, length = match
            
            # Validate according to RE specifications
            if lexeme[0].isdigit():
                self._report_error("Identifier cannot start with a digit", col=start_col)
                # Consume the invalid identifier
                while (not self._is_at_end() and self._peek() and 
                      (self._peek().isalnum() or self._peek() == '_')):
                    self._advance()
                lexeme = self.src[start_pos:self.pos]
                return self._make_token(TokenType.IDENTIFIER, lexeme, col=start_col)
            
            # Check length limit (20 chars from RE)
            if len(lexeme) > 20:
                self._report_error("Identifier exceeds 20 character limit", col=start_col)
                # Consume only first 20 chars
                lexeme = lexeme[:20]
                length = 20
            
            # Update position properly
            self.pos = start_pos + length
            self.column = start_col + length
            
            token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
            
            # Set flag if this is a data type keyword
            if token_type in [TokenType.tile, TokenType.glass, TokenType.brick, 
                              TokenType.wall, TokenType.beam, TokenType.field]:
                self._expecting_identifier = True
                
            return self._make_token(token_type, lexeme, col=start_col)
        
        # Fallback: character-by-character parsing
        if not (self._peek() and (self._peek().isalpha() or self._peek() == '_')):
            return None
            
        start_pos = self.pos
        start_col = self.column
        
        char_count = 0
        while (not self._is_at_end() and self._peek() and 
               (self._peek().isalnum() or self._peek() == '_') and
               char_count < 20):
            self._advance()
            char_count += 1
    
        # Check if there are more characters beyond limit
        if (not self._is_at_end() and self._peek() and 
            (self._peek().isalnum() or self._peek() == '_')):
            self._report_error("Identifier exceeds 20 character limit", col=start_col)
            while not self._is_at_end() and self._peek() and (self._peek().isalnum() or self._peek() == '_'):
                self._advance()

        lexeme = self.src[start_pos:self.pos]
        token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
        
        if token_type in [TokenType.tile, TokenType.glass, TokenType.brick, 
                          TokenType.wall, TokenType.beam, TokenType.field]:
            self._expecting_identifier = True
            
        return self._make_token(token_type, lexeme, col=start_col)

    def _handle_tile_literal(self) -> Token | None:
        """Handle tile literals according to RE: (-/λ)(numbers)(numbers/λ)14"""
        start_pos = self.pos
        start_col = self.column
        
        # Try formal pattern first
        if match := self._match_pattern(self.patterns.TILE_LIT):
            lexeme, length = match
            self.pos = start_pos + length
            self.column = start_col + length
            
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
        
        # Fallback: character-by-character parsing
        if not (self._peek() and self._peek().isdigit()):
            return None
            
        start_pos = self.pos
        start_col = self.column
        
        digit_count = 0
        max_digits = 15
        
        while not self._is_at_end() and self._peek() and self._peek().isdigit() and digit_count < max_digits:
            self._advance()
            digit_count += 1
        
        # Check for excess digits
        if not self._is_at_end() and self._peek() and self._peek().isdigit():
            self._report_error("Tile literal exceeds 15-digit limit", col=start_col)
            while not self._is_at_end() and self._peek() and self._peek().isdigit():
                self._advance()
        
        lexeme = self.src[start_pos:self.pos]
        
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
        """Handle glass literals according to RE: (-/λ)(numbers)(numbers/λ)14(.)(numbers)(numbers/λ)6"""
        start_pos = self.pos
        start_col = self.column
        
        # Try formal pattern first
        if match := self._match_pattern(self.patterns.GLASS_LIT):
            lexeme, length = match
            self.pos = start_pos + length
            self.column = start_col + length
            
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
        
        return None

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
        """Handle string literals according to RE: (“)(ascii/λ)*(”)"""
        if self._peek() != '"':
            return None
            
        start_pos = self.pos
        start_col = self.column
        
        # Try formal pattern first
        if match := self._match_pattern(self.patterns.WALL_LIT):
            lexeme, length = match
            self.pos = start_pos + length
            self.column = start_col + length
            
            # Extract string value and handle escapes
            str_content = lexeme[1:-1]
            value = ""
            i = 0
            while i < len(str_content):
                if str_content[i] == '\\' and i + 1 < len(str_content):
                    escape_char = str_content[i + 1]
                    value += self.escape_sequences.get(escape_char, escape_char)
                    i += 2
                else:
                    value += str_content[i]
                    i += 1
                    
            return self._make_token(TokenType.wall_lit, lexeme, value, start_col)
        
        return None

    def _handle_number(self) -> Token | None:
        """Handle numbers (both tile and glass literals)"""
        start_pos = self.pos
        start_col = self.column
        
        # Check for negative sign
        has_sign = False
        if self._peek() == '-':
            has_sign = True
            self._advance()
        
        # Try glass literal first (more specific)
        if token := self._handle_glass_literal():
            return token
        
        # Try tile literal
        if token := self._handle_tile_literal():
            return token
        
        # If no pattern matched, reset position and return None
        if has_sign:
            self.pos = start_pos
            self.column = start_col
        return None

    def get_next_token(self) -> Token | None:
        # Handle whitespace and comments first
        token = self._handle_whitespace_and_comments()
        if token:
            return token

        if self._is_at_end():
            return self._make_token(TokenType.EOF, "EOF")

        start_col = self.column
        
        # Handle identifiers and keywords
        if token := self._handle_identifier():
            return token

        # Handle numbers (both tile and glass literals)
        if token := self._handle_number():
            return token

        # Handle character and string literals
        if token := self._handle_char_literal():
            return token
        if token := self._handle_string_literal():
            return token

        # Handle operators and delimiters
        char = self._advance()

        # Operators and delims
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
            case '%': return self._make_token(TokenType.modulo, "%", col=start_col)

            # Arithmetic | Unary | Assignment Operators (excluding =)
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

            # Relational Operators (= is placed here) | Logical Operators
            case '>':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.gt_equal, ">=", col=start_col)
                return self._make_token(TokenType.greater_than, ">", col=start_col)

            case '<':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.lt_equal, "<=", col=start_col)
                return self._make_token(TokenType.less_than, "<", col=start_col)

            case '=':
                if not self._is_at_end() and self._peek() == '=':
                    self._advance()
                    return self._make_token(TokenType.equal, "==", col=start_col)
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