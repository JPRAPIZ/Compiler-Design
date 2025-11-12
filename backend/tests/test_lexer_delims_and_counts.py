# backend/tests/test_lexer_delims_and_counts.py
# Pytest suite that (1) verifies delimiters, (2) enforces identifier & numeric counts,
# and (3) locks identifier length to 15 chars.
#
# Run:
#   pip install pytest
#   pytest -q backend/tests/test_lexer_delims_and_counts.py

import pytest

from dfa_lexer_pkg.lexer import Lexer
from dfa_lexer_pkg.token_types import TokenType
from dfa_lexer_pkg import config as CFG
from dfa_lexer_pkg.errors import ERR_IDENT_TOO_LONG


# ---------------------------
# Test configuration fixture
# ---------------------------
@pytest.fixture(autouse=True)
def set_limits_and_reset():
    """Snapshot/restore config; set strict 15-char cap for identifiers."""
    snapshot = (
        CFG.IDENT_MAX_LEN,
        CFG.INT_MAX_DIGITS,
        CFG.FLOAT_INT_MAX_DIGITS,
        CFG.FLOAT_FRAC_MAX_DIGITS,
        CFG.EMIT_TOKEN_ON_LENGTH_ERROR,
    )
    CFG.IDENT_MAX_LEN = 15
    CFG.INT_MAX_DIGITS = 19
    CFG.FLOAT_INT_MAX_DIGITS = 19
    CFG.FLOAT_FRAC_MAX_DIGITS = 19
    CFG.EMIT_TOKEN_ON_LENGTH_ERROR = False  # on overflow: error + drop token
    yield
    (
        CFG.IDENT_MAX_LEN,
        CFG.INT_MAX_DIGITS,
        CFG.FLOAT_INT_MAX_DIGITS,
        CFG.FLOAT_FRAC_MAX_DIGITS,
        CFG.EMIT_TOKEN_ON_LENGTH_ERROR,
    ) = snapshot


# ---------------
# Helper utils
# ---------------
def lex(code: str):
    L = Lexer(code)
    toks = L.tokenize_all()
    return L, toks


def strip_ws(tokens):
    """Drop whitespace tokens for simpler assertions."""
    WS = {TokenType.TOK_SPACE, TokenType.TOK_TAB, TokenType.TOK_NEWLINE}
    return [t for t in tokens if t.type not in WS]


# ---------------------------------------
# A) Delimiter sanity: exact order/types
# ---------------------------------------
def test_delimiters_sequence_and_types():
    code = "(\t)\n{ }[ ] , : . ;"
    L, toks = lex(code)

    # keep delimiters only (ignore WS)
    tt = [t.type for t in strip_ws(toks)]

    expected = [
        TokenType.TOK_OP_PARENTHESES,   # (
        TokenType.TOK_CL_PARENTHESES,   # )
        TokenType.TOK_OP_BRACE,         # {
        TokenType.TOK_CL_BRACE,         # }
        TokenType.TOK_OP_BRACKET,       # [
        TokenType.TOK_CL_BRACKET,       # ]
        TokenType.TOK_COMMA,            # ,
        TokenType.TOK_COLON,            # :
        TokenType.TOK_PERIOD,           # .
        TokenType.TOK_SEMICOLON,        # ;
        TokenType.TOK_EOF,
    ]
    assert tt == expected, f"Delimiter types/order mismatch.\nGot: {tt}\nExp: {expected}"

    # Also verify distinct whitespace tokens were produced
    ws_types = [t.type for t in toks if t.type in (TokenType.TOK_SPACE, TokenType.TOK_TAB, TokenType.TOK_NEWLINE)]
    assert TokenType.TOK_TAB in ws_types and TokenType.TOK_NEWLINE in ws_types and TokenType.TOK_SPACE in ws_types


# ------------------------------------------------------------
# B) Identifier and numeric counts (clean, unambiguous input)
# ------------------------------------------------------------
def test_identifier_and_numeric_counts_clean():
    code = """
        tile a;
        TILE b;           // uppercase => IDENTIFIER
        abcdefghijklmno;  // 15 chars => OK
        // numbers:
        42; -5; 12.34; 0; -3.14;
        // more idents:
        x; y; z;
    """
    L, toks = lex(code)

    # Count identifiers (keywords are NOT identifiers)
    ident_lexemes = [t.lexeme for t in toks if t.type == TokenType.IDENTIFIER]
    # Expected: TILE, b, abcdefghijklmno, x, y, z  => 6
    assert set(ident_lexemes) >= {"TILE", "b", "abcdefghijklmno", "x", "y", "z"}
    assert len(ident_lexemes) >= 6

    # Count numbers (both integer and float)
    numeric_tokens = [t for t in toks if t.type in (TokenType.NUMBER, TokenType.GLASS_NUMBER)]
    # Expected numeric count: 42, -5, 12.34, 0, -3.14  => 5
    assert len(numeric_tokens) >= 5

    # Spot-check the actual numeric lexemes we care about
    numeric_lexemes = {t.lexeme for t in numeric_tokens}
    for expected in {"42", "-5", "12.34", "0", "-3.14"}:
        assert expected in numeric_lexemes, f"Missing numeric token: {expected}"


# -------------------------------------------------------------------------
# C) Identifier length cap (15): overlong identifier triggers error & drop
# -------------------------------------------------------------------------
def test_identifier_length_cap_and_errors():
    # 15 chars (OK), 16 chars (ERROR + dropped)
    ok15 = "abcdefghijklmno"      # length = 15
    bad16 = "abcdefghijklmnop"    # length = 16

    code = f"{ok15}; {bad16}; tile {bad16};"

    L, toks = lex(code)

    # Gather errors
    len_errors = [e for e in L.errors if e["message"] == ERR_IDENT_TOO_LONG]
    assert len(len_errors) >= 2, f"Expected >=2 length errors, got {len(len_errors)}: {L.errors}"

    # Confirm 16-char idents are not emitted as tokens when EMIT_TOKEN_ON_LENGTH_ERROR == False
    all_lexemes = [t.lexeme for t in toks]
    assert ok15 in all_lexemes, "15-char identifier should be present"
    assert bad16 not in all_lexemes, "16-char identifier should be dropped"
    assert ("tile" + bad16) not in all_lexemes, "Overlong keyword+suffix should be dropped as IDENTIFIER"

    # Ensure the accepted 15-char token is an IDENTIFIER, not a keyword
    accepted = [t for t in toks if t.lexeme == ok15]
    assert accepted and accepted[0].type == TokenType.IDENTIFIER
