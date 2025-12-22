"""Monomorphization for compile-time parameters

This module handles generating specialized versions of generic functions
and types for each unique combination of compile-time parameters.
"""

from typing import Dict, Tuple, List, Any, Set, Optional
from .. import ast
from copy import deepcopy


class MonomorphizationContext:
    """Context for tracking monomorphized functions"""
    
    def __init__(self):
        # Map from (function_name, compile_time_args_tuple) -> specialized_function
        self.specialized_functions: Dict[Tuple[str, Tuple], ast.FunctionDef] = {}
        
        # Map from (struct_name, compile_time_args_tuple) -> specialized_struct
        self.specialized_structs: Dict[Tuple[str, Tuple], ast.StructDef] = {}
        
        # Track which specializations are needed
        self.pending_specializations: List[Tuple[str, Tuple]] = []
        
        # Original function definitions (before specialization)
        self.original_functions: Dict[str, ast.FunctionDef] = {}
    
    def get_specialized_function_name(self, base_name: str, compile_time_args: Tuple) -> str:
        """Generate a unique name for a specialized function"""
        if not compile_time_args:
            return base_name
        
        # Create mangled name: process_256_true for process[256, true]
        arg_strs = []
        for arg in compile_time_args:
            if isinstance(arg, bool):
                arg_strs.append("true" if arg else "false")
            elif isinstance(arg, int):
                # Use positive/negative indicator for clarity
                arg_strs.append(str(arg).replace('-', 'neg'))
            else:
                arg_strs.append(str(arg))
        
        return f"{base_name}_{'_'.join(arg_strs)}"
    
    def needs_specialization(self, func: ast.FunctionDef) -> bool:
        """Check if a function needs specialization"""
        return len(func.compile_time_params) > 0
    
    def register_original_function(self, func: ast.FunctionDef):
        """Store original function definition for specialization"""
        if func.name not in self.original_functions:
            self.original_functions[func.name] = func
    
    def specialize_function(
        self, 
        func: ast.FunctionDef, 
        compile_time_args: Tuple[Any, ...]
    ) -> ast.FunctionDef:
        """
        Create a specialized version of a function with concrete compile-time arguments.
        
        Example:
            process[N: int](data: &[u8]) with N=256
            -> process_256(data: &[u8])
        """
        # Check if already specialized
        key = (func.name, compile_time_args)
        if key in self.specialized_functions:
            return self.specialized_functions[key]
        
        # Create a deep copy of the function
        specialized = deepcopy(func)
        
        # Create substitution map: param_name -> concrete_value
        substitutions = {}
        for param, arg in zip(func.compile_time_params, compile_time_args):
            substitutions[param.name] = arg
        
        # Generate specialized name
        specialized.name = self.get_specialized_function_name(func.name, compile_time_args)
        
        # Clear compile-time params (they're now constants)
        specialized.compile_time_params = []
        
        # Substitute compile-time parameters in the function body
        specialized.body = self._substitute_in_block(specialized.body, substitutions)
        
        # Substitute in return type if needed
        if specialized.return_type:
            specialized.return_type = self._substitute_in_type(specialized.return_type, substitutions)
        
        # Substitute in parameter types
        for param in specialized.params:
            param.type_annotation = self._substitute_in_type(param.type_annotation, substitutions)
        
        # Cache the specialization
        self.specialized_functions[key] = specialized
        
        return specialized
    
    def _substitute_in_block(self, block: ast.Block, substitutions: Dict[str, Any]) -> ast.Block:
        """Substitute compile-time parameters in a block"""
        new_statements = []
        for stmt in block.statements:
            new_stmt = self._substitute_in_statement(stmt, substitutions)
            new_statements.append(new_stmt)
        
        block.statements = new_statements
        return block
    
    def _substitute_in_statement(self, stmt: ast.Statement, substitutions: Dict[str, Any]) -> ast.Statement:
        """Substitute compile-time parameters in a statement"""
        if isinstance(stmt, ast.VarDecl):
            stmt.initializer = self._substitute_in_expression(stmt.initializer, substitutions)
            if stmt.type_annotation:
                stmt.type_annotation = self._substitute_in_type(stmt.type_annotation, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.Assignment):
            stmt.target = self._substitute_in_expression(stmt.target, substitutions)
            stmt.value = self._substitute_in_expression(stmt.value, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                stmt.value = self._substitute_in_expression(stmt.value, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.IfStmt):
            stmt.condition = self._substitute_in_expression(stmt.condition, substitutions)
            stmt.then_block = self._substitute_in_block(stmt.then_block, substitutions)
            if stmt.elif_clauses:
                new_elif_clauses = []
                for cond, block in stmt.elif_clauses:
                    new_cond = self._substitute_in_expression(cond, substitutions)
                    new_block = self._substitute_in_block(block, substitutions)
                    new_elif_clauses.append((new_cond, new_block))
                stmt.elif_clauses = new_elif_clauses
            if stmt.else_block:
                stmt.else_block = self._substitute_in_block(stmt.else_block, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.WhileStmt):
            stmt.condition = self._substitute_in_expression(stmt.condition, substitutions)
            stmt.body = self._substitute_in_block(stmt.body, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.ForStmt):
            stmt.iterable = self._substitute_in_expression(stmt.iterable, substitutions)
            stmt.body = self._substitute_in_block(stmt.body, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.ExpressionStmt):
            stmt.expression = self._substitute_in_expression(stmt.expression, substitutions)
            return stmt
        
        elif isinstance(stmt, ast.DeferStmt):
            stmt.body = self._substitute_in_block(stmt.body, substitutions)
            return stmt
        
        # Other statement types pass through unchanged
        return stmt
    
    def _substitute_in_expression(self, expr: ast.Expression, substitutions: Dict[str, Any]) -> ast.Expression:
        """Substitute compile-time parameters in an expression"""
        
        # Identifier - replace with literal if it's a compile-time param
        if isinstance(expr, ast.Identifier):
            if expr.name in substitutions:
                value = substitutions[expr.name]
                if isinstance(value, bool):
                    return ast.BoolLiteral(value=value, span=expr.span)
                elif isinstance(value, int):
                    return ast.IntLiteral(value=value, span=expr.span)
            return expr
        
        # Binary operations - substitute both sides
        elif isinstance(expr, ast.BinOp):
            expr.left = self._substitute_in_expression(expr.left, substitutions)
            expr.right = self._substitute_in_expression(expr.right, substitutions)
            # Try to evaluate if both sides are now literals
            return self._try_const_fold(expr)
        
        # Unary operations - substitute operand
        elif isinstance(expr, ast.UnaryOp):
            expr.operand = self._substitute_in_expression(expr.operand, substitutions)
            return expr
        
        # Function calls - substitute arguments and compile-time args
        elif isinstance(expr, ast.FunctionCall):
            expr.function = self._substitute_in_expression(expr.function, substitutions)
            expr.arguments = [self._substitute_in_expression(arg, substitutions) for arg in expr.arguments]
            if expr.compile_time_args:
                expr.compile_time_args = [
                    self._substitute_in_expression(arg, substitutions) 
                    for arg in expr.compile_time_args
                ]
            return expr
        
        # Method calls - substitute object and arguments
        elif isinstance(expr, ast.MethodCall):
            expr.object = self._substitute_in_expression(expr.object, substitutions)
            expr.arguments = [self._substitute_in_expression(arg, substitutions) for arg in expr.arguments]
            return expr
        
        # Field access - substitute object
        elif isinstance(expr, ast.FieldAccess):
            expr.object = self._substitute_in_expression(expr.object, substitutions)
            return expr
        
        # Index access - substitute object and index
        elif isinstance(expr, ast.IndexAccess):
            expr.object = self._substitute_in_expression(expr.object, substitutions)
            expr.index = self._substitute_in_expression(expr.index, substitutions)
            return expr
        
        # Slice access - substitute object, start, and end
        elif isinstance(expr, ast.SliceAccess):
            expr.object = self._substitute_in_expression(expr.object, substitutions)
            if expr.start:
                expr.start = self._substitute_in_expression(expr.start, substitutions)
            if expr.end:
                expr.end = self._substitute_in_expression(expr.end, substitutions)
            return expr
        
        # List literal - substitute elements
        elif isinstance(expr, ast.ListLiteral):
            expr.elements = [self._substitute_in_expression(elem, substitutions) for elem in expr.elements]
            return expr
        
        # Struct literal - substitute field values
        elif isinstance(expr, ast.StructLiteral):
            new_fields = []
            for field_name, field_value in expr.fields:
                new_value = self._substitute_in_expression(field_value, substitutions)
                new_fields.append((field_name, new_value))
            expr.fields = new_fields
            return expr
        
        # Try expression - substitute inner expression
        elif isinstance(expr, ast.TryExpr):
            expr.expression = self._substitute_in_expression(expr.expression, substitutions)
            return expr
        
        # Ternary expression - substitute all parts
        elif isinstance(expr, ast.TernaryExpr):
            expr.true_expr = self._substitute_in_expression(expr.true_expr, substitutions)
            expr.condition = self._substitute_in_expression(expr.condition, substitutions)
            expr.false_expr = self._substitute_in_expression(expr.false_expr, substitutions)
            return expr
        
        # Literals and other leaf nodes pass through unchanged
        return expr
    
    def _substitute_in_type(self, type_node: ast.Type, substitutions: Dict[str, Any]) -> ast.Type:
        """Substitute compile-time parameters in type annotations"""
        
        # Array type with size expression: [T; N] where N might be a compile-time param
        if isinstance(type_node, ast.ArrayType):
            if type_node.size:
                type_node.size = self._substitute_in_expression(type_node.size, substitutions)
            if type_node.element_type:
                type_node.element_type = self._substitute_in_type(type_node.element_type, substitutions)
            return type_node
        
        # PrimitiveType, ReferenceType, etc. - check if they contain compile-time params
        # For now, these pass through unchanged (compile-time params in types are rare)
        # TODO: Handle compile-time params in type annotations if needed
        
        # Generic type with arguments: List[T] or Matrix[Rows, Cols]
        elif isinstance(type_node, ast.GenericType):
            if type_node.type_args:
                type_node.type_args = [
                    self._substitute_in_type(arg, substitutions) if isinstance(arg, ast.Type)
                    else self._substitute_in_expression(arg, substitutions)
                    for arg in type_node.type_args
                ]
            return type_node
        
        # Other types pass through unchanged
        return type_node
    
    def _try_const_fold(self, expr: ast.BinOp) -> ast.Expression:
        """Try to evaluate binary operations at compile time"""
        # Only fold if both operands are literals
        if isinstance(expr.left, ast.IntLiteral) and isinstance(expr.right, ast.IntLiteral):
            left_val = expr.left.value
            right_val = expr.right.value
            
            # Evaluate based on operator
            if expr.op == '+':
                return ast.IntLiteral(value=left_val + right_val, span=expr.span)
            elif expr.op == '-':
                return ast.IntLiteral(value=left_val - right_val, span=expr.span)
            elif expr.op == '*':
                return ast.IntLiteral(value=left_val * right_val, span=expr.span)
            elif expr.op == '/':
                if right_val != 0:
                    return ast.IntLiteral(value=left_val // right_val, span=expr.span)
            elif expr.op == '%':
                if right_val != 0:
                    return ast.IntLiteral(value=left_val % right_val, span=expr.span)
        
        # Boolean operations
        elif isinstance(expr.left, ast.BoolLiteral) and isinstance(expr.right, ast.BoolLiteral):
            left_val = expr.left.value
            right_val = expr.right.value
            
            if expr.op == 'and':
                return ast.BoolLiteral(value=left_val and right_val, span=expr.span)
            elif expr.op == 'or':
                return ast.BoolLiteral(value=left_val or right_val, span=expr.span)
        
        # Can't fold, return original
        return expr


def monomorphize_program(program: ast.Program) -> ast.Program:
    """
    Monomorphize a program by generating specialized versions of functions
    with compile-time parameters.
    
    Algorithm:
    1. Find all functions with compile-time parameters
    2. Scan program for all function calls with compile-time arguments
    3. Generate specialized versions for each unique argument combination
    4. Replace call sites with specialized function names
    5. Add specialized functions to program
    """
    context = MonomorphizationContext()
    
    # Step 1: Register all functions with compile-time parameters
    for item in program.items:
        if isinstance(item, ast.FunctionDef) and context.needs_specialization(item):
            context.register_original_function(item)
    
    # Step 2: Collect all needed specializations by scanning call sites
    call_sites = _collect_function_calls(program)
    needed_specializations: Dict[str, Set[Tuple]] = {}
    
    for call in call_sites:
        if call.compile_time_args:
            func_name = _get_function_name_from_call(call)
            if func_name:
                compile_time_args = extract_compile_time_args(call)
                if func_name not in needed_specializations:
                    needed_specializations[func_name] = set()
                needed_specializations[func_name].add(compile_time_args)
    
    # Step 3: Generate specialized functions
    specialized_funcs = []
    for func_name, arg_sets in needed_specializations.items():
        if func_name in context.original_functions:
            original_func = context.original_functions[func_name]
            for compile_time_args in arg_sets:
                specialized = context.specialize_function(original_func, compile_time_args)
                specialized_funcs.append(specialized)
    
    # Step 4: Update call sites to use specialized names
    _update_call_sites(program, context)
    
    # Step 5: Add specialized functions to program (and remove originals with compile-time params)
    new_items = []
    for item in program.items:
        # Keep functions without compile-time params
        if isinstance(item, ast.FunctionDef):
            if not context.needs_specialization(item):
                new_items.append(item)
            # Skip originals with compile-time params (replaced by specializations)
        else:
            # Keep all non-function items
            new_items.append(item)
    
    # Add all specialized functions
    new_items.extend(specialized_funcs)
    program.items = new_items
    
    return program


def _collect_function_calls(node: Any) -> List[ast.FunctionCall]:
    """Recursively collect all function calls in the AST"""
    calls = []
    
    if isinstance(node, ast.FunctionCall):
        calls.append(node)
    
    # Recursively search in all child nodes
    if isinstance(node, ast.Program):
        for item in node.items:
            calls.extend(_collect_function_calls(item))
    
    elif isinstance(node, ast.FunctionDef):
        calls.extend(_collect_function_calls(node.body))
    
    elif isinstance(node, ast.Block):
        for stmt in node.statements:
            calls.extend(_collect_function_calls(stmt))
    
    elif isinstance(node, ast.VarDecl):
        calls.extend(_collect_function_calls(node.initializer))
    
    elif isinstance(node, ast.Assignment):
        calls.extend(_collect_function_calls(node.target))
        calls.extend(_collect_function_calls(node.value))
    
    elif isinstance(node, ast.ReturnStmt):
        if node.value:
            calls.extend(_collect_function_calls(node.value))
    
    elif isinstance(node, ast.IfStmt):
        calls.extend(_collect_function_calls(node.condition))
        calls.extend(_collect_function_calls(node.then_block))
        if node.elif_clauses:
            for cond, block in node.elif_clauses:
                calls.extend(_collect_function_calls(cond))
                calls.extend(_collect_function_calls(block))
        if node.else_block:
            calls.extend(_collect_function_calls(node.else_block))
    
    elif isinstance(node, ast.WhileStmt):
        calls.extend(_collect_function_calls(node.condition))
        calls.extend(_collect_function_calls(node.body))
    
    elif isinstance(node, ast.ForStmt):
        calls.extend(_collect_function_calls(node.iterable))
        calls.extend(_collect_function_calls(node.body))
    
    elif isinstance(node, ast.ExpressionStmt):
        calls.extend(_collect_function_calls(node.expression))
    
    elif isinstance(node, ast.DeferStmt):
        calls.extend(_collect_function_calls(node.body))
    
    elif isinstance(node, ast.BinOp):
        calls.extend(_collect_function_calls(node.left))
        calls.extend(_collect_function_calls(node.right))
    
    elif isinstance(node, ast.UnaryOp):
        calls.extend(_collect_function_calls(node.operand))
    
    elif isinstance(node, ast.MethodCall):
        calls.extend(_collect_function_calls(node.object))
        for arg in node.arguments:
            calls.extend(_collect_function_calls(arg))
    
    elif isinstance(node, ast.IndexAccess):
        calls.extend(_collect_function_calls(node.object))
        calls.extend(_collect_function_calls(node.index))
    
    elif isinstance(node, ast.FieldAccess):
        calls.extend(_collect_function_calls(node.object))
    
    elif isinstance(node, ast.ListLiteral):
        for elem in node.elements:
            calls.extend(_collect_function_calls(elem))
    
    elif isinstance(node, ast.StructLiteral):
        for field_name, field_expr in node.fields:
            calls.extend(_collect_function_calls(field_expr))
    
    elif isinstance(node, ast.MatchStmt):
        calls.extend(_collect_function_calls(node.scrutinee))
        for arm in node.arms:
            if arm.guard:
                calls.extend(_collect_function_calls(arm.guard))
            calls.extend(_collect_function_calls(arm.body))
    
    elif isinstance(node, ast.WithStmt):
        calls.extend(_collect_function_calls(node.value))
        calls.extend(_collect_function_calls(node.body))
    
    elif isinstance(node, ast.SliceAccess):
        calls.extend(_collect_function_calls(node.object))
        if node.start:
            calls.extend(_collect_function_calls(node.start))
        if node.end:
            calls.extend(_collect_function_calls(node.end))
    
    elif isinstance(node, ast.TryExpr):
        calls.extend(_collect_function_calls(node.expression))
    
    elif isinstance(node, ast.TernaryExpr):
        calls.extend(_collect_function_calls(node.true_expr))
        calls.extend(_collect_function_calls(node.condition))
        calls.extend(_collect_function_calls(node.false_expr))
    
    return calls


def _get_function_name_from_call(call: ast.FunctionCall) -> Optional[str]:
    """Extract function name from a call expression"""
    if isinstance(call.function, ast.Identifier):
        return call.function.name
    # TODO: Handle method calls, field access, etc.
    return None


def _update_call_sites(node: Any, context: MonomorphizationContext):
    """Update all call sites to use specialized function names"""
    
    if isinstance(node, ast.FunctionCall):
        if node.compile_time_args:
            func_name = _get_function_name_from_call(node)
            if func_name and func_name in context.original_functions:
                compile_time_args = extract_compile_time_args(node)
                specialized_name = context.get_specialized_function_name(func_name, compile_time_args)
                
                # Update the function name
                if isinstance(node.function, ast.Identifier):
                    node.function.name = specialized_name
                
                # Clear compile-time args (they're now baked into the name)
                node.compile_time_args = []
    
    # Recursively update in all child nodes
    if isinstance(node, ast.Program):
        for item in node.items:
            _update_call_sites(item, context)
    
    elif isinstance(node, ast.FunctionDef):
        _update_call_sites(node.body, context)
    
    elif isinstance(node, ast.Block):
        for stmt in node.statements:
            _update_call_sites(stmt, context)
    
    elif isinstance(node, ast.VarDecl):
        _update_call_sites(node.initializer, context)
    
    elif isinstance(node, ast.Assignment):
        _update_call_sites(node.target, context)
        _update_call_sites(node.value, context)
    
    elif isinstance(node, ast.ReturnStmt):
        if node.value:
            _update_call_sites(node.value, context)
    
    elif isinstance(node, ast.IfStmt):
        _update_call_sites(node.condition, context)
        _update_call_sites(node.then_block, context)
        if node.elif_clauses:
            for cond, block in node.elif_clauses:
                _update_call_sites(cond, context)
                _update_call_sites(block, context)
        if node.else_block:
            _update_call_sites(node.else_block, context)
    
    elif isinstance(node, ast.WhileStmt):
        _update_call_sites(node.condition, context)
        _update_call_sites(node.body, context)
    
    elif isinstance(node, ast.ForStmt):
        _update_call_sites(node.iterable, context)
        _update_call_sites(node.body, context)
    
    elif isinstance(node, ast.ExpressionStmt):
        _update_call_sites(node.expression, context)
    
    elif isinstance(node, ast.DeferStmt):
        _update_call_sites(node.body, context)
    
    elif isinstance(node, ast.BinOp):
        _update_call_sites(node.left, context)
        _update_call_sites(node.right, context)
    
    elif isinstance(node, ast.UnaryOp):
        _update_call_sites(node.operand, context)
    
    elif isinstance(node, ast.MethodCall):
        _update_call_sites(node.object, context)
        for arg in node.arguments:
            _update_call_sites(arg, context)
    
    elif isinstance(node, ast.IndexAccess):
        _update_call_sites(node.object, context)
        _update_call_sites(node.index, context)
    
    elif isinstance(node, ast.FieldAccess):
        _update_call_sites(node.object, context)
    
    elif isinstance(node, ast.ListLiteral):
        for elem in node.elements:
            _update_call_sites(elem, context)
    
    elif isinstance(node, ast.StructLiteral):
        for field_name, field_expr in node.fields:
            _update_call_sites(field_expr, context)
    
    elif isinstance(node, ast.MatchStmt):
        _update_call_sites(node.scrutinee, context)
        for arm in node.arms:
            if arm.guard:
                _update_call_sites(arm.guard, context)
            _update_call_sites(arm.body, context)
    
    elif isinstance(node, ast.WithStmt):
        _update_call_sites(node.value, context)
        _update_call_sites(node.body, context)
    
    elif isinstance(node, ast.SliceAccess):
        _update_call_sites(node.object, context)
        if node.start:
            _update_call_sites(node.start, context)
        if node.end:
            _update_call_sites(node.end, context)
    
    elif isinstance(node, ast.TryExpr):
        _update_call_sites(node.expression, context)
    
    elif isinstance(node, ast.TernaryExpr):
        _update_call_sites(node.true_expr, context)
        _update_call_sites(node.condition, context)
        _update_call_sites(node.false_expr, context)


def extract_compile_time_args(call: ast.FunctionCall) -> Tuple[Any, ...]:
    """
    Extract concrete compile-time argument values from a function call.
    
    Example:
        create_buffer[256]() -> (256,)
        process[256, true](data) -> (256, True)
    """
    args = []
    for arg_expr in call.compile_time_args:
        if isinstance(arg_expr, ast.IntLiteral):
            args.append(arg_expr.value)
        elif isinstance(arg_expr, ast.BoolLiteral):
            args.append(arg_expr.value)
        else:
            # For now, only support literal compile-time args
            # Full implementation would support const expressions
            raise ValueError(f"Compile-time arguments must be literals, got {type(arg_expr)}")
    
    return tuple(args)

