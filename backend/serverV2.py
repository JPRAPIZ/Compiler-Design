# serverV2.py
from __future__ import annotations
import os
import sys
from typing import Any, Dict  # <-- needed for type hints

from flask import Flask, request, jsonify
from flask_cors import CORS

# --- ensure we can import the local lexer package (as a package) ---
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # add backend/ to sys.path

# Now import from the package
from dfa_lexer_pkg import config as CFG
from dfa_lexer_pkg.lexer import Lexer
from dfa_lexer_pkg.token_types import TokenType

app = Flask(__name__)
CORS(app)


def apply_runtime_config(cfg_in: Dict[str, Any]) -> Dict[str, Any]:
    """Optionally override limits at runtime per-request."""
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


@app.post("/lex")
def lex():
    data = request.get_json(force=True) or {}
    if "code" not in data:
        return jsonify({"errors": [{"message": "No 'code' field provided."}]}), 400

    effective_cfg = apply_runtime_config(data.get("config", {}))

    L = Lexer(data["code"])
    tokens = L.tokenize_all()

    tokens_out = [{
        "type": t.type.name if isinstance(t.type, TokenType) else str(t.type),
        "lexeme": t.lexeme,
        "value": t.value,
        "line": t.line,
        "col": t.col,
    } for t in tokens]

    traces_out = [{
        "index": i,
        "type": t.type.name if isinstance(t.type, TokenType) else str(t.type),
        "lexeme": t.lexeme,
        "trace": t.trace or []
    } for i, t in enumerate(tokens)]

    return jsonify({
        "tokens": tokens_out,
        "errors": L.errors,
        "backend": {
            "traces": traces_out,
            "config_used": effective_cfg
        }
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
