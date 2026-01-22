PREDICT_SET = {
    '<program>': ['roof', 'tile', 'glass', 'brick', 'wall', 'beam', 'field', 'blueprint'],  # prod 1
    '<global>': ['roof'],  # prod 2
    '<global_1>': ['blueprint', 'tile', 'glass', 'brick', 'wall', 'beam', 'field'],  # prod 3
    '<global_dec>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 4
    '<global_dec_1>': ['house'],  # prod 5
    '<global_dec_2>': ['cement'],  # prod 6
    '<global_var>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 7
    '<data_type>': ['tile'],  # prod 8
    '<data_type_1>': ['glass'],  # prod 9
    '<data_type_2>': ['brick'],  # prod 10
    '<data_type_3>': ['wall'],  # prod 11
    '<data_type_4>': ['beam'],  # prod 12
    '<global_end>': ['=', ';', ',', ','],  # prod 13
    '<global_end_1>': ['['],  # prod 14
    '<global_init>': ['='],  # prod 15
    '<global_init_1>': [';', ',', ','],  # prod 16
    '<global_mult>': [',', ','],  # prod 17
    '<global_mult_1>': [';'],  # prod 18
    '<value>': ['tile_lit'],  # prod 19
    '<value_1>': ['glass_lit'],  # prod 20
    '<value_2>': ['brick_lit'],  # prod 21
    '<value_3>': ['wall_lit'],  # prod 22
    '<value_4>': ['solid'],  # prod 23
    '<value_5>': ['fragile'],  # prod 24
    '<array_dec>': ['['],  # prod 25
    '<arr_size>': [']'],  # prod 26
    '<arr_size_1>': ['tile_lit'],  # prod 27
    '<one_d_end>': ['['],  # prod 28
    '<one_d_end_1>': ['='],  # prod 29
    '<one_d_end2>': ['['],  # prod 30
    '<one_d_end2_1>': ['='],  # prod 31
    '<one_d_end2_2>': [';'],  # prod 32
    '<two_d_end>': ['='],  # prod 33
    '<two_d_end_1>': [';'],  # prod 34
    '<elements>': ['tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile'],  # prod 35
    '<mult_elem>': [',', ','],  # prod 36
    '<mult_elem_1>': ['}'],  # prod 37
    '<mult_elem2>': [',', ','],  # prod 38
    '<mult_elem2_1>': ['}'],  # prod 39
    '<structure>': ['house'],  # prod 40
    '<struct_type>': ['{'],  # prod 41
    '<struct_type_1>': ['id'],  # prod 42
    '<struct_dec>': ['{'],  # prod 43
    '<struct_members>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 44
    '<data_type_dec>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 45
    '<array>': ['['],  # prod 46
    '<array_1>': [';'],  # prod 47
    '<array2>': ['['],  # prod 48
    '<array2_1>': [';'],  # prod 49
    '<mult_members>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 50
    '<mult_members_1>': ['}'],  # prod 51
    '<struct_id_end>': ['id'],  # prod 52
    '<struct_id_end_1>': [';'],  # prod 53
    '<struct_init>': ['='],  # prod 54
    '<struct_init_1>': [';', ',', ','],  # prod 55
    '<struct_elem>': ['tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile'],  # prod 56
    '<struct_elem_1>': ['{'],  # prod 57
    '<struct_arr_elem>': ['tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile'],  # prod 58
    '<struct_arr_elem_1>': ['{'],  # prod 59
    '<mult_struct_elem>': [',', ','],  # prod 60
    '<mult_struct_elem_1>': ['}'],  # prod 61
    '<mult_struct_id>': [',', ','],  # prod 62
    '<mult_struct_id_1>': [';'],  # prod 63
    '<struct_var>': ['id'],  # prod 64
    '<global_const>': ['cement'],  # prod 65
    '<global_const_type>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 66
    '<global_const_type_1>': ['house'],  # prod 67
    '<global_const_end>': ['='],  # prod 68
    '<global_const_end_1>': ['['],  # prod 69
    '<global_const_end2>': ['='],  # prod 70
    '<global_const_end2_1>': ['['],  # prod 71
    '<global_mult_const>': [',', ','],  # prod 72
    '<global_mult_const_1>': [';'],  # prod 73
    '<global_const_struct>': [',', ','],  # prod 74
    '<global_const_struct_1>': [';'],  # prod 75
    '<function>': ['tile', 'glass', 'brick', 'wall', 'beam', 'field'],  # prod 76
    '<function_1>': ['blueprint', 'tile', 'glass', 'brick', 'beam', 'field'],  # prod 77
    '<return_type>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 78
    '<return_type_1>': ['field'],  # prod 79
    '<param_list>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 80
    '<param_list_1>': [')'],  # prod 81
    '<mult_param>': [',', ','],  # prod 82
    '<mult_param_1>': [')'],  # prod 83
    '<func_body>': ['tile', 'glass', 'brick', 'wall', 'beam', 'house', 'cement'],  # prod 84
    '<func_body_1>': ['id', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 85
    '<func_body2>': ['id', 'tile', 'glass', 'brick', 'wall', 'beam', 'house', 'cement', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 86
    '<func_body2_1>': ['}'],  # prod 87
    '<local>': ['tile', 'glass', 'brick', 'wall', 'beam', 'house', 'cement'],  # prod 88
    '<declaration>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 89
    '<declaration_1>': ['house'],  # prod 90
    '<declaration_2>': ['cement'],  # prod 91
    '<variable>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 92
    '<var_end>': ['=', ';', ',', ','],  # prod 93
    '<var_end_1>': ['['],  # prod 94
    '<initializer>': ['='],  # prod 95
    '<initializer_1>': [';', ',', ','],  # prod 96
    '<mult_var>': [',', ','],  # prod 97
    '<mult_var_1>': [';'],  # prod 98
    '<constant>': ['cement'],  # prod 99
    '<const_type>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 100
    '<const_type_1>': ['house'],  # prod 101
    '<const_end>': ['='],  # prod 102
    '<const_end_1>': ['['],  # prod 103
    '<const_end2>': ['='],  # prod 104
    '<const_end2_1>': ['['],  # prod 105
    '<mult_const>': [',', ','],  # prod 106
    '<mult_const_1>': [';'],  # prod 107
    '<mult_const_struct>': [',', ','],  # prod 108
    '<mult_const_struct_1>': [';'],  # prod 109
    '<init_value>': ['(', 'id', 'tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile', '-'],  # prod 110
    '<init_value_1>': ['++', '--', '!'],  # prod 111
    '<value_exp>': ['id', 'tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile'],  # prod 112
    '<value_exp_1>': ['('],  # prod 113
    '<value_exp_2>': ['-'],  # prod 114
    '<value_type>': ['id'],  # prod 115
    '<value_type_1>': ['tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile'],  # prod 116
    '<id_type>': ['(', ')', ';', ',', ',', '[', ']', '-', '.', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 117
    '<id_type_1>': [')', ';', ',', ',', ']', '-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 118
    '<id_type2>': [')', ';', ',', ',', '[', ']', '-', '.', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 119
    '<id_type2_1>': ['(', ')', ';', ',', ',', ']', '-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 120
    '<arr_struct>': ['[', ')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 121
    '<arr_struct_1>': ['.', ')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 122
    '<arr_struct_2>': [')', ';', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 123
    '<array_index>': ['['],  # prod 124
    '<array_index_1>': [')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 125
    '<array_index2>': ['['],  # prod 126
    '<array_index2_1>': [')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 127
    '<struct_id>': ['.'],  # prod 128
    '<struct_id_1>': [')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 129
    '<func_call>': ['('],  # prod 130
    '<func_call_1>': [')', ';', ',', ',', ']', '-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 131
    '<func_argu>': ['(', 'id', 'tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile', '-', '++', '--', '!'],  # prod 132
    '<func_argu_1>': [')'],  # prod 133
    '<func_mult_call>': [',', ','],  # prod 134
    '<func_mult_call_1>': [')'],  # prod 135
    '<postfix_op>': ['++', '--'],  # prod 136
    '<postfix_op_1>': [')', ';', ',', ',', ']', '-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 137
    '<unary_op>': ['++'],  # prod 138
    '<unary_op_1>': ['--'],  # prod 139
    '<group>': ['('],  # prod 140
    '<negative_type>': ['id', 'tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile'],  # prod 141
    '<negative_type_1>': ['('],  # prod 142
    '<exp_op>': ['-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 143
    '<exp_op_1>': [')', ';', ',', ',', ']'],  # prod 144
    '<prefix_op>': ['!'],  # prod 145
    '<prefix_op_1>': ['++', '--'],  # prod 146
    '<id_val>': ['id'],  # prod 147
    '<id_type3>': ['[', ')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 148
    '<id_type3_1>': ['.', ')', ';', '=', ',', ',', ']', '-', '++', '--', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 149
    '<id_type3_2>': [')', ';', '=', ',', ',', ']', '-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 150
    '<operator>': ['+'],  # prod 151
    '<operator_1>': ['-'],  # prod 152
    '<operator_2>': ['*'],  # prod 153
    '<operator_3>': ['/'],  # prod 154
    '<operator_4>': ['%'],  # prod 155
    '<operator_5>': ['<'],  # prod 156
    '<operator_6>': ['<='],  # prod 157
    '<operator_7>': ['>'],  # prod 158
    '<operator_8>': ['>='],  # prod 159
    '<operator_9>': ['=='],  # prod 160
    '<operator_10>': ['!='],  # prod 161
    '<operator_11>': ['&&'],  # prod 162
    '<operator_12>': ['||'],  # prod 163
    '<statement>': ['write', 'view'],  # prod 164
    '<statement_1>': ['id', '++', '--'],  # prod 165
    '<statement_2>': ['if'],  # prod 166
    '<statement_3>': ['room'],  # prod 167
    '<statement_4>': ['for'],  # prod 168
    '<statement_5>': ['while'],  # prod 169
    '<statement_6>': ['do'],  # prod 170
    '<statement_7>': ['crack'],  # prod 171
    '<statement_8>': ['mend'],  # prod 172
    '<statement_9>': ['home'],  # prod 173
    '<io_statement>': ['write'],  # prod 174
    '<io_statement_1>': ['view'],  # prod 175
    '<write_argu>': ['&'],  # prod 176
    '<write_argu_1>': ['id'],  # prod 177
    '<mult_write_argu>': [',', ','],  # prod 178
    '<mult_write_argu_1>': [')'],  # prod 179
    '<view_argu>': [',', ','],  # prod 180
    '<view_argu_1>': [')'],  # prod 181
    '<mult_view_argu>': [',', ',', ')'],  # prod 182
    '<mult_view_argu_1>': [')'],  # prod 183
    '<assign_statement>': ['++', '--'],  # prod 184
    '<assign_statement_1>': ['id'],  # prod 185
    '<id_type4>': ['('],  # prod 186
    '<id_type4_1>': ['++', '--'],  # prod 187
    '<id_type4_2>': ['[', '.', ')', ';', '=', ',', ',', ']', '-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 188
    '<assign_op>': ['='],  # prod 189
    '<assign_op_1>': ['+='],  # prod 190
    '<assign_op_2>': ['-='],  # prod 191
    '<assign_op_3>': ['*='],  # prod 192
    '<assign_op_4>': ['/='],  # prod 193
    '<assign_op_5>': ['%='],  # prod 194
    '<if_statement>': ['if'],  # prod 195
    '<else_statement>': ['else'],  # prod 196
    '<else_statement_1>': ['}', 'id', 'tile', 'glass', 'brick', 'wall', 'beam', 'house', 'cement', '++', '--', 'write', 'view', 'if', 'room', 'door', 'ground', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 197
    '<else_statement2>': ['if'],  # prod 198
    '<else_statement2_1>': ['{'],  # prod 199
    '<switch_statement>': ['room'],  # prod 200
    '<switch_body>': ['door'],  # prod 201
    '<switch_body_1>': ['ground'],  # prod 202
    '<case_exp>': ['(', 'tile_lit', 'brick_lit', 'solid', 'fragile', '-'],  # prod 203
    '<case_type>': ['tile_lit', 'brick_lit', 'solid', 'fragile'],  # prod 204
    '<case_type_1>': ['('],  # prod 205
    '<case_type_2>': ['-'],  # prod 206
    '<case_val>': ['tile_lit'],  # prod 207
    '<case_val_1>': ['brick_lit'],  # prod 208
    '<case_val_2>': ['solid'],  # prod 209
    '<case_val_3>': ['fragile'],  # prod 210
    '<case_group>': ['('],  # prod 211
    '<case_negative>': ['tile_lit', 'brick_lit', 'solid', 'fragile'],  # prod 212
    '<case_negative_1>': ['('],  # prod 213
    '<case_op>': ['-', '+', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 214
    '<case_op_1>': [')', ':'],  # prod 215
    '<case_body>': ['id', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 216
    '<case_body_1>': ['{'],  # prod 217
    '<case_body_2>': ['}', 'door', 'ground'],  # prod 218
    '<mult_smt>': ['id', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 219
    '<mult_smt_1>': ['}', 'door', 'ground'],  # prod 220
    '<for_statement>': ['for'],  # prod 221
    '<for_dec>': ['tile', 'glass', 'brick', 'wall', 'beam'],  # prod 222
    '<for_dec_1>': ['id'],  # prod 223
    '<for_dec_2>': [';'],  # prod 224
    '<for_exp>': ['(', 'id', 'tile_lit', 'glass_lit', 'brick_lit', 'wall_lit', 'solid', 'fragile', '-', '++', '--', '!'],  # prod 225
    '<for_exp_1>': [')', ';'],  # prod 226
    '<while_statement>': ['while'],  # prod 227
    '<dowhile_statement>': ['do'],  # prod 228
    '<break_statement>': ['crack'],  # prod 229
    '<continue_statement>': ['mend'],  # prod 230
    '<return_statement>': ['home'],  # prod 231
    '<main_type>': ['tile'],  # prod 232
    '<main_type_1>': ['glass'],  # prod 233
    '<main_type_2>': ['brick'],  # prod 234
    '<main_type_3>': ['beam'],  # prod 235
    '<main_type_4>': ['field'],  # prod 236
    '<main_type_5>': ['blueprint'],  # prod 237
}
