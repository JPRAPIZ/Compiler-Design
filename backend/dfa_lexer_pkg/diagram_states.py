# Fill these with the numbers from your AUTOMATA.drawio
# You can update them anytime without touching lexer logic.

KW_PATHS = {
    # example: b → r → i → c → k
    "brick":   [20, 21, 22, 23, 24],
    # example: b → e → a → m
    "beam":    [20, 1, 3, 4],
    # example: b → l → u → e → p → r → i → n → t
    "blueprint": [6, 7, 8, 9, 10, 11, 12, 13],
    # w → a → l → l
    "wall":    [83, 84, 85, 86],
    # w → h → i → l → e
    "while":   [88, 89, 90, 91, 92],
    # w → r → i → t → e
    "write":   [95, 96, 97, 98, 99],
    # t → i → l → e
    "tile":    [100, 101, 102, 103],
    # g → l → a → s → s
    "glass":   [105, 106, 107, 108, 109],
    # g → r → o → u → n → d
    "ground":  [112, 113, 114, 115, 116, 117],
    # f → o → r
    "for":     [121, 122, 123],
    # f → r → a → g → i → l → e
    "fragile": [124, 125, 126, 127, 128, 129, 130],
    # f → i → e → l → d
    "field":   [131, 132, 133, 134, 135],
    # h → o → u → s → e
    "house":   [136, 137, 138, 139, 140],
    # h → o → m → e
    "home":    [141, 142, 143, 144],
    # r → o → o → f
    "roof":    [145, 146, 147, 148],
    # r → o → o → m
    "room":    [149, 150, 151, 152],
    # c → e → m → e → n → t
    "cement":  [153, 154, 155, 156, 157, 158],
    # c → r → a → c → k
    "crack":   [159, 160, 161, 162, 163],
    # m → e → n → d
    "mend":    [164, 165, 166, 167],
    # d → o   (and optionally d→o→o→r)
    "do":      [168, 169],
    "door":    [168, 169, 170, 171],
    # e → l → s → e
    "else":    [172, 173, 174, 175],
    # i → f
    "if":      [176, 177],
    # v → i → e → w
    "view":    [178, 179, 180, 181],
    # s → o → l → i → d
    "solid":   [182, 183, 184, 185, 186],
}

# Non-keyword / generic DFA state numbers (examples; adjust to your chart):
GEN = {
    "START": 0,
    "SPACE": 193,
    "TAB":   194,
    "NEWLINE": 195,
    "INT": 236,           # number loop
    "FLOAT_FRAC": 266,    # after dot w/ digit
    "INT_NEG": 132,       # '-' then digit
    "SLASH": 146,         # '/'
    "LINE_COMMENT": 293,  # //
    "BLOCK_COMMENT": 292, # /* ... 
    # add more generic states if your diagram has numbers for them
}
