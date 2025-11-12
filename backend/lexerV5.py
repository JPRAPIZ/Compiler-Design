# -*- coding: utf-8 -*-
from enum import Enum, auto
from dataclasses import dataclass
import sys

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

@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int
    value: any = None

class State:
    START=0; INT=1; INT_NEG=2; FLOAT_FRAC=3
    STRING=4; STRING_ESC=5; CHAR=6; CHAR_ESC=7
    SLASH=8; LINE_COMMENT=9; BLOCK_COMMENT=10; BLOCK_COMMENT_STAR=11

class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1
        self.errors = []

    # ---- helpers ----
    def _is_at_end(self): return self.pos >= len(self.src)
    def _peek(self): return None if self._is_at_end() else self.src[self.pos]
    def _peek_next(self): return None if self.pos+1 >= len(self.src) else self.src[self.pos+1]
    def _advance(self):
        ch = self.src[self.pos]; self.pos += 1
        if ch == '\n': self.line += 1; self.col = 1
        else: self.col += 1
        return ch
    def _is_alpha_id(self, ch): return ch is not None and (ch == '_' or ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'))
    def _is_digit(self, ch): return ch is not None and ch.isdigit()
    def _is_id_continue(self, ch): return ch is not None and (ch == '_' or ch.isalnum())
    def _make_token(self, ttype, lexeme, start_col, value=None):
        if value is None: value = lexeme
        return Token(ttype, lexeme, self.line, start_col, value)
    def _err(self, msg, ch=None, col=None):
        if ch is None: ch = self._peek() or "EOF"
        if col is None: col = self.col
        self.errors.append({"line": self.line, "col": col, "character": ch, "message": msg})
        print(f"[Lexical Error] {self.line}:{col} {msg} ('{ch}')", file=sys.stderr)

    # ====== KEYWORD LADDERS (literal TD paths; lowercase only) ======
    def _finish_ident(self, start_col, buf):
        while self._is_id_continue(self._peek()):
            buf.append(self._advance())
        return self._make_token(TokenType.IDENTIFIER, "".join(buf), start_col)

    def _emit_kw_or_ident(self, start_col, buf, kw_type):
        # keyword valid iff next char is NOT id-continue
        if not self._is_id_continue(self._peek()):
            return self._make_token(kw_type, "".join(buf), start_col)
        return self._finish_ident(start_col, buf)

    def _kw_from_b(self, start_col, first):  # brick / beam / blueprint
        buf=[first]
        c=self._peek()
        if c=='r':
            buf.append(self._advance()); c=self._peek()
            if c=='i':
                buf.append(self._advance()); c=self._peek()
                if c=='c':
                    buf.append(self._advance()); c=self._peek()
                    if c=='k':
                        buf.append(self._advance())
                        return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_BRICK)
        elif c=='e':
            buf.append(self._advance()); c=self._peek()
            if c=='a':
                buf.append(self._advance()); c=self._peek()
                if c=='m':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_BEAM)
        elif c=='l':  # blueprint
            buf.append(self._advance())
            for expect in ('u','e','p','r','i','n','t'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_BLUEPRINT)
        return self._finish_ident(start_col, buf)

    def _kw_from_w(self, start_col, first):  # wall / while / write
        buf=[first]
        c=self._peek()
        if c=='a':
            buf.append(self._advance())
            if self._peek()=='l':
                buf.append(self._advance())
                if self._peek()=='l':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_WALL)
        if c=='h':
            buf.append(self._advance())
            for expect in ('i','l','e'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_WHILE)
        if c=='r':
            buf.append(self._advance())
            for expect in ('i','t','e'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_WRITE)
        return self._finish_ident(start_col, buf)

    def _kw_from_t(self, start_col, first):  # tile
        buf=[first]
        if self._peek()=='i':
            buf.append(self._advance())
            if self._peek()=='l':
                buf.append(self._advance())
                if self._peek()=='e':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_TILE)
        return self._finish_ident(start_col, buf)

    def _kw_from_g(self, start_col, first):  # glass / ground
        buf=[first]; c=self._peek()
        if c=='l':
            buf.append(self._advance())
            for expect in ('a','s','s'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_GLASS)
        if c=='r':
            buf.append(self._advance())
            for expect in ('o','u','n','d'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_GROUND)
        return self._finish_ident(start_col, buf)

    def _kw_from_f(self, start_col, first):  # for / fragile / field
        buf=[first]; c=self._peek()
        if c=='o':
            buf.append(self._advance())
            if self._peek()=='r':
                buf.append(self._advance())
                return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_FOR)
        if c=='r':
            buf.append(self._advance())
            for expect in ('a','g','i','l','e'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_FRAGILE)
        if c=='i':
            buf.append(self._advance())
            for expect in ('e','l','d'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_FIELD)
        return self._finish_ident(start_col, buf)

    def _kw_from_h(self, start_col, first):  # house / home
        buf=[first]; c=self._peek()
        if c=='o':
            buf.append(self._advance()); c=self._peek()
            if c=='u':
                buf.append(self._advance())
                for expect in ('s','e'):
                    if self._peek()==expect: buf.append(self._advance())
                    else: return self._finish_ident(start_col, buf)
                return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_HOUSE)
            if c=='m':
                buf.append(self._advance())
                if self._peek()=='e':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_HOME)
        return self._finish_ident(start_col, buf)

    def _kw_from_r(self, start_col, first):  # roof / room
        buf=[first]; c=self._peek()
        if c=='o':
            buf.append(self._advance())
            if self._peek()=='o':
                buf.append(self._advance())
                if self._peek()=='f':
                    buf.append(self._advance()); return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_ROOF)
                if self._peek()=='m':
                    buf.append(self._advance()); return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_ROOM)
        return self._finish_ident(start_col, buf)

    def _kw_from_c(self, start_col, first):  # cement / crack
        buf=[first]; c=self._peek()
        if c=='e':
            buf.append(self._advance())
            for expect in ('m','e','n','t'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_CEMENT)
        if c=='r':
            buf.append(self._advance())
            for expect in ('a','c','k'):
                if self._peek()==expect: buf.append(self._advance())
                else: return self._finish_ident(start_col, buf)
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_CRACK)
        return self._finish_ident(start_col, buf)

    def _kw_from_m(self, start_col, first):  # mend
        buf=[first]
        if self._peek()=='e':
            buf.append(self._advance())
            if self._peek()=='n':
                buf.append(self._advance())
                if self._peek()=='d':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_MEND)
        return self._finish_ident(start_col, buf)

    def _kw_from_d(self, start_col, first):  # do / door
        buf=[first]
        if self._peek()=='o':
            buf.append(self._advance())
            if not self._is_id_continue(self._peek()):
                return self._make_token(TokenType.TOK_DO, "".join(buf), start_col)
            if self._peek()=='o':
                buf.append(self._advance())
                if self._peek()=='r':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_DOOR)
        return self._finish_ident(start_col, buf)

    def _kw_from_e(self, start_col, first):  # else
        buf=[first]
        if self._peek()=='l':
            buf.append(self._advance())
            if self._peek()=='s':
                buf.append(self._advance())
                if self._peek()=='e':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_ELSE)
        return self._finish_ident(start_col, buf)

    def _kw_from_i(self, start_col, first):  # if
        buf=[first]
        if self._peek()=='f':
            buf.append(self._advance())
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_IF)
        return self._finish_ident(start_col, buf)

    def _kw_from_v(self, start_col, first):  # view
        buf=[first]
        if self._peek()=='i':
            buf.append(self._advance())
            if self._peek()=='e':
                buf.append(self._advance())
                if self._peek()=='w':
                    buf.append(self._advance())
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_VIEW)
        return self._finish_ident(start_col, buf)

    def _kw_from_s(self, start_col, first):  # solid
        buf=[first]
        if self._peek()=='o':
            buf.append(self._advance())
            if self._peek()=='l':
                buf.append(self._advance())
                if self._peek()=='i':
                    buf.append(self._advance())
                    if self._peek()=='d':
                        buf.append(self._advance())
                        return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_SOLID)
        return self._finish_ident(start_col, buf)

    # ====== Core DFA ======
    def get_next_token(self):
        state = State.START
        start_col = self.col
        buf = []

        while True:
            ch = self._peek()

            # EOF
            if ch is None:
                if state == State.INT:
                    return self._make_token(TokenType.NUMBER, "".join(buf), start_col)
                if state == State.FLOAT_FRAC:
                    return self._make_token(TokenType.GLASS_NUMBER, "".join(buf), start_col)
                if state == State.BLOCK_COMMENT:
                    self._err("Unterminated block comment at EOF", "EOF", self.col)
                return self._make_token(TokenType.TOK_EOF, "EOF", self.col)

            if state == State.START:
                start_col = self.col
                # whitespace (distinct)
                if ch == ' ':
                    self._advance(); return self._make_token(TokenType.TOK_SPACE, " ", start_col)
                if ch == '\t':
                    self._advance(); return self._make_token(TokenType.TOK_TAB, "\t", start_col)
                if ch == '\n':
                    self._advance(); return self._make_token(TokenType.TOK_NEWLINE, "\n", start_col)

                # identifier or keyword (case-sensitive; keywords must be lowercase)
                if self._is_alpha_id(ch):
                    first = self._advance()
                    if 'A' <= first <= 'Z':
                        buf=[first]
                        while self._is_id_continue(self._peek()):
                            buf.append(self._advance())
                        return self._make_token(TokenType.IDENTIFIER, "".join(buf), start_col)
                    if first == 'b': return self._kw_from_b(start_col, first)
                    if first == 'w': return self._kw_from_w(start_col, first)
                    if first == 't': return self._kw_from_t(start_col, first)
                    if first == 'g': return self._kw_from_g(start_col, first)
                    if first == 'f': return self._kw_from_f(start_col, first)
                    if first == 'h': return self._kw_from_h(start_col, first)
                    if first == 'r': return self._kw_from_r(start_col, first)
                    if first == 'c': return self._kw_from_c(start_col, first)
                    if first == 'm': return self._kw_from_m(start_col, first)
                    if first == 'd': return self._kw_from_d(start_col, first)
                    if first == 'e': return self._kw_from_e(start_col, first)
                    if first == 'i': return self._kw_from_i(start_col, first)
                    if first == 'v': return self._kw_from_v(start_col, first)
                    if first == 's': return self._kw_from_s(start_col, first)
                    # not a keyword head -> IDENTIFIER
                    buf=[first]
                    while self._is_id_continue(self._peek()):
                        buf.append(self._advance())
                    return self._make_token(TokenType.IDENTIFIER, "".join(buf), start_col)

                # numbers
                if ch == '-':
                    if self._peek_next() and self._peek_next().isdigit():
                        state = State.INT_NEG; buf=['-']; self._advance(); continue
                    self._advance()
                    if self._peek() == '-':
                        self._advance(); return self._make_token(TokenType.TOK_DECREMENT, "--", start_col)
                    if self._peek() == '=':
                        self._advance(); return self._make_token(TokenType.TOK_SUB_ASSIGN, "-=", start_col)
                    return self._make_token(TokenType.TOK_MINUS, "-", start_col)

                if ch.isdigit():
                    state = State.INT; buf=[self._advance()]; continue

                if ch == '.':
                    self._advance(); return self._make_token(TokenType.TOK_PERIOD, ".", start_col)

                # string / char
                if ch == '"':
                    state = State.STRING; buf=[]; self._advance(); continue
                if ch == "'":
                    state = State.CHAR; buf=[]; self._advance(); continue

                # slash → comment or divide
                if ch == '/':
                    state = State.SLASH; self._advance(); continue

                # operators & symbols
                if ch == '+':
                    self._advance()
                    if self._peek()=='+': self._advance(); return self._make_token(TokenType.TOK_INCREMENT,"++",start_col)
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_ADD_ASSIGN,"+=",start_col)
                    return self._make_token(TokenType.TOK_PLUS,"+",start_col)

                if ch == '*':
                    self._advance()
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_MUL_ASSIGN,"*=",start_col)
                    return self._make_token(TokenType.TOK_MULTIPLY,"*",start_col)

                if ch == '%':
                    self._advance()
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_MOD_ASSIGN,"%=",start_col)
                    return self._make_token(TokenType.TOK_MODULO,"%",start_col)

                if ch == '=':
                    self._advance()
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_EQUALS,"==",start_col)
                    return self._make_token(TokenType.TOK_ASSIGN,"=",start_col)

                if ch == '!':
                    self._advance()
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_NOT_EQUAL,"!=",start_col)
                    return self._make_token(TokenType.TOK_NOT,"!",start_col)

                if ch == '<':
                    self._advance()
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_LT_EQUAL,"<=",start_col)
                    return self._make_token(TokenType.TOK_LESS_THAN,"<",start_col)

                if ch == '>':
                    self._advance()
                    if self._peek()=='=': self._advance(); return self._make_token(TokenType.TOK_GT_EQUAL,">=",start_col)
                    return self._make_token(TokenType.TOK_GREATER_THAN,">",start_col)

                if ch == '&':
                    self._advance()
                    if self._peek()=='&':
                        self._advance(); return self._make_token(TokenType.TOK_AND,"&&",start_col)
                    self._err("Unexpected '&' (expected '&&')", '&', start_col)
                    continue  # error, no token

                if ch == '|':
                    self._advance()
                    if self._peek()=='|':
                        self._advance(); return self._make_token(TokenType.TOK_OR,"||",start_col)
                    self._err("Unexpected '|' (expected '||')", '|', start_col)
                    continue  # error, no token

                if ch == '(':
                    self._advance(); return self._make_token(TokenType.TOK_OP_PARENTHESES,"(",start_col)
                if ch == ')':
                    self._advance(); return self._make_token(TokenType.TOK_CL_PARENTHESES,")",start_col)
                if ch == '{':
                    self._advance(); return self._make_token(TokenType.TOK_OP_BRACE,"{",start_col)
                if ch == '}':
                    self._advance(); return self._make_token(TokenType.TOK_CL_BRACE,"}",start_col)
                if ch == '[':
                    self._advance(); return self._make_token(TokenType.TOK_OP_BRACKET,"[",start_col)
                if ch == ']':
                    self._advance(); return self._make_token(TokenType.TOK_CL_BRACKET,"]",start_col)
                if ch == ';':
                    self._advance(); return self._make_token(TokenType.TOK_SEMICOLON,";",start_col)
                if ch == ':':
                    self._advance(); return self._make_token(TokenType.TOK_COLON,":",start_col)
                if ch == ',':
                    self._advance(); return self._make_token(TokenType.TOK_COMMA,",",start_col)

                # unknown single char
                bad = self._advance()
                self._err("Unknown character", bad, start_col)
                continue

            # ===== Numbers =====
            if state == State.INT:
                if ch.isdigit():
                    buf.append(self._advance())
                    continue
                if ch == '.':
                    # float only if a digit follows the dot
                    if self._peek_next() and self._peek_next().isdigit():
                        buf.append(self._advance())  # '.'
                        state = State.FLOAT_FRAC
                        continue
                    # end integer; '.' will be handled next
                    return self._make_token(TokenType.NUMBER, "".join(buf), start_col)

                # 🚫 forbid identifier-start right after a number (e.g., 123abc, 1x)
                if self._is_alpha_id(ch):
                    self._err("Invalid token: identifier cannot start with a digit (e.g., '1x')", ch, self.col)
                    # consume bad tail to avoid cascading errors
                    while self._is_id_continue(self._peek()):
                        self._advance()
                    state = State.START
                    buf.clear()
                    continue

                # any other non-digit ends integer
                return self._make_token(TokenType.NUMBER, "".join(buf), start_col)

            if state == State.INT_NEG:
                if ch and ch.isdigit():
                    buf.append(self._advance())
                    state = State.INT
                    continue

                # 🚫 '-<alpha|_>' invalid numeric start
                if self._is_alpha_id(ch):
                    self._err("Invalid token: identifier cannot start with a digit (e.g., '-5x')", ch, self.col)
                    while self._is_id_continue(self._peek()):
                        self._advance()
                    state = State.START
                    buf.clear()
                    continue

                self._err("Invalid negative number (expected digit after '-')", ch, start_col)
                state = State.START
                continue

            if state == State.FLOAT_FRAC:
                if ch.isdigit():
                    buf.append(self._advance())
                    continue

                # 🚫 forbid identifier-start right after a float (e.g., 12.3x)
                if self._is_alpha_id(ch):
                    self._err("Invalid token: identifier cannot start with a digit (e.g., '1x')", ch, self.col)
                    while self._is_id_continue(self._peek()):
                        self._advance()
                    state = State.START
                    buf.clear()
                    continue

                # fraction ends on first non-digit; no second dot allowed
                if ch == '.':
                    self._err("Invalid float: multiple '.'", ch, self.col)
                    self._advance()  # consume stray '.'
                    return self._make_token(TokenType.GLASS_NUMBER, "".join(buf), start_col)

                return self._make_token(TokenType.GLASS_NUMBER, "".join(buf), start_col)

            # ===== Strings & Chars =====
            if state == State.STRING:
                if ch == '"':
                    self._advance()
                    lex = '"' + "".join(buf) + '"'
                    return self._make_token(TokenType.TOK_WALL_LITERAL, lex, start_col, value="".join(buf))
                if ch == '\\':
                    self._advance(); state = State.STRING_ESC; continue
                buf.append(self._advance()); continue

            if state == State.STRING_ESC:
                esc = self._advance()
                if esc in ('n','t','\\',"'",'"','0'):
                    mapping = {'n':'\n','t':'\t','\\':'\\',"'":"'",'"':'"','0':'\0'}
                    buf.append(mapping[esc])
                else:
                    self._err("Invalid escape in string", esc, self.col-1)
                    buf.append(esc)
                state = State.STRING; continue

            if state == State.CHAR:
                if ch is None or ch == '\n':
                    self._err("Unterminated char literal", ch, start_col)
                    state = State.START; continue
                if ch == "'":
                    self._err("Empty char literal", ch, start_col)
                    self._advance(); state = State.START; continue
                if ch == '\\':
                    self._advance(); state = State.CHAR_ESC; continue
                buf.append(self._advance())
                if self._peek() == "'":
                    self._advance()
                    if len(buf) != 1:
                        self._err("Char literal must contain exactly one character", "'", self.col-1)
                        state = State.START; buf.clear(); continue
                    lex = "'" + "".join(buf) + "'"
                    return self._make_token(TokenType.TOK_BRICK_LITERAL, lex, start_col, value=buf[0])
                else:
                    self._err("Expected closing ' in char literal", self._peek(), self.col)
                    state = State.START; buf.clear(); continue

            if state == State.CHAR_ESC:
                esc = self._advance()
                if esc in ('n','t','\\',"'",'"','0'):
                    mapping = {'n':'\n','t':'\t','\\':'\\',"'":"'",'"':'"','0':'\0'}
                    buf.append(mapping[esc])
                else:
                    self._err("Invalid escape in char literal", esc, self.col-1)
                    buf.append(esc)
                if self._peek() == "'":
                    self._advance()
                    if len(buf) != 1:
                        self._err("Char literal must contain exactly one character", "'", self.col-1)
                        state = State.START; buf.clear(); continue
                    lex = "'" + "".join(buf) + "'"
                    return self._make_token(TokenType.TOK_BRICK_LITERAL, lex, start_col, value=buf[0])
                else:
                    self._err("Expected closing ' after escape", self._peek(), self.col)
                    state = State.START; buf.clear(); continue

            # ===== Comments / Slash branch =====
            if state == State.SLASH:
                if ch == '/':
                    self._advance(); state = State.LINE_COMMENT; continue
                if ch == '*':
                    self._advance(); state = State.BLOCK_COMMENT; continue
                if ch == '=':
                    self._advance(); return self._make_token(TokenType.TOK_DIV_ASSIGN, "/=", start_col)
                return self._make_token(TokenType.TOK_DIVIDE, "/", start_col)

            if state == State.LINE_COMMENT:
                if ch == '\n':
                    state = State.START; continue
                self._advance(); continue

            if state == State.BLOCK_COMMENT:
                if ch == '*':
                    self._advance(); state = State.BLOCK_COMMENT_STAR; continue
                self._advance(); continue

            if state == State.BLOCK_COMMENT_STAR:
                if ch == '/':
                    self._advance(); state = State.START; continue
                else:
                    state = State.BLOCK_COMMENT; continue

    def tokenize_all(self):
        out=[]
        while True:
            t=self.get_next_token()
            out.append(t)
            if t.type == TokenType.TOK_EOF: break
        return out

if __name__ == "__main__":
    demo = r"""tile x = 10;
glass g = -5.25;
wall s = "He\tllo";
brick c = '\n';
if (solid && x >= 10) {
  // line
  view("#d", s);
  g /= 2.0;  a123   // number then ident is not allowed; handled as error chunk
  c = 'AB';        // error: too many chars
  do { write("ok"); } while (0);
  FRAGILE;         // IDENTIFIER (case-sensitive)
  1x;              // error: identifier cannot start with a digit
  12.3abc;         // error: same rule for float
  -5y;             // error: same rule for negative
  a = 1..2;        // error: multiple dots in float
  a = 1.|2;        // error: single '|'
  a = 1.&2;        // error: single '&'
  /* unterminated...
"""
    L = Lexer(demo)
    for tok in L.tokenize_all():
        print(tok)
    if L.errors:
        print("\nErrors:")
        for e in L.errors:
            print(e)
