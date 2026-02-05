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
        self.context_stack = []  # Track parsing context for better error messages

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
        exp = self.filter_expected_by_context(exp, nt)  # Filter by context
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

    def filter_expected_by_context(self, expected: list[str], nt: str) -> list[str]:
        if not self.context_stack:
            return expected
        
        context = self.context_stack[-1]
        base_nt = self._base_nt(nt)
        
        context_filters = {
            ('for_declaration', '<initializer>'): ['=', ';'],
            ('for_declaration', '<var_end>'): ['=', ';'],
            ('for_declaration', '<exp_op>'): [';'],
            ('for_condition', '<exp_op>'): [';', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('for_condition', '<id_type>'): [';', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('for_condition', '<postfix_op>'): [';', '++', '--'],
            ('for_condition', '<arr_struct>'): [';', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('for_increment', '<exp_op>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('for_increment', '<id_type>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('for_increment', '<postfix_op>'): [')', '++', '--'],
            ('for_increment', '<arr_struct>'): [')', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('if_condition', '<exp_op>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('if_condition', '<id_type>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('if_condition', '<postfix_op>'): [')', '++', '--'],
            ('if_condition', '<arr_struct>'): [')', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('while_condition', '<exp_op>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('while_condition', '<id_type>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('while_condition', '<postfix_op>'): [')', '++', '--'],
            ('while_condition', '<arr_struct>'): [')', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('dowhile_condition', '<exp_op>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('dowhile_condition', '<id_type>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('dowhile_condition', '<postfix_op>'): [')', '++', '--'],
            ('dowhile_condition', '<arr_struct>'): [')', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('switch_condition', '<exp_op>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('switch_condition', '<id_type>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('array_index', '<exp_op>'): [']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('array_index', '<id_type>'): [']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('array_index', '<postfix_op>'): [']', '++', '--'],
            ('array_index', '<arr_struct>'): [']', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('func_args', '<exp_op>'): [')', ',', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('func_args', '<func_mult_call>'): [')', ','],
            ('func_args', '<id_type>'): [')', ',', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('func_args', '<postfix_op>'): [')', ',', '++', '--'],
            ('func_args', '<arr_struct>'): [')', ',', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('assignment', '<exp_op>'): [';', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('assignment', '<id_type>'): [';', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('assignment', '<postfix_op>'): [';', '++', '--'],
            ('assignment', '<arr_struct>'): [';', '[', '.', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('assignment', '<id_type4>'): [';', '(', '=', '[', '.', '++', '--', '+=', '-=', '*=', '/=', '%='],
            ('var_declaration', '<initializer>'): ['=', ';', ','],
            ('var_declaration', '<var_end>'): ['=', ';', ',', '['],
            ('var_declaration', '<exp_op>'): [';', ',', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('return_statement', '<exp_op>'): [';', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('return_statement', '<id_type>'): [';', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
            ('group_expr', '<exp_op>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],
            ('group_expr', '<id_type>'): [')', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '(', '[', '.', '++', '--'],
        }
        
        filter_key = (context, base_nt)
        if filter_key in context_filters:
            valid_tokens = set(context_filters[filter_key])
            filtered = [t for t in expected if t in valid_tokens]
            return filtered if filtered else expected
        
        return expected

    # ---------------- entry ----------------
    def parse(self, _predict_set=None):
        self.parse_program()

        if not self.stop and self.current_type != "EOF":
            self._add_error(f"Extra token after program end: {self.current_lexeme!r}")

        return self.errors

    # ---------------- production parsing methods ----------------


    def parse_program(self):
        """<program> → <global> <program_body>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<program>']):  # prod 1
            self.parse_global()
            if self.stop: return
            self.parse_program_body()
            if self.stop: return
            return
        self.syntax_error('<program>')

    def parse_program_body(self):
        """
        <program_body> → wall id ( <param_list> ) { <func_body> } <program_body>  # prod 2
        <program_body> → <return_type> <program_body2>  # prod 3
        """
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
        """
        <program_body2> → id ( <param_list> ) { <func_body> } <program_body>  # prod 4
        <program_body2> → blueprint ( ) { <func_body> }  # prod 5
        """
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
        """
        <global> → roof <global_dec> ; <global>  # prod 6
        <global> → λ  # prod 7
        """
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
        """
        <global_dec> → <global_var>  # prod 8
        <global_dec> → <structure>  # prod 9
        <global_dec> → <global_const>  # prod 10
        """
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
        """
        <global_var> → <data_type> id <global_end>  # prod 11
        <global_var> → wall id <global_wall_end>  # prod 12
        """
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
        """
        <data_type> → tile  # prod 13
        <data_type> → glass  # prod 14
        <data_type> → brick  # prod 15
        <data_type> → beam  # prod 16
        """
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
        """
        <global_end> → <global_init> <global_mult>  # prod 17
        <global_end> → <array_dec>  # prod 18
        """
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
        """
        <global_init> → = <value>  # prod 19
        <global_init> → λ  # prod 20
        """
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
        """
        <global_mult> → , id <global_init> <global_mult>  # prod 21
        <global_mult> → λ  # prod 22
        """
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
        """
        <value> → tile_lit  # prod 23
        <value> → glass_lit  # prod 24
        <value> → brick_lit  # prod 25
        <value> → solid  # prod 26
        <value> → fragile  # prod 27
        """
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
        """<array_dec> → [ <arr_size>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_dec>']):  # prod 28
            self.match_token('[')
            if self.stop: return
            self.parse_arr_size()
            if self.stop: return
            return
        self.syntax_error('<array_dec>')

    def parse_arr_size(self):
        """
        <arr_size> → ] <one_d_end>  # prod 29
        <arr_size> → tile_lit ] <one_d_end2>  # prod 30
        """
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
        """
        <one_d_end> → [ tile_lit ] = { { <elements> } <mult_elem2> }  # prod 31
        <one_d_end> → = { <elements> }  # prod 32
        """
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
        """
        <one_d_end2> → [ tile_lit ] <two_d_end>  # prod 33
        <one_d_end2> → = { <elements> }  # prod 34
        <one_d_end2> → λ  # prod 35
        """
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
        """
        <two_d_end> → = { { <elements> } <mult_elem2> }  # prod 36
        <two_d_end> → λ  # prod 37
        """
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
        """<elements> → <value> <mult_elem>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<elements>']):  # prod 38
            self.parse_value()
            if self.stop: return
            self.parse_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<elements>')

    def parse_mult_elem(self):
        """
        <mult_elem> → , <value> <mult_elem>  # prod 39
        <mult_elem> → λ  # prod 40
        """
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
        """
        <mult_elem2> → , { <elements> } <mult_elem2>  # prod 41
        <mult_elem2> → λ  # prod 42
        """
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
        """
        <global_wall_end> → <global_wall_init> <global_mult_wall>  # prod 43
        <global_wall_end> → <wall_array>  # prod 44
        """
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
        """
        <global_wall_init> → = wall_lit  # prod 45
        <global_wall_init> → λ  # prod 46
        """
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
        """
        <global_mult_wall> → , id <global_wall_init> <global_mult_wall>  # prod 47
        <global_mult_wall> → λ  # prod 48
        """
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
        """<wall_array> → [ <wall_size>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_array>']):  # prod 49
            self.match_token('[')
            if self.stop: return
            self.parse_wall_size()
            if self.stop: return
            return
        self.syntax_error('<wall_array>')

    def parse_wall_size(self):
        """
        <wall_size> → ] <wall_one_d_end>  # prod 50
        <wall_size> → tile_lit ] <wall_one_d_end2>  # prod 51
        """
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
        """
        <wall_one_d_end> → [ tile_lit ] = { { <wall_elem> } <wall_mult_elem2> }  # prod 52
        <wall_one_d_end> → = { <wall_elem> }  # prod 53
        """
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
        """
        <wall_one_d_end2> → [ tile_lit ] <wall_two_d_end>  # prod 54
        <wall_one_d_end2> → = { <wall_elem> }  # prod 55
        <wall_one_d_end2> → λ  # prod 56
        """
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
        """
        <wall_two_d_end> → = { { <wall_elem> } <wall_mult_elem2> }  # prod 57
        <wall_two_d_end> → λ  # prod 58
        """
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
        """<wall_elem> → wall_lit <wall_mult_elem>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_elem>']):  # prod 59
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<wall_elem>')

    def parse_wall_mult_elem(self):
        """
        <wall_mult_elem> → , wall_lit <wall_mult_elem>  # prod 60
        <wall_mult_elem> → λ  # prod 61
        """
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
        """
        <wall_mult_elem2> → , { <wall_elem> } <wall_mult_elem2>  # prod 62
        <wall_mult_elem2> → λ  # prod 63
        """
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
        """<structure> → house id <struct_type>"""
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
        """
        <struct_type> → <struct_dec>  # prod 65
        <struct_type> → <struct_var>  # prod 66
        """
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
        """<struct_dec> → { <struct_members> } <struct_id_end>"""
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
        """<struct_members> → <data_type_dec> <array> ; <mult_members>"""
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
        """
        <data_type_dec> → <data_type> id  # prod 69
        <data_type_dec> → wall id  # prod 70
        """
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
        """
        <array> → [ tile_lit ] <array2>  # prod 71
        <array> → λ  # prod 72
        """
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
        """
        <array2> → [ tile_lit ]  # prod 73
        <array2> → λ  # prod 74
        """
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
        """
        <mult_members> → <data_type_dec> <array> ; <mult_members>  # prod 75
        <mult_members> → λ  # prod 76
        """
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
        """
        <struct_id_end> → id <struct_init> <mult_struct_id>  # prod 77
        <struct_id_end> → λ  # prod 78
        """
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
        """
        <struct_init> → = { <struct_elem> }  # prod 79
        <struct_init> → λ  # prod 80
        """
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
        """
        <struct_elem> → <struct_value> <mult_struct_elem>  # prod 81
        <struct_elem> → { <struct_arr_elem> } <mult_struct_elem>  # prod 82
        """
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
        """
        <struct_value> → <value>  # prod 83
        <struct_value> → wall_lit  # prod 84
        """
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
        """
        <mult_struct_elem> → , <struct_elem>  # prod 85
        <mult_struct_elem> → λ  # prod 86
        """
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
        """
        <struct_arr_elem> → <struct_elements>  # prod 87
        <struct_arr_elem> → { <struct_elements> } <struct_mult_elem2>  # prod 88
        """
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
        """<struct_elements> → <struct_value> <struct_mult_elem>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_elements>']):  # prod 89
            self.parse_struct_value()
            if self.stop: return
            self.parse_struct_mult_elem()
            if self.stop: return
            return
        self.syntax_error('<struct_elements>')

    def parse_struct_mult_elem(self):
        """
        <struct_mult_elem> → , <struct_value>  # prod 90
        <struct_mult_elem> → λ  # prod 91
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_mult_elem>']):  # prod 90
            self.match_token(',')
            if self.stop: return
            self.parse_struct_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_mult_elem_1>']):  # prod 91
            return
        self.syntax_error('<struct_mult_elem>')

    def parse_struct_mult_elem2(self):
        """
        <struct_mult_elem2> → , { <struct_elements> } <struct_mult_elem2>  # prod 92
        <struct_mult_elem2> → λ  # prod 93
        """
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
        """
        <mult_struct_id> → , id <struct_init> <mult_struct_id>  # prod 94
        <mult_struct_id> → λ  # prod 95
        """
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
        """<struct_var> → id <struct_init> <mult_struct_id>"""
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
        """<global_const> → cement <global_const_type>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<global_const>']):  # prod 97
            self.match_token('cement')
            if self.stop: return
            self.parse_global_const_type()
            if self.stop: return
            return
        self.syntax_error('<global_const>')

    def parse_global_const_type(self):
        """
        <global_const_type> → <data_type> id <global_const_end>  # prod 98
        <global_const_type> → wall id <g_const_wall_end>  # prod 99
        <global_const_type> → house id id = { <struct_elem> } <global_const_struct>  # prod 100
        """
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
        """
        <global_const_end> → = <value> <global_mult_const>  # prod 101
        <global_const_end> → [ tile_lit ] <global_const_end2>  # prod 102
        """
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
        """
        <global_mult_const> → , id = <value> <global_mult_const>  # prod 103
        <global_mult_const> → λ  # prod 104
        """
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
        """
        <global_const_end2> → = { <elements> }  # prod 105
        <global_const_end2> → [ tile_lit ] = { { <elements> } <mult_elem2> }  # prod 106
        """
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
        """
        <g_const_wall_end> → = wall_lit <g_mult_const_wall>  # prod 107
        <g_const_wall_end> → [ tile_lit ] <g_const_wall_end2>  # prod 108
        """
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
        """
        <g_mult_const_wall> → , id = wall_lit <g_mult_const_wall>  # prod 109
        <g_mult_const_wall> → λ  # prod 110
        """
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
        """
        <g_const_wall_end2> → = { <wall_elem> }  # prod 111
        <g_const_wall_end2> → [ tile_lit ] = { { <wall_elem> } <wall_mult_elem2> }  # prod 112
        """
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
        """
        <global_const_struct> → , id = { <struct_elem> } <global_const_struct>  # prod 113
        <global_const_struct> → λ  # prod 114
        """
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
        """
        <return_type> → <data_type>  # prod 115
        <return_type> → field  # prod 116
        """
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
        """
        <param_list> → <data_type_dec> <mult_param>  # prod 117
        <param_list> → λ  # prod 118
        """
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
        """
        <mult_param> → , <data_type_dec> <mult_param>  # prod 119
        <mult_param> → λ  # prod 120
        """
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
        """
        <func_body> → <local> <func_body2>  # prod 121
        <func_body> → <statement> <func_body2>  # prod 122
        """
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
        """
        <func_body2> → <func_body>  # prod 123
        <func_body2> → λ  # prod 124
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_body2>']):  # prod 123
            self.parse_func_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_body2_1>']):  # prod 124
            return
        self.syntax_error('<func_body2>')

    def parse_local(self):
        """<local> → <declaration> ;"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<local>']):  # prod 125
            self.parse_declaration()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<local>')

    def parse_declaration(self):
        """
        <declaration> → <variable>  # prod 126
        <declaration> → <structure>  # prod 127
        <declaration> → <constant>  # prod 128
        """
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
        """
        <variable> → <data_type> id <var_end>  # prod 129
        <variable> → wall id <wall_end>  # prod 130
        """
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
        """
        <var_end> → <initializer> <mult_var>  # prod 131
        <var_end> → <array_dec>  # prod 132
        """
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
        """
        <initializer> → = <init_value>  # prod 133
        <initializer> → λ  # prod 134
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<initializer>']):  # prod 133
            self.match_token('=')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<initializer_1>']):  # prod 134
            return
        self.syntax_error('<initializer>')

    def parse_mult_var(self):
        """
        <mult_var> → , id <initializer> <mult_var>  # prod 135
        <mult_var> → λ  # prod 136
        """
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
        """
        <wall_end> → <wall_initializer> <mult_wall>  # prod 137
        <wall_end> → <wall_array>  # prod 138
        """
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
        """
        <wall_initializer> → = <wall_init>  # prod 139
        <wall_initializer> → λ  # prod 140
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_initializer>']):  # prod 139
            self.match_token('=')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_initializer_1>']):  # prod 140
            return
        self.syntax_error('<wall_initializer>')

    def parse_wall_init(self):
        """
        <wall_init> → ( <wall_init> )  # prod 141
        <wall_init> → wall_lit <wall_op>  # prod 142
        <wall_init> → brick_lit + wall_lit <wall_op>  # prod 143
        <wall_init> → id <id_type> <wall_op>  # prod 144
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_init>']):  # prod 141
            self.match_token('(')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_init_1>']):  # prod 142
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_init_2>']):  # prod 143
            self.match_token('brick_lit')
            if self.stop: return
            self.match_token('+')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_init_3>']):  # prod 144
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        self.syntax_error('<wall_init>')

    def parse_wall_op(self):
        """
        <wall_op> → + ( <wall_init> )  # prod 145
        <wall_op> → + wall_lit <wall_op>  # prod 146
        <wall_op> → + brick_lit <wall_op>  # prod 147
        <wall_op> → + id <id_type> <wall_op>  # prod 148
        <wall_op> → λ  # prod 149
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<wall_op>']):  # prod 145
            self.match_token('+')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_op_1>']):  # prod 146
            self.match_token('+')
            if self.stop: return
            self.match_token('wall_lit')
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_op_2>']):  # prod 147
            self.match_token('+')
            if self.stop: return
            self.match_token('brick_lit')
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_op_3>']):  # prod 148
            self.match_token('+')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            self.parse_wall_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<wall_op_4>']):  # prod 149
            return
        self.syntax_error('<wall_op>')

    def parse_mult_wall(self):
        """
        <mult_wall> → , id <wall_initializer> <mult_wall>  # prod 150
        <mult_wall> → λ  # prod 151
        """
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
        """<constant> → cement <const_type>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<constant>']):  # prod 152
            self.match_token('cement')
            if self.stop: return
            self.parse_const_type()
            if self.stop: return
            return
        self.syntax_error('<constant>')

    def parse_const_type(self):
        """
        <const_type> → <data_type> id <const_end>  # prod 153
        <const_type> → wall id <const_wall_end>  # prod 154
        <const_type> → house id id = { <struct_elem> } <mult_const_struct>  # prod 155
        """
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
        """
        <const_end> → = <init_value> <mult_const>  # prod 156
        <const_end> → [ tile_lit ] <global_const_end2>  # prod 157
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_end>']):  # prod 156
            self.match_token('=')
            if self.stop: return
            self.parse_init_value()
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
        """
        <mult_const> → , id = <init_value> <mult_const>  # prod 158
        <mult_const> → λ  # prod 159
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_const>']):  # prod 158
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
        elif self.in_predict(PREDICT_SET['<mult_const_1>']):  # prod 159
            return
        self.syntax_error('<mult_const>')

    def parse_const_wall_end(self):
        """
        <const_wall_end> → = <wall_init> <mult_wall>  # prod 160
        <const_wall_end> → [ tile_lit ] <g_const_wall_end2>  # prod 161
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<const_wall_end>']):  # prod 160
            self.match_token('=')
            if self.stop: return
            self.parse_wall_init()
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
        """
        <mult_const_struct> → , id = { <struct_elem> } <mult_const_struct>  # prod 162
        <mult_const_struct> → λ  # prod 163
        """
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
        """
        <init_value> → <value_exp> <exp_op>  # prod 164
        <init_value> → <prefix_op> <id_val> <exp_op>  # prod 165
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<init_value>']):  # prod 164
            self.parse_value_exp()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<init_value_1>']):  # prod 165
            self.parse_prefix_op()
            if self.stop: return
            self.parse_id_val()
            if self.stop: return
            self.parse_exp_op()
            if self.stop: return
            return
        self.syntax_error('<init_value>')

    def parse_value_exp(self):
        """
        <value_exp> → <value_type>  # prod 166
        <value_exp> → <group>  # prod 167
        <value_exp> → - <negative_type>  # prod 168
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value_exp>']):  # prod 166
            self.parse_value_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_exp_1>']):  # prod 167
            self.parse_group()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_exp_2>']):  # prod 168
            self.match_token('-')
            if self.stop: return
            self.parse_negative_type()
            if self.stop: return
            return
        self.syntax_error('<value_exp>')

    def parse_value_type(self):
        """
        <value_type> → id <id_type>  # prod 169
        <value_type> → <value>  # prod 170
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<value_type>']):  # prod 169
            self.match_token('id')
            if self.stop: return
            self.parse_id_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<value_type_1>']):  # prod 170
            self.parse_value()
            if self.stop: return
            return
        self.syntax_error('<value_type>')

    def parse_id_type(self):
        """
        <id_type> → <id_type2>  # prod 171
        <id_type> → λ  # prod 172
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type>']):  # prod 171
            self.parse_id_type2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type_1>']):  # prod 172
            return
        self.syntax_error('<id_type>')

    def parse_id_type2(self):
        """
        <id_type2> → <arr_struct> <postfix_op>  # prod 173
        <id_type2> → <func_call>  # prod 174
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_type2>']):  # prod 173
            self.parse_arr_struct()
            if self.stop: return
            self.parse_postfix_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<id_type2_1>']):  # prod 174
            self.parse_func_call()
            if self.stop: return
            return
        self.syntax_error('<id_type2>')

    def parse_arr_struct(self):
        """
        <arr_struct> → <array_index>  # prod 175
        <arr_struct> → <struct_id>  # prod 176
        <arr_struct> → λ  # prod 177
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<arr_struct>']):  # prod 175
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_struct_1>']):  # prod 176
            self.parse_struct_id()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<arr_struct_2>']):  # prod 177
            return
        self.syntax_error('<arr_struct>')

    def parse_array_index(self):
        """
        <array_index> → [ init_value ] <array_index2>  # prod 178
        <array_index> → λ  # prod 179
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index>']):  # prod 178
            self.match_token('[')
            if self.stop: return
            self.context_stack.append('array_index')
            self.parse_init_value()
            self.context_stack.pop()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            self.parse_array_index2()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index_1>']):  # prod 179
            return
        self.syntax_error('<array_index>')

    def parse_array_index2(self):
        """
        <array_index2> → [ init_value ]  # prod 180
        <array_index2> → λ  # prod 181
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<array_index2>']):  # prod 180
            self.match_token('[')
            if self.stop: return
            self.context_stack.append('array_index')
            self.parse_init_value()
            self.context_stack.pop()
            if self.stop: return
            self.match_token(']')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<array_index2_1>']):  # prod 181
            return
        self.syntax_error('<array_index2>')

    def parse_struct_id(self):
        """
        <struct_id> → . id <array_index>  # prod 182
        <struct_id> → λ  # prod 183
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<struct_id>']):  # prod 182
            self.match_token('.')
            if self.stop: return
            self.match_token('id')
            if self.stop: return
            self.parse_array_index()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<struct_id_1>']):  # prod 183
            return
        self.syntax_error('<struct_id>')

    def parse_func_call(self):
        """
        <func_call> → ( <func_argu> )  # prod 184
        <func_call> → λ  # prod 185
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_call>']):  # prod 184
            self.match_token('(')
            if self.stop: return
            self.parse_func_argu()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_call_1>']):  # prod 185
            return
        self.syntax_error('<func_call>')

    def parse_func_argu(self):
        """
        <func_argu> → <init_value> <func_mult_call>  # prod 186
        <func_argu> → <wall_init> <func_mult_call>  # prod 187
        <func_argu> → λ  # prod 188
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_argu>']):  # prod 186
            self.parse_init_value()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_argu_1>']):  # prod 187
            self.parse_wall_init()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_argu_2>']):  # prod 188
            return
        self.syntax_error('<func_argu>')

    def parse_func_mult_call(self):
        """
        <func_mult_call> → , <init_value> <func_mult_call>  # prod 189
        <func_mult_call> → , <wall_init> <func_mult_call>  # prod 190
        <func_mult_call> → λ  # prod 191
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<func_mult_call>']):  # prod 189
            self.match_token(',')
            if self.stop: return
            self.parse_init_value()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_mult_call_1>']):  # prod 190
            self.match_token(',')
            if self.stop: return
            self.parse_wall_init()
            if self.stop: return
            self.parse_func_mult_call()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<func_mult_call_2>']):  # prod 191
            return
        self.syntax_error('<func_mult_call>')

    def parse_postfix_op(self):
        """
        <postfix_op> → <unary_op>  # prod 192
        <postfix_op> → λ  # prod 193
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<postfix_op>']):  # prod 192
            self.parse_unary_op()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<postfix_op_1>']):  # prod 193
            return
        self.syntax_error('<postfix_op>')

    def parse_unary_op(self):
        """
        <unary_op> → ++  # prod 194
        <unary_op> → --  # prod 195
        """
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
        """<group> → ( <init_value> )"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<group>']):  # prod 196
            self.match_token('(')
            if self.stop: return
            self.context_stack.append('if_condition')
            self.parse_init_value()
            self.context_stack.pop()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            return
        self.syntax_error('<group>')

    def parse_negative_type(self):
        """
        <negative_type> → <value_type>  # prod 197
        <negative_type> → <group>  # prod 198
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<negative_type>']):  # prod 197
            self.parse_value_type()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<negative_type_1>']):  # prod 198
            self.parse_group()
            if self.stop: return
            return
        self.syntax_error('<negative_type>')

    def parse_exp_op(self):
        """
        <exp_op> → <operator> <init_value>  # prod 199
        <exp_op> → λ  # prod 200
        """
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
        """
        <prefix_op> → !  # prod 201
        <prefix_op> → <unary_op>  # prod 202
        """
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

    def parse_id_val(self):
        """<id_val> → id <id_type3>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<id_val>']):  # prod 203
            self.match_token('id')
            if self.stop: return
            self.parse_id_type3()
            if self.stop: return
            return
        self.syntax_error('<id_val>')

    def parse_id_type3(self):
        """
        <id_type3> → <array_index>  # prod 204
        <id_type3> → <struct_id>  # prod 205
        <id_type3> → λ  # prod 206
        """
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
        """
        <operator> → +  # prod 207
        <operator> → -  # prod 208
        <operator> → *  # prod 209
        <operator> → /  # prod 210
        <operator> → %  # prod 211
        <operator> → <  # prod 212
        <operator> → <=  # prod 213
        <operator> → >  # prod 214
        <operator> → >=  # prod 215
        <operator> → ==  # prod 216
        <operator> → !=  # prod 217
        <operator> → &&  # prod 218
        <operator> → ||  # prod 219
        """
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
        """
        <statement> → <io_statement>  # prod 220
        <statement> → <assign_statement>  # prod 221
        <statement> → <if_statement>  # prod 222
        <statement> → <switch_statement>  # prod 223
        <statement> → <for_statement>  # prod 224
        <statement> → <while_statement>  # prod 225
        <statement> → <dowhile_statement>  # prod 226
        <statement> → <break_statement>  # prod 227
        <statement> → <continue_statement>  # prod 228
        <statement> → <return_statement>  # prod 229
        """
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
        """
        <io_statement> → write ( wall_lit , <write_argu> ) ;  # prod 230
        <io_statement> → view ( wall_lit <view_argu> ) ;  # prod 231
        """
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
        """
        <write_argu> → & <id_val> <mult_write_argu>  # prod 232
        <write_argu> → <id_val> <mult_write_argu>  # prod 233
        """
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
        """
        <mult_write_argu> → , <write_argu>  # prod 234
        <mult_write_argu> → λ  # prod 235
        """
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
        """
        <view_argu> → , <home_value> <mult_view_argu>  # prod 236
        <view_argu> → λ  # prod 237
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<view_argu>']):  # prod 236
            self.match_token(',')
            if self.stop: return
            self.parse_home_value()
            if self.stop: return
            self.parse_mult_view_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<view_argu_1>']):  # prod 237
            return
        self.syntax_error('<view_argu>')

    def parse_mult_view_argu(self):
        """
        <mult_view_argu> → <view_argu>  # prod 238
        <mult_view_argu> → λ  # prod 239
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_view_argu>']):  # prod 238
            self.parse_view_argu()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_view_argu_1>']):  # prod 239
            return
        self.syntax_error('<mult_view_argu>')

    def parse_assign_statement(self):
        """
        <assign_statement> → <unary_op> id ;  # prod 240
        <assign_statement> → id <id_type4> ;  # prod 241
        """
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
        """
        <id_type4> → ( <func_argu> )  # prod 242
        <id_type4> → <unary_op>  # prod 243
        <id_type4> → <id_type3> <assign_op> <assign_value>  # prod 244
        """
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
        """
        <assign_value> → <init_value>  # prod 245
        <assign_value> → <wall_init>  # prod 246
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_value>']):  # prod 245
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_value_1>']):  # prod 246
            self.parse_wall_init()
            if self.stop: return
            return
        self.syntax_error('<assign_value>')

    def parse_assign_op(self):
        """
        <assign_op> → =  # prod 247
        <assign_op> → +=  # prod 248
        <assign_op> → -=  # prod 249
        <assign_op> → *=  # prod 250
        <assign_op> → /=  # prod 251
        <assign_op> → %=  # prod 252
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<assign_op>']):  # prod 247
            self.match_token('=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_1>']):  # prod 248
            self.match_token('+=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_2>']):  # prod 249
            self.match_token('-=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_3>']):  # prod 250
            self.match_token('*=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_4>']):  # prod 251
            self.match_token('/=')
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<assign_op_5>']):  # prod 252
            self.match_token('%=')
            if self.stop: return
            return
        self.syntax_error('<assign_op>')

    def parse_if_statement(self):
        """<if_statement> → if ( <init_value> ) { <func_body> } <else_statement>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<if_statement>']):  # prod 253
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
        """
        <else_statement> → else <else_statement2>  # prod 254
        <else_statement> → λ  # prod 255
        """
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
        """
        <else_statement2> → <if_statement>  # prod 256
        <else_statement2> → { <func_body> }  # prod 257
        """
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
        """<switch_statement> → room ( <init_value> ) { <switch_body> }"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<switch_statement>']):  # prod 258
            self.match_token('room')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.context_stack.append('switch_condition')
            self.parse_init_value()
            self.context_stack.pop()
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
        """
        <switch_body> → door <case_exp> : <case_body> <mult_switch_body>  # prod 259
        <switch_body> → ground : <case_body>  # prod 260
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<switch_body>']):  # prod 259
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
        elif self.in_predict(PREDICT_SET['<switch_body_1>']):  # prod 260
            self.match_token('ground')
            if self.stop: return
            self.match_token(':')
            if self.stop: return
            self.parse_case_body()
            if self.stop: return
            return
        self.syntax_error('<switch_body>')

    def parse_mult_switch_body(self):
        """
        <mult_switch_body> → <switch_body>  # prod 261
        <mult_switch_body> → λ  # prod 262
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_switch_body>']):  # prod 261
            self.parse_switch_body()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_switch_body_1>']):  # prod 262
            return
        self.syntax_error('<mult_switch_body>')

    def parse_case_exp(self):
        """<case_exp> → <case_type> <case_op>"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_exp>']):  # prod 263
            self.parse_case_type()
            if self.stop: return
            self.parse_case_op()
            if self.stop: return
            return
        self.syntax_error('<case_exp>')

    def parse_case_type(self):
        """
        <case_type> → <case_val>  # prod 264
        <case_type> → <case_group>  # prod 265
        <case_type> → - <case_negative>  # prod 266
        """
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
        """
        <case_val> → tile_lit  # prod 267
        <case_val> → brick_lit  # prod 268
        <case_val> → solid  # prod 269
        <case_val> → fragile  # prod 270
        """
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
        """<case_group> → ( <case_exp> )"""
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
        """
        <case_negative> → <case_val>  # prod 272
        <case_negative> → <case_group>  # prod 273
        """
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
        """
        <case_op> → <operator> <case_exp>  # prod 274
        <case_op> → λ  # prod 275
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<case_op>']):  # prod 274
            self.parse_operator()
            if self.stop: return
            self.parse_case_exp()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<case_op_1>']):  # prod 275
            return
        self.syntax_error('<case_op>')

    def parse_case_body(self):
        """
        <case_body> → <statement> <mult_smt>  # prod 276
        <case_body> → { <func_body> }  # prod 277
        <case_body> → λ  # prod 278
        """
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
        """
        <mult_smt> → <statement>  # prod 279
        <mult_smt> → λ  # prod 280
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<mult_smt>']):  # prod 279
            self.parse_statement()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<mult_smt_1>']):  # prod 280
            return
        self.syntax_error('<mult_smt>')

    def parse_for_statement(self):
        """<for_statement> → for ( <for_dec> ; <init_value> ; <init_value> ) { <func_body> }"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<for_statement>']):  # prod 281
            self.match_token('for')
            if self.stop: return
            self.match_token('(')
            if self.stop: return
            self.context_stack.append('for_declaration')
            self.parse_for_dec()
            self.context_stack.pop()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.context_stack.append('for_condition')
            self.parse_init_value()
            self.context_stack.pop()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            self.context_stack.append('for_increment')
            self.parse_init_value()
            self.context_stack.pop()
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
        """
        <for_dec> → <data_type> id <initializer>  # prod 282
        <for_dec> → id <initializer>  # prod 283
        """
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
        """<while_statement> → while ( <init_value> ) { <func_body> }"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<while_statement>']):  # prod 284
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
        """<dowhile_statement> → do { <func_body> } while ( <init_value> ) ;"""
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
            self.context_stack.append('dowhile_condition')
            self.parse_init_value()
            self.context_stack.pop()
            if self.stop: return
            self.match_token(')')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<dowhile_statement>')

    def parse_break_statement(self):
        """<break_statement> → crack ;"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<break_statement>']):  # prod 286
            self.match_token('crack')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<break_statement>')

    def parse_continue_statement(self):
        """<continue_statement> → mend ;"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<continue_statement>']):  # prod 287
            self.match_token('mend')
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<continue_statement>')

    def parse_return_statement(self):
        """<return_statement> → home <home_value> ;"""
        if self.stop: return
        if self.in_predict(PREDICT_SET['<return_statement>']):  # prod 288
            self.match_token('home')
            if self.stop: return
            self.parse_home_value()
            if self.stop: return
            self.match_token(';')
            if self.stop: return
            return
        self.syntax_error('<return_statement>')

    def parse_home_value(self):
        """
        <home_value> → <init_value>  # prod 289
        <home_value> → <wall_init>  # prod 290
        """
        if self.stop: return
        if self.in_predict(PREDICT_SET['<home_value>']):  # prod 289
            self.parse_init_value()
            if self.stop: return
            return
        elif self.in_predict(PREDICT_SET['<home_value_1>']):  # prod 290
            self.parse_wall_init()
            if self.stop: return
            return
        self.syntax_error('<home_value>')