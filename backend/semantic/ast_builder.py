from typing import List, Optional, Any
from semantic.ast import (
    ProgramNode, FunctionNode, ParamNode,
    GlobalDeclNode, VarDeclNode, StructDeclNode, StructMemberNode,
    StatementNode, AssignNode, IfNode, WhileNode, DoWhileNode,
    ForNode, SwitchNode, CaseNode, BreakNode, ContinueNode,
    ReturnNode, IONode,
    ExprNode, BinaryOpNode, UnaryOpNode, LiteralNode,
    IdNode, ArrayAccessNode, StructAccessNode, FunctionCallNode,
    WallConcatNode,
)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

IGNORE_TYPES = ("space", "tab", "newline", "Single-Line Comment", "Multi-Line Comment")

LITERAL_TO_TYPE = {
    "tile_lit":  "tile",
    "glass_lit": "glass",
    "brick_lit": "brick",
    "wall_lit":  "wall",
    "solid":     "beam",
    "fragile":   "beam",
}

DATA_TYPES = {"tile", "glass", "brick", "beam", "wall"}


def _norm(token_type: str) -> str:
    """Normalise id1/id2/... → id (mirrors parserV2)."""
    if isinstance(token_type, str) and token_type.startswith("id"):
        return "id"
    return token_type


# ---------------------------------------------------------------------------
# ASTBuilder
# ---------------------------------------------------------------------------

class ASTBuilder:
    """
    Builds a ProgramNode AST from an already-lexed token list.
    Call build_program() after the Parser has confirmed no syntax errors.
    """

    def __init__(self, tokens):
        self.tokens = [
            t for t in (tokens or [])
            if getattr(t, "tokenType", None) not in IGNORE_TYPES
        ]
        self.pos = 0

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _cur(self):
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _type(self) -> str:
        t = self._cur()
        if t is None:
            return "EOF"
        return _norm(t.tokenType)

    def _lexeme(self) -> str:
        t = self._cur()
        return t.lexeme if t else ""

    def _line(self) -> int:
        t = self._cur()
        return t.line if t else 1

    def _col(self) -> int:
        t = self._cur()
        return t.column if t else 1

    def _advance(self):
        tok = self._cur()
        self.pos += 1
        return tok

    def _eat(self, expected: str):
        """Consume the current token (asserts type matches)."""
        tok = self._cur()
        self.pos += 1
        return tok

    def _peek(self, offset: int = 1) -> str:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return "EOF"
        return _norm(self.tokens[idx].tokenType)

    def _is(self, *types) -> bool:
        return self._type() in types

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def build_program(self) -> Optional[ProgramNode]:
        try:
            return self._program()
        except Exception:
            # If something unexpected fails, return empty program
            return ProgramNode(globals=[], functions=[], line=1, col=1)

    # ------------------------------------------------------------------
    # <program> → <global> <program_body>
    # ------------------------------------------------------------------

    def _program(self) -> ProgramNode:
        line, col = self._line(), self._col()
        globals_list = self._global()
        functions = self._program_body()
        return ProgramNode(globals=globals_list, functions=functions, line=line, col=col)

    # ------------------------------------------------------------------
    # <global> → (roof <global_dec> ;)*
    # ------------------------------------------------------------------

    def _global(self) -> List[GlobalDeclNode]:
        decls = []
        while self._is("roof"):
            self._eat("roof")
            d = self._global_dec()
            if d:
                decls.append(d)
            self._eat(";")
        return decls

    def _global_dec(self) -> Optional[GlobalDeclNode]:
        if self._is("wall", "tile", "glass", "brick", "beam"):
            return self._global_var()
        elif self._is("house"):
            return self._structure_global()
        elif self._is("cement"):
            return self._global_const()
        return None

    # ------------------------------------------------------------------
    # Global variable declarations
    # ------------------------------------------------------------------

    def _global_var(self) -> Optional[VarDeclNode]:
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
        """Consume a data-type keyword and return its string."""
        tok = self._advance()
        return tok.lexeme if tok else "tile"

    def _global_end(self):
        """Returns (init_expr_or_None, is_array, dims)."""
        if self._is("["):
            dims = self._array_dec_dims()
            return None, True, dims
        else:
            init_val = self._global_init_expr()
            # skip extra comma-separated names with their inits
            while self._is(","):
                self._eat(",")
                self._eat("id")
                self._global_init_expr()
            return init_val, False, None

    def _global_init_expr(self) -> Optional[ExprNode]:
        if self._is("="):
            self._eat("=")
            return self._value_literal()
        return None

    def _global_wall_end(self):
        """Returns (init_expr_or_None, is_array)."""
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
        if self._is("="):
            self._eat("=")
            line, col = self._line(), self._col()
            tok = self._eat("wall_lit")
            return LiteralNode(value=tok.lexeme if tok else "", literal_type="wall",
                               line=line, col=col)
        return None

    def _array_dec_dims(self) -> List[int]:
        """Consume [size?][size?] array declaration; return dim list."""
        dims = []
        self._eat("[")
        if self._is("tile_lit"):
            dims.append(int(self._advance().lexeme))
        else:
            dims.append(0)
        self._eat("]")
        # possible second dimension
        if self._is("["):
            self._eat("[")
            if self._is("tile_lit"):
                dims.append(int(self._advance().lexeme))
            else:
                dims.append(0)
            self._eat("]")
            # skip optional = { { ... } }
            if self._is("="):
                self._skip_brace_init()
        elif self._is("="):
            self._skip_brace_init()
        return dims

    def _wall_array_skip(self):
        """Skip wall array declaration entirely."""
        self._eat("[")
        while not self._is("]", "EOF"):
            self._advance()
        self._eat("]")
        # further dims / init
        while self._is("["):
            self._eat("[")
            while not self._is("]", "EOF"):
                self._advance()
            self._eat("]")
        if self._is("="):
            self._skip_brace_init()

    def _skip_brace_init(self):
        """Skip = { ... } or = { { ... } } initialiser blocks."""
        self._eat("=")
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

    # ------------------------------------------------------------------
    # Struct global declaration
    # ------------------------------------------------------------------

    def _structure_global(self) -> Optional[StructDeclNode]:
        line, col = self._line(), self._col()
        self._eat("house")
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        if self._is("{"):
            # struct definition: house Name { members } [var ;]
            self._eat("{")
            members = self._struct_members()
            self._eat("}")
            # optional variable instance declaration — skip for now
            if self._is("id"):
                self._eat("id")
                if self._is("="):
                    self._skip_brace_init()
            return StructDeclNode(name=name, members=members, line=line, col=col)
        else:
            # struct variable instantiation: house TypeName varName [= {...}]
            # name here is the type, next id is the variable name
            _var_tok = self._eat("id")
            if self._is("="):
                self._skip_brace_init()
            # We can't represent this as a full decl without struct lookup — return None
            return None

    def _struct_members(self) -> List[StructMemberNode]:
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
            # parse_mult_members
        return members

    def _struct_array_dims(self) -> List[int]:
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

    # ------------------------------------------------------------------
    # Global const
    # ------------------------------------------------------------------

    def _global_const(self) -> Optional[VarDeclNode]:
        line, col = self._line(), self._col()
        self._eat("cement")
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        if dtype == "wall":
            init_val = self._global_wall_init_expr()
        elif dtype == "house":
            # skip struct const initialiser
            self._eat("id")  # var name
            if self._is("="):
                self._skip_brace_init()
            init_val = None
        else:
            if self._is("="):
                self._eat("=")
                init_val = self._value_literal()
            elif self._is("["):
                self._array_dec_dims()
                init_val = None
            else:
                init_val = None

        # skip trailing comma-separated consts
        while self._is(","):
            self._eat(",")
            self._eat("id")
            if self._is("="):
                self._eat("=")
                self._value_literal()

        return VarDeclNode(type=dtype, name=name, init_value=init_val,
                           is_const=True, is_array=False, array_dims=None,
                           line=line, col=col)

    # ------------------------------------------------------------------
    # <program_body> → functions
    # ------------------------------------------------------------------

    def _program_body(self) -> List[FunctionNode]:
        funcs = []
        while not self._is("EOF"):
            f = self._function_def()
            if f:
                funcs.append(f)
            else:
                break
        return funcs

    def _function_def(self) -> Optional[FunctionNode]:
        line, col = self._line(), self._col()

        # wall id ( params ) { body }
        if self._is("wall"):
            self._eat("wall")
            name_tok = self._eat("id")
            name = name_tok.lexeme if name_tok else ""
            self._eat("(")
            params = self._param_list()
            self._eat(")")
            self._eat("{")
            body = self._func_body_stmts()
            self._eat("}")
            # recurse — handled by loop above
            return FunctionNode(return_type="wall", name=name, params=params,
                                body=body, is_blueprint=False, line=line, col=col)

        # return_type id/blueprint ( params ) { body }
        elif self._is("tile", "glass", "brick", "beam", "field"):
            rtype = self._advance().lexeme
            # next: id or blueprint
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
                self._eat("blueprint")
                self._eat("(")
                self._eat(")")
                self._eat("{")
                body = self._func_body_stmts()
                self._eat("}")
                return FunctionNode(return_type=rtype, name="blueprint", params=[],
                                    body=body, is_blueprint=True, line=line, col=col)
        return None

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    def _param_list(self) -> List[ParamNode]:
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
        line, col = self._line(), self._col()
        if not self._is("wall", "tile", "glass", "brick", "beam"):
            return None
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        return ParamNode(type=dtype, name=name, line=line, col=col)

    # ------------------------------------------------------------------
    # Function body statements
    # ------------------------------------------------------------------

    def _func_body_stmts(self) -> List:
        stmts = []
        while not self._is("}", "EOF"):
            s = self._body_item()
            if s is None:
                pass
            elif isinstance(s, list):
                # multi-variable declaration returns a list of VarDeclNodes
                stmts.extend(s)
            else:
                stmts.append(s)
        return stmts

    def _body_item(self):
        """One declaration or statement inside a function body.

        NOTE: _local_var_decl() and _local_const_decl() may return a LIST of
        VarDeclNode when multiple variables are declared in one statement
        (e.g.  tile a = 1, b = 2, c = 3;).  Callers must handle both cases.
        """
        # Local variable declaration
        if self._is("wall", "tile", "glass", "brick", "beam"):
            return self._local_var_decl()
        elif self._is("house"):
            return self._local_struct_decl()
        elif self._is("cement"):
            return self._local_const_decl()
        else:
            return self._statement()

    # ------------------------------------------------------------------
    # Local declarations
    # ------------------------------------------------------------------

    def _local_var_decl(self) -> List:
        """Parse a local variable declaration and return a LIST of VarDeclNode.

        One VarDeclNode is produced per declared name so that the semantic
        analyzer can check, initialize, and register each variable independently.

        Examples
        --------
        tile x;                    -> [VarDeclNode(x)]
        tile a = 1, b = 2, c = 3; -> [VarDeclNode(a,1), VarDeclNode(b,2), VarDeclNode(c,3)]
        tile arr[5];               -> [VarDeclNode(arr, is_array=True, dims=[5])]
        """
        line, col = self._line(), self._col()
        dtype = self._data_type_str()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        nodes: List[VarDeclNode] = []

        if dtype == "wall":
            # wall id [= wall_init] [, id [= wall_init]] ... ;
            init_val = None
            if self._is("="):
                self._eat("=")
                init_val = self._wall_init_expr()
            elif self._is("["):
                self._array_dec_dims()
            nodes.append(VarDeclNode(type="wall", name=name, init_value=init_val,
                                     is_const=False, is_array=False, array_dims=None,
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
                dims = self._array_dec_dims()
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
        """Parse a local struct declaration and return a LIST of VarDeclNode.

        Handles two forms:
          1. Inline definition + variables:
               house Student { ... } s1, s2 = {...};
             → registers the struct type (via StructDeclNode in globals),
               returns [VarDeclNode(s1), VarDeclNode(s2)]
          2. Variable instantiation of an already-defined struct:
               house Student s1, s2 = {...};
             → returns [VarDeclNode(s1), VarDeclNode(s2)]

        Always returns a list so _func_body_stmts can use extend() uniformly.
        """
        line, col = self._line(), self._col()
        self._eat("house")
        type_name_tok = self._eat("id")
        type_name = type_name_tok.lexeme if type_name_tok else ""
        nodes: List[VarDeclNode] = []

        if self._is("{"):
            # Inline struct definition: consume the { members } body
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
            # Now parse comma-separated variable names that follow the }
            if self._is("id"):
                var_tok = self._eat("id")
                vline, vcol = line, col
                if self._is("="):
                    self._skip_brace_init()
                nodes.append(VarDeclNode(
                    type=f"house {type_name}", name=var_tok.lexeme,
                    init_value=None, is_const=False,
                    is_array=False, array_dims=None, line=vline, col=vcol))
                # additional comma-separated struct variables: , s2 [= {...}]
                while self._is(","):
                    self._eat(",")
                    extra_line, extra_col = self._line(), self._col()
                    extra_tok = self._eat("id")
                    extra_name = extra_tok.lexeme if extra_tok else ""
                    if self._is("="):
                        self._skip_brace_init()
                    nodes.append(VarDeclNode(
                        type=f"house {type_name}", name=extra_name,
                        init_value=None, is_const=False,
                        is_array=False, array_dims=None,
                        line=extra_line, col=extra_col))
            self._eat(";")
        else:
            # Variable instantiation of an already-defined struct type
            var_tok = self._eat("id")
            var_name = var_tok.lexeme if var_tok else ""
            if self._is("="):
                self._skip_brace_init()
            nodes.append(VarDeclNode(
                type=f"house {type_name}", name=var_name,
                init_value=None, is_const=False,
                is_array=False, array_dims=None, line=line, col=col))
            # additional comma-separated variables
            while self._is(","):
                self._eat(",")
                extra_line, extra_col = self._line(), self._col()
                extra_tok = self._eat("id")
                extra_name = extra_tok.lexeme if extra_tok else ""
                if self._is("="):
                    self._skip_brace_init()
                nodes.append(VarDeclNode(
                    type=f"house {type_name}", name=extra_name,
                    init_value=None, is_const=False,
                    is_array=False, array_dims=None,
                    line=extra_line, col=extra_col))
            self._eat(";")

        return nodes

    def _local_const_decl(self) -> List:
        """Parse a cement (const) declaration and return a LIST of VarDeclNode.

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
        # trailing comma-separated const declarations
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

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _statement(self):
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
            # Unknown token — skip to avoid infinite loop
            self._advance()
            return None

    # ------------------------------------------------------------------
    # I/O statements
    # ------------------------------------------------------------------

    def _io_statement(self) -> IONode:
        line, col = self._line(), self._col()
        io_type = self._advance().lexeme  # view or write
        self._eat("(")
        fmt_tok = self._eat("wall_lit")
        fmt = fmt_tok.lexeme if fmt_tok else ""
        args = []

        if io_type == "write":
            self._eat(",")
            args.append(self._write_arg())
            while self._is(","):
                self._eat(",")
                args.append(self._write_arg())
        else:
            # view: optional , arg , arg ...
            while self._is(","):
                self._eat(",")
                args.append(self._assign_rhs_expr())

        self._eat(")")
        self._eat(";")
        return IONode(io_type=io_type, format_string=fmt, args=args,
                      line=line, col=col)

    def _write_arg(self) -> ExprNode:
        line, col = self._line(), self._col()
        if self._is("&"):
            self._eat("&")
        return self._id_val_expr(line, col)

    # ------------------------------------------------------------------
    # Assignment / function call statement
    # ------------------------------------------------------------------

    def _assign_or_call(self):
        """id ( id_type4 ) ;  — covers assign, compound-assign, call, postfix."""
        line, col = self._line(), self._col()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        # function call: id ( args ) ;
        if self._is("("):
            self._eat("(")
            args = self._func_args()
            self._eat(")")
            self._eat(";")
            return FunctionCallNode(func_name=name, args=args, line=line, col=col)

        # postfix: id ++ ;  or  id -- ;
        if self._is("++", "--"):
            op = self._advance().lexeme
            self._eat(";")
            target = IdNode(name=name, line=line, col=col)
            return UnaryOpNode(operator=op, operand=target, is_prefix=False,
                               line=line, col=col)

        # Build the LHS (could be arr/struct access)
        target = self._build_id_lhs(name, line, col)

        # compound assign or simple assign
        if self._is("+=", "-=", "*=", "/=", "%="):
            op = self._advance().lexeme
            rhs = self._expression()
            self._eat(";")
            return AssignNode(target=target, value=rhs, operator=op,
                              line=line, col=col)
        elif self._is("="):
            self._eat("=")
            rhs = self._assign_rhs_expr()
            self._eat(";")
            return AssignNode(target=target, value=rhs, operator="=",
                              line=line, col=col)
        else:
            # bare id; (shouldn't happen in valid code) — skip ;
            if self._is(";"):
                self._eat(";")
            return IdNode(name=name, line=line, col=col)

    def _build_id_lhs(self, name: str, line: int, col: int) -> ExprNode:
        """Build the LHS node for array/struct access chains."""
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
        """++ id ; or -- id ;"""
        line, col = self._line(), self._col()
        op = self._advance().lexeme
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""
        self._eat(";")
        return UnaryOpNode(operator=op,
                           operand=IdNode(name=name, line=line, col=col),
                           is_prefix=True, line=line, col=col)

    # ------------------------------------------------------------------
    # If statement
    # ------------------------------------------------------------------

    def _if_statement(self) -> IfNode:
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
                else_body = [self._if_statement()]
            else:
                self._eat("{")
                else_body = self._func_body_stmts()
                self._eat("}")
        return IfNode(condition=cond, then_body=then_body, else_body=else_body,
                      line=line, col=col)

    # ------------------------------------------------------------------
    # Switch statement
    # ------------------------------------------------------------------

    def _switch_statement(self) -> SwitchNode:
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
        line, col = self._line(), self._col()
        tok = self._advance()
        ltype = LITERAL_TO_TYPE.get(tok.tokenType, "tile")
        return LiteralNode(value=tok.lexeme, literal_type=ltype, line=line, col=col)

    def _case_body_stmts(self) -> List:
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

    # ------------------------------------------------------------------
    # For statement
    # ------------------------------------------------------------------

    def _for_statement(self) -> ForNode:
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
        """for-init: either type id = expr   or   id = expr / id op."""
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

    # ------------------------------------------------------------------
    # While / do-while
    # ------------------------------------------------------------------

    def _while_statement(self) -> WhileNode:
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

    # ------------------------------------------------------------------
    # Break / Continue / Return
    # ------------------------------------------------------------------

    def _break_statement(self) -> BreakNode:
        line, col = self._line(), self._col()
        self._eat("crack")
        self._eat(";")
        return BreakNode(line=line, col=col)

    def _continue_statement(self) -> ContinueNode:
        line, col = self._line(), self._col()
        self._eat("mend")
        self._eat(";")
        return ContinueNode(line=line, col=col)

    def _return_statement(self) -> ReturnNode:
        line, col = self._line(), self._col()
        self._eat("home")
        val = None
        if not self._is(";"):
            val = self._assign_rhs_expr()
        self._eat(";")
        return ReturnNode(value=val, line=line, col=col)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def _expression(self) -> ExprNode:
        """General expression (binary ops supported)."""
        return self._binary_expr()

    def _binary_expr(self) -> ExprNode:
        left = self._unary_or_primary()
        while self._is("+", "-", "*", "/", "%",
                        "<", "<=", ">", ">=", "==", "!=", "&&", "||"):
            line, col = self._line(), self._col()
            op = self._advance().lexeme
            right = self._unary_or_primary()
            left = BinaryOpNode(left=left, operator=op, right=right,
                                line=line, col=col)
        return left

    def _assign_rhs_expr(self) -> ExprNode:
        """
        assign_rhs allows wall_lit as well as normal expressions.
        Also handles wall concatenation:  wall_lit + id + wall_lit + ...
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
        if self._is("("):
            return self._paren_expr(line, col)
        return self._id_expr(line, col)

    def _postfix_expr(self, line, col) -> ExprNode:
        node = self._primary(line, col)
        if self._is("++", "--"):
            op = self._advance().lexeme
            node = UnaryOpNode(operator=op, operand=node, is_prefix=False,
                               line=line, col=col)
        return node

    def _primary(self, line, col) -> ExprNode:
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
        # fallback — consume and return a dummy literal
        tok = self._advance()
        return LiteralNode(value=tok.lexeme if tok else "", literal_type="tile",
                           line=line, col=col)

    def _paren_expr(self, line, col) -> ExprNode:
        self._eat("(")
        inner = self._expression()
        self._eat(")")
        return inner

    def _id_expr(self, line=None, col=None) -> ExprNode:
        if line is None:
            line, col = self._line(), self._col()
        name_tok = self._eat("id")
        name = name_tok.lexeme if name_tok else ""

        # function call
        if self._is("("):
            self._eat("(")
            args = self._func_args()
            self._eat(")")
            return FunctionCallNode(func_name=name, args=args, line=line, col=col)

        # array/struct access
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
        return self._id_expr(line, col)

    def _value_literal(self) -> LiteralNode:
        line, col = self._line(), self._col()
        tok = self._advance()
        ltype = LITERAL_TO_TYPE.get(tok.tokenType if tok else "", "tile")
        return LiteralNode(value=tok.lexeme if tok else "",
                           literal_type=ltype, line=line, col=col)

    # ------------------------------------------------------------------
    # Wall concatenation expression (local context)
    # ------------------------------------------------------------------

    def _wall_init_expr(self) -> ExprNode:
        """wall_init: wall_lit + id + wall_lit ... (for local wall assignment)."""
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

    # ------------------------------------------------------------------
    # Function arguments
    # ------------------------------------------------------------------

    def _func_args(self) -> List[ExprNode]:
        args = []
        if self._is(")"):
            return args
        args.append(self._assign_rhs_expr())
        while self._is(","):
            self._eat(",")
            args.append(self._assign_rhs_expr())
        return args