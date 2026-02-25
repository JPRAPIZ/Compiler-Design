"""
Semantic Analyzer for arCh Language
Performs type checking, scope resolution, and semantic error detection
Uses Visitor Pattern with DFS traversal (Pre-order for analysis)
"""

from typing import List, Dict, Optional, Any
from parser.cfg import PRODUCTIONS
from semantic.ast import *
from semantic.symbol_table import SymbolTable, Symbol


class SemanticError:
    """Represents a semantic error"""

    def __init__(self, message: str, line: int, col: int):
        self.message = message
        self.line = line
        self.col = col
        self.start_line = line
        self.start_col = col
        self.end_line = line
        self.end_col = col + 1

    def to_dict(self):
        return {
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }


class SemanticAnalyzer:
    """
    Semantic Analyzer using Visitor Pattern
    Traversal: DFS Pre-order (analyze before children)
    """

    def __init__(self, ast: ProgramNode):
        self.ast = ast
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticError] = []
        self.current_function_return_type: Optional[str] = None
        self.in_loop = False

    def analyze(self) -> List[Dict]:
        """
        Main entry point for semantic analysis
        Returns list of error dicts
        """
        try:
            self.visit_program(self.ast)
        except Exception as e:
            # Catch any unexpected errors during analysis
            self.errors.append(SemanticError(
                f"Internal semantic error: {str(e)}",
                1, 1
            ))

        return [err.to_dict() for err in self.errors]

    def add_error(self, message: str, line: int, col: int):
        """Add a semantic error"""
        self.errors.append(SemanticError(message, line, col))

    # ========================================================================
    # Visitor Methods (Pre-order DFS)
    # ========================================================================

    def visit_program(self, node: ProgramNode):
        """Visit program root"""
        # Pass 1: Declare all global symbols (structs, functions, globals)
        for global_decl in node.globals:
            if isinstance(global_decl, StructDeclNode):
                self.declare_struct(global_decl)

        for global_decl in node.globals:
            if isinstance(global_decl, VarDeclNode):
                self.declare_global_variable(global_decl)

        for func in node.functions:
            self.declare_function(func)

        # Pass 2: Analyze function bodies
        for func in node.functions:
            self.visit_function(func)

        # Check that blueprint() exists
        if not self.symbol_table.get_function("blueprint"):
            self.add_error(
                "Missing entry point: blueprint() function not defined",
                1, 1
            )

    def declare_struct(self, node: StructDeclNode):
        """Declare a struct in symbol table"""
        # Check if struct already exists
        if self.symbol_table.get_struct(node.name):
            self.add_error(
                f"Struct '{node.name}' already defined",
                node.line, node.col
            )
            return

        # Build member dict
        members = {}
        member_names = set()

        for member in node.members:
            if member.name in member_names:
                self.add_error(
                    f"Duplicate member '{member.name}' in struct '{node.name}'",
                    member.line, member.col
                )
                continue

            member_names.add(member.name)
            members[member.name] = Symbol(
                name=member.name,
                type=member.type,
                kind="variable",
                is_array=member.is_array,
                array_dims=member.array_dims,
                line=member.line,
                col=member.col
            )

        self.symbol_table.define_struct(node.name, members, node.line, node.col)

    def declare_global_variable(self, node: VarDeclNode):
        """Declare global variable"""
        # Check if already defined
        if self.symbol_table.lookup_local(node.name):
            self.add_error(
                f"Global variable '{node.name}' already defined",
                node.line, node.col
            )
            return

        # Create symbol
        symbol = Symbol(
            name=node.name,
            type=node.type,
            kind="constant" if node.is_const else "variable",
            is_const=node.is_const,
            is_array=node.is_array,
            array_dims=node.array_dims,
            line=node.line,
            col=node.col
        )

        self.symbol_table.define_global(symbol)

        # Type check initializer if present
        if node.init_value:
            init_type = self.visit_expr(node.init_value)
            if init_type and not self.can_assign(node.type, init_type):
                self.add_error(
                    f"Type mismatch in initialization: cannot assign {init_type} to {node.type}",
                    node.line, node.col
                )

    def declare_function(self, node: FunctionNode):
        """Declare function in symbol table"""
        # Check if already defined
        if self.symbol_table.get_function(node.name):
            self.add_error(
                f"Function '{node.name}' already defined",
                node.line, node.col
            )
            return

        # Build parameter list
        params = []
        for param in node.params:
            params.append(Symbol(
                name=param.name,
                type=param.type,
                kind="parameter",
                line=param.line,
                col=param.col
            ))

        # Create function symbol
        func_symbol = Symbol(
            name=node.name,
            type=node.return_type,
            kind="function",
            return_type=node.return_type,
            params=params,
            line=node.line,
            col=node.col
        )

        self.symbol_table.define_global(func_symbol)

    def visit_function(self, node: FunctionNode):
        """Visit function definition and analyze body"""
        self.current_function_return_type = node.return_type

        # Enter function scope
        self.symbol_table.enter_scope(node.name)

        # Add parameters to function scope
        param_names = set()
        for param in node.params:
            if param.name in param_names:
                self.add_error(
                    f"Duplicate parameter '{param.name}'",
                    param.line, param.col
                )
                continue

            param_names.add(param.name)
            symbol = Symbol(
                name=param.name,
                type=param.type,
                kind="parameter",
                line=param.line,
                col=param.col
            )
            self.symbol_table.define(symbol)

        # Analyze body
        for stmt in node.body:
            self.visit_statement(stmt)

        # Check return type
        if node.return_type != "field" and not node.is_blueprint:
            # TODO: Add path analysis to ensure all paths return
            pass

        # Exit function scope
        self.symbol_table.exit_scope()
        self.current_function_return_type = None

    def visit_statement(self, node: ASTNode):
        """Dispatch to specific statement visitor"""
        if isinstance(node, VarDeclNode):
            self.visit_var_decl(node)
        elif isinstance(node, AssignNode):
            self.visit_assign(node)
        elif isinstance(node, IfNode):
            self.visit_if(node)
        elif isinstance(node, WhileNode):
            self.visit_while(node)
        elif isinstance(node, DoWhileNode):
            self.visit_dowhile(node)
        elif isinstance(node, ForNode):
            self.visit_for(node)
        elif isinstance(node, SwitchNode):
            self.visit_switch(node)
        elif isinstance(node, BreakNode):
            self.visit_break(node)
        elif isinstance(node, ContinueNode):
            self.visit_continue(node)
        elif isinstance(node, ReturnNode):
            self.visit_return(node)
        elif isinstance(node, IONode):
            self.visit_io(node)
        elif isinstance(node, FunctionCallNode):
            self.visit_function_call(node)

    def visit_var_decl(self, node: VarDeclNode):
        """Visit variable declaration"""
        # Check if already declared in current scope
        if self.symbol_table.lookup_local(node.name):
            self.add_error(
                f"Variable '{node.name}' already declared in this scope",
                node.line, node.col
            )
            return

        # Create symbol
        symbol = Symbol(
            name=node.name,
            type=node.type,
            kind="constant" if node.is_const else "variable",
            is_const=node.is_const,
            is_array=node.is_array,
            array_dims=node.array_dims,
            line=node.line,
            col=node.col
        )

        self.symbol_table.define(symbol)

        # Type check initializer
        if node.init_value:
            init_type = self.visit_expr(node.init_value)
            if init_type and not self.can_assign(node.type, init_type):
                self.add_error(
                    f"Type mismatch: cannot assign {init_type} to {node.type}",
                    node.line, node.col
                )

    def visit_assign(self, node: AssignNode):
        """Visit assignment statement"""
        # Get target type
        target_type = self.visit_expr(node.target)
        if not target_type:
            return

        # Check if target is assignable (not const)
        if isinstance(node.target, IdNode):
            symbol = self.symbol_table.lookup(node.target.name)
            if symbol and symbol.is_const:
                self.add_error(
                    f"Cannot assign to constant '{node.target.name}'",
                    node.line, node.col
                )
                return

        # Get value type
        value_type = self.visit_expr(node.value)
        if not value_type:
            return

        # For compound operators (+=, -=, etc.), check operator compatibility
        if node.operator != '=':
            # Extract base operator (+, -, *, /, %)
            base_op = node.operator[0]
            result_type = self.check_binary_op(target_type, base_op, value_type, node.line, node.col)
            if result_type and not self.can_assign(target_type, result_type):
                self.add_error(
                    f"Type mismatch in compound assignment: {target_type} {node.operator} {value_type}",
                    node.line, node.col
                )
        else:
            # Regular assignment
            if not self.can_assign(target_type, value_type):
                self.add_error(
                    f"Type mismatch: cannot assign {value_type} to {target_type}",
                    node.line, node.col
                )

    def visit_if(self, node: IfNode):
        """Visit if statement"""
        # Check condition is beam (bool)
        cond_type = self.visit_expr(node.condition)
        if cond_type and cond_type != "beam":
            self.add_error(
                f"If condition must be beam (boolean), got {cond_type}",
                node.line, node.col
            )

        # Visit then body
        self.symbol_table.enter_scope("block")
        for stmt in node.then_body:
            self.visit_statement(stmt)
        self.symbol_table.exit_scope()

        # Visit else body
        if node.else_body:
            self.symbol_table.enter_scope("block")
            for stmt in node.else_body:
                self.visit_statement(stmt)
            self.symbol_table.exit_scope()

    def visit_while(self, node: WhileNode):
        """Visit while loop"""
        cond_type = self.visit_expr(node.condition)
        if cond_type and cond_type != "beam":
            self.add_error(
                f"While condition must be beam (boolean), got {cond_type}",
                node.line, node.col
            )

        self.symbol_table.enter_scope("while")
        old_in_loop = self.in_loop
        self.in_loop = True

        for stmt in node.body:
            self.visit_statement(stmt)

        self.in_loop = old_in_loop
        self.symbol_table.exit_scope()

    def visit_dowhile(self, node: DoWhileNode):
        """Visit do-while loop"""
        self.symbol_table.enter_scope("dowhile")
        old_in_loop = self.in_loop
        self.in_loop = True

        for stmt in node.body:
            self.visit_statement(stmt)

        self.in_loop = old_in_loop
        self.symbol_table.exit_scope()

        cond_type = self.visit_expr(node.condition)
        if cond_type and cond_type != "beam":
            self.add_error(
                f"Do-while condition must be beam (boolean), got {cond_type}",
                node.line, node.col
            )

    def visit_for(self, node: ForNode):
        """Visit for loop"""
        self.symbol_table.enter_scope("for")
        old_in_loop = self.in_loop
        self.in_loop = True

        # Visit init
        if node.init:
            if isinstance(node.init, VarDeclNode):
                self.visit_var_decl(node.init)
            elif isinstance(node.init, AssignNode):
                self.visit_assign(node.init)

        # Check condition
        cond_type = self.visit_expr(node.condition)
        if cond_type and cond_type != "beam":
            self.add_error(
                f"For condition must be beam (boolean), got {cond_type}",
                node.line, node.col
            )

        # Visit increment
        if node.increment:
            self.visit_expr(node.increment)

        # Visit body
        for stmt in node.body:
            self.visit_statement(stmt)

        self.in_loop = old_in_loop
        self.symbol_table.exit_scope()

    def visit_switch(self, node: SwitchNode):
        """Visit switch statement"""
        # Check switch expression type
        switch_type = self.visit_expr(node.expr)

        self.symbol_table.enter_scope("switch")
        old_in_loop = self.in_loop
        self.in_loop = True

        # Visit each case
        for case in node.cases:
            if not case.is_default and case.value:
                case_type = self.visit_expr(case.value)
                if switch_type and case_type and switch_type != case_type:
                    self.add_error(
                        f"Case value type {case_type} doesn't match switch type {switch_type}",
                        case.line, case.col
                    )

            for stmt in case.body:
                self.visit_statement(stmt)

        self.in_loop = old_in_loop
        self.symbol_table.exit_scope()

    def visit_break(self, node: BreakNode):
        """Visit break statement"""
        if not self.in_loop:
            self.add_error(
                "Break statement outside loop or switch",
                node.line, node.col
            )

    def visit_continue(self, node: ContinueNode):
        """Visit continue statement"""
        if not self.in_loop:
            self.add_error(
                "Continue statement outside loop",
                node.line, node.col
            )

    def visit_return(self, node: ReturnNode):
        """Visit return statement"""
        if not self.current_function_return_type:
            self.add_error(
                "Return statement outside function",
                node.line, node.col
            )
            return

        if self.current_function_return_type == "field":
            # void function
            if node.value:
                self.add_error(
                    "Cannot return value from field (void) function",
                    node.line, node.col
                )
        else:
            # non-void function
            if not node.value:
                self.add_error(
                    f"Must return {self.current_function_return_type} value",
                    node.line, node.col
                )
                return

            return_type = self.visit_expr(node.value)
            if return_type and not self.can_assign(self.current_function_return_type, return_type):
                self.add_error(
                    f"Return type mismatch: expected {self.current_function_return_type}, got {return_type}",
                    node.line, node.col
                )

    def visit_io(self, node: IONode):
        """Visit I/O statement (view/write)"""
        # Check format string is wall (string)
        # Check arguments match format specs (simplified - just check they're valid expressions)
        for arg in node.args:
            self.visit_expr(arg)

    # ========================================================================
    # Expression Visitors (return type string)
    # ========================================================================

    def visit_expr(self, node: ExprNode) -> Optional[str]:
        """Visit expression and return its type"""
        if isinstance(node, BinaryOpNode):
            return self.visit_binary_op(node)
        elif isinstance(node, UnaryOpNode):
            return self.visit_unary_op(node)
        elif isinstance(node, LiteralNode):
            return node.literal_type
        elif isinstance(node, IdNode):
            return self.visit_id(node)
        elif isinstance(node, ArrayAccessNode):
            return self.visit_array_access(node)
        elif isinstance(node, StructAccessNode):
            return self.visit_struct_access(node)
        elif isinstance(node, FunctionCallNode):
            return self.visit_function_call(node)
        elif isinstance(node, WallConcatNode):
            return self.visit_wall_concat(node)
        return None

    def visit_binary_op(self, node: BinaryOpNode) -> Optional[str]:
        """Visit binary operation and return result type"""
        left_type = self.visit_expr(node.left)
        right_type = self.visit_expr(node.right)

        if not left_type or not right_type:
            return None

        return self.check_binary_op(left_type, node.operator, right_type, node.line, node.col)

    def check_binary_op(self, left: str, op: str, right: str, line: int, col: int) -> Optional[str]:
        """Check binary operation and return result type with type coercion"""
        # Arithmetic: +, -, *, /, %
        if op in ('+', '-', '*', '/', '%'):
            # Special case: wall + wall = wall (concatenation)
            if op == '+' and left == 'wall' and right == 'wall':
                return 'wall'

            # wall cannot be used in arithmetic (no implicit casting)
            if left == 'wall' or right == 'wall':
                self.add_error(
                    f"Cannot use wall (string) in arithmetic operation",
                    line, col
                )
                return None

            # Both must be numeric
            if left not in ('tile', 'glass', 'brick') or right not in ('tile', 'glass', 'brick'):
                self.add_error(
                    f"Operator '{op}' requires numeric operands, got {left} and {right}",
                    line, col
                )
                return None

            # Type coercion: tile < glass < brick
            # Result is the wider type
            hierarchy = {'tile': 0, 'glass': 1, 'brick': 2}
            if hierarchy[left] >= hierarchy[right]:
                return left
            return right

        # Relational: <, <=, >, >=
        elif op in ('<', '<=', '>', '>='):
            # wall cannot be compared
            if left == 'wall' or right == 'wall':
                self.add_error(
                    f"Cannot compare wall (string) types",
                    line, col
                )
                return None

            # Both must be numeric
            if left not in ('tile', 'glass', 'brick') or right not in ('tile', 'glass', 'brick'):
                self.add_error(
                    f"Relational operator '{op}' requires numeric operands",
                    line, col
                )
                return None

            return 'beam'  # Result is boolean

        # Equality: ==, !=
        elif op in ('==', '!='):
            # Types must be compatible
            if not self.types_compatible(left, right):
                self.add_error(
                    f"Cannot compare {left} and {right}",
                    line, col
                )
                return None
            return 'beam'

        # Logical: &&, ||
        elif op in ('&&', '||'):
            if left != 'beam' or right != 'beam':
                self.add_error(
                    f"Logical operator '{op}' requires beam (boolean) operands",
                    line, col
                )
                return None
            return 'beam'

        return None

    def visit_unary_op(self, node: UnaryOpNode) -> Optional[str]:
        """Visit unary operation and return result type"""
        operand_type = self.visit_expr(node.operand)
        if not operand_type:
            return None

        # Negation: -
        if node.operator == '-':
            if operand_type not in ('tile', 'glass', 'brick'):
                self.add_error(
                    f"Unary minus requires numeric operand, got {operand_type}",
                    node.line, node.col
                )
                return None
            return operand_type

        # Logical not: !
        elif node.operator == '!':
            if operand_type != 'beam':
                self.add_error(
                    f"Logical not requires beam (boolean) operand, got {operand_type}",
                    node.line, node.col
                )
                return None
            return 'beam'

        # Increment/decrement: ++, --
        elif node.operator in ('++', '--'):
            if operand_type not in ('tile', 'glass', 'brick'):
                self.add_error(
                    f"Increment/decrement requires numeric operand, got {operand_type}",
                    node.line, node.col
                )
                return None
            return operand_type

        return None

    def visit_id(self, node: IdNode) -> Optional[str]:
        """Visit identifier and return its type"""
        symbol = self.symbol_table.lookup(node.name)
        if not symbol:
            self.add_error(
                f"Undeclared variable '{node.name}'",
                node.line, node.col
            )
            return None
        return symbol.type

    def visit_array_access(self, node: ArrayAccessNode) -> Optional[str]:
        """Visit array access and return element type"""
        array_type = self.visit_expr(node.array)
        if not array_type:
            return None

        # Check each index is tile (integer)
        for idx_expr in node.indices:
            idx_type = self.visit_expr(idx_expr)
            if idx_type and idx_type != 'tile':
                self.add_error(
                    f"Array index must be tile (integer), got {idx_type}",
                    node.line, node.col
                )

        # Return element type (same as array base type)
        return array_type

    def visit_struct_access(self, node: StructAccessNode) -> Optional[str]:
        """Visit struct member access and return member type"""
        struct_type = self.visit_expr(node.struct)
        if not struct_type:
            return None

        # Get struct definition
        if isinstance(node.struct, IdNode):
            symbol = self.symbol_table.lookup(node.struct.name)
            if symbol and symbol.struct_name:
                struct_def = self.symbol_table.get_struct(symbol.struct_name)
                if struct_def and struct_def.members:
                    member = struct_def.members.get(node.member)
                    if not member:
                        self.add_error(
                            f"Struct has no member '{node.member}'",
                            node.line, node.col
                        )
                        return None
                    return member.type

        return None

    def visit_function_call(self, node: FunctionCallNode) -> Optional[str]:
        """Visit function call and return return type"""
        func_symbol = self.symbol_table.get_function(node.func_name)
        if not func_symbol:
            self.add_error(
                f"Undefined function '{node.func_name}'",
                node.line, node.col
            )
            return None

        # Check argument count and types (simplified for built-ins)
        if func_symbol.name not in ('view', 'write'):
            if len(node.args) != len(func_symbol.params):
                self.add_error(
                    f"Function '{node.func_name}' expects {len(func_symbol.params)} arguments, got {len(node.args)}",
                    node.line, node.col
                )
                return func_symbol.return_type

            # Check argument types
            for i, (arg_expr, param) in enumerate(zip(node.args, func_symbol.params)):
                arg_type = self.visit_expr(arg_expr)
                if arg_type and not self.can_assign(param.type, arg_type):
                    self.add_error(
                        f"Argument {i + 1} type mismatch: expected {param.type}, got {arg_type}",
                        node.line, node.col
                    )

        return func_symbol.return_type

    def visit_wall_concat(self, node: WallConcatNode) -> str:
        """Visit wall concatenation"""
        for part in node.parts:
            part_type = self.visit_expr(part)
            if part_type and part_type != 'wall':
                self.add_error(
                    f"Cannot concatenate {part_type} to wall (string)",
                    node.line, node.col
                )
        return 'wall'

    # ========================================================================
    # Type Checking Helpers
    # ========================================================================

    def can_assign(self, target_type: str, value_type: str) -> bool:
        """Check if value_type can be assigned to target_type (with coercion)"""
        # Exact match
        if target_type == value_type:
            return True

        # wall (string) has NO implicit casting
        if target_type == 'wall' or value_type == 'wall':
            return False

        # Numeric type hierarchy: tile → glass → brick
        # Can assign narrower to wider type
        numeric_hierarchy = {'tile': 0, 'glass': 1, 'brick': 2}

        if target_type in numeric_hierarchy and value_type in numeric_hierarchy:
            return numeric_hierarchy[value_type] <= numeric_hierarchy[target_type]

        # beam (bool) can only be beam
        if target_type == 'beam' or value_type == 'beam':
            return False

        return False

    def types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two types can be compared for equality"""
        if type1 == type2:
            return True

        # Numeric types can be compared
        if type1 in ('tile', 'glass', 'brick') and type2 in ('tile', 'glass', 'brick'):
            return True

        return False