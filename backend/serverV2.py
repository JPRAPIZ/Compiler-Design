# ---- imports (same) ----
from __future__ import annotations
import os
import sys
from typing import Any, Dict

from flask import Flask, request, jsonify
from flask_cors import CORS

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from dfa_lexer_pkg import config as CFG
from dfa_lexer_pkg.lexer import Lexer
from dfa_lexer_pkg.token_types import TokenType

# --- diagnostics: show exactly which lexer file is loaded ---
import dfa_lexer_pkg.lexer as LEXMOD
print("Using lexer module file:", getattr(LEXMOD, "__file__", "<unknown>"))

app = Flask(__name__)
CORS(app)


def apply_runtime_config(cfg_in: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = {
        "IDENT_MAX_LEN": CFG.IDENT_MAX_LEN,
        "INT_MAX_DIGITS": CFG.INT_MAX_DIGITS,
        "FLOAT_INT_MAX_DIGITS": CFG.FLOAT_INT_MAX_DIGITS,
        "FLOAT_FRAC_MAX_DIGITS": CFG.FLOAT_FRAC_MAX_DIGITS,
        "EMIT_TOKEN_ON_LENGTH_ERROR": CFG.EMIT_TOKEN_ON_LENGTH_ERROR,
        "CASE_SENSITIVE_KEYWORDS": CFG.CASE_SENSITIVE_KEYWORDS,
    }
    if not cfg_in:
        return snapshot

    if "ident_max_len" in cfg_in:
        CFG.IDENT_MAX_LEN = int(cfg_in["ident_max_len"])
    if "int_max_digits" in cfg_in:
        CFG.INT_MAX_DIGITS = int(cfg_in["int_max_digits"])
    if "float_int_max_digits" in cfg_in:
        CFG.FLOAT_INT_MAX_DIGITS = int(cfg_in["float_int_max_digits"])
    if "float_frac_max_digits" in cfg_in:
        CFG.FLOAT_FRAC_MAX_DIGITS = int(cfg_in["float_frac_max_digits"])
    if "emit_token_on_length_error" in cfg_in:
        CFG.EMIT_TOKEN_ON_LENGTH_ERROR = bool(cfg_in["emit_token_on_length_error"])

    return {
        "IDENT_MAX_LEN": CFG.IDENT_MAX_LEN,
        "INT_MAX_DIGITS": CFG.INT_MAX_DIGITS,
        "FLOAT_INT_MAX_DIGITS": CFG.FLOAT_INT_MAX_DIGITS,
        "FLOAT_FRAC_MAX_DIGITS": CFG.FLOAT_FRAC_MAX_DIGITS,
        "EMIT_TOKEN_ON_LENGTH_ERROR": CFG.EMIT_TOKEN_ON_LENGTH_ERROR,
        "CASE_SENSITIVE_KEYWORDS": CFG.CASE_SENSITIVE_KEYWORDS,
    }


@app.get("/health")
def health():
    return jsonify({"ok": True})


def _scan_all_tokens(lex: Lexer):
    """
    Works with any of these lexer APIs:
      - tokenize_all()
      - __iter__()
      - get_next_token()
    """
    # 1) Preferred: tokenize_all
    if hasattr(lex, "tokenize_all") and callable(getattr(lex, "tokenize_all")):
        return lex.tokenize_all()

    # 2) Iterator protocol
    if hasattr(lex, "__iter__"):
        try:
            return list(iter(lex))
        except TypeError:
            pass  # not actually iterable

    # 3) Fallback: manual loop via get_next_token
    if hasattr(lex, "get_next_token") and callable(getattr(lex, "get_next_token")):
        out = []
        while True:
            t = lex.get_next_token()
            out.append(t)
            # TokenType may be an Enum, name is TOK_EOF
            eof = getattr(t, "type", None)
            if eof == TokenType.TOK_EOF or getattr(eof, "name", None) == "TOK_EOF":
                break
        return out

    # If none are available, fail clearly
    raise RuntimeError(
        "Loaded Lexer does not expose tokenize_all(), __iter__(), or get_next_token(). "
        f"Module path: {getattr(LEXMOD, '__file__', '<unknown>')}"
    )


@app.post("/lex")
def lex():
    data = request.get_json(force=True) or {}
    if "code" not in data:
        return jsonify({"errors": [{"message": "No 'code' field provided."}]}), 400

    effective_cfg = apply_runtime_config(data.get("config", {}))

    L = Lexer(data["code"])
    tokens = _scan_all_tokens(L)

    tokens_out = [{
        "type": t.type.name if isinstance(t.type, TokenType) else str(t.type),
        "lexeme": t.lexeme,
        "value": getattr(t, "value", None),
        "line": t.line,
        "col": t.col,
    } for t in tokens]

    traces_out = [{
        "index": i,
        "type": t.type.name if isinstance(t.type, TokenType) else str(t.type),
        "lexeme": t.lexeme,
        "trace": getattr(t, "trace", None) or []
    } for i, t in enumerate(tokens)]

    return jsonify({
        "tokens": tokens_out,
        "errors": getattr(L, "errors", []),
        "backend": {
            "traces": traces_out,
            "config_used": effective_cfg
        }
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
