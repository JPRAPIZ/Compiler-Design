from flask import Flask, request, jsonify
from flask_cors import CORS
from lexerV3 import Lexer
import time

app = Flask(__name__)
CORS(app, resources={r"/lex": {"origins": "*"}})

@app.route('/lex', methods=['POST'])
def run_lexer():
    try:
        data = request.json or {}
        
        # Input validation
        if 'code' not in data:
            return jsonify({
                "status": "error",
                "tokens": [],
                "errors": [{"message": "No 'code' field provided."}]
            }), 400
        
        source_code = data['code']
        
        # Type validation
        if not isinstance(source_code, str):
            return jsonify({
                "status": "error", 
                "tokens": [],
                "errors": [{"message": "Code must be a string."}]
            }), 400
            
        # Size validation (100KB limit)
        if len(source_code) > 100000:
            return jsonify({
                "status": "error",
                "tokens": [],
                "errors": [{"message": "Code too large (max 100KB)."}]
            }), 400
            
        # Empty code validation
        if not source_code.strip():
            return jsonify({
                "status": "success",
                "tokens": [],
                "errors": [],
                "time_ms": 0
            }), 200

        # Normalize line endings and clean input
        source_code = source_code.replace('\r\n', '\n').strip()
        
        # Initialize lexer and process
        lexer = Lexer(source_code)

        start_time = time.time()
        valid_tokens = lexer.tokenize_all()
        elapsed = round((time.time() - start_time) * 1000, 2)

        # Serialize tokens
        serializable_tokens = [{
            "type": t.type.name,
            "lexeme": t.lexeme,
            "value": t.value,
            "line": t.line,
            "col": t.col
        } for t in valid_tokens]

        return jsonify({
            "status": "success",
            "tokens": serializable_tokens,
            "errors": lexer.errors,
            "time_ms": elapsed
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "tokens": [],
            "errors": [{"message": f"Server error: {str(e)}"}]
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)