from dataclasses import dataclass, field
from typing import Any, Optional, List


# ============================================================================
# Base Node
# ============================================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    line: int
    col: int


# ============================================================================
# Program Structure
# ============================================================================

@dataclass
class ProgramNode(ASTNode):
    """Root node: <program> → <global> <program_body>"""
    globals: list  # List[GlobalDeclNode]
    functions: list  # List[FunctionNode]


@dataclass
class FunctionNode(ASTNode):
    """Function definition: wall/return_type id(...) { ... }"""
    return_type: str  # 'tile', 'glass', 'brick', 'beam', 'field', 'wall'
    name: str
    params: list  # List[ParamNode]
    body: list    # List[ASTNode]  — statements and declarations
    is_blueprint: bool = False  # True for blueprint() entry point


@dataclass
class ParamNode(ASTNode):
    """Function parameter: type id"""
    type: str
    name: str


# ============================================================================
# Declarations
# ============================================================================

@dataclass
class GlobalDeclNode(ASTNode):
    """Global variable/const/struct declaration"""
    pass


@dataclass
class VarDeclNode(GlobalDeclNode):
    """Variable declaration: type id = expr

    Fields (all preserved from original):
      type        — primitive type string ('tile', 'glass', 'brick', 'beam', 'wall')
                    or 'house <StructName>' for struct variables
      name        — identifier string
      init_value  — initializer expression node, or None
      is_const    — True when declared with 'cement'
      is_array    — True when declared with array dimensions
      array_dims  — list of dimension sizes (or None)

    NEW fields:
      struct_type_name — when type starts with 'house', stores the bare struct name
                         so that member lookups work without string-splitting.
    """
    type: str
    name: str
    init_value: Optional['ExprNode'] = None
    is_const: bool = False  # cement keyword
    is_array: bool = False
    array_dims: list = None  # List[int]  For arrays

    # NEW: for house-typed variables, records the struct type name separately
    # so the semantic analyzer can call symbol_table.get_struct() directly.
    # Populated by ast_builder when it parses "house TypeName varName".
    struct_type_name: Optional[str] = None

    def __post_init__(self):
        # Auto-derive struct_type_name from type field if not set
        # e.g. type="house Area" → struct_type_name="Area"
        if self.struct_type_name is None and isinstance(self.type, str):
            if self.type.startswith("house "):
                self.struct_type_name = self.type[6:].strip()


@dataclass
class StructDeclNode(GlobalDeclNode):
    """Struct declaration: house id { members }"""
    name: str
    members: list  # List[StructMemberNode]


@dataclass
class StructMemberNode(ASTNode):
    """Struct member: type id [array_spec]"""
    type: str
    name: str
    is_array: bool = False
    array_dims: list = None  # List[int]


# ============================================================================
# Statements
# ============================================================================

@dataclass
class StatementNode(ASTNode):
    """Base class for statements"""
    pass


@dataclass
class AssignNode(StatementNode):
    """Assignment: lhs = rhs or lhs op= rhs"""
    target: 'ExprNode'  # id, array access, or struct access
    value: 'ExprNode'
    operator: str = '='  # '=', '+=', '-=', '*=', '/=', '%='


@dataclass
class IfNode(StatementNode):
    """If statement: if (cond) { body } else { else_body }"""
    condition: 'ExprNode'
    then_body: list  # List[ASTNode]
    else_body: Optional[list] = None  # Optional[List[ASTNode]]


@dataclass
class WhileNode(StatementNode):
    """While loop: while (cond) { body }"""
    condition: 'ExprNode'
    body: list  # List[ASTNode]


@dataclass
class DoWhileNode(StatementNode):
    """Do-while loop: do { body } while (cond)"""
    body: list  # List[ASTNode]
    condition: 'ExprNode'


@dataclass
class ForNode(StatementNode):
    """For loop: for (init; cond; incr) { body }"""
    init: Optional[ASTNode]  # VarDeclNode or AssignNode
    condition: 'ExprNode'
    increment: 'ExprNode'
    body: list  # List[ASTNode]


@dataclass
class SwitchNode(StatementNode):
    """Switch: room (expr) { cases }"""
    expr: 'ExprNode'
    cases: list  # List[CaseNode]


@dataclass
class CaseNode(ASTNode):
    """Case: door value: body or ground: body"""
    value: Optional['ExprNode']  # None for ground (default)
    body: list  # List[ASTNode]
    is_default: bool = False


@dataclass
class BreakNode(StatementNode):
    """Break: crack"""
    pass


@dataclass
class ContinueNode(StatementNode):
    """Continue: mend"""
    pass


@dataclass
class ReturnNode(StatementNode):
    """Return: home expr"""
    value: Optional['ExprNode'] = None


@dataclass
class IONode(StatementNode):
    """I/O: view(...) or write(...)"""
    io_type: str  # 'view' or 'write'
    format_string: str
    args: list  # List[ExprNode]


# ============================================================================
# Expressions
# ============================================================================

@dataclass
class ExprNode(ASTNode):
    """Base class for expressions"""
    pass  # expr_type: Optional[str] = None


@dataclass
class BinaryOpNode(ExprNode):
    """Binary operation: left op right"""
    left: 'ExprNode'
    operator: str
    right: 'ExprNode'
    expr_type: Optional[str] = None


@dataclass
class UnaryOpNode(ExprNode):
    """Unary operation: op expr"""
    operator: str  # !, ++, --, - (negation)
    operand: 'ExprNode'
    is_prefix: bool = True
    expr_type: Optional[str] = None


@dataclass
class LiteralNode(ExprNode):
    """Literal value: 123, 3.14, "string", solid, fragile"""
    value: Any
    literal_type: str  # 'tile', 'glass', 'brick', 'wall', 'beam'
    expr_type: Optional[str] = None


@dataclass
class IdNode(ExprNode):
    """Identifier: variable name"""
    name: str
    expr_type: Optional[str] = None


@dataclass
class ArrayAccessNode(ExprNode):
    """Array access: array[index1][index2]"""
    array: 'ExprNode'
    indices: list  # List[ExprNode]
    expr_type: Optional[str] = None


@dataclass
class StructAccessNode(ExprNode):
    """Struct member access: struct.member"""
    struct: 'ExprNode'
    member: str
    expr_type: Optional[str] = None


@dataclass
class FunctionCallNode(ExprNode):
    """Function call: func(args)"""
    func_name: str
    args: list  # List[ExprNode]
    expr_type: Optional[str] = None


@dataclass
class WallConcatNode(ExprNode):
    """Wall (string) concatenation: wall1 + wall2"""
    parts: list  # List[ExprNode]  — wall expressions to concatenate
    expr_type: Optional[str] = None


# ============================================================================
# Type Information
# ============================================================================

# ---------------------------------------------------------------------------
# Centralised type hierarchy — used by TypeInfo and SemanticAnalyzer.
#
# The language supports BOTH promotion (widening) and demotion (narrowing)
# between brick / beam / tile / glass, exactly like C.
#
#   brick  (char)    — narrowest  rank 0
#   beam   (bool)    — rank 1
#   tile   (int)     — rank 2
#   glass  (float)   — widest     rank 3
#
# wall (string) is COMPLETELY ISOLATED: no casting to or from any other type.
#
# Promotion  (e.g. brick → tile): always safe, no precision loss.
# Demotion   (e.g. glass → tile): allowed but may truncate, just like C.
#
# Previous name _NUMERIC_RANK is kept as an alias so existing call-sites
# that check `x in _NUMERIC_RANK` still work — they just now also cover beam.
# ---------------------------------------------------------------------------
TYPE_ORDER: dict = {
    'brick': 0,   # char     — narrowest
    'beam':  1,   # bool
    'tile':  2,   # int
    'glass': 3,   # float    — widest
}

# Alias for backward compatibility with existing isinstance / membership checks
_NUMERIC_RANK: dict = TYPE_ORDER

# The set of all types that participate in implicit casting (wall excluded)
_CASTABLE_TYPES: frozenset = frozenset(TYPE_ORDER.keys())


@dataclass
class TypeInfo:
    """Type information for semantic analysis.

    Preserved from original: base_type, is_array, array_dims, struct_name,
    is_const, is_numeric(), is_bool(), is_string(), can_cast_to().

    NEW helpers: wider_numeric(), is_void(), is_struct().
    """
    base_type: str  # 'tile', 'glass', 'brick', 'beam', 'wall', 'field', 'house'
    is_array: bool = False
    array_dims: list = None  # List[int]
    struct_name: Optional[str] = None  # For house types
    is_const: bool = False

    def __str__(self):
        if self.is_array:
            dims = ''.join(f'[{d}]' for d in (self.array_dims or []))
            return f'{self.base_type}{dims}'
        if self.struct_name:
            return f'house {self.struct_name}'
        return self.base_type

    # ── type predicates ───────────────────────────────────────────────────────

    def is_numeric(self) -> bool:
        """True for all types in the implicit cast hierarchy: brick, beam, tile, glass."""
        return self.base_type in TYPE_ORDER

    def is_bool(self) -> bool:
        """beam"""
        return self.base_type == 'beam'

    def is_string(self) -> bool:
        """wall"""
        return self.base_type == 'wall'

    def is_void(self) -> bool:
        """field (void return type)"""
        return self.base_type == 'field'

    def is_struct(self) -> bool:
        """house <n>"""
        return self.base_type == 'house'

    # ── promotion / demotion ──────────────────────────────────────────────────

    def wider_numeric(self, other: 'TypeInfo') -> Optional['TypeInfo']:
        """Return the dominant (wider) of two castable types.

        For EXPRESSION EVALUATION, always pick the WIDER type so precision
        is preserved during computation.
        Returns None if either type is not in TYPE_ORDER (e.g. wall, house).

        Examples
        --------
        brick.wider_numeric(tile)  -> tile   (rank 2 > rank 0)
        tile.wider_numeric(glass)  -> glass  (rank 3 > rank 2)
        beam.wider_numeric(glass)  -> glass
        """
        if self.base_type not in TYPE_ORDER or other.base_type not in TYPE_ORDER:
            return None
        if TYPE_ORDER[self.base_type] >= TYPE_ORDER[other.base_type]:
            return self
        return other

    # ── assignment / cast compatibility ───────────────────────────────────────

    def can_cast_to(self, target: 'TypeInfo') -> bool:
        """Check whether this type can be implicitly cast to *target*.

        Rules (aligned with language specification):
          1. Same base type  -> always valid (struct: same name; array: same dims).
          2. wall is COMPLETELY ISOLATED.
             wall->X  and  X->wall  are both invalid (except wall->wall).
          3. Both types are in TYPE_ORDER (brick/beam/tile/glass) -> VALID.
             The language allows BOTH promotion AND demotion, like C.
               Promotions: brick->beam, beam->tile, tile->glass, brick->glass ...
               Demotions:  glass->tile, tile->beam, beam->brick ...
             Demotion may truncate values but is NOT a type error.
          4. Arrays: cross-type array assignment is not allowed.
          5. Structs: must be the same named struct.
          6. Everything else: exact match only.
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

        # Rule 3: both in castable hierarchy -> valid in both directions
        if self.base_type in TYPE_ORDER and target.base_type in TYPE_ORDER:
            return True

        # Rule 6: anything else requires exact match (already checked in rule 1)
        return False