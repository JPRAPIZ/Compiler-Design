# backend/dfa_lexer_pkg/diagram_states.py
# State numbers copied from your transition-diagram images.
# If you adjust the diagram, just edit these lists—no lexer logic changes needed.

KW_PATHS = {
    # left panel
    "beam":      [0, 1, 2, 3, 4],
    "blueprint": [0, 6, 7, 8, 9, 10, 11, 12, 13],
    "brick":     [0, 15, 16, 17, 18, 19],            # 19 -> whitespace
    "cement":    [0, 20, 21, 22, 23, 24, 26],        # 26 -> whitespace
    "crack":     [0, 27, 28, 29, 30, 31],            # 31 -> delim2
    "do":        [0, 32, 33, 34],                    # 34 -> delim3
    "else":      [0, 38, 39, 40, 41, 42],            # 42 -> whitespace
    "for":       [0, 43, 44, 45, 46],                # 46 -> delim1
    "field":     [0, 47, 48, 49, 50, 51],            # 51 -> whitespace
    "fragile":   [0, 52, 53, 54, 55, 56, 57, 58],    # 58 -> delim4
    "glass":     [0, 59, 60, 61, 62, 63, 64],        # 64 -> whitespace
    "ground":    [0, 65, 66, 67, 68, 69, 70],        # 70 -> delim5
    "home":      [0, 71, 72, 73, 74, 75],            # 75 -> whitespace
    "house":     [0, 76, 77, 78, 79],                # 79 -> whitespace

    # right panel
    "if":        [0, 80, 81, 82],                    # 82 -> delim1
    "mend":      [0, 83, 84, 85, 86, 87],            # 87 -> delim2
    "for_right": [0, 88, 89, 90, 91, 92],            # label shows whitespace; we keep main "for"
    "solid":     [0, 95, 96, 97, 98, 99, 100],       # 100 -> delim4
    "tile":      [0, 101, 102, 103, 104, 105],       # 105 -> whitespace
    "view":      [0, 106, 107, 108, 109, 110],       # 110 -> delim1
    "wall":      [0, 111, 112, 113, 114, 115],       # 115 -> whitespace
    "while":     [0, 116, 117, 118, 119, 120],       # 120 -> delim1
    "write":     [0, 121, 122, 123, 124, 125],       # 125 -> delim1
    "room":      [0, 145, 146, 147, 148],            # from “others” table
    "roof":      [0, 149, 150, 151, 152],            # from “others” table
}

# generic (non-keyword) states we record in traces
GEN = {
    "START": 0,

    # whitespace tokens from “Reserved Symbols”
    "SPACE":   193,
    "TAB":     194,
    "NEWLINE": 195,

    # operators/symbols (use if you want to trace them; otherwise harmless)
    "SLASH": 146,

    # comments (last sheet)
    "LINE_COMMENT": 291,   # newline terminal
    "BLOCK_COMMENT": 292,  # /* -> … states (292,293,294,295,296)

    # numbers (numbers sheet)
    "INT":        236,     # loop for integer digits
    "FLOAT_FRAC": 266,     # loop for frac digits after '.'
    "INT_NEG":    132,     # from minus path into numbers

    # identifier continuation
    "ID_HEAD": 196,        # alpha_id
    "ID_CONT": 198,        # alpha_num loop branches (any of 198,200,202… ok)
}
