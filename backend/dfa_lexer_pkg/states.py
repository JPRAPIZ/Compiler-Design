
from enum import Enum, auto

class State(Enum):
    START = 0
    INT = auto()
    INT_NEG = auto()
    FLOAT_FRAC = auto()
    STRING = auto()
    STRING_ESC = auto()
    CHAR = auto()
    CHAR_ESC = auto()
    SLASH = auto()
    LINE_COMMENT = auto()
    BLOCK_COMMENT = auto()
    BLOCK_COMMENT_STAR = auto()
    ID_KW = auto()    # generic id/keyword scanning state

# For keyword ladders, we use dynamic trace labels like "KW:brick:br" so we don't
# explode the Enum. The backend can rely on these strings in token.trace.
