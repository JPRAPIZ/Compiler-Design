import React, { useState } from 'react';
import AceEditor from "react-ace";

// Ace themes + modes
import "ace-builds/src-noconflict/mode-text";
import "ace-builds/src-noconflict/theme-tomorrow_night";
import "ace-builds/src-noconflict/ext-language_tools";

import archLogo from "./assets/arCh.png";

function App() {
  // === State ===
  const [code, setCode] = useState(
`tile blueprint() {

wall welcome = "Hello World!";

home 0;

}`
  );
  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [annotations, setAnnotations] = useState([]);
  const [markers, setMarkers] = useState([]);
  const [editor, setEditor] = useState(null);

  // ✅ RESTORED: ranges derived from errors, for token highlighting
  const errorRanges = errors.map(err => {
    const sLine = err.start_line ?? err.line;
    const sCol  = err.start_col  ?? err.col;
    const eLine = err.end_line   ?? sLine;
    const eCol  = err.end_col    ?? (sCol + 1);

    return { sLine, sCol, eLine, eCol };
  });

  const handleSubmit = async () => {
    setIsLoading(true);
    setTokens([]);
    setErrors([]);
    setAnnotations([]);
    setMarkers([]);

    try {
      const response = await fetch('http://localhost:8000/lex', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: code }),
      });

      const data = await response.json();

      const newTokens = Array.isArray(data.tokens) ? data.tokens : [];
      const newErrors = Array.isArray(data.errors) ? data.errors : [];

      setTokens(newTokens);
      setErrors(newErrors);

      // Annotations (gutter X + tooltip)
      const anns = newErrors.map(err => ({
        row: (err.line ?? err.start_line ?? 1) - 1,
        column: (err.col ?? err.start_col ?? 1) - 1,
        text: err.message,
        type: "error",
      }));
      setAnnotations(anns);

      // Markers (red highlight in code)
      const markers = newErrors.map(err => {
        const startRow = (err.start_line ?? err.line ?? 1) - 1;
        const startCol = (err.start_col  ?? err.col  ?? 1) - 1;
        const endRow   = (err.end_line   ?? err.line ?? 1) - 1;
        const endCol   = (err.end_col    ?? err.col  ?? (startCol + 1)) - 1;

        return {
          startRow,
          startCol,
          endRow,
          endCol,
          className: "lexer-error-marker",
          type: "text",
        };
      });

      setMarkers(markers);

    } catch (error) {
      setErrors([{
        message: "Cannot connect to compiler backend. Is it running?",
        line: 1,
        col: 1,
      }]);
    }

    setIsLoading(false);
  };

  const handleErrorClick = (err) => {
    if (!editor) return;

    const row = (err.start_line ?? err.line ?? 1) - 1;
    const col = (err.start_col  ?? err.col  ?? 1) - 1;

    editor.focus();
    editor.gotoLine(row + 1, col, true);
    editor.selection.moveTo(row, col);
  };

  return (
    <div className="min-h-screen font-sans bg-[#111] text-gray-300">

      {/* Header */}
      <header className="flex flex-col md:flex-row items-center justify-between p-4 border-b border-[#333] bg-[#1a1a1a]">
        <div className="flex items-center space-x-3">
          <img
            src={archLogo}
            alt="arCh Compiler"
            className="h-10 md:h-16 object-contain"
          />
        </div>

        <div className="flex flex-wrap justify-center space-x-2 mt-2 md:mt-0">
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md font-semibold hover:bg-blue-700 disabled:bg-gray-500"
          >
            {isLoading ? "Running..." : "Run Lexer"}
          </button>

          <button disabled className="px-4 py-2 bg-gray-700 text-gray-400 rounded-md font-semibold cursor-not-allowed">
            Run Syntax
          </button>
          <button disabled className="px-4 py-2 bg-gray-700 text-gray-400 rounded-md font-semibold cursor-not-allowed">
            Run Semantic
          </button>
        </div>
      </header>

      {/* Main panels */}
      <div className="flex flex-col md:flex-row" style={{ height: 'calc(100vh - 125px)' }}>
        
        {/* Editor Panel */}
        <div className="flex flex-col w-full md:w-3/5 border-r border-[#333]">
          <h2 className="text-lg font-semibold p-2 border-b bg-[#222] border-[#333]">
            Source Code
          </h2>

          <AceEditor
            mode="text"
            theme="tomorrow_night"
            onChange={setCode}
            value={code}
            name="SOURCE_CODE_EDITOR"
            editorProps={{ $blockScrolling: true }}
            onLoad={(ed) => setEditor(ed)}
            setOptions={{
              useWorker: false,
              showLineNumbers: true,
              tabSize: 5,
              useSoftTabs: false,
            }}
            width="100%"
            height="100%"
            style={{ backgroundColor: '#0a0a0a' }}
            fontSize={22}
            annotations={annotations}
            markers={markers}
          />
        </div>

        {/* Output Panels */}
        <div className="flex flex-col w-full md:w-2/5">
          
          {/* Errors */}
          <div className="flex flex-col" style={{ height: '30%' }}>
            <h2 className="text-lg font-semibold p-2 border-b bg-[#222] border-[#333]">
              Errors
            </h2>
            <div className="flex-1 overflow-auto p-2 bg-[#0a0a0a] text-red-400">
              {errors.length > 0 ? (
                <div className="text-lg space-y-1">
                  {errors.map((err, i) => (
                    <div
                      key={i}
                      className="cursor-pointer hover:bg-red-900/30 rounded px-1 py-0.5"
                      onClick={() => handleErrorClick(err)}
                    >
                      Line {err.line}:{err.col} - {err.message}
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-gray-500">No Lexical errors.</span>
              )}
            </div>
          </div>

          {/* Tokens */}
          <div className="flex flex-col border-t border-[#333]" style={{ height: '70%' }}>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm text-gray-300">
                <thead className="sticky top-0 bg-[#222]">
                  <tr>
                    <th className="px-2 py-1 text-left font-semibold">Lexeme</th>
                    <th className="px-2 py-1 text-left font-semibold">Token</th>
                    <th className="px-2 py-1 text-left font-semibold">Line</th>
                    <th className="px-2 py-1 text-left font-semibold">Col</th>
                  </tr>
                </thead>
                <tbody className="bg-[#0a0a0a]">
                  {tokens.map((t, idx) => {
                    const tokenStartLine = t.line;
                    const tokenStartCol  = t.column;
                    const tokenEndCol    = t.column + (t.lexeme?.length ?? 1);

                    const isErrorToken = errors.some(err => {
                      const sLine = err.start_line ?? err.line;
                      const sCol  = err.start_col  ?? err.col;
                      const eCol  = err.end_col    ?? (sCol + 1);

                      if (sLine !== tokenStartLine) return false;

                      const isDelimError = err.message?.startsWith("Invalid delimiter");

                      if (isDelimError) {
                        // Only mark the token whose delimiter is wrong:
                        // its END column is exactly where the error starts.
                        return tokenEndCol === sCol;
                      }

                      // For other errors (e.g. unterminated wall literal),
                      // mark tokens whose chars overlap the error span.
                      const overlaps =
                        tokenStartCol < eCol && tokenEndCol > sCol;

                      return overlaps;
                    });

                    return (
                      <tr
                        key={idx}
                        className={
                          "border-t border-[#333] hover:bg-[#1a1a1a]" +
                          (isErrorToken ? " bg-red-900/40" : "")
                        }
                      >
                        <td
                          className={
                            "px-3 py-1 text-lg font-mono whitespace-pre-wrap break-words " +
                            (isErrorToken ? "text-red-300" : "text-gray-100")
                          }
                        >
                          {t.lexeme}
                        </td>
                        <td
                          className={
                            "px-2 py-1 text-lg font-mono whitespace-nowrap " +
                            (isErrorToken ? "text-red-300" : "text-gray-100")
                          }
                        >
                          {t.tokenType}
                        </td>
                        <td
                          className={
                            "px-2 py-1 text-lg whitespace-nowrap " +
                            (isErrorToken ? "text-red-300" : "")
                          }
                        >
                          {t.line}
                        </td>
                        <td
                          className={
                            "px-2 py-1 text-lg whitespace-nowrap " +
                            (isErrorToken ? "text-red-300" : "")
                          }
                        >
                          {t.column}
                        </td>
                      </tr>
                    );
                  })}
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
