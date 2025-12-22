"""Parameter closure inlining for Pyrite

Parameter closures (fn[...]) are compile-time only and must be inlined
at call sites. This module provides utilities for inlining closure bodies.
"""

from typing import Dict, List, Optional
from .. import ast
from ..frontend.tokens import Span


class ClosureInliner:
    """Inlines parameter closures at call sites"""
    
    def __init__(self):
        self.inlining_depth = 0
        self.max_inlining_depth = 10  # Prevent infinite recursion
        self.max_inlined_statements = 1000  # Prevent code explosion
    
    def inline_parameter_closure(
        self,
        closure: ast.ParameterClosure,
        arguments: List[ast.Expression],
        span: Optional[Span] = None
    ) -> ast.Block:
        """
        Inline a parameter closure body, substituting parameters with arguments.
        
        Args:
            closure: The parameter closure to inline
            arguments: List of argument expressions to substitute for parameters
            span: Source span for error reporting
        
        Returns:
            Inlined block with parameters substituted
        """
        if self.inlining_depth >= self.max_inlining_depth:
            raise ValueError(
                f"Maximum inlining depth ({self.max_inlining_depth}) exceeded. "
                "Possible recursive closure?"
            )
        
        if len(arguments) != len(closure.params):
            raise ValueError(
                f"Parameter count mismatch: closure has {len(closure.params)} "
                f"parameters but {len(arguments)} arguments provided"
            )
        
        # Create substitution map: parameter name -> argument expression
        substitutions: Dict[str, ast.Expression] = {}
        for param, arg in zip(closure.params, arguments):
            substitutions[param.name] = arg
        
        # Estimate code size to prevent explosion
        estimated_size = self._estimate_block_size(closure.body)
        if estimated_size > self.max_inlined_statements:
            raise ValueError(
                f"Closure body too large ({estimated_size} statements). "
                f"Maximum allowed: {self.max_inlined_statements}. "
                "Consider simplifying the closure or increasing max_inlined_statements."
            )
        
        # Increment depth to prevent recursion
        self.inlining_depth += 1
        try:
            # Clone and substitute the closure body
            inlined_body = self._substitute_in_block(closure.body, substitutions)
            return inlined_body
        finally:
            self.inlining_depth -= 1
    
    def _substitute_in_block(
        self,
        block: ast.Block,
        substitutions: Dict[str, ast.Expression]
    ) -> ast.Block:
        """Substitute parameter references in a block"""
        new_statements = []
        for stmt in block.statements:
            new_stmt = self._substitute_in_statement(stmt, substitutions)
            new_statements.append(new_stmt)
        
        return ast.Block(
            statements=new_statements,
            span=block.span
        )
    
    def _substitute_in_statement(
        self,
        stmt: ast.Statement,
        substitutions: Dict[str, ast.Expression]
    ) -> ast.Statement:
        """Substitute parameter references in a statement"""
        if isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                new_value = self._substitute_in_expression(stmt.value, substitutions)
                return ast.ReturnStmt(value=new_value, span=stmt.span)
            return stmt
        
        elif isinstance(stmt, ast.ExpressionStmt):
            new_expr = self._substitute_in_expression(stmt.expression, substitutions)
            return ast.ExpressionStmt(expression=new_expr, span=stmt.span)
        
        elif isinstance(stmt, ast.VarDecl):
            new_init = self._substitute_in_expression(stmt.initializer, substitutions)
            return ast.VarDecl(
                pattern=stmt.pattern,
                mutable=stmt.mutable,
                type_annotation=stmt.type_annotation,
                initializer=new_init,
                span=stmt.span
            )
        
        elif isinstance(stmt, ast.Assignment):
            new_target = self._substitute_in_expression(stmt.target, substitutions)
            new_value = self._substitute_in_expression(stmt.value, substitutions)
            return ast.Assignment(target=new_target, value=new_value, span=stmt.span)
        
        elif isinstance(stmt, ast.IfStmt):
            new_cond = self._substitute_in_expression(stmt.condition, substitutions)
            new_then = self._substitute_in_block(stmt.then_block, substitutions)
            new_else = None
            if stmt.else_block:
                new_else = self._substitute_in_block(stmt.else_block, substitutions)
            return ast.IfStmt(
                condition=new_cond,
                then_block=new_then,
                elif_clauses=stmt.elif_clauses,  # Preserve elif clauses
                else_block=new_else,
                span=stmt.span
            )
        
        elif isinstance(stmt, ast.WhileStmt):
            new_cond = self._substitute_in_expression(stmt.condition, substitutions)
            new_body = self._substitute_in_block(stmt.body, substitutions)
            return ast.WhileStmt(
                condition=new_cond,
                body=new_body,
                span=stmt.span
            )
        
        elif isinstance(stmt, ast.ForStmt):
            new_iterable = self._substitute_in_expression(stmt.iterable, substitutions)
            new_body = self._substitute_in_block(stmt.body, substitutions)
            return ast.ForStmt(
                variable=stmt.variable,
                iterable=new_iterable,
                body=new_body,
                span=stmt.span
            )
        
        elif isinstance(stmt, ast.MatchStmt):
            new_scrutinee = self._substitute_in_expression(stmt.scrutinee, substitutions)
            new_arms = []
            for arm in stmt.arms:
                new_arm_body = self._substitute_in_block(arm.body, substitutions)
                new_guard = None
                if arm.guard:
                    new_guard = self._substitute_in_expression(arm.guard, substitutions)
                new_arms.append(ast.MatchArm(
                    pattern=arm.pattern,  # Patterns don't need substitution
                    guard=new_guard,
                    body=new_arm_body,
                    span=arm.span
                ))
            return ast.MatchStmt(
                scrutinee=new_scrutinee,
                arms=new_arms,
                span=stmt.span
            )
        
        # For other statement types, return as-is (defer, with, etc. don't need substitution)
        return stmt
    
    def _substitute_in_expression(
        self,
        expr: ast.Expression,
        substitutions: Dict[str, ast.Expression]
    ) -> ast.Expression:
        """Substitute parameter references in an expression"""
        if isinstance(expr, ast.Identifier):
            # Check if this identifier is a parameter we need to substitute
            if expr.name in substitutions:
                # Return the substituted expression (clone it)
                return self._clone_expression(substitutions[expr.name])
            return expr
        
        elif isinstance(expr, ast.BinOp):
            new_left = self._substitute_in_expression(expr.left, substitutions)
            new_right = self._substitute_in_expression(expr.right, substitutions)
            return ast.BinOp(
                op=expr.op,
                left=new_left,
                right=new_right,
                span=expr.span
            )
        
        elif isinstance(expr, ast.UnaryOp):
            new_operand = self._substitute_in_expression(expr.operand, substitutions)
            return ast.UnaryOp(
                op=expr.op,
                operand=new_operand,
                span=expr.span
            )
        
        elif isinstance(expr, ast.FunctionCall):
            new_function = self._substitute_in_expression(expr.function, substitutions)
            new_args = [
                self._substitute_in_expression(arg, substitutions)
                for arg in expr.arguments
            ]
            # Preserve compile_time_args if present
            new_compile_time_args = []
            if expr.compile_time_args:
                for ct_arg in expr.compile_time_args:
                    new_compile_time_args.append(self._substitute_in_expression(ct_arg, substitutions))
            return ast.FunctionCall(
                function=new_function,
                compile_time_args=new_compile_time_args,
                arguments=new_args,
                span=expr.span
            )
        
        elif isinstance(expr, ast.MethodCall):
            new_object = self._substitute_in_expression(expr.object, substitutions)
            new_args = [
                self._substitute_in_expression(arg, substitutions)
                for arg in expr.arguments
            ]
            return ast.MethodCall(
                object=new_object,
                method=expr.method,
                arguments=new_args,
                span=expr.span
            )
        
        elif isinstance(expr, ast.FieldAccess):
            new_object = self._substitute_in_expression(expr.object, substitutions)
            return ast.FieldAccess(
                object=new_object,
                field=expr.field,
                span=expr.span
            )
        
        elif isinstance(expr, ast.IndexAccess):
            new_object = self._substitute_in_expression(expr.object, substitutions)
            new_index = self._substitute_in_expression(expr.index, substitutions)
            return ast.IndexAccess(
                object=new_object,
                index=new_index,
                span=expr.span
            )
        
        elif isinstance(expr, ast.StructLiteral):
            new_fields = [
                (field_name, self._substitute_in_expression(field_expr, substitutions))
                for field_name, field_expr in expr.fields
            ]
            return ast.StructLiteral(
                struct_name=expr.struct_name,
                fields=new_fields,
                span=expr.span
            )
        
        elif isinstance(expr, ast.ListLiteral):
            new_elements = [
                self._substitute_in_expression(elem, substitutions)
                for elem in expr.elements
            ]
            return ast.ListLiteral(
                elements=new_elements,
                span=expr.span
            )
        
        elif isinstance(expr, ast.TryExpr):
            new_expr = self._substitute_in_expression(expr.expression, substitutions)
            return ast.TryExpr(
                expression=new_expr,
                span=expr.span
            )
        
        # For literals and other expressions that don't contain identifiers, return as-is
        return expr
    
    def _clone_expression(self, expr: ast.Expression) -> ast.Expression:
        """Create a shallow clone of an expression"""
        # For now, just return the expression (Python objects are references)
        # In a full implementation, we might want deep cloning
        # But for inlining, sharing is fine since we're not modifying the original
        return expr
    
    def _estimate_block_size(self, block: ast.Block) -> int:
        """Estimate the size of a block in statements (for code explosion prevention)"""
        size = 0
        for stmt in block.statements:
            size += 1
            # Add extra weight for complex statements
            if isinstance(stmt, ast.IfStmt):
                size += self._estimate_block_size(stmt.then_block)
                if stmt.else_block:
                    size += self._estimate_block_size(stmt.else_block)
            elif isinstance(stmt, ast.WhileStmt):
                size += self._estimate_block_size(stmt.body)
            elif isinstance(stmt, ast.ForStmt):
                size += self._estimate_block_size(stmt.body)
            elif isinstance(stmt, ast.MatchStmt):
                for arm in stmt.arms:
                    size += self._estimate_block_size(arm.body)
        return size

