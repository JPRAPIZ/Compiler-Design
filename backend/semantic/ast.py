from dataclasses import dataclass
from typing import Any, Optional


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
    globals: list['GlobalDeclNode']
    functions: list['FunctionNode']


@dataclass
class FunctionNode(ASTNode):
    """Function definition: wall/return_type id(...) { ... }"""
    return_type: str  # 'tile', 'glass', 'brick', 'beam', 'field', 'wall'
    name: str
    params: list['ParamNode']
    body: list[ASTNode]  # statements and declarations
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
    """Variable declaration: type id = expr"""
    type: str
    name: str
    init_value: Optional['ExprNode'] = None
    is_const: bool = False  # cement keyword
    is_array: bool = False
    array_dims: list[int] = None  # For arrays


@dataclass
class StructDeclNode(GlobalDeclNode):
    """Struct declaration: house id { members }"""
    name: str
    members: list['StructMemberNode']


@dataclass
class StructMemberNode(ASTNode):
    """Struct member: type id [array_spec]"""
    type: str
    name: str
    is_array: bool = False
    array_dims: list[int] = None


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
    then_body: list[ASTNode]
    else_body: Optional[list[ASTNode]] = None


@dataclass
class WhileNode(StatementNode):
    """While loop: while (cond) { body }"""
    condition: 'ExprNode'
    body: list[ASTNode]


@dataclass
class DoWhileNode(StatementNode):
    """Do-while loop: do { body } while (cond)"""
    body: list[ASTNode]
    condition: 'ExprNode'


@dataclass
class ForNode(StatementNode):
    """For loop: for (init; cond; incr) { body }"""
    init: Optional[ASTNode]  # VarDeclNode or AssignNode
    condition: 'ExprNode'
    increment: 'ExprNode'
    body: list[ASTNode]


@dataclass
class SwitchNode(StatementNode):
    """Switch: room (expr) { cases }"""
    expr: 'ExprNode'
    cases: list['CaseNode']


@dataclass
class CaseNode(ASTNode):
    """Case: door value: body or ground: body"""
    value: Optional['ExprNode']  # None for ground (default)
    body: list[ASTNode]
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
    args: list['ExprNode']


# ============================================================================
# Expressions
# ============================================================================

@dataclass
class ExprNode(ASTNode):
    """Base class for expressions"""
    pass # expr_type: Optional[str] = None


@dataclass
class BinaryOpNode(ExprNode):
    """Binary operation: left op right"""
    left: ExprNode
    operator: str
    right: ExprNode
    expr_type: Optional[str] = None  # ← Move this line to end


@dataclass
class UnaryOpNode(ExprNode):
    """Unary operation: op expr"""
    operator: str  # !, ++, --, - (negation)
    operand: ExprNode
    is_prefix: bool = True
    expr_type: Optional[str] = None

@dataclass
class LiteralNode(ExprNode):
    """Literal value: 123, 3.14, "string", solid, fragile"""
    value: Any
    literal_type: str  # 'tile', 'glass', 'brick', 'wall', 'solid', 'fragile'
    expr_type: Optional[str] = None

@dataclass
class IdNode(ExprNode):
    """Identifier: variable name"""
    name: str
    expr_type: Optional[str] = None

@dataclass
class ArrayAccessNode(ExprNode):
    """Array access: array[index1][index2]"""
    array: ExprNode
    indices: list[ExprNode]
    expr_type: Optional[str] = None

@dataclass
class StructAccessNode(ExprNode):
    """Struct member access: struct.member"""
    struct: ExprNode
    member: str
    expr_type: Optional[str] = None

@dataclass
class FunctionCallNode(ExprNode):
    """Function call: func(args)"""
    func_name: str
    args: list[ExprNode]
    expr_type: Optional[str] = None

@dataclass
class WallConcatNode(ExprNode):
    """Wall (string) concatenation: wall1 + wall2"""
    parts: list[ExprNode]  # List of wall expressions to concatenate
    expr_type: Optional[str] = None

# ============================================================================
# Type Information
# ============================================================================

@dataclass
class TypeInfo:
    """Type information for semantic analysis"""
    base_type: str  # 'tile', 'glass', 'brick', 'beam', 'wall', 'field', 'house'
    is_array: bool = False
    array_dims: list[int] = None
    struct_name: Optional[str] = None  # For house types
    is_const: bool = False

    def __str__(self):
        if self.is_array:
            dims = ''.join(f'[{d}]' for d in (self.array_dims or []))
            return f'{self.base_type}{dims}'
        if self.struct_name:
            return f'house {self.struct_name}'
        return self.base_type

    def is_numeric(self) -> bool:
        """Check if type is numeric (tile, glass, brick)"""
        return self.base_type in ('tile', 'glass', 'brick')

    def is_bool(self) -> bool:
        """Check if type is boolean (beam)"""
        return self.base_type == 'beam'

    def is_string(self) -> bool:
        """Check if type is string (wall)"""
        return self.base_type == 'wall'

    def can_cast_to(self, target: 'TypeInfo') -> bool:
        """Check if this type can be implicitly cast to target type"""
        # Wall (string) has NO implicit casting
        if self.is_string() or target.is_string():
            return self.base_type == target.base_type

        # Arrays must match exactly
        if self.is_array or target.is_array:
            return (self.is_array == target.is_array and
                    self.base_type == target.base_type and
                    self.array_dims == target.array_dims)

        # Numeric type hierarchy: tile → glass → brick
        numeric_hierarchy = {'tile': 0, 'glass': 1, 'brick': 2}

        if self.base_type in numeric_hierarchy and target.base_type in numeric_hierarchy:
            return numeric_hierarchy[self.base_type] <= numeric_hierarchy[target.base_type]

        # beam (bool) can only be beam
        if self.is_bool() or target.is_bool():
            return self.base_type == target.base_type

        # Exact match
        return self.base_type == target.base_type