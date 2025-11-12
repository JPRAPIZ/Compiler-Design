import React, { useState } from 'react';
import AceEditor from "react-ace";
import "ace-builds/src-noconflict/mode-text";
import "ace-builds/src-noconflict/theme-tomorrow_night";
import "ace-builds/src-noconflict/theme-textmate";
import "ace-builds/src-noconflict/ext-language_tools";

// === NEW: Token type color mapping ===
const getTokenColor = (tokenType, isDarkMode) => {
  const colors = {
    // Keywords
    TOK_TILE: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_GLASS: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_BRICK: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_WALL: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_BEAM: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_FIELD: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_HOUSE: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_IF: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_ELSE: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_FOR: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_WHILE: isDarkMode ? '#ff79c6' : '#d33682',
    TOK_RETURN: isDarkMode ? '#ff79c6' : '#d33682',
    
    // Literals
    TOK_TILE_LITERAL: isDarkMode ? '#bd93f9' : '#6c71c4',
    TOK_GLASS_LITERAL: isDarkMode ? '#bd93f9' : '#6c71c4',
    TOK_BRICK_LITERAL: isDarkMode ? '#bd93f9' : '#6c71c4',
    TOK_WALL_LITERAL: isDarkMode ? '#bd93f9' : '#6c71c4',
    
    // Identifiers
    IDENTIFIER: isDarkMode ? '#50fa7b' : '#859900',
    
    // Operators
    TOK_PLUS: isDarkMode ? '#ffb86c' : '#cb4b16',
    TOK_MINUS: isDarkMode ? '#ffb86c' : '#cb4b16',
    TOK_MULTIPLY: isDarkMode ? '#ffb86c' : '#cb4b16',
    TOK_DIVIDE: isDarkMode ? '#ffb86c' : '#cb4b16',
    TOK_ASSIGN: isDarkMode ? '#ffb86c' : '#cb4b16',
    TOK_EQUALS: isDarkMode ? '#ffb86c' : '#cb4b16',
    
    // Delimiters
    TOK_SEMICOLON: isDarkMode ? '#f1fa8c' : '#b58900',
    TOK_COMMA: isDarkMode ? '#f1fa8c' : '#b58900',
    TOK_OP_BRACE: isDarkMode ? '#f1fa8c' : '#b58900',
    TOK_CL_BRACE: isDarkMode ? '#f1fa8c' : '#b58900',
  };
  
  return colors[tokenType] || (isDarkMode ? '#6272a4' : '#839496');
};

// === NEW: Sample test cases  ===
const SAMPLE_PROGRAMS = {
  basic: `// Basic variable declarations
roof tile global_count = 100;
tile calculate_sum(tile a, tile b) {
    tile result = a + b;
    home result;
}

blueprint() {
    tile x = 42;
    glass y = 3.14159;
    brick initial = 'A';
    wall greeting = "Hello\\\\nWorld";
    
    if (x > 10 && y < 5.0) {
        view("Condition met!");
    }
    home 0;
}`,

  errorExamples: `// Examples that should produce lexical errors
tile very_long_identifier_name = 10;  // 28 chars - too long!
glass out_of_range = 9999999999999999.99999999;  // Exceeds glass limits
brick invalid_char = 'abc';  // Multi-character
wall bad_escape = "Hello\\x";  // Unknown escape
tile bad_number = 123abc;  // Invalid number`,

  operators: `// Operator examples
tile a = 10, b = 3;
tile sum = a + b;
tile diff = a - b;
tile product = a * b;
glass quotient = a / b;
tile remainder = a % b;

// Comparison operators
beam is_equal = (a == b);
beam not_equal = (a != b);
beam greater = (a > b);
beam less = (a < b);
beam greater_equal = (a >= b);
beam less_equal = (a <= b);

// Logical operators
beam logical_and = (a > 5 && b < 10);
beam logical_or = (a == 10 || b == 20);
beam logical_not = !(a == b);`
};

function App() {
  const [code, setCode] = useState(SAMPLE_PROGRAMS.basic);
  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [selectedSample, setSelectedSample] = useState('basic'); // NEW

  const handleSubmit = async () => {
    // Early return for empty code
    if (!code.trim()) {
    setTokens([]);
    setErrors([{ message: "Code is empty", line: 1, col: 1 }]);
    return;
  }

    setIsLoading(true);
    setTokens([]);
    setErrors([]);

    try {
      const response = await fetch('http://localhost:5000/lex', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code }),
      });

      const data = await response.json();

      // Handle the new response format with status field
      if (response.ok && data.status === "success") {
      setTokens(data.tokens || []);
      setErrors(data.errors || []);
      // Optional: You can also show the timing in console
      console.log(`Lexing completed in ${data.time_ms}ms`);
      } else {
      setErrors(data.errors || [{ message: "Unknown server error" }]);
      }

    } catch (error) {
      console.error("Fetch error:", error);
      setErrors([{ 
        message: "Cannot connect to compiler backend. Is it running on port 5000?", 
        line: 1, 
        col: 1 
      }]);
    }
    
    setIsLoading(false);
  };

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  // === NEW: Sample program handler ===
  const handleSampleChange = (sampleKey) => {
    setSelectedSample(sampleKey);
    setCode(SAMPLE_PROGRAMS[sampleKey]);
    setTokens([]);
    setErrors([]);
  };

  // === NEW: Statistics calculation ===
  const stats = {
    totalTokens: tokens.length,
    keywords: tokens.filter(t => t.type.startsWith('TOK_') && !t.type.includes('LITERAL')).length,
    identifiers: tokens.filter(t => t.type === 'IDENTIFIER').length,
    literals: tokens.filter(t => t.type.includes('LITERAL')).length,
    operators: tokens.filter(t => 
      t.type.includes('ASSIGN') || 
      t.type.includes('PLUS') ||
      t.type.includes('MINUS') ||
      t.type.includes('MULTIPLY') ||
      t.type.includes('DIVIDE') ||
      t.type.includes('EQUALS') ||
      t.type.includes('LESS') ||
      t.type.includes('GREATER') ||
      t.type.includes('AND') ||
      t.type.includes('OR') ||
      t.type.includes('NOT')
    ).length,
  };

  return (
    <div className={`min-h-screen font-sans ${isDarkMode ? "bg-[#111] text-gray-300" : "bg-white text-black"}`}>
      
      {/* Enhanced Header */}
      <header className={`flex flex-col md:flex-row items-center justify-between p-4 border-b ${isDarkMode ? "border-[#333] bg-[#1a1a1a]" : "border-gray-200 bg-gray-50"}`}>
        <div className="flex items-center space-x-4">
          <h1 className={`text-2xl font-bold ${isDarkMode ? "text-white" : "text-black"}`}>
            arCh Compiler 🏛️
          </h1>
          
          {/* NEW: Sample Program Selector */}
          <select 
            value={selectedSample}
            onChange={(e) => handleSampleChange(e.target.value)}
            className={`px-3 py-2 rounded-md border ${
              isDarkMode 
                ? "bg-[#333] border-[#555] text-white" 
                : "bg-white border-gray-300 text-black"
            }`}
          >
            <option value="basic">Basic Program</option>
            <option value="operators">Operators Demo</option>
            <option value="errorExamples">Error Examples</option>
          </select>
        </div>
        
        <div className="flex flex-wrap justify-center space-x-2 mt-2 md:mt-0">
          <button
            onClick={toggleTheme}
            className={`px-4 py-2 rounded-md font-semibold ${
              isDarkMode 
                ? "bg-gray-700 text-white hover:bg-gray-600" 
                : "bg-gray-200 text-black hover:bg-gray-300"
            }`}
          >
            {isDarkMode ? "Light Mode ☀️" : "Dark Mode 🌙"}
          </button>

          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 disabled:bg-gray-500"
          >
            {isLoading ? "Running..." : "Run Lexer"}
          </button>

          <button
            disabled={true}
            className="px-4 py-2 bg-gray-600 text-gray-400 rounded-md font-semibold cursor-not-allowed"
            title="Coming soon!"
          >
            Run Syntax
          </button>
          <button
            disabled={true}
            className="px-4 py-2 bg-gray-600 text-gray-400 rounded-md font-semibold cursor-not-allowed"
            title="Coming soon!"
          >
            Run Semantic
          </button>
        </div>
      </header>

      {/* NEW: Statistics Bar */}
      {tokens.length > 0 && (
        <div className={`px-4 py-2 border-b ${
          isDarkMode ? "border-[#333] bg-[#1a1a1a]" : "border-gray-200 bg-gray-50"
        }`}>
          <div className="flex flex-wrap gap-4 text-sm">
            <span>Total Tokens: <strong>{stats.totalTokens}</strong></span>
            <span>Keywords: <strong>{stats.keywords}</strong></span>
            <span>Identifiers: <strong>{stats.identifiers}</strong></span>
            <span>Literals: <strong>{stats.literals}</strong></span>
            <span>Operators: <strong>{stats.operators}</strong></span>
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row" style={{ height: 'calc(100vh - 180px)' }}>
        
        {/* Editor Panel */}
        <div className={`flex flex-col w-full md:w-3/5 ${isDarkMode ? "border-r border-[#333]" : "border-r border-gray-200"}`}>
          <h2 className={`text-lg font-semibold p-2 border-b ${isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"}`}>
            Source Code Editor
          </h2>
          
          <AceEditor
            mode="text"
            theme={isDarkMode ? "tomorrow_night" : "textmate"}
            onChange={setCode}
            value={code}
            name="SOURCE_CODE_EDITOR"
            editorProps={{ $blockScrolling: true }}
            setOptions={{
              useWorker: false,
              showLineNumbers: true,
              tabSize: 2,
              highlightActiveLine: true,
              highlightSelectedWord: true,
            }}
            width="100%"
            height="100%"
            style={{ backgroundColor: isDarkMode ? '#0a0a0a' : '#ffffff' }}
            fontSize={16}
          />
        </div>

        {/* Output Panels */}
        <div className="flex flex-col w-full md:w-2/5">
          
          {/* Enhanced Error Panel */}
          <div className="flex flex-col" style={{ height: '30%' }}>
            <h2 className={`text-lg font-semibold p-2 border-b ${
              isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"
            }`}>
              Lexical Errors {errors.length > 0 && `(${errors.length})`}
            </h2>
            <div className={`flex-1 overflow-auto p-2 ${isDarkMode ? "bg-[#0a0a0a]" : "bg-white"}`}>
              {errors.length > 0 ? (
                <div className="space-y-1">
                  {errors.map((err, i) => (
                    <div 
                      key={i}
                      className={`p-2 rounded text-sm ${
                        isDarkMode ? "bg-red-900/30 text-red-300" : "bg-red-50 text-red-700"
                      }`}
                    >
                      <div className="font-mono">
                        <strong>Line {err.line}:{err.col}</strong> - {err.message}
                        {err.character && err.character !== 'EOF' && (
                          <span> at '{err.character}'</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={`text-center p-4 ${isDarkMode ? "text-green-400" : "text-green-600"}`}>
                  ✓ No lexical errors detected
                </div>
              )}
            </div>
          </div>

          {/* Enhanced Token Panel */}
          <div className={`flex flex-col border-t ${isDarkMode ? "border-[#333]" : "border-gray-200"}`} style={{ height: '70%' }}>
            <h2 className={`text-lg font-semibold p-2 border-b ${
              isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"
            }`}>
              Token Stream {tokens.length > 0 && `(${tokens.length})`}
            </h2>
            <div className="flex-1 overflow-auto">
              <table className={`w-full text-sm ${isDarkMode ? "text-gray-300" : "text-black"}`}>
                <thead className={`sticky top-0 ${isDarkMode ? "bg-[#222]" : "bg-gray-100"}`}>
                  <tr>
                    <th className="px-2 py-1 text-left font-semibold">Type</th>
                    <th className="px-2 py-1 text-left font-semibold">Lexeme</th>
                    <th className="px-2 py-1 text-left font-semibold">Value</th>
                    <th className="px-2 py-1 text-left font-semibold">Line:Col</th>
                  </tr>
                </thead>
                <tbody className={isDarkMode ? "bg-[#0a0a0a]" : "bg-white"}>
                  {tokens.map((token, idx) => (
                    <tr
                      key={idx}
                      className={`border-t ${
                        isDarkMode ? "border-[#333] hover:bg-[#1a1a1a]" : "border-gray-200 hover:bg-gray-50"
                      }`}
                    >
                      <td className="px-2 py-1">
                        <span 
                          className="inline-block px-2 py-0.5 rounded text-xs font-mono"
                          style={{ 
                            backgroundColor: getTokenColor(token.type, isDarkMode) + '20',
                            color: getTokenColor(token.type, isDarkMode),
                            border: `1px solid ${getTokenColor(token.type, isDarkMode)}30`
                          }}
                        >
                          {token.type.replace('TOK_', '')}
                        </span>
                      </td>
                      <td className={`px-2 py-1 font-mono ${isDarkMode ? "text-gray-100" : "text-black"}`}>
                        {token.lexeme}
                      </td>
                      <td className={`px-2 py-1 font-mono ${isDarkMode ? "text-gray-100" : "text-black"}`}>
                        {token.value !== null && token.value !== undefined 
                          ? (typeof token.value === 'string' 
                              ? `"${token.value}"` 
                              : token.value.toString())
                          : '—'}
                      </td>
                      <td className="px-2 py-1 font-mono text-xs opacity-70">
                        {token.line}:{token.col}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;