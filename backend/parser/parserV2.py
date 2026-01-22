from __future__ import annotations
from typing import List, Dict, Any

from parser.predict_set import PREDICT_SET

class Parser:
    IGNORE_TYPES = ("space", "tab", "newline", "Single-Line Comment", "Multi-Line Comment")

    def __init__(self, tokens):
        self.tokens = [t for t in (tokens or []) if getattr(t, "tokenType", None) not in self.IGNORE_TYPES]

        self.index = 0
        self.stop = False
        self.errors: List[Dict[str, Any]] = []

        self.current_type = "EOF"
        self.current_lexeme = "$"
        self.current_line = 1
        self.current_col = 1

        self._update_current()

    # ---------------- token helpers ----------------
    # nomralizes token id1, id2 ... to id
    def _norm_type(self, token_type: str) -> str:
        if isinstance(token_type, str) and token_type.startswith("id"):
            return "id"
        return token_type

    def _update_current(self):
        if self.index >= len(self.tokens):
            self.current_type = "EOF"
            self.current_lexeme = "$"
            return

        tok = self.tokens[self.index]
        self.current_type = self._norm_type(tok.tokenType)
        self.current_lexeme = tok.lexeme
        self.current_line = tok.line
        self.current_col = tok.column

    # basically advance
    def _consume(self):
        if self.stop:
            return
        self.index += 1
        self._update_current()

    # Checks next token
    def _peek_type(self, offset: int = 1) -> str:
        pos = self.index + offset
        if pos >= len(self.tokens):
            return "EOF"
        tok = self.tokens[pos]
        return self._norm_type(tok.tokenType)

    # Checks if token is in predict set for that production
    def in_predict(self, predict_list: list[str]) -> bool:
        return self.current_type in predict_list

    def match_token(self, expected_type: str):
        if self.stop:
            return
        if self.current_type == expected_type:
            self._consume()
            return
        self._add_error(f"Unexpected Character {self.current_lexeme!r}; expected {expected_type!r}")

    # ---------------- expected tokens for errors ----------------
    def _base_nt(self, key: str) -> str:
        # Turns "<main_type_3>" -> "<main_type>"
        # Leaves "<func_body>" unchanged
        if not key.endswith(">"):
            return key

        core = key[:-1]
        underscore_pos = core.rfind("_")
        if underscore_pos == -1:
            return key

        suffix = core[underscore_pos + 1 :]
        if suffix.isdigit():
            return core[:underscore_pos] + ">"

        return key

    def expected_for(self, nt: str) -> list[str]:
        base = self._base_nt(nt)
        expected: list[str] = []
        for k, lst in PREDICT_SET.items():
            if self._base_nt(k) == base:
                for t in lst:
                    if t not in expected:
                        expected.append(t)
        return expected


    def syntax_error(self, nt: str):
        exp = self.expected_for(nt)
        self._add_error(f"Unexpected Character {self.current_lexeme!r}; Expected one of {exp}")

    def _add_error(self, msg: str):
        self.errors.append({
            "message": msg,
            "line": self.current_line,
            "col": self.current_col,
            "start_line": self.current_line,
            "start_col": self.current_col,
            "end_line": self.current_line,
            "end_col": self.current_col + max(1, len(str(self.current_lexeme))),
        })
        self.stop = True

    # ---------------- entry ----------------
    def parse(self, _predict_set=None):
        self.parse_program()

        if not self.stop and self.current_type != "EOF":
            self._add_error(f"Extra token after program end: {self.current_lexeme!r}")

        return self.errors

    def parse_program(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<program>']):  # prod 1
            self.parse_global()
            if self.stop: return
            self.parse_function()
            if self.stop: return
            self.parse_main_type()
            if self.stop: return
            self.match_token('blueprint')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<program>')

    def parse_global(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global>']):  # prod 2
            self.match_token('roof')
            if self.stop: return
            self.parse_global_dec()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_global()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_1>']):  # prod 3
            return
        self.syntax_error('<global>')

    def parse_global_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_dec>']):  # prod 4
            self.parse_global_var()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_dec_1>']):  # prod 5
            self.parse_structure()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_dec_2>']):  # prod 6
            self.parse_global_const()
            if self.stop: return
            return
        self.syntax_error('<global_dec>')

    def parse_global_var(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_var>']):  # prod 7
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_end()
            if self.stop: return
            return
        self.syntax_error('<global_var>')

    def parse_data_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<data_type>']):  # prod 8
            self.match_token('tile')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_1>']):  # prod 9
            self.match_token('glass')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_2>']):  # prod 10
            self.match_token('brick')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_3>']):  # prod 11
            self.match_token('wall')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_4>']):  # prod 12
            self.match_token('beam')
            if self.stop: return
            return
        self.syntax_error('<data_type>')

    def parse_global_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_end>']):  # prod 13
            self.parse_global_init()
            if self.stop: return
            self.parse_global_mult()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_end_1>']):  # prod 14
            self.parse_array_dec()
            if self.stop: return
            return
        self.syntax_error('<global_end>')

    def parse_global_init(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_init>']):  # prod 15
            self.match_token('=')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_init_1>']):  # prod 16
            return
        self.syntax_error('<global_init>')

    def parse_global_mult(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_mult>']):  # prod 17
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_init()
            if self.stop: return
            self.parse_global_mult()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_mult_1>']):  # prod 18
            return
        self.syntax_error('<global_mult>')

    def parse_value(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value>']):  # prod 19
            self.match_token('tile_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_1>']):  # prod 20
            self.match_token('glass_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_2>']):  # prod 21
            self.match_token('brick_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_3>']):  # prod 22
            self.match_token('wall_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_4>']):  # prod 23
            self.match_token('solid')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_5>']):  # prod 24
            self.match_token('fragile')
            if self.stop: return
            return
        self.syntax_error('<value>')

    def parse_array_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_dec>']):  # prod 25
            self.match_token('[')
            if self.stop: return
            self.parse_arr_size()
            if self.stop: return
            return
        self.syntax_error('<array_dec>')

    def parse_arr_size(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<arr_size>']):  # prod 26
            self.match_token(']')
            if self.stop: return
            self.parse_one_d_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_size_1>']):  # prod 27
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_one_d_end2()
            if self.stop: return
            return
        self.syntax_error('<arr_size>')

    def parse_one_d_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<one_d_end>']):  # prod 28
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<one_d_end_1>']):  # prod 29
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<one_d_end>')

    def parse_one_d_end2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<one_d_end2>']):  # prod 30
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_two_d_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<one_d_end2_1>']):  # prod 31
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<one_d_end2_2>']):  # prod 32
            return
        self.syntax_error('<one_d_end2>')

    def parse_two_d_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<two_d_end>']):  # prod 33
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<two_d_end_1>']):  # prod 34
            return
        self.syntax_error('<two_d_end>')

    def parse_elements(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<elements>']):  # prod 35
            self.parse_value()
            if self.stop: return
            self.parse_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<elements>')

    def parse_mult_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_elem>']):  # prod 36
            self.match_token(',')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            self.parse_mult_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_elem_1>']):  # prod 37
            return
        self.syntax_error('<mult_elem>')

    def parse_mult_elem2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_elem2>']):  # prod 38
            self.match_token(',')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_elem2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_elem2_1>']):  # prod 39
            return
        self.syntax_error('<mult_elem2>')

    def parse_structure(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<structure>']):  # prod 40
            self.match_token('house')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_struct_type()
            if self.stop: return
            return
        self.syntax_error('<structure>')

    def parse_struct_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_type>']):  # prod 41
            self.parse_struct_dec()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_type_1>']):  # prod 42
            self.parse_struct_var()
            if self.stop: return
            return
        self.syntax_error('<struct_type>')

    def parse_struct_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_dec>']):  # prod 43
            self.match_token('{')
            if self.stop: return
            self.parse_struct_members()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_struct_id_end()
            if self.stop: return
            return
        self.syntax_error('<struct_dec>')

    def parse_struct_members(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_members>']):  # prod 44
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_array()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_mult_members()
            if self.stop: return
            return
        self.syntax_error('<struct_members>')

    def parse_data_type_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<data_type_dec>']):  # prod 45
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            return
        self.syntax_error('<data_type_dec>')

    def parse_array(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array>']):  # prod 46
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_array2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_1>']):  # prod 47
            return
        self.syntax_error('<array>')

    def parse_array2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array2>']):  # prod 48
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array2_1>']):  # prod 49
            return
        self.syntax_error('<array2>')

    def parse_mult_members(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_members>']):  # prod 50
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_array()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_mult_members()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_members_1>']):  # prod 51
            return
        self.syntax_error('<mult_members>')

    def parse_struct_id_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_id_end>']):  # prod 52
            self.match_token('id')
            if self.stop: return
            self.parse_struct_init()
            if self.stop: return
            self.parse_mult_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_id_end_1>']):  # prod 53
            return
        self.syntax_error('<struct_id_end>')

    def parse_struct_init(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_init>']):  # prod 54
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_init_1>']):  # prod 55
            return
        self.syntax_error('<struct_init>')

    def parse_struct_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_elem>']):  # prod 56
            self.parse_value()
            if self.stop: return
            self.parse_mult_struct_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_elem_1>']):  # prod 57
            self.match_token('{')
            if self.stop: return
            self.parse_struct_arr_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_struct_elem()
            if self.stop: return
            return
        self.syntax_error('<struct_elem>')

    def parse_struct_arr_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_arr_elem>']):  # prod 58
            self.parse_elements()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_arr_elem_1>']):  # prod 59
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_elem2()
            if self.stop: return
            return
        self.syntax_error('<struct_arr_elem>')

    def parse_mult_struct_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_struct_elem>']):  # prod 60
            self.match_token(',')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_struct_elem_1>']):  # prod 61
            return
        self.syntax_error('<mult_struct_elem>')

    def parse_mult_struct_id(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_struct_id>']):  # prod 62
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_struct_init()
            if self.stop: return
            self.parse_mult_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_struct_id_1>']):  # prod 63
            return
        self.syntax_error('<mult_struct_id>')

    def parse_struct_var(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_var>']):  # prod 64
            self.match_token('id')
            if self.stop: return
            self.parse_struct_init()
            if self.stop: return
            self.parse_mult_struct_id()
            if self.stop: return
            return
        self.syntax_error('<struct_var>')

    def parse_global_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const>']):  # prod 65
            self.match_token('cement')
            if self.stop: return
            self.parse_global_const_type()
            if self.stop: return
            return
        self.syntax_error('<global_const>')

    def parse_global_const_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_type>']):  # prod 66
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_const_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_type_1>']):  # prod 67
            self.match_token('house')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_global_const_struct()
            if self.stop: return
            return
        self.syntax_error('<global_const_type>')

    def parse_global_const_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_end>']):  # prod 68
            self.match_token('=')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            self.parse_global_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_end_1>']):  # prod 69
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_global_const_end2()
            if self.stop: return
            return
        self.syntax_error('<global_const_end>')

    def parse_global_const_end2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_end2>']):  # prod 70
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_end2_1>']):  # prod 71
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<global_const_end2>')

    def parse_global_mult_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_mult_const>']):  # prod 72
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            self.parse_global_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_mult_const_1>']):  # prod 73
            return
        self.syntax_error('<global_mult_const>')

    def parse_global_const_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_struct>']):  # prod 74
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_global_const_struct()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_struct_1>']):  # prod 75
            return
        self.syntax_error('<global_const_struct>')

    def parse_function(self):
        if self.stop: return

        # Disambiguation (no rollback):
        # If a type keyword is followed by an identifier, it's a function declaration.
        # Otherwise, treat <function> as λ and let <main_type> handle it.
        if self.current_type in ("tile", "glass", "brick", "wall", "beam", "field"):
            if self._peek_type(1) == "id":
                self.parse_return_type()
                if self.stop: return
                self.match_token('id')
                if self.stop: return
                self.match_token('(')
                if self.stop: return
                self.parse_param_list()
                if self.stop: return
                self.match_token(')')
                if self.stop: return
                self.match_token('{')
                if self.stop: return
                self.parse_func_body()
                if self.stop: return
                self.match_token('}')
                if self.stop: return
                return
            return  # λ

        if self.current_type == "blueprint":
            return  # λ

        self.syntax_error('<function>')

    def parse_return_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<return_type>']):  # prod 78
            self.parse_data_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<return_type_1>']):  # prod 79
            self.match_token('field')
            if self.stop: return
            return
        self.syntax_error('<return_type>')

    def parse_param_list(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<param_list>']):  # prod 80
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_mult_param()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<param_list_1>']):  # prod 81
            return
        self.syntax_error('<param_list>')

    def parse_mult_param(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_param>']):  # prod 82
            self.match_token(',')
            if self.stop: return
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_mult_param()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_param_1>']):  # prod 83
            return
        self.syntax_error('<mult_param>')

    def parse_func_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_body>']):  # prod 84
            self.parse_local()
            if self.stop: return
            self.parse_func_body2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_body_1>']):  # prod 85
            self.parse_statement()
            if self.stop: return
            self.parse_func_body2()
            if self.stop: return
            return
        self.syntax_error('<func_body>')

    def parse_func_body2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_body2>']):  # prod 86
            self.parse_func_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_body2_1>']):  # prod 87
            return
        self.syntax_error('<func_body2>')

    def parse_local(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<local>']):  # prod 88
            self.parse_declaration()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<local>')

    def parse_declaration(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<declaration>']):  # prod 89
            self.parse_variable()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<declaration_1>']):  # prod 90
            self.parse_structure()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<declaration_2>']):  # prod 91
            self.parse_constant()
            if self.stop: return
            return
        self.syntax_error('<declaration>')

    def parse_variable(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<variable>']):  # prod 92
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_var_end()
            if self.stop: return
            return
        self.syntax_error('<variable>')

    def parse_var_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<var_end>']):  # prod 93
            self.parse_initializer()
            if self.stop: return
            self.parse_mult_var()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<var_end_1>']):  # prod 94
            self.parse_array_dec()
            if self.stop: return
            return
        self.syntax_error('<var_end>')

    def parse_initializer(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<initializer>']):  # prod 95
            self.match_token('=')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<initializer_1>']):  # prod 96
            return
        self.syntax_error('<initializer>')

    def parse_mult_var(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_var>']):  # prod 97
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            self.parse_mult_var()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_var_1>']):  # prod 98
            return
        self.syntax_error('<mult_var>')

    def parse_constant(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<constant>']):  # prod 99
            self.match_token('cement')
            if self.stop: return
            self.parse_const_type()
            if self.stop: return
            return
        self.syntax_error('<constant>')

    def parse_const_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_type>']):  # prod 100
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_const_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_type_1>']):  # prod 101
            self.match_token('house')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_const_struct()
            if self.stop: return
            return
        self.syntax_error('<const_type>')

    def parse_const_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_end>']):  # prod 102
            self.match_token('=')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.parse_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_end_1>']):  # prod 103
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_const_end2()
            if self.stop: return
            return
        self.syntax_error('<const_end>')

    def parse_const_end2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_end2>']):  # prod 104
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_end2_1>']):  # prod 105
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<const_end2>')

    def parse_mult_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const>']):  # prod 106
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.parse_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_const_1>']):  # prod 107
            return
        self.syntax_error('<mult_const>')

    def parse_mult_const_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const_struct>']):  # prod 108
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_mult_const_struct()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_const_struct_1>']):  # prod 109
            return
        self.syntax_error('<mult_const_struct>')

    def parse_init_value(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<init_value>']):  # prod 110
            self.parse_value_exp()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<init_value_1>']):  # prod 111
            self.parse_prefix_op()
            if self.stop: return
            self.parse_id_val()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        self.syntax_error('<init_value>')

    def parse_value_exp(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value_exp>']):  # prod 112
            self.parse_value_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_exp_1>']):  # prod 113
            self.parse_group()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_exp_2>']):  # prod 114
            self.match_token('-')
            if self.stop: return
            self.parse_negative_type()
            if self.stop: return
            return
        self.syntax_error('<value_exp>')

    def parse_value_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value_type>']):  # prod 115
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_type_1>']):  # prod 116
            self.parse_value()
            if self.stop: return
            return
        self.syntax_error('<value_type>')

    def parse_id_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type>']):  # prod 117
            self.parse_id_type2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type_1>']):  # prod 118
            return
        self.syntax_error('<id_type>')

    def parse_id_type2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type2>']):  # prod 119
            self.parse_arr_struct()
            if self.stop: return
            self.parse_postfix_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type2_1>']):  # prod 120
            self.parse_func_call()
            if self.stop: return
            return
        self.syntax_error('<id_type2>')

    def parse_arr_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<arr_struct>']):  # prod 121
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_struct_1>']):  # prod 122
            self.parse_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_struct_2>']):  # prod 123
            return
        self.syntax_error('<arr_struct>')

    def parse_array_index(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index>']):  # prod 124
            self.match_token('[')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_array_index2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index_1>']):  # prod 125
            return
        self.syntax_error('<array_index>')

    def parse_array_index2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index2>']):  # prod 126
            self.match_token('[')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index2_1>']):  # prod 127
            return
        self.syntax_error('<array_index2>')

    def parse_struct_id(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_id>']):  # prod 128
            self.match_token('.')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_id_1>']):  # prod 129
            return
        self.syntax_error('<struct_id>')

    def parse_func_call(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_call>']):  # prod 130
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_call_1>']):  # prod 131
            return
        self.syntax_error('<func_call>')

    def parse_func_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_argu>']):  # prod 132
            self.parse_init_value()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_argu_1>']):  # prod 133
            return
        self.syntax_error('<func_argu>')

    def parse_func_mult_call(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_mult_call>']):  # prod 134
            self.match_token(',')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_mult_call_1>']):  # prod 135
            return
        self.syntax_error('<func_mult_call>')

    def parse_postfix_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<postfix_op>']):  # prod 136
            self.parse_unary_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<postfix_op_1>']):  # prod 137
            return
        self.syntax_error('<postfix_op>')

    def parse_unary_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<unary_op>']):  # prod 138
            self.match_token('++')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<unary_op_1>']):  # prod 139
            self.match_token('--')
            if self.stop: return
            return
        self.syntax_error('<unary_op>')

    def parse_group(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<group>']):  # prod 140
            self.match_token('(')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        self.syntax_error('<group>')

    def parse_negative_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<negative_type>']):  # prod 141
            self.parse_value_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<negative_type_1>']):  # prod 142
            self.parse_group()
            if self.stop: return
            return
        self.syntax_error('<negative_type>')

    def parse_exp_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<exp_op>']):  # prod 143
            self.parse_operator()
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<exp_op_1>']):  # prod 144
            return
        self.syntax_error('<exp_op>')

    def parse_prefix_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<prefix_op>']):  # prod 145
            self.match_token('!')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<prefix_op_1>']):  # prod 146
            self.parse_unary_op()
            if self.stop: return
            return
        self.syntax_error('<prefix_op>')

    def parse_id_val(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_val>']):  # prod 147
            self.match_token('id')
            if self.stop: return
            self.parse_id_type3()
            if self.stop: return
            return
        self.syntax_error('<id_val>')

    def parse_id_type3(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type3>']):  # prod 148
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type3_1>']):  # prod 149
            self.parse_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type3_2>']):  # prod 150
            return
        self.syntax_error('<id_type3>')

    def parse_operator(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<operator>']):  # prod 151
            self.match_token('+')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_1>']):  # prod 152
            self.match_token('-')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_2>']):  # prod 153
            self.match_token('*')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_3>']):  # prod 154
            self.match_token('/')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_4>']):  # prod 155
            self.match_token('%')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_5>']):  # prod 156
            self.match_token('<')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_6>']):  # prod 157
            self.match_token('<=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_7>']):  # prod 158
            self.match_token('>')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_8>']):  # prod 159
            self.match_token('>=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_9>']):  # prod 160
            self.match_token('==')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_10>']):  # prod 161
            self.match_token('!=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_11>']):  # prod 162
            self.match_token('&&')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_12>']):  # prod 163
            self.match_token('||')
            if self.stop: return
            return
        self.syntax_error('<operator>')

    def parse_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<statement>']):  # prod 164
            self.parse_io_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_1>']):  # prod 165
            self.parse_assign_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_2>']):  # prod 166
            self.parse_if_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_3>']):  # prod 167
            self.parse_switch_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_4>']):  # prod 168
            self.parse_for_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_5>']):  # prod 169
            self.parse_while_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_6>']):  # prod 170
            self.parse_dowhile_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_7>']):  # prod 171
            self.parse_break_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_8>']):  # prod 172
            self.parse_continue_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_9>']):  # prod 173
            self.parse_return_statement()
            if self.stop: return
            return
        self.syntax_error('<statement>')

    def parse_io_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<io_statement>']):  # prod 174
            self.match_token('write')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.match_token(',')
            if self.stop: return
            self.parse_write_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<io_statement_1>']):  # prod 175
            self.match_token('view')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_view_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<io_statement>')

    def parse_write_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<write_argu>']):  # prod 176
            self.match_token('&')
            if self.stop: return
            self.parse_id_val()
            if self.stop: return
            self.parse_mult_write_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<write_argu_1>']):  # prod 177
            self.parse_id_val()
            if self.stop: return
            self.parse_mult_write_argu()
            if self.stop: return
            return
        self.syntax_error('<write_argu>')

    def parse_mult_write_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_write_argu>']):  # prod 178
            self.match_token(',')
            if self.stop: return
            self.parse_write_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_write_argu_1>']):  # prod 179
            return
        self.syntax_error('<mult_write_argu>')

    def parse_view_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<view_argu>']):  # prod 180
            self.match_token(',')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.parse_mult_view_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<view_argu_1>']):  # prod 181
            return
        self.syntax_error('<view_argu>')

    def parse_mult_view_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_view_argu>']):  # prod 182
            self.parse_view_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_view_argu_1>']):  # prod 183
            return
        self.syntax_error('<mult_view_argu>')

    def parse_assign_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_statement>']):  # prod 184
            self.parse_unary_op()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_statement_1>']):  # prod 185
            self.match_token('id')
            if self.stop: return
            self.parse_id_type4()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<assign_statement>')

    def parse_id_type4(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type4>']):  # prod 186
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type4_1>']):  # prod 187
            self.parse_unary_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type4_2>']):  # prod 188
            self.parse_id_type3()
            if self.stop: return
            self.parse_assign_op()
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            return
        self.syntax_error('<id_type4>')

    def parse_assign_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_op>']):  # prod 189
            self.match_token('=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_1>']):  # prod 190
            self.match_token('+=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_2>']):  # prod 191
            self.match_token('-=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_3>']):  # prod 192
            self.match_token('*=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_4>']):  # prod 193
            self.match_token('/=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_5>']):  # prod 194
            self.match_token('%=')
            if self.stop: return
            return
        self.syntax_error('<assign_op>')

    def parse_if_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<if_statement>']):  # prod 195
            self.match_token('if')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_else_statement()
            if self.stop: return
            return
        self.syntax_error('<if_statement>')

    def parse_else_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<else_statement>']):  # prod 196
            self.match_token('else')
            if self.stop: return
            self.parse_else_statement2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<else_statement_1>']):  # prod 197
            return
        self.syntax_error('<else_statement>')

    def parse_else_statement2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<else_statement2>']):  # prod 198
            self.parse_if_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<else_statement2_1>']):  # prod 199
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<else_statement2>')

    def parse_switch_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<switch_statement>']):  # prod 200
            self.match_token('room')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_switch_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<switch_statement>')

    def parse_switch_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<switch_body>']):  # prod 201
            self.match_token('door')
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            self.parse_switch_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<switch_body_1>']):  # prod 202
            self.match_token('ground')
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            return
        self.syntax_error('<switch_body>')

    def parse_case_exp(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_exp>']):  # prod 203
            self.parse_case_type()
            if self.stop: return
            self.parse_case_op()
            if self.stop: return
            return
        self.syntax_error('<case_exp>')

    def parse_case_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_type>']):  # prod 204
            self.parse_case_val()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_type_1>']):  # prod 205
            self.parse_case_group()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_type_2>']):  # prod 206
            self.match_token('-')
            if self.stop: return
            self.parse_case_negative()
            if self.stop: return
            return
        self.syntax_error('<case_type>')

    def parse_case_val(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_val>']):  # prod 207
            self.match_token('tile_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_1>']):  # prod 208
            self.match_token('brick_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_2>']):  # prod 209
            self.match_token('solid')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_3>']):  # prod 210
            self.match_token('fragile')
            if self.stop: return
            return
        self.syntax_error('<case_val>')

    def parse_case_group(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_group>']):  # prod 211
            self.match_token('(')
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        self.syntax_error('<case_group>')

    def parse_case_negative(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_negative>']):  # prod 212
            self.parse_case_val()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_negative_1>']):  # prod 213
            self.parse_case_group()
            if self.stop: return
            return
        self.syntax_error('<case_negative>')

    def parse_case_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_op>']):  # prod 214
            self.parse_operator()
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_op_1>']):  # prod 215
            return
        self.syntax_error('<case_op>')

    def parse_case_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_body>']):  # prod 216
            self.parse_statement()
            if self.stop: return
            self.parse_mult_smt()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_body_1>']):  # prod 217
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_body_2>']):  # prod 218
            return
        self.syntax_error('<case_body>')

    def parse_mult_smt(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_smt>']):  # prod 219
            self.parse_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_smt_1>']):  # prod 220
            return
        self.syntax_error('<mult_smt>')

    def parse_for_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<for_statement>']):  # prod 221
            self.match_token('for')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_for_dec()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_for_exp()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_for_exp()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<for_statement>')

    def parse_for_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<for_dec>']):  # prod 222
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<for_dec_1>']):  # prod 223
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<for_dec_2>']):  # prod 224
            return
        self.syntax_error('<for_dec>')

    def parse_for_exp(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<for_exp>']):  # prod 225
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<for_exp_1>']):  # prod 226
            return
        self.syntax_error('<for_exp>')

    def parse_while_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<while_statement>']):  # prod 227
            self.match_token('while')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<while_statement>')

    def parse_dowhile_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<dowhile_statement>']):  # prod 228
            self.match_token('do')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.match_token('while')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<dowhile_statement>')

    def parse_break_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<break_statement>']):  # prod 229
            self.match_token('crack')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<break_statement>')

    def parse_continue_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<continue_statement>']):  # prod 230
            self.match_token('mend')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<continue_statement>')

    def parse_return_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<return_statement>']):  # prod 231
            self.match_token('home')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<return_statement>')

    def parse_main_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<main_type>']):  # prod 232
            self.match_token('tile')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<main_type_1>']):  # prod 233
            self.match_token('glass')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<main_type_2>']):  # prod 234
            self.match_token('brick')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<main_type_3>']):  # prod 235
            self.match_token('beam')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<main_type_4>']):  # prod 236
            self.match_token('field')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<main_type_5>']):  # prod 237
            return
        self.syntax_error('<main_type>')
