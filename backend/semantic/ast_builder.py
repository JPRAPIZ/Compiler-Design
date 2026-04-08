# ===========================================================================
# ast_builder.py — AST Construction from Token Stream
# ===========================================================================
#
# ROLE IN THE PIPELINE
# --------------------
# ASTBuilder is the bridge between the Parser/Lexer and the SemanticAnalyzer.
# It consumes the same flat token list that the Parser already validated and
# produces a typed ProgramNode tree.
#
# IMPORTANT: ASTBuilder is called AFTER the Parser has confirmed there are no
# syntax errors.  It therefore does NOT need to re-validate syntax.  When it
# encounters something unexpected it simply skips tokens and continues so
# that semantic analysis can still proceed.
#
# DEPENDENCIES
# ------------
#   - Imports all node types from semantic/ast.py.
#   - Receives a token list from the caller (ParserV2 output).
#   - Has NO knowledge of the SymbolTable or SemanticAnalyzer.
#
# DATA FLOW
# ---------
#   token list (whitespace/comment tokens already present)
#       │
#       ▼ (ASTBuilder filters IGNORE_TYPES on construction)
#   filtered token list
#       │
#       ▼ build_program()
#   ProgramNode
#       ├── globals  list  (GlobalDeclNode subclasses)
#       └── functions list (FunctionNode)
#
# GRAMMAR CORRESPONDENCE
# ----------------------
# Each private method maps to one grammar production:
#   _program()           → <program>
#   _global()            → <global>  (roof declarations)
#   _global_dec()        → <global_dec>
#   _global_var()        → global variable declaration
#   _global_const()      → global constant declaration
#   _structure_global()  → struct definition or variable instantiation
#   _program_body()      → <program_body>  (function definitions)
#   _function_def()      → function definition
#   _param_list/_param() → parameter list
#   _func_body_stmts()   → function body
#   _body_item()         → one declaration or statement
#   _local_var_decl()    → local variable declaration (returns LIST)
#   _local_struct_decl() → local struct instantiation (returns LIST)
#   _local_const_decl()  → local constant declaration (returns LIST)
#   _statement()         → dispatcher for all statement types
#   _if/switch/for/while/dowhile/break/continue/return_statement()
#   _io_statement()      → view() / write()
#   _assign_or_call()    → assignment or standalone function call
#   _expression()        → general expression
#   _binary_expr()       → binary operators
#   _unary_or_primary()  → unary operators and primary expressions
#   _primary()           → literals, identifiers, parenthesised expressions
#   _id_expr()           → identifier possibly followed by (), [], .
#   _value_literal()     → consume and wrap a literal token
#   _wall_init_expr()    → wall concatenation expression
#   _func_args()         → comma-separated argument list
#
# MULTI-VARIABLE DECLARATIONS
# ---------------------------
# tile a = 1, b = 2, c = 3;  is a single statement in the grammar but
# produces THREE VarDeclNode objects.  _local_var_decl(), _local_struct_decl(),
# and _local_const_decl() therefore return List[VarDeclNode].
# _func_body_stmts() uses extend() to flatten these lists into the body.
#
# TAC READINESS NOTE
# ------------------
# ASTBuilder does NOT set expr_type on any node.  All expr_type fields are
# None after this phase.  The SemanticAnalyzer fills them in.  A TAC generator
# must only be invoked after semantic analysis is complete.
#
# ===========================================================================

from typing import List, Optional, Any
from semantic.ast import (
    ProgramNode, FunctionNode, ParamNode,
    GlobalDeclNode, VarDeclNode, StructDeclNode, StructMemberNode,
    StatementNode, AssignNode, IfNode, WhileNode, DoWhileNode,
    ForNode, SwitchNode, CaseNode, BreakNode, ContinueNode,
    ReturnNode, IONode,
    ExprNode, BinaryOpNode, UnaryOpNode, LiteralNode,
    IdNode, ArrayAccessNode, StructAccessNode, FunctionCallNode,
    WallConcatNode, ArrayInitNode,
)


# ---------------------------------------------------------------------------
# Module-level constants and token helpers
# ---------------------------------------------------------------------------
# These constants are used throughout the builder to classify and map tokens.
# They mirror the token-type strings emitted by the arCh Lexer.

# Token types that carry no semantic meaning and should be discarded before
# any tree-building begins.
IGNORE_TYPES = ("space", "tab", "newline", "Single-Line Comment", "Multi-Line Comment")

# Maps lexer token types for literal values to the corresponding arCh type name.
# Used in _value_literal() and _case_value() to set LiteralNode.literal_type.
LITERAL_TO_TYPE = {
    "tile_lit":  "tile",
    "glass_lit": "glass",
    "brick_lit": "brick",
    "wall_lit":  "wall",
    "solid":     "beam",
    "fragile":   "beam",
}

# The set of primitive data-type keywords (excludes 'house' and 'field').
DATA_TYPES = {"tile", "glass", "brick", "beam", "wall"}


def _norm(token_type: str) -> str:
    """Normalise numbered identifier token types to 'id'.

    The Lexer emits id1, id2, id3, ... for identifiers in different positions.
    This mirrors the normalisation done in parserV2 so that all identifier
    tokens can be matched with a single string 'id'.
    """
    if isinstance(token_type, str) and token_type.startswith("id"):
        return "id"
    return token_type


# ---------------------------------------------------------------------------
# ASTBuilder class
# ---------------------------------------------------------------------------

class ASTBuilder:
    """Builds a ProgramNode AST from an already-lexed and validated token list.

    Usage
    -----
        builder = ASTBuilder(token_list)
        program_node = builder.build_program()

    The constructor filters out whitespace and comment tokens immediately so
    that all parsing methods see a compact sequence of meaningful tokens.
    """

    def __init__(self, tokens):
        # Filter insignificant tokens once upfront.
        self.tokens = [
            t for t in (tokens or [])
            if getattr(t, "tokenType", None) not in IGNORE_TYPES
        ]
        self.pos = 0  # index into self.tokens

    # -----------------------------------------------------------------------
    # Low-level token cursor helpers
    # -----------------------------------------------------------------------
    # These methods form the primitive vocabulary of the builder.  All higher-
    # level methods are built exclusively from these five operations:
    #   _cur()     — inspect without consuming
    #   _type()    — normalised type of current token
    #   _lexeme()  — raw text of current token
    #   _advance() — consume and return current token
    #   _eat()     — consume current token (type is asserted by the caller,
    #                but NOT enforced here because syntax was pre-validated)
    #   _peek()    — look ahead without consuming

    def _cur(self):
        """Return the current token, or None at EOF."""
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _type(self) -> str:
        """Return the normalised type of the current token ('EOF' at end)."""
        t = self._cur()
        if t is None:
            return "EOF"
        return _norm(t.tokenType)

    def _lexeme(self) -> str:
        """Return the raw lexeme of the current token ('' at EOF)."""
        t = self._cur()
        return t.lexeme if t else ""

    def _line(self) -> int:
        """Return the source line of the current token (1 at EOF)."""
        t = self._cur()
        return t.line if t else 1

    def _col(self) -> int:
        """Return the source column of the current token (1 at EOF)."""
        t = self._cur()
        return t.column if t else 1

    def _advance(self):
        """Consume and return the current token (advances position)."""
        tok = self._cur()
        self.pos += 1
        return tok

    def _eat(self, expected: str):
        """Consume the current token.

        The `expected` parameter is informational — it documents what the
        grammar requires but is NOT checked at runtime because the parser has
        already validated syntax.  Mismatches here indicate a builder bug,
        not a user error.
        """
        tok = self._cur()
        self.pos += 1
        return tok

    def _peek(self, offset: int = 1) -> str:
        """Return the normalised type of the token `offset` positions ahead.

        Used for one-token look-ahead decisions (e.g. distinguishing
        struct definition from struct variable instantiation).
        """
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return "EOF"
        return _norm(self.tokens[idx].tokenType)

    def _is(self, *types) -> bool:
        """Return True if the current token's type matches any of `types`."""
        return self._type() in types

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    def build_program(self) -> Optional[ProgramNode]:
        """Parse the full token stream and return a ProgramNode.

        On unexpected failure, returns an empty ProgramNode rather than
        propagating an exception so that later pipeline stages see a valid
        (if empty) tree.
        """
        try:
            return self._program()
        except Exception:
            return ProgramNode(globals=[], functions=[], line=1, col=1)

    # -----------------------------------------------------------------------
    # Top-level program structure
    # -----------------------------------------------------------------------
    # <program> → <global> <program_body>

    def _program(self) -> ProgramNode:
        """Parse the root program node."""
        line, col = self._line(), self._col()
        globals_list = self._global()
        functions = self._program_body()
        return ProgramNode(globals=globals_list, functions=functions,
                           line=line, col=col)

    # -----------------------------------------------------------------------
    # Global declarations  (the 'roof' section)
    # -----------------------------------------------------------------------
    # <global> → (roof <global_dec> ;)*
    #
    # Zero or more 'roof'-prefixed declarations appear before any function.
    # Each can be a variable, a constant, or a struct definition.

    def _global(self) -> List[GlobalDeclNode]:
        """Consume all 'roof' declarations and return the list of nodes."""
        decls = []
        while self._is("roof"):
            self._eat("roof")
            d = self._global_dec()
            if d:
                decls.append(d)
            self._eat(";")
        return decls

    def _global_dec(self) -> Optional[GlobalDeclNode]:
        """Dispatch to the correct global declaration parser."""
        if self._is("wall", "tile", "glass", "brick", "beam"):
            return self._global_var()
        elif self._is("house"):
            return self._structure_global()
        elif self._is("cement"):
            return self._global_const()
        return None

    # ── Global variable declarations ─────────────────────────────────────────

    def _global_var(self) -> Optional[VarDeclNode]:
        """Parse a global primitive-type variable declaration.

        Handles: type id [= literal] [, id [= literal]] ...
        and:     type id [dim][dim]  (array form)
        wall variables use _global_wall_end() to handle string initialisers.
        """
        line, col = self._line(), self._col()
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        if dtype == "wall":
            init_val, _ = self._global_wall_end()
            return VarDeclNode(type="wall", name=name, init_value=init_val,
                               is_const=False, is_array=False, array_dims=None,
                               line=line, col=col)
        else:
            init_val, is_array, dims = self._global_end()
            return VarDeclNode(type=dtype, name=name, init_value=init_val,
                               is_const=False, is_array=is_array, array_dims=dims,
                               line=line, col=col)

    def _data_type_str(self) -> str:
        """Consume one data-type keyword token and return its lexeme string."""
        tok = self._advance()
        return tok.lexeme if tok else "tile"

    def _global_end(self):
        """Parse the tail of a non-wall global declaration.

        Returns a tuple (init_expr_or_None, is_array, dims).
        Array declarations have no init_expr (brace initializers are skipped).
        """
        if self._is("["):
            dims, arr_init = self._array_dec_dims()
            return arr_init, True, dims
        else:
            init_val = self._global_init_expr()
            # Skip any additional comma-separated names in the same statement
            while self._is(","):
                self._eat(",")
                self._eat("id")
                self._global_init_expr()
            return init_val, False, None

    def _global_init_expr(self) -> Optional[ExprNode]:
        """Parse an optional '= literal' initialiser for a global variable."""
        if self._is("="):
            self._eat("=")
            return self._value_literal()
        return None

    def _global_wall_end(self):
        """Parse the tail of a global wall (string) declaration.

        Returns (init_expr_or_None, is_array).
        """
        if self._is("["):
            self._wall_array_skip()
            return None, True
        else:
            init_val = self._global_wall_init_expr()
            while self._is(","):
                self._eat(",")
                self._eat("id")
                self._global_wall_init_expr()
            return init_val, False

    def _global_wall_init_expr(self) -> Optional[LiteralNode]:
        """Parse an optional '= wall_lit' initialiser for a global wall variable."""
        if self._is("="):
            self._eat("=")
            line, col = self._line(), self._col()
            tok = self._eat("wall_lit")
            return LiteralNode(value=tok.lexeme if tok else "", literal_type="wall",
                               line=line, col=col)
        return None

    # ── Array dimension parsing helpers ──────────────────────────────────────

    def _array_dec_dims(self):
        """Consume [size?][size?] array declaration brackets.

        Returns (dims, init_node):
          dims      — list of int dimension sizes
          init_node — ArrayInitNode if '= { ... }' was present, else None
        """
        dims = []
        self._eat("[")
        if self._is("tile_lit"):
            dims.append(int(self._advance().lexeme))
        else:
            dims.append(0)
        self._eat("]")
        init_node = None
        # possible second dimension
        if self._is("["):
            self._eat("[")
            if self._is("tile_lit"):
                dims.append(int(self._advance().lexeme))
            else:
                dims.append(0)
            self._eat("]")
            if self._is("="):
                init_node = self._parse_brace_init()
        elif self._is("="):
            init_node = self._parse_brace_init()
        return dims, init_node

    def _wall_array_skip(self):
        """Skip a wall array declaration entirely (wall arrays are not supported)."""
        self._eat("[")
        while not self._is("]", "EOF"):
            self._advance()
        self._eat("]")
        while self._is("["):
            self._eat("[")
            while not self._is("]", "EOF"):
                self._advance()
            self._eat("]")
        if self._is("="):
            self._skip_brace_init()

    def _skip_brace_init(self):
        """Skip a brace initializer block without parsing values.

        Used for struct initializers where full parsing isn't needed.
        """
        self._eat("=")
        self._consume_braces()

    def _consume_braces(self):
        """Consume a balanced { ... } block, discarding content."""
        depth = 0
        while not self._is("EOF"):
            if self._is("{"):
                depth += 1
                self._advance()
            elif self._is("}"):
                depth -= 1
                self._advance()
                if depth == 0:
                    break
            else:
                self._advance()

    def _parse_brace_init(self) -> 'ArrayInitNode':
        """Parse a brace initializer: = { val1, val2, ... } or = { {r1}, {r2} }.

        Returns an ArrayInitNode containing the parsed element expressions.
        Handles both 1-D arrays ({1, 2, 3}) and 2-D arrays ({{1,2},{3,4}}).
        """
        line, col = self._line(), self._col()
        self._eat("=")
        return self._parse_brace_list(line, col)

    def _parse_brace_list(self, line=None, col=None) -> 'ArrayInitNode':
        """Parse { val, val, ... } or { {row}, {row}, ... }."""
        if line is None:
            line, col = self._line(), self._col()
        self._eat("{")
        elements = []

        if self._is("}"):
            # Empty initializer
            self._eat("}")
            return ArrayInitNode(elements=[], line=line, col=col)

        if self._is("{"):
            # 2-D: nested brace lists
            elements.append(self._parse_brace_list())
            while self._is(","):
                self._eat(",")
                if self._is("{"):
                    elements.append(self._parse_brace_list())
                else:
                    break
        else:
            # 1-D: comma-separated values
            elements.append(self._expression())
            while self._is(","):
                self._eat(",")
                if self._is("}"):
                    break
                elements.append(self._expression())

        self._eat("}")
        return ArrayInitNode(elements=elements, line=line, col=col)

    # ── Struct global declaration ─────────────────────────────────────────────

    def _structure_global(self) -> Optional[StructDeclNode]:
        """Parse a 'house' declaration at global scope.

        Two forms are handled:
          1. Struct TYPE definition:  house Name { members } [var] ;
             → returns StructDeclNode
          2. Struct VARIABLE instantiation: house TypeName varName [= {...}] ;
             → returns None (ASTBuilder cannot construct VarDeclNode here
               without knowing whether TypeName is a valid struct — that is
               the semantic analyzer's job).
        """
        line, col = self._line(), self._col()
        self._eat("house")
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        if self._is("{"):
            # Form 1: struct type definition
            self._eat("{")
            members = self._struct_members()
            self._eat("}")
            # Optional variable instance after the closing brace — skip it
            if self._is("id"):
                self._eat("id")
                if self._is("="):
                    self._skip_brace_init()
            return StructDeclNode(name=name, members=members, line=line, col=col)
        else:
            # Form 2: variable instantiation — skip and return None
            _var_tok = self._eat("id")
            if self._is("="):
                self._skip_brace_init()
            return None

    def _struct_members(self) -> List[StructMemberNode]:
        """Parse all field declarations inside a struct body { ... }.

        Each field is: type id [array_spec] ;
        Stops when a non-type token is seen (i.e., the closing '}'.
        """
        members = []
        while self._is("wall", "tile", "glass", "brick", "beam"):
            line, col = self._line(), self._col()
            dtype = self._data_type_str()
            name_tok = self._eat("id")
            name = name_tok.lexeme if name_tok else ""
            is_arr = False
            dims = None
            if self._is("["):
                is_arr = True
                dims = self._struct_array_dims()
            self._eat(";")
            members.append(StructMemberNode(type=dtype, name=name,
                                            is_array=is_arr, array_dims=dims,
                                            line=line, col=col))
        return members

    def _struct_array_dims(self) -> List[int]:
        """Parse array dimensions for a struct member field."""
        dims = []
        self._eat("[")
        if self._is("tile_lit"):
            dims.append(int(self._advance().lexeme))
        else:
            dims.append(0)
        self._eat("]")
        if self._is("["):
            self._eat("[")
            if self._is("tile_lit"):
                dims.append(int(self._advance().lexeme))
            else:
                dims.append(0)
            self._eat("]")
        return dims

    # ── Global constant declaration ───────────────────────────────────────────

    def _global_const(self) -> Optional[VarDeclNode]:
        """Parse a 'cement' (const) declaration at global scope.

        cement type id [= literal] [, id [= literal]] ...
        Returns a VarDeclNode with is_const=True.
        Only the FIRST name in a comma list is returned; subsequent names are
        consumed but discarded.  (TODO: return a list like local const decl.)
        """
        line, col = self._line(), self._col()
        self._eat("cement")
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        if dtype == "wall":
            init_val = self._global_wall_init_expr()
        elif dtype == "house":
            # Skip struct const initialiser — not representable here
            self._eat("id")  # variable name
            if self._is("="):
                self._skip_brace_init()
            init_val = None
        else:
            if self._is("="):
                self._eat("=")
                init_val = self._value_literal()
            elif self._is("["):
                self._array_dec_dims()  # unpack: (dims, init)
                init_val = None
            else:
                init_val = None

        # Skip trailing comma-separated const declarations in the same statement
        while self._is(","):
            self._eat(",")
            self._eat("id")
            if self._is("="):
                self._eat("=")
                self._value_literal()

        return VarDeclNode(type=dtype, name=name, init_value=init_val,
                           is_const=True, is_array=False, array_dims=None,
                           line=line, col=col)

    # -----------------------------------------------------------------------
    # Function definitions  (<program_body>)
    # -----------------------------------------------------------------------
    # <program_body> → (<function_def>)*
    #
    # Functions may have any primitive return type ('tile', 'glass', 'brick',
    # 'beam', 'field', 'wall') or be the special 'blueprint()' entry point.

    def _program_body(self) -> List[FunctionNode]:
        """Parse all function definitions until EOF."""
        funcs = []
        while not self._is("EOF"):
            f = self._function_def()
            if f:
                funcs.append(f)
            else:
                break
        return funcs

    def _function_def(self) -> Optional[FunctionNode]:
        """Parse one function definition.

        Handles two forms:
          wall id ( params ) { body }          — wall-return function
          type id ( params ) { body }           — primitive-return function
          type blueprint ( ) { body }           — entry point
        Returns None if the current token is not a valid function start.
        """
        line, col = self._line(), self._col()

        if self._is("wall"):
            # wall-return function: wall id ( params ) { body }
            self._eat("wall")
            name_tok = self._eat("id")
            name = name_tok.lexeme if name_tok else ""
            self._eat("(")
            params = self._param_list()
            self._eat(")")
            self._eat("{")
            body = self._func_body_stmts()
            self._eat("}")
            return FunctionNode(return_type="wall", name=name, params=params,
                                body=body, is_blueprint=False, line=line, col=col)

        elif self._is("tile", "glass", "brick", "beam", "field"):
            # non-wall return type: may be a named function or the blueprint entry
            rtype = self._advance().lexeme
            if self._is("id"):
                name_tok = self._eat("id")
                name = name_tok.lexeme if name_tok else ""
                self._eat("(")
                params = self._param_list()
                self._eat(")")
                self._eat("{")
                body = self._func_body_stmts()
                self._eat("}")
                return FunctionNode(return_type=rtype, name=name, params=params,
                                    body=body, is_blueprint=False, line=line, col=col)
            elif self._is("blueprint"):
                # blueprint() entry point takes no parameters
                self._eat("blueprint")
                self._eat("(")
                self._eat(")")
                self._eat("{")
                body = self._func_body_stmts()
                self._eat("}")
                return FunctionNode(return_type=rtype, name="blueprint", params=[],
                                    body=body, is_blueprint=True, line=line, col=col)
        return None

    # -----------------------------------------------------------------------
    # Parameter list
    # -----------------------------------------------------------------------

    def _param_list(self) -> List[ParamNode]:
        """Parse a comma-separated list of formal parameters.

        Returns an empty list for functions with no parameters.
        Each parameter is: type id
        """
        params = []
        if self._is(")"):
            return params
        p = self._param()
        if p:
            params.append(p)
        while self._is(","):
            self._eat(",")
            p = self._param()
            if p:
                params.append(p)
        return params

    def _param(self) -> Optional[ParamNode]:
        """Parse one formal parameter: type id"""
        line, col = self._line(), self._col()
        if not self._is("wall", "tile", "glass", "brick", "beam"):
            return None
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        return ParamNode(type=dtype, name=name, line=line, col=col)

    # -----------------------------------------------------------------------
    # Function body — statement and declaration dispatch
    # -----------------------------------------------------------------------

    def _func_body_stmts(self) -> List:
        """Parse all items inside a function body or nested block.

        Stops at '}' or EOF.  When a declaration method returns a list (for
        comma-declared variables), extend() flattens it into the body list.
        """
        stmts = []
        while not self._is("}", "EOF"):
            s = self._body_item()
            if s is None:
                pass
            elif isinstance(s, list):
                # Multi-variable declarations expand into multiple VarDeclNodes
                stmts.extend(s)
            else:
                stmts.append(s)
        return stmts

    def _body_item(self):
        """Parse one declaration or statement inside a function body.

        Declaration parsers (_local_var_decl, _local_const_decl,
        _local_struct_decl) may return a LIST of VarDeclNode when multiple
        variables are declared in one statement.  Callers must handle both
        a single node and a list.
        """
        if self._is("wall", "tile", "glass", "brick", "beam"):
            return self._local_var_decl()
        elif self._is("house"):
            return self._local_struct_decl()
        elif self._is("cement"):
            return self._local_const_decl()
        else:
            return self._statement()

    # -----------------------------------------------------------------------
    # Local declarations
    # -----------------------------------------------------------------------

    def _local_var_decl(self) -> List:
        """Parse a local variable declaration; return a LIST of VarDeclNode.

        One VarDeclNode is produced per declared name so that the semantic
        analyzer can check, initialize, and register each variable independently.

        Examples
        --------
        tile x;                    → [VarDeclNode(x)]
        tile a = 1, b = 2, c = 3; → [VarDeclNode(a,1), VarDeclNode(b,2), VarDeclNode(c,3)]
        tile arr[5];               → [VarDeclNode(arr, is_array=True, dims=[5])]
        """
        line, col = self._line(), self._col()
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        nodes: List[VarDeclNode] = []

        if dtype == "wall":
            # wall id [= wall_init] [, id [= wall_init]] ... ;
            # OR wall id[size] [= {...}] ;
            init_val = None
            is_arr = False
            dims = None
            if self._is("="):
                self._eat("=")
                init_val = self._wall_init_expr()
            elif self._is("["):
                is_arr = True
                dims, arr_init = self._array_dec_dims()
                init_val = arr_init
            nodes.append(VarDeclNode(type="wall", name=name, init_value=init_val,
                                     is_const=False, is_array=is_arr, array_dims=dims,
                                     line=line, col=col))
            while self._is(","):
                self._eat(",")
                extra_line, extra_col = self._line(), self._col()
                extra_tok = self._eat("id")
                extra_name = extra_tok.lexeme if extra_tok else ""
                extra_init = None
                if self._is("="):
                    self._eat("=")
                    extra_init = self._wall_init_expr()
                nodes.append(VarDeclNode(type="wall", name=extra_name,
                                         init_value=extra_init,
                                         is_const=False, is_array=False,
                                         array_dims=None,
                                         line=extra_line, col=extra_col))
            self._eat(";")
        else:
            # non-wall: may be array or scalar, may have comma-separated names
            init_val = None
            is_array = False
            dims = None
            if self._is("="):
                self._eat("=")
                init_val = self._expression()
            elif self._is("["):
                is_array = True
                dims, arr_init = self._array_dec_dims()
                init_val = arr_init  # ArrayInitNode or None
            nodes.append(VarDeclNode(type=dtype, name=name, init_value=init_val,
                                     is_const=False, is_array=is_array,
                                     array_dims=dims, line=line, col=col))
            # Only scalar (non-array) declarations allow comma-separated names
            if not is_array:
                while self._is(","):
                    self._eat(",")
                    extra_line, extra_col = self._line(), self._col()
                    extra_tok = self._eat("id")
                    extra_name = extra_tok.lexeme if extra_tok else ""
                    extra_init = None
                    if self._is("="):
                        self._eat("=")
                        extra_init = self._expression()
                    nodes.append(VarDeclNode(type=dtype, name=extra_name,
                                             init_value=extra_init,
                                             is_const=False, is_array=False,
                                             array_dims=None,
                                             line=extra_line, col=extra_col))
            self._eat(";")
        return nodes

    def _local_struct_decl(self) -> List:
        """Parse a local struct declaration; return a LIST of VarDeclNode.

        Handles two forms:
          1. Inline definition + variables:
               house Student { ... } s1, s2 = {...};
             → skips the struct body, returns [VarDeclNode(s1), VarDeclNode(s2)]
          2. Variable instantiation of an already-defined struct:
               house Student s1, s2 = {...};
             → returns [VarDeclNode(s1), VarDeclNode(s2)]

        Note: Inline struct definitions inside function bodies are unusual
        but valid in arCh.  The struct type body is skipped here because it
        was registered in the global scope during the global-declaration pass.
        """
        line, col = self._line(), self._col()
        self._eat("house")
        type_name_tok = self._eat("id")
        type_name = type_name_tok.lexeme if type_name_tok else ""
        nodes: List[VarDeclNode] = []

        # Sentinel for brace-initialized struct variables: marks
        # init_value as non-None so semantic analysis sees them as initialized.
        def _brace_sentinel():
            return LiteralNode(value="0", literal_type="tile", line=line, col=col)

        if self._is("{"):
            # Inline struct definition: consume { members } body
            depth = 0
            while not self._is("EOF"):
                if self._is("{"):
                    depth += 1; self._advance()
                elif self._is("}"):
                    depth -= 1; self._advance()
                    if depth == 0:
                        break
                else:
                    self._advance()
            # Parse comma-separated variable names that follow the '}'
            if self._is("id"):
                var_tok = self._eat("id")
                vline, vcol = line, col
                init_val = None
                if self._is("="):
                    init_val = self._parse_brace_init()
                nodes.append(VarDeclNode(
                    type=f"house {type_name}", name=var_tok.lexeme,
                    init_value=init_val, is_const=False,
                    is_array=False, array_dims=None, line=vline, col=vcol))
                while self._is(","):
                    self._eat(",")
                    extra_line, extra_col = self._line(), self._col()
                    extra_tok = self._eat("id")
                    extra_name = extra_tok.lexeme if extra_tok else ""
                    extra_init = None
                    if self._is("="):
                        extra_init = self._parse_brace_init()
                    nodes.append(VarDeclNode(
                        type=f"house {type_name}", name=extra_name,
                        init_value=extra_init, is_const=False,
                        is_array=False, array_dims=None,
                        line=extra_line, col=extra_col))
            self._eat(";")
        else:
            # Variable instantiation of an already-defined struct type
            var_tok = self._eat("id")
            var_name = var_tok.lexeme if var_tok else ""
            init_val = None
            if self._is("="):
                init_val = self._parse_brace_init()
            nodes.append(VarDeclNode(
                type=f"house {type_name}", name=var_name,
                init_value=init_val, is_const=False,
                is_array=False, array_dims=None, line=line, col=col))
            while self._is(","):
                self._eat(",")
                extra_line, extra_col = self._line(), self._col()
                extra_tok = self._eat("id")
                extra_name = extra_tok.lexeme if extra_tok else ""
                extra_init = None
                if self._is("="):
                    extra_init = self._parse_brace_init()
                nodes.append(VarDeclNode(
                    type=f"house {type_name}", name=extra_name,
                    init_value=extra_init, is_const=False,
                    is_array=False, array_dims=None,
                    line=extra_line, col=extra_col))
            self._eat(";")

        return nodes

    def _local_const_decl(self) -> List:
        """Parse a cement (const) declaration; return a LIST of VarDeclNode.

        Each comma-separated name produces its own VarDeclNode so the semantic
        analyzer can validate each constant independently.
        """
        line, col = self._line(), self._col()
        self._eat("cement")
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        nodes: List[VarDeclNode] = []

        init_val = None
        if dtype == "wall":
            if self._is("="):
                self._eat("=")
                init_val = self._wall_init_expr()
            elif self._is("["):
                self._array_dec_dims()
        elif dtype == "house":
            self._eat("id")
            if self._is("="):
                self._skip_brace_init()
        else:
            if self._is("="):
                self._eat("=")
                init_val = self._expression()
            elif self._is("["):
                self._array_dec_dims()

        nodes.append(VarDeclNode(type=dtype, name=name, init_value=init_val,
                                 is_const=True, is_array=False, array_dims=None,
                                 line=line, col=col))
        # Trailing comma-separated const declarations in the same statement
        while self._is(","):
            self._eat(",")
            extra_line, extra_col = self._line(), self._col()
            extra_tok = self._eat("id")
            extra_name = extra_tok.lexeme if extra_tok else ""
            extra_init = None
            if self._is("="):
                self._eat("=")
                extra_init = self._expression()
            nodes.append(VarDeclNode(type=dtype, name=extra_name,
                                     init_value=extra_init,
                                     is_const=True, is_array=False,
                                     array_dims=None,
                                     line=extra_line, col=extra_col))
        self._eat(";")
        return nodes

    # -----------------------------------------------------------------------
    # Statement dispatch
    # -----------------------------------------------------------------------

    def _statement(self):
        """Dispatch to the appropriate statement parser based on current token."""
        if self._is("view", "write"):
            return self._io_statement()
        elif self._is("id"):
            return self._assign_or_call()
        elif self._is("++", "--"):
            return self._prefix_inc_statement()
        elif self._is("if"):
            return self._if_statement()
        elif self._is("room"):
            return self._switch_statement()
        elif self._is("for"):
            return self._for_statement()
        elif self._is("while"):
            return self._while_statement()
        elif self._is("do"):
            return self._dowhile_statement()
        elif self._is("crack"):
            return self._break_statement()
        elif self._is("mend"):
            return self._continue_statement()
        elif self._is("home"):
            return self._return_statement()
        else:
            # Unknown token in statement position — skip to avoid infinite loop.
            # This should not occur in syntactically valid input.
            self._advance()
            return None

    # -----------------------------------------------------------------------
    # I/O statements
    # -----------------------------------------------------------------------
    # arCh's built-in I/O uses view() for output and write() for input.
    # Both take a format string as their first argument followed by
    # optional arguments.  For write(), each argument may be preceded by '&'
    # (address-of, for scanf compatibility), which ASTBuilder silently discards.

    def _io_statement(self) -> IONode:
        """Parse view(...); or write(...);"""
        line, col = self._line(), self._col()
        io_type = self._advance().lexeme   # 'view' or 'write'
        self._eat("(")
        fmt_tok = self._eat("wall_lit")
        fmt = fmt_tok.lexeme if fmt_tok else ""
        args = []

        if io_type == "write":
            # write always requires at least one argument after the format string
            self._eat(",")
            args.append(self._write_arg())
            while self._is(","):
                self._eat(",")
                args.append(self._write_arg())
        else:
            # view: format string only, or format + optional args
            while self._is(","):
                self._eat(",")
                args.append(self._assign_rhs_expr())

        self._eat(")")
        self._eat(";")
        return IONode(io_type=io_type, format_string=fmt, args=args,
                      line=line, col=col)

    def _write_arg(self) -> ExprNode:
        """Parse one write() argument, silently discarding a leading '&'."""
        line, col = self._line(), self._col()
        if self._is("&"):
            self._eat("&")
        return self._id_val_expr(line, col)

    # -----------------------------------------------------------------------
    # Assignment and standalone function call
    # -----------------------------------------------------------------------

    def _assign_or_call(self):
        """Parse a statement starting with an identifier.

        Four cases:
          id ( args ) ;          — standalone function call
          id ++ ;  or  id -- ;   — postfix increment/decrement statement
          lhs = rhs ;            — simple assignment
          lhs op= rhs ;          — compound assignment (+=, -=, *=, /=, %=)
        The LHS may include array subscripts and struct member accesses.
        """
        line, col = self._line(), self._col()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        # Standalone function call: id ( args ) ;
        if self._is("("):
            self._eat("(")
            args = self._func_args()
            self._eat(")")
            self._eat(";")
            return FunctionCallNode(func_name=name, args=args, line=line, col=col)

        # Postfix statement: id ++ ;  or  id -- ;
        if self._is("++", "--"):
            op = self._advance().lexeme
            self._eat(";")
            target = IdNode(name=name, line=line, col=col)
            return UnaryOpNode(operator=op, operand=target, is_prefix=False,
                               line=line, col=col)

        # Build LHS node (array/struct access chains are handled inside)
        target = self._build_id_lhs(name, line, col)

        # Compound assignment
        if self._is("+=", "-=", "*=", "/=", "%="):
            op = self._advance().lexeme
            rhs = self._expression()
            self._eat(";")
            return AssignNode(target=target, value=rhs, operator=op,
                              line=line, col=col)
        # Simple assignment
        elif self._is("="):
            self._eat("=")
            rhs = self._assign_rhs_expr()
            self._eat(";")
            return AssignNode(target=target, value=rhs, operator="=",
                              line=line, col=col)
        else:
            # Bare identifier statement — should not occur in valid input
            if self._is(";"):
                self._eat(";")
            return IdNode(name=name, line=line, col=col)

    def _build_id_lhs(self, name: str, line: int, col: int) -> ExprNode:
        """Build an LHS expression node for assignment targets.

        Starting from an IdNode, applies any following [] (array access)
        or . (struct member access) operators to build a chain.

        Examples
        --------
        arr[i]       → ArrayAccessNode(IdNode('arr'), [IdNode('i')])
        s.x          → StructAccessNode(IdNode('s'), 'x')
        s.arr[0]     → ArrayAccessNode(StructAccessNode(IdNode('s'), 'arr'), [...])
        """
        node: ExprNode = IdNode(name=name, line=line, col=col)
        while self._is("[", "."):
            if self._is("["):
                self._eat("[")
                idx = self._expression()
                self._eat("]")
                indices = [idx]
                if self._is("["):
                    self._eat("[")
                    idx2 = self._expression()
                    self._eat("]")
                    indices.append(idx2)
                node = ArrayAccessNode(array=node, indices=indices,
                                       line=line, col=col)
            elif self._is("."):
                self._eat(".")
                member_tok = self._eat("id")
                member = member_tok.lexeme if member_tok else ""
                node = StructAccessNode(struct=node, member=member,
                                        line=line, col=col)
        return node

    def _prefix_inc_statement(self):
        """Parse ++ id ;  or  -- id ; as a statement."""
        line, col = self._line(), self._col()
        op = self._advance().lexeme
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        self._eat(";")
        return UnaryOpNode(operator=op,
                           operand=IdNode(name=name, line=line, col=col),
                           is_prefix=True, line=line, col=col)

    # -----------------------------------------------------------------------
    # Control-flow statements
    # -----------------------------------------------------------------------

    def _if_statement(self) -> IfNode:
        """Parse if (cond) { body } [else { body } | else if ...]"""
        line, col = self._line(), self._col()
        self._eat("if")
        self._eat("(")
        cond = self._expression()
        self._eat(")")
        self._eat("{")
        then_body = self._func_body_stmts()
        self._eat("}")
        else_body = None
        if self._is("else"):
            self._eat("else")
            if self._is("if"):
                # else-if chain: wrap the nested IfNode in a list
                else_body = [self._if_statement()]
            else:
                self._eat("{")
                else_body = self._func_body_stmts()
                self._eat("}")
        return IfNode(condition=cond, then_body=then_body, else_body=else_body,
                      line=line, col=col)

    def _switch_statement(self) -> SwitchNode:
        """Parse room (expr) { door val: body ... ground: body }"""
        line, col = self._line(), self._col()
        self._eat("room")
        self._eat("(")
        expr = self._expression()
        self._eat(")")
        self._eat("{")
        cases = self._switch_cases()
        self._eat("}")
        return SwitchNode(expr=expr, cases=cases, line=line, col=col)

    def _switch_cases(self) -> List[CaseNode]:
        """Parse all case (door) and default (ground) branches."""
        cases = []
        while self._is("door", "ground"):
            cline, ccol = self._line(), self._col()
            if self._is("door"):
                self._eat("door")
                val = self._case_value()
                self._eat(":")
                body = self._case_body_stmts()
                cases.append(CaseNode(value=val, body=body, is_default=False,
                                      line=cline, col=ccol))
            else:
                self._eat("ground")
                self._eat(":")
                body = self._case_body_stmts()
                cases.append(CaseNode(value=None, body=body, is_default=True,
                                      line=cline, col=ccol))
        return cases

    def _case_value(self) -> LiteralNode:
        """Consume and wrap a case label value as a LiteralNode."""
        line, col = self._line(), self._col()
        tok = self._advance()
        ltype = LITERAL_TO_TYPE.get(tok.tokenType, "tile")
        return LiteralNode(value=tok.lexeme, literal_type=ltype, line=line, col=col)

    def _case_body_stmts(self) -> List:
        """Parse the body of a case branch.

        Accepts either a braced block { ... } or bare statements terminated
        by the next 'door', 'ground', '}', or EOF.
        """
        stmts = []
        if self._is("{"):
            self._eat("{")
            stmts = self._func_body_stmts()
            self._eat("}")
        else:
            while not self._is("door", "ground", "}", "EOF"):
                s = self._statement()
                if s is not None:
                    stmts.append(s)
        return stmts

    def _for_statement(self) -> ForNode:
        """Parse for (init ; cond ; incr) { body }"""
        line, col = self._line(), self._col()
        self._eat("for")
        self._eat("(")
        init = self._for_init()
        self._eat(";")
        cond = self._expression()
        self._eat(";")
        incr = self._expression()
        self._eat(")")
        self._eat("{")
        body = self._func_body_stmts()
        self._eat("}")
        return ForNode(init=init, condition=cond, increment=incr, body=body,
                       line=line, col=col)

    def _for_init(self):
        """Parse the initializer part of a for loop header.

        Two forms:
          type id = expr   — variable declaration (returns VarDeclNode)
          id op= expr      — assignment (returns AssignNode)
          id               — bare identifier (returns AssignNode or target)
        """
        line, col = self._line(), self._col()
        if self._is("tile", "glass", "brick", "beam"):
            dtype = self._advance().lexeme
            name_tok = self._eat("id")
            name = name_tok.lexeme if name_tok else ""
            init_val = None
            if self._is("="):
                self._eat("=")
                init_val = self._expression()
            return VarDeclNode(type=dtype, name=name, init_value=init_val,
                               is_const=False, is_array=False, array_dims=None,
                               line=line, col=col)
        elif self._is("id"):
            name_tok = self._eat("id")
            name = name_tok.lexeme if name_tok else ""
            target = self._build_id_lhs(name, line, col)
            if self._is("="):
                self._eat("=")
                rhs = self._expression()
                return AssignNode(target=target, value=rhs, operator="=",
                                  line=line, col=col)
            elif self._is("+=", "-=", "*=", "/=", "%="):
                op = self._advance().lexeme
                rhs = self._expression()
                return AssignNode(target=target, value=rhs, operator=op,
                                  line=line, col=col)
            return target
        return None

    def _while_statement(self) -> WhileNode:
        """Parse while (cond) { body }"""
        line, col = self._line(), self._col()
        self._eat("while")
        self._eat("(")
        cond = self._expression()
        self._eat(")")
        self._eat("{")
        body = self._func_body_stmts()
        self._eat("}")
        return WhileNode(condition=cond, body=body, line=line, col=col)

    def _dowhile_statement(self) -> DoWhileNode:
        """Parse do { body } while (cond) ;"""
        line, col = self._line(), self._col()
        self._eat("do")
        self._eat("{")
        body = self._func_body_stmts()
        self._eat("}")
        self._eat("while")
        self._eat("(")
        cond = self._expression()
        self._eat(")")
        self._eat(";")
        return DoWhileNode(body=body, condition=cond, line=line, col=col)

    def _break_statement(self) -> BreakNode:
        """Parse crack ;"""
        line, col = self._line(), self._col()
        self._eat("crack")
        self._eat(";")
        return BreakNode(line=line, col=col)

    def _continue_statement(self) -> ContinueNode:
        """Parse mend ;"""
        line, col = self._line(), self._col()
        self._eat("mend")
        self._eat(";")
        return ContinueNode(line=line, col=col)

    def _return_statement(self) -> ReturnNode:
        """Parse home [expr] ;"""
        line, col = self._line(), self._col()
        self._eat("home")
        val = None
        if not self._is(";"):
            val = self._assign_rhs_expr()
        self._eat(";")
        return ReturnNode(value=val, line=line, col=col)

    # -----------------------------------------------------------------------
    # Expression parsing
    # -----------------------------------------------------------------------
    # Expressions are parsed using a precedence-climbing parser that respects
    # the arCh operator precedence table (spec M):
    #
    #   Precedence 3: *, /, %       (highest among binary ops)
    #   Precedence 4: +, -
    #   Precedence 5: <, <=, >, >=
    #   Precedence 6: ==, !=
    #   Precedence 7: &&
    #   Precedence 8: ||            (lowest among binary ops)
    #
    # All binary operators are left-associative.
    # Unary operators (precedence 1-2) are handled by _unary_or_primary().

    # Maps operator lexeme → integer precedence level (lower number = tighter binding)
    _OP_PRECEDENCE = {
        "*":  3, "/":  3, "%":  3,
        "+":  4, "-":  4,
        "<":  5, "<=": 5, ">":  5, ">=": 5,
        "==": 6, "!=": 6,
        "&&": 7,
        "||": 8,
    }

    _BINARY_OPS = frozenset(_OP_PRECEDENCE.keys())

    def _expression(self) -> ExprNode:
        """General expression entry point — precedence-climbing parser."""
        return self._prec_expr(8)  # start at lowest precedence (loosest binding)

    def _prec_expr(self, max_prec: int) -> ExprNode:
        """Parse a binary expression with precedence climbing.

        Parses operators at precedence level `max_prec` or tighter (lower number).
        Left-associative: a + b + c  →  BinaryOpNode(BinaryOpNode(a, +, b), +, c).
        """
        left = self._unary_or_primary()
        while (self._type() in self._BINARY_OPS or self._lexeme() in self._BINARY_OPS):
            op_lexeme = self._lexeme()
            op_prec = self._OP_PRECEDENCE.get(op_lexeme)
            if op_prec is None or op_prec > max_prec:
                break  # operator binds too loosely for this level
            line, col = self._line(), self._col()
            self._advance()
            # Recurse at one level tighter to enforce left-associativity
            right = self._prec_expr(op_prec - 1)
            left = BinaryOpNode(left=left, operator=op_lexeme, right=right,
                                line=line, col=col)
        return left

    def _binary_expr(self) -> ExprNode:
        """Parse a left-associative chain of binary operations.

        Kept as an alias for backward compatibility with callers that use
        _binary_expr() directly (e.g. some condition/for contexts).
        Now delegates to the precedence-climbing parser.
        """
        return self._prec_expr(8)

    def _assign_rhs_expr(self) -> ExprNode:
        """Parse the right-hand side of an assignment.

        Extends _binary_expr with support for:
          - wall (string) literals as starting values
          - wall concatenation:  "hello " + name + " world"

        If only a single part is parsed (no '+'), the part itself is returned
        rather than a WallConcatNode.
        """
        line, col = self._line(), self._col()

        if self._is("wall_lit"):
            parts = [LiteralNode(value=self._advance().lexeme, literal_type="wall",
                                 line=line, col=col)]
            while self._is("+"):
                self._eat("+")
                pline, pcol = self._line(), self._col()
                if self._is("wall_lit"):
                    parts.append(LiteralNode(value=self._advance().lexeme,
                                             literal_type="wall",
                                             line=pline, col=pcol))
                elif self._is("id"):
                    parts.append(self._id_expr(pline, pcol))
                elif self._is("("):
                    parts.append(self._paren_expr(pline, pcol))
                else:
                    break
            if len(parts) == 1:
                return parts[0]
            return WallConcatNode(parts=parts, line=line, col=col)

        return self._binary_expr()

    def _unary_or_primary(self) -> ExprNode:
        """Parse a prefix unary operator or delegate to _postfix_expr."""
        line, col = self._line(), self._col()

        if self._is("-"):
            self._eat("-")
            operand = self._unary_or_primary()
            return UnaryOpNode(operator="-", operand=operand, is_prefix=True,
                               line=line, col=col)
        if self._is("!"):
            self._eat("!")
            operand = self._unary_or_primary()
            return UnaryOpNode(operator="!", operand=operand, is_prefix=True,
                               line=line, col=col)
        if self._is("++", "--"):
            op = self._advance().lexeme
            operand = self._prefix_target(line, col)
            return UnaryOpNode(operator=op, operand=operand, is_prefix=True,
                               line=line, col=col)

        return self._postfix_expr(line, col)

    def _prefix_target(self, line, col) -> ExprNode:
        """Parse the target of a prefix ++ or -- operator."""
        if self._is("("):
            return self._paren_expr(line, col)
        return self._id_expr(line, col)

    def _postfix_expr(self, line, col) -> ExprNode:
        """Parse a primary expression possibly followed by postfix ++ or --."""
        node = self._primary(line, col)
        if self._is("++", "--"):
            op = self._advance().lexeme
            node = UnaryOpNode(operator=op, operand=node, is_prefix=False,
                               line=line, col=col)
        return node

    def _primary(self, line, col) -> ExprNode:
        """Parse a primary expression: literal, identifier, or parenthesised expr.

        Falls through to a dummy LiteralNode on unrecognised tokens to prevent
        infinite loops during error recovery.
        """
        if self._is("tile_lit", "glass_lit", "brick_lit", "solid", "fragile"):
            return self._value_literal()
        if self._is("wall_lit"):
            tok = self._advance()
            return LiteralNode(value=tok.lexeme, literal_type="wall",
                               line=line, col=col)
        if self._is("id"):
            return self._id_expr(line, col)
        if self._is("("):
            return self._paren_expr(line, col)
        # Fallback: consume one token and return a dummy tile literal
        tok = self._advance()
        return LiteralNode(value=tok.lexeme if tok else "", literal_type="tile",
                           line=line, col=col)

    def _paren_expr(self, line, col) -> ExprNode:
        """Parse a parenthesised expression: ( expr )"""
        self._eat("(")
        inner = self._expression()
        self._eat(")")
        return inner

    def _id_expr(self, line=None, col=None) -> ExprNode:
        """Parse an identifier and any following access operators.

        Handles all of:
          id                      → IdNode
          id ( args )             → FunctionCallNode
          id [ idx ] [ idx ]      → ArrayAccessNode
          id . member             → StructAccessNode
          Chains: id[i].field[j]  → nested access nodes

        This method is used for BOTH expression context (RHS) and for the
        postfix part of LHS chains via _build_id_lhs().
        """
        if line is None:
            line, col = self._line(), self._col()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        # Function call
        if self._is("("):
            self._eat("(")
            args = self._func_args()
            self._eat(")")
            return FunctionCallNode(func_name=name, args=args, line=line, col=col)

        # Array or struct access chain
        node: ExprNode = IdNode(name=name, line=line, col=col)
        while self._is("[", "."):
            if self._is("["):
                self._eat("[")
                idx = self._expression()
                self._eat("]")
                indices = [idx]
                if self._is("["):
                    self._eat("[")
                    idx2 = self._expression()
                    self._eat("]")
                    indices.append(idx2)
                node = ArrayAccessNode(array=node, indices=indices,
                                       line=line, col=col)
            elif self._is("."):
                self._eat(".")
                member_tok = self._eat("id")
                member = member_tok.lexeme if member_tok else ""
                node = StructAccessNode(struct=node, member=member,
                                        line=line, col=col)
        return node

    def _id_val_expr(self, line, col) -> ExprNode:
        """Alias for _id_expr; used specifically in write() argument context."""
        return self._id_expr(line, col)

    def _value_literal(self) -> LiteralNode:
        """Consume one literal token and wrap it in a LiteralNode.

        Maps the token's tokenType to an arCh type string via LITERAL_TO_TYPE.
        """
        line, col = self._line(), self._col()
        tok = self._advance()
        ltype = LITERAL_TO_TYPE.get(tok.tokenType if tok else "", "tile")
        return LiteralNode(value=tok.lexeme if tok else "",
                           literal_type=ltype, line=line, col=col)

    # -----------------------------------------------------------------------
    # Wall (string) concatenation expression
    # -----------------------------------------------------------------------

    def _wall_init_expr(self) -> ExprNode:
        """Parse a wall initialisation expression in a local variable context.

        Handles: wall_lit  |  id  |  ( wall_init_expr )
        followed by zero or more:  + ( wall_lit | id | ( wall_init_expr ) )

        Returns a single LiteralNode or IdNode when only one part is found,
        or a WallConcatNode when two or more parts are concatenated.
        """
        line, col = self._line(), self._col()

        if self._is("("):
            self._eat("(")
            inner = self._wall_init_expr()
            self._eat(")")
            result: ExprNode = inner
        elif self._is("wall_lit"):
            tok = self._advance()
            result = LiteralNode(value=tok.lexeme, literal_type="wall",
                                 line=line, col=col)
        elif self._is("id"):
            result = self._id_expr(line, col)
        else:
            result = LiteralNode(value="", literal_type="wall", line=line, col=col)

        parts = [result]
        while self._is("+"):
            self._eat("+")
            pline, pcol = self._line(), self._col()
            if self._is("wall_lit"):
                tok = self._advance()
                parts.append(LiteralNode(value=tok.lexeme, literal_type="wall",
                                         line=pline, col=pcol))
            elif self._is("id"):
                parts.append(self._id_expr(pline, pcol))
            elif self._is("("):
                self._eat("(")
                inner = self._wall_init_expr()
                self._eat(")")
                parts.append(inner)
            else:
                break

        if len(parts) == 1:
            return parts[0]
        return WallConcatNode(parts=parts, line=line, col=col)

    # -----------------------------------------------------------------------
    # Function argument list
    # -----------------------------------------------------------------------

    def _func_args(self) -> List[ExprNode]:
        """Parse a comma-separated function argument list.

        Returns an empty list for zero-argument calls.
        Each argument is parsed with _assign_rhs_expr() so that wall literals
        and concatenations are valid arguments.
        """
        args = []
        if self._is(")"):
            return args
        args.append(self._assign_rhs_expr())
        while self._is(","):
            self._eat(",")
            args.append(self._assign_rhs_expr())
        return args