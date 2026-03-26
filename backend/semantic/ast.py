# ===========================================================================
# ast.py — Abstract Syntax Tree Node Definitions
# ===========================================================================
#
# ROLE IN THE PIPELINE
# --------------------
# This file defines every node type that can appear in the AST produced by
# ASTBuilder (ast_builder.py).  It is a pure data layer: no parsing logic,
# no semantic logic, and no code-generation logic lives here.
#
# DEPENDENCIES
# ------------
#   - Used by ast_builder.py  : ASTBuilder instantiates and returns these nodes.
#   - Used by semantic.py     : SemanticAnalyzer reads and annotates these nodes
#                               (writing back expr_type after type-checking).
#   - Will be used by tac.py  : The future TAC generator will walk the same tree.
#
# DATA FLOW
# ---------
#   Token list (from Lexer)
#       │
#       ▼
#   ASTBuilder  ──creates──►  ProgramNode
#                                 ├── GlobalDeclNode list  (VarDeclNode / StructDeclNode)
#                                 └── FunctionNode list
#                                         ├── ParamNode list
#                                         └── body: StatementNode / ExprNode list
#       │
#       ▼
#   SemanticAnalyzer  ──reads──►  every node
#                     ──writes──► expr_type fields on ExprNode subclasses
#
# NODE HIERARCHY OVERVIEW
# -----------------------
#   ASTNode                         (base: line, col)
#   ├── ProgramNode                 (root)
#   ├── FunctionNode
#   ├── ParamNode
#   ├── GlobalDeclNode              (abstract base for top-level declarations)
#   │   ├── VarDeclNode
#   │   ├── StructDeclNode
#   │   └── StructMemberNode
#   ├── StatementNode               (abstract base for statements)
#   │   ├── AssignNode
#   │   ├── IfNode
#   │   ├── WhileNode
#   │   ├── DoWhileNode
#   │   ├── ForNode
#   │   ├── SwitchNode / CaseNode
#   │   ├── BreakNode / ContinueNode
#   │   ├── ReturnNode
#   │   └── IONode
#   └── ExprNode                    (abstract base for expressions)
#       ├── BinaryOpNode
#       ├── UnaryOpNode
#       ├── LiteralNode
#       ├── IdNode
#       ├── ArrayAccessNode
#       ├── StructAccessNode
#       ├── FunctionCallNode
#       └── WallConcatNode
#
# TAC READINESS NOTE
# ------------------
# Every ExprNode subclass already has an `expr_type` field.  The semantic
# phase fills this in during type-checking.  A TAC generator can rely on
# `node.expr_type` to determine what temporary variable type to allocate.
# ProgramNode → FunctionNode → body list gives the full traversal order
# needed for sequential TAC emission.
#
# ===========================================================================

from dataclasses import dataclass, field
from typing import Any, Optional, List


# ---------------------------------------------------------------------------
# Base Node
# ---------------------------------------------------------------------------
# Every AST node extends ASTNode.  The line/col pair is always populated by
# ASTBuilder so that SemanticAnalyzer can report errors at the right location.

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    line: int
    col: int


# ---------------------------------------------------------------------------
# Program Structure
# ---------------------------------------------------------------------------
# These nodes describe the top-level layout of a compiled arCh source file.
# A ProgramNode is always the root; it separates global declarations (prefixed
# with 'roof') from function definitions.

@dataclass
class ProgramNode(ASTNode):
    """Root node: <program> → <global> <program_body>

    globals   — list of GlobalDeclNode produced by the 'roof' section.
    functions — list of FunctionNode; must include exactly one blueprint().
    """
    globals: list   # List[GlobalDeclNode]
    functions: list # List[FunctionNode]


@dataclass
class FunctionNode(ASTNode):
    """Function definition: return_type id ( params ) { body }
    or the special entry point:   field blueprint() { body }

    return_type — one of 'tile', 'glass', 'brick', 'beam', 'field', 'wall'
    name        — function identifier string (or 'blueprint' for the entry point)
    params      — ordered list of ParamNode
    body        — flattened list of declaration and statement nodes
    is_blueprint— True only for the blueprint() entry point
    """
    return_type: str
    name: str
    params: list    # List[ParamNode]
    body: list      # List[ASTNode]  — statements and declarations interleaved
    is_blueprint: bool = False


@dataclass
class ParamNode(ASTNode):
    """A single formal parameter in a function signature: type id

    type — primitive type string
    name — parameter identifier string
    """
    type: str
    name: str


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------
# Declarations can appear globally (inside a 'roof' block) or locally inside
# a function body.  VarDeclNode is reused for both contexts; the semantic
# analyzer distinguishes them by the scope it is currently traversing.

@dataclass
class GlobalDeclNode(ASTNode):
    """Abstract base class for all top-level (roof) declarations.

    Subclasses: VarDeclNode, StructDeclNode.
    StructMemberNode is NOT a GlobalDeclNode — it lives inside StructDeclNode.
    """
    pass


@dataclass
class VarDeclNode(GlobalDeclNode):
    """Variable (or constant) declaration: [cement] type id [= expr]

    Used for BOTH global declarations and local function-body declarations.

    Fields
    ------
    type             — primitive type ('tile', 'glass', 'brick', 'beam', 'wall')
                       or 'house <StructName>' for struct-typed variables.
    name             — identifier string.
    init_value       — initializer expression node, or None if absent.
    is_const         — True when declared with the 'cement' keyword.
    is_array         — True when array dimensions were declared.
    array_dims       — list of integer dimension sizes, e.g. [5] or [3, 4].
    struct_type_name — for 'house X' types, stores the bare struct name 'X'
                       so semantic code can call symbol_table.get_struct()
                       directly without string-splitting.  Automatically
                       derived in __post_init__ when not provided explicitly.

    Note: ASTBuilder may return a LIST of VarDeclNode from a single statement
    when multiple names are declared with commas (tile a=1, b=2, c=3;).
    """
    type: str
    name: str
    init_value: Optional['ExprNode'] = None
    is_const: bool = False      # cement keyword
    is_array: bool = False
    array_dims: list = None     # List[int] — dimension sizes

    # Brace initializer list for arrays and structs: [ExprNode, ...]
    # For 2D arrays: [[ExprNode, ...], [ExprNode, ...], ...]
    # None when no brace initializer was provided.
    init_list: Optional[list] = None

    # For house-typed variables: the bare struct type name extracted from `type`.
    struct_type_name: Optional[str] = None

    def __post_init__(self):
        # Auto-derive struct_type_name from the type field when it is a
        # 'house X' string.  This avoids repeated string-splitting in the
        # semantic analyzer.
        if self.struct_type_name is None and isinstance(self.type, str):
            if self.type.startswith("house "):
                self.struct_type_name = self.type[6:].strip()


@dataclass
class StructDeclNode(GlobalDeclNode):
    """Struct type definition: house id { members }

    name    — struct type name (used as a key in the symbol table).
    members — ordered list of StructMemberNode describing each field.
    """
    name: str
    members: list   # List[StructMemberNode]


@dataclass
class StructMemberNode(ASTNode):
    """One field inside a struct definition: type id [array_spec]

    type     — primitive type string.
    name     — field identifier string.
    is_array — True when the field is declared as an array.
    array_dims — dimension sizes, or None.
    """
    type: str
    name: str
    is_array: bool = False
    array_dims: list = None     # List[int]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------
# StatementNode is the abstract base for all executable statements.
# Control-flow nodes (IfNode, WhileNode, etc.) each contain a nested `body`
# list so the tree can represent arbitrarily deep nesting.

@dataclass
class StatementNode(ASTNode):
    """Abstract base class for all statement nodes."""
    pass


@dataclass
class AssignNode(StatementNode):
    """Assignment statement: target = value  or  target op= value

    target   — IdNode, ArrayAccessNode, or StructAccessNode (the LHS).
    value    — any ExprNode (the RHS).
    operator — '=', '+=', '-=', '*=', '/=', or '%='.
    """
    target: 'ExprNode'
    value: 'ExprNode'
    operator: str = '='


@dataclass
class IfNode(StatementNode):
    """If / else-if / else statement.

    condition — boolean expression that controls branching.
    then_body — list of nodes executed when condition is true.
    else_body — list of nodes for the else branch, or None.
                An else-if is represented as [IfNode(...)].
    """
    condition: 'ExprNode'
    then_body: list             # List[ASTNode]
    else_body: Optional[list] = None   # Optional[List[ASTNode]]


@dataclass
class WhileNode(StatementNode):
    """While loop: while (condition) { body }"""
    condition: 'ExprNode'
    body: list                  # List[ASTNode]


@dataclass
class DoWhileNode(StatementNode):
    """Do-while loop: do { body } while (condition) ;

    Note: body executes BEFORE condition is evaluated for the first time.
    """
    body: list                  # List[ASTNode]
    condition: 'ExprNode'


@dataclass
class ForNode(StatementNode):
    """For loop: for (init ; condition ; increment) { body }

    init      — VarDeclNode or AssignNode (or None).
    condition — loop continuation condition expression.
    increment — update expression (often a postfix UnaryOpNode).
    body      — list of body statements.
    """
    init: Optional[ASTNode]     # VarDeclNode or AssignNode
    condition: 'ExprNode'
    increment: 'ExprNode'
    body: list                  # List[ASTNode]


@dataclass
class SwitchNode(StatementNode):
    """Switch statement: room (expr) { cases }

    expr  — expression whose value is matched against each case.
    cases — ordered list of CaseNode (door ... and ground).
    """
    expr: 'ExprNode'
    cases: list                 # List[CaseNode]


@dataclass
class CaseNode(ASTNode):
    """One branch of a switch statement.

    value      — literal ExprNode to match, or None for the default case.
    body       — statements in this branch.
    is_default — True when this is the 'ground:' (default) case.
    """
    value: Optional['ExprNode']
    body: list                  # List[ASTNode]
    is_default: bool = False


@dataclass
class BreakNode(StatementNode):
    """Break out of the current loop or switch: crack ;"""
    pass


@dataclass
class ContinueNode(StatementNode):
    """Skip to the next loop iteration: mend ;"""
    pass


@dataclass
class ReturnNode(StatementNode):
    """Function return: home [expr] ;

    value — return expression, or None for void (field) functions.
    """
    value: Optional['ExprNode'] = None


@dataclass
class IONode(StatementNode):
    """Built-in I/O call: view(...) or write(...)

    io_type       — 'view' (output / printf-like) or 'write' (input / scanf-like).
    format_string — the leading wall_lit format string.
    args          — list of expression arguments after the format string.
                    For 'write', ASTBuilder already strips the leading '&'.
    """
    io_type: str                # 'view' or 'write'
    format_string: str
    args: list                  # List[ExprNode]


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------
# Every ExprNode subclass carries an `expr_type` field (Optional[str]).
# This field is None when the node is first built by ASTBuilder.
# The SemanticAnalyzer fills it in during the type-checking pass.
# The TAC generator can read expr_type to know which temporary type to emit.

@dataclass
class ExprNode(ASTNode):
    """Abstract base class for all expression nodes.

    Note: expr_type is intentionally left out of the base class so that
    dataclass inheritance works cleanly.  Each concrete subclass declares
    its own expr_type field with a default of None.
    """
    pass


@dataclass
class BinaryOpNode(ExprNode):
    """Binary operation: left op right

    Covers arithmetic (+, -, *, /, %), relational (<, <=, >, >=, ==, !=),
    and logical (&&, ||) operators.
    expr_type is set by the semantic analyzer after operand types are resolved.
    """
    left: 'ExprNode'
    operator: str
    right: 'ExprNode'
    expr_type: Optional[str] = None


@dataclass
class UnaryOpNode(ExprNode):
    """Unary operation: op expr  or  expr op

    operator  — '!', '-' (negation), '++', or '--'.
    is_prefix — True for prefix forms (++x, --x, !x, -x).
                False for postfix forms (x++, x--).
    expr_type — set by the semantic analyzer.
    """
    operator: str
    operand: 'ExprNode'
    is_prefix: bool = True
    expr_type: Optional[str] = None


@dataclass
class LiteralNode(ExprNode):
    """A literal constant value: 123, 3.14, 'c', "string", solid, fragile

    value        — raw lexeme string from the token stream.
    literal_type — the arCh type inferred from the token type:
                   'tile' (tile_lit), 'glass' (glass_lit), 'brick' (brick_lit),
                   'wall' (wall_lit), 'beam' (solid/fragile).
    expr_type    — same as literal_type; set redundantly by the semantic analyzer
                   to keep the traversal uniform.
    """
    value: Any
    literal_type: str
    expr_type: Optional[str] = None


@dataclass
class IdNode(ExprNode):
    """A bare identifier reference (variable or constant name).

    name      — the identifier string.
    expr_type — set by the semantic analyzer after the symbol is resolved.
    """
    name: str
    expr_type: Optional[str] = None


@dataclass
class ArrayAccessNode(ExprNode):
    """Array element access: array[index]  or  array[i][j]

    array    — the base expression (typically an IdNode).
    indices  — list of index expressions; length 1 for 1-D, 2 for 2-D.
    expr_type— element type, set by the semantic analyzer.
    """
    array: 'ExprNode'
    indices: list               # List[ExprNode]
    expr_type: Optional[str] = None


@dataclass
class StructAccessNode(ExprNode):
    """Struct member access: struct_expr . member_name

    struct    — the expression evaluating to a struct instance (usually IdNode).
    member    — the field name string.
    expr_type — the field's type, set by the semantic analyzer.
    """
    struct: 'ExprNode'
    member: str
    expr_type: Optional[str] = None


@dataclass
class FunctionCallNode(ExprNode):
    """Function call expression (also used as a standalone call-statement).

    func_name — the function identifier string.
    args      — ordered list of argument ExprNodes.
    expr_type — the function's return type, set by the semantic analyzer.
    """
    func_name: str
    args: list                  # List[ExprNode]
    expr_type: Optional[str] = None


@dataclass
class WallConcatNode(ExprNode):
    """Wall (string) concatenation: wall_expr + wall_expr + ...

    parts     — ordered list of ExprNodes that are joined into one string.
                Each element must evaluate to type 'wall'.
    expr_type — always 'wall'; set by the semantic analyzer.
    """
    parts: list                 # List[ExprNode]
    expr_type: Optional[str] = None


@dataclass
class ArrayInitNode(ExprNode):
    """Brace-enclosed array initializer: {val1, val2, ...}

    elements  — flat list of ExprNodes for 1-D arrays, or list of
                ArrayInitNode for 2-D arrays ({row1}, {row2}).
    expr_type — set to the array element type by the semantic analyzer.
    """
    elements: list              # List[ExprNode] or List[ArrayInitNode]
    expr_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Type Information and Type Hierarchy
# ---------------------------------------------------------------------------
# TypeInfo wraps a base_type string with metadata (arrays, structs, const).
# It is used by the semantic analyzer for type comparison and casting decisions.
#
# The numeric type hierarchy (used for implicit promotion and demotion):
#
#   brick (char)  rank 0  — narrowest
#   beam  (bool)  rank 1
#   tile  (int)   rank 2
#   glass (float) rank 3  — widest
#
# wall (string) is COMPLETELY ISOLATED: it cannot be cast to or from any
# other type.  house (struct) types are also isolated except from themselves.
#
# Both widening (brick → glass) and narrowing (glass → tile) are permitted
# by the language specification, matching C semantics.  Narrowing may
# truncate values but is NOT reported as a type error.

TYPE_ORDER: dict = {
    'brick': 0,   # char     — narrowest
    'beam':  1,   # bool
    'tile':  2,   # int
    'glass': 3,   # float    — widest
}

# Backward-compatibility alias.  Existing code checks `x in _NUMERIC_RANK`
# to test membership in the castable hierarchy.
_NUMERIC_RANK: dict = TYPE_ORDER

# The frozenset of all types that participate in implicit casting.
# wall and house are excluded because they are not castable.
_CASTABLE_TYPES: frozenset = frozenset(TYPE_ORDER.keys())


@dataclass
class TypeInfo:
    """Wraps a type for use in semantic analysis.

    base_type  — the raw type keyword: 'tile', 'glass', 'brick', 'beam',
                 'wall', 'field' (void), or 'house' (struct).
    is_array   — True when this represents an array type.
    array_dims — dimension sizes for array types.
    struct_name— the struct type name when base_type == 'house'.
    is_const   — True when the symbol was declared with 'cement'.

    Key methods
    -----------
    is_numeric()    — True for brick/beam/tile/glass (all castable types).
    is_bool()       — True for beam.
    is_string()     — True for wall.
    is_void()       — True for field.
    is_struct()     — True for house.
    wider_numeric() — Returns the wider of two numeric TypeInfos (for expression typing).
    can_cast_to()   — Returns True when this type is assignment-compatible with target.
    """
    base_type: str
    is_array: bool = False
    array_dims: list = None     # List[int]
    struct_name: Optional[str] = None
    is_const: bool = False

    def __str__(self):
        if self.is_array:
            dims = ''.join(f'[{d}]' for d in (self.array_dims or []))
            return f'{self.base_type}{dims}'
        if self.struct_name:
            return f'house {self.struct_name}'
        return self.base_type

    # ── type predicates ───────────────────────────────────────────────────

    def is_numeric(self) -> bool:
        """True for all types in the implicit cast hierarchy: brick, beam, tile, glass."""
        return self.base_type in TYPE_ORDER

    def is_bool(self) -> bool:
        """beam (boolean)"""
        return self.base_type == 'beam'

    def is_string(self) -> bool:
        """wall (string)"""
        return self.base_type == 'wall'

    def is_void(self) -> bool:
        """field (void return type)"""
        return self.base_type == 'field'

    def is_struct(self) -> bool:
        """house <StructName>"""
        return self.base_type == 'house'

    # ── promotion / demotion ─────────────────────────────────────────────

    def wider_numeric(self, other: 'TypeInfo') -> Optional['TypeInfo']:
        """Return the dominant (wider) type between self and other.

        Used when resolving the result type of a binary expression:
        the result should be the wider operand's type so precision is kept.

        Returns None if either type is not in TYPE_ORDER (e.g. wall, house).

        Examples
        --------
        brick.wider_numeric(tile)  → tile   (rank 2 > rank 0)
        tile.wider_numeric(glass)  → glass  (rank 3 > rank 2)
        beam.wider_numeric(glass)  → glass
        """
        if self.base_type not in TYPE_ORDER or other.base_type not in TYPE_ORDER:
            return None
        if TYPE_ORDER[self.base_type] >= TYPE_ORDER[other.base_type]:
            return self
        return other

    # ── assignment / cast compatibility ──────────────────────────────────

    def can_cast_to(self, target: 'TypeInfo') -> bool:
        """Return True when this type is implicitly compatible with target.

        Rules (aligned with the arCh language specification)
        -----------------------------------------------------
        1. Same base type is always valid.
           - For structs: struct names must also match.
           - For arrays:  both must be arrays with the same dimension list.
        2. wall is COMPLETELY ISOLATED.
           wall→X and X→wall are invalid (except wall→wall, covered by rule 1).
        3. Both types in TYPE_ORDER (brick/beam/tile/glass) → VALID in BOTH
           directions.  Demotions (glass→tile) may truncate but are not errors.
        4. Cross-type array assignment (tile[] = glass[]) is not allowed.
        5. Structs must share the same named type.
        6. All other combinations require an exact match (already checked in 1).
        """
        # Rule 1: exact match
        if self.base_type == target.base_type:
            if self.base_type == 'house':
                return self.struct_name == target.struct_name
            if self.is_array or target.is_array:
                return (self.is_array == target.is_array
                        and self.array_dims == target.array_dims)
            return True

        # Rule 2: wall isolation
        if self.is_string() or target.is_string():
            return False

        # Rule 4: cross-type array cast not allowed
        if self.is_array or target.is_array:
            return False

        # Rule 3: both in castable hierarchy → valid in both directions
        if self.base_type in TYPE_ORDER and target.base_type in TYPE_ORDER:
            return True

        # Rule 6: anything else requires exact match (already handled by rule 1)
        return False