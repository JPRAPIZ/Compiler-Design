from flask import Flask, request, jsonify
from flask_cors import CORS
from lexerV5 import Lexer # Import your *upgraded* Lexer class

app = Flask(__name__)
CORS(app)

@app.route('/lex', methods=['POST'])
def run_lexer():
    try:
        data = request.json
        if 'code' not in data:
            return jsonify({"errors": [{"message": "No 'code' field provided."}]}), 400
        
        source_code = data['code']
        
        lexer = Lexer(source_code)
        valid_tokens = lexer.tokenize_all()
        lexical_errors = lexer.errors # These are already dicts, ready for JSON
        
        serializable_tokens = []
        for t in valid_tokens:
            serializable_tokens.append({
                "type": t.type.name,
                "lexeme": t.lexeme,
                "value": t.value,
                "line": t.line,
                "col": t.col  # <-- THE NEWLY ADDED FIELD
            })
            
        return jsonify({
            "tokens": serializable_tokens,
            "errors": lexical_errors # Already includes 'col' from the lexer
        })

    except Exception as e:
        return jsonify({"errors": [{"message": f"Server error: {str(e)}"}]}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)