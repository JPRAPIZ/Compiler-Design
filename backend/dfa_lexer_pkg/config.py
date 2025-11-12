
# Configuration for lexical limits and behavior
IDENT_MAX_LEN = 15            # max identifier length
INT_MAX_DIGITS = 19           # max digits in integer part (approx 64-bit safe)
FLOAT_INT_MAX_DIGITS = 19     # max digits before decimal
FLOAT_FRAC_MAX_DIGITS = 19    # max digits after decimal
EMIT_TOKEN_ON_LENGTH_ERROR = False  # if True, still emit token and mark error; else drop bad token
CASE_SENSITIVE_KEYWORDS = True       # keywords must be exact lowercase as defined
