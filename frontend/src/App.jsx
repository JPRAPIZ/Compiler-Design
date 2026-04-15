import React, { useState, useRef, useEffect } from "react";
import AceEditor from "react-ace";

import "ace-builds/src-noconflict/mode-text";
import "ace-builds/src-noconflict/theme-tomorrow_night";
import "ace-builds/src-noconflict/ext-language_tools";

import archLogo from "./assets/arCh.png";

// =============================================================================
// Custom Ace Mode for arCh — registered via editor onLoad callback
// =============================================================================

function registerArchMode(editor) {
  try {
    const session = editor.getSession();
    // Access the current mode's internals to build our custom highlight rules
    const currentMode = session.getMode();
    const currentRules = currentMode.$highlightRules;
    if (!currentRules) return;

    // Clone the highlight rules constructor pattern
    const RulesProto = Object.getPrototypeOf(currentRules);

    // Create new rules instance and override with arCh rules
    const archRules = Object.create(RulesProto);
    archRules.$rules = getArchRules();
    if (typeof archRules.normalizeRules === "function") {
      archRules.normalizeRules();
    }

    // Apply to the current mode
    currentMode.$highlightRules = archRules;
    currentMode.lineCommentStart = "//";
    currentMode.blockComment = { start: "/*", end: "*/" };

    // Force re-tokenization
    currentMode.$tokenizer = null;
    session.bgTokenizer.setTokenizer(currentMode.getTokenizer());
    session.bgTokenizer.start(0);
  } catch (_) {
    // Syntax highlighting not available — plain text fallback is fine
  }
}

function getArchRules() {
  return {
    start: [
      { token: "comment.line", regex: "//.*$" },
      { token: "comment.block", regex: "/\\*", next: "comment" },
      { token: "string.double", regex: '"(?:[^"\\\\]|\\\\.)*"' },
      { token: "string.single", regex: "'(?:[^'\\\\]|\\\\.)*'" },
      { token: "constant.numeric.float", regex: "\\b\\d+\\.\\d+\\b" },
      { token: "constant.numeric.integer", regex: "\\b\\d+\\b" },
      { token: "constant.language.boolean", regex: "\\b(?:solid|fragile)\\b" },
      {
        token: "storage.type",
        regex: "\\b(?:tile|glass|brick|wall|beam|field|house)\\b",
      },
      {
        token: "keyword.control",
        regex: "\\b(?:if|else|for|while|do|room|door|ground|crack|mend|home)\\b",
      },
      {
        token: "keyword.other",
        regex: "\\b(?:blueprint|view|write|cement|roof)\\b",
      },
      { token: "constant.other.placeholder", regex: "#(?:\\.\\d+)?[dfcsb]" },
      {
        token: "keyword.operator",
        regex: "\\+\\+|--|&&|\\|\\||[+\\-*/%]=?|[<>!=]=?|!|=",
      },
      { token: "identifier", regex: "[a-zA-Z_][a-zA-Z0-9_]*" },
      { token: "paren.lparen", regex: "[({\\[]" },
      { token: "paren.rparen", regex: "[)}\\]]" },
      { token: "punctuation", regex: "[;,\\.:]" },
      { token: "text", regex: "\\s+" },
    ],
    comment: [
      { token: "comment.block", regex: "\\*/", next: "start" },
      { defaultToken: "comment.block" },
    ],
  };
}

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
    // Flat-key array access: resolve "arr[i]" by resolving index variables
    if (operand.includes("[")) {
      const resolved = resolveDestKey(operand, mem);
      if (resolved in mem) return mem[resolved];
      if (mem !== globalMem && resolved in globalMem) return globalMem[resolved];
      // Wall character indexing: wall[i] → charCode of character at index
      const m = resolved.match(/^(\w+)\[(\d+)\]$/);
      if (m) {
        const baseVal = resolve(m[1], mem);
        if (typeof baseVal === "string") {
          const idx = Math.trunc(Number(m[2]));
          return idx >= 0 && idx < baseVal.length ? baseVal.charCodeAt(idx) : 0;
        }
      }
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

  // Resolve variable indices in dest/src keys: "arr[i]" → "arr[3]"
  function resolveDestKey(key, mem) {
    const m = key.match(/^(\w+)((?:\[[^\]]+\])+)$/);
    if (!m) return key;
    const base = m[1];
    const idxExprs = [...m[2].matchAll(/\[([^\]]+)\]/g)].map(x => x[1]);
    const parts = idxExprs.map(expr => {
      const v = resolve(expr, mem);
      return typeof v === "number" ? String(Math.trunc(v)) : String(v);
    });
    return base + parts.map(p => `[${p}]`).join("");
  }

  // ── arithmetic ────────────────────────────────────────────────────────────
  function applyBinop(op, l, r) {
    try {
      // Coerce booleans to numbers for arithmetic and comparison
      // (arCh: solid=1, fragile=0 in all numeric contexts)
      if (typeof l === "boolean") l = l ? 1 : 0;
      if (typeof r === "boolean") r = r ? 1 : 0;
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

  // ── implicit type conversion ────────────────────────────────────────────
  function coerceToType(value, targetType) {
    if (!targetType) return value;
    if (targetType === "tile") {
      if (typeof value === "boolean") return value ? 1 : 0;
      if (typeof value === "number") return Math.trunc(value);
      return Math.trunc(Number(value)) || 0;
    }
    if (targetType === "glass") {
      if (typeof value === "boolean") return value ? 1.0 : 0.0;
      return Number(value) || 0.0;
    }
    if (targetType === "brick") {
      let v = typeof value === "boolean" ? (value ? 1 : 0) :
              typeof value === "number" ? Math.trunc(value) : (parseInt(value, 10) || 0);
      return ((v % 128) + 128) % 128;
    }
    if (targetType === "beam") {
      if (typeof value === "boolean") return value;
      if (typeof value === "number") return value !== 0;
      return Boolean(value);
    }
    return value;
  }

  function isTruthy(v) {
    if (v === null || v === undefined) return false;
    if (typeof v === "boolean") return v;
    if (typeof v === "number") return v !== 0;
    if (typeof v === "string") return v.length > 0;
    return Boolean(v);
  }

  // ── global memory routing (mirrors Python _target_mem) ────────────────────
  // When a function writes to a global variable (e.g. roof tile arr[100]),
  // the destination key must be stored in globalMem, not the local scope.
  // Temporaries (t1, t2, ...) always stay in local memory.
  function targetMem(dest, mem) {
    if (mem === globalMem) return mem;
    // Temporaries always stay local
    if (/^t\d+$/.test(dest)) return mem;
    const base = dest.split("[")[0].split(".")[0];
    // If base exists in local memory, store locally
    if (base in mem) return mem;
    // If base or any flat key exists in global memory, store globally
    if (base in globalMem) return globalMem;
    if (dest.includes("[") || dest.includes(".")) {
      const prefix = dest.includes("[") ? base + "[" : base + ".";
      for (const k of Object.keys(globalMem)) {
        if (k.startsWith(prefix)) return globalMem;
      }
    }
    return mem;
  }

  // ── format helpers ────────────────────────────────────────────────────────
  // arCh uses # exclusively — % is not a valid format prefix
  // Supports: #d, #f, #c, #s, #b, and #.Nf (precision, e.g. #.2f)
  const SPEC_RE = /#(?:\.\d+)?[dfcsb]/g;

  function formatSpecifier(spec, value) {
    const kind = spec[spec.length - 1];
    // Extract precision for #.Nf (e.g. "#.2f" → 2)
    let precision = null;
    const dotIdx = spec.indexOf(".");
    if (dotIdx !== -1) {
      precision = parseInt(spec.slice(dotIdx + 1, -1), 10);
    }
    if (kind === "d") return String(Math.trunc(Number(value)));
    if (kind === "f") return Number(value).toFixed(precision !== null ? precision : 7);
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
      let dest = instr.dest;
      if (dest.includes("[")) dest = resolveDestKey(dest, mem);
      let val = resolve(instr.src, mem);
      if (instr.dest_type) val = coerceToType(val, instr.dest_type);
      targetMem(dest, mem)[dest] = val;
    } else if (op === "binop") {
      const l = resolve(instr.left, mem);
      const r = resolve(instr.right, mem);
      let bDest = instr.dest;
      if (bDest.includes("[")) bDest = resolveDestKey(bDest, mem);
      targetMem(bDest, mem)[bDest] = applyBinop(instr.operator, l, r);
    } else if (op === "unary") {
      let uDest = instr.dest;
      if (uDest.includes("[")) uDest = resolveDestKey(uDest, mem);
      targetMem(uDest, mem)[uDest] = applyUnary(instr.operator, resolve(instr.operand, mem));
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
      //
      // Spec K.2 §13 / F.9 — brick array with #s:
      //   When #s is used with a bare brick array name, the runtime reads a
      //   wall (string) input and stores each character as its char code into
      //   sequential flat keys: chars[0], chars[1], chars[2], ...
      const args = instr.args || [];
      const fmt = instr.fmt || "";
      let cleanFmt = fmt;
      if (cleanFmt.startsWith('"') && cleanFmt.endsWith('"'))
        cleanFmt = cleanFmt.slice(1, -1);
      const specs = [...cleanFmt.matchAll(/#(?:\.\d+)?[dfcsb]/g)].map((m) => m[0]);

      for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        // Resolve variable indices in destination key (e.g. "A[i]" → "A[3]")
        const dest = arg.includes("[") ? resolveDestKey(arg, mem) : arg;
        const spec = specs[i] ?? specs[0] ?? "#d";
        const kind = spec[spec.length - 1];

        // ── Spec K.2 §13 / F.9: detect brick array with #s ──────────────
        // If kind is 's' and dest is a bare name (no subscript) and flat keys
        // like dest[0] exist in memory, this is a brick array string input.
        let isBrickArrayS = false;
        let brickTargetMem = mem;   // where the brick array flat keys live
        if (kind === "s" && !dest.includes("[")) {
          const firstKey = `${dest}[0]`;
          if (firstKey in mem) {
            isBrickArrayS = true;
          } else if (mem !== globalMem && firstKey in globalMem) {
            isBrickArrayS = true;
            brickTargetMem = globalMem;
          }
        }

        // Suspend — UI will resume us with the raw string the user typed
        const raw = yield { signal: "INPUT", varName: dest, spec };

        if (isBrickArrayS) {
          // Spec K.2 §13: store string char-by-char into brick array
          const str = String(raw);
          for (let ci = 0; ci < str.length; ci++) {
            brickTargetMem[`${dest}[${ci}]`] = str.charCodeAt(ci);
          }
        } else {
          // Standard conversion per format specifier type
          let val;
          if (kind === "d") val = Math.trunc(Number(raw));
          else if (kind === "f") val = parseFloat(raw);
          else if (kind === "b")
            val = raw === "solid" || raw === "1" || raw === "true";
          else if (kind === "c") val = String(raw)[0] ?? "";
          else val = String(raw);

          // Route to the correct memory (local vs global).
          // If the base variable lives in global memory (e.g. a roof array),
          // store the value there instead of in local scope.
          const baseName = dest.split("[")[0].split(".")[0];
          let writeMem = mem;
          if (mem !== globalMem) {
            if (!(baseName in mem) && baseName in globalMem) {
              writeMem = globalMem;
            } else if (dest.includes("[") && !(baseName in mem)) {
              // Check if any flat key for this array base lives in globalMem
              const prefix = baseName + "[";
              for (const k of Object.keys(globalMem)) {
                if (k.startsWith(prefix)) { writeMem = globalMem; break; }
              }
            }
          }
          writeMem[dest] = val;
        }
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

    } else if (op === "array_read" || op === "struct_read") {
      // Resolve subscript/member access: "arr[i]" → resolve index, build flat key
      const src = instr.src;
      let val;
      if (src.includes("[")) {
        // Array read: resolve variable indices and look up flat key
        val = resolve(resolveDestKey(src, mem), mem);
      } else if (src.includes(".")) {
        // Struct read: try flat key "s.field"
        const resolved = src;
        val = (resolved in mem) ? mem[resolved] :
              (mem !== globalMem && resolved in globalMem) ? globalMem[resolved] : 0;
      } else {
        val = resolve(src, mem);
      }
      mem[instr.dest] = val;
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

  const [fileName, setFileName] = useState("untitled.arCh");
  const [isDirty, setIsDirty] = useState(false);
  const [cursorPos, setCursorPos] = useState({ row: 1, col: 1 });
  const [editorWidth, setEditorWidth] = useState(60); // percentage

  // Generator runner state (persists across re-renders)
  const genRef = useRef(null);
  const resolverRef = useRef(null); // resolves the pending yield
  const outputRef = useRef(null); // scrolls terminal to bottom
  const inputMetaRef = useRef(null); // {varName, spec} from current write() pause
  const fileInputRef = useRef(null); // hidden file input for upload
  const savedCodeRef = useRef(code); // tracks last saved content for dirty detection
  const containerRef = useRef(null); // main split container for resize

  useEffect(() => {
    if (outputRef.current)
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [outputLines, waitingInput]);

  // ── dirty tracking ───────────────────────────────────────────────────────
  const handleCodeChange = (newCode) => {
    setCode(newCode);
    setIsDirty(newCode !== savedCodeRef.current);
  };

  // ── cursor position tracking + syntax highlighting ────────────────────
  const handleEditorLoad = (ed) => {
    setEditor(ed);
    ed.selection.on("changeCursor", () => {
      const pos = ed.getCursorPosition();
      setCursorPos({ row: pos.row + 1, col: pos.column + 1 });
    });
    // Register arCh syntax highlighting after editor is fully loaded
    setTimeout(() => registerArchMode(ed), 50);
  };

  // ── keyboard shortcuts ───────────────────────────────────────────────────
  useEffect(() => {
    const onKeyDown = (e) => {
      const ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.key === "s") {
        e.preventDefault();
        handleDownload();
      } else if (ctrl && e.key === "o") {
        e.preventDefault();
        fileInputRef.current?.click();
      } else if ((ctrl && e.key === "Enter") || e.key === "F5") {
        e.preventDefault();
        if (!isLoading && !isRunning) handleRun();
      } else if (ctrl && e.key === "n") {
        e.preventDefault();
        handleNewFile();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  // ── warn on tab close with unsaved changes ────────────────────────────
  useEffect(() => {
    const onBeforeUnload = (e) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty]);

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
        const kind = (phaseErrors[0]?.kind ?? "semantic").toUpperCase();
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

  // ── file management ─────────────────────────────────────────────────────
  const handleNewFile = () => {
    if (isDirty && !window.confirm("You have unsaved changes. Start a new file anyway?")) return;
    const defaultCode = `tile blueprint() {\n\n\nhome 0;\n\n}`;
    setCode(defaultCode);
    savedCodeRef.current = defaultCode;
    setFileName("untitled.arCh");
    setIsDirty(false);
    setErrors([]);
    setErrorKind(null);
    setOutputLines([]);
    applyErrorsToEditor([]);
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    savedCodeRef.current = code;
    setIsDirty(false);
  };

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (isDirty && !window.confirm("You have unsaved changes. Open a new file anyway?")) {
      e.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      const content = ev.target.result;
      setCode(content);
      savedCodeRef.current = content;
      setFileName(file.name);
      setIsDirty(false);
      // Clear previous results when loading a new file
      setErrors([]);
      setErrorKind(null);
      setOutputLines([]);
      applyErrorsToEditor([]);
    };
    reader.readAsText(file);
    // Reset so the same file can be re-uploaded
    e.target.value = "";
  };

  const handleClear = () => {
    setErrors([]);
    setErrorKind(null);
    setOutputLines([]);
    setWaitingInput(false);
    setInputValue("");
    genRef.current = null;
    inputMetaRef.current = null;
    applyErrorsToEditor([]);
    setIsRunning(false);
  };

  const handleStop = () => {
    genRef.current = null;
    inputMetaRef.current = null;
    setIsRunning(false);
    setWaitingInput(false);
    setInputValue("");
    setOutputLines((prev) => [
      ...prev,
      { type: "err", text: "Program stopped.\n" },
    ]);
  };

  // ── panel resize drag ─────────────────────────────────────────────────
  const handleDragStart = (e) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const onMove = (ev) => {
      const clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const pct = ((clientX - rect.left) / rect.width) * 100;
      setEditorWidth(Math.min(Math.max(pct, 25), 80));
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", onUp);
  };

  const hasErrors = errors.length > 0;
  const hasOutput = outputLines.length > 0 || hasErrors;
  const displayName = (isDirty ? "● " : "") + fileName;

  return (
    <div className="flex flex-col h-screen font-sans bg-[#111] text-gray-300">
      <header className="flex items-center p-4 border-b border-[#333] bg-[#1a1a1a] shrink-0">
        <img
          src={archLogo}
          alt="arCh Compiler"
          className="h-10 md:h-16 object-contain"
        />
      </header>

      <div ref={containerRef} className="flex flex-col md:flex-row flex-1 min-h-0">
        {/* ── Left: editor ── */}
        <div
          className="flex flex-col border-r border-[#333] min-h-0"
          style={{ width: "100%", flex: `0 0 ${editorWidth}%` }}
        >
          {/* Toolbar */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b bg-[#222] border-[#333] shrink-0 flex-wrap gap-1">
            <div className="flex items-center gap-2 min-w-0">
              <h2 className="text-lg font-semibold whitespace-nowrap">Source Code</h2>
              <span
                className="text-sm text-gray-400 truncate max-w-[200px] hidden sm:inline"
                title={fileName + (isDirty ? " (unsaved)" : "")}
              >
                — {displayName}
              </span>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".arCh,.arch,.txt"
                onChange={handleUpload}
                className="hidden"
              />
              <button
                onClick={handleNewFile}
                title="New file (Ctrl+N)"
                className="px-3 py-1.5 bg-[#333] text-gray-300 font-semibold hover:bg-[#444] rounded text-sm"
              >
                New
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                title="Open .arCh file (Ctrl+O)"
                className="px-3 py-1.5 bg-[#333] text-gray-300 font-semibold hover:bg-[#444] rounded text-sm"
              >
                Open
              </button>
              <button
                onClick={handleDownload}
                title="Save as .arCh file (Ctrl+S)"
                className="px-3 py-1.5 bg-[#333] text-gray-300 font-semibold hover:bg-[#444] rounded text-sm"
              >
                Save
              </button>
              {isRunning ? (
                <button
                  onClick={handleStop}
                  className="px-5 py-1.5 bg-red-600 text-white font-semibold hover:bg-red-700 rounded text-sm"
                >
                  Stop
                </button>
              ) : (
                <button
                  onClick={handleRun}
                  disabled={isLoading}
                  title="Run program (Ctrl+Enter / F5)"
                  className="px-5 py-1.5 bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:bg-gray-500 rounded text-sm"
                >
                  {isLoading ? "Compiling…" : "Run"}
                </button>
              )}
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 min-h-0">
            <AceEditor
              mode="text"
              theme="tomorrow_night"
              onChange={handleCodeChange}
              value={code}
              name="SOURCE_CODE_EDITOR"
              editorProps={{ $blockScrolling: true }}
              onLoad={handleEditorLoad}
              setOptions={{
                useWorker: false,
                showLineNumbers: true,
                tabSize: 4,
                useSoftTabs: true,
                highlightActiveLine: true,
                highlightSelectedWord: true,
                showPrintMargin: false,
              }}
              width="100%"
              height="100%"
              style={{ backgroundColor: "#0a0a0a" }}
              fontSize={20}
              annotations={annotations}
              markers={markers}
            />
          </div>

          {/* Status bar */}
          <div className="flex items-center justify-between px-3 py-1 bg-[#1a1a1a] border-t border-[#333] text-xs text-gray-500 shrink-0">
            <span>Ln {cursorPos.row}, Col {cursorPos.col}</span>
            <span className="hidden sm:inline">{displayName}</span>
            <span>arCh</span>
          </div>
        </div>

        {/* ── Resize handle ── */}
        <div
          className="hidden md:flex items-center justify-center w-1.5 cursor-col-resize bg-[#222] hover:bg-blue-600/40 active:bg-blue-600/60 transition-colors shrink-0 select-none"
          onMouseDown={handleDragStart}
          onTouchStart={handleDragStart}
          title="Drag to resize panels"
        />

        {/* ── Right: output terminal ── */}
        <div className="flex flex-col flex-1 min-h-0 min-w-0">
          <div className="flex items-center justify-between px-3 py-2 border-b bg-[#222] border-[#333] shrink-0">
            <h2 className="text-lg font-semibold py-1">Output</h2>
            <button
              onClick={handleClear}
              title="Clear output"
              className="px-3 py-1.5 mr-1 bg-[#333] text-gray-300 font-semibold hover:bg-[#444] rounded text-sm"
            >
              Clear
            </button>
          </div>

          <div className="flex flex-col flex-1 overflow-hidden bg-[#0a0a0a] min-h-0">
            {/* Error list */}
            {hasErrors && (
              <div className="p-2 space-y-1 overflow-auto">
                {errors.map((err, i) => {
                  const line = err.start_line ?? err.line ?? 1;
                  const col = err.start_col ?? err.col ?? 1;
                  return (
                    <div
                      key={i}
                      className="text-base text-red-400 cursor-pointer hover:bg-red-900/30 rounded px-1 py-0.5"
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
                  fontSize: "18px",
                }}
              >
                {/* Empty state placeholder */}
                {!hasOutput && !isRunning && (
                  <div className="flex flex-col items-center justify-center h-full text-gray-600 select-none">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mb-3 opacity-40">
                      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                      <polyline points="13 2 13 9 20 9" />
                    </svg>
                    <p className="text-sm">Press <span className="text-gray-400 font-mono">Run</span> or <span className="text-gray-400 font-mono">Ctrl+Enter</span> to compile &amp; run</p>
                  </div>
                )}

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