
from typing import List
from tokens import Token

#   DO THE TRANSITION LIMITS FOR ID AND TILE GLASS LIT 
#   FIX WALL LIMITS
#   FIX TILE LIMITS / GLASS LIMITS
#   FIX ORDER OF RETURN LEXEME FIRST THEN TOKENS (CONSISTENCY)
#   

# numbers { 0 , 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9 }
numbers = {
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'
}

# alpha { a..z, A..Z }
alpha = {
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
    'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
    'u', 'v', 'w', 'x', 'y', 'z',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
    'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
    'U', 'V', 'W', 'X', 'Y', 'Z',
}

# ascii1: code 32 to 126 excluding '\' and "'"
ascii1 = {
    ' ', '!', '"', '#', '$', '%', '&', '(',
    ')', '*', '+', ',', '-', '.', '/', '0',
    '1', '2', '3', '4', '5', '6', '7', '8',
    '9', ':', ';', '<', '=', '>', '?', '@',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
    'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
    'Y', 'Z', '[', ']', '^', '_', '`', 'a',
    'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i',
    'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
    'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
    'z', '{', '|', '}', '~',
}

# ascii2: code 32 to 126 excluding '\' and '"'
ascii2 = {
    ' ', '!', '#', '$', '%', '&', "'", '(',
    ')', '*', '+', ',', '-', '.', '/', '0',
    '1', '2', '3', '4', '5', '6', '7', '8',
    '9', ':', ';', '<', '=', '>', '?', '@',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
    'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
    'Y', 'Z', '[', ']', '^', '_', '`', 'a',
    'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i',
    'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
    'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
    'z', '{', '|', '}', '~',
}

# ascii3: full printable ASCII 32–126
ascii3 = {
    ' ', '!', '"', '#', '$', '%', '&', "'",
    '(', ')', '*', '+', ',', '-', '.', '/',
    '0', '1', '2', '3', '4', '5', '6', '7',
    '8', '9', ':', ';', '<', '=', '>', '?',
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
    'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
    'X', 'Y', 'Z', '[', '\\', ']', '^', '_',
    '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
    'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w',
    'x', 'y', 'z', '{', '|', '}', '~',
}

# ascii4: code 33-126 excluding ' ' space
ascii4 = {
    '!', '"', '#', '$', '%', '&', "'", '*',
    '(', ')', '+', ',', '-', '.', '/', '0',
    '1', '2', '3', '4', '5', '6', '7', '8',
    '9', ':', ';', '<', '=', '>', '?', '@',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
    'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
    'Y', 'Z', '[', '\\', ']', '^', '_', '`',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',
    'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
    'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
    'y', 'z', '{', '|', '}', '~',
}


class LexerError(Exception):
    pass

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.current = self.source[0] if self.source else None
        self.tokens: List[Token] = []

        self.errors: list[dict] = []

        self.line = 1
        self.column = 1

        self.token_start_pos = 0
        self.token_start_line = 1
        self.token_start_col = 1

        # ID counter + map: lexeme -> index
        self.id_table: dict[str, int] = {}
        self.next_id_index: int = 1

    def add_error(self, message: str, *, start_line=None, start_col=None):

        # Where the error starts (token_start_* for lexemes, current pos for single chars)
        s_line = start_line if start_line is not None else self.line
        s_col  = start_col if start_col is not None else self.column

        # At minimum, highlight 1 character
        e_line = self.line
        e_col  = self.column
        if e_line == s_line and e_col <= s_col:
            e_col = s_col + 1

        self.errors.append({
            "message": message,
            "line": self.line,
            "col": self.column,
            "start_line": s_line,
            "start_col": s_col,
            "end_line": e_line,
            "end_col": e_col,
        })


    def get_id_token_type(self, lexeme: str) -> str:
        """
        Map each distinct identifier lexeme to a stable idN name.
        Example: x,y,z,x -> id1, id2, id3, id1
        """
        idx = self.id_table.get(lexeme)
        if idx is None:
            idx = self.next_id_index
            self.id_table[lexeme] = idx
            self.next_id_index += 1
        return f"id{idx}"


    # ============================================================
    # Basic helpers
    # ============================================================

    def advance(self):
        """Move one character forward, updating current, line, column."""
        if self.current == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.pos += 1
        self.current = self.source[self.pos] if self.pos < len(self.source) else None

    def peek(self):
        nxt = self.pos + 1
        return self.source[nxt] if nxt < len(self.source) else None

    # ------------------------------------------------------------
    # Character classes
    # ------------------------------------------------------------

    def is_eof(self, ch) -> bool:
        return ch is None

    def is_number(self, ch) -> bool:
        # numbers { 0 , 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9 }
        return ch in numbers

    def is_alpha(self, ch) -> bool:
        # alpha { a..z, A..Z }
        return ch in alpha

    def is_alpha_id(self, ch) -> bool:
        # alpha_id { alpha , _ }
        return self.is_alpha(ch) or ch == '_'

    def is_alpha_num(self, ch) -> bool:
        # alpha_num { numbers , alpha_id }
        return self.is_number(ch) or self.is_alpha_id(ch)

    def is_whitespace(self, ch) -> bool:
        return ch in (' ', '\t', '\n')

    def is_newline(self, ch) -> bool:
        return ch == '\n'

    def is_operator_char(self, ch) -> bool:
        return ch in "+-*/%<>=!&|"

    # def is_ascii_range(self, ch, lo: int, hi: int) -> bool:
    #     return ch is not None and lo <= ord(ch) <= hi

    def is_ascii1(self, ch) -> bool:
        # ascii code 32 to 126 excluding \ and '
        return ch is not None and ch in ascii1

    def is_ascii2(self, ch) -> bool:
        # ascii code 32 to 126 excluding \ and "
        return ch is not None and ch in ascii2

    def is_ascii3(self, ch) -> bool:
        # ascii code 32 to 126
        return ch is not None and ch in ascii3

    def is_ascii4(self, ch) -> bool:
        # ascii code 32 to 126 excluding *
        return ch is not None and ch in ascii4

    def is_escape_seq_char(self, ch) -> bool:
        # { n , t , ' , " , \ , 0 }
        return ch in ('n', 't', "'", '"', '\\', '0')

    # ============================================================
    # Delimiters  (delim1 ... delim25)
    # ============================================================

    def is_delim1(self, ch) -> bool:
        # delim1 { ( , whitespace }
        return self.is_eof(ch) or ch == '(' or self.is_whitespace(ch)

    def is_delim2(self, ch) -> bool:
        # delim2 { ; , whitespace }
        return self.is_eof(ch) or ch == ';' or self.is_whitespace(ch)

    def is_delim3(self, ch) -> bool:
        # delim3 { { , whitespace }
        return self.is_eof(ch) or ch == '{' or self.is_whitespace(ch)

    def is_delim4(self, ch) -> bool:
        # delim4 { operators , } , ) , ] , : , ; , , ,  whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in ('}', ')', ']', ':', ';', ',')
            or self.is_whitespace(ch)
        )

    def is_delim5(self, ch) -> bool:
        # delim5 { : , whitespace }
        return self.is_eof(ch) or ch == ':' or self.is_whitespace(ch)

    def is_delim6(self, ch) -> bool:
        # delim6 { alpha_num , + , - , ! , { , ( , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', '{', '(', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim7(self, ch) -> bool:
        # delim7 { alpha_num , + , - , ! , ( , ' , " ,  whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', '(', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim8(self, ch) -> bool:
        # delim8 { alpha_num , - , ! , ( , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '!', '(', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim9(self, ch) -> bool:
        # delim9 { alpha_id , ) , ] , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_id(ch)
            or ch in (')', ']', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim10(self, ch) -> bool:
        # delim10 { alpha_num , + , - , ! , ' , ( , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', "'", '(')
            or self.is_whitespace(ch)
        )

    def is_delim11(self, ch) -> bool:
        # delim11 { alpha_id , + , ! , ( , ' , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_id(ch)
            or ch in ('+', '!', '(', "'")
            or self.is_whitespace(ch)
        )

    def is_delim12(self, ch) -> bool:
        # delim12 { alpha , numbers , - , { , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or (ch is not None and ch.isalpha())  # alpha
            or self.is_number(ch)                 # numbers
            or ch in ('-', '{', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim13(self, ch) -> bool:
        # delim13 { alpha_id, } , ; , , , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_id(ch)
            or ch in ('}', ';', ',')
            or self.is_whitespace(ch)
        )

    def is_delim14(self, ch) -> bool:
        # delim14 { alpha_num , - , + , ! , ( , ) , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '+', '!', '(', ')', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim15(self, ch) -> bool:
        # delim15 { operators , { , ) , ] , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in ('{', ')', ']', ';')
            or self.is_whitespace(ch)
        )

    def is_delim16(self, ch) -> bool:
        # delim16 { alpha_num , + , - , ! , ( , ] , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', '(', ']', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim17(self, ch) -> bool:
        # delim17 { operators , ) , [ , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', '[', ';')
            or self.is_whitespace(ch)
        )

    def is_delim18(self, ch) -> bool:
        # delim18 { alpha_num , - , & , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '&', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim19(self, ch) -> bool:
        # delim19 { alpha_num , + , - , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-')
            or self.is_whitespace(ch)
        )

    def is_delim20(self, ch) -> bool:
        # delim20 { operators , ( , ) , [ , ] , . , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in ('(', ')', '[', ']', '.', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim21(self, ch) -> bool:
        # delim21 { operators , ) , ] , } , , , : , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', ']', '}', ',', ':', ';')
            or self.is_whitespace(ch)
        )

    def is_delim22(self, ch) -> bool:
        # delim22 { operators, ) , ] , } , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', ']', '}', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim23(self, ch) -> bool:
        # delim23 { + , > , < , = , ! , & , | , ) , ] , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or ch in ('+', '>', '<', '=', '!', '&', '|', ')', ']', ',', ';')
            or self.is_whitespace(ch)
        )

    # ============================================================
    # Public API
    # ============================================================

    def scanTokens(self) -> List[Token]:
        while self.current is not None:
            # remember where this token starts (for error highlighting)
            self.token_start_pos = self.pos
            self.token_start_line = self.line
            self.token_start_col = self.column

            try:

                self.lex_from_state0()

            except LexerError as e:

                self.add_error(
                    str(e),
                    start_line=self.token_start_line,
                    start_col=self.token_start_col,
                )

                if self.current is not None and self.pos == self.token_start_pos:
                    self.advance()

                continue

                # If a token was pending when the error occurred (e.g., delimiter error),
                # still add it to the token list so it appears in the Tokens panel.
                if self.pendingToken is not None:
                    self.tokenList.append(self.pendingToken)
                    self.pendingToken = None

        # EOF token
        eof = Token("$", "EOF", self.line, self.column)
        self.tokens.append(eof)
        return self.tokens






    # ============================================================
    # Transition Table
    # ============================================================

    def lex_from_state0(self):
        start_pos = self.pos
        start_line = self.line
        start_col = self.column

        self.token_start_pos = start_pos
        self.token_start_line = start_line
        self.token_start_col = start_col

        state = 0


        while True:
            ch = self.current

            # ================= STATE 0 (start) =================
            if state == 0:

                # --- whitespace tokens ---
                if ch == ' ':
                    self.advance()
                    state = 193   # space
                    continue

                if ch == '\t':
                    self.advance()
                    state = 194   # tab
                    continue

                if ch == '\n':
                    self.advance()
                    state = 195   # newline
                    continue

                if ch == 'b':
                    self.advance()
                    state = 1
                    continue

                if ch == 'c':
                    self.advance()
                    state = 20
                    continue

                if ch == 'd':
                    self.advance()
                    state = 32
                    continue

                if ch == 'e':
                    self.advance()
                    state = 38
                    continue

                if ch == 'f':
                    self.advance()
                    state = 43
                    continue

                if ch == 'g':
                    self.advance()
                    state = 59
                    continue

                if ch == 'h':
                    self.advance()
                    state = 71
                    continue

                if ch == 'i':
                    self.advance()
                    state = 80
                    continue

                if ch == 'm':
                    self.advance()
                    state = 83
                    continue

                if ch == 'r':
                    self.advance()
                    state = 88
                    continue

                if ch == 's':
                    self.advance()
                    state = 95
                    continue

                if ch == 't':
                    self.advance()
                    state = 101
                    continue

                if ch == 'v':
                    self.advance()
                    state = 106
                    continue

                if ch == 'w':
                    self.advance()
                    state = 111
                    continue

                # --- numbers (integer / float) ---
                if self.is_number(ch):
                    self.advance()
                    state = 236
                    continue

                # --- operators & punctuation ---
                if ch == '=':
                    self.advance()
                    state = 126
                    continue

                if ch == '+':
                    self.advance()
                    state = 130
                    continue

                if ch == '-':
                    self.advance()
                    state = 136
                    continue

                if ch == '*':
                    self.advance()
                    state = 142
                    continue

                if ch == '/':
                    self.advance()
                    state = 146
                    continue

                if ch == '%':
                    self.advance()
                    state = 150
                    continue

                if ch == '>':
                    self.advance()
                    state = 154
                    continue

                if ch == '<':
                    self.advance()
                    state = 158
                    continue

                if ch == '!':
                    self.advance()
                    state = 162
                    continue

                if ch == '&':
                    self.advance()
                    state = 166
                    continue

                if ch == '|':
                    self.advance()
                    state = 170
                    continue

                if ch == '{':
                    self.advance()
                    state = 173
                    continue

                if ch == '}':
                    self.advance()
                    state = 175
                    continue

                if ch == '(':
                    self.advance()
                    state = 177
                    continue

                if ch == ')':
                    self.advance()
                    state = 179
                    continue

                if ch == '[':
                    self.advance()
                    state = 181
                    continue

                if ch == ']':
                    self.advance()
                    state = 183
                    continue

                if ch == '.':
                    self.advance()
                    state = 185
                    continue

                if ch == ',':
                    self.advance()
                    state = 187
                    continue

                if ch == ':':
                    self.advance()
                    state = 189
                    continue

                if ch == ';':
                    self.advance()
                    state = 191
                    continue

                # --- brick / wall literals ---
                if ch == "'":
                    self.advance()
                    state = 281
                    continue

                if ch == '"':
                    self.advance()
                    state = 286
                    continue

                # --- identifiers ---
                if self.is_alpha_id(ch):
                    self.advance()
                    state = 196
                    continue

                lexeme = ch
                raise LexerError(
                    f"Error on line {self.line}, col {self.column}: {lexeme!r} is an invalid lexeme"
                )


            # ===================================================
            # b-branch (beam / blueprint / brick) 1–18
            # ===================================================

            elif state == 1:
                if ch == 'e':
                    self.advance()
                    state = 2
                    continue
                if ch == 'l':
                    self.advance()
                    state = 6
                    continue
                if ch == 'r':
                    self.advance()
                    state = 15
                    continue
                state = 196
                continue

            # beam: b e a m
            elif state == 2:
                if ch == 'a':
                    self.advance()
                    state = 3
                    continue
                state = 196
                continue

            elif state == 3:
                if ch == 'm':
                    self.advance()
                    state = 4
                    continue
                state = 196
                continue

            elif state == 4:
                if self.is_whitespace(ch):
                    state = 5
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 5:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("beam", lexeme, start_line, start_col))
                return

            # blueprint: b l u e p r i n t
            elif state == 6:
                if ch == 'u':
                    self.advance()
                    state = 7
                    continue
                state = 196
                continue

            elif state == 7:
                if ch == 'e':
                    self.advance()
                    state = 8
                    continue
                state = 196
                continue

            elif state == 8:
                if ch == 'p':
                    self.advance()
                    state = 9
                    continue
                state = 196
                continue

            elif state == 9:
                if ch == 'r':
                    self.advance()
                    state = 10
                    continue
                state = 196
                continue

            elif state == 10:
                if ch == 'i':
                    self.advance()
                    state = 11
                    continue
                state = 196
                continue

            elif state == 11:
                if ch == 'n':
                    self.advance()
                    state = 12
                    continue
                state = 196
                continue

            elif state == 12:
                if ch == 't':
                    self.advance()
                    state = 13
                    continue
                state = 196
                continue

            elif state == 13:
                if self.is_delim1(ch):
                    state = 14
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 14:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("blueprint", lexeme, start_line, start_col))
                return


            # brick: b r i c k
            elif state == 15:
                if ch == 'i':
                    self.advance()
                    state = 16
                    continue
                state = 196
                continue

            elif state == 16:
                if ch == 'c':
                    self.advance()
                    state = 17
                    continue
                state = 196
                continue

            elif state == 17:
                if ch == 'k':
                    self.advance()
                    state = 18
                    continue
                state = 196
                continue

            elif state == 18:
                if self.is_whitespace(ch):
                    state = 19
                    continue

                if self.is_alpha_num(ch):    
                    state = 196
                    continue
                
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )
            
            elif state == 19:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("brick", lexeme, start_line, start_col))
                return

            # ===================================================
            # c-branch (cement / crack) 20–30
            # ===================================================

            elif state == 20:
                if ch == 'e':
                    self.advance()
                    state = 21
                    continue
                if ch == 'r':
                    self.advance()
                    state = 27
                    continue
                state = 196
                continue

            # cement: c e m e n t
            elif state == 21:
                if ch == 'm':
                    self.advance()
                    state = 22
                    continue
                state = 196
                continue

            elif state == 22:
                if ch == 'e':
                    self.advance()
                    state = 23
                    continue
                state = 196
                continue

            elif state == 23:
                if ch == 'n':
                    self.advance()
                    state = 24
                    continue
                state = 196
                continue

            elif state == 24:
                if ch == 't':
                    self.advance()
                    state = 25
                    continue
                state = 196
                continue

            elif state == 25:
                if self.is_whitespace(ch):
                    state = 26
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 26:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("cement", lexeme, start_line, start_col))
                return


            # crack: c r a c k
            elif state == 27:
                if ch == 'a':
                    self.advance()
                    state = 28
                    continue
                state = 196
                continue

            elif state == 28:
                if ch == 'c':
                    self.advance()
                    state = 29
                    continue
                state = 196
                continue

            elif state == 29:
                if ch == 'k':
                    self.advance()
                    state = 30
                    continue
                state = 196
                continue

            elif state == 30:
                if self.is_delim2(ch):
                    state = 31
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 31:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("crack", lexeme, start_line, start_col))
                return

            # ===================================================
            # d-branch (do / door) 32–36
            # ===================================================

            elif state == 32:
                if ch == 'o':
                    self.advance()
                    state = 33
                    continue
                state = 196
                continue

            elif state == 33:
                if self.is_delim3(ch):
                    state = 34
                    continue

                if ch == 'o':
                    self.advance()
                    state = 35
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 34:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("do", lexeme, start_line, start_col))
                return

            elif state == 35:
                if ch == 'r':
                    self.advance()
                    state = 36
                    continue
                state = 196
                continue

            elif state == 36:
                if self.is_whitespace(ch):
                    state = 37
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 37:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("door", lexeme, start_line, start_col))
                return

            # ===================================================
            # e-branch (else) 38–41
            # ===================================================

            elif state == 38:
                if ch == 'l':
                    self.advance()
                    state = 39
                    continue
                state = 196
                continue

            elif state == 39:
                if ch == 's':
                    self.advance()
                    state = 40
                    continue
                state = 196
                continue

            elif state == 40:
                if ch == 'e':
                    self.advance()
                    state = 41
                    continue
                state = 196
                continue

            elif state == 41:
                if self.is_delim3(ch):
                    state = 42
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 42:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("else", lexeme, start_line, start_col))
                return

            # ===================================================
            # f-branch (for / field / fragile) 43–57
            # ===================================================

            elif state == 43:
                if ch == 'o':
                    self.advance()
                    state = 44
                    continue
                if ch == 'i':
                    self.advance()
                    state = 47
                    continue
                if ch == 'r':
                    self.advance()
                    state = 52
                    continue
                state = 196
                continue

            # for
            elif state == 44:
                if ch == 'r':
                    self.advance()
                    state = 45
                    continue
                state = 196
                continue

            elif state == 45:
                if self.is_delim1(ch):
                    state = 46
                    continue
        
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 46:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("for", lexeme, start_line, start_col))
                return

            # field: f i e l d
            elif state == 47:
                if ch == 'e':
                    self.advance()
                    state = 48
                    continue
                state = 196
                continue

            elif state == 48:
                if ch == 'l':
                    self.advance()
                    state = 49
                    continue
                state = 196
                continue

            elif state == 49:
                if ch == 'd':
                    self.advance()
                    state = 50
                    continue
                state = 196
                continue

            elif state == 50:
                if self.is_whitespace(ch):
                    state = 51
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 51:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("field", lexeme, start_line, start_col))
                return


            # fragile: f r a g i l e
            elif state == 52:
                if ch == 'a':
                    self.advance()
                    state = 53
                    continue
                state = 196
                continue

            elif state == 53:
                if ch == 'g':
                    self.advance()
                    state = 54
                    continue
                state = 196
                continue

            elif state == 54:
                if ch == 'i':
                    self.advance()
                    state = 55
                    continue
                state = 196
                continue

            elif state == 55:
                if ch == 'l':
                    self.advance()
                    state = 56
                    continue
                state = 196
                continue

            elif state == 56:
                if ch == 'e':
                    self.advance()
                    state = 57
                    continue
                state = 196
                continue

            elif state == 57:
                if self.is_delim4(ch):
                    state = 58
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 58:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("fragile", lexeme, start_line, start_col))
                return

            # ===================================================
            # g-branch (glass / ground) 59–69
            # ===================================================

            elif state == 59:
                if ch == 'l':
                    self.advance()
                    state = 60
                    continue
                if ch == 'r':
                    self.advance()
                    state = 65
                    continue
                state = 196
                continue

            # glass: g l a s s
            elif state == 60:
                if ch == 'a':
                    self.advance()
                    state = 61
                    continue
                state = 196
                continue

            elif state == 61:
                if ch == 's':
                    self.advance()
                    state = 62
                    continue
                state = 196
                continue

            elif state == 62:
                if ch == 's':
                    self.advance()
                    state = 63
                    continue
                state = 196
                continue

            elif state == 63:
                if self.is_whitespace(ch):
                    state = 64
                    continue
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 64:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass", lexeme, start_line, start_col))
                return

            # ground: g r o u n d
            elif state == 65:
                if ch == 'o':
                    self.advance()
                    state = 66
                    continue
                state = 196
                continue

            elif state == 66:
                if ch == 'u':
                    self.advance()
                    state = 67
                    continue
                state = 196
                continue

            elif state == 67:
                if ch == 'n':
                    self.advance()
                    state = 68
                    continue
                state = 196
                continue

            elif state == 68:
                if ch == 'd':
                    self.advance()
                    state = 69
                    continue
                state = 196
                continue

            elif state == 69:
                if self.is_delim5(ch):
                    state = 70
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )
            
            elif state == 70:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("ground", lexeme, start_line, start_col))
                return

            # ===================================================
            # h-branch (home / house) 71–79
            # ===================================================

            elif state == 71:
                if ch == 'o':
                    self.advance()
                    state = 72
                    continue
                state = 196
                continue

            elif state == 72:
                if ch == 'm':
                    self.advance()
                    state = 73
                    continue
                if ch == 'u':
                    self.advance()
                    state = 76
                    continue
                state = 196
                continue

            # home: h o m e
            elif state == 73:
                if ch == 'e':
                    self.advance()
                    state = 74
                    continue
                state = 196
                continue

            elif state == 74:
                if self.is_whitespace(ch):
                    state = 75
                    continue
                
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 75:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("home", lexeme, start_line, start_col))
                return                

            # house: h o u s e
            elif state == 76:
                if ch == 's':
                    self.advance()
                    state = 77
                    continue
                state = 196
                continue

            elif state == 77:
                if ch == 'e':
                    self.advance()
                    state = 78
                    continue
                state = 196
                continue

            elif state == 78:
                if self.is_whitespace(ch):
                    state = 79
                    continue
                
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )
            
            elif state == 79:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("house", lexeme, start_line, start_col))
                return

            # ===================================================
            # i-branch (if) 80–81
            # ===================================================

            elif state == 80:
                if ch == 'f':
                    self.advance()
                    state = 81
                    continue
                state = 196
                continue

            elif state == 81:
                if self.is_delim1(ch):
                    state = 82
                    continue
            
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 82:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("if", lexeme, start_line, start_col))
                return

            # ===================================================
            # m-branch (mend) 83–86
            # ===================================================

            elif state == 83:
                if ch == 'e':
                    self.advance()
                    state = 84
                    continue
                state = 196
                continue

            elif state == 84:
                if ch == 'n':
                    self.advance()
                    state = 85
                    continue
                state = 196
                continue

            elif state == 85:
                if ch == 'd':
                    self.advance()
                    state = 86
                    continue
                state = 196
                continue

            elif state == 86:
                if self.is_delim2(ch):
                    state = 87
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 87:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("mend", lexeme, start_line, start_col))
                return                

            # ===================================================
            # r-branch (roof / room) 88–93
            # ===================================================

            elif state == 88:
                if ch == 'o':
                    self.advance()
                    state = 89
                    continue
                if ch == 'i':
                    self.advance()
                    state = 121
                    continue
                state = 196
                continue

            elif state == 89:
                if ch == 'o':
                    self.advance()
                    state = 90
                    continue
                state = 196
                continue

            elif state == 90:
                if ch == 'f':
                    self.advance()
                    state = 91
                    continue
                if ch == 'm':
                    self.advance()
                    state = 93
                    continue
                state = 196
                continue

            # roof
            elif state == 91:
                if self.is_whitespace(ch):
                    state = 92
                    continue
                
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 92:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("roof", lexeme, start_line, start_col))
                return                

            # room
            elif state == 93:
                if self.is_delim1(ch):
                    state = 94
                    continue
                
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 94:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("room", lexeme, start_line, start_col))
                return                


            # ===================================================
            # s-branch (solid) 95–99
            # ===================================================

            elif state == 95:
                if ch == 'o':
                    self.advance()
                    state = 96
                    continue
                state = 196
                continue

            elif state == 96:
                if ch == 'l':
                    self.advance()
                    state = 97
                    continue
                state = 196
                continue

            elif state == 97:
                if ch == 'i':
                    self.advance()
                    state = 98
                    continue
                state = 196
                continue

            elif state == 98:
                if ch == 'd':
                    self.advance()
                    state = 99
                    continue
                state = 196
                continue

            elif state == 99:
                if self.is_delim4(ch):
                    state = 100
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 100:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("solid", lexeme, start_line, start_col))
                return

            # ===================================================
            # t-branch (tile) 101–104
            # ===================================================

            elif state == 101:
                if ch == 'i':
                    self.advance()
                    state = 102
                    continue
                state = 196
                continue

            elif state == 102:
                if ch == 'l':
                    self.advance()
                    state = 103
                    continue
                state = 196
                continue

            elif state == 103:
                if ch == 'e':
                    self.advance()
                    state = 104
                    continue
                state = 196
                continue

            elif state == 104:
                if self.is_whitespace(ch):
                    state = 105
                    continue
                
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 105:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile", lexeme, start_line, start_col))
                return

            # ===================================================
            # v-branch (view) 106–109
            # ===================================================

            elif state == 106:
                if ch == 'i':
                    self.advance()
                    state = 107
                    continue
                state = 196
                continue

            elif state == 107:
                if ch == 'e':
                    self.advance()
                    state = 108
                    continue
                state = 196
                continue

            elif state == 108:
                if ch == 'w':
                    self.advance()
                    state = 109
                    continue
                state = 196
                continue

            elif state == 109:
                if self.is_delim1(ch):
                    state = 110
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 110:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("view", lexeme, start_line, start_col))
                return

            # ===================================================
            # w-branch (wall / while / write) 111–119
            # ===================================================

            elif state == 111:
                if ch == 'a':
                    self.advance()
                    state = 112
                    continue
                if ch == 'h':
                    self.advance()
                    state = 116
                    continue
                if ch == 'r':
                    self.advance()
                    state = 121
                    continue
                state = 196
                continue

            # wall: w a l l
            elif state == 112:
                if ch == 'l':
                    self.advance()
                    state = 113
                    continue
                state = 196
                continue

            elif state == 113:
                if ch == 'l':
                    self.advance()
                    state = 114
                    continue
                state = 196
                continue

            elif state == 114:
                if self.is_whitespace(ch):
                    state = 115
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 115:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("wall", lexeme, start_line, start_col))
                return

            # while: w h i l e
            elif state == 116:
                if ch == 'i':
                    self.advance()
                    state = 117
                    continue
                state = 196
                continue

            elif state == 117:
                if ch == 'l':
                    self.advance()
                    state = 118
                    continue
                state = 196
                continue

            elif state == 118:
                if ch == 'e':
                    self.advance()
                    state = 119
                    continue
                state = 196
                continue

            elif state == 119:
                if self.is_delim1(ch):
                    state = 120
                    continue
                    
                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 120:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("while", lexeme, start_line, start_col))
                return            

            # write: w r i t e
            elif state == 121:
                if ch == 'i':
                    self.advance()
                    state = 122
                    continue
                state = 196
                continue

            elif state == 122:
                if ch == 't':
                    self.advance()
                    state = 123
                    continue
                state = 196
                continue

            elif state == 123:
                if ch == 'e':
                    self.advance()
                    state = 124
                    continue
                state = 196
                continue

            elif state == 124:
                if self.is_delim1(ch):
                    state = 125
                    continue

                if self.is_alpha_num(ch):
                    state = 196
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )
            
            elif state == 125:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("write", lexeme, start_line, start_col))
                return

            # ===================================================
            # Operators: =, ==, +, ++, +=, -, --, -=, *, *=, /, /=,
            #            %, %=, >, >=, <, <=  (126–161)
            # ===================================================

            # '=' or '=='
            elif state == 126:
                if ch == '=':
                    self.advance()
                    state = 128
                    continue

                if self.is_delim6(ch):
                    state = 127
                    continue
                
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 127:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("=", lexeme, start_line, start_col))
                return

            elif state == 128:
                if self.is_delim7(ch):
                    state = 129
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )
            
            elif state == 129:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("==", lexeme, start_line, start_col))
                return

            # '+', '++', '+='
            elif state == 130:
                if ch == '+':
                    self.advance()
                    state = 132
                    continue
                if ch == '=':
                    self.advance()
                    state = 134
                    continue
                if self.is_delim8(ch):
                    state = 131
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 131:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("+", lexeme, start_line, start_col))
                return

            elif state == 132:
                if self.is_delim9(ch):
                    state = 133
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 133:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("++", lexeme, start_line, start_col))
                return

            elif state == 134:
                if self.is_delim10(ch):
                    state = 135
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 135:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("+=", lexeme, start_line, start_col))
                return

            # '-', '--', '-=' (and negative numbers)
            elif state == 136:
                if self.is_number(ch):
                    self.advance()
                    state = 236
                    continue

                # 2) "--"
                if ch == '-':
                    self.advance()
                    state = 138
                    continue

                # 3) "-="
                if ch == '=':
                    self.advance()
                    state = 140
                    continue

                # 4) single '-'
                if self.is_delim11(ch):
                    state = 137
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 137:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("-", lexeme, start_line, start_col))
                return

            elif state == 138:
                if self.is_delim9(ch):
                    state = 139
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 139:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("--", lexeme, start_line, start_col))
                return

            elif state == 140:
                if self.is_delim10(ch):
                    state = 141
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 141:
                # FINAL STATE for "-="
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("-=", lexeme, start_line, start_col))
                return

            # '*', '*='
            elif state == 142:
                if ch == '=':
                    self.advance()
                    state = 144
                    continue

                if self.is_delim10(ch):
                    state = 143
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 143:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("*", lexeme, start_line, start_col))
                return

            elif state == 144:
                if self.is_delim10(ch):
                    state = 145
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 145:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("*=", lexeme, start_line, start_col))
                return

            # '/', '/=', '//' and '/* ... */'
            elif state == 146:
                if ch == '/':
                    self.advance()
                    state = 290      # line comment "///..." or "//"
                    continue
                if ch == '*':
                    self.advance()
                    state = 292      # block comment "/* ... */"
                    continue
                if ch == '=':
                    self.advance()
                    state = 148      # "/="
                    continue

                if self.is_delim10(ch):
                    state = 147
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 147:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("/", lexeme, start_line, start_col))
                return

            elif state == 148:
                if self.is_delim10(ch):
                    state = 149
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 149:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("/=", lexeme, start_line, start_col))
                return

            # '%', '%='
            elif state == 150:
                if ch == '=':
                    self.advance()
                    state = 152

                if self.is_delim10(ch):
                    state = 151
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 151:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("%", lexeme, start_line, start_col))
                return

            elif state == 152:
                if self.is_delim10(ch):
                    state = 153
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 153:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("%=", lexeme, start_line, start_col))
                return

            # '>', '>='
            elif state == 154:
                if ch == '=':
                    self.advance()
                    state = 156
                    continue

                if self.is_delim7(ch):
                    state = 155
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 155:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(">", lexeme, start_line, start_col))
                return

            elif state == 156:
                if self.is_delim7(ch):
                    state = 157
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 157:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(">=", lexeme, start_line, start_col))
                return

            # '<', '<='
            elif state == 158:
                if ch == '=':
                    self.advance()
                    state = 160
                    continue

                if self.is_delim7(ch):
                    state = 159
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 159:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("<", lexeme, start_line, start_col))
                return

            elif state == 160:
                if self.is_delim7(ch):
                    state = 161
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 161:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("<=", lexeme, start_line, start_col))
                return


            # ===================================================
            # Logical / bitwise / punctuation with 2-step finals
            # ===================================================

            # '!' and '!='
            elif state == 162:
                if ch == '=':
                    self.advance()
                    state = 164
                    continue
                if self.is_delim7(ch):
                    state = 163
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 163:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("!", lexeme, start_line, start_col))
                return

            elif state == 164:
                if self.is_delim7(ch):
                    state = 165
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 165:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("!=", lexeme, start_line, start_col))
                return

            # '&' (address-of) and '&&' (logical AND)
            elif state == 166:
                if ch == '&':
                    self.advance()
                    state = 168
                    continue
                if self.is_alpha_id(ch):
                    state = 167
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 167:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("&", lexeme, start_line, start_col))
                return

            elif state == 168:
                if self.is_delim7(ch):
                    state = 169
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 169:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("&&", lexeme, start_line, start_col))
                return

            # '||' (logical OR) - single '|' is invalid
            elif state == 170:
                if ch == '|':
                    self.advance()
                    state = 171
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 171:
                if self.is_delim7(ch):
                    state = 172
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 172:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("||", lexeme, start_line, start_col))
                return

            # Single-character separators with their own final states

            # '{'
            elif state == 173:
                if self.is_delim12(ch):
                    state = 174
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 174:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("{", lexeme, start_line, start_col))
                return

            # '}'
            elif state == 175:
                if self.is_delim13(ch):
                    state = 176
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 176:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("}", lexeme, start_line, start_col))
                return

            # '('
            elif state == 177:
                if self.is_delim14(ch):
                    state = 178
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 178:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("(", lexeme, start_line, start_col))
                return

            # ')'
            elif state == 179:
                if self.is_delim15(ch):
                    state = 180
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 180:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(")", lexeme, start_line, start_col))
                return

            # '['
            elif state == 181:
                if self.is_delim16(ch):
                    state = 182
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 182:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("[", lexeme, start_line, start_col))
                return

            # ']'
            elif state == 183:
                if self.is_delim17(ch):
                    state = 184
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 184:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("]", lexeme, start_line, start_col))
                return

            # '.' (dot)
            elif state == 185:
                if self.is_alpha_id(ch):
                    state = 186
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 186:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(".", lexeme, start_line, start_col))
                return

            # ','
            elif state == 187:
                if self.is_delim18(ch):
                    state = 188
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 188:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(",", lexeme, start_line, start_col))
                return

            # ':'
            elif state == 189:
                if self.is_whitespace(ch):
                    state = 190
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 190:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(":", lexeme, start_line, start_col))
                return

            # ';'
            elif state == 191:
                if self.is_delim19(ch):
                    state = 192
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 192:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(";", lexeme, start_line, start_col))
                return



            # ===================================================
            # Whitespace tokens: space / tab / newline 193–195
            # ===================================================

            elif state == 193:  # space
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("space", lexeme, start_line, start_col))
                return

            elif state == 194:  # tab
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tab", lexeme, start_line, start_col))
                return

            elif state == 195:  # newline
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("newline", lexeme, start_line, start_col))
                return


            # ===================================================
            # Generic identifier DFA (20-char max)
            # States: 196,198,...,234  (reading)
            # Final states: 197,199,...,235 (after delim20)
            # ===================================================

            # length 1
            elif state == 196:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 198  # length 2
                    continue
                if self.is_delim20(ch):
                    state = 197
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 197:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 2
            elif state == 198:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 200  # length 3
                    continue
                if self.is_delim20(ch):
                    state = 199
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 199:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 3
            elif state == 200:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 202  # length 4
                    continue
                if self.is_delim20(ch):
                    state = 201
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 201:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 4
            elif state == 202:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 204  # length 5
                    continue
                if self.is_delim20(ch):
                    state = 203
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 203:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 5
            elif state == 204:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 206  # length 6
                    continue
                if self.is_delim20(ch):
                    state = 205
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 205:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 6
            elif state == 206:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 208  # length 7
                    continue
                if self.is_delim20(ch):
                    state = 207
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 207:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 7
            elif state == 208:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 210  # length 8
                    continue
                if self.is_delim20(ch):
                    state = 209
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 209:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 8
            elif state == 210:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 212  # length 9
                    continue
                if self.is_delim20(ch):
                    state = 211
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 211:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 9
            elif state == 212:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 214  # length 10
                    continue
                if self.is_delim20(ch):
                    state = 213
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 213:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 10
            elif state == 214:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 216  # length 11
                    continue
                if self.is_delim20(ch):
                    state = 215
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 215:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 11
            elif state == 216:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 218  # length 12
                    continue
                if self.is_delim20(ch):
                    state = 217
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 217:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 12
            elif state == 218:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 220  # length 13
                    continue
                if self.is_delim20(ch):
                    state = 219
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 219:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 13
            elif state == 220:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 222  # length 14
                    continue
                if self.is_delim20(ch):
                    state = 221
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 221:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 14
            elif state == 222:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 224  # length 15
                    continue
                if self.is_delim20(ch):
                    state = 223
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 223:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 15
            elif state == 224:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 226  # length 16
                    continue
                if self.is_delim20(ch):
                    state = 225
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 225:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 16
            elif state == 226:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 228  # length 17
                    continue
                if self.is_delim20(ch):
                    state = 227
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 227:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 17
            elif state == 228:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 230  # length 18
                    continue
                if self.is_delim20(ch):
                    state = 229
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 229:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 18
            elif state == 230:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 232  # length 19
                    continue
                if self.is_delim20(ch):
                    state = 231
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 231:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 19
            elif state == 232:
                if self.is_alpha_num(ch):
                    self.advance()
                    state = 234  # length 20
                    continue
                if self.is_delim20(ch):
                    state = 233
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 233:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return

            # length 20 (max)
            elif state == 234:
                if self.is_delim20(ch):
                    state = 235
                    continue
                if self.is_alpha_num(ch):
                    lexeme = self.source[start_pos:self.pos]
                    raise LexerError(
                        f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                    )
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 235:
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return



            # ===================================================
            # Numeric literal DFA
            # Integers: up to 15 digits (states 236..265)
            # Floats:   up to 7 decimal digits (states 266..280)
            # ===================================================

            # integer length 1
            elif state == 236:
                if self.is_delim21(ch):
                    state = 237
                    continue
                if self.is_number(ch):
                    self.advance()
                    state = 238  # integer length 2
                    continue
                if ch == '.':
                    self.advance()
                    state = 266  # enter decimal part
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 237:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 2
            elif state == 238:
                if self.is_number(ch):
                    self.advance()
                    state = 240  # integer length 3
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 239
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 239:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 3
            elif state == 240:
                if self.is_number(ch):
                    self.advance()
                    state = 242  # integer length 4
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 241
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 241:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 4
            elif state == 242:
                if self.is_number(ch):
                    self.advance()
                    state = 244  # integer length 5
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 243
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 243:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 5
            elif state == 244:
                if self.is_number(ch):
                    self.advance()
                    state = 246  # integer length 6
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 245
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 245:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 6
            elif state == 246:
                if self.is_number(ch):
                    self.advance()
                    state = 248  # integer length 7
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 247
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 247:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 7
            elif state == 248:
                if self.is_number(ch):
                    self.advance()
                    state = 250  # integer length 8
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 249
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 249:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 8
            elif state == 250:
                if self.is_number(ch):
                    self.advance()
                    state = 252  # integer length 9
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 251
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 251:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 9
            elif state == 252:
                if self.is_number(ch):
                    self.advance()
                    state = 254  # integer length 10
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 253
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 253:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 10
            elif state == 254:
                if self.is_number(ch):
                    self.advance()
                    state = 256  # integer length 11
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 255
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 255:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 11
            elif state == 256:
                if self.is_number(ch):
                    self.advance()
                    state = 258  # integer length 12
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 257
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 257:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 12
            elif state == 258:
                if self.is_number(ch):
                    self.advance()
                    state = 260  # integer length 13
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 259
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 259:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 13
            elif state == 260:
                if self.is_number(ch):
                    self.advance()
                    state = 262  # integer length 14
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 261
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 261:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 14
            elif state == 262:
                if self.is_number(ch):
                    self.advance()
                    state = 264  # integer length 15
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 263
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 263:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # integer length 15 (max)
            elif state == 264:
                if self.is_number(ch):
                    lexeme = self.source[start_pos:self.pos]
                    raise LexerError(
                        f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                    )
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    state = 265
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 265:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                return

            # ---- decimal part ----
            # state 266: just after '.', expecting first decimal digit
            elif state == 266:
                if not self.is_number(ch):
                    lexeme = self.source[start_pos:self.pos]
                    raise LexerError(
                        f"Error on line {start_line}: {lexeme!r} is an invalid lexeme (expected digit after '.')"
                    )
                # consume first decimal digit and go to length-1 state (268)
                self.advance()
                state = 268  # decimal length 1
                continue

            # decimal length 1
            elif state == 268:
                if self.is_number(ch):
                    self.advance()
                    state = 270  # decimal length 2
                    continue
                if self.is_delim22(ch):
                    state = 267
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 267:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return

            # decimal length 2
            elif state == 270:
                if self.is_number(ch):
                    self.advance()
                    state = 272  # decimal length 3
                    continue
                if self.is_delim22(ch):
                    state = 269
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 269:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return

            # decimal length 3
            elif state == 272:
                if self.is_number(ch):
                    self.advance()
                    state = 274  # decimal length 4
                    continue
                if self.is_delim22(ch):
                    state = 271
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 271:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return

            # decimal length 4
            elif state == 274:
                if self.is_number(ch):
                    self.advance()
                    state = 276  # decimal length 5
                    continue
                if self.is_delim22(ch):
                    state = 273
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 273:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return

            # decimal length 5
            elif state == 276:
                if self.is_number(ch):
                    self.advance()
                    state = 278  # decimal length 6
                    continue
                if self.is_delim22(ch):
                    state = 275
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 275:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return

            # decimal length 6
            elif state == 278:
                if self.is_number(ch):
                    self.advance()
                    state = 280  # decimal length 7
                    continue
                if self.is_delim22(ch):
                    state = 277
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 277:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return

            # decimal length 7 (max)
            elif state == 280:
                if self.is_number(ch):
                    lexeme = self.source[start_pos:self.pos]
                    raise LexerError(
                        f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                    )
                if self.is_delim22(ch):
                    state = 279
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )

            elif state == 279:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("glass_lit", lexeme, start_line, start_col))
                return





            # ===================================================
            # Brick literal: 'a' or '\n'   281–284  (unchanged except 284)
            # ===================================================

            elif state == 281:
                if ch == '\\':
                    self.advance()
                    state = 282
                    continue
                if self.is_ascii1(ch):
                    self.advance()
                    state = 283
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )


            elif state == 282:
                if self.is_escape_seq_char(ch):
                    self.advance()
                    state = 283
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )


            elif state == 283:
                if ch == "'":
                    self.advance()
                    state = 284
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )


            elif state == 284:
                lexeme = self.source[start_pos:self.pos]
                if self.is_delim23(ch):
                    self.tokens.append(Token("brick_lit", lexeme, start_line, start_col))
                    return

                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )



            # ===================================================
            # Wall / string literal: "..."  286–288
            # ===================================================

            elif state == 286:
                if ch == '"':
                    # closing quote
                    self.advance()
                    state = 288
                    continue
                if ch == '\\':
                    self.advance()
                    state = 287
                    continue
                if self.is_ascii2(ch):
                    # ascii content
                    self.advance()
                    continue

                # newline / EOF / bad char → unterminated
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )


            elif state == 287:
                if self.is_escape_seq_char(ch):
                    self.advance()
                    state = 286
                    continue
                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme (invalid escape sequence)"
                )


            elif state == 288:
                lexeme = self.source[start_pos:self.pos]
                if self.is_delim23(ch):
                    self.tokens.append(Token("wall_lit", lexeme, start_line, start_col))
                    return

                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme"
                )




            # ===================================================
            # Comments: '//' and '/* ... */' 290, 292, 293, 295
            # ===================================================

            # single-line: //
            elif state == 290:
                # after seeing '//' – inside single-line comment body
                ch = self.current

                # λ (EOF) OR newline ends the comment → go to FINAL STATE 291
                if ch is None or self.is_newline(ch):
                    state = 291
                    continue

                # ascii3 / tab / any other char on this line → stay in 290
                self.advance()
                continue

            elif state == 291:
                # FINAL state for single-line comment
                # comment text is from start_pos up to (but not including) newline/EOF
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(
                    Token("Single-Line Comment", lexeme, start_line, start_col)
                )

                # If we ended on a newline, consume it so next token starts on next line
                if self.current == '\n':
                    self.advance()

                return

            elif state == 292:
                if ch is None:
                    lexeme = self.source[start_pos:self.pos]
                    raise LexerError(
                        f"Error on line {start_line}: {lexeme!r} is an unterminated multi-line comment"
                    )

                if ch == '*':
                    self.advance()
                    state = 293
                    continue

                self.advance()
                continue

            elif state == 293:
                if ch is None:
                    lexeme = self.source[start_pos:self.pos]
                    raise LexerError(
                        f"Error on line {start_line}: {lexeme!r} is an unterminated multi-line comment"
                    )

                if ch == '*':
                    self.advance()
                    state = 293
                    continue

                if ch == '/':
                    self.advance()
                    state = 294
                    continue

                self.advance()
                state = 292
                continue


            elif state == 294:
                if ch is None or self.is_whitespace(ch):
                    state = 295
                    continue

                lexeme = self.source[start_pos:self.pos]
                raise LexerError(
                    f"Error on line {start_line}: {lexeme!r} is an invalid lexeme (invalid delimiter after multi-line comment)"
                )

            elif state == 295:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(
                    Token("Multi-Line Comment", lexeme, start_line, start_col)
                )
                return
