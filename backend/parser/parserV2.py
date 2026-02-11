from __future__ import annotations
from typing import List, Dict, Any

from parser.predict_set import PREDICT_SET
from parser.follow_set import FOLLOW_SET

class Parser:
    IGNORE_TYPES = ("space", "tab", "newline", "Single-Line Comment", "Multi-Line Comment")

    def __init__(self, tokens):
        self.tokens = [t for t in (tokens or []) if getattr(t, "tokenType", None) not in self.IGNORE_TYPES]

        self.index = 0
        self.stop = False
        self.errors: List[Dict[str, Any]] = []
        
        # Track parsing context for better error filtering
        self.context_stack = []

        self.current_type = "EOF"
        self.current_lexeme = "$"
        self.current_line = 1
        self.current_col = 1

        self._update_current()

    # ---------------- token helpers ----------------
    # normalizes token id1, id2 ... to id
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

    # ---------------- context tracking ----------------
    def _push_context(self, context_type: str):
        """Push a parsing context onto the stack."""
        self.context_stack.append(context_type)
    
    def _pop_context(self):
        """Pop a parsing context from the stack."""
        if self.context_stack:
            self.context_stack.pop()
    
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

    def syntax_error(self, nt: str):
        """Generate error with correct expected tokens from PREDICT sets"""
        base = self._base_nt(nt)
        expected = set()
        
        # Collect all PREDICT tokens for this non-terminal
        for key in PREDICT_SET:
            if self._base_nt(key) == base:
                expected.update(PREDICT_SET[key])
        
        # Sort for consistent output
        expected = sorted(list(expected))
        self._add_error(f"Unexpected Character {self.current_lexeme!r}; Expected one of {expected}")

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

    # ---------------- production parsing methods ----------------

    # Production 1: <program>
    def parse_program(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<program>']):  # prod 1
            self.parse_global()
            if self.stop: return
            self.parse_program_body()
            if self.stop: return
            return
        self.syntax_error('<program>')

    # Productions 2-3: <program_body>
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

    # Productions 4-5: <program_body2>
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

    # Productions 6-7: <global>
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

    # Productions 8-10: <global_dec>
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

    # Productions 11-12: <global_var>
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

    # Productions 13-16: <data_type>
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

    # Productions 17-18: <global_end>
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

    # Productions 19-20: <global_init>
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

    # Productions 21-22: <global_mult>
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

    # Productions 23-27: <value>
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

    # Production 28: <array_dec>
    def parse_array_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_dec>']):  # prod 28
            self.match_token('[')
            if self.stop: return
            self.parse_arr_size()
            if self.stop: return
            return
        self.syntax_error('<array_dec>')

    # Productions 29-30: <arr_size>
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

    # Productions 31-32: <one_d_end>
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

    # Productions 33-35: <one_d_end2>
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

    # Productions 36-37: <two_d_end>
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

    # Production 38: <elements>
    def parse_elements(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<elements>']):  # prod 38
            self.parse_value()
            if self.stop: return
            self.parse_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<elements>')

    # Productions 39-40: <mult_elem>
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

    # Productions 41-42: <mult_elem2>
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

    # Productions 43-44: <global_wall_end>
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

    # Productions 45-46: <global_wall_init>
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

    # Productions 47-48: <global_mult_wall>
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

    # Production 49: <wall_array>
    def parse_wall_array(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_array>']):  # prod 49
            self.match_token('[')
            if self.stop: return
            self.parse_wall_size()
            if self.stop: return
            return
        self.syntax_error('<wall_array>')

    # Productions 50-51: <wall_size>
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

    # Productions 52-53: <wall_one_d_end>
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

    # Productions 54-56: <wall_one_d_end2>
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

    # Productions 57-58: <wall_two_d_end>
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

    # Production 59: <wall_elem>
    def parse_wall_elem(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_elem>']):  # prod 59
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<wall_elem>')

    # Productions 60-61: <wall_mult_elem>
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

    # Productions 62-63: <wall_mult_elem2>
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

    # Production 64: <structure>
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

    # Productions 65-66: <struct_type>
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

    # Production 67: <struct_dec>
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

    # Production 68: <struct_members>
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

    # Productions 69-70: <data_type_dec>
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

    # Productions 71-72: <array>
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
        elif self.in_predict(PREDICT_SET['<array>_1']):  # prod 72
            return
        self.syntax_error('<array>')

    # Productions 73-74: <array2>
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

    # Productions 75-76: <mult_members>
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

    # Productions 77-78: <struct_id_end>
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

    # Productions 79-80: <struct_init>
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

    # Productions 81-82: <struct_elem>
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

    # Productions 83-84: <struct_value>
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

    # Productions 85-86: <mult_struct_elem>
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

    # Productions 87-88: <struct_arr_elem>
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

    # Production 89: <struct_elements>
    def parse_struct_elements(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_elements>']):  # prod 89
            self.parse_struct_value()
            if self.stop: return
            self.parse_struct_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<struct_elements>')

    # Productions 90-91: <struct_mult_elem>
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

    # Productions 92-93: <struct_mult_elem2>
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

    # Productions 94-95: <mult_struct_id>
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

    # Production 96: <struct_var>
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

    # Production 97: <global_const>
    def parse_global_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const>']):  # prod 97
            self.match_token('cement')
            if self.stop: return
            self.parse_global_const_type()
            if self.stop: return
            return
        self.syntax_error('<global_const>')

    # Productions 98-100: <global_const_type>
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

    # Productions 101-102: <global_const_end>
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

    # Productions 103-104: <global_mult_const>
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

    # Productions 105-106: <global_const_end2>
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

    # Productions 107-108: <g_const_wall_end>
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

    # Productions 109-110: <g_mult_const_wall>
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

    # Productions 111-112: <g_const_wall_end2>
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

    # Productions 113-114: <global_const_struct>
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

    # Productions 115-116: <return_type>
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

    # Productions 117-118: <param_list>
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

    # Productions 119-120: <mult_param>
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

    # Productions 121-122: <func_body>
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

    # Productions 123-124: <func_body2>
    def parse_func_body2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_body2>']):  # prod 123
            self.parse_func_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_body2_1>']):  # prod 124
            return
        self.syntax_error('<func_body2>')

    # Production 125: <local>
    def parse_local(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<local>']):  # prod 125
            self.parse_declaration()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<local>')

    # Productions 126-128: <declaration>
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

    # Productions 129-130: <variable>
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

    # Productions 131-132: <var_end>
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

    # Productions 133-134: <initializer>
    def parse_initializer(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<initializer>']):  # prod 133
            self.match_token('=')
            if self.stop: return
            # ADD CONTEXT TRACKING
            self._push_context("assignment_rhs")
            self.parse_expression()
            self._pop_context()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<initializer_1>']):  # prod 134
            return
        self.syntax_error('<initializer>')

    # Productions 135-136: <mult_var>
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

    # Productions 137-140: <expression>
    def parse_expression(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<expression>']):  # prod 137
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<expression_1>']):  # prod 138
            self.match_token('(')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.parse_postfix_op()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<expression_2>']):  # prod 139
            self.parse_value_exp()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<expression_3>']):  # prod 140
            self.parse_prefix_op()
            if self.stop: return
            self.parse_prefix_exp()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        self.syntax_error('<expression>')

    # Productions 141-142: <value_exp>
    def parse_value_exp(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value_exp>']):  # prod 141
            self.parse_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_exp_1>']):  # prod 142
            self.match_token('-')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            return
        self.syntax_error('<value_exp>')

    # Productions 143-144: <id_type>
    def parse_id_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type>']):  # prod 143
            self.parse_id_type2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type_1>']):  # prod 144
            return
        self.syntax_error('<id_type>')

    # Productions 145-146: <id_type2>
    def parse_id_type2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type2>']):  # prod 145
            self.parse_arr_struct()
            if self.stop: return
            self.parse_postfix_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type2_1>']):  # prod 146
            self.parse_func_call()
            if self.stop: return
            return
        self.syntax_error('<id_type2>')

    # Productions 147-148: <arr_struct>
    def parse_arr_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<arr_struct>']):  # prod 147
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_struct_1>']):  # prod 148
            self.parse_struct_id()
            if self.stop: return
            return
        self.syntax_error('<arr_struct>')

    # Productions 149-150: <array_index>
    def parse_array_index(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index>']):  # prod 149
            self.match_token('[')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_array_index2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index_1>']):  # prod 150
            return
        self.syntax_error('<array_index>')

    # Productions 151-152: <array_index2>
    def parse_array_index2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index2>']):  # prod 151
            self.match_token('[')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index2_1>']):  # prod 152
            return
        self.syntax_error('<array_index2>')

    # Productions 153-154: <struct_id>
    def parse_struct_id(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_id>']):  # prod 153
            self.match_token('.')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_id_1>']):  # prod 154
            return
        self.syntax_error('<struct_id>')

    # Productions 155-156: <func_call>
    def parse_func_call(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_call>']):  # prod 155
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_call_1>']):  # prod 156
            return
        self.syntax_error('<func_call>')

    # Productions 157-158: <func_argu>
    def parse_func_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_argu>']):  # prod 157
            # ADD CONTEXT TRACKING
            self._push_context("func_args")
            self.parse_assign_rhs()
            if self.stop: return
            self.parse_func_mult_call()
            self._pop_context()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_argu_1>']):  # prod 158
            return
        self.syntax_error('<func_argu>')

    # Productions 159-160: <func_mult_call>
    def parse_func_mult_call(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_mult_call>']):  # prod 159
            self.match_token(',')
            if self.stop: return
            self.parse_assign_rhs()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_mult_call_1>']):  # prod 160
            return
        self.syntax_error('<func_mult_call>')

    # Productions 161-162: <postfix_op>
    def parse_postfix_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<postfix_op>']):  # prod 161
            self.parse_unary_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<postfix_op_1>']):  # prod 162
            return
        self.syntax_error('<postfix_op>')

    # Productions 163-164: <unary_op>
    def parse_unary_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<unary_op>']):  # prod 163
            self.match_token('++')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<unary_op_1>']):  # prod 164
            self.match_token('--')
            if self.stop: return
            return
        self.syntax_error('<unary_op>')

    # Productions 165-166: <exp_op>
    def parse_exp_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<exp_op>']):  # prod 165
            self.parse_operator()
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<exp_op_1>']): #prod 166
            return
        self.syntax_error('<exp_op>')

    # Productions 167-168: <prefix_op>
    def parse_prefix_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<prefix_op>']):  # prod 167
            self.match_token('!')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<prefix_op_1>']):  # prod 168
            self.parse_unary_op()
            if self.stop: return
            return
        self.syntax_error('<prefix_op>')

    # Production 169-170: <prefix_exp>
    def parse_prefix_exp(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<prefix_exp>']): # prod 169
            self.match_token('(')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<prefix_exp_1>']): # prod 170
            self.parse_id_val()
            if self.stop: return
            return
        
    # Production 171: <id_val>
    def parse_id_val(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_val>']):  # prod 171
            self.match_token('id')
            if self.stop: return
            self.parse_id_type3()
            if self.stop: return
            return
        self.syntax_error('<id_val>')

    # Productions 172-174: <id_type3>
    def parse_id_type3(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type3>']):  # prod 172
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type3_1>']):  # prod 173
            self.parse_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type3_2>']):  # prod 174
            return
        self.syntax_error('<id_type3>')

    # Productions 175-187: <operator>
    def parse_operator(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<operator>']):  # prod 175
            self.match_token('+')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_1>']):  # prod 176
            self.match_token('-')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_2>']):  # prod 177
            self.match_token('*')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_3>']):  # prod 178
            self.match_token('/')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_4>']):  # prod 179
            self.match_token('%')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_5>']):  # prod 180
            self.match_token('<')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_6>']):  # prod 181
            self.match_token('<=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_7>']):  # prod 182
            self.match_token('>')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_8>']):  # prod 183
            self.match_token('>=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_9>']):  # prod 184
            self.match_token('==')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_10>']):  # prod 185
            self.match_token('!=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_11>']):  # prod 186
            self.match_token('&&')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<operator_12>']):  # prod 187
            self.match_token('||')
            if self.stop: return
            return
        self.syntax_error('<operator>')

    # Productions 188-189: <wall_end>
    def parse_wall_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_end>']):  # prod 188
            self.parse_wall_initializer()
            if self.stop: return
            self.parse_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_end_1>']):  # prod 189
            self.parse_wall_array()
            if self.stop: return
            return
        self.syntax_error('<wall_end>')

    # Productions 190-191: <wall_initializer>
    def parse_wall_initializer(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_initializer>']):  # prod 190
            self.match_token('=')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_initializer_1>']):  # prod 191
            return
        self.syntax_error('<wall_initializer>')

    # Productions 192-194: <wall_init>
    def parse_wall_init(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_init>']):  # prod 192
            self.match_token('(')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_init_1>']):  # prod 193
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_init_2>']):  # prod 194
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        self.syntax_error('<wall_init>')

    # Productions 195-196: <wall_op>
    def parse_wall_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_op>']):  # prod 195
            self.match_token('+')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_op_1>']):  # prod 196
            return
        self.syntax_error('<wall_op>')

    # Productions 197-198: <mult_wall>
    def parse_mult_wall(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_wall>']):  # prod 197
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_wall_initializer()
            if self.stop: return
            self.parse_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_wall_1>']):  # prod 198
            return
        self.syntax_error('<mult_wall>')

    # Production 199: <constant>
    def parse_constant(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<constant>']):  # prod 199
            self.match_token('cement')
            if self.stop: return
            self.parse_const_type()
            if self.stop: return
            return
        self.syntax_error('<constant>')

    # Productions 200-202: <const_type>
    def parse_const_type(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_type>']):  # prod 200
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_const_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_type_1>']):  # prod 201
            self.match_token('wall')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_const_wall_end()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_type_2>']):  # prod 202
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

    # Productions 203-204: <const_end>
    def parse_const_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_end>']):  # prod 203
            self.match_token('=')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            self.parse_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_end_1>']):  # prod 204
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

    # Productions 205-206: <mult_const>
    def parse_mult_const(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const>']):  # prod 205
            self.match_token(',')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token('=')
            if self.stop: return
            self.parse_expression()
            if self.stop: return
            self.parse_mult_const()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_const_1>']):  # prod 206
            return
        self.syntax_error('<mult_const>')

    # Productions 207-208: <const_wall_end>
    def parse_const_wall_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_wall_end>']):  # prod 207
            self.match_token('=')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            self.parse_mult_wall()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<const_wall_end_1>']):  # prod 208
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

    # Productions 209-210: <mult_const_struct>
    def parse_mult_const_struct(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const_struct>']):  # prod 209
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
        elif self.in_predict(PREDICT_SET['<mult_const_struct_1>']):  # prod 210
            return
        self.syntax_error('<mult_const_struct>')

    # Productions 211-220: <statement>
    def parse_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<statement>']):  # prod 211
            self.parse_io_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_1>']):  # prod 212
            self.parse_assign_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_2>']):  # prod 213
            self.parse_if_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_3>']):  # prod 214
            self.parse_switch_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_4>']):  # prod 215
            self.parse_for_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_5>']):  # prod 216
            self.parse_while_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_6>']):  # prod 217
            self.parse_dowhile_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_7>']):  # prod 218
            self.parse_break_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_8>']):  # prod 219
            self.parse_continue_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<statement_9>']):  # prod 220
            self.parse_return_statement()
            if self.stop: return
            return
        self.syntax_error('<statement>')

    # Productions 221-222: <io_statement>
    def parse_io_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<io_statement>']):  # prod 221
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
        elif self.in_predict(PREDICT_SET['<io_statement_1>']):  # prod 222
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

    # Productions 223-224: <write_argu>
    def parse_write_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<write_argu>']):  # prod 223
            self.match_token('&')
            if self.stop: return
            self.parse_id_val()
            if self.stop: return
            self.parse_mult_write_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<write_argu_1>']):  # prod 224
            self.parse_id_val()
            if self.stop: return
            self.parse_mult_write_argu()
            if self.stop: return
            return
        self.syntax_error('<write_argu>')

    # Productions 225-226: <mult_write_argu>
    def parse_mult_write_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_write_argu>']):  # prod 225
            self.match_token(',')
            if self.stop: return
            self.parse_write_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_write_argu_1>']):  # prod 226
            return
        self.syntax_error('<mult_write_argu>')

    # Productions 227-228: <view_argu>
    def parse_view_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<view_argu>']):  # prod 227
            self.match_token(',')
            if self.stop: return
            self.parse_assign_rhs()
            if self.stop: return
            self.parse_mult_view_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<view_argu_1>']):  # prod 228
            return
        self.syntax_error('<view_argu>')

    # Productions 229-230: <mult_view_argu>
    def parse_mult_view_argu(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_view_argu>']):  # prod 229
            self.parse_view_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_view_argu_1>']):  # prod 230
            return
        self.syntax_error('<mult_view_argu>')

    # Productions 231-232: <assign_statement>
    def parse_assign_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_statement>']):  # prod 231
            self.parse_unary_op()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_statement_1>']):  # prod 232
            self.match_token('id')
            if self.stop: return
            self.parse_id_type4()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<assign_statement>')

    # Productions 233-235: <id_type4>
    def parse_id_type4(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type4>']):  # prod 233
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type4_1>']):  # prod 234
            self.parse_unary_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type4_2>']):  # prod 235
            self.parse_id_type3()
            if self.stop: return
            self.parse_assign_end()
            if self.stop: return
            return
        self.syntax_error('<id_type4>')

    # Productions 236-237: <assign_end>
    def parse_assign_end(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_end>']):  # prod 236
            self.parse_compound_op()
            if self.stop: return
            # ADD CONTEXT TRACKING for compound assignment
            self._push_context("assignment_rhs")
            self.parse_expression()
            self._pop_context()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_end_1>']):  # prod 237
            self.match_token('=')
            if self.stop: return
            # ADD CONTEXT TRACKING
            self._push_context("assignment_rhs")
            self.parse_assign_rhs()
            self._pop_context()
            if self.stop: return
            return
        self.syntax_error('<assign_end>')

    # Productions 238-242: <compound_op>
    def parse_compound_op(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<compound_op>']):  # prod 238
            self.match_token('+=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_1>']):  # prod 239
            self.match_token('-=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_2>']):  # prod 240
            self.match_token('*=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_3>']):  # prod 241
            self.match_token('/=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<compound_op_4>']):  # prod 242
            self.match_token('%=')
            if self.stop: return
            return
        self.syntax_error('<compound_op>')

    # Productions 243-247: <assign_rhs>
    def parse_assign_rhs(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_rhs>']):  # prod 243
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            self.parse_assign_exp()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_rhs_1>']):  # prod 244
            self.match_token('(')
            if self.stop: return
            self.parse_assign_rhs()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.parse_assign_exp()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_rhs_2>']):  # prod 245
            self.parse_value_exp()
            if self.stop: return
            self.parse_assign_exp()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_rhs_3>']):  # prod 246
            self.parse_operator()
            if self.stop: return
            self.parse_assign_rhs()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_rhs_4>']):  # prod 247
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_assign_exp()
            if self.stop: return
            return
        self.syntax_error('<assign_rhs>')

    # Productions 248-249: <assign_exp>
    def parse_assign_exp(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_exp>']):  # prod 248
            self.parse_operator()
            if self.stop: return
            self.parse_assign_rhs()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_exp_1>']):  # prod 249
            return
        self.syntax_error('<assign_exp>')

    # Production 250: <if_statement>
    def parse_if_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<if_statement>']):  # prod 250
            self.match_token('if')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            # ADD CONTEXT TRACKING
            self._push_context("if_condition")
            self.parse_expression()
            self._pop_context()
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

    # Productions 251-252: <else_statement>
    def parse_else_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<else_statement>']):  # prod 251
            self.match_token('else')
            if self.stop: return
            self.parse_else_statement2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<else_statement_1>']):  # prod 252
            return
        self.syntax_error('<else_statement>')

    # Productions 253-254: <else_statement2>
    def parse_else_statement2(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<else_statement2>']):  # prod 253
            self.parse_if_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<else_statement2_1>']):  # prod 254
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        self.syntax_error('<else_statement2>')

    # Production 255: <switch_statement>
    def parse_switch_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<switch_statement>']):  # prod 255
            self.match_token('room')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            # ADD CONTEXT TRACKING
            self._push_context("switch_condition")
            self.parse_expression()
            self._pop_context()
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

    # Productions 256-257: <switch_body>
    def parse_switch_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<switch_body>']):  # prod 256
            self.match_token('door')
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            self.parse_mult_switch_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<switch_body_1>']):  # prod 257
            self.match_token('ground')
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            return
        self.syntax_error('<switch_body>')

    # Productions 258-259: <mult_switch_body>
    def parse_mult_switch_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_switch_body>']):  # prod 258
            self.parse_switch_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_switch_body_1>']):  # prod 259
            return
        self.syntax_error('<mult_switch_body>')

    # Productions 260-263: <case_val>
    def parse_case_val(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_val>']):  # prod 260
            self.match_token('tile_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_1>']):  # prod 261
            self.match_token('brick_lit')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_2>']):  # prod 262
            self.match_token('solid')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_val_3>']):  # prod 263
            self.match_token('fragile')
            if self.stop: return
            return
        self.syntax_error('<case_val>')

    # Productions 264-266: <case_body>
    def parse_case_body(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_body>']):  # prod 264
            self.parse_statement()
            if self.stop: return
            self.parse_mult_smt()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_body_1>']):  # prod 265
            self.match_token('{')
            if self.stop: return
            self.parse_func_body()
            if self.stop: return
            self.match_token('}')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_body_2>']):  # prod 266
            return
        self.syntax_error('<case_body>')

    # Productions 267-268: <mult_smt>
    def parse_mult_smt(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_smt>']):  # prod 267
            self.parse_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_smt_1>']):  # prod 268
            return
        self.syntax_error('<mult_smt>')

    # Production 269: <for_statement>
    def parse_for_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<for_statement>']):  # prod 269
            self.match_token('for')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_for_dec()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            # ADD CONTEXT TRACKING for condition
            self._push_context("for_condition")
            self.parse_expression()
            self._pop_context()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            # ADD CONTEXT TRACKING for increment
            self._push_context("for_increment")
            self.parse_expression()
            self._pop_context()
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

    # Productions 270-271: <for_dec>
    def parse_for_dec(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<for_dec>']):  # prod 270
            self.parse_data_type()
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<for_dec_1>']):  # prod 271
            self.match_token('id')
            if self.stop: return
            self.parse_id_type3()
            if self.stop: return
            self.parse_initializer()
            if self.stop: return
            return
        self.syntax_error('<for_dec>')

    # Production 272: <while_statement>
    def parse_while_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<while_statement>']):  # prod 272
            self.match_token('while')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            # ADD CONTEXT TRACKING
            self._push_context("while_condition")
            self.parse_expression()
            self._pop_context()
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

    # Production 273: <dowhile_statement>
    def parse_dowhile_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<dowhile_statement>']):  # prod 273
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
            # ADD CONTEXT TRACKING
            self._push_context("while_condition")
            self.parse_expression()
            self._pop_context()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<dowhile_statement>')

    # Production 274: <break_statement>
    def parse_break_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<break_statement>']):  # prod 274
            self.match_token('crack')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<break_statement>')

    # Production 275: <continue_statement>
    def parse_continue_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<continue_statement>']):  # prod 275
            self.match_token('mend')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<continue_statement>')

    # Production 276: <return_statement>
    def parse_return_statement(self):
        if self.stop: return
        if self.in_predict(PREDICT_SET['<return_statement>']):  # prod 276
            self.match_token('home')
            if self.stop: return
            self.parse_assign_rhs()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<return_statement>')