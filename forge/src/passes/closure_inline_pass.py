"""Post-type-check parameter closure inlining pass

This pass runs AFTER type checking and uses type information to inline
parameter closures at their call sites within function bodies.

The key insight: when a function receives a parameter closure as an argument,
and then calls that closure parameter, we need to inline the closure body
at the call site with the actual arguments.
"""

from typing import Dict, List, Optional, Set
from .. import ast
from .closure_inlining import ClosureInliner
from ..types import FunctionType, Type
from ..frontend.tokens import Span


class ClosureInlinePass:
    """AST pass that inlines parameter closures using type information"""
    
    def __init__(self, type_checker):
        """Initialize with type checker for type information"""
        self.inliner = ClosureInliner()
        self.type_checker = type_checker
        # Track parameter closures passed to functions: {func_name: {param_index: ParameterClosure}}
        self.function_closure_args: Dict[str, Dict[int, ast.ParameterClosure]] = {}
        # Track which function parameters are parameter closures: {func_name: {param_name: param_index}}
        self.param_closure_params: Dict[str, Dict[str, int]] = {}
    
    def inline_closures_in_program(self, program: ast.Program) -> ast.Program:
        """Inline all parameter closures in a program"""
        # Step 1: Collect parameter closures passed as function arguments
        self._collect_closure_arguments(program)
        
        # Step 2: Identify which function parameters are parameter closures (using type info)
        self._identify_closure_parameters(program)
        
        # Step 3: Transform function bodies to inline closures at call sites
        self._inline_in_functions(program)
        
        return program
    
    def _collect_closure_arguments(self, program: ast.Program):
        """Collect parameter closures passed as function arguments"""
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                self._collect_in_function(item)
    
    def _collect_in_function(self, func: ast.FunctionDef):
        """Collect parameter closures in a function's body"""
        self._collect_in_block(func.body)
    
    def _collect_in_block(self, block: ast.Block):
        """Collect parameter closures in a block"""
        for stmt in block.statements:
            self._collect_in_statement(stmt)
    
    def _collect_in_statement(self, stmt: ast.Statement):
        """Collect parameter closures in a statement"""
        if isinstance(stmt, ast.ExpressionStmt):
            self._collect_in_expression(stmt.expression)
        elif isinstance(stmt, ast.VarDecl):
            self._collect_in_expression(stmt.initializer)
        elif isinstance(stmt, ast.Assignment):
            self._collect_in_expression(stmt.value)
        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                self._collect_in_expression(stmt.value)
        elif isinstance(stmt, ast.IfStmt):
            self._collect_in_expression(stmt.condition)
            self._collect_in_block(stmt.then_block)
            if stmt.else_block:
                self._collect_in_block(stmt.else_block)
        elif isinstance(stmt, ast.WhileStmt):
            self._collect_in_expression(stmt.condition)
            self._collect_in_block(stmt.body)
        elif isinstance(stmt, ast.ForStmt):
            self._collect_in_expression(stmt.iterable)
            self._collect_in_block(stmt.body)
        elif isinstance(stmt, ast.MatchStmt):
            self._collect_in_expression(stmt.scrutinee)
            for arm in stmt.arms:
                if arm.guard:
                    self._collect_in_expression(arm.guard)
                self._collect_in_block(arm.body)
        elif isinstance(stmt, ast.WithStmt):
            self._collect_in_expression(stmt.value)
            self._collect_in_block(stmt.body)
    
    def _collect_in_expression(self, expr: ast.Expression):
        """Collect parameter closures in an expression"""
        if isinstance(expr, ast.FunctionCall):
            # Check if any arguments are parameter closures
            if isinstance(expr.function, ast.Identifier):
                func_name = expr.function.name
                for i, arg in enumerate(expr.arguments):
                    if isinstance(arg, ast.ParameterClosure):
                        if func_name not in self.function_closure_args:
                            self.function_closure_args[func_name] = {}
                        self.function_closure_args[func_name][i] = arg
            # Recurse into nested expressions
            for arg in expr.arguments:
                self._collect_in_expression(arg)
        elif isinstance(expr, ast.BinOp):
            self._collect_in_expression(expr.left)
            self._collect_in_expression(expr.right)
        elif isinstance(expr, ast.UnaryOp):
            self._collect_in_expression(expr.operand)
        elif isinstance(expr, ast.MethodCall):
            self._collect_in_expression(expr.object)
            for arg in expr.arguments:
                self._collect_in_expression(arg)
        elif isinstance(expr, ast.FieldAccess):
            self._collect_in_expression(expr.object)
        elif isinstance(expr, ast.IndexAccess):
            self._collect_in_expression(expr.object)
            self._collect_in_expression(expr.index)
        elif isinstance(expr, ast.StructLiteral):
            for _, field_expr in expr.fields:
                self._collect_in_expression(field_expr)
        elif isinstance(expr, ast.ListLiteral):
            for elem in expr.elements:
                self._collect_in_expression(elem)
        elif isinstance(expr, ast.TryExpr):
            self._collect_in_expression(expr.expression)
    
    def _identify_closure_parameters(self, program: ast.Program):
        """Identify which function parameters are parameter closures using type information"""
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                func_name = item.name
                closure_params = {}
                
                # Check each parameter's type
                for param_index, param in enumerate(item.params):
                    if param.type_annotation:
                        param_type = self.type_checker.resolve_type(param.type_annotation)
                        # Parameter closures have FunctionType
                        # We need to distinguish them from regular function pointers
                        # For MVP, we'll check if the type is FunctionType
                        # In full implementation, we'd check for fn[...] syntax vs fn(...)
                        if isinstance(param_type, FunctionType):
                            closure_params[param.name] = param_index
                
                if closure_params:
                    self.param_closure_params[func_name] = closure_params
    
    def _inline_in_functions(self, program: ast.Program):
        """Inline parameter closures in function bodies"""
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                # Check if this function has parameter closures passed to it
                if item.name in self.function_closure_args:
                    # Transform the function body to inline closures
                    item.body = self._inline_in_block(item.body, item)
                else:
                    # Still need to inline nested closures
                    item.body = self._inline_in_block(item.body, item)
    
    def _inline_in_block(self, block: ast.Block, func: ast.FunctionDef) -> ast.Block:
        """Inline parameter closures in a block"""
        new_statements = []
        for stmt in block.statements:
            new_stmt = self._inline_in_statement(stmt, func)
            # new_stmt might be a single statement or a list (if inlining produced multiple)
            # For now, we only return single statements, so just append
            new_statements.append(new_stmt)
        return ast.Block(statements=new_statements, span=block.span)
    
    def _inline_in_statement(self, stmt: ast.Statement, func: ast.FunctionDef) -> ast.Statement:
        """Inline parameter closures in a statement"""
        if isinstance(stmt, ast.ExpressionStmt):
            # Check if this expression is a call to a parameter closure parameter
            if isinstance(stmt.expression, ast.FunctionCall):
                call = stmt.expression
                if isinstance(call.function, ast.Identifier):
                    param_name = call.function.name
                    
                    # Check if this parameter is a parameter closure
                    if (func.name in self.param_closure_params and 
                        param_name in self.param_closure_params[func.name]):
                        param_index = self.param_closure_params[func.name][param_name]
                        
                        # Find the closure that was passed to this parameter
                        if (func.name in self.function_closure_args and 
                            param_index in self.function_closure_args[func.name]):
                            closure = self.function_closure_args[func.name][param_index]
                            
                            # Inline the closure body with the actual arguments
                            try:
                                inlined_block = self.inliner.inline_parameter_closure(
                                    closure, 
                                    call.arguments,
                                    call.span
                                )
                                
                                # Handle inlined block
                                # If it's a single return statement, extract the value
                                if len(inlined_block.statements) == 1:
                                    inlined_stmt = inlined_block.statements[0]
                                    if isinstance(inlined_stmt, ast.ReturnStmt) and inlined_stmt.value:
                                        # Return statement with value - create expression statement
                                        return ast.ExpressionStmt(
                                            expression=inlined_stmt.value,
                                            span=stmt.span
                                        )
                                    else:
                                        # Single statement (not return) - return as-is
                                        return inlined_stmt
                                else:
                                    # Multiple statements - for MVP, handle first return if present
                                    # TODO: Handle statement sequences properly (need block-level transformation)
                                    for st in inlined_block.statements:
                                        if isinstance(st, ast.ReturnStmt) and st.value:
                                            return ast.ExpressionStmt(
                                                expression=st.value,
                                                span=stmt.span
                                            )
                                    # No return found, return first statement
                                    return inlined_block.statements[0]
                            except ValueError as e:
                                # Inlining failed - keep original statement
                                # TODO: Report proper error
                                pass
            
            # Not a parameter closure call, process normally
            new_expr = self._inline_in_expression(stmt.expression, func)
            return ast.ExpressionStmt(expression=new_expr, span=stmt.span)
        elif isinstance(stmt, ast.VarDecl):
            new_init = self._inline_in_expression(stmt.initializer, func)
            return ast.VarDecl(
                pattern=stmt.pattern,
                type_annotation=stmt.type_annotation,
                initializer=new_init,
                mutable=stmt.mutable,
                span=stmt.span
            )
        elif isinstance(stmt, ast.Assignment):
            new_target = self._inline_in_expression(stmt.target, func)
            new_value = self._inline_in_expression(stmt.value, func)
            return ast.Assignment(target=new_target, value=new_value, span=stmt.span)
        elif isinstance(stmt, ast.ReturnStmt):
            new_value = None
            if stmt.value:
                new_value = self._inline_in_expression(stmt.value, func)
            return ast.ReturnStmt(value=new_value, span=stmt.span)
        elif isinstance(stmt, ast.IfStmt):
            new_cond = self._inline_in_expression(stmt.condition, func)
            new_then = self._inline_in_block(stmt.then_block, func)
            new_else = None
            if stmt.else_block:
                new_else = self._inline_in_block(stmt.else_block, func)
            return ast.IfStmt(
                condition=new_cond,
                then_block=new_then,
                elif_clauses=stmt.elif_clauses,  # Preserve elif clauses
                else_block=new_else,
                span=stmt.span
            )
        elif isinstance(stmt, ast.WhileStmt):
            new_cond = self._inline_in_expression(stmt.condition, func)
            new_body = self._inline_in_block(stmt.body, func)
            return ast.WhileStmt(
                condition=new_cond,
                body=new_body,
                span=stmt.span
            )
        elif isinstance(stmt, ast.ForStmt):
            new_iterable = self._inline_in_expression(stmt.iterable, func)
            new_body = self._inline_in_block(stmt.body, func)
            return ast.ForStmt(
                variable=stmt.variable,
                iterable=new_iterable,
                body=new_body,
                span=stmt.span
            )
        elif isinstance(stmt, ast.MatchStmt):
            new_scrutinee = self._inline_in_expression(stmt.scrutinee, func)
            new_arms = []
            for arm in stmt.arms:
                new_guard = None
                if arm.guard:
                    new_guard = self._inline_in_expression(arm.guard, func)
                new_body = self._inline_in_block(arm.body, func)
                new_arms.append(ast.MatchArm(
                    pattern=arm.pattern,
                    guard=new_guard,
                    body=new_body,
                    span=arm.span
                ))
            return ast.MatchStmt(
                scrutinee=new_scrutinee,
                arms=new_arms,
                span=stmt.span
            )
        elif isinstance(stmt, ast.WithStmt):
            new_value = self._inline_in_expression(stmt.value, func)
            new_body = self._inline_in_block(stmt.body, func)
            return ast.WithStmt(
                variable=stmt.variable,
                value=new_value,
                body=new_body,
                span=stmt.span
            )
        # For other statement types, return as-is
        return stmt
    
    def _inline_in_expression(self, expr: ast.Expression, func: ast.FunctionDef) -> ast.Expression:
        """Inline parameter closures in an expression"""
        if isinstance(expr, ast.FunctionCall):
            # Check if this is a call to a parameter closure parameter
            if isinstance(expr.function, ast.Identifier):
                param_name = expr.function.name
                
                # Note: Parameter closure calls are handled at the statement level,
                # not here. This is because inlining produces statements, not expressions.
                
                # Check if this function call has parameter closures as arguments
                new_args = []
                for arg in expr.arguments:
                    if isinstance(arg, ast.ParameterClosure):
                        # Keep as-is for now - will be inlined at the receiving function
                        new_args.append(arg)
                    else:
                        new_args.append(self._inline_in_expression(arg, func))
                
                new_function = self._inline_in_expression(expr.function, func)
                # Preserve compile_time_args if present
                new_compile_time_args = []
                if expr.compile_time_args:
                    for ct_arg in expr.compile_time_args:
                        new_compile_time_args.append(self._inline_in_expression(ct_arg, func))
                return ast.FunctionCall(
                    function=new_function,
                    compile_time_args=new_compile_time_args,
                    arguments=new_args,
                    span=expr.span
                )
        
        # For other expression types, recurse
        if isinstance(expr, ast.BinOp):
            new_left = self._inline_in_expression(expr.left, func)
            new_right = self._inline_in_expression(expr.right, func)
            return ast.BinOp(
                op=expr.op,
                left=new_left,
                right=new_right,
                span=expr.span
            )
        elif isinstance(expr, ast.UnaryOp):
            new_operand = self._inline_in_expression(expr.operand, func)
            return ast.UnaryOp(
                op=expr.op,
                operand=new_operand,
                span=expr.span
            )
        elif isinstance(expr, ast.MethodCall):
            new_object = self._inline_in_expression(expr.object, func)
            new_args = [self._inline_in_expression(arg, func) for arg in expr.arguments]
            return ast.MethodCall(
                object=new_object,
                method=expr.method,
                arguments=new_args,
                span=expr.span
            )
        elif isinstance(expr, ast.FieldAccess):
            new_object = self._inline_in_expression(expr.object, func)
            return ast.FieldAccess(
                object=new_object,
                field=expr.field,
                span=expr.span
            )
        elif isinstance(expr, ast.IndexAccess):
            new_object = self._inline_in_expression(expr.object, func)
            new_index = self._inline_in_expression(expr.index, func)
            return ast.IndexAccess(
                object=new_object,
                index=new_index,
                span=expr.span
            )
        elif isinstance(expr, ast.StructLiteral):
            new_fields = [
                (field_name, self._inline_in_expression(field_expr, func))
                for field_name, field_expr in expr.fields
            ]
            return ast.StructLiteral(
                struct_name=expr.struct_name,
                fields=new_fields,
                span=expr.span
            )
        elif isinstance(expr, ast.ListLiteral):
            new_elements = [
                self._inline_in_expression(elem, func)
                for elem in expr.elements
            ]
            return ast.ListLiteral(
                elements=new_elements,
                span=expr.span
            )
        elif isinstance(expr, ast.TryExpr):
            new_expr = self._inline_in_expression(expr.expression, func)
            return ast.TryExpr(
                expression=new_expr,
                span=expr.span
            )
        # For other expressions (literals, identifiers), return as-is
        return expr

