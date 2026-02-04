PREDICT_SET = {
    '<program>': ['roof', 'wall', 'tile', 'glass', 'brick', 'beam', 'field'],  # prod 1
    '<program_body>': ['wall'],  # prod 2
    '<program_body_1>': ['tile', 'glass', 'brick', 'beam', 'field'],  # prod 3
    '<program_body2>': ['id'],  # prod 4
    '<program_body2_1>': ['blueprint'],  # prod 5
    '<global>': ['roof'],  # prod 6
    '<global_1>': ['wall', 'tile', 'glass', 'brick', 'beam', 'field'],  # prod 7
    '<global_dec>': ['wall', 'tile', 'glass', 'brick', 'beam'],  # prod 8
    '<global_dec_1>': ['house'],  # prod 9
    '<global_dec_2>': ['cement'],  # prod 10
    '<global_var>': ['tile', 'glass', 'brick', 'beam'],  # prod 11
    '<global_var_1>': ['wall'],  # prod 12
    '<data_type>': ['tile'],  # prod 13
    '<data_type_1>': ['glass'],  # prod 14
    '<data_type_2>': ['brick'],  # prod 15
    '<data_type_3>': ['beam'],  # prod 16
    '<global_end>': ['=', ';', ','],  # prod 17
    '<global_end_1>': ['['],  # prod 18
    '<global_init>': ['='],  # prod 19
    '<global_init_1>': [';', ','],  # prod 20
    '<global_mult>': [','],  # prod 21
    '<global_mult_1>': [';'],  # prod 22
    '<value>': ['tile_lit'],  # prod 23
    '<value_1>': ['glass_lit'],  # prod 24
    '<value_2>': ['brick_lit'],  # prod 25
    '<value_3>': ['solid'],  # prod 26
    '<value_4>': ['fragile'],  # prod 27
    '<array_dec>': ['['],  # prod 28
    '<arr_size>': [']'],  # prod 29
    '<arr_size_1>': ['tile_lit'],  # prod 30
    '<one_d_end>': ['['],  # prod 31
    '<one_d_end_1>': ['='],  # prod 32
    '<one_d_end2>': ['['],  # prod 33
    '<one_d_end2_1>': ['='],  # prod 34
    '<one_d_end2_2>': [';'],  # prod 35
    '<two_d_end>': ['='],  # prod 36
    '<two_d_end_1>': [';'],  # prod 37
    '<elements>': ['tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile'],  # prod 38
    '<mult_elem>': [','],  # prod 39
    '<mult_elem_1>': ['}'],  # prod 40
    '<mult_elem2>': [','],  # prod 41
    '<mult_elem2_1>': ['}'],  # prod 42
    '<global_wall_end>': ['=', ';', ','],  # prod 43
    '<global_wall_end_1>': ['['],  # prod 44
    '<global_wall_init>': ['='],  # prod 45
    '<global_wall_init_1>': [';', ','],  # prod 46
    '<global_mult_wall>': [','],  # prod 47
    '<global_mult_wall_1>': [';'],  # prod 48
    '<wall_array>': ['['],  # prod 49
    '<wall_size>': [']'],  # prod 50
    '<wall_size_1>': ['tile_lit'],  # prod 51
    '<wall_one_d_end>': ['['],  # prod 52
    '<wall_one_d_end_1>': ['='],  # prod 53
    '<wall_one_d_end2>': ['['],  # prod 54
    '<wall_one_d_end2_1>': ['='],  # prod 55
    '<wall_one_d_end2_2>': [';'],  # prod 56
    '<wall_two_d_end>': ['='],  # prod 57
    '<wall_two_d_end_1>': [';'],  # prod 58
    '<wall_elem>': ['wall_lit'],  # prod 59
    '<wall_mult_elem>': [','],  # prod 60
    '<wall_mult_elem_1>': ['}'],  # prod 61
    '<wall_mult_elem2>': [','],  # prod 62
    '<wall_mult_elem2_1>': ['}'],  # prod 63
    '<structure>': ['house'],  # prod 64
    '<struct_type>': ['{'],  # prod 65
    '<struct_type_1>': ['id'],  # prod 66
    '<struct_dec>': ['{'],  # prod 67
    '<struct_members>': ['wall', 'tile', 'glass', 'brick', 'beam'],  # prod 68
    '<data_type_dec>': ['tile', 'glass', 'brick', 'beam'],  # prod 69
    '<data_type_dec_1>': ['wall'],  # prod 70
    '<array>': ['['],  # prod 71
    '<array_1>': [';'],  # prod 72
    '<array2>': ['['],  # prod 73
    '<array2_1>': [';'],  # prod 74
    '<mult_members>': ['wall', 'tile', 'glass', 'brick', 'beam'],  # prod 75
    '<mult_members_1>': ['}'],  # prod 76
    '<struct_id_end>': ['id'],  # prod 77
    '<struct_id_end_1>': [';'],  # prod 78
    '<struct_init>': ['='],  # prod 79
    '<struct_init_1>': [';', ','],  # prod 80
    '<struct_elem>': ['tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', 'wall_lit'],  # prod 81
    '<struct_elem_1>': ['{'],  # prod 82
    '<struct_value>': ['tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile'],  # prod 83
    '<struct_value_1>': ['wall_lit'],  # prod 84
    '<mult_struct_elem>': [','],  # prod 85
    '<mult_struct_elem_1>': ['}'],  # prod 86
    '<struct_arr_elem>': ['tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', 'wall_lit'],  # prod 87
    '<struct_arr_elem_1>': ['{'],  # prod 88
    '<struct_elements>': ['tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', 'wall_lit'],  # prod 89
    '<struct_mult_elem>': [','],  # prod 90
    '<struct_mult_elem_1>': ['}'],  # prod 91
    '<struct_mult_elem2>': [','],  # prod 92
    '<struct_mult_elem2_1>': ['}'],  # prod 93
    '<mult_struct_id>': [','],  # prod 94
    '<mult_struct_id_1>': [';'],  # prod 95
    '<struct_var>': ['id'],  # prod 96
    '<global_const>': ['cement'],  # prod 97
    '<global_const_type>': ['tile', 'glass', 'brick', 'beam'],  # prod 98
    '<global_const_type_1>': ['wall'],  # prod 99
    '<global_const_type_2>': ['house'],  # prod 100
    '<global_const_end>': ['='],  # prod 101
    '<global_const_end_1>': ['['],  # prod 102
    '<global_mult_const>': [','],  # prod 103
    '<global_mult_const_1>': [';'],  # prod 104
    '<global_const_end2>': ['='],  # prod 105
    '<global_const_end2_1>': ['['],  # prod 106
    '<g_const_wall_end>': ['='],  # prod 107
    '<g_const_wall_end_1>': ['['],  # prod 108
    '<g_mult_const_wall>': [','],  # prod 109
    '<g_mult_const_wall_1>': [';'],  # prod 110
    '<g_const_wall_end2>': ['='],  # prod 111
    '<g_const_wall_end2_1>': ['['],  # prod 112
    '<global_const_struct>': [','],  # prod 113
    '<global_const_struct_1>': [';'],  # prod 114
    '<return_type>': ['tile', 'glass', 'brick', 'beam'],  # prod 115
    '<return_type_1>': ['field'],  # prod 116
    '<param_list>': ['wall', 'tile', 'glass', 'brick', 'beam'],  # prod 117
    '<param_list_1>': [')'],  # prod 118
    '<mult_param>': [','],  # prod 119
    '<mult_param_1>': [')'],  # prod 120
    '<func_body>': ['wall', 'tile', 'glass', 'brick', 'beam', 'house', 'cement'],  # prod 121
    '<func_body_1>': ['id', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 122
    '<func_body2>': ['wall', 'id', 'tile', 'glass', 'brick', 'beam', 'house', 'cement', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 123
    '<func_body2_1>': ['}'],  # prod 124
    '<local>': ['wall', 'tile', 'glass', 'brick', 'beam', 'house', 'cement'],  # prod 125
    '<declaration>': ['wall', 'tile', 'glass', 'brick', 'beam'],  # prod 126
    '<declaration_1>': ['house'],  # prod 127
    '<declaration_2>': ['cement'],  # prod 128
    '<variable>': ['tile', 'glass', 'brick', 'beam'],  # prod 129
    '<variable_1>': ['wall'],  # prod 130
    '<var_end>': ['=', ';', ','],  # prod 131
    '<var_end_1>': ['['],  # prod 132
    '<initializer>': ['='],  # prod 133
    '<initializer_1>': [';', ','],  # prod 134
    '<mult_var>': [','],  # prod 135
    '<mult_var_1>': [';'],  # prod 136
    '<wall_end>': ['=', ';', ','],  # prod 137
    '<wall_end_1>': ['['],  # prod 138
    '<wall_initializer>': ['='],  # prod 139
    '<wall_initializer_1>': [';', ','],  # prod 140
    '<wall_init>': ['('],  # prod 141
    '<wall_init_1>': ['wall_lit'],  # prod 142
    '<wall_init_2>': ['brick_lit'],  # prod 143
    '<wall_init_3>': ['id'],  # prod 144
    '<wall_op>': ['+'],  # prod 145
    '<wall_op_1>': ['+'],  # prod 146
    '<wall_op_2>': ['+'],  # prod 147
    '<wall_op_3>': ['+'],  # prod 148
    '<wall_op_4>': [')', ';', ','],  # prod 149
    '<mult_wall>': [','],  # prod 150
    '<mult_wall_1>': [';'],  # prod 151
    '<constant>': ['cement'],  # prod 152
    '<const_type>': ['tile', 'glass', 'brick', 'beam'],  # prod 153
    '<const_type_1>': ['wall'],  # prod 154
    '<const_type_2>': ['house'],  # prod 155
    '<const_end>': ['='],  # prod 156
    '<const_end_1>': ['['],  # prod 157
    '<mult_const>': [','],  # prod 158
    '<mult_const_1>': [';'],  # prod 159
    '<const_wall_end>': ['='],  # prod 160
    '<const_wall_end_1>': ['['],  # prod 161
    '<mult_const_struct>': [','],  # prod 162
    '<mult_const_struct_1>': [';'],  # prod 163
    '<init_value>': ['id', '(', 'tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', '-'],  # prod 164
    '<init_value_1>': ['++', '--', '!'],  # prod 165
    '<value_exp>': ['id', 'tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile'],  # prod 166
    '<value_exp_1>': ['('],  # prod 167
    '<value_exp_2>': ['-'],  # prod 168
    '<value_type>': ['id'],  # prod 169
    '<value_type_1>': ['tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile'],  # prod 170
    '<id_type>': ['(', '[', '.', '++', '--', ')', ';', ',', ']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 171
    '<id_type_1>': [')', ';', ',', ']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 172
    '<id_type2>': ['[', '.', ')', ';', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 173
    '<id_type2_1>': ['(', ')', ';', ',', ']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 174
    '<arr_struct>': ['[', ')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 175
    '<arr_struct_1>': ['.', ')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 176
    '<arr_struct_2>': [')', ';', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 177
    '<array_index>': ['['],  # prod 178
    '<array_index_1>': [')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 179
    '<array_index2>': ['['],  # prod 180
    '<array_index2_1>': [')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 181
    '<struct_id>': ['.'],  # prod 182
    '<struct_id_1>': [')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 183
    '<func_call>': ['('],  # prod 184
    '<func_call_1>': [')', ';', ',', ']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 185
    '<func_argu>': ['id', '(', 'tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', '-', '++', '--', '!'],  # prod 186
    '<func_argu_1>': ['id', '(', 'brick_lit', 'wall_lit'],  # prod 187
    '<func_argu_2>': [')'],  # prod 188
    '<func_mult_call>': [','],  # prod 189
    '<func_mult_call_1>': [','],  # prod 190
    '<func_mult_call_2>': [')'],  # prod 191
    '<postfix_op>': ['++', '--'],  # prod 192
    '<postfix_op_1>': [')', ';', ',', ']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 193
    '<unary_op>': ['++'],  # prod 194
    '<unary_op_1>': ['--'],  # prod 195
    '<group>': ['('],  # prod 196
    '<negative_type>': ['id', 'tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile'],  # prod 197
    '<negative_type_1>': ['('],  # prod 198
    '<exp_op>': ['+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 199
    '<exp_op_1>': [')', ';', ',', ']'],  # prod 200
    '<prefix_op>': ['!'],  # prod 201
    '<prefix_op_1>': ['++', '--'],  # prod 202
    '<id_val>': ['id'],  # prod 203
    '<id_type3>': ['[', ')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 204
    '<id_type3_1>': ['.', ')', ';', '=', ',', ']', '+', '-', '++', '--', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 205
    '<id_type3_2>': [')', ';', '=', ',', ']', '+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||', '+=', '-=', '*=', '/=', '%='],  # prod 206
    '<operator>': ['+'],  # prod 207
    '<operator_1>': ['-'],  # prod 208
    '<operator_2>': ['*'],  # prod 209
    '<operator_3>': ['/'],  # prod 210
    '<operator_4>': ['%'],  # prod 211
    '<operator_5>': ['<'],  # prod 212
    '<operator_6>': ['<='],  # prod 213
    '<operator_7>': ['>'],  # prod 214
    '<operator_8>': ['>='],  # prod 215
    '<operator_9>': ['=='],  # prod 216
    '<operator_10>': ['!='],  # prod 217
    '<operator_11>': ['&&'],  # prod 218
    '<operator_12>': ['||'],  # prod 219
    '<statement>': ['write', 'view'],  # prod 220
    '<statement_1>': ['id', '++', '--'],  # prod 221
    '<statement_2>': ['if'],  # prod 222
    '<statement_3>': ['room'],  # prod 223
    '<statement_4>': ['for'],  # prod 224
    '<statement_5>': ['while'],  # prod 225
    '<statement_6>': ['do'],  # prod 226
    '<statement_7>': ['crack'],  # prod 227
    '<statement_8>': ['mend'],  # prod 228
    '<statement_9>': ['home'],  # prod 229
    '<io_statement>': ['write'],  # prod 230
    '<io_statement_1>': ['view'],  # prod 231
    '<write_argu>': ['&'],  # prod 232
    '<write_argu_1>': ['id'],  # prod 233
    '<mult_write_argu>': [','],  # prod 234
    '<mult_write_argu_1>': [')'],  # prod 235
    '<view_argu>': [','],  # prod 236
    '<view_argu_1>': [')'],  # prod 237
    '<mult_view_argu>': [',', ')'],  # prod 238
    '<mult_view_argu_1>': [')'],  # prod 239
    '<assign_statement>': ['++', '--'],  # prod 240
    '<assign_statement_1>': ['id'],  # prod 241
    '<id_type4>': ['('],  # prod 242
    '<id_type4_1>': ['++', '--'],  # prod 243
    '<id_type4_2>': ['[', '.', '=', '+=', '-=', '*=', '/=', '%='],  # prod 244
    '<assign_value>': ['id', '(', 'tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', '-', '++', '--', '!'],  # prod 245
    '<assign_value_1>': ['id', '(', 'brick_lit', 'wall_lit'],  # prod 246
    '<assign_op>': ['='],  # prod 247
    '<assign_op_1>': ['+='],  # prod 248
    '<assign_op_2>': ['-='],  # prod 249
    '<assign_op_3>': ['*='],  # prod 250
    '<assign_op_4>': ['/='],  # prod 251
    '<assign_op_5>': ['%='],  # prod 252
    '<if_statement>': ['if'],  # prod 253
    '<else_statement>': ['else'],  # prod 254
    '<else_statement_1>': ['wall', 'id', '}', 'tile', 'glass', 'brick', 'beam', 'house', 'cement', '++', '--', 'write', 'view', 'if', 'room', 'door', 'ground', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 255
    '<else_statement2>': ['if'],  # prod 256
    '<else_statement2_1>': ['{'],  # prod 257
    '<switch_statement>': ['room'],  # prod 258
    '<switch_body>': ['door'],  # prod 259
    '<switch_body_1>': ['ground'],  # prod 260
    '<mult_switch_body>': ['door', 'ground'],  # prod 261
    '<mult_switch_body_1>': ['}'],  # prod 262
    '<case_exp>': ['(', 'tile_lit', 'brick_lit', 'solid', 'fragile', '-'],  # prod 263
    '<case_type>': ['tile_lit', 'brick_lit', 'solid', 'fragile'],  # prod 264
    '<case_type_1>': ['('],  # prod 265
    '<case_type_2>': ['-'],  # prod 266
    '<case_val>': ['tile_lit'],  # prod 267
    '<case_val_1>': ['brick_lit'],  # prod 268
    '<case_val_2>': ['solid'],  # prod 269
    '<case_val_3>': ['fragile'],  # prod 270
    '<case_group>': ['('],  # prod 271
    '<case_negative>': ['tile_lit', 'brick_lit', 'solid', 'fragile'],  # prod 272
    '<case_negative_1>': ['('],  # prod 273
    '<case_op>': ['+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||'],  # prod 274
    '<case_op_1>': [')', ':'],  # prod 275
    '<case_body>': ['id', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 276
    '<case_body_1>': ['{'],  # prod 277
    '<case_body_2>': ['}', 'door', 'ground'],  # prod 278
    '<mult_smt>': ['id', '++', '--', 'write', 'view', 'if', 'room', 'for', 'while', 'do', 'crack', 'mend', 'home'],  # prod 279
    '<mult_smt_1>': ['}', 'door', 'ground'],  # prod 280
    '<for_statement>': ['for'],  # prod 281
    '<for_dec>': ['tile', 'glass', 'brick', 'beam'],  # prod 282
    '<for_dec_1>': ['id'],  # prod 283
    '<while_statement>': ['while'],  # prod 284
    '<dowhile_statement>': ['do'],  # prod 285
    '<break_statement>': ['crack'],  # prod 286
    '<continue_statement>': ['mend'],  # prod 287
    '<return_statement>': ['home'],  # prod 288
    '<home_value>': ['id', '(', 'tile_lit', 'glass_lit', 'brick_lit', 'solid', 'fragile', '-', '++', '--', '!'],  # prod 289
    '<home_value_1>': ['id', '(', 'brick_lit', 'wall_lit'],  # prod 290
}