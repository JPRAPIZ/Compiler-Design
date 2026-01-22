from parser.predict_set import PREDICT_SET

class Parser:

    IGNORE_TYPES = ("space", "tab", "newline", "Single-Line Comment", "Multi-Line Comment")

    def __init__(self, tokens):
        self.tokens = [t for t in (tokens or []) if t.tokenType not in self.IGNORE_TYPES]
        self.index = 0
        self.last_index = len(self.tokens) - 1

        self.current_type = "EOF"
        self.current_lexeme = "$"
        self.current_line = 1
        self.current_col = 1

        self.matched_tokens = []

        self.errors = []
        self.stop = False

        self.update_current()

    def expected_tokens(self, nonterminal: str) -> list[str]:
        # union of PREDICT sets
        base = nonterminal[1:-1]
        out: list[str] = []
        for key, toks in PREDICT_SET.items():
            key_base = key[1:-1]
            if key_base == base:
                for t in toks:
                    if t not in out:
                        out.append(t)
                continue
            if key_base.startswith(base + "_"):
                suffix = key_base[len(base) + 1 :]
                if suffix.isdigit():
                    for t in toks:
                        if t not in out:
                            out.append(t)
        return out


    def update_current(self):
        if self.last_index < 0 or self.index > self.last_index:
            self.current_type = "EOF"
            self.current_lexeme = "$"
            return

        t = self.tokens[self.index]
        tok_type = t.tokenType
        if isinstance(tok_type, str) and tok_type.startswith("id"):
            tok_type = "id"

        self.current_type = tok_type
        self.current_lexeme = t.lexeme
        self.current_line = t.line
        self.current_col = t.column

    def consume(self):
        if self.stop:
            return
        if self.index <= self.last_index:
            self.matched_tokens.append(self.tokens[self.index])
            self.index += 1
        self.update_current()

    def checkpoint(self):
        return (self.index, len(self.errors), len(self.matched_tokens))

    def rollback(self, cp):
        self.index = cp[0]
        self.errors = self.errors[:cp[1]]
        self.matched_tokens = self.matched_tokens[:cp[2]]
        self.stop = False
        self.update_current()

    def lookahead(self) -> str:
        return self.current_type

    def in_predict(self, predict_list: list[str]) -> bool:
        return self.lookahead() in (predict_list or [])

    def match_token(self, expected_type: str):
        if self.stop:
            return
        if self.current_type == expected_type:
            self.consume()
            return
        self.add_error(
            f"Unexpected Character {self.current_lexeme!r}; expected one of {[expected_type]!r}"
        )

    def add_error(self, message: str):
        if self.stop:
            return
        line = self.current_line
        col = self.current_col
        width = max(1, len(str(self.current_lexeme)))
        self.errors.append({
            "message": message,
            "line": line, "col": col,
            "start_line": line, "start_col": col,
            "end_line": line, "end_col": col + width,
        })
        self.stop = True

    def syntax_error(self, nonterminal: str):
        expected = self.expected_tokens(nonterminal)
        got = self.current_lexeme
        self.add_error(f"Unexpected Character {got!r}; expected one of {expected}")

    def parse(self):
        if not self.tokens:
            self.current_type = "EOF"
            self.current_lexeme = "$"
            self.current_line = 1
            self.current_col = 1
            self.syntax_error("<program>")
            return self.errors

        self.parse_program()

        if not self.stop and self.current_type != "EOF":
            self.add_error(
                f"Unexpected Character {self.current_lexeme!r}; expected one of {['EOF']!r}"
            )

        return self.errors

    def parse_program(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        if self.in_predict(PREDICT_SET['<program>']):  # prod 1
            cp = self.checkpoint()
            self.parse_global()
            self.parse_function()
            self.parse_main_type()
            self.match_token('blueprint')
            self.match_token('(')
            self.match_token(')')
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<program>')

    def parse_global(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global>']):  # prod 2
            cp = self.checkpoint()
            self.match_token('roof')
            self.parse_global_dec()
            self.match_token(';')
            self.parse_global()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_1>']):  # prod 3
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global>')

    def parse_global_dec(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
         
        if self.in_predict(PREDICT_SET['<global_dec>']):  # prod 4
            cp = self.checkpoint()
            self.parse_global_var()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_dec_1>']):  # prod 5
            cp = self.checkpoint()
            self.parse_structure()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_dec_2>']):  # prod 6
            cp = self.checkpoint()
            self.parse_global_const()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_dec>')

    def parse_global_var(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
         
        if self.in_predict(PREDICT_SET['<global_var>']):  # prod 7
            cp = self.checkpoint()
            self.parse_data_type()
            self.match_token('id')
            self.parse_global_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_var>')

    def parse_data_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<data_type>']):  # prod 8
            cp = self.checkpoint()
            self.match_token('tile')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<data_type_1>']):  # prod 9
            cp = self.checkpoint()
            self.match_token('glass')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<data_type_2>']):  # prod 10
            cp = self.checkpoint()
            self.match_token('brick')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<data_type_3>']):  # prod 11
            cp = self.checkpoint()
            self.match_token('wall')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<data_type_4>']):  # prod 12
            cp = self.checkpoint()
            self.match_token('beam')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<data_type>')

    def parse_global_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_end>']):  # prod 13
            cp = self.checkpoint()
            self.parse_global_init()
            self.parse_global_mult()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_end_1>']):  # prod 14
            cp = self.checkpoint()
            self.parse_array_dec()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_end>')

    def parse_global_init(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_init>']):  # prod 15
            cp = self.checkpoint()
            self.match_token('=')
            self.parse_value()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_init_1>']):  # prod 16
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_init>')

    def parse_global_mult(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_mult>']):  # prod 17
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.parse_global_init()
            self.parse_global_mult()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_mult_1>']):  # prod 18
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_mult>')

    def parse_value(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<value>']):  # prod 19
            cp = self.checkpoint()
            self.match_token('tile_lit')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_1>']):  # prod 20
            cp = self.checkpoint()
            self.match_token('glass_lit')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_2>']):  # prod 21
            cp = self.checkpoint()
            self.match_token('brick_lit')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_3>']):  # prod 22
            cp = self.checkpoint()
            self.match_token('wall_lit')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_4>']):  # prod 23
            cp = self.checkpoint()
            self.match_token('solid')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_5>']):  # prod 24
            cp = self.checkpoint()
            self.match_token('fragile')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<value>')

    def parse_array_dec(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<array_dec>']):  # prod 25
            cp = self.checkpoint()
            self.match_token('[')
            self.parse_arr_size()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<array_dec>')

    def parse_arr_size(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<arr_size>']):  # prod 26
            cp = self.checkpoint()
            self.match_token(']')
            self.parse_one_d_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<arr_size_1>']):  # prod 27
            cp = self.checkpoint()
            self.match_token('tile_lit')
            self.match_token(']')
            self.parse_one_d_end2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<arr_size>')

    def parse_one_d_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<one_d_end>']):  # prod 28
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.match_token('=')
            self.match_token('{')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            self.parse_mult_elem2()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<one_d_end_1>']):  # prod 29
            cp = self.checkpoint()
            self.match_token('=')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<one_d_end>')

    def parse_one_d_end2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<one_d_end2>']):  # prod 30
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.parse_two_d_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<one_d_end2_1>']):  # prod 31
            cp = self.checkpoint()
            self.match_token('=')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<one_d_end2_2>']):  # prod 32
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<one_d_end2>')

    def parse_two_d_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<two_d_end>']):  # prod 33
            cp = self.checkpoint()
            self.match_token('=')
            self.match_token('{')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            self.parse_mult_elem2()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<two_d_end_1>']):  # prod 34
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<two_d_end>')

    def parse_elements(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<elements>']):  # prod 35
            cp = self.checkpoint()
            self.parse_value()
            self.parse_mult_elem()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<elements>')

    def parse_mult_elem(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_elem>']):  # prod 36
            cp = self.checkpoint()
            self.match_token(',')
            self.parse_value()
            self.parse_mult_elem()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_elem_1>']):  # prod 37
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_elem>')

    def parse_mult_elem2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_elem2>']):  # prod 38
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            self.parse_mult_elem2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_elem2_1>']):  # prod 39
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_elem2>')

    def parse_structure(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<structure>']):  # prod 40
            cp = self.checkpoint()
            self.match_token('house')
            self.match_token('id')
            self.parse_struct_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<structure>')

    def parse_struct_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_type>']):  # prod 41
            cp = self.checkpoint()
            self.parse_struct_dec()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<struct_type_1>']):  # prod 42
            cp = self.checkpoint()
            self.parse_struct_var()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_type>')

    def parse_struct_dec(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_dec>']):  # prod 43
            cp = self.checkpoint()
            self.match_token('{')
            self.parse_struct_members()
            self.match_token('}')
            self.parse_struct_id_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_dec>')

    def parse_struct_members(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_members>']):  # prod 44
            cp = self.checkpoint()
            self.parse_data_type_dec()
            self.parse_array()
            self.match_token(';')
            self.parse_mult_members()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_members>')

    def parse_data_type_dec(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<data_type_dec>']):  # prod 45
            cp = self.checkpoint()
            self.parse_data_type()
            self.match_token('id')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<data_type_dec>')

    def parse_array(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<array>']):  # prod 46
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.parse_array2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<array_1>']):  # prod 47
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<array>')

    def parse_array2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<array2>']):  # prod 48
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<array2_1>']):  # prod 49
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<array2>')

    def parse_mult_members(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_members>']):  # prod 50
            cp = self.checkpoint()
            self.parse_data_type_dec()
            self.parse_array()
            self.match_token(';')
            self.parse_mult_members()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_members_1>']):  # prod 51
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_members>')

    def parse_struct_id_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_id_end>']):  # prod 52
            cp = self.checkpoint()
            self.match_token('id')
            self.parse_struct_init()
            self.parse_mult_struct_id()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<struct_id_end_1>']):  # prod 53
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_id_end>')

    def parse_struct_init(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_init>']):  # prod 54
            cp = self.checkpoint()
            self.match_token('=')
            self.match_token('{')
            self.parse_struct_elem()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<struct_init_1>']):  # prod 55
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_init>')

    def parse_struct_elem(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_elem>']):  # prod 56
            cp = self.checkpoint()
            self.parse_value()
            self.parse_mult_struct_elem()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<struct_elem_1>']):  # prod 57
            cp = self.checkpoint()
            self.match_token('{')
            self.parse_struct_arr_elem()
            self.match_token('}')
            self.parse_mult_struct_elem()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_elem>')

    def parse_struct_arr_elem(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_arr_elem>']):  # prod 58
            cp = self.checkpoint()
            self.parse_elements()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<struct_arr_elem_1>']):  # prod 59
            cp = self.checkpoint()
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            self.parse_mult_elem2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_arr_elem>')

    def parse_mult_struct_elem(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_struct_elem>']):  # prod 60
            cp = self.checkpoint()
            self.match_token(',')
            self.parse_struct_elem()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_struct_elem_1>']):  # prod 61
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_struct_elem>')

    def parse_mult_struct_id(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_struct_id>']):  # prod 62
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.parse_struct_init()
            self.parse_mult_struct_id()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_struct_id_1>']):  # prod 63
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_struct_id>')

    def parse_struct_var(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_var>']):  # prod 64
            cp = self.checkpoint()
            self.match_token('id')
            self.parse_struct_init()
            self.parse_mult_struct_id()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_var>')

    def parse_global_const(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_const>']):  # prod 65
            cp = self.checkpoint()
            self.match_token('cement')
            self.parse_global_const_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_const>')

    def parse_global_const_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_const_type>']):  # prod 66
            cp = self.checkpoint()
            self.parse_data_type()
            self.match_token('id')
            self.parse_global_const_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_const_type_1>']):  # prod 67
            cp = self.checkpoint()
            self.match_token('house')
            self.match_token('id')
            self.match_token('id')
            self.match_token('=')
            self.match_token('{')
            self.parse_struct_elem()
            self.match_token('}')
            self.parse_global_const_struct()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_const_type>')

    def parse_global_const_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_const_end>']):  # prod 68
            cp = self.checkpoint()
            self.match_token('=')
            self.parse_value()
            self.parse_global_mult_const()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_const_end_1>']):  # prod 69
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.parse_global_const_end2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_const_end>')

    def parse_global_const_end2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_const_end2>']):  # prod 70
            cp = self.checkpoint()
            self.match_token('=')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_const_end2_1>']):  # prod 71
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.match_token('=')
            self.match_token('{')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            self.parse_mult_elem2()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_const_end2>')

    def parse_global_mult_const(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_mult_const>']):  # prod 72
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.match_token('=')
            self.parse_value()
            self.parse_global_mult_const()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_mult_const_1>']):  # prod 73
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_mult_const>')

    def parse_global_const_struct(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<global_const_struct>']):  # prod 74
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.match_token('=')
            self.match_token('{')
            self.parse_struct_elem()
            self.match_token('}')
            self.parse_global_const_struct()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<global_const_struct_1>']):  # prod 75
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<global_const_struct>')

    def parse_function(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<function>']):  # prod 76
            cp = self.checkpoint()
            self.parse_return_type()
            self.match_token('id')
            self.match_token('(')
            self.parse_param_list()
            self.match_token(')')
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<function_1>']):  # prod 77
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<function>')

    def parse_return_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<return_type>']):  # prod 78
            cp = self.checkpoint()
            self.parse_data_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<return_type_1>']):  # prod 79
            cp = self.checkpoint()
            self.match_token('field')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<return_type>')

    def parse_param_list(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<param_list>']):  # prod 80
            cp = self.checkpoint()
            self.parse_data_type_dec()
            self.parse_mult_param()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<param_list_1>']):  # prod 81
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<param_list>')

    def parse_mult_param(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_param>']):  # prod 82
            cp = self.checkpoint()
            self.match_token(',')
            self.parse_data_type_dec()
            self.parse_mult_param()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_param_1>']):  # prod 83
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_param>')

    def parse_func_body(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<func_body>']):  # prod 84
            cp = self.checkpoint()
            self.parse_local()
            self.parse_func_body2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<func_body_1>']):  # prod 85
            cp = self.checkpoint()
            self.parse_statement()
            self.parse_func_body2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<func_body>')

    def parse_func_body2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<func_body2>']):  # prod 86
            cp = self.checkpoint()
            self.parse_func_body()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<func_body2_1>']):  # prod 87
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<func_body2>')

    def parse_local(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<local>']):  # prod 88
            cp = self.checkpoint()
            self.parse_declaration()
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<local>')

    def parse_declaration(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<declaration>']):  # prod 89
            cp = self.checkpoint()
            self.parse_variable()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<declaration_1>']):  # prod 90
            cp = self.checkpoint()
            self.parse_structure()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<declaration_2>']):  # prod 91
            cp = self.checkpoint()
            self.parse_constant()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<declaration>')

    def parse_variable(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<variable>']):  # prod 92
            cp = self.checkpoint()
            self.parse_data_type()
            self.match_token('id')
            self.parse_var_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<variable>')

    def parse_var_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<var_end>']):  # prod 93
            cp = self.checkpoint()
            self.parse_initializer()
            self.parse_mult_var()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<var_end_1>']):  # prod 94
            cp = self.checkpoint()
            self.parse_array_dec()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<var_end>')

    def parse_initializer(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<initializer>']):  # prod 95
            cp = self.checkpoint()
            self.match_token('=')
            self.parse_init_value()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<initializer_1>']):  # prod 96
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<initializer>')

    def parse_mult_var(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_var>']):  # prod 97
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.parse_initializer()
            self.parse_mult_var()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_var_1>']):  # prod 98
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_var>')

    def parse_constant(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<constant>']):  # prod 99
            cp = self.checkpoint()
            self.match_token('cement')
            self.parse_const_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<constant>')

    def parse_const_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<const_type>']):  # prod 100
            cp = self.checkpoint()
            self.parse_data_type()
            self.match_token('id')
            self.parse_const_end()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<const_type_1>']):  # prod 101
            cp = self.checkpoint()
            self.match_token('house')
            self.match_token('id')
            self.match_token('id')
            self.match_token('=')
            self.match_token('{')
            self.parse_struct_elem()
            self.match_token('}')
            self.parse_mult_const_struct()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<const_type>')

    def parse_const_end(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<const_end>']):  # prod 102
            cp = self.checkpoint()
            self.match_token('=')
            self.parse_init_value()
            self.parse_mult_const()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<const_end_1>']):  # prod 103
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.parse_const_end2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<const_end>')

    def parse_const_end2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<const_end2>']):  # prod 104
            cp = self.checkpoint()
            self.match_token('=')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<const_end2_1>']):  # prod 105
            cp = self.checkpoint()
            self.match_token('[')
            self.match_token('tile_lit')
            self.match_token(']')
            self.match_token('=')
            self.match_token('{')
            self.match_token('{')
            self.parse_elements()
            self.match_token('}')
            self.parse_mult_elem2()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<const_end2>')

    def parse_mult_const(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_const>']):  # prod 106
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.match_token('=')
            self.parse_init_value()
            self.parse_mult_const()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_const_1>']):  # prod 107
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_const>')

    def parse_mult_const_struct(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_const_struct>']):  # prod 108
            cp = self.checkpoint()
            self.match_token(',')
            self.match_token('id')
            self.match_token('=')
            self.match_token('{')
            self.parse_struct_elem()
            self.match_token('}')
            self.parse_mult_const_struct()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_const_struct_1>']):  # prod 109
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_const_struct>')

    def parse_init_value(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<init_value>']):  # prod 110
            cp = self.checkpoint()
            self.parse_value_exp()
            self.parse_exp_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<init_value_1>']):  # prod 111
            cp = self.checkpoint()
            self.parse_prefix_op()
            self.parse_id_val()
            self.parse_exp_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<init_value>')

    def parse_value_exp(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<value_exp>']):  # prod 112
            cp = self.checkpoint()
            self.parse_value_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_exp_1>']):  # prod 113
            cp = self.checkpoint()
            self.parse_group()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_exp_2>']):  # prod 114
            cp = self.checkpoint()
            self.match_token('-')
            self.parse_negative_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<value_exp>')

    def parse_value_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<value_type>']):  # prod 115
            cp = self.checkpoint()
            self.match_token('id')
            self.parse_id_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<value_type_1>']):  # prod 116
            cp = self.checkpoint()
            self.parse_value()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<value_type>')

    def parse_id_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<id_type>']):  # prod 117
            cp = self.checkpoint()
            self.parse_id_type2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<id_type_1>']):  # prod 118
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<id_type>')

    def parse_id_type2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<id_type2>']):  # prod 119
            cp = self.checkpoint()
            self.parse_arr_struct()
            self.parse_postfix_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<id_type2_1>']):  # prod 120
            cp = self.checkpoint()
            self.parse_func_call()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<id_type2>')

    def parse_arr_struct(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<arr_struct>']):  # prod 121
            cp = self.checkpoint()
            self.parse_array_index()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<arr_struct_1>']):  # prod 122
            cp = self.checkpoint()
            self.parse_struct_id()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<arr_struct_2>']):  # prod 123
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<arr_struct>')

    def parse_array_index(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<array_index>']):  # prod 124
            cp = self.checkpoint()
            self.match_token('[')
            self.parse_init_value()
            self.match_token(']')
            self.parse_array_index2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<array_index_1>']):  # prod 125
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<array_index>')

    def parse_array_index2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<array_index2>']):  # prod 126
            cp = self.checkpoint()
            self.match_token('[')
            self.parse_init_value()
            self.match_token(']')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<array_index2_1>']):  # prod 127
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<array_index2>')

    def parse_struct_id(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<struct_id>']):  # prod 128
            cp = self.checkpoint()
            self.match_token('.')
            self.match_token('id')
            self.parse_array_index()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<struct_id_1>']):  # prod 129
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<struct_id>')

    def parse_func_call(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<func_call>']):  # prod 130
            cp = self.checkpoint()
            self.match_token('(')
            self.parse_func_argu()
            self.match_token(')')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<func_call_1>']):  # prod 131
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<func_call>')

    def parse_func_argu(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<func_argu>']):  # prod 132
            cp = self.checkpoint()
            self.parse_init_value()
            self.parse_func_mult_call()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<func_argu_1>']):  # prod 133
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<func_argu>')

    def parse_func_mult_call(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<func_mult_call>']):  # prod 134
            cp = self.checkpoint()
            self.match_token(',')
            self.parse_init_value()
            self.parse_func_mult_call()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<func_mult_call_1>']):  # prod 135
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<func_mult_call>')

    def parse_postfix_op(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<postfix_op>']):  # prod 136
            cp = self.checkpoint()
            self.parse_unary_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<postfix_op_1>']):  # prod 137
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<postfix_op>')

    def parse_unary_op(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<unary_op>']):  # prod 138
            cp = self.checkpoint()
            self.match_token('++')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<unary_op_1>']):  # prod 139
            cp = self.checkpoint()
            self.match_token('--')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<unary_op>')

    def parse_group(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<group>']):  # prod 140
            cp = self.checkpoint()
            self.match_token('(')
            self.parse_init_value()
            self.match_token(')')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<group>')

    def parse_negative_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<negative_type>']):  # prod 141
            cp = self.checkpoint()
            self.parse_value_type()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<negative_type_1>']):  # prod 142
            cp = self.checkpoint()
            self.parse_group()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<negative_type>')

    def parse_exp_op(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<exp_op>']):  # prod 143
            cp = self.checkpoint()
            self.parse_operator()
            self.parse_init_value()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<exp_op_1>']):  # prod 144
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<exp_op>')

    def parse_prefix_op(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<prefix_op>']):  # prod 145
            cp = self.checkpoint()
            self.match_token('!')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<prefix_op_1>']):  # prod 146
            cp = self.checkpoint()
            self.parse_unary_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<prefix_op>')

    def parse_id_val(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<id_val>']):  # prod 147
            cp = self.checkpoint()
            self.match_token('id')
            self.parse_id_type3()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<id_val>')

    def parse_id_type3(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<id_type3>']):  # prod 148
            cp = self.checkpoint()
            self.parse_array_index()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<id_type3_1>']):  # prod 149
            cp = self.checkpoint()
            self.parse_struct_id()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<id_type3_2>']):  # prod 150
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<id_type3>')

    def parse_operator(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<operator>']):  # prod 151
            cp = self.checkpoint()
            self.match_token('+')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_1>']):  # prod 152
            cp = self.checkpoint()
            self.match_token('-')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_2>']):  # prod 153
            cp = self.checkpoint()
            self.match_token('*')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_3>']):  # prod 154
            cp = self.checkpoint()
            self.match_token('/')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_4>']):  # prod 155
            cp = self.checkpoint()
            self.match_token('%')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_5>']):  # prod 156
            cp = self.checkpoint()
            self.match_token('<')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_6>']):  # prod 157
            cp = self.checkpoint()
            self.match_token('<=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_7>']):  # prod 158
            cp = self.checkpoint()
            self.match_token('>')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_8>']):  # prod 159
            cp = self.checkpoint()
            self.match_token('>=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_9>']):  # prod 160
            cp = self.checkpoint()
            self.match_token('==')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_10>']):  # prod 161
            cp = self.checkpoint()
            self.match_token('!=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_11>']):  # prod 162
            cp = self.checkpoint()
            self.match_token('&&')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<operator_12>']):  # prod 163
            cp = self.checkpoint()
            self.match_token('||')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<operator>')

    def parse_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<statement>']):  # prod 164
            cp = self.checkpoint()
            self.parse_io_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_1>']):  # prod 165
            cp = self.checkpoint()
            self.parse_assign_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_2>']):  # prod 166
            cp = self.checkpoint()
            self.parse_if_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_3>']):  # prod 167
            cp = self.checkpoint()
            self.parse_switch_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_4>']):  # prod 168
            cp = self.checkpoint()
            self.parse_for_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_5>']):  # prod 169
            cp = self.checkpoint()
            self.parse_while_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_6>']):  # prod 170
            cp = self.checkpoint()
            self.parse_dowhile_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_7>']):  # prod 171
            cp = self.checkpoint()
            self.parse_break_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_8>']):  # prod 172
            cp = self.checkpoint()
            self.parse_continue_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<statement_9>']):  # prod 173
            cp = self.checkpoint()
            self.parse_return_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<statement>')

    def parse_io_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<io_statement>']):  # prod 174
            cp = self.checkpoint()
            self.match_token('write')
            self.match_token('(')
            self.match_token('wall_lit')
            self.match_token(',')
            self.parse_write_argu()
            self.match_token(')')
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<io_statement_1>']):  # prod 175
            cp = self.checkpoint()
            self.match_token('view')
            self.match_token('(')
            self.match_token('wall_lit')
            self.parse_view_argu()
            self.match_token(')')
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<io_statement>')

    def parse_write_argu(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<write_argu>']):  # prod 176
            cp = self.checkpoint()
            self.match_token('&')
            self.parse_id_val()
            self.parse_mult_write_argu()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<write_argu_1>']):  # prod 177
            cp = self.checkpoint()
            self.parse_id_val()
            self.parse_mult_write_argu()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<write_argu>')

    def parse_mult_write_argu(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_write_argu>']):  # prod 178
            cp = self.checkpoint()
            self.match_token(',')
            self.parse_write_argu()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_write_argu_1>']):  # prod 179
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_write_argu>')

    def parse_view_argu(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<view_argu>']):  # prod 180
            cp = self.checkpoint()
            self.match_token(',')
            self.parse_init_value()
            self.parse_mult_view_argu()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<view_argu_1>']):  # prod 181
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<view_argu>')

    def parse_mult_view_argu(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_view_argu>']):  # prod 182
            cp = self.checkpoint()
            self.parse_view_argu()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_view_argu_1>']):  # prod 183
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_view_argu>')

    def parse_assign_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<assign_statement>']):  # prod 184
            cp = self.checkpoint()
            self.parse_unary_op()
            self.match_token('id')
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<assign_statement_1>']):  # prod 185
            cp = self.checkpoint()
            self.match_token('id')
            self.parse_id_type4()
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<assign_statement>')

    def parse_id_type4(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<id_type4>']):  # prod 186
            cp = self.checkpoint()
            self.match_token('(')
            self.parse_func_argu()
            self.match_token(')')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<id_type4_1>']):  # prod 187
            cp = self.checkpoint()
            self.parse_unary_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<id_type4_2>']):  # prod 188
            cp = self.checkpoint()
            self.parse_id_type3()
            self.parse_assign_op()
            self.parse_init_value()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<id_type4>')

    def parse_assign_op(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<assign_op>']):  # prod 189
            cp = self.checkpoint()
            self.match_token('=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<assign_op_1>']):  # prod 190
            cp = self.checkpoint()
            self.match_token('+=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<assign_op_2>']):  # prod 191
            cp = self.checkpoint()
            self.match_token('-=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<assign_op_3>']):  # prod 192
            cp = self.checkpoint()
            self.match_token('*=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<assign_op_4>']):  # prod 193
            cp = self.checkpoint()
            self.match_token('/=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<assign_op_5>']):  # prod 194
            cp = self.checkpoint()
            self.match_token('%=')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<assign_op>')

    def parse_if_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<if_statement>']):  # prod 195
            cp = self.checkpoint()
            self.match_token('if')
            self.match_token('(')
            self.parse_init_value()
            self.match_token(')')
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            self.parse_else_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<if_statement>')

    def parse_else_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<else_statement>']):  # prod 196
            cp = self.checkpoint()
            self.match_token('else')
            self.parse_else_statement2()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<else_statement_1>']):  # prod 197
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<else_statement>')

    def parse_else_statement2(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<else_statement2>']):  # prod 198
            cp = self.checkpoint()
            self.parse_if_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<else_statement2_1>']):  # prod 199
            cp = self.checkpoint()
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<else_statement2>')

    def parse_switch_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<switch_statement>']):  # prod 200
            cp = self.checkpoint()
            self.match_token('room')
            self.match_token('(')
            self.parse_init_value()
            self.match_token(')')
            self.match_token('{')
            self.parse_switch_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<switch_statement>')

    def parse_switch_body(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<switch_body>']):  # prod 201
            cp = self.checkpoint()
            self.match_token('door')
            self.parse_case_exp()
            self.match_token(':')
            self.parse_case_body()
            self.parse_switch_body()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<switch_body_1>']):  # prod 202
            cp = self.checkpoint()
            self.match_token('ground')
            self.match_token(':')
            self.parse_case_body()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<switch_body>')

    def parse_case_exp(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_exp>']):  # prod 203
            cp = self.checkpoint()
            self.parse_case_type()
            self.parse_case_op()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_exp>')

    def parse_case_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_type>']):  # prod 204
            cp = self.checkpoint()
            self.parse_case_val()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_type_1>']):  # prod 205
            cp = self.checkpoint()
            self.parse_case_group()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_type_2>']):  # prod 206
            cp = self.checkpoint()
            self.match_token('-')
            self.parse_case_negative()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_type>')

    def parse_case_val(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_val>']):  # prod 207
            cp = self.checkpoint()
            self.match_token('tile_lit')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_val_1>']):  # prod 208
            cp = self.checkpoint()
            self.match_token('brick_lit')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_val_2>']):  # prod 209
            cp = self.checkpoint()
            self.match_token('solid')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_val_3>']):  # prod 210
            cp = self.checkpoint()
            self.match_token('fragile')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_val>')

    def parse_case_group(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_group>']):  # prod 211
            cp = self.checkpoint()
            self.match_token('(')
            self.parse_case_exp()
            self.match_token(')')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_group>')

    def parse_case_negative(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_negative>']):  # prod 212
            cp = self.checkpoint()
            self.parse_case_val()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_negative_1>']):  # prod 213
            cp = self.checkpoint()
            self.parse_case_group()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_negative>')

    def parse_case_op(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_op>']):  # prod 214
            cp = self.checkpoint()
            self.parse_operator()
            self.parse_case_exp()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_op_1>']):  # prod 215
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_op>')

    def parse_case_body(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<case_body>']):  # prod 216
            cp = self.checkpoint()
            self.parse_statement()
            self.parse_mult_smt()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_body_1>']):  # prod 217
            cp = self.checkpoint()
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<case_body_2>']):  # prod 218
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<case_body>')

    def parse_mult_smt(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<mult_smt>']):  # prod 219
            cp = self.checkpoint()
            self.parse_statement()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<mult_smt_1>']):  # prod 220
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<mult_smt>')

    def parse_for_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<for_statement>']):  # prod 221
            cp = self.checkpoint()
            self.match_token('for')
            self.match_token('(')
            self.parse_for_dec()
            self.match_token(';')
            self.parse_for_exp()
            self.match_token(';')
            self.parse_for_exp()
            self.match_token(')')
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<for_statement>')

    def parse_for_dec(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<for_dec>']):  # prod 222
            cp = self.checkpoint()
            self.parse_data_type()
            self.match_token('id')
            self.parse_initializer()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<for_dec_1>']):  # prod 223
            cp = self.checkpoint()
            self.match_token('id')
            self.parse_initializer()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<for_dec_2>']):  # prod 224
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<for_dec>')

    def parse_for_exp(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<for_exp>']):  # prod 225
            cp = self.checkpoint()
            self.parse_init_value()
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<for_exp_1>']):  # prod 226
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<for_exp>')

    def parse_while_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<while_statement>']):  # prod 227
            cp = self.checkpoint()
            self.match_token('while')
            self.match_token('(')
            self.parse_init_value()
            self.match_token(')')
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<while_statement>')

    def parse_dowhile_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<dowhile_statement>']):  # prod 228
            cp = self.checkpoint()
            self.match_token('do')
            self.match_token('{')
            self.parse_func_body()
            self.match_token('}')
            self.match_token('while')
            self.match_token('(')
            self.parse_init_value()
            self.match_token(')')
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<dowhile_statement>')

    def parse_break_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<break_statement>']):  # prod 229
            cp = self.checkpoint()
            self.match_token('crack')
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<break_statement>')

    def parse_continue_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<continue_statement>']):  # prod 230
            cp = self.checkpoint()
            self.match_token('mend')
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<continue_statement>')

    def parse_return_statement(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<return_statement>']):  # prod 231
            cp = self.checkpoint()
            self.match_token('home')
            self.parse_init_value()
            self.match_token(';')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<return_statement>')

    def parse_main_type(self):
        if self.stop:
            return
        best_index = -1
        best_errors = None
        best_matched_len = -1
        
        if self.in_predict(PREDICT_SET['<main_type>']):  # prod 232
            cp = self.checkpoint()
            self.match_token('tile')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<main_type_1>']):  # prod 233
            cp = self.checkpoint()
            self.match_token('glass')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<main_type_2>']):  # prod 234
            cp = self.checkpoint()
            self.match_token('brick')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<main_type_3>']):  # prod 235
            cp = self.checkpoint()
            self.match_token('beam')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<main_type_4>']):  # prod 236
            cp = self.checkpoint()
            self.match_token('field')
            if not self.stop:
                return
            
            if self.index > best_index and self.errors:
                best_index = self.index
                best_errors = list(self.errors)
                best_matched_len = len(self.matched_tokens)
            self.rollback(cp)
        if self.in_predict(PREDICT_SET['<main_type_5>']):  # prod 237
            cp = self.checkpoint()
            return
        if best_errors is not None:
            self.errors = best_errors
            self.matched_tokens = self.matched_tokens[:best_matched_len]
            self.stop = True
            self.index = best_index
            self.update_current()
            return
        self.syntax_error('<main_type>')
