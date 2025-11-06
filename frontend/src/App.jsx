import React, { useState } from 'react';

// --- NEW: Imports for the code editor ---
import AceEditor from "react-ace";

// Import themes and modes for the editor
import "ace-builds/src-noconflict/mode-text"; // Basic text mode
import "ace-builds/src-noconflict/theme-tomorrow_night"; // The dark theme
import "ace-builds/src-noconflict/theme-textmate"; // A good light theme
import "ace-builds/src-noconflict/ext-language_tools";

function App() {
  // === State ===
  const [code, setCode] = useState("tile x = -5;\nbrick c = 'a';\nwall s = \"err@or\";\n\n/* This is a comment */\nglass y = 10.5;");
  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // --- NEW: State for theme toggle (defaulted to light mode) ---
  const [isDarkMode, setIsDarkMode] = useState(false);

  // === Handlers ===
  const handleSubmit = async () => {
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

      if (response.ok) {
        setTokens(data.tokens || []);
        setErrors(data.errors || []);
      } else {
        setErrors(data.errors || [{ message: "Unknown server error" }]);
      }

    } catch (error) {
      console.error("Fetch error:", error);
      setErrors([{ message: "Cannot connect to compiler backend. Is it running?", line: 1, col: 1 }]);
    }
    
    setIsLoading(false);
  };

  // --- NEW: Handler for the theme button ---
  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  // === Render ===
  return (
    // --- DYNAMIC THEME: Root element ---
    <div className={`min-h-screen font-sans ${isDarkMode ? "bg-[#111] text-gray-300" : "bg-white text-black"}`}>
      
      {/* --- MODIFIED: Header with all buttons --- */}
      <header className={`flex flex-col md:flex-row items-center justify-between p-4 border-b ${isDarkMode ? "border-[#333] bg-[#1a1a1a]" : "border-gray-200 bg-gray-50"}`}>
        <h1 className={`text-2xl font-bold ${isDarkMode ? "text-white" : "text-black"}`}>arCh Compiler 🏛️</h1>
        
        <div className="flex flex-wrap justify-center space-x-2 mt-2 md:mt-0">
          {/* --- NEW: Theme Toggle Button --- */}
          <button
            onClick={toggleTheme}
            className={`px-4 py-2 rounded-md font-semibold ${isDarkMode ? "bg-gray-700 text-white hover:bg-gray-600" : "bg-gray-200 text-black hover:bg-gray-300"}`}
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

          {/* --- NEW: Placeholder Buttons --- */}
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

      {/* --- MODIFIED: Adjusted height for new header size --- */}
      <div className="flex flex-col md:flex-row" style={{ height: 'calc(100vh - 125px)' }}> {/* Adjusted for multi-line header on mobile */}
        
        {/* --- MODIFIED: Editor Panel (60% width) --- */}
        <div className={`flex flex-col w-full md:w-3/5 ${isDarkMode ? "border-r border-[#333]" : "border-r border-gray-200"}`}>
          <h2 className={`text-lg font-semibold p-2 border-b ${isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"}`}>
            Source Code
          </h2>
          
          {/* --- NEW: Replaced <textarea> with <AceEditor> --- */}
          <AceEditor
            mode="text"
            theme={isDarkMode ? "tomorrow_night" : "textmate"} // Dynamic theme
            onChange={setCode}
            value={code}
            name="SOURCE_CODE_EDITOR"
            editorProps={{ $blockScrolling: true }}
            setOptions={{
              useWorker: false,
              showLineNumbers: true, // <-- YOUR LINE NUMBERS!
              tabSize: 2,
            }}
            width="100%"
            height="100%"
            style={{ backgroundColor: isDarkMode ? '#0a0a0a' : '#ffffff' }} // Dynamic BG
            fontSize={18} // <-- BIGGER FONT SIZE!
          />
        </div>

        {/* --- MODIFIED: Output Panels (40% width) --- */}
        <div className="flex flex-col w-full md:w-2/5">
          
          {/* --- Error Panel (Dynamic Theme) --- */}
          <div className="flex flex-col" style={{ height: '30%' }}>
            <h2 className={`text-lg font-semibold p-2 border-b ${isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"}`}>
              Errors
            </h2>
            <div className={`flex-1 overflow-auto p-2 ${isDarkMode ? "bg-[#0a0a0a]" : "bg-white"}`}>
              {errors.length > 0 ? (
                <pre className={`text-sm whitespace-pre-wrap ${isDarkMode ? "text-red-400" : "text-red-600"}`}>
                  {errors.map((err, i) => (
                    `Line ${err.line}:${err.col} - ${err.message}\n`
                  ))}
                </pre>
              ) : (
                <span className="text-gray-500">No errors.</span>
              )}
            </div>
          </div>

          {/* --- Token Panel (Dynamic Theme) --- */}
          <div className={`flex flex-col border-t ${isDarkMode ? "border-[#333]" : "border-gray-200"}`} style={{ height: '70%' }}>
            <h2 className={`text-lg font-semibold p-2 border-b ${isDarkMode ? "bg-[#222] border-[#333]" : "bg-gray-100 border-gray-200"}`}>
              Token Stream
            </h2>
            <div className="flex-1 overflow-auto">
              <table className={`w-full text-sm ${isDarkMode ? "text-gray-300" : "text-black"}`}>
                <thead className={`sticky top-0 ${isDarkMode ? "bg-[#222]" : "bg-gray-100"}`}>
                  <tr>
                    <th className="px-2 py-1 text-left font-semibold">Type</th>
                    <th className="px-2 py-1 text-left font-semibold">Lexeme</th>
                    <th className="px-2 py-1 text-left font-semibold">Value</th>
                    <th className="px-2 py-1 text-left font-semibold">Line</th>
                    <th className="px-2 py-1 text-left font-semibold">Col</th>
                  </tr>
                </thead>
                <tbody className={isDarkMode ? "bg-[#0a0a0a]" : "bg-white"}>
                  {tokens.map((token, idx) => (
                    <tr
                      key={idx}
                      className={`border-t ${isDarkMode ? "border-[#333] hover:bg-[#1a1a1a]" : "border-gray-200 hover:bg-gray-50"}`}
                    >
                      <td className="px-2 py-1">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs ${isDarkMode ? "bg-[#333] text-gray-400" : "bg-gray-200 text-gray-800"}`}>
                          {token.type}
                        </span>
                      </td>
                      <td className={`px-2 py-1 font-mono ${isDarkMode ? "text-gray-100" : "text-black"}`}>
                        {JSON.stringify(token.lexeme)}
                      </td>
                      <td className={`px-2 py-1 font-mono ${isDarkMode ? "text-gray-100" : "text-black"}`}>
                        {JSON.stringify(token.value)}
                      </td>
      
                      <td className="px-2 py-1">{token.line}</td>
                      <td className="px-2 py-1">{token.col}</td>
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