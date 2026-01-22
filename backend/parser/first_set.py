FIRST_SET = {
    "<program>": {
        "blueprint", "roof", "tile", "glass", "brick", "wall", "beam", "field"},

    "<global>": {"roof", "λ"},

    "<global_dec>": {"tile", "glass", "brick", "wall", "beam", "house", "cement"},

    "<global_var>": {"tile", "glass", "brick", "wall", "beam"},

    "<data_type>": {"tile", "glass", "brick", "wall", "beam"},

    "<global_end>": {"=", ",", "[", "λ"},

    "<global_init>": {"=", "λ"},

    "<global_mult>": {",", "λ"},

    "<value>": {"tile_lit", "glass_lit", "brick_lit", "wall_lit", "solid", "fragile"},

    "<array_dec>": {"["},

    "<arr_size>": {"tile_lit", "]"},

    "<one_d_end>": {"=", "["},

    "<one_d_end2>": {"=", "[", "λ"},

    "<two_d_end>": {"=", "λ"},

    "<elements>": {"tile_lit", "glass_lit", "brick_lit", "wall_lit", "solid", "fragile"},

    "<mult_elem>": {",", "λ"},

    "<mult_elem2>": {",", "λ"},

    "<structure>": {"house"},

    "<struct_type>": {"{", "id"},

    "<struct_dec>": {"{"},

    "<struct_members>": {"tile", "glass", "brick", "wall", "beam"},

    "<data_type_dec>": {"tile", "glass", "brick", "wall", "beam"},

    "<array>": {"[", "λ"},

    "<array2>": {"[", "λ"},

    "<mult_members>": {"tile", "glass", "brick", "wall", "beam", "λ"},

    "<struct_id_end>": {"id", "λ"},

    "<struct_init>": {"=", "λ"},

    "<struct_elem>": {
        "{", "tile_lit", "glass_lit", "brick_lit", "wall_lit", "solid", "fragile"
    },

    "<struct_arr_elem>": {
        "{", "tile_lit", "glass_lit", "brick_lit", "wall_lit", "solid", "fragile"
    },

    "<mult_struct_elem>": {",", "λ"},

    "<mult_struct_id>": {",", "λ"},

    "<struct_var>": {"id"},

    "<global_const>": {"cement"},

    "<global_const_type>": {"tile", "glass", "brick", "wall", "beam", "house"},

    "<global_const_end>": {"=", "["},

    "<global_const_end2>": {"=", "["},

    "<global_mult_const>": {",", "λ"},

    "<global_const_struct>": {",", "λ"},

    "<function>": {"tile", "glass", "brick", "wall", "beam", "field", "λ"},

    "<return_type>": {"tile", "glass", "brick", "wall", "beam", "field"},

    "<param_list>": {"tile", "glass", "brick", "wall", "beam", "λ"},

    "<mult_param>": {",", "λ"},

    "<func_body>": {
        "id", "tile", "glass", "brick", "wall", "beam", "house", "cement",
        "++", "--", "write", "view", "if", "room", "for", "while", "do",
        "crack", "mend", "home"
    },

    "<func_body2>": {
        "id", "tile", "glass", "brick", "wall", "beam", "house", "cement",
        "++", "--", "write", "view", "if", "room", "for", "while", "do",
        "crack", "mend", "home", "λ"
    },

    "<local>": {"tile", "glass", "brick", "wall", "beam", "house", "cement"},

    "<declaration>": {"tile", "glass", "brick", "wall", "beam", "house", "cement"},

    "<variable>": {"tile", "glass", "brick", "wall", "beam"},

    "<var_end>": {"=", ",", "[", "λ"},

    "<initializer>": {"=", "λ"},

    "<mult_var>": {",", "λ"},

    "<constant>": {"cement"},

    "<const_type>": {"tile", "glass", "brick", "wall", "beam", "house"},

    "<const_end>": {"=", "["},

    "<const_end2>": {"=", "["},

    "<mult_const>": {",", "λ"},

    "<mult_const_struct>": {",", "λ"},

    "<init_value>": {
        "(", "id", "tile_lit", "glass_lit", "brick_lit", "wall_lit",
        "solid", "fragile", "-", "++", "--", "!"
    },

    "<value_exp>": {
        "(", "id", "tile_lit", "glass_lit", "brick_lit", "wall_lit",
        "solid", "fragile", "-"
    },

    "<value_type>": {"id", "tile_lit", "glass_lit", "brick_lit", "wall_lit", "solid", "fragile"},

    "<id_type>": {"(", "[", ".", "++", "--", "λ"},

    "<id_type2>": {"(", "[", ".", "++", "--", "λ"},

    "<arr_struct>": {"[", ".", "λ"},

    "<array_index>": {"[", "λ"},

    "<array_index2>": {"[", "λ"},

    "<struct_id>": {".", "λ"},

    "<func_call>": {"(", "λ"},

    "<func_argu>": {
        "(", "id", "tile_lit", "glass_lit", "brick_lit", "wall_lit",
        "solid", "fragile", "-", "++", "--", "!", "λ"
    },

    "<func_mult_call>": {",", "λ"},

    "<postfix_op>": {"++", "--", "λ"},

    "<unary_op>": {"++", "--"},

    "<group>": {"("},

    "<negative_type>": {
        "(", "id", "tile_lit", "glass_lit", "brick_lit", "wall_lit",
        "solid", "fragile"
    },

    "<exp_op>": {
        "-", "+", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=",
        "&&", "||", "λ"
    },

    "<prefix_op>": {"++", "--", "!"},

    "<id_val>": {"id"},

    "<id_type3>": {"[", ".", "λ"},

    "<operator>": {
        "-", "+", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=",
        "&&", "||", "λ"
    },

    "<statement>": {
        "id", "++", "--", "write", "view", "if", "room", "for", "while",
        "do", "crack", "mend", "home"
    },

    "<io_statement>": {"write", "view"},

    "<write_argu>": {"id", "&"},

    "<mult_write_argu>": {",", "λ"},

    "<view_argu>": {",", "λ"},

    "<mult_view_argu>": {",", "λ"},

    "<assign_statement>": {"id", "++", "--"},

    "<id_type4>": {"(", "=", "[", ".", "++", "--", "+=", "-=", "*=", "/=", "%="},

    "<assign_op>": {"=", "+=", "-=", "*=", "/=", "%="},

    "<if_statement>": {"if"},

    "<else_statement>": {"else", "λ"},

    "<else_statement2>": {"{", "if"},

    "<switch_statement>": {"room"},

    "<switch_body>": {"door", "ground"},

    "<case_exp>": {"(", "tile_lit", "brick_lit", "solid", "fragile", "-"},

    "<case_type>": {"(", "tile_lit", "brick_lit", "solid", "fragile", "-"},

    "<case_val>": {"tile_lit", "brick_lit", "solid", "fragile"},

    "<case_group>": {"("},

    "<case_negative>": {"(", "tile_lit", "brick_lit", "solid", "fragile"},

    "<case_op>": {
        "-", "+", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=",
        "&&", "||", "λ"
    },

    "<case_body>": {
        "{", "id", "++", "--", "write", "view", "if", "room", "for", "while",
        "do", "crack", "mend", "home", "λ"
    },

    "<mult_smt>": {
        "id", "++", "--", "write", "view", "if", "room", "for", "while",
        "do", "crack", "mend", "home", "λ"
    },

    "<for_statement>": {"for"},

    "<for_dec>": {"id", "tile", "glass", "brick", "wall", "beam", "λ"},

    "<for_exp>": {
        "(", "id", "tile_lit", "glass_lit", "brick_lit", "wall_lit",
        "solid", "fragile", "-", "++", "--", "!", "λ"
    },

    "<while_statement>": {"while"},

    "<dowhile_statement>": {"do"},

    "<break_statement>": {"crack"},

    "<continue_statement>": {"mend"},

    "<return_statement>": {"home"},  # changed return to home

    "<main_type>": {"tile", "glass", "brick", "beam", "field", "λ"},
}
