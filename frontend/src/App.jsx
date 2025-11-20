import React, { useState, useRef } from 'react';
import AceEditor from "react-ace";
import "ace-builds/src-noconflict/mode-text";
import "ace-builds/src-noconflict/theme-tomorrow_night";
import "ace-builds/src-noconflict/theme-textmate";
import "ace-builds/src-noconflict/ext-language_tools";

// Default source code
const DEFAULT_CODE = `// Basic arCh program
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
}`;

function App() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const editorRef = useRef(null);

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

  // Function to get editor markers for error highlighting
  const getErrorMarkers = () => {
    return errors.map(error => ({
      startRow: error.line - 1,
      startCol: error.col - 1,
      endRow: error.line - 1,
      endCol: error.col,
      className: isDarkMode ? 'error-marker-dark' : 'error-marker-light',
      type: 'text'
    }));
  };

  return (
    <div className={`min-h-screen font-sans ${isDarkMode ? "bg-[#111] text-gray-300" : "bg-white text-black"}`}>
      
      {/* Add CSS for error highlighting */}
      <style>
        {`
          .error-marker-light {
            position: absolute;
            background-color: rgba(239, 68, 68, 0.3);
            border-bottom: 2px solid #dc2626;
          }
          .error-marker-dark {
            position: absolute;
            background-color: rgba(239, 68, 68, 0.4);
            border-bottom: 2px solid #f87171;
          }
        `}
      </style>

      {/* Simplified Header */}
      <header className={`flex flex-col md:flex-row items-center justify-between p-4 border-b ${isDarkMode ? "border-[#333] bg-[#1a1a1a]" : "border-gray-200 bg-gray-50"}`}>
        <h1 className={`text-2xl font-bold ${isDarkMode ? "text-white" : "text-black"}`}>
          arCh Compiler
        </h1>
        
        <div className="flex flex-wrap justify-center space-x-2 mt-2 md:mt-0">
          <button
            onClick={toggleTheme}
            className={`px-4 py-2 rounded-md font-semibold ${
              isDarkMode 
                ? "bg-gray-700 text-white hover:bg-gray-600" 
                : "bg-gray-200 text-black hover:bg-gray-300"
            }`}
          >
            {isDarkMode ? "Light Mode" : "Dark Mode"}
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

      <div className="flex flex-col md:flex-row" style={{ height: 'calc(100vh - 80px)' }}>
        
        {/* Editor Panel with Error Highlighting */}
        <div className={`flex flex-col w-full md:w-3/5 ${isDarkMode ? "border-r border-[#333]" : "border-r border-gray-200"}`}>
          <h2 className={`text-lg font-semibold p-2 border-b ${isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"}`}>
            Source Code {errors.length > 0 && `- ${errors.length} Error(s) Found`}
          </h2>
          
          <AceEditor
            ref={editorRef}
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
            markers={getErrorMarkers()}
            width="100%"
            height="100%"
            style={{ backgroundColor: isDarkMode ? '#0a0a0a' : '#ffffff' }}
            fontSize={16}
          />
        </div>

        {/* Output Panels */}
        <div className="flex flex-col w-full md:w-2/5">
          
          {/* Enhanced Error Panel */}
          <div className="flex flex-col" style={{ height: '40%' }}>
            <h2 className={`text-lg font-semibold p-2 border-b ${
              isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"
            }`}>
              Lexical Errors
            </h2>
            <div className={`flex-1 overflow-auto p-3 ${isDarkMode ? "bg-[#0a0a0a]" : "bg-white"}`}>
              {errors.length > 0 ? (
                <div className="space-y-3">
                  {errors.map((err, i) => (
                    <div 
                      key={i}
                      className={`p-3 rounded-lg border-l-4 cursor-pointer hover:opacity-80 ${
                        isDarkMode 
                          ? "bg-red-900/30 border-red-500 text-red-300" 
                          : "bg-red-50 border-red-500 text-red-700"
                      }`}
                      onClick={() => {
                        // Scroll to error in editor
                        if (editorRef.current) {
                          const editor = editorRef.current.editor;
                          editor.gotoLine(err.line, err.col - 1, true);
                          editor.focus();
                        }
                      }}
                    >
                      <div className="flex items-start">
                        <div className="flex-1">
                          <div className="font-semibold mb-1">Lexical Error</div>
                          <div className="text-sm space-y-1">
                            <div>
                              <strong>Location:</strong> Line {err.line}, Column {err.col}
                            </div>
                            <div>
                              <strong>Issue:</strong> {err.message}
                            </div>
                            {err.character && err.character !== 'EOF' && (
                              <div>
                                <strong>Character:</strong> '{err.character}'
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={`flex flex-col items-center justify-center h-full ${isDarkMode ? "text-green-400" : "text-green-600"}`}>
                  <div className="text-lg font-semibold">No Lexical Errors</div>
                  <div className="text-sm mt-1 opacity-70">All tokens are valid</div>
                </div>
              )}
            </div>
          </div>

          {/* Simplified Token Panel */}
          <div className={`flex flex-col border-t ${isDarkMode ? "border-[#333]" : "border-gray-200"}`} style={{ height: '60%' }}>
            <div className="flex-1 overflow-auto">
              <table className={`w-full text-sm ${isDarkMode ? "text-gray-300" : "text-black"}`}>
                <thead className={`sticky top-0 ${isDarkMode ? "bg-[#222]" : "bg-gray-100"}`}>
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold">Token</th>
                    <th className="px-3 py-2 text-left font-semibold">Lexeme</th>
                    <th className="px-3 py-2 text-left font-semibold">Line:Col</th>
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
                      <td className="px-3 py-2">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-mono ${
                          isDarkMode ? "bg-[#333] text-gray-300" : "bg-gray-200 text-gray-800"
                        }`}>
                          {token.type}
                        </span>
                      </td>
                      <td className={`px-3 py-2 font-mono ${isDarkMode ? "text-gray-100" : "text-black"}`}>
                        {token.lexeme}
                      </td>
                      <td className={`px-3 py-2 font-mono text-xs ${isDarkMode ? "text-gray-400" : "text-gray-600"}`}>
                        {token.line}:{token.col}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {tokens.length === 0 && (
                <div className={`flex items-center justify-center h-32 ${isDarkMode ? "text-gray-500" : "text-gray-400"}`}>
                  No tokens generated yet
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;