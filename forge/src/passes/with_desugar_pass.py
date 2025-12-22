"""AST desugaring pass for with statements

This pass transforms with statements into let + defer at the AST level.
This allows the rest of the compiler (type checker, ownership, etc.) to
see the desugared form.

Transformation:
    with resource = try expression:
        body
    
Becomes:
    let resource = try expression
    defer:
        resource.close()
    body
"""

from typing import List
from .. import ast
from ..frontend.tokens import Span


class WithDesugarPass:
    """AST pass that desugars with statements to let + defer"""
    
    def desugar_program(self, program: ast.Program) -> ast.Program:
        """Desugar all with statements in a program"""
        new_items = []
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                new_item = self._desugar_function(item)
                new_items.append(new_item)
            else:
                new_items.append(item)
        
        return ast.Program(
            imports=program.imports,
            items=new_items,
            span=program.span
        )
    
    def _desugar_function(self, func: ast.FunctionDef) -> ast.FunctionDef:
        """Desugar with statements in a function"""
        new_body = self._desugar_block(func.body)
        return ast.FunctionDef(
            name=func.name,
            generic_params=func.generic_params,
            compile_time_params=func.compile_time_params,
            params=func.params,
            return_type=func.return_type,
            body=new_body,
            is_unsafe=func.is_unsafe,
            is_extern=func.is_extern,
            extern_abi=func.extern_abi,
            span=func.span
        )
    
    def _desugar_block(self, block: ast.Block) -> ast.Block:
        """Desugar with statements in a block"""
        new_statements = []
        for stmt in block.statements:
            if isinstance(stmt, ast.WithStmt):
                # Desugar: with resource = try expr: body
                # Into: let resource = try expr; defer: resource.close(); body
                desugared = self._desugar_with(stmt)
                new_statements.extend(desugared)
            else:
                # Recurse into other statements that may contain blocks
                new_stmt = self._desugar_statement(stmt)
                new_statements.append(new_stmt)
        
        return ast.Block(statements=new_statements, span=block.span)
    
    def _desugar_statement(self, stmt: ast.Statement) -> ast.Statement:
        """Desugar with statements in nested structures"""
        if isinstance(stmt, ast.IfStmt):
            new_then = self._desugar_block(stmt.then_block)
            new_elif = [(cond, self._desugar_block(block)) for cond, block in stmt.elif_clauses]
            new_else = None
            if stmt.else_block:
                new_else = self._desugar_block(stmt.else_block)
            return ast.IfStmt(
                condition=stmt.condition,
                then_block=new_then,
                elif_clauses=new_elif,
                else_block=new_else,
                span=stmt.span
            )
        elif isinstance(stmt, ast.WhileStmt):
            new_body = self._desugar_block(stmt.body)
            return ast.WhileStmt(
                condition=stmt.condition,
                body=new_body,
                span=stmt.span
            )
        elif isinstance(stmt, ast.ForStmt):
            new_body = self._desugar_block(stmt.body)
            return ast.ForStmt(
                variable=stmt.variable,
                iterable=stmt.iterable,
                body=new_body,
                span=stmt.span
            )
        elif isinstance(stmt, ast.MatchStmt):
            new_arms = []
            for arm in stmt.arms:
                new_body = self._desugar_block(arm.body)
                new_arms.append(ast.MatchArm(
                    pattern=arm.pattern,
                    guard=arm.guard,
                    body=new_body,
                    span=arm.span
                ))
            return ast.MatchStmt(
                scrutinee=stmt.scrutinee,
                arms=new_arms,
                span=stmt.span
            )
        elif isinstance(stmt, ast.UnsafeBlock):
            new_body = self._desugar_block(stmt.body)
            return ast.UnsafeBlock(
                body=new_body,
                span=stmt.span
            )
        # For other statements, return as-is
        return stmt
    
    def _desugar_with(self, with_stmt: ast.WithStmt) -> List[ast.Statement]:
        """Desugar a with statement into let + defer + body
        
        Returns a list of statements: [let_stmt, defer_stmt, ...body_statements]
        """
        # Create: let resource = try expression
        let_stmt = ast.VarDecl(
            name=with_stmt.variable,
            mutable=False,  # let is immutable
            type_annotation=None,  # Type will be inferred
            initializer=with_stmt.value,  # Already contains try expression
            span=with_stmt.span
        )
        
        # Create: defer: resource.close()
        # Create identifier for the variable
        var_ident = ast.Identifier(name=with_stmt.variable, span=with_stmt.span)
        close_call = ast.MethodCall(
            object=var_ident,
            method="close",
            arguments=[],
            span=with_stmt.span
        )
        defer_body = ast.Block(
            statements=[ast.ExpressionStmt(expression=close_call, span=with_stmt.span)],
            span=with_stmt.span
        )
        defer_stmt = ast.DeferStmt(
            body=defer_body,
            span=with_stmt.span
        )
        
        # Desugar any nested with statements in the body
        desugared_body = self._desugar_block(with_stmt.body)
        
        # Return: let, defer, and body statements
        result = [let_stmt, defer_stmt]
        result.extend(desugared_body.statements)
        return result

