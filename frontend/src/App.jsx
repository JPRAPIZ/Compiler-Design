import React, { useState, useRef, useEffect } from "react";
import AceEditor from "react-ace";

import "ace-builds/src-noconflict/mode-text";
import "ace-builds/src-noconflict/theme-tomorrow_night";
import "ace-builds/src-noconflict/ext-language_tools";

import archLogo from "./assets/arCh.png";

// =============================================================================
// JS TAC Interpreter — mirrors tac_runtime.py exactly
// =============================================================================

function createInterpreter(instructions, onOutput, onInput) {
  // label map
  const labelMap = {};
  const funcMap = {};
  instructions.forEach((instr, idx) => {
    if (instr.op === "label") labelMap[instr.name] = idx;
    if (instr.op === "func_begin") funcMap[instr.name] = idx;
  });

  const globalMem = {};
  const callStack = [];
  const runtimeErrors = [];
  let pc = 0;
  let iterCount = 0;
  const MAX_ITER = 10_000_000;

  // ── value resolution ──────────────────────────────────────────────────────
  function currentMem() {
    return callStack.length
      ? callStack[callStack.length - 1].locals
      : globalMem;
  }

  function resolve(operand, mem) {
    if (operand === null || operand === undefined) return null;
    if (typeof operand !== "string") return operand;
    if (operand in mem) return mem[operand];
    if (mem !== globalMem && operand in globalMem) return globalMem[operand];
    if (operand === "True") return true;
    if (operand === "False") return false;
    if (operand.startsWith('"') && operand.endsWith('"'))
      return operand
        .slice(1, -1)
        .replace(
          /\\([ntv\\'"0])/g,
          (_, c) =>
            ({ n: "\n", t: "\t", "\\": "\\", "'": "'", '"': '"', 0: "\0" })[
              c
            ] || c,
        );
    // Single-quoted brick (char) literal: 'A' → charCode, '\n' → 10
    if (operand.startsWith("'") && operand.endsWith("'")) {
      const inner = operand.slice(1, -1);
      if (inner.startsWith("\\") && inner.length === 2) {
        const escMap = { n: 10, t: 9, "\\": 92, "'": 39, '"': 34, 0: 0 };
        return escMap[inner[1]] ?? inner.charCodeAt(1);
      }
      return inner.length === 1 ? inner.charCodeAt(0) : 0;
    }
    if (operand.includes(".")) {
      const f = parseFloat(operand);
      if (!isNaN(f)) return f;
    }
    const n = parseInt(operand, 10);
    if (!isNaN(n) && String(n) === operand) return n;
    runtimeErrors.push(`Runtime error: undefined variable '${operand}'`);
    return 0;
  }

  // ── arithmetic ────────────────────────────────────────────────────────────
  function applyBinop(op, l, r) {
    try {
      if (op === "+")
        return typeof l === "string" || typeof r === "string"
          ? String(l) + String(r)
          : l + r;
      if (op === "-") return l - r;
      if (op === "*") return l * r;
      if (op === "/") {
        if (r === 0) {
          runtimeErrors.push("Runtime error: division by zero");
          return 0;
        }
        return Number.isInteger(l) && Number.isInteger(r)
          ? Math.trunc(l / r)
          : l / r;
      }
      if (op === "%") {
        if (r === 0) {
          runtimeErrors.push("Runtime error: modulo by zero");
          return 0;
        }
        return l % r;
      }
      // Coerce booleans to numbers for comparison (Python: True==1, False==0)
      if (typeof l === "boolean") l = l ? 1 : 0;
      if (typeof r === "boolean") r = r ? 1 : 0;
      if (op === "<") return l < r;
      if (op === "<=") return l <= r;
      if (op === ">") return l > r;
      if (op === ">=") return l >= r;
      if (op === "==") return l == r;
      if (op === "!=") return l != r;
      if (op === "&&") return Boolean(l) && Boolean(r);
      if (op === "||") return Boolean(l) || Boolean(r);
    } catch (e) {
      runtimeErrors.push(`Runtime error in '${op}': ${e.message}`);
    }
    return 0;
  }

  function applyUnary(op, v) {
    if (op === "-") return -v;
    if (op === "!") return !Boolean(v);
    return v;
  }

  function isTruthy(v) {
    if (v === null || v === undefined) return false;
    if (typeof v === "boolean") return v;
    if (typeof v === "number") return v !== 0;
    if (typeof v === "string") return v.length > 0;
    return Boolean(v);
  }

  // ── format helpers ────────────────────────────────────────────────────────
  const SPEC_RE = /[#%][dfcsb]/g;

  function formatSpecifier(spec, value) {
    const kind = spec[spec.length - 1];
    if (kind === "d") return String(Math.trunc(Number(value)));
    if (kind === "f") return Number(value).toFixed(7);
    if (kind === "c")
      return typeof value === "number"
        ? String.fromCharCode(value)
        : String(value);
    if (kind === "s") return String(value);
    if (kind === "b") return value ? "solid" : "fragile";
    return String(value);
  }

  function formatView(fmt, args) {
    let clean = fmt;
    if (clean.startsWith('"') && clean.endsWith('"'))
      clean = clean.slice(1, -1);
    clean = clean.replace(
      /\\([ntv\\'"0])/g,
      (_, c) =>
        ({ n: "\n", t: "\t", "\\": "\\", "'": "'", '"': '"', 0: "\0" })[c] || c,
    );

    const specs = [...clean.matchAll(SPEC_RE)].map((m) => m[0]);
    if (!specs.length) {
      if (args.length) {
        const vals = args.map((a) => displayValue(a));
        return clean ? clean + " " + vals.join(" ") : vals.join(" ");
      }
      return clean;
    }
    let result = clean;
    specs.forEach((spec, i) => {
      if (i < args.length)
        result = result.replace(spec, formatSpecifier(spec, args[i]));
    });
    return result;
  }

  function displayValue(v) {
    if (v === null || v === undefined) return "";
    if (typeof v === "boolean") return v ? "solid" : "fragile";
    if (typeof v === "number" && !Number.isInteger(v))
      return parseFloat(v.toFixed(6)).toString();
    return String(v);
  }

  // ── async execution engine ────────────────────────────────────────────────
  // Uses an async generator so we can `yield` at write() and await user input.

  async function* execGen() {
    // execute globals (before first func_begin)
    for (let i = 0; i < instructions.length; i++) {
      if (instructions[i].op === "func_begin") break;
      yield* execOne(instructions[i], globalMem);
    }

    // call blueprint()
    if (!("blueprint" in funcMap)) return;
    pc = funcMap["blueprint"] + 1;
    callStack.push({
      name: "blueprint",
      locals: {},
      returnAddr: instructions.length,
      returnDest: null,
    });

    while (pc < instructions.length && callStack.length > 0) {
      iterCount++;
      if (iterCount > MAX_ITER) {
        runtimeErrors.push("Infinite loop detected");
        break;
      }
      const instr = instructions[pc++];
      yield* execOne(instr, currentMem());
    }
  }

  function* execOne(instr, mem) {
    const op = instr.op || "";

    if (op === "assign") {
      mem[instr.dest] = resolve(instr.src, mem);
    } else if (op === "binop") {
      const l = resolve(instr.left, mem);
      const r = resolve(instr.right, mem);
      mem[instr.dest] = applyBinop(instr.operator, l, r);
    } else if (op === "unary") {
      mem[instr.dest] = applyUnary(instr.operator, resolve(instr.operand, mem));
    } else if (op === "label" || op === "func_begin" || op === "func_end") {
      if (op === "func_end" && callStack.length) {
        const rec = callStack.pop();
        if (rec.returnDest !== null && rec.returnDest !== undefined) {
          currentMem()[rec.returnDest] = null;
        }
        pc = rec.returnAddr;
      }
    } else if (op === "jump") {
      if (instr.target in labelMap) pc = labelMap[instr.target];
    } else if (op === "jump_if") {
      if (isTruthy(resolve(instr.cond, mem)))
        if (instr.target in labelMap) pc = labelMap[instr.target];
    } else if (op === "jump_if_false") {
      if (!isTruthy(resolve(instr.cond, mem)))
        if (instr.target in labelMap) pc = labelMap[instr.target];
    } else if (op === "call") {
      const argVals = (instr.args || []).map((a) => resolve(a, mem));
      if (instr.func in funcMap) {
        const retAddr = pc;
        const fpc = funcMap[instr.func];
        const params = instructions[fpc].params || [];
        const locals = {};
        params.forEach((p, i) => {
          locals[p] = argVals[i] ?? 0;
        });
        callStack.push({
          name: instr.func,
          locals,
          returnAddr: retAddr,
          returnDest: instr.dest ?? null,
        });
        pc = fpc + 1;
      }
    } else if (op === "view") {
      const argVals = (instr.args || []).map((a) => resolve(a, mem));
      const text = formatView(instr.fmt || "", argVals);
      onOutput(text);
    } else if (op === "write") {
      // PAUSE here — ask the user for input, wait for their response.
      // Yield an object so the UI knows the expected type for validation.
      const args = instr.args || [];
      const fmt = instr.fmt || "";
      let cleanFmt = fmt;
      if (cleanFmt.startsWith('"') && cleanFmt.endsWith('"'))
        cleanFmt = cleanFmt.slice(1, -1);
      const specs = [...cleanFmt.matchAll(/[#%][dfcsb]/g)].map((m) => m[0]);

      for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        const spec = specs[i] ?? specs[0] ?? "#d";
        const kind = spec[spec.length - 1];

        // Suspend — UI will resume us with the raw string the user typed
        const raw = yield { signal: "INPUT", varName: arg, spec };

        // Convert (validation already done in handleSubmitInput before resume)
        let val;
        if (kind === "d") val = Math.trunc(Number(raw));
        else if (kind === "f") val = parseFloat(raw);
        else if (kind === "b")
          val = raw === "solid" || raw === "1" || raw === "true";
        else if (kind === "c") val = String(raw)[0] ?? "";
        else val = String(raw);

        mem[arg] = val;
      }
    } else if (op === "return") {
      const retVal =
        instr.value !== undefined ? resolve(instr.value, mem) : null;
      if (callStack.length) {
        const rec = callStack.pop();
        if (rec.returnDest !== null && rec.returnDest !== undefined) {
          currentMem()[rec.returnDest] = retVal;
        }
        pc = rec.returnAddr;
      }
    }
  }

  return { execGen, runtimeErrors };
}

// =============================================================================
// App
// =============================================================================

function App() {
  const [code, setCode] = useState(
    `tile blueprint() {\n\nwall welcome = "Hello World!";\n\nview("#s", welcome);
\nhome 0;\n\n}`,
  );
  const [editor, setEditor] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const [errors, setErrors] = useState([]);
  const [errorKind, setErrorKind] = useState(null);
  const [outputLines, setOutputLines] = useState([]); // {type: "out"|"in", text}
  const [waitingInput, setWaitingInput] = useState(false);
  const [inputValue, setInputValue] = useState("");

  const [annotations, setAnnotations] = useState([]);
  const [markers, setMarkers] = useState([]);

  // Generator runner state (persists across re-renders)
  const genRef = useRef(null);
  const resolverRef = useRef(null); // resolves the pending yield
  const outputRef = useRef(null); // scrolls terminal to bottom
  const inputMetaRef = useRef(null); // {varName, spec} from current write() pause

  useEffect(() => {
    if (outputRef.current)
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [outputLines, waitingInput]);

  // ── editor error highlighting ─────────────────────────────────────────────
  const applyErrorsToEditor = (errs) => {
    setAnnotations(
      errs.map((err) => ({
        row: (err.start_line ?? err.line ?? 1) - 1,
        column: (err.start_col ?? err.col ?? 1) - 1,
        text: err.message,
        type: "error",
      })),
    );
    setMarkers(
      errs.map((err) => {
        const startRow = (err.start_line ?? err.line ?? 1) - 1;
        const startCol = (err.start_col ?? err.col ?? 1) - 1;
        const endRow = (err.end_line ?? err.line ?? err.start_line ?? 1) - 1;
        const endColRaw =
          err.end_col ??
          (err.end_line ? 1 : (err.start_col ?? err.col ?? 1) + 1);
        return {
          startRow,
          startCol,
          endRow,
          endCol: Math.max(endColRaw - 1, startCol + 1),
          className: "lexer-error-marker",
          type: "text",
        };
      }),
    );
  };

  const handleErrorClick = (err) => {
    if (!editor) return;
    const row = (err.start_line ?? err.line ?? 1) - 1;
    const col = (err.start_col ?? err.col ?? 1) - 1;
    editor.focus();
    editor.gotoLine(row + 1, col, true);
    editor.selection.moveTo(row, col);
  };

  // ── step the async generator ──────────────────────────────────────────────
  async function stepGen(gen, inputVal = undefined) {
    let result;
    try {
      result =
        inputVal !== undefined ? await gen.next(inputVal) : await gen.next();
    } catch (e) {
      setOutputLines((prev) => [
        ...prev,
        { type: "err", text: `Runtime error: ${e.message}` },
      ]);
      setIsRunning(false);
      setWaitingInput(false);
      genRef.current = null;
      return;
    }

    if (result.done) {
      setIsRunning(false);
      setWaitingInput(false);
      genRef.current = null;
      return;
    }

    // Generator paused for input (new object form) or legacy string form
    const sig = result.value?.signal ?? result.value;
    if (sig === "INPUT") {
      inputMetaRef.current = result.value?.signal ? result.value : null;
      setWaitingInput(true);
      genRef.current = gen;
    } else {
      // Keep stepping synchronously
      await stepGen(gen, undefined);
    }
  }

  // ── Run button ────────────────────────────────────────────────────────────
  const handleRun = async () => {
    setIsLoading(true);
    setErrors([]);
    setErrorKind(null);
    setOutputLines([]);
    setWaitingInput(false);
    setInputValue("");
    genRef.current = null;
    inputMetaRef.current = null;
    applyErrorsToEditor([]);

    try {
      const response = await fetch("http://localhost:8000/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: code }),
      });
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const data = await response.json();

      const phaseErrors = Array.isArray(data.errors) ? data.errors : [];
      if (phaseErrors.length > 0) {
        const kind = (phaseErrors[0]?._kind ?? "semantic").toUpperCase();
        setErrors(phaseErrors);
        setErrorKind(kind);
        applyErrorsToEditor(phaseErrors);
        setIsLoading(false);
        return;
      }

      const instructions = data.instructions || [];
      setIsLoading(false);
      setIsRunning(true);

      // Build interpreter
      const { execGen, runtimeErrors } = createInterpreter(
        instructions,
        (text) => {
          // onOutput — called synchronously during execution
          setOutputLines((prev) => {
            const last = prev[prev.length - 1];
            // Append to last "out" line if no newline yet, else new entry
            if (last && last.type === "out" && !last.text.endsWith("\n"))
              return [
                ...prev.slice(0, -1),
                { type: "out", text: last.text + text },
              ];
            return [...prev, { type: "out", text }];
          });
        },
        null,
      );

      const gen = execGen();
      await stepGen(gen);
    } catch (err) {
      const fallback = [
        {
          message: `Cannot connect to backend: ${err.message}`,
          line: 1,
          col: 1,
        },
      ];
      setErrors(fallback);
      setErrorKind("BACKEND");
      applyErrorsToEditor(fallback);
      setIsLoading(false);
      setIsRunning(false);
    }
  };

  // ── input type validation ────────────────────────────────────────────────────
  // Phase 5: validate user input strictly against expected arCh type.
  // Returns null on success, or an error string on failure.
  const validateInput = (raw, meta) => {
    if (!meta) return null;
    const kind = meta.spec?.[meta.spec.length - 1];
    const name = meta.varName ?? "variable";
    const v = raw.trim();
    if (kind === "d") {
      if (v === "" || !/^-?\d+$/.test(v))
        return (
          "Invalid input: expected tile (integer) for variable '" + name + "'"
        );
      const n = Number(v);
      if (n < -999999999999999 || n > 999999999999999)
        return (
          "Invalid input: tile value out of range for variable '" + name + "'"
        );
    } else if (kind === "f") {
      if (v === "" || isNaN(Number(v)))
        return (
          "Invalid input: expected glass (float) for variable '" + name + "'"
        );
    } else if (kind === "c") {
      if (raw.length !== 1 || raw.charCodeAt(0) > 127)
        return (
          "Invalid input: expected brick (single ASCII character 0-127) for variable '" +
          name +
          "'"
        );
    } else if (kind === "b") {
      if (v !== "solid" && v !== "fragile")
        return (
          "Invalid input: expected beam (solid or fragile) for variable '" +
          name +
          "'"
        );
    }
    return null;
  };

  // ── user submits input ────────────────────────────────────────────────────
  const handleSubmitInput = async () => {
    const val = inputValue;
    const meta = inputMetaRef.current;

    const errMsg = validateInput(val, meta);
    if (errMsg) {
      // Invalid input — show error, stop execution (Phase 5: NO silent fallback)
      setOutputLines((prev) => [
        ...prev,
        { type: "in", text: val + "\n" },
        { type: "err", text: errMsg + "\n" },
      ]);
      setInputValue("");
      setWaitingInput(false);
      setIsRunning(false);
      genRef.current = null;
      inputMetaRef.current = null;
      return;
    }

    // Valid — echo and resume
    setInputValue("");
    setWaitingInput(false);
    inputMetaRef.current = null;
    setOutputLines((prev) => [...prev, { type: "in", text: val + "\n" }]);
    const gen = genRef.current;
    if (gen) await stepGen(gen, val);
  };

  const hasErrors = errors.length > 0;

  return (
    <div className="min-h-screen font-sans bg-[#111] text-gray-300">
      <header className="flex items-center p-4 border-b border-[#333] bg-[#1a1a1a]">
        <img
          src={archLogo}
          alt="arCh Compiler"
          className="h-10 md:h-16 object-contain"
        />
      </header>

      <div
        className="flex flex-col md:flex-row"
        style={{ height: "calc(100vh - 125px)" }}
      >
        {/* ── Left: editor ── */}
        <div className="flex flex-col w-full md:w-3/5 border-r border-[#333]">
          <div className="flex items-center justify-between p-2 border-b bg-[#222] border-[#333]">
            <h2 className="text-lg font-semibold">Source Code</h2>
            <button
              onClick={handleRun}
              disabled={isLoading || isRunning}
              className="px-6 py-2 bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:bg-gray-500"
            >
              {isLoading ? "Compiling…" : isRunning ? "Running…" : "Run"}
            </button>
          </div>
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

        {/* ── Right: output terminal ── */}
        <div className="flex flex-col w-full md:w-2/5">
          <div className="flex items-center p-2 border-b bg-[#222] border-[#333]">
            <h2 className="text-lg font-semibold py-1.5">Output</h2>
          </div>

          <div className="flex flex-col flex-1 overflow-hidden bg-[#0a0a0a]">
            {/* Error list */}
            {hasErrors && (
              <div className="p-2 space-y-1 overflow-auto">
                {errors.map((err, i) => {
                  const line = err.start_line ?? err.line ?? 1;
                  const col = err.start_col ?? err.col ?? 1;
                  return (
                    <div
                      key={i}
                      className="text-lg text-red-400 cursor-pointer hover:bg-red-900/30 rounded px-1 py-0.5"
                      onClick={() => handleErrorClick(err)}
                    >
                      Line {line}:{col} - {err.message}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Terminal — output + inline input */}
            {!hasErrors && (
              <div
                ref={outputRef}
                className="flex-1 overflow-auto p-3"
                style={{
                  fontFamily:
                    "'Monaco','Menlo','Consolas','Courier New',monospace",
                  fontSize: "20px",
                }}
              >
                {outputLines.map((line, i) => (
                  <span
                    key={i}
                    className={
                      line.type === "in"
                        ? "text-yellow-300"
                        : line.type === "err"
                          ? "text-red-400"
                          : "text-white"
                    }
                    style={{ whiteSpace: "pre" }}
                  >
                    {line.text}
                  </span>
                ))}

                {/* Inline input prompt — appears right after last output */}
                {waitingInput && (
                  <span className="inline-flex items-center">
                    <input
                      autoFocus
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSubmitInput();
                      }}
                      className="bg-transparent text-yellow-300 outline-none border-none"
                      style={{
                        fontFamily: "inherit",
                        fontSize: "inherit",
                        width: Math.max(inputValue.length + 1, 8) + "ch",
                        caretColor: "#fde047",
                      }}
                    />
                    <span className="animate-pulse text-yellow-300">█</span>
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
