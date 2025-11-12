# backend/dfa_lexer_pkg/lexer.py
# -*- coding: utf-8 -*-
from typing import List, Tuple
from . import config as CFG
from .token_types import TokenType
from .lexer_token import Token
from .states import State
from .keywords import KEYWORDS  # if you keep a dict; not strictly used here
from .errors import *
from .diagram_states import KW_PATHS, GEN

# --------------------------------------------------------------------
# Delimiter predicates from your spec (including delim25 you added)
# --------------------------------------------------------------------
OPS = set("+-*/%<>=!&|")
BRACES = set("{}")
PARENS = set("()")
WS = {" ", "\t", "\n"}

def _is_alpha_id_ch(ch: str) -> bool:
    return ch is not None and (ch == "_" or ("a" <= ch <= "z") or ("A" <= ch <= "Z"))

def _is_alpha_num_ch(ch: str) -> bool:
    return ch is not None and (_is_alpha_id_ch(ch) or ch.isdigit())

def _is_ws(ch: str) -> bool:
    return ch in WS

def _is_ops(ch: str) -> bool:
    return ch in OPS

def _is_ascii3(ch: str) -> bool:
    return ch is not None and len(ch) == 1 and 32 <= ord(ch) <= 126

def _delim1(ch):   return ch in PARENS or _is_ws(ch)
def _delim2(ch):   return ch == ";" or _is_ws(ch)
def _delim3(ch):   return ch in BRACES or _is_ws(ch)
def _delim4(ch):   return _is_ops(ch) or ch in BRACES or ch in {")", "]", ":", ";", ","} or _is_ws(ch)
def _delim5(ch):   return ch == ":" or _is_ws(ch)
def _delim6(ch):   return _is_alpha_num_ch(ch) or ch in {"+","-","!","{","(","'",'"'} or _is_ws(ch)
def _delim7(ch):   return _is_alpha_num_ch(ch) or ch in {"+","-","!","(","'",'"'} or _is_ws(ch)
def _delim8(ch):   return _is_alpha_num_ch(ch) or ch in {"-","!","(","'",'"'} or _is_ws(ch)
def _delim9(ch):   return _is_alpha_id_ch(ch) or ch in {")","]",",",";"} or _is_ws(ch)
def _delim10(ch):  return _is_alpha_num_ch(ch) or ch in {"+","-","!","'"} or _is_ws(ch)
def _delim11(ch):  return _is_alpha_id_ch(ch) or ch in {"+","!","(","'"} or _is_ws(ch)
def _delim12(ch):  return _is_alpha_num_ch(ch) or ch in {"-","{","'",'"'} or _is_ws(ch)
def _delim13(ch):  return _is_alpha_id_ch(ch) or ch in {"}", ";", ","} or _is_ws(ch)
def _delim14(ch):  return _is_alpha_num_ch(ch) or ch in {"+","-","!","(",")","'",'"'} or _is_ws(ch)
def _delim15(ch):  return _is_ops(ch) or ch in {"{",")","]",";"} or _is_ws(ch)
def _delim16(ch):  return _is_alpha_num_ch(ch) or ch in {"+","-","!","(","]","'"} or _is_ws(ch)
def _delim17(ch):  return _is_ops(ch) or ch in {")","[",";"} or _is_ws(ch)
def _delim18(ch):  return _is_alpha_num_ch(ch) or ch in {"-","&","'",'"'} or _is_ws(ch)
def _delim19(ch):  return _is_alpha_num_ch(ch) or ch in {"+","-"} or _is_ws(ch)
def _delim20(ch):  return _is_ops(ch) or ch in {"(",")","[","]",".",",",";"} or _is_ws(ch)
def _delim21(ch):  return _is_ops(ch) or ch in {")","]","}",",",":",";"} or _is_ws(ch)
def _delim22(ch):  return _is_ops(ch) or ch in {")","]","}",",",";"} or _is_ws(ch)
def _delim23(ch):  return _is_ops(ch) or ch in {")","]","}",",",":",";"} or _is_ws(ch)
def _delim24(ch):  return ch in {"+",">","<","=","!","&","|",")",",",";"} or _is_ws(ch)
def _delim25(ch):  return ch is None or _is_ascii3(ch) or _is_ws(ch)  # { ascii3 , whitespace }

def _whitespace_only(ch):
    # some ladders literally label "whitespace" at the end
    return _is_ws(ch) or ch is None

# ---------- STRICT LOOKAHEAD HELPERS ----------
def _skip_ws_peek(lex):
    """
    Return first NON-whitespace char ahead (without consuming).
    None if EOF.
    """
    i = lex.pos
    n = len(lex.src)
    while i < n and lex.src[i] in WS:
        i += 1
    return None if i >= n else lex.src[i]

def _delim1_strict(lex, _next_immediate_char_unused):
    # TD: delim1 = { ( , whitespace }  -> after optional WS, next must be '(' (or EOF)
    ch = _skip_ws_peek(lex)
    return ch in ('(', None)

def _delim2_strict(lex, _next_immediate_char_unused):
    # TD: delim2 = { ; , whitespace }  -> after optional WS, next must be ';' (or EOF)
    ch = _skip_ws_peek(lex)
    return ch in (';', None)

def _delim3_strict(lex, _next_immediate_char_unused):
    # TD: delim3 = { { , whitespace }  -> after optional WS, next must be '{' (or EOF)
    ch = _skip_ws_peek(lex)
    return ch in ('{', None)

def _delim5_strict(lex, _next_immediate_char_unused):
    # TD: delim5 = { : , whitespace }  -> after optional WS, next must be ':' (or EOF)
    ch = _skip_ws_peek(lex)
    return ch in (':', None)

# ---------- IMMEDIATE DELIMS WITH (lex, ch) SIGNATURE ----------
def _imm_delim1(lex, ch):   return _delim1(ch)
def _imm_delim2(lex, ch):   return _delim2(ch)
def _imm_delim3(lex, ch):   return _delim3(ch)
def _imm_delim4(lex, ch):   return _delim4(ch)
def _imm_delim5(lex, ch):   return _delim5(ch)
def _imm_delim6(lex, ch):   return _delim6(ch)
def _imm_delim7(lex, ch):   return _delim7(ch)
def _imm_delim8(lex, ch):   return _delim8(ch)
def _imm_delim9(lex, ch):   return _delim9(ch)
def _imm_delim10(lex, ch):  return _delim10(ch)
def _imm_delim11(lex, ch):  return _delim11(ch)
def _imm_delim12(lex, ch):  return _delim12(ch)
def _imm_delim13(lex, ch):  return _delim13(ch)
def _imm_delim14(lex, ch):  return _delim14(ch)
def _imm_delim15(lex, ch):  return _delim15(ch)
def _imm_delim16(lex, ch):  return _delim16(ch)
def _imm_delim17(lex, ch):  return _delim17(ch)
def _imm_delim18(lex, ch):  return _delim18(ch)
def _imm_delim19(lex, ch):  return _delim19(ch)
def _imm_delim20(lex, ch):  return _delim20(ch)
def _imm_delim21(lex, ch):  return _delim21(ch)
def _imm_delim22(lex, ch):  return _delim22(ch)
def _imm_delim23(lex, ch):  return _delim23(ch)
def _imm_delim24(lex, ch):  return _delim24(ch)
def _imm_delim25(lex, ch):  return _delim25(ch)

def _ws_only(lex, ch):      return _whitespace_only(ch)

# ---------- TOKEN -> DELIMITER PREDICATE (STRICT WHERE TD REQUIRES) ----------
_TOKEN_DELIM = {
    # identifiers & literals (from "Others" table)
    TokenType.IDENTIFIER:        _imm_delim20,
    TokenType.NUMBER:            _imm_delim21,  # Tile_Literal (integer form)
    TokenType.GLASS_NUMBER:      _imm_delim22,  # Glass_Literal (float form)
    TokenType.TOK_BRICK_LITERAL: _imm_delim23,
    TokenType.TOK_WALL_LITERAL:  _imm_delim24,

    # keywords — strict vs immediate per the TD
    # Must be '(' after optional WS (delim1 strict)
    TokenType.TOK_BLUEPRINT: _delim1_strict,
    TokenType.TOK_FOR:       _delim1_strict,
    TokenType.TOK_WHILE:     _delim1_strict,
    TokenType.TOK_WRITE:     _delim1_strict,
    TokenType.TOK_VIEW:      _delim1_strict,
    TokenType.TOK_IF:        _delim1_strict,

    # Must be ';' after optional WS (delim2 strict)
    TokenType.TOK_CRACK:     _delim2_strict,
    TokenType.TOK_MEND:      _delim2_strict,

    # Must be '{' after optional WS (delim3 strict)
    TokenType.TOK_DO:        _delim3_strict,

    # Must be ':' after optional WS (delim5 strict)
    TokenType.TOK_GROUND:    _delim5_strict,

    # Whitespace-only endings (per diagram)
    TokenType.TOK_BRICK:     _ws_only,
    TokenType.TOK_CEMENT:    _ws_only,
    TokenType.TOK_ELSE:      _ws_only,
    TokenType.TOK_FIELD:     _ws_only,
    TokenType.TOK_GLASS:     _ws_only,
    TokenType.TOK_HOME:      _ws_only,
    TokenType.TOK_HOUSE:     _ws_only,
    TokenType.TOK_ROOF:      _ws_only,
    TokenType.TOK_ROOM:      _ws_only,
    TokenType.TOK_TILE:      _ws_only,
    TokenType.TOK_SOLID:     _ws_only,
    TokenType.TOK_FRAGILE:   _imm_delim4,   # your table says delim4 after 'fragile'
    TokenType.TOK_WALL:      _ws_only,

    # whitespace tokens themselves end with delim25 per your sheet
    TokenType.TOK_SPACE:    _imm_delim25,
    TokenType.TOK_TAB:      _imm_delim25,
    TokenType.TOK_NEWLINE:  _imm_delim25,
}

def _delimiter_ok(lex, ttype, next_char):
    pred = _TOKEN_DELIM.get(ttype)
    return True if pred is None else pred(lex, next_char)

# --------------------------------------------------------------------
# Lexer with diagram-state tracing and delimiter validation
# --------------------------------------------------------------------
class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1
        self.errors = []
        self._trace_buf: List[Tuple[str, str, str]] = []

    def _is_at_end(self): return self.pos >= len(self.src)
    def _peek(self): return None if self._is_at_end() else self.src[self.pos]
    def _peek_next(self): return None if self.pos+1 >= len(self.src) else self.src[self.pos+1]

    def _advance_state(self, state_num: int, logical_label: str):
        ch = self.src[self.pos]
        self.pos += 1
        self._trace_buf.append((str(state_num), logical_label, ch))
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _make_token(self, ttype, lexeme, start_col, value=None):
        if value is None: value = lexeme
        tok = Token(ttype, lexeme, self.line, start_col, value=value, trace=self._trace_buf)
        self._trace_buf = []
        return tok

    def _emit_with_delim_check(self, ttype, lexeme, start_col, value=None):
        nxt = self._peek()  # immediate next char (for error context)
        if not _delimiter_ok(self, ttype, nxt):
            self._err(f"Invalid delimiter after {ttype.name} (got {repr(nxt)} per TD)", nxt, self.col)
        return self._make_token(ttype, lexeme, start_col, value)

    def _err(self, msg, ch=None, col=None):
        if ch is None: ch = self._peek() or "EOF"
        if col is None: col = self.col
        self.errors.append({"line": self.line, "col": col, "character": ch, "message": msg})

    # helpers
    def _is_alpha_id(self, ch): return _is_alpha_id_ch(ch)
    def _is_digit(self, ch): return ch is not None and ch.isdigit()
    def _is_id_continue(self, ch): return _is_alpha_num_ch(ch)

    # ---------------- identifiers / keywords ----------------
    def _emit_kw_or_ident(self, start_col, buf, kw_type):
        if not self._is_id_continue(self._peek()):
            return self._emit_with_delim_check(kw_type, "".join(buf), start_col)
        return self._finish_ident(start_col, buf)

    def _finish_ident(self, start_col, buf):
        while self._is_id_continue(self._peek()):
            if len(buf) >= CFG.IDENT_MAX_LEN:
                self._err(ERR_IDENT_TOO_LONG, self._peek(), self.col)
                while self._is_id_continue(self._peek()):
                    self._advance_state(GEN.get("ID_CONT", GEN["START"]), "ID:overflow")
                if CFG.EMIT_TOKEN_ON_LENGTH_ERROR:
                    return self._emit_with_delim_check(TokenType.IDENTIFIER, "".join(buf), start_col)
                else:
                    self._trace_buf = []
                    return None
            buf.append(self._advance_state(GEN.get("ID_CONT", GEN["START"]), "ID:cont"))
        return self._emit_with_delim_check(TokenType.IDENTIFIER, "".join(buf), start_col)

    # --- keyword ladders (exact TD paths) ---
    # NOTE: first letter already consumed in START; we use KW_PATHS to step states.
    def _kw_from_b(self, start_col, first):
        buf=[first]
        if self._peek() == 'r':  # brick
            p = KW_PATHS["brick"]; buf.append(self._advance_state(p[1], "KW:brick:r"))
            if self._peek() == 'i':
                buf.append(self._advance_state(p[2], "KW:brick:i"))
                if self._peek() == 'c':
                    buf.append(self._advance_state(p[3], "KW:brick:c"))
                    if self._peek() == 'k':
                        buf.append(self._advance_state(p[4], "KW:brick:k"))
                        return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_BRICK)
        if self._peek() == 'e':  # beam
            p = KW_PATHS["beam"]; buf.append(self._advance_state(p[1], "KW:beam:e"))
            if self._peek() == 'a':
                buf.append(self._advance_state(p[2], "KW:beam:a"))
                if self._peek() == 'm':
                    buf.append(self._advance_state(p[3], "KW:beam:m"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_BEAM)
        if self._peek() == 'l':  # blueprint
            p = KW_PATHS["blueprint"]; buf.append(self._advance_state(p[1], "KW:blueprint:l"))
            for idx, ch in enumerate(('u','e','p','r','i','n','t'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:blueprint:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_BLUEPRINT)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_w(self, start_col, first):
        buf=[first]
        if self._peek() == 'a':  # wall
            p = KW_PATHS["wall"]; buf.append(self._advance_state(p[1], "KW:wall:a"))
            if self._peek() == 'l':
                buf.append(self._advance_state(p[2], "KW:wall:l"))
                if self._peek() == 'l':
                    buf.append(self._advance_state(p[3], "KW:wall:l"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_WALL)
        if self._peek() == 'h':  # while
            p = KW_PATHS["while"]; buf.append(self._advance_state(p[1], "KW:while:h"))
            for idx, ch in enumerate(('i','l','e'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:while:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_WHILE)
        if self._peek() == 'r':  # write
            p = KW_PATHS["write"]; buf.append(self._advance_state(p[1], "KW:write:r"))
            for idx, ch in enumerate(('i','t','e'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:write:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_WRITE)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_t(self, start_col, first):
        buf=[first]
        p = KW_PATHS["tile"]
        if self._peek() == 'i':
            buf.append(self._advance_state(p[1], "KW:tile:i"))
            if self._peek() == 'l':
                buf.append(self._advance_state(p[2], "KW:tile:l"))
                if self._peek() == 'e':
                    buf.append(self._advance_state(p[3], "KW:tile:e"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_TILE)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_g(self, start_col, first):
        buf=[first]
        if self._peek() == 'l':  # glass
            p = KW_PATHS["glass"]; buf.append(self._advance_state(p[1], "KW:glass:l"))
            for idx, ch in enumerate(('a','s','s'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:glass:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_GLASS)
        if self._peek() == 'r':  # ground
            p = KW_PATHS["ground"]; buf.append(self._advance_state(p[1], "KW:ground:r"))
            for idx, ch in enumerate(('o','u','n','d'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:ground:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_GROUND)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_f(self, start_col, first):
        buf=[first]
        if self._peek() == 'o':  # for
            p = KW_PATHS["for"]; buf.append(self._advance_state(p[1], "KW:for:o"))
            if self._peek() == 'r':
                buf.append(self._advance_state(p[2], "KW:for:r"))
                return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_FOR)
        if self._peek() == 'r':  # fragile
            p = KW_PATHS["fragile"]; buf.append(self._advance_state(p[1], "KW:fragile:r"))
            for idx, ch in enumerate(('a','g','i','l','e'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:fragile:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_FRAGILE)
        if self._peek() == 'i':  # field
            p = KW_PATHS["field"]; buf.append(self._advance_state(p[1], "KW:field:i"))
            for idx, ch in enumerate(('e','l','d'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:field:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_FIELD)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_h(self, start_col, first):
        buf=[first]
        if self._peek() == 'o':
            if self._peek_next() == 'u':  # house
                p = KW_PATHS["house"]; buf.append(self._advance_state(p[1], "KW:house:o"))
                buf.append(self._advance_state(p[2], "KW:house:u"))
                if self._peek() == 's':
                    buf.append(self._advance_state(p[3], "KW:house:s"))
                    if self._peek() == 'e':
                        buf.append(self._advance_state(p[4], "KW:house:e"))
                        return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_HOUSE)
            elif self._peek_next() == 'm':  # home
                p = KW_PATHS["home"]; buf.append(self._advance_state(p[1], "KW:home:o"))
                buf.append(self._advance_state(p[2], "KW:home:m"))
                if self._peek() == 'e':
                    buf.append(self._advance_state(p[3], "KW:home:e"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_HOME)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_r(self, start_col, first):
        buf=[first]
        if self._peek() == 'o':
            # roof / room
            p_roof = KW_PATHS["roof"]; p_room = KW_PATHS["room"]
            buf.append(self._advance_state(p_roof[1], "KW:r:o"))
            if self._peek() == 'o':
                if self._peek_next() == 'f':
                    buf.append(self._advance_state(p_roof[2], "KW:roof:o"))
                    buf.append(self._advance_state(p_roof[3], "KW:roof:f"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_ROOF)
                if self._peek_next() == 'm':
                    buf.append(self._advance_state(p_room[2], "KW:room:o"))
                    buf.append(self._advance_state(p_room[3], "KW:room:m"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_ROOM)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_c(self, start_col, first):
        buf=[first]
        if self._peek() == 'e':  # cement
            p = KW_PATHS["cement"]; buf.append(self._advance_state(p[1], "KW:cement:e"))
            for idx, ch in enumerate(('m','e','n','t'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:cement:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_CEMENT)
        if self._peek() == 'r':  # crack
            p = KW_PATHS["crack"]; buf.append(self._advance_state(p[1], "KW:crack:r"))
            for idx, ch in enumerate(('a','c','k'), start=2):
                if self._peek() == ch:
                    buf.append(self._advance_state(p[idx], f"KW:crack:{ch}"))
                else:
                    return self._finish_ident(start_col, buf) or self.get_next_token()
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_CRACK)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_d(self, start_col, first):
        buf=[first]
        if self._peek() == 'o':
            p_do = KW_PATHS["do"]; buf.append(self._advance_state(p_do[1], "KW:do:o"))
            if not self._is_id_continue(self._peek()):
                return self._emit_with_delim_check(TokenType.TOK_DO, "".join(buf), start_col)
            # door handled via _kw_from_r in your table; optional
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_e(self, start_col, first):
        buf=[first]
        if self._peek() == 'l':
            p = KW_PATHS["else"]; buf.append(self._advance_state(p[1], "KW:else:l"))
            if self._peek() == 's':
                buf.append(self._advance_state(p[2], "KW:else:s"))
                if self._peek() == 'e':
                    buf.append(self._advance_state(p[3], "KW:else:e"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_ELSE)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_i(self, start_col, first):
        buf=[first]
        if self._peek() == 'f':
            p = KW_PATHS["if"]; buf.append(self._advance_state(p[1], "KW:if:f"))
            return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_IF)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_v(self, start_col, first):
        buf=[first]
        if self._peek() == 'i':
            p = KW_PATHS["view"]; buf.append(self._advance_state(p[1], "KW:view:i"))
            if self._peek() == 'e':
                buf.append(self._advance_state(p[2], "KW:view:e"))
                if self._peek() == 'w':
                    buf.append(self._advance_state(p[3], "KW:view:w"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_VIEW)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_s(self, start_col, first):
        buf=[first]
        if self._peek() == 'o':
            p = KW_PATHS["solid"]; buf.append(self._advance_state(p[1], "KW:solid:o"))
            if self._peek() == 'l':
                buf.append(self._advance_state(p[2], "KW:solid:l"))
                if self._peek() == 'i':
                    buf.append(self._advance_state(p[3], "KW:solid:i"))
                    if self._peek() == 'd':
                        buf.append(self._advance_state(p[4], "KW:solid:d"))
                        return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_SOLID)
        return self._finish_ident(start_col, buf) or self.get_next_token()

    def _kw_from_m(self, start_col, first):
        # TD path: m-e-n-d
        buf = [first]
        if self._peek() == 'e':
            p = KW_PATHS["mend"]  # must exist in diagram_states.KW_PATHS
            buf.append(self._advance_state(p[1], "KW:mend:e"))
            if self._peek() == 'n':
                buf.append(self._advance_state(p[2], "KW:mend:n"))
                if self._peek() == 'd':
                    buf.append(self._advance_state(p[3], "KW:mend:d"))
                    return self._emit_kw_or_ident(start_col, buf, TokenType.TOK_MEND)
        # fall back to identifier if any letter mismatches
        return self._finish_ident(start_col, buf) or self.get_next_token()


    # ---------------- core DFA ----------------
    def get_next_token(self):
        state = State.START
        start_col = self.col
        buf: List[str] = []

        while True:
            ch = self._peek()

            if ch is None:
                if state == State.INT:
                    return self._emit_with_delim_check(TokenType.NUMBER, "".join(buf), start_col)
                if state == State.FLOAT_FRAC:
                    return self._emit_with_delim_check(TokenType.GLASS_NUMBER, "".join(buf), start_col)
                if state == State.BLOCK_COMMENT:
                    self._err(ERR_UNTERM_BLOCK_COMMENT, "EOF", self.col)
                return self._make_token(TokenType.TOK_EOF, "EOF", self.col)

            if state == State.START:
                start_col = self.col
                if ch == ' ':
                    self._advance_state(GEN["SPACE"], "WS:space")
                    return self._emit_with_delim_check(TokenType.TOK_SPACE, " ", start_col)
                if ch == '\t':
                    self._advance_state(GEN["TAB"], "WS:tab")
                    return self._emit_with_delim_check(TokenType.TOK_TAB, "\t", start_col)
                if ch == '\n':
                    self._advance_state(GEN["NEWLINE"], "WS:newline")
                    return self._emit_with_delim_check(TokenType.TOK_NEWLINE, "\n", start_col)

                if self._is_alpha_id(ch):
                    first = self._advance_state(GEN.get("ID_HEAD", GEN["START"]), "IDKW:first")
                    if 'A' <= first <= 'Z':
                        buf=[first]
                        while self._is_id_continue(self._peek()):
                            if len(buf) >= CFG.IDENT_MAX_LEN:
                                self._err(ERR_IDENT_TOO_LONG, self._peek(), self.col)
                                while self._is_id_continue(self._peek()):
                                    self._advance_state(GEN.get("ID_CONT", GEN["START"]), "ID:overflow")
                                if CFG.EMIT_TOKEN_ON_LENGTH_ERROR:
                                    return self._emit_with_delim_check(TokenType.IDENTIFIER, "".join(buf), start_col)
                                else:
                                    self._trace_buf = []
                                    return self.get_next_token()
                            buf.append(self._advance_state(GEN.get("ID_CONT", GEN["START"]), "ID:cont"))
                        return self._emit_with_delim_check(TokenType.IDENTIFIER, "".join(buf), start_col)

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

                    buf=[first]
                    while self._is_id_continue(self._peek()):
                        if len(buf) >= CFG.IDENT_MAX_LEN:
                            self._err(ERR_IDENT_TOO_LONG, self._peek(), self.col)
                            while self._is_id_continue(self._peek()):
                                self._advance_state(GEN.get("ID_CONT", GEN["START"]), "ID:overflow")
                            if CFG.EMIT_TOKEN_ON_LENGTH_ERROR:
                                return self._emit_with_delim_check(TokenType.IDENTIFIER, "".join(buf), start_col)
                            else:
                                self._trace_buf = []
                                return self.get_next_token()
                        buf.append(self._advance_state(GEN.get("ID_CONT", GEN["START"]), "ID:cont"))
                    return self._emit_with_delim_check(TokenType.IDENTIFIER, "".join(buf), start_col)

                # numbers / operators
                if ch == '-':
                    if self._peek_next() and self._peek_next().isdigit():
                        state = State.INT_NEG; buf=['-']; self._advance_state(GEN["INT_NEG"], "NUM:-"); continue
                    # '-' operator branch (unchanged)
                    self._advance_state(GEN.get("OP_MINUS", GEN["START"]), "OP:-")
                    if self._peek() == '-':
                        self._advance_state(GEN.get("OP_DEC", GEN["START"]), "OP:--"); return self._make_token(TokenType.TOK_DECREMENT, "--", start_col)
                    if self._peek() == '=':
                        self._advance_state(GEN.get("OP_SUB_EQ", GEN["START"]), "OP:-="); return self._make_token(TokenType.TOK_SUB_ASSIGN, "-=", start_col)
                    return self._make_token(TokenType.TOK_MINUS, "-", start_col)

                if ch.isdigit():
                    state = State.INT
                    buf = [ self._advance_state(GEN["INT"], "NUM:int") ]
                    continue

                if ch == '.':
                    self._advance_state(GEN.get("SYM_DOT", GEN["START"]), "SYM:."); return self._make_token(TokenType.TOK_PERIOD, ".", start_col)

                if ch == '"':
                    state = State.STRING; buf=[]; self._advance_state(GEN.get("STR_OPEN", GEN["START"]), "STR:open"); continue
                if ch == "'":
                    state = State.CHAR; buf=[]; self._advance_state(GEN.get("CHR_OPEN", GEN["START"]), "CHR:open"); continue

                if ch == '/':
                    state = State.SLASH; self._advance_state(GEN["SLASH"], "OP:/"); continue

                # (operators and symbols below unchanged — emit with _make_token)
                if ch == '+':
                    self._advance_state(GEN.get("OP_PLUS", GEN["START"]), "OP:+")
                    if self._peek()=='+' : self._advance_state(GEN.get("OP_INC", GEN["START"]), "OP:++"); return self._make_token(TokenType.TOK_INCREMENT,"++",start_col)
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_ADD_EQ", GEN["START"]), "OP:+="); return self._make_token(TokenType.TOK_ADD_ASSIGN,"+=",start_col)
                    return self._make_token(TokenType.TOK_PLUS,"+",start_col)

                if ch == '*':
                    self._advance_state(GEN.get("OP_MUL", GEN["START"]), "OP:*")
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_MUL_EQ", GEN["START"]), "OP:*="); return self._make_token(TokenType.TOK_MUL_ASSIGN,"*=",start_col)
                    return self._make_token(TokenType.TOK_MULTIPLY,"*",start_col)

                if ch == '%':
                    self._advance_state(GEN.get("OP_MOD", GEN["START"]), "OP:%")
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_MOD_EQ", GEN["START"]), "OP:%="); return self._make_token(TokenType.TOK_MOD_ASSIGN,"%=",start_col)
                    return self._make_token(TokenType.TOK_MODULO,"%",start_col)

                if ch == '=':
                    self._advance_state(GEN.get("OP_EQ", GEN["START"]), "OP:=")
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_EQEQ", GEN["START"]), "OP:=="); return self._make_token(TokenType.TOK_EQUALS,"==",start_col)
                    return self._make_token(TokenType.TOK_ASSIGN,"=",start_col)

                if ch == '!':
                    self._advance_state(GEN.get("OP_NOT", GEN["START"]), "OP:!")
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_NEQ", GEN["START"]), "OP:!="); return self._make_token(TokenType.TOK_NOT_EQUAL,"!=",start_col)
                    return self._make_token(TokenType.TOK_NOT,"!",start_col)

                if ch == '<':
                    self._advance_state(GEN.get("OP_LT", GEN["START"]), "OP:<")
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_LTE", GEN["START"]), "OP:<="); return self._make_token(TokenType.TOK_LT_EQUAL,"<=",start_col)
                    return self._make_token(TokenType.TOK_LESS_THAN,"<",start_col)

                if ch == '>':
                    self._advance_state(GEN.get("OP_GT", GEN["START"]), "OP:>")
                    if self._peek()=='=' : self._advance_state(GEN.get("OP_GTE", GEN["START"]), "OP:>="); return self._make_token(TokenType.TOK_GT_EQUAL,">=",start_col)
                    return self._make_token(TokenType.TOK_GREATER_THAN,">",start_col)

                if ch == '&':
                    self._advance_state(GEN.get("OP_AMP", GEN["START"]), "OP:&")
                    if self._peek()=='&':
                        self._advance_state(GEN.get("OP_AND", GEN["START"]), "OP:&&"); return self._make_token(TokenType.TOK_AND,"&&",start_col)
                    self._err(ERR_SINGLE_AND, '&', start_col); self._trace_buf=[]; return self.get_next_token()

                if ch == '|':
                    self._advance_state(GEN.get("OP_BAR", GEN["START"]), "OP:|")
                    if self._peek()=='|':
                        self._advance_state(GEN.get("OP_OR", GEN["START"]), "OP:||"); return self._make_token(TokenType.TOK_OR,"||",start_col)
                    self._err(ERR_SINGLE_OR, '|', start_col); self._trace_buf=[]; return self.get_next_token()

                if ch == '(':
                    self._advance_state(GEN.get("SYM_LP", GEN["START"]), "SYM:("); return self._make_token(TokenType.TOK_OP_PARENTHESES,"(",start_col)
                if ch == ')':
                    self._advance_state(GEN.get("SYM_RP", GEN["START"]), "SYM:)"); return self._make_token(TokenType.TOK_CL_PARENTHESES,")",start_col)
                if ch == '{':
                    self._advance_state(GEN.get("SYM_LB", GEN["START"]), "SYM:{"); return self._make_token(TokenType.TOK_OP_BRACE,"{",start_col)
                if ch == '}':
                    self._advance_state(GEN.get("SYM_RB", GEN["START"]), "SYM:}"); return self._make_token(TokenType.TOK_CL_BRACE,"}",start_col)
                if ch == '[':
                    self._advance_state(GEN.get("SYM_LS", GEN["START"]), "SYM:["); return self._make_token(TokenType.TOK_OP_BRACKET,"[",start_col)
                if ch == ']':
                    self._advance_state(GEN.get("SYM_RS", GEN["START"]), "SYM:]"); return self._make_token(TokenType.TOK_CL_BRACKET,"]",start_col)
                if ch == ';':
                    self._advance_state(GEN.get("SYM_SEMI", GEN["START"]), "SYM:;"); return self._make_token(TokenType.TOK_SEMICOLON,";",start_col)
                if ch == ':':
                    self._advance_state(GEN.get("SYM_COLON", GEN["START"]), "SYM::"); return self._make_token(TokenType.TOK_COLON,":",start_col)
                if ch == ',':
                    self._advance_state(GEN.get("SYM_COMMA", GEN["START"]), "SYM:,"); return self._make_token(TokenType.TOK_COMMA,",",start_col)

                bad = self._advance_state(GEN["START"], "ERR:unknown")
                self._err(ERR_UNKNOWN_CHAR, bad, start_col); self._trace_buf=[]; return self.get_next_token()

            # ----- numbers -----
            if state == State.INT:
                if ch.isdigit():
                    digits_so_far = sum(1 for d in buf if d.isdigit())
                    if digits_so_far >= CFG.INT_MAX_DIGITS:
                        self._err(ERR_INT_TOO_LONG, ch, self.col)
                        while self._peek() and self._peek().isdigit():
                            self._advance_state(GEN["INT"], "NUM:int_overflow")
                        self._trace_buf=[]
                        if CFG.EMIT_TOKEN_ON_LENGTH_ERROR:
                            return self._emit_with_delim_check(TokenType.NUMBER, "".join(buf), start_col)
                        else:
                            state = State.START; buf.clear(); continue
                    buf.append(self._advance_state(GEN["INT"], "NUM:int")); continue
                if ch == '.':
                    if self._peek_next() and self._peek_next().isdigit():
                        buf.append(self._advance_state(GEN["INT"], "NUM:dot")); state = State.FLOAT_FRAC; continue
                    return self._emit_with_delim_check(TokenType.NUMBER, "".join(buf), start_col)

                if self._is_alpha_id(ch):
                    self._err(ERR_IDENT_STARTS_WITH_DIGIT, ch, self.col)
                    while self._is_id_continue(self._peek()):
                        self._advance_state(GEN["INT"], "NUM:bad_tail")
                    state = State.START; buf.clear(); self._trace_buf=[]; return self.get_next_token()

                return self._emit_with_delim_check(TokenType.NUMBER, "".join(buf), start_col)

            if state == State.INT_NEG:
                if ch and ch.isdigit():
                    buf.append(self._advance_state(GEN["INT_NEG"], "NUM:-digit")); state = State.INT; continue
                if self._is_alpha_id(ch):
                    self._err(ERR_IDENT_STARTS_WITH_DIGIT, ch, self.col)
                    while self._is_id_continue(self._peek()):
                        self._advance_state(GEN["INT_NEG"], "NUM:bad_tail")
                    state = State.START; buf.clear(); self._trace_buf=[]; return self.get_next_token()
                self._err(ERR_INVALID_NEGATIVE, ch, start_col); state = State.START; self._trace_buf=[]; return self.get_next_token()

            if state == State.FLOAT_FRAC:
                if ch.isdigit():
                    # fractional digit cap
                    frac_len = 0
                    for c in reversed(buf):
                        if c.isdigit(): frac_len += 1
                        elif c == '.': break
                    if frac_len >= CFG.FLOAT_FRAC_MAX_DIGITS:
                        self._err(ERR_FLOAT_FRAC_TOO_LONG, ch, self.col)
                        while self._peek() and self._peek().isdigit():
                            self._advance_state(GEN["FLOAT_FRAC"], "NUM:frac_overflow")
                        self._trace_buf=[]
                        if CFG.EMIT_TOKEN_ON_LENGTH_ERROR:
                            return self._emit_with_delim_check(TokenType.GLASS_NUMBER, "".join(buf), start_col)
                        else:
                            state = State.START; buf.clear(); continue
                    buf.append(self._advance_state(GEN["FLOAT_FRAC"], "NUM:frac")); continue

                if self._is_alpha_id(ch):
                    self._err(ERR_IDENT_STARTS_WITH_DIGIT, ch, self.col)
                    while self._is_id_continue(self._peek()):
                        self._advance_state(GEN["FLOAT_FRAC"], "NUM:bad_tail")
                    state = State.START; buf.clear(); self._trace_buf=[]; return self.get_next_token()

                if ch == '.':
                    self._err(ERR_FLOAT_MULTIPLE_DOTS, ch, self.col)
                    self._advance_state(GEN["FLOAT_FRAC"], "NUM:second_dot")
                    return self._emit_with_delim_check(TokenType.GLASS_NUMBER, "".join(buf), start_col)

                # check integer part length (digits before dot)
                int_part = 0
                for c in buf:
                    if c == '.': break
                    if c.isdigit(): int_part += 1
                if int_part > CFG.FLOAT_INT_MAX_DIGITS:
                    self._err(ERR_FLOAT_INT_TOO_LONG, None, self.col)

                return self._emit_with_delim_check(TokenType.GLASS_NUMBER, "".join(buf), start_col)

            # ----- strings & chars -----
            if state == State.STRING:
                if ch == '"':
                    self._advance_state(GEN.get("STR_CLOSE", GEN["START"]), "STR:close")
                    lex = '"' + "".join(buf) + '"'
                    return self._emit_with_delim_check(TokenType.TOK_WALL_LITERAL, lex, start_col, value="".join(buf))
                if ch == '\\':
                    self._advance_state(GEN.get("STR_ESC", GEN["START"]), "STR:esc"); state = State.STRING_ESC; continue
                buf.append(self._advance_state(GEN.get("STR_CH", GEN["START"]), "STR:ch")); continue

            if state == State.STRING_ESC:
                esc = self._advance_state(GEN.get("STR_ESC_CH", GEN["START"]), "STR:esc_ch")
                mapping = {'n':'\n','t':'\t','\\':'\\',"'" :"'",'"':'"','0':'\0'}
                if esc in mapping: buf.append(mapping[esc])
                else: self._err(ERR_STRING_BAD_ESCAPE, esc, self.col-1); buf.append(esc)
                state = State.STRING; continue

            if state == State.CHAR:
                if ch is None or ch == '\n':
                    self._err(ERR_CHAR_UNTERMINATED, ch, start_col); state = State.START; self._trace_buf=[]; continue
                if ch == "'":
                    self._err(ERR_CHAR_EMPTY, ch, start_col)
                    self._advance_state(GEN.get("CHR_CLOSE", GEN["START"]), "CHR:empty_close"); state = State.START; self._trace_buf=[]; continue
                if ch == '\\':
                    self._advance_state(GEN.get("CHR_ESC", GEN["START"]), "CHR:esc"); state = State.CHAR_ESC; continue
                buf.append(self._advance_state(GEN.get("CHR_CH", GEN["START"]), "CHR:ch"))
                if self._peek() == "'":
                    self._advance_state(GEN.get("CHR_CLOSE", GEN["START"]), "CHR:close")
                    if len(buf) != 1:
                        self._err(ERR_CHAR_EXPECT_QUOTE, "'", self.col-1); state = State.START; buf.clear(); self._trace_buf=[]; continue
                    lex = "'" + "".join(buf) + "'"
                    return self._emit_with_delim_check(TokenType.TOK_BRICK_LITERAL, lex, start_col, value=buf[0])
                else:
                    self._err(ERR_CHAR_EXPECT_QUOTE, self._peek(), self.col); state = State.START; buf.clear(); self._trace_buf=[]; continue

            if state == State.CHAR_ESC:
                esc = self._advance_state(GEN.get("CHR_ESC_CH", GEN["START"]), "CHR:esc_ch")
                mapping = {'n':'\n','t':'\t','\\':'\\',"'" :"'",'"':'"','0':'\0'}
                if esc in mapping: buf.append(mapping[esc])
                else: self._err(ERR_CHAR_BAD_ESCAPE, esc, self.col-1); buf.append(esc)
                if self._peek() == "'":
                    self._advance_state(GEN.get("CHR_CLOSE", GEN["START"]), "CHR:close")
                    if len(buf) != 1:
                        self._err(ERR_CHAR_EXPECT_QUOTE_AFTER_ESCAPE, "'", self.col-1); state = State.START; buf.clear(); self._trace_buf=[]; continue
                    lex = "'" + "".join(buf) + "'"
                    return self._emit_with_delim_check(TokenType.TOK_BRICK_LITERAL, lex, start_col, value=buf[0])
                else:
                    self._err(ERR_CHAR_EXPECT_QUOTE_AFTER_ESCAPE, self._peek(), self.col); state = State.START; buf.clear(); self._trace_buf=[]; continue

            # ----- comments / slash -----
            if state == State.SLASH:
                if ch == '/':
                    self._advance_state(GEN["LINE_COMMENT"], "CMT://"); state = State.LINE_COMMENT; continue
                if ch == '*':
                    self._advance_state(GEN["BLOCK_COMMENT"], "CMT:/*"); state = State.BLOCK_COMMENT; continue
                if ch == '=':
                    self._advance_state(GEN.get("OP_DIV_EQ", GEN["START"]), "OP:/="); return self._make_token(TokenType.TOK_DIV_ASSIGN, "/=", start_col)
                return self._make_token(TokenType.TOK_DIVIDE, "/", start_col)

            if state == State.LINE_COMMENT:
                if ch == '\n':
                    state = State.START; continue
                self._advance_state(GEN["LINE_COMMENT"], "CMT:line"); continue

            if state == State.BLOCK_COMMENT:
                if ch == '*':
                    self._advance_state(GEN["BLOCK_COMMENT"], "CMT:*"); state = State.BLOCK_COMMENT_STAR; continue
                self._advance_state(GEN["BLOCK_COMMENT"], "CMT:blk"); continue

            if state == State.BLOCK_COMMENT_STAR:
                if ch == '/':
                    self._advance_state(GEN["BLOCK_COMMENT"], "CMT:*/"); state = State.START; continue
                else:
                    state = State.BLOCK_COMMENT; continue

    def tokenize_all(self):
        """Return a full list of tokens until TOK_EOF."""
        out = []
        while True:
            t = self.get_next_token()
            out.append(t)
            # TokenType may be Enum; compare by value or name
            if t.type == TokenType.TOK_EOF or getattr(t.type, "name", None) == "TOK_EOF":
                break
        return out

    def __iter__(self):
        """Allow: for t in Lexer(src): ..."""
        for t in self.tokenize_all():
            yield t
