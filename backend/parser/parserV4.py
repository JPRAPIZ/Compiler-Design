from __future__ import annotations
from typing import List, Dict, Any


from parser.predict_setV5 import PREDICT_SET


class Parser:
    IGNORE_TYPES = ("space", "tab", "newline", "Single-Line Comment", "Multi-Line Comment")

    def __init__(self, tokens):
        self.tokens = [t for t in (tokens or []) if getattr(t, "tokenType", None) not in self.IGNORE_TYPES]

        self.index = 0
        self.stop = False
        self.errors: List[Dict[str, Any]] = []

        self.delim_stack: List[str] = []

        self.track_delims: int = 0

        self.expr_end_stack: List[set[str]] = []

        self.current_type = "EOF"
        self.current_lexeme = "$"
        self.current_line = 1
        self.current_col = 1

        self._update_current()

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

    def _consume(self):
        if self.stop:
            return
        self.index += 1
        self._update_current()

    def in_predict(self, predict_list: list[str]) -> bool:
        return self.current_type in predict_list
    def match_token(self, expected_type: str):
        if self.stop:
            return
        if self.current_type == expected_type:

            if self.track_delims > 0:
                self._push_delim_if_needed(expected_type)
                self._pop_delim_if_needed(expected_type)
            self._consume()
            return
        self._add_error(f"Unexpected Character {self.current_lexeme!r}; expected {expected_type!r}")

    def _push_delim_if_needed(self, token_type: str):
        if token_type == '(':
            self.delim_stack.append(')')
        elif token_type == '[':
            self.delim_stack.append(']')
        elif token_type == '{':
            self.delim_stack.append('}')

    def _pop_delim_if_needed(self, token_type: str):
        if not self.delim_stack:
            return
        if token_type in (')', ']', '}'):
            if self.delim_stack[-1] == token_type:
                self.delim_stack.pop()

    def _filter_expected_by_delims(self, expected: list[str]) -> list[str]:
        end_tokens = {')', ']', '}', ';', ',', ':'}

        if self.delim_stack:
            top_closer = self.delim_stack[-1]
            filtered: list[str] = []
            for t in expected:
                if t in end_tokens and t != top_closer:
                    continue
                filtered.append(t)
            return filtered

        if self.expr_end_stack:
            allowed = self.expr_end_stack[-1]
            filtered: list[str] = []
            for t in expected:
                if t in end_tokens and t not in allowed:
                    continue
                filtered.append(t)
            return filtered

        return expected
    
    def _push_expr_end_tokens(self, end_tokens: set[str]) -> None:
        self.expr_end_stack.append(set(end_tokens))

    def _pop_expr_end_tokens(self) -> None:
        if self.expr_end_stack:
            self.expr_end_stack.pop()

# ---------------- expected tokens for errors ----------------
    def _base_nt(self, key: str) -> str:
        # Turns "<main_type_3>" -> "<main_type>"
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
        exp = self._filter_expected_by_delims(exp)
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
            self.parse_program_body()
            if self.stop: return
            return
        self.syntax_error('<program>')

    def parse_program_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<program_body>']):  # prod 2
            self.match_token('wall')
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
            self.parse_program_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<program_body_1>']):  # prod 3
            self.parse_return_type()
            if self.stop: return
            self.parse_program_body2()
            if self.stop: return
            return
        self.syntax_error('<program_body>')

    def parse_program_body2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<program_body2>']):  # prod 4
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
            self.parse_program_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<program_body2_1>']):  # prod 5
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
        self.syntax_error('<program_body2>')

    def parse_global(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global>']):  # prod 6
            self.match_token('roof')
            if self.stop: return
            self.parse_global_dec()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_global()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_1>']):  # prod 7
            return
        self.syntax_error('<global>')

    def parse_global_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_dec>']):  # prod 8
            self.parse_global_var()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_dec_1>']):  # prod 9
            self.parse_structure()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_dec_2>']):  # prod 10
            self.parse_global_const()
            if self.stop: return
            return
        self.syntax_error('<global_dec>')

    def parse_global_var(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_var>']):  # prod 11
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_var_1>']):  # prod 12
            self.match_token('wall')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_wall_end()
            if self.stop: return
            return
        self.syntax_error('<global_var>')

    def parse_data_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<data_type>']):  # prod 13
            self.match_token('tile')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_1>']):  # prod 14
            self.match_token('glass')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_2>']):  # prod 15
            self.match_token('brick')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_3>']):  # prod 16
            self.match_token('beam')
            if self.stop: return
            return
        self.syntax_error('<data_type>')

    def parse_global_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_end>']):  # prod 17
            self.parse_global_init()
            if self.stop: return
            self.parse_global_mult()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_end_1>']):  # prod 18
            self.parse_array_dec()
            if self.stop: return
            return
        self.syntax_error('<global_end>')

    def parse_global_init(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_init>']):  # prod 19
            self.match_token('=')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_init_1>']):  # prod 20
            return
        self.syntax_error('<global_init>')

    def parse_global_mult(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_mult>']):  # prod 21
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_init()
            if self.stop: return
            self.parse_global_mult()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_mult_1>']):  # prod 22
            return
        self.syntax_error('<global_mult>')

    def parse_value(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value>']):  # prod 23
            self.match_token('tile_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_1>']):  # prod 24
            self.match_token('glass_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_2>']):  # prod 25
            self.match_token('brick_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_3>']):  # prod 26
            self.match_token('solid')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_4>']):  # prod 27
            self.match_token('fragile')
            if self.stop: return
            return
        self.syntax_error('<value>')

    def parse_array_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_dec>']):  # prod 28
            self.match_token('[')
            if self.stop: return
            self.parse_arr_size()
            if self.stop: return
            return
        self.syntax_error('<array_dec>')

    def parse_arr_size(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<arr_size>']):  # prod 29
            self.match_token(']')
            if self.stop: return
            self.parse_one_d_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_size_1>']):  # prod 30
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
        if self.in_predict(PREDICT_SET['<one_d_end>']):  # prod 31
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
        elif self.in_predict(PREDICT_SET['<one_d_end_1>']):  # prod 32
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
        if self.in_predict(PREDICT_SET['<one_d_end2>']):  # prod 33
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_two_d_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<one_d_end2_1>']):  # prod 34
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<one_d_end2_2>']):  # prod 35
            return
        self.syntax_error('<one_d_end2>')

    def parse_two_d_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<two_d_end>']):  # prod 36
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
        elif self.in_predict(PREDICT_SET['<two_d_end_1>']):  # prod 37
            return
        self.syntax_error('<two_d_end>')

    def parse_elements(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<elements>']):  # prod 38
            self.parse_value()
            if self.stop: return
            self.parse_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<elements>')

    def parse_mult_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_elem>']):  # prod 39
            self.match_token(',')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            self.parse_mult_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_elem_1>']):  # prod 40
            return
        self.syntax_error('<mult_elem>')

    def parse_mult_elem2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_elem2>']):  # prod 41
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
        elif self.in_predict(PREDICT_SET['<mult_elem2_1>']):  # prod 42
            return
        self.syntax_error('<mult_elem2>')

    def parse_global_wall_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_wall_end>']):  # prod 43
            self.parse_global_wall_init()
            if self.stop: return
            self.parse_global_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_wall_end_1>']):  # prod 44
            self.parse_wall_array()
            if self.stop: return
            return
        self.syntax_error('<global_wall_end>')

    def parse_global_wall_init(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_wall_init>']):  # prod 45
            self.match_token('=')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_wall_init_1>']):  # prod 46
            return
        self.syntax_error('<global_wall_init>')

    def parse_global_mult_wall(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_mult_wall>']):  # prod 47
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_wall_init()
            if self.stop: return
            self.parse_global_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_mult_wall_1>']):  # prod 48
            return
        self.syntax_error('<global_mult_wall>')

    def parse_wall_array(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_array>']):  # prod 49
            self.match_token('[')
            if self.stop: return
            self.parse_wall_size()
            if self.stop: return
            return
        self.syntax_error('<wall_array>')

    def parse_wall_size(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_size>']):  # prod 50
            self.match_token(']')
            if self.stop: return
            self.parse_wall_one_d_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_size_1>']):  # prod 51
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_wall_one_d_end2()
            if self.stop: return
            return
        self.syntax_error('<wall_size>')

    def parse_wall_one_d_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_one_d_end>']):  # prod 52
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
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_wall_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_one_d_end_1>']):  # prod 53
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<wall_one_d_end>')

    def parse_wall_one_d_end2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_one_d_end2>']):  # prod 54
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_wall_two_d_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_one_d_end2_1>']):  # prod 55
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_one_d_end2_2>']):  # prod 56
            return
        self.syntax_error('<wall_one_d_end2>')

    def parse_wall_two_d_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_two_d_end>']):  # prod 57
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_wall_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_two_d_end_1>']):  # prod 58
            return
        self.syntax_error('<wall_two_d_end>')

    def parse_wall_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_elem>']):  # prod 59
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<wall_elem>')

    def parse_wall_mult_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_mult_elem>']):  # prod 60
            self.match_token(',')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_mult_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_mult_elem_1>']):  # prod 61
            return
        self.syntax_error('<wall_mult_elem>')

    def parse_wall_mult_elem2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_mult_elem2>']):  # prod 62
            self.match_token(',')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_wall_mult_elem2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_mult_elem2_1>']):  # prod 63
            return
        self.syntax_error('<wall_mult_elem2>')

    def parse_structure(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<structure>']):  # prod 64
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
        if self.in_predict(PREDICT_SET['<struct_type>']):  # prod 65
            self.parse_struct_dec()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_type_1>']):  # prod 66
            self.parse_struct_var()
            if self.stop: return
            return
        self.syntax_error('<struct_type>')

    def parse_struct_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_dec>']):  # prod 67
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
        if self.in_predict(PREDICT_SET['<struct_members>']):  # prod 68
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
        if self.in_predict(PREDICT_SET['<data_type_dec>']):  # prod 69
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<data_type_dec_1>']):  # prod 70
            self.match_token('wall')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            return
        self.syntax_error('<data_type_dec>')

    def parse_array(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array>']):  # prod 71
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_array2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_1>']):  # prod 72
            return
        self.syntax_error('<array>')

    def parse_array2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array2>']):  # prod 73
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array2_1>']):  # prod 74
            return
        self.syntax_error('<array2>')

    def parse_mult_members(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_members>']):  # prod 75
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_array()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.parse_mult_members()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_members_1>']):  # prod 76
            return
        self.syntax_error('<mult_members>')

    def parse_struct_id_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_id_end>']):  # prod 77
            self.match_token('id')
            if self.stop: return
            self.parse_struct_init()
            if self.stop: return
            self.parse_mult_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_id_end_1>']):  # prod 78
            return
        self.syntax_error('<struct_id_end>')

    def parse_struct_init(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_init>']):  # prod 79
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_init_1>']):  # prod 80
            return
        self.syntax_error('<struct_init>')

    def parse_struct_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_elem>']):  # prod 81
            self.parse_struct_value()
            if self.stop: return
            self.parse_mult_struct_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_elem_1>']):  # prod 82
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

    def parse_struct_value(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_value>']):  # prod 83
            self.parse_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_value_1>']):  # prod 84
            self.match_token('wall_lit')
            if self.stop: return
            return
        self.syntax_error('<struct_value>')

    def parse_mult_struct_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_struct_elem>']):  # prod 85
            self.match_token(',')
            if self.stop: return
            self.parse_struct_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_struct_elem_1>']):  # prod 86
            return
        self.syntax_error('<mult_struct_elem>')

    def parse_struct_arr_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_arr_elem>']):  # prod 87
            self.parse_struct_elements()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_arr_elem_1>']):  # prod 88
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_struct_mult_elem2()
            if self.stop: return
            return
        self.syntax_error('<struct_arr_elem>')

    def parse_struct_elements(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_elements>']):  # prod 89
            self.parse_struct_value()
            if self.stop: return
            self.parse_struct_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<struct_elements>')

    def parse_struct_mult_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_mult_elem>']):  # prod 90
            self.match_token(',')
            if self.stop: return
            self.parse_struct_value()
            if self.stop: return
            self.parse_struct_mult_elem()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_mult_elem_1>']):  # prod 91
            return
        self.syntax_error('<struct_mult_elem>')

    def parse_struct_mult_elem2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_mult_elem2>']):  # prod 92
            self.match_token(',')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_struct_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_struct_mult_elem2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_mult_elem2_1>']):  # prod 93
            return
        self.syntax_error('<struct_mult_elem2>')

    def parse_mult_struct_id(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_struct_id>']):  # prod 94
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_struct_init()
            if self.stop: return
            self.parse_mult_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_struct_id_1>']):  # prod 95
            return
        self.syntax_error('<mult_struct_id>')

    def parse_struct_var(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_var>']):  # prod 96
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
        if self.in_predict(PREDICT_SET['<global_const>']):  # prod 97
            self.match_token('cement')
            if self.stop: return
            self.parse_global_const_type()
            if self.stop: return
            return
        self.syntax_error('<global_const>')

    def parse_global_const_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_type>']):  # prod 98
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_global_const_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_type_1>']):  # prod 99
            self.match_token('wall')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_g_const_wall_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_type_2>']):  # prod 100
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
        if self.in_predict(PREDICT_SET['<global_const_end>']):  # prod 101
            self.match_token('=')
            if self.stop: return
            self.parse_value()
            if self.stop: return
            self.parse_global_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_end_1>']):  # prod 102
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

    def parse_global_mult_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_mult_const>']):  # prod 103
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
        elif self.in_predict(PREDICT_SET['<global_mult_const_1>']):  # prod 104
            return
        self.syntax_error('<global_mult_const>')

    def parse_global_const_end2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_end2>']):  # prod 105
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_elements()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<global_const_end2_1>']):  # prod 106
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

    def parse_g_const_wall_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<g_const_wall_end>']):  # prod 107
            self.match_token('=')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_g_mult_const_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<g_const_wall_end_1>']):  # prod 108
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_g_const_wall_end2()
            if self.stop: return
            return
        self.syntax_error('<g_const_wall_end>')

    def parse_g_mult_const_wall(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<g_mult_const_wall>']):  # prod 109
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_g_mult_const_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<g_mult_const_wall_1>']):  # prod 110
            return
        self.syntax_error('<g_mult_const_wall>')

    def parse_g_const_wall_end2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<g_const_wall_end2>']):  # prod 111
            self.match_token('=')
            if self.stop: return
            self.match_token('{')
            if self.stop: return
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<g_const_wall_end2_1>']):  # prod 112
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
            self.parse_wall_elem()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            self.parse_wall_mult_elem2()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<g_const_wall_end2>')

    def parse_global_const_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const_struct>']):  # prod 113
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
        elif self.in_predict(PREDICT_SET['<global_const_struct_1>']):  # prod 114
            return
        self.syntax_error('<global_const_struct>')

    def parse_return_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<return_type>']):  # prod 115
            self.parse_data_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<return_type_1>']):  # prod 116
            self.match_token('field')
            if self.stop: return
            return
        self.syntax_error('<return_type>')

    def parse_param_list(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<param_list>']):  # prod 117
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_mult_param()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<param_list_1>']):  # prod 118
            return
        self.syntax_error('<param_list>')

    def parse_mult_param(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_param>']):  # prod 119
            self.match_token(',')
            if self.stop: return
            self.parse_data_type_dec()
            if self.stop: return
            self.parse_mult_param()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_param_1>']):  # prod 120
            return
        self.syntax_error('<mult_param>')

    def parse_func_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_body>']):  # prod 121
            self.parse_local()
            if self.stop: return
            self.parse_func_body2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_body_1>']):  # prod 122
            self.parse_statement()
            if self.stop: return
            self.parse_func_body2()
            if self.stop: return
            return
        self.syntax_error('<func_body>')

    def parse_func_body2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_body2>']):  # prod 123
            self.parse_func_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_body2_1>']):  # prod 124
            return
        self.syntax_error('<func_body2>')

    def parse_local(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<local>']):  # prod 125
            self.parse_declaration()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<local>')

    def parse_declaration(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<declaration>']):  # prod 126
            self.parse_variable()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<declaration_1>']):  # prod 127
            self.parse_structure()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<declaration_2>']):  # prod 128
            self.parse_constant()
            if self.stop: return
            return
        self.syntax_error('<declaration>')

    def parse_variable(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<variable>']):  # prod 129
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_var_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<variable_1>']):  # prod 130
            self.match_token('wall')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_wall_end()
            if self.stop: return
            return
        self.syntax_error('<variable>')

    def parse_var_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<var_end>']):  # prod 131
            self.parse_initializer()
            if self.stop: return
            self.parse_mult_var()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<var_end_1>']):  # prod 132
            self.parse_array_dec()
            if self.stop: return
            return
        self.syntax_error('<var_end>')

    def parse_initializer(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<initializer>']):  # prod 133
            self.match_token('=')
            if self.stop: return
            self._push_expr_end_tokens({';', ','})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<initializer_1>']):  # prod 134
            return
        self.syntax_error('<initializer>')

    def parse_mult_var(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_var>']):  # prod 135
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            self.parse_mult_var()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_var_1>']):  # prod 136
            return
        self.syntax_error('<mult_var>')

    def parse_wall_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_end>']):  # prod 137
            self.parse_wall_initializer()
            if self.stop: return
            self.parse_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_end_1>']):  # prod 138
            self.parse_wall_array()
            if self.stop: return
            return
        self.syntax_error('<wall_end>')

    def parse_wall_initializer(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_initializer>']):  # prod 139
            self.match_token('=')
            if self.stop: return
            self._push_expr_end_tokens({';', ','})
            try:
                self.parse_wall_init()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_initializer_1>']):  # prod 140
            return
        self.syntax_error('<wall_initializer>')


    def parse_wall_init(self):
        if self.stop:
            return

        # Track delimiters inside wall expressions (for expected-token filtering only).
        self.track_delims += 1
        try:
            # v4: <wall_init> -> ( <wall_init> ) <wall_op>
            if self.in_predict(PREDICT_SET['<wall_init>']):  # '('
                self.match_token('(')
                if self.stop: return
                self._push_expr_end_tokens({')'})
                try:
                    self.parse_wall_init()
                finally:
                    self._pop_expr_end_tokens()
                if self.stop: return
                self.match_token(')')
                if self.stop: return
                self.parse_wall_op()
                if self.stop: return
                return

            # v4: <wall_init_1> -> wall_lit <wall_op>
            if self.in_predict(PREDICT_SET['<wall_init_1>']):  # wall_lit
                self.match_token('wall_lit')
                if self.stop: return
                self.parse_wall_op()
                if self.stop: return
                return

            # v4: <wall_init_2> -> id <id_type> <wall_op>
            if self.in_predict(PREDICT_SET['<wall_init_2>']):  # id
                self.match_token('id')
                if self.stop: return
                self.parse_id_type()
                if self.stop: return
                self.parse_wall_op()
                if self.stop: return
                return

            self.syntax_error('<wall_init>')
        finally:
            self.track_delims -= 1
            if self.track_delims <= 0:
                self.track_delims = 0
                self.delim_stack.clear()


    def parse_wall_op(self):
        if self.stop:
            return

        # v4: <wall_op> -> + <wall_init> | λ
        if self.in_predict(PREDICT_SET['<wall_op>']):  # '+'
            self.match_token('+')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_op_1>']):  # FOLLOW
            return

        self.syntax_error('<wall_op>')


    def parse_wall_rhs(self):
        """Deprecated in v4: kept for compatibility; delegates to <wall_init>."""
        if self.stop:
            return
        self.parse_wall_init()

    def parse_mult_wall(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_wall>']):  # prod 150
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_wall_initializer()
            if self.stop: return
            self.parse_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_wall_1>']):  # prod 151
            return
        self.syntax_error('<mult_wall>')

    def parse_constant(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<constant>']):  # prod 152
            self.match_token('cement')
            if self.stop: return
            self.parse_const_type()
            if self.stop: return
            return
        self.syntax_error('<constant>')

    def parse_const_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_type>']):  # prod 153
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_const_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_type_1>']):  # prod 154
            self.match_token('wall')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_const_wall_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_type_2>']):  # prod 155
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
        if self.in_predict(PREDICT_SET['<const_end>']):  # prod 156
            self.match_token('=')
            if self.stop: return
            self._push_expr_end_tokens({';', ','})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_end_1>']):  # prod 157
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_global_const_end2()
            if self.stop: return
            return
        self.syntax_error('<const_end>')

    def parse_mult_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const>']):  # prod 158
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self._push_expr_end_tokens({';', ','})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_const_1>']):  # prod 159
            return
        self.syntax_error('<mult_const>')

    def parse_const_wall_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_wall_end>']):  # prod 160
            self.match_token('=')
            if self.stop: return
            self._push_expr_end_tokens({';', ','})
            try:
                self.parse_wall_init()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_wall_end_1>']):  # prod 161
            self.match_token('[')
            if self.stop: return
            self.match_token('tile_lit')
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_g_const_wall_end2()
            if self.stop: return
            return
        self.syntax_error('<const_wall_end>')

    def parse_mult_const_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const_struct>']):  # prod 162
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
        elif self.in_predict(PREDICT_SET['<mult_const_struct_1>']):  # prod 163
            return
        self.syntax_error('<mult_const_struct>')


    def parse_init_value(self):
        """Expression parser (updated for PredictSet v4 / CFG 8.0 LL(1))."""
        if self.stop:
            return

        # Track delimiters inside expressions for cleaner expected-token filtering.
        self.track_delims += 1
        try:
            # <expression> -> id <id_type> <exp_op>
            if self.in_predict(PREDICT_SET['<expression>']):  # prod v4
                self.match_token('id')
                if self.stop: return
                self.parse_id_type()
                if self.stop: return
                self.parse_exp_op()
                if self.stop: return
                return

            # <expression_1> -> ( <expression> ) <postfix_opt> <exp_op>
            if self.in_predict(PREDICT_SET['<expression_1>']):  # prod v4
                self.match_token('(')
                if self.stop: return
                self._push_expr_end_tokens({')'})
                try:
                    self.parse_init_value()
                finally:
                    self._pop_expr_end_tokens()
                if self.stop: return
                self.match_token(')')
                if self.stop: return
                self.parse_postfix_opt()
                if self.stop: return
                self.parse_exp_op()
                if self.stop: return
                return

            # <expression_2> -> <value_exp> <exp_op>
            if self.in_predict(PREDICT_SET['<expression_2>']):  # prod v4
                self.parse_value_exp()
                if self.stop: return
                self.parse_exp_op()
                if self.stop: return
                return

            # <expression_3> -> <prefix_op> <prefix_exp> <exp_op>
            if self.in_predict(PREDICT_SET['<expression_3>']):  # prod v4
                self.parse_prefix_op()
                if self.stop: return
                self.parse_prefix_exp()
                if self.stop: return
                self.parse_exp_op()
                if self.stop: return
                return

            self.syntax_error('<expression>')
        finally:
            self.track_delims -= 1
            if self.track_delims <= 0:
                self.track_delims = 0
                self.delim_stack.clear()


    def parse_value_exp(self):
        if self.stop: 
            return

        # <value_exp> -> literal | - <negative_type>
        if self.in_predict(PREDICT_SET['<value_exp>']):  # literals
            self.parse_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_exp_1>']):  # '-'
            self.match_token('-')
            if self.stop: return
            self.parse_negative_type()
            if self.stop: return
            return

        self.syntax_error('<value_exp>')


    def parse_value_type(self):
        """Removed in v4; kept for compatibility (delegates to <value> or id-based expression)."""
        if self.stop:
            return
        if self.current_type == 'id':
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            return
        self.parse_value()

    def parse_id_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type>']):  # prod 171
            self.parse_id_type2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type_1>']):  # prod 172
            return
        self.syntax_error('<id_type>')


    def parse_id_type2(self):
        if self.stop: 
            return

        # v4:
        # <id_type2>   -> <func_call>
        # <id_type2_1> -> <arr_struct> <postfix_opt>
        # <id_type2_2> -> <postfix_op>
        if self.in_predict(PREDICT_SET['<id_type2>']):  # '('
            self.parse_func_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type2_1>']):  # '[' or '.'
            self.parse_arr_struct()
            if self.stop: return
            self.parse_postfix_opt()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type2_2>']):  # '++' or '--'
            self.parse_postfix_op()
            if self.stop: return
            return

        self.syntax_error('<id_type2>')


    def parse_arr_struct(self):
        if self.stop:
            return

        # v4: <arr_struct> -> <array_index> | <struct_id>
        if self.in_predict(PREDICT_SET['<arr_struct>']):  # '['
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_struct_1>']):  # '.'
            self.parse_struct_id()
            if self.stop: return
            return

        self.syntax_error('<arr_struct>')


    def parse_array_index(self):
        if self.stop:
            return

        # v4: non-nullable
        if self.in_predict(PREDICT_SET['<array_index>']):  # '['
            self.match_token('[')
            if self.stop: return
            self._push_expr_end_tokens({']'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_array_index2()
            if self.stop: return
            return

        self.syntax_error('<array_index>')

    def parse_array_index2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index2>']):  # prod 180
            self.match_token('[')
            if self.stop: return
            self._push_expr_end_tokens({']'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index2_1>']):  # prod 181
            return
        self.syntax_error('<array_index2>')




    def parse_array_index_opt(self):
        if self.stop:
            return

        # v4: optional
        if self.in_predict(PREDICT_SET['<array_index_opt>']):  # '['
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index_opt_1>']):  # FOLLOW (closers/operators)
            return

        self.syntax_error('<array_index_opt>')

    def parse_struct_id(self):
        if self.stop:
            return

        # v4: non-nullable; index is optional
        if self.in_predict(PREDICT_SET['<struct_id>']):  # '.'
            self.match_token('.')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_array_index_opt()
            if self.stop: return
            return

        self.syntax_error('<struct_id>')


    def parse_func_call(self):
        if self.stop:
            return

        # v4: non-nullable
        if self.in_predict(PREDICT_SET['<func_call>']):  # '('
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return

        self.syntax_error('<func_call>')


    def parse_func_argu(self):
        if self.stop:
            return

        # v4: <func_argu> -> <assign_rhs> <func_mult_call> | λ
        if self.in_predict(PREDICT_SET['<func_argu_1>']):  # ')'
            return

        if self.in_predict(PREDICT_SET['<func_argu>']):  # non-empty
            self._push_expr_end_tokens({',', ')'})
            try:
                if self.current_type == 'wall_lit':
                    self.parse_wall_init()
                else:
                    self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return

        self.syntax_error('<func_argu>')


    def parse_func_mult_call(self):
        if self.stop:
            return

        # v4: <func_mult_call> -> , <assign_rhs> <func_mult_call> | λ
        if self.in_predict(PREDICT_SET['<func_mult_call>']):  # ','
            self.match_token(',')
            if self.stop: return
            self._push_expr_end_tokens({',', ')'})
            try:
                if self.current_type == 'wall_lit':
                    self.parse_wall_init()
                else:
                    self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_mult_call_1>']):  # ')'
            return

        self.syntax_error('<func_mult_call>')


    def parse_postfix_op(self):
        if self.stop:
            return

        # v4: non-nullable (++, --)
        if self.in_predict(PREDICT_SET['<postfix_op>']):
            self.parse_unary_op()
            if self.stop: return
            return

        self.syntax_error('<postfix_op>')



    def parse_postfix_opt(self):
        if self.stop:
            return

        if self.in_predict(PREDICT_SET['<postfix_opt>']):  # '++' or '--'
            self.parse_postfix_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<postfix_opt_1>']):  # FOLLOW
            return

        self.syntax_error('<postfix_opt>')

    def parse_unary_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<unary_op>']):  # prod 194
            self.match_token('++')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<unary_op_1>']):  # prod 195
            self.match_token('--')
            if self.stop: return
            return
        self.syntax_error('<unary_op>')


    def parse_group(self):
        """Removed in v4; kept for compatibility: parses '( <expression> )'."""
        if self.stop:
            return
        if self.current_type != '(':
            self.syntax_error('<prefix_exp>')
            return
        self.match_token('(')
        if self.stop: return
        self._push_expr_end_tokens({')'})
        try:
            self.parse_init_value()
        finally:
            self._pop_expr_end_tokens()
        if self.stop: return
        self.match_token(')')
        if self.stop: return

    def parse_negative_type(self):
        if self.stop:
            return

        # <negative_type> -> literal | id <id_type> | ( <expression> ) <postfix_opt>
        if self.in_predict(PREDICT_SET['<negative_type>']):  # literals
            self.parse_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<negative_type_1>']):  # id
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<negative_type_2>']):  # '('
            self.match_token('(')
            if self.stop: return
            self._push_expr_end_tokens({')'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.parse_postfix_opt()
            if self.stop: return
            return

        self.syntax_error('<negative_type>')

    def parse_exp_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<exp_op>']):  # prod 199
            self.parse_operator()
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<exp_op_1>']):  # prod 200
            return
        self.syntax_error('<exp_op>')

    def parse_prefix_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<prefix_op>']):  # prod 201
            self.match_token('!')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<prefix_op_1>']):  # prod 202
            self.parse_unary_op()
            if self.stop: return
            return
        self.syntax_error('<prefix_op>')



    def parse_prefix_exp(self):
        if self.stop:
            return

        # v4: <prefix_exp> -> ( <expression> ) <postfix_opt> | <id_val>
        if self.in_predict(PREDICT_SET['<prefix_exp>']):  # '('
            self.match_token('(')
            if self.stop: return
            self._push_expr_end_tokens({')'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.parse_postfix_opt()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<prefix_exp_1>']):  # 'id'
            self.parse_id_val()
            if self.stop: return
            return

        self.syntax_error('<prefix_exp>')

    def parse_id_val(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_val>']):  # prod 203
            self.match_token('id')
            if self.stop: return
            self.parse_id_type3()
            if self.stop: return
            return
        self.syntax_error('<id_val>')

    def parse_id_type3(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type3>']):  # prod 204
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type3_1>']):  # prod 205
            self.parse_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type3_2>']):  # prod 206
            return
        self.syntax_error('<id_type3>')

    def parse_operator(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<operator>']):  # prod 207
            self.match_token('+')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_1>']):  # prod 208
            self.match_token('-')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_2>']):  # prod 209
            self.match_token('*')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_3>']):  # prod 210
            self.match_token('/')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_4>']):  # prod 211
            self.match_token('%')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_5>']):  # prod 212
            self.match_token('<')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_6>']):  # prod 213
            self.match_token('<=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_7>']):  # prod 214
            self.match_token('>')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_8>']):  # prod 215
            self.match_token('>=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_9>']):  # prod 216
            self.match_token('==')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_10>']):  # prod 217
            self.match_token('!=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_11>']):  # prod 218
            self.match_token('&&')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_12>']):  # prod 219
            self.match_token('||')
            if self.stop: return
            return
        self.syntax_error('<operator>')

    def parse_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<statement>']):  # prod 220
            self.parse_io_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_1>']):  # prod 221
            self.parse_assign_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_2>']):  # prod 222
            self.parse_if_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_3>']):  # prod 223
            self.parse_switch_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_4>']):  # prod 224
            self.parse_for_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_5>']):  # prod 225
            self.parse_while_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_6>']):  # prod 226
            self.parse_dowhile_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_7>']):  # prod 227
            self.parse_break_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_8>']):  # prod 228
            self.parse_continue_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_9>']):  # prod 229
            self.parse_return_statement()
            if self.stop: return
            return
        self.syntax_error('<statement>')

    def parse_io_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<io_statement>']):  # prod 230
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
        elif self.in_predict(PREDICT_SET['<io_statement_1>']):  # prod 231
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
        if self.in_predict(PREDICT_SET['<write_argu>']):  # prod 232
            self.match_token('&')
            if self.stop: return
            self.parse_id_val()
            if self.stop: return
            self.parse_mult_write_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<write_argu_1>']):  # prod 233
            self.parse_id_val()
            if self.stop: return
            self.parse_mult_write_argu()
            if self.stop: return
            return
        self.syntax_error('<write_argu>')

    def parse_mult_write_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_write_argu>']):  # prod 234
            self.match_token(',')
            if self.stop: return
            self.parse_write_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_write_argu_1>']):  # prod 235
            return
        self.syntax_error('<mult_write_argu>')


    def parse_view_argu(self):
        if self.stop:
            return

        # v4: <view_argu> -> , <assign_rhs> <view_argu_tail> | λ
        if self.in_predict(PREDICT_SET['<view_argu>']):  # ','
            self.match_token(',')
            if self.stop: return
            self._push_expr_end_tokens({',', ')'})
            try:
                if self.current_type == 'wall_lit':
                    self.parse_wall_init()
                else:
                    self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_view_argu_tail()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<view_argu_1>']):  # ')'
            return

        self.syntax_error('<view_argu>')




    def parse_view_argu_tail(self):
        if self.stop:
            return

        # v4: <view_argu_tail> -> , <assign_rhs> <view_argu_tail> | λ
        if self.in_predict(PREDICT_SET['<view_argu_tail>']):  # ','
            self.match_token(',')
            if self.stop: return
            self._push_expr_end_tokens({',', ')'})
            try:
                if self.current_type == 'wall_lit':
                    self.parse_wall_init()
                else:
                    self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.parse_view_argu_tail()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<view_argu_tail_1>']):  # ')'
            return

        self.syntax_error('<view_argu_tail>')

    def parse_mult_view_argu(self):
        """Removed in v4; kept as an alias to <view_argu_tail> for compatibility."""
        if self.stop:
            return
        self.parse_view_argu_tail()

    def parse_assign_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_statement>']):  # prod 240
            self.parse_unary_op()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_statement_1>']):  # prod 241
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
        if self.in_predict(PREDICT_SET['<id_type4>']):  # prod 242
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type4_1>']):  # prod 243
            self.parse_unary_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type4_2>']):  # prod 244
            self.parse_id_type3()
            if self.stop: return
            self.parse_assign_op()
            if self.stop: return
            self.parse_assign_value()
            if self.stop: return
            return
        self.syntax_error('<id_type4>')


    def parse_assign_value(self):
        """RHS of assignment: expression or wall_init (updated for v4)."""
        if self.stop:
            return

        self._push_expr_end_tokens({';'})
        try:
            if self.current_type == 'wall_lit':
                self.parse_wall_init()
            else:
                self.parse_init_value()
        finally:
            self._pop_expr_end_tokens()

        if self.stop: 
            return

    def parse_assign_op(self):
        """Assignment operator parser (updated for v4): '=' or compound op."""
        if self.stop:
            return

        if self.in_predict(PREDICT_SET['<assign_end_1>']):  # '='
            self.match_token('=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_end>']):  # compound ops
            self.parse_compound_op()
            if self.stop: return
            return

        self.syntax_error('<assign_end>')



    def parse_compound_op(self):
        if self.stop:
            return

        if self.in_predict(PREDICT_SET['<compound_op>']):
            self.match_token('+=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_1>']):
            self.match_token('-=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_2>']):
            self.match_token('*=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_3>']):
            self.match_token('/=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_4>']):
            self.match_token('%=')
            if self.stop: return
            return

        self.syntax_error('<compound_op>')

    def parse_if_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<if_statement>']):  # prod 253
            self.match_token('if')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self._push_expr_end_tokens({')'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
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
        if self.in_predict(PREDICT_SET['<else_statement>']):  # prod 254
            self.match_token('else')
            if self.stop: return
            self.parse_else_statement2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<else_statement_1>']):  # prod 255
            return
        self.syntax_error('<else_statement>')

    def parse_else_statement2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<else_statement2>']):  # prod 256
            self.parse_if_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<else_statement2_1>']):  # prod 257
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
        if self.in_predict(PREDICT_SET['<switch_statement>']):  # prod 258
            self.match_token('room')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self._push_expr_end_tokens({')'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
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
        if self.in_predict(PREDICT_SET['<switch_body>']):  # updated
            self.parse_case_list()
            if self.stop: return
            self.parse_default_opt()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<switch_body_1>']):  # updated
            self.match_token('ground')
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            return
        self.syntax_error('<switch_body>')

    def parse_case_list(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_list>']):  # updated
            self.match_token('door')
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            self.parse_case_list_tail()
            if self.stop: return
            return
        self.syntax_error('<case_list>')

    def parse_case_list_tail(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_list_tail>']):  # updated
            self.match_token('door')
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            self.parse_case_list_tail()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_list_tail_1>']):  # updated
            return
        self.syntax_error('<case_list_tail>')

    def parse_default_opt(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<default_opt>']):  # updated
            self.match_token('ground')
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<default_opt_1>']):  # updated
            return
        self.syntax_error('<default_opt>')

    def parse_case_exp(self):

        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_exp>']):  # prod 263
            self.parse_case_type()
            if self.stop: return
            self.parse_case_op()
            if self.stop: return
            return
        self.syntax_error('<case_exp>')

    def parse_case_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_type>']):  # prod 264
            self.parse_case_val()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_type_1>']):  # prod 265
            self.parse_case_group()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_type_2>']):  # prod 266
            self.match_token('-')
            if self.stop: return
            self.parse_case_negative()
            if self.stop: return
            return
        self.syntax_error('<case_type>')

    def parse_case_val(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_val>']):  # prod 267
            self.match_token('tile_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_1>']):  # prod 268
            self.match_token('brick_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_2>']):  # prod 269
            self.match_token('solid')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_3>']):  # prod 270
            self.match_token('fragile')
            if self.stop: return
            return
        self.syntax_error('<case_val>')

    def parse_case_group(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_group>']):  # prod 271
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
        if self.in_predict(PREDICT_SET['<case_negative>']):  # prod 272
            self.parse_case_val()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_negative_1>']):  # prod 273
            self.parse_case_group()
            if self.stop: return
            return
        self.syntax_error('<case_negative>')

    def parse_case_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_op>']):  # updated
            self.parse_operator()
            if self.stop: return
            self.parse_case_type()
            if self.stop: return
            self.parse_case_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_op_1>']):  # updated
            return
        self.syntax_error('<case_op>')

    def parse_case_body(self):

        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_body>']):  # prod 276
            self.parse_statement()
            if self.stop: return
            self.parse_mult_smt()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_body_1>']):  # prod 277
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_body_2>']):  # prod 278
            return
        self.syntax_error('<case_body>')

    def parse_mult_smt(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_smt>']):  # prod 279
            self.parse_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_smt_1>']):  # prod 280
            return
        self.syntax_error('<mult_smt>')
    def parse_for_statement(self):
        if self.stop: return
        # CFG 7.0 / arCh Document alignment:
        # for ( <for_dec> ; <init_value> ; <init_value> ) { <func_body> }
        # Empty clauses like for(;;) or for(;;;) are NOT allowed.
        if self.in_predict(PREDICT_SET['<for_statement>']):  # prod 281
            self.match_token('for')
            if self.stop: return
            self.match_token('(')
            if self.stop: return

            # init: required <for_dec>
            self.parse_for_dec()
            if self.stop: return
            self.match_token(';')
            if self.stop: return

            # condition: required <init_value>
            self._push_expr_end_tokens({';'})
# condition: required <init_value>
            try:
# condition: required <init_value>
                self.parse_init_value()
# condition: required <init_value>
            finally:
# condition: required <init_value>
                self._pop_expr_end_tokens()
            if self.stop: return
            self.match_token(';')
            if self.stop: return

            # update: required <init_value>
            self._push_expr_end_tokens({')'})
# update: required <init_value>
            try:
# update: required <init_value>
                self.parse_init_value()
# update: required <init_value>
            finally:
# update: required <init_value>
                self._pop_expr_end_tokens()
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
        if self.in_predict(PREDICT_SET['<for_dec>']):  # prod 282
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<for_dec_1>']):  # prod 283
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            return
        self.syntax_error('<for_dec>')

    def parse_while_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<while_statement>']):  # prod 284
            self.match_token('while')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self._push_expr_end_tokens({')'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
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
        if self.in_predict(PREDICT_SET['<dowhile_statement>']):  # prod 285
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
            self._push_expr_end_tokens({')'})
            try:
                self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<dowhile_statement>')

    def parse_break_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<break_statement>']):  # prod 286
            self.match_token('crack')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<break_statement>')

    def parse_continue_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<continue_statement>']):  # prod 287
            self.match_token('mend')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<continue_statement>')


    def parse_return_statement(self):
        if self.stop:
            return

        if self.in_predict(PREDICT_SET['<return_statement>']):  # 'home'
            self.match_token('home')
            if self.stop: return

            # Return value: expression or wall_init
            self._push_expr_end_tokens({';'})
            try:
                if self.current_type == 'wall_lit':
                    self.parse_wall_init()
                else:
                    self.parse_init_value()
            finally:
                self._pop_expr_end_tokens()

            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return

        self.syntax_error('<return_statement>')


    def parse_home_value(self, end_tokens=None):
        """Removed in v4; kept for compatibility."""
        if self.stop:
            return

        if end_tokens is not None:
            self._push_expr_end_tokens(set(end_tokens))
        try:
            if self.current_type == 'wall_lit':
                self.parse_wall_init()
            else:
                self.parse_init_value()
        finally:
            if end_tokens is not None:
                self._pop_expr_end_tokens()

