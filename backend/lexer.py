# backend/lexer.py

from typing import List
from tokens import Token


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
        """Record an error at the current position without raising."""
        self.errors.append({
            "message": message,
            "line": self.line,
            "col": self.column,
            "start_line": start_line if start_line is not None else self.line,
            "start_col": start_col if start_col is not None else self.column,
            "end_line": self.line,
            "end_col": self.column,
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
        return ch is not None and ch.isdigit()

    def is_alpha_id(self, ch) -> bool:
        return ch is not None and (ch.isalpha() or ch == '_')

    def is_alpha_num(self, ch) -> bool:
        return self.is_number(ch) or self.is_alpha_id(ch)

    def is_whitespace(self, ch) -> bool:
        return ch in (' ', '\t', '\n')

    def is_operator_char(self, ch) -> bool:
        return ch in "+-*/%<>=!&|"

    def is_ascii_range(self, ch, lo: int, hi: int) -> bool:
        return ch is not None and lo <= ord(ch) <= hi

    def is_ascii1(self, ch) -> bool:
        # ascii code 32 to 126 excluding \ and '
        return self.is_ascii_range(ch, 32, 126) and ch not in ('\\', "'")

    def is_ascii2(self, ch) -> bool:
        # ascii code 32 to 126 excluding \ and "
        return self.is_ascii_range(ch, 32, 126) and ch not in ('\\', '"')

    def is_ascii3(self, ch) -> bool:
        # ascii code 32 to 126
        return self.is_ascii_range(ch, 32, 126)

    def is_ascii4(self, ch) -> bool:
        # ascii code 32 to 126 excluding *
        return self.is_ascii_range(ch, 32, 126) and ch != '*'

    def is_ascii5(self, ch) -> bool:
        # ascii code 32 to 126 excluding /
        return self.is_ascii_range(ch, 32, 126) and ch != '/'

    def is_escape_seq_char(self, ch) -> bool:
        # { n , t , ' , " , \ , 0 }
        return ch in ('n', 't', "'", '"', '\\', '0')

    # ============================================================
    # Delimiters  (delim1 ... delim25)
    # ============================================================

    def is_delim1(self, ch) -> bool:
        # { ( , whitespace }
        return self.is_eof(ch) or ch == '(' or self.is_whitespace(ch)

    def is_delim2(self, ch) -> bool:
        # { ; , whitespace }
        return self.is_eof(ch) or ch == ';' or self.is_whitespace(ch)

    def is_delim3(self, ch) -> bool:
        # { { , whitespace }
        return self.is_eof(ch) or ch == '{' or self.is_whitespace(ch)

    def is_delim4(self, ch) -> bool:
        # { operators , } , ) , ] , : , ; , , ,  whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in ('}', ')', ']', ':', ';', ',')
            or self.is_whitespace(ch)
        )

    def is_delim5(self, ch) -> bool:
        # { : , whitespace }
        return self.is_eof(ch) or ch == ':' or self.is_whitespace(ch)

    def is_delim6(self, ch) -> bool:
        # { alpha_num , + , - , ! , { , ( , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', '{', '(', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim7(self, ch) -> bool:
        # { alpha_num , + , - , ! , ( , ' , " ,  whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', '(', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim8(self, ch) -> bool:
        # { alpha_num , - , ! , ( , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '!', '(', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim9(self, ch) -> bool:
        # { alpha_id , ) , ] , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_id(ch)
            or ch in (')', ']', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim10(self, ch) -> bool:
        # { alpha_num , + , - , ! , ' , ( , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', "'", '(')
            or self.is_whitespace(ch)
        )

    def is_delim11(self, ch) -> bool:
        # { alpha_id , + , ! , ( , ' , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_id(ch)
            or ch in ('+', '!', '(', "'")
            or self.is_whitespace(ch)
        )

    def is_delim12(self, ch) -> bool:
        # { alpha_num , - , { , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '{', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim13(self, ch) -> bool:
        # { alpha_id, } , ; , , , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_id(ch)
            or ch in ('}', ';', ',')
            or self.is_whitespace(ch)
        )

    def is_delim14(self, ch) -> bool:
        # { alpha_num , - , + , ! , ( , ) , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '+', '!', '(', ')', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim15(self, ch) -> bool:
        # { operators , { , ) , ] , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in ('{', ')', ']', ';')
            or self.is_whitespace(ch)
        )

    def is_delim16(self, ch) -> bool:
        # { alpha_num , + , - , ! , ( , ] , ' , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-', '!', '(', ']', "'")
            or self.is_whitespace(ch)
        )

    def is_delim17(self, ch) -> bool:
        # { operators , ) , [ , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', '[', ';')
            or self.is_whitespace(ch)
        )

    def is_delim18(self, ch) -> bool:
        # { alpha_num , - , & , ' , " , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('-', '&', "'", '"')
            or self.is_whitespace(ch)
        )

    def is_delim19(self, ch) -> bool:
        # { alpha_num , + , - , whitespace }
        return (
            self.is_eof(ch)
            or self.is_alpha_num(ch)
            or ch in ('+', '-')
            or self.is_whitespace(ch)
        )

    def is_delim20(self, ch) -> bool:
        # { operators , ( , ) , [ , ] , . , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in ('(', ')', '[', ']', '.', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim21(self, ch) -> bool:
        # { operators, ) , ] , } , , , : , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', ']', '}', ',', ':', ';')
            or self.is_whitespace(ch)
        )

    def is_delim22(self, ch) -> bool:
        # { operators, ) , ] , } , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', ']', '}', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim23(self, ch) -> bool:
        # { operators , ) , ] , } , , , : , ; , whitespace }
        return (
            self.is_eof(ch)
            or self.is_operator_char(ch)
            or ch in (')', ']', '}', ',', ':', ';')
            or self.is_whitespace(ch)
        )

    def is_delim24(self, ch) -> bool:
        # { + , > , < , = , ! , & , | , ) , , , ; , whitespace }
        return (
            self.is_eof(ch)
            or ch in ('+', '>', '<', '=', '!', '&', '|', ')', ',', ';')
            or self.is_whitespace(ch)
        )

    def is_delim25(self, ch) -> bool:
        # { ascii3 , whitespace }
        if self.is_eof(ch):
            return True
        return self.is_ascii3(ch) or self.is_whitespace(ch)

    # ============================================================
    # Public API
    # ============================================================

    def scanTokens(self) -> List[Token]:
        """Scan the entire source into a list of tokens."""
        while self.current is not None:
            # remember where this token starts (for error highlighting)
            self.token_start_pos = self.pos
            self.token_start_line = self.line
            self.token_start_col = self.column

            try:
                # one DFA run per token/comment/whitespace
                self.lex_from_state0()

            except LexerError as e:
                # 1) store the error, so api.py + frontend can show it
                self.add_error(
                    str(e),
                    start_line=self.token_start_line,
                    start_col=self.token_start_col,
                )

                # 2) also push an ERROR token so it appears in the token area
                end_index = self.pos
                if self.current is not None:
                    end_index = self.pos + 1

                err_lexeme = self.source[self.token_start_pos:end_index]
                self.tokens.append(
                    Token("ERROR", err_lexeme, self.token_start_line, self.token_start_col)
                )

                # 3) recovery: advance at least 1 char to avoid infinite loop,
                #    then continue scanning. This allows multiple errors on the same line.
                if self.current is not None:
                    self.advance()

                continue

        # EOF token (same idea as old lexer)
        eof = Token("$", "EOF", self.line, self.column)
        self.tokens.append(eof)
        return self.tokens





    # ============================================================
    # Main DFA (transition table encoded as states)
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

                # --- keywords by first letter ---
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

                # --- identifiers (generic) ---
                if self.is_alpha_id(ch):
                    self.advance()
                    state = 196
                    continue

                raise LexerError(
                    f"Unexpected start of token {ch!r} at line {self.line}, col {self.column}"
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
                if self.is_delim1(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("beam", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("blueprint", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("brick", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("cement", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("crack", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("do", lexeme, start_line, start_col))
                    return
                if ch == 'o':
                    self.advance()
                    state = 35
                    continue
                state = 196
                continue

            elif state == 35:
                if ch == 'r':
                    self.advance()
                    state = 36
                    continue
                state = 196
                continue

            elif state == 36:
                if self.is_delim3(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("door", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("else", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("for", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("field", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("fragile", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim5(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("glass", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("ground", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("home", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("house", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("if", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("mend", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # ===================================================
            # r-branch (roof / room / rite) 88–93, 121–123
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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("roof", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # room
            elif state == 93:
                if self.is_delim1(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("room", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # rite: r i t e
            elif state == 121:
                if ch == 't':
                    self.advance()
                    state = 122
                    continue
                state = 196
                continue

            elif state == 122:
                if ch == 'e':
                    self.advance()
                    state = 123
                    continue
                state = 196
                continue

            elif state == 123:
                if self.is_delim1(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("rite", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("solid", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("tile", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("view", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # ===================================================
            # w-branch (wall / while) 111–119
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
                if self.is_delim4(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("wall", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("while", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 128:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("==", lexeme, start_line, start_col))
                    return
                state = 196
                continue

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
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("+", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 132:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("++", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 134:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("+=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '-', '--', '-=' (and negative numbers)
            elif state == 136:
                if self.is_number(ch):
                    self.advance()
                    state = 236
                    continue
                if ch == '-':
                    self.advance()
                    state = 138
                    continue
                if ch == '=':
                    self.advance()
                    state = 140
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("-", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 138:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("--", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 140:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("-=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '*', '*='
            elif state == 142:
                if ch == '=':
                    self.advance()
                    state = 144
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("*", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 144:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("*=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '/', '/=', '//' and '/* ... */'
            elif state == 146:
                if ch == '/':
                    self.advance()
                    state = 290
                    continue
                if ch == '*':
                    self.advance()
                    state = 292
                    continue
                if ch == '=':
                    self.advance()
                    state = 148
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("/", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 148:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("/=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '%', '%='
            elif state == 150:
                if ch == '=':
                    self.advance()
                    state = 152
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("%", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 152:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("%=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '>', '>='
            elif state == 154:
                if ch == '=':
                    self.advance()
                    state = 156
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token(">", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 156:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token(">=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '<', '<='
            elif state == 158:
                if ch == '=':
                    self.advance()
                    state = 160
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("<", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 160:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("<=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # ===================================================
            # Logical / punctuation / grouping 162–191
            # ===================================================

            # '!' and '!='
            elif state == 162:
                if ch == '=':
                    self.advance()
                    state = 164
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("!", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 164:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("!=", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '&' and '&&'
            elif state == 166:
                if ch == '&':
                    self.advance()
                    state = 168
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("&", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            elif state == 168:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("&&", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # '||'
            elif state == 170:
                if ch == '|':
                    self.advance()
                    state = 171
                    continue
                state = 196
                continue

            elif state == 171:
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("||", lexeme, start_line, start_col))
                    return
                state = 196
                continue

            # braces, parens, brackets, punctuation
            elif state == 173:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("{", lexeme, start_line, start_col))
                return

            elif state == 175:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("}", lexeme, start_line, start_col))
                return

            elif state == 177:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("(", lexeme, start_line, start_col))
                return

            elif state == 179:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(")", lexeme, start_line, start_col))
                return

            elif state == 181:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("[", lexeme, start_line, start_col))
                return

            elif state == 183:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("]", lexeme, start_line, start_col))
                return

            elif state == 185:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(".", lexeme, start_line, start_col))
                return

            elif state == 187:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(",", lexeme, start_line, start_col))
                return

            elif state == 189:
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token(":", lexeme, start_line, start_col))
                return

            elif state == 191:
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
            # Generic identifier (alpha_id / alpha_num) 196
            # ===================================================

            elif state == 196:
                if self.is_alpha_num(ch):
                    self.advance()
                    continue
                if self.is_delim20(ch):
                    lexeme = self.source[start_pos:self.pos]
                    tok_type = self.get_id_token_type(lexeme)
                    self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                    return
                raise LexerError(
                    f"Invalid character {ch!r} after identifier at line {self.line}"
                )

            # ===================================================
            # Numbers (int + float) 236, 266, 267
            # ===================================================

            elif state == 236:
                if self.is_number(ch):
                    self.advance()
                    continue
                if ch == '.':
                    self.advance()
                    state = 266
                    continue
                if self.is_delim21(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("tile_lit", lexeme, start_line, start_col))
                    return
                raise LexerError(
                    f"Invalid character {ch!r} after integer literal at line {self.line}"
                )

            elif state == 266:
                if not self.is_number(ch):
                    raise LexerError(
                        f"Expected digit after '.' in float literal at line {self.line}"
                    )
                self.advance()
                state = 267
                continue

            elif state == 267:
                if self.is_number(ch):
                    self.advance()
                    continue
                if self.is_delim22(ch):
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(Token("number_float", lexeme, start_line, start_col))
                    return
                raise LexerError(
                    f"Invalid character {ch!r} after float literal at line {self.line}"
                )

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
                raise LexerError(f"Invalid brick literal start at line {self.line}")

            elif state == 282:
                if self.is_escape_seq_char(ch):
                    self.advance()
                    state = 283
                    continue
                raise LexerError(
                    f"Invalid escape sequence in brick literal at line {self.line}"
                )

            elif state == 283:
                if ch == "'":
                    self.advance()
                    state = 284
                    continue
                raise LexerError(f"Unterminated brick literal at line {self.line}")

            elif state == 284:
                # We ALWAYS emit the brick literal token (it's valid by itself)
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("brick_lit", lexeme, start_line, start_col))

                if self.is_delim23(ch):
                    # good delimiter → just finish
                    return
                else:
                    # bad delimiter → report error, BUT do not consume the char
                    # so that the next DFA run can start from it
                    self.add_error(
                        "Invalid delimiter after brick literal",
                        start_line=start_line,
                        start_col=start_col,
                    )
                    return

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
                raise LexerError(f"Unterminated wall literal at line {self.line}")

            elif state == 287:
                if self.is_escape_seq_char(ch):
                    self.advance()
                    state = 286
                    continue
                raise LexerError(
                    f"Invalid escape sequence in wall literal at line {self.line}"
                )

            elif state == 288:
                # We ALWAYS emit the wall literal token; the string itself is valid
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(Token("wall_lit", lexeme, start_line, start_col))

                if self.is_delim24(ch):
                    # good delimiter → done
                    return
                else:
                    # bad delimiter → log error but DO NOT advance,
                    # so the same char becomes the start of the next token.
                    self.add_error(
                        "Invalid delimiter after wall literal",
                        start_line=start_line,
                        start_col=start_col,
                    )
                    return


            # ===================================================
            # Comments: '//' and '/* ... */' 290, 292, 293, 295
            # ===================================================

            # single-line: //
            elif state == 290:   # after '//'
                # newline ends the comment
                if ch == '\n':
                    # comment is from start_pos up to (but not including) newline
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(
                        Token("comment_single", lexeme, start_line, start_col)
                    )
                    self.advance()   # consume newline so next token sees the next line
                    return

                # EOF ends the comment too
                if ch is None:
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(
                        Token("comment_single", lexeme, start_line, start_col)
                    )
                    return

                # ascii3: any other char on the line
                self.advance()
                continue


            # Inside '/* ... */'
            elif state == 292:   # comment body (ascii4 / λ)
                # EOF: treat entire rest of file as part of the comment, then stop
                if ch is None:
                    # emit multi-line comment token up to EOF
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(
                        Token("comment_multi", lexeme, start_line, start_col)
                    )
                    return   # matches your rule: everything until EOF is comment

                if ch == '*':
                    self.advance()
                    state = 293   # possible end sequence
                    continue

                # any other char (including newline)
                self.advance()
                continue


            elif state == 293:   # have seen at least one '*'
                # EOF: still just “comment until end of file”
                if ch is None:
                    lexeme = self.source[start_pos:self.pos]
                    self.tokens.append(
                        Token("comment_multi", lexeme, start_line, start_col)
                    )
                    return

                if ch == '/':
                    # found closing */
                    self.advance()
                    state = 295
                    continue

                # ascii5: not '/', go back to body
                self.advance()
                state = 292
                continue


            elif state == 295:   # just finished '*/'
                # comment token is from start_pos up to current pos (including */)
                lexeme = self.source[start_pos:self.pos]
                self.tokens.append(
                    Token("comment_multi", lexeme, start_line, start_col)
                )
                # according to your TD, delim25 (ascii3 or whitespace) is checked
                # by the next DFA run, so we just return here.
                return

            
            elif state == 100:
                # consume any remaining identifier chars
                if ch is not None and (ch.isalnum() or ch == '_'):
                    self.advance()
                    continue

                # reached delimiter → emit identifier
                lexeme = self.source[start_pos:self.pos]
                tok_type = self.get_id_token_type(lexeme)  # id1, id2, ...
                self.tokens.append(Token(tok_type, lexeme, start_line, start_col))
                return


