import React, { useState } from "react";
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

  // NEW: which button was used
  const [mode, setMode] = useState("LEX"); // "LEX" | "SYNTAX"
  // NEW: what type of errors are being shown
  const [errorKind, setErrorKind] = useState(null); // null | "LEX" | "SYNTAX"

  // Helper: build annotations + markers from errors (supports range or point)
  const applyErrorsToEditor = (errs) => {
    // gutter annotations
    const anns = errs.map((err) => {
      const row = (err.start_line ?? err.line ?? 1) - 1;
      const col = (err.start_col ?? err.col ?? 1) - 1;
      return {
        row,
        column: col,
        text: err.message,
        type: "error",
      };
    });
    setAnnotations(anns);

    // red highlight markers
    const mks = errs.map((err) => {
      const startRow = (err.start_line ?? err.line ?? 1) - 1;
      const startCol = (err.start_col ?? err.col ?? 1) - 1;
      const endRow = (err.end_line ?? err.line ?? err.start_line ?? 1) - 1;

      // if end_col missing, highlight 1 char
      const endColRaw =
        err.end_col ?? (err.end_line ? 1 : (err.start_col ?? err.col ?? 1) + 1);

      const endCol = Math.max(endColRaw - 1, startCol + 1);

      return {
        startRow,
        startCol,
        endRow,
        endCol,
        className: "lexer-error-marker", // you can rename later if you want
        type: "text",
      };
    });

    setMarkers(mks);
  };

  const clearOutput = () => {
    setTokens([]);
    setErrors([]);
    setAnnotations([]);
    setMarkers([]);
    setErrorKind(null);
  };

  const handleSubmit = async () => {
    setMode("LEX");
    setIsLoading(true);
    clearOutput();

    try {
      const response = await fetch("http://localhost:8000/lex", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: code }),
      });

      const data = await response.json();

      const newTokens = Array.isArray(data.tokens) ? data.tokens : [];
      const newErrors = Array.isArray(data.errors) ? data.errors : [];

      setTokens(newTokens);
      setErrors(newErrors);
      setErrorKind("LEX");

      applyErrorsToEditor(newErrors);
    } catch (error) {
      const fallback = [
        {
          message: "Cannot connect to compiler backend. Is it running?",
          line: 1,
          col: 1,
        },
      ];
      setErrors(fallback);
      setErrorKind("LEX");
      applyErrorsToEditor(fallback);
    }

    setIsLoading(false);
  };

  const handleRunSyntax = async () => {
    setMode("SYNTAX");
    setIsLoading(true);
    clearOutput(); // hides table (mode does), clears lists

    try {
      // 1) Run lexer first
      const lexResponse = await fetch("http://localhost:8000/lex", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: code }),
      });

      const lexData = await lexResponse.json();
      const lexErrors = Array.isArray(lexData.errors) ? lexData.errors : [];

      // If lexer errors exist, show ONLY those (and stop)
      if (lexErrors.length > 0) {
        setErrors(lexErrors);
        setErrorKind("LEX");
        applyErrorsToEditor(lexErrors);
        setIsLoading(false);
        return;
      }

      // 2) Call parser only if lexer is clean
      const parseResponse = await fetch("http://localhost:8000/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: code }),
      });

      const parseData = await parseResponse.json();
      const synErrors = Array.isArray(parseData.errors) ? parseData.errors : [];

      setErrors(synErrors);
      setErrorKind("SYNTAX");
      applyErrorsToEditor(synErrors);
    } catch (error) {
      const fallback = [
        {
          message: "Cannot connect to parser backend. Is it running?",
          line: 1,
          col: 1,
        },
      ];
      setErrors(fallback);
      setErrorKind("SYNTAX");
      applyErrorsToEditor(fallback);
    }

    setIsLoading(false);
  };

  const handleErrorClick = (err) => {
    if (!editor) return;

    const row = (err.start_line ?? err.line ?? 1) - 1;
    const col = (err.start_col ?? err.col ?? 1) - 1;

    editor.focus();
    editor.gotoLine(row + 1, col, true);
    editor.selection.moveTo(row, col);
  };

  const errorsTitle =
    errorKind === "LEX"
      ? "Errors (Lexical)"
      : errorKind === "SYNTAX"
      ? "Errors (Syntax)"
      : "Errors";

  const emptyErrorsText =
    mode === "LEX"
      ? "No Lexical errors."
      : errorKind === "LEX"
      ? "No Lexical errors." // (this means lex passed; next would be syntax)
      : "No Syntax errors.";

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
            Run Lexer
          </button>

          <button
            onClick={handleRunSyntax}
            disabled={isLoading}
            className="px-4 py-2 bg-purple-600 text-white rounded-md font-semibold hover:bg-purple-700 disabled:bg-gray-500"
          >
            Run Syntax
          </button>

          <button
            disabled
            className="px-4 py-2 bg-gray-700 text-gray-400 rounded-md font-semibold cursor-not-allowed"
          >
            Run Semantic
          </button>
        </div>
      </header>

      {/* Main panels */}
      <div
        className="flex flex-col md:flex-row"
        style={{ height: "calc(100vh - 125px)" }}
      >
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
              highlightActiveLine: false,
              highlightSelectedWord: false,
            }}
            width="100%"
            height="100%"
            style={{ backgroundColor: "#0a0a0a" }}
            fontSize={22}
            annotations={annotations}
            markers={markers}
          />
        </div>

        {/* Output Panels */}
        <div className="flex flex-col w-full md:w-2/5">
          {/* Errors */}
          <div
            className="flex flex-col"
            style={{ height: mode === "LEX" ? "30%" : "100%" }}
          >
            <h2 className="text-lg font-semibold p-2 border-b bg-[#222] border-[#333]">
              {errorsTitle}
            </h2>
            <div className="flex-1 overflow-auto p-2 bg-[#0a0a0a] text-red-400">
              {errors.length > 0 ? (
                <div className="text-lg space-y-1">
                  {errors.map((err, i) => {
                    const line = err.start_line ?? err.line ?? 1;
                    const col = err.start_col ?? err.col ?? 1;
                    return (
                      <div
                        key={i}
                        className="cursor-pointer hover:bg-red-900/30 rounded px-1 py-0.5"
                        onClick={() => handleErrorClick(err)}
                      >
                        Line {line}:{col} - {err.message}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <span className="text-gray-500">{emptyErrorsText}</span>
              )}
            </div>
          </div>

          {/* Tokens: show ONLY in lexer mode */}
          {mode === "LEX" && (
            <div
              className="flex flex-col border-t border-[#333]"
              style={{ height: "70%" }}
            >
              <div className="flex-1 overflow-y-auto overflow-x-hidden">
                <table className="w-full text-sm text-gray-300 table-fixed">
                  <colgroup>
                    <col className="w-1/2" />
                    <col className="w-1/3" />
                    <col className="w-1/12" />
                    <col className="w-1/12" />
                  </colgroup>
                  <thead className="sticky top-0 bg-[#222]">
                    <tr>
                      <th className="px-2 py-1 text-lg text-left font-semibold">
                        Lexeme
                      </th>
                      <th className="px-2 py-1 text-lg text-left font-semibold">
                        Token
                      </th>
                      <th className="px-2 py-1 text-lg text-left font-semibold">
                        Line
                      </th>
                      <th className="px-2 py-1 text-lg text-left font-semibold">
                        Col
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-[#0a0a0a]">
                    {tokens.map((t, idx) => (
                      <tr
                        key={idx}
                        className="border-t border-[#333] hover:bg-[#1a1a1a]"
                      >
                        <td className="px-3 py-1 text-sm md:text-lg font-mono break-words whitespace-pre-wrap text-gray-100">
                          {t.lexeme}
                        </td>
                        <td className="px-2 py-1 text-sm md:text-lg font-mono whitespace-nowrap text-gray-100">
                          {t.tokenType}
                        </td>
                        <td className="px-2 py-1 text-sm md:text-lg whitespace-nowrap text-gray-400">
                          {t.line}
                        </td>
                        <td className="px-2 py-1 text-sm md:text-lg whitespace-nowrap text-gray-400">
                          {t.column}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
