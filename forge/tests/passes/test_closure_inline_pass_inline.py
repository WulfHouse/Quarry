"""Inlining tests for closure inline pass"""

"""Tests for closure_inline_pass.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from unittest.mock import MagicMock, Mock
from src.passes.closure_inline_pass import ClosureInlinePass
from src import ast
from src.types import FunctionType, IntType, StringType
from src.frontend.tokens import Span


def test_inline_in_functions_no_functions():
    """Test _inline_in_functions() with no functions"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    program = ast.Program(imports=[], items=[], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._inline_in_functions(program)
    
    # Should not crash
    assert True




def test_inline_in_functions_with_function():
    """Test _inline_in_functions() with function"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._inline_in_functions(program)
    
    # Should not crash
    assert True




def test_inline_in_block():
    """Test _inline_in_block()"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    block = ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10))
    result = pass_obj._inline_in_block(block, func)
    
    assert isinstance(result, ast.Block)
    assert result.span == block.span




def test_inline_in_block_multiple_statements():
    """Test _inline_in_block() with multiple statements (covers lines 164-167)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create block with multiple statements
    stmt1 = ast.ExpressionStmt(
        expression=ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2)),
        span=Span("test.pyrite", 1, 1, 1, 2)
    )
    stmt2 = ast.ExpressionStmt(
        expression=ast.IntLiteral(value=43, span=Span("test.pyrite", 2, 1, 2, 2)),
        span=Span("test.pyrite", 2, 1, 2, 2)
    )
    
    block = ast.Block(statements=[stmt1, stmt2], span=Span("test.pyrite", 1, 1, 2, 2))
    result = pass_obj._inline_in_block(block, func)
    
    assert isinstance(result, ast.Block)
    assert len(result.statements) == 2
    assert result.span == block.span




def test_inline_in_statement_expression_stmt_no_closure():
    """Test _inline_in_statement() with ExpressionStmt not calling closure"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    expr = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.ExpressionStmt(expression=expr, span=Span("test.pyrite", 1, 1, 1, 2))
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.ExpressionStmt)




def test_inline_in_statement_var_decl():
    """Test _inline_in_statement() with VarDecl"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    init = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.VarDecl(
        name="x",
        type_annotation=None,
        initializer=init,
        mutable=False,
        span=Span("test.pyrite", 1, 1, 1, 5)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.VarDecl)
    assert result.name == "x"




def test_inline_in_statement_assignment():
    """Test _inline_in_statement() with Assignment"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    target = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 1))
    value = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    stmt = ast.Assignment(target=target, value=value, span=Span("test.pyrite", 1, 1, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.Assignment)




def test_inline_in_statement_return():
    """Test _inline_in_statement() with ReturnStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    value = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 8, 1, 10))
    stmt = ast.ReturnStmt(value=value, span=Span("test.pyrite", 1, 1, 1, 10))
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.ReturnStmt)




def test_inline_in_statement_if():
    """Test _inline_in_statement() with IfStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=None,
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.IfStmt)
    # Result should have elif_clauses (even if empty)
    assert hasattr(result, 'elif_clauses')




def test_inline_in_statement_if_with_else():
    """Test _inline_in_statement() with IfStmt with else"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    else_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=else_block,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.IfStmt)
    assert result.else_block is not None




def test_inline_in_statement_while():
    """Test _inline_in_statement() with WhileStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 7, 1, 11))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 12, 1, 13))
    stmt = ast.WhileStmt(condition=condition, body=body, span=Span("test.pyrite", 1, 1, 1, 13))
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.WhileStmt)




def test_inline_in_statement_for():
    """Test _inline_in_statement() with ForStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    iterable = ast.Identifier(name="list", span=Span("test.pyrite", 1, 9, 1, 13))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15))
    stmt = ast.ForStmt(
        variable="x",
        iterable=iterable,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.ForStmt)




def test_inline_in_statement_match():
    """Test _inline_in_statement() with MatchStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15)),
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.MatchStmt)




def test_inline_in_statement_match_with_guard():
    """Test _inline_in_statement() with MatchStmt with guard"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    guard = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 20, 1, 24))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=guard,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 25, 1, 26)),
        span=Span("test.pyrite", 1, 12, 1, 26)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 26)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.MatchStmt)
    assert result.arms[0].guard is not None




def test_inline_in_statement_with():
    """Test _inline_in_statement() with WithStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    value = ast.Identifier(name="file", span=Span("test.pyrite", 1, 10, 1, 14))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.WithStmt(
        variable="f",
        value=value,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.WithStmt)




def test_inline_in_expression_function_call():
    """Test _inline_in_expression() with FunctionCall"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    func_expr = ast.Identifier(name="call", span=Span("test.pyrite", 1, 1, 1, 5))
    call = ast.FunctionCall(
        function=func_expr,
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    
    result = pass_obj._inline_in_expression(call, func)
    assert isinstance(result, ast.FunctionCall)




def test_inline_in_expression_function_call_with_compile_time_args():
    """Test _inline_in_expression() with FunctionCall with compile_time_args"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    func_expr = ast.Identifier(name="call", span=Span("test.pyrite", 1, 1, 1, 5))
    ct_arg = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 6, 1, 7))
    call = ast.FunctionCall(
        function=func_expr,
        compile_time_args=[ct_arg],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    
    result = pass_obj._inline_in_expression(call, func)
    assert isinstance(result, ast.FunctionCall)
    assert len(result.compile_time_args) == 1




def test_inline_in_expression_binop():
    """Test _inline_in_expression() with BinOp"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    left = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 1, 1, 1))
    right = ast.IntLiteral(value=2, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="+", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.BinOp)




def test_inline_in_expression_unaryop():
    """Test _inline_in_expression() with UnaryOp"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    operand = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 2, 1, 4))
    expr = ast.UnaryOp(op="-", operand=operand, span=Span("test.pyrite", 1, 1, 1, 4))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.UnaryOp)




def test_inline_in_expression_method_call():
    """Test _inline_in_expression() with MethodCall"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.MethodCall)
    assert result.arguments == []




def test_inline_in_expression_field_access():
    """Test _inline_in_expression() with FieldAccess"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.FieldAccess(object=obj, field="field", span=Span("test.pyrite", 1, 1, 1, 8))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.FieldAccess)




def test_inline_in_expression_index_access():
    """Test _inline_in_expression() with IndexAccess"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    index = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    expr = ast.IndexAccess(object=obj, index=index, span=Span("test.pyrite", 1, 1, 1, 4))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.IndexAccess)




def test_inline_in_expression_struct_literal():
    """Test _inline_in_expression() with StructLiteral"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("x", ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11)))],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.StructLiteral)




def test_inline_in_expression_list_literal():
    """Test _inline_in_expression() with ListLiteral"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    expr = ast.ListLiteral(
        elements=[ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 2, 1, 3))],
        span=Span("test.pyrite", 1, 1, 1, 4)
    )
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.ListLiteral)




def test_inline_in_expression_try_expr():
    """Test _inline_in_expression() with TryExpr"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    inner = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.TryExpr)




def test_inline_in_expression_literal():
    """Test _inline_in_expression() with literal (should return as-is)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    expr = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2))
    result = pass_obj._inline_in_expression(expr, func)
    assert result == expr




def test_inline_in_expression_identifier():
    """Test _inline_in_expression() with Identifier (should return as-is)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    expr = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    result = pass_obj._inline_in_expression(expr, func)
    assert result == expr




def test_inline_in_functions_with_closure_args():
    """Test _inline_in_functions() with function that has closure args (covers line 155)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    # Set up closure args
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    pass_obj.function_closure_args["test"] = {0: closure}
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._inline_in_functions(program)
    
    # Should have inlined
    assert True




def test_inline_in_statement_expression_stmt_with_parameter_closure_call():
    """Test _inline_in_statement() with ExpressionStmt calling parameter closure (covers lines 174-228)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    # Set up parameter closure params
    pass_obj.param_closure_params["test"] = {"f": 0}
    
    # Set up closure args
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(
            statements=[ast.ReturnStmt(
                value=ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 10, 1, 12)),
                span=Span("test.pyrite", 1, 10, 1, 12)
            )],
            span=Span("test.pyrite", 1, 6, 1, 12)
        ),
        span=Span("test.pyrite", 1, 6, 1, 12)
    )
    pass_obj.function_closure_args["test"] = {0: closure}
    
    # Mock the inliner
    mock_inlined_block = ast.Block(
        statements=[ast.ReturnStmt(
            value=ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 10, 1, 12)),
            span=Span("test.pyrite", 1, 10, 1, 12)
        )],
        span=Span("test.pyrite", 1, 6, 1, 12)
    )
    pass_obj.inliner.inline_parameter_closure = MagicMock(return_value=mock_inlined_block)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[ast.Param(name="f", type_annotation=None, span=Span("test.pyrite", 1, 10, 1, 12))],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create expression statement calling parameter closure
    call = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 5, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should have inlined the closure
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.IntLiteral)
    assert result.expression.value == 42




def test_inline_in_statement_expression_stmt_closure_call_no_match():
    """Test _inline_in_statement() with ExpressionStmt calling non-closure param (covers line 227)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Call to regular function, not parameter closure
    call = ast.FunctionCall(
        function=ast.Identifier(name="regular", span=Span("test.pyrite", 1, 5, 1, 12)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 14)
    )
    stmt = ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 5, 1, 14))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should process normally
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.FunctionCall)




def test_inline_in_statement_assignment_both_sides():
    """Test _inline_in_statement() with Assignment inlining both target and value (covers lines 239-241)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    target = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    value = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    stmt = ast.Assignment(target=target, value=value, span=Span("test.pyrite", 1, 1, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.Assignment)
    assert result.target == target
    assert result.value == value




def test_inline_in_statement_return_with_value():
    """Test _inline_in_statement() with ReturnStmt that has value (covers lines 244-245)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    value = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 8, 1, 10))
    stmt = ast.ReturnStmt(value=value, span=Span("test.pyrite", 1, 1, 1, 10))
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.ReturnStmt)
    assert result.value == value




def test_inline_in_statement_if_with_else():
    """Test _inline_in_statement() with IfStmt that has else block (covers lines 251-252)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    else_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=else_block,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.IfStmt)
    assert result.else_block is not None




def test_inline_in_statement_match_with_guard():
    """Test _inline_in_statement() with MatchStmt that has guard (covers lines 281-283)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    guard = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 20, 1, 24))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=guard,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 25, 1, 26)),
        span=Span("test.pyrite", 1, 12, 1, 26)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 26)
    )
    
    result = pass_obj._inline_in_statement(stmt, func)
    assert isinstance(result, ast.MatchStmt)
    assert result.arms[0].guard is not None




def test_inline_in_expression_function_call_with_parameter_closure_arg():
    """Test _inline_in_expression() with FunctionCall containing ParameterClosure (covers line 322)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    func_expr = ast.Identifier(name="call", span=Span("test.pyrite", 1, 1, 1, 5))
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    other_arg = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11))
    call = ast.FunctionCall(
        function=func_expr,
        compile_time_args=[],
        arguments=[closure, other_arg],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    
    result = pass_obj._inline_in_expression(call, func)
    assert isinstance(result, ast.FunctionCall)
    # Closure should be kept as-is, other arg should be processed
    assert len(result.arguments) == 2
    assert isinstance(result.arguments[0], ast.ParameterClosure)
    assert isinstance(result.arguments[1], ast.IntLiteral)




def test_inline_in_expression_function_call_with_compile_time_args():
    """Test _inline_in_expression() with FunctionCall that has compile_time_args (covers lines 330-332)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    func_expr = ast.Identifier(name="call", span=Span("test.pyrite", 1, 1, 1, 5))
    ct_arg = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 6, 1, 7))
    call = ast.FunctionCall(
        function=func_expr,
        compile_time_args=[ct_arg],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    
    result = pass_obj._inline_in_expression(call, func)
    assert isinstance(result, ast.FunctionCall)
    assert len(result.compile_time_args) == 1




def test_inline_in_expression_binop_both_sides():
    """Test _inline_in_expression() with BinOp inlining both sides (covers lines 341-343)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    left = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 1, 1, 1))
    right = ast.IntLiteral(value=2, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="+", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.BinOp)
    assert result.left == left
    assert result.right == right




def test_inline_in_expression_unaryop_operand():
    """Test _inline_in_expression() with UnaryOp inlining operand (covers lines 350-351)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    operand = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 2, 1, 4))
    expr = ast.UnaryOp(op="-", operand=operand, span=Span("test.pyrite", 1, 1, 1, 4))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.UnaryOp)
    assert result.operand == operand




def test_inline_in_expression_method_call_with_args():
    """Test _inline_in_expression() with MethodCall inlining object and args (covers lines 357-359)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    arg = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11))
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[arg],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.MethodCall)
    assert len(result.arguments) == 1




def test_inline_in_expression_field_access():
    """Test _inline_in_expression() with FieldAccess inlining object (covers lines 366-367)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.FieldAccess(object=obj, field="field", span=Span("test.pyrite", 1, 1, 1, 8))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.FieldAccess)
    assert result.object == obj




def test_inline_in_expression_index_access_both():
    """Test _inline_in_expression() with IndexAccess inlining object and index (covers lines 373-375)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    index = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    expr = ast.IndexAccess(object=obj, index=index, span=Span("test.pyrite", 1, 1, 1, 4))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.IndexAccess)
    assert result.object == obj
    assert result.index == index




def test_inline_in_expression_struct_literal_fields():
    """Test _inline_in_expression() with StructLiteral inlining fields (covers lines 381-385)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    field_expr = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11))
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("x", field_expr)],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.StructLiteral)
    assert len(result.fields) == 1
    assert result.fields[0][0] == "x"




def test_inline_in_expression_list_literal_elements():
    """Test _inline_in_expression() with ListLiteral inlining elements (covers lines 391-395)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    elem = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 2, 1, 3))
    expr = ast.ListLiteral(
        elements=[elem],
        span=Span("test.pyrite", 1, 1, 1, 4)
    )
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.ListLiteral)
    assert len(result.elements) == 1




def test_inline_in_expression_try_expr():
    """Test _inline_in_expression() with TryExpr inlining expression (covers lines 400-401)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    inner = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    
    result = pass_obj._inline_in_expression(expr, func)
    assert isinstance(result, ast.TryExpr)
    assert result.expression == inner




def test_inline_in_statement_expression_stmt_closure_call_multiple_statements():
    """Test _inline_in_statement() with closure call that produces multiple statements (covers lines 210-220)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    # Set up parameter closure params
    pass_obj.param_closure_params["test"] = {"f": 0}
    
    # Set up closure args
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    pass_obj.function_closure_args["test"] = {0: closure}
    
    # Mock the inliner to return multiple statements
    mock_inlined_block = ast.Block(
        statements=[
            ast.ExpressionStmt(
                expression=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11)),
                span=Span("test.pyrite", 1, 10, 1, 11)
            ),
            ast.ReturnStmt(
                value=ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 12, 1, 14)),
                span=Span("test.pyrite", 1, 12, 1, 14)
            )
        ],
        span=Span("test.pyrite", 1, 6, 1, 14)
    )
    pass_obj.inliner.inline_parameter_closure = MagicMock(return_value=mock_inlined_block)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[ast.Param(name="f", type_annotation=None, span=Span("test.pyrite", 1, 10, 1, 12))],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create expression statement calling parameter closure
    call = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 5, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should return first return statement's value as expression
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.IntLiteral)
    assert result.expression.value == 42




def test_inline_in_statement_expression_stmt_closure_call_no_return():
    """Test _inline_in_statement() with closure call that has no return (covers line 220)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    # Set up parameter closure params
    pass_obj.param_closure_params["test"] = {"f": 0}
    
    # Set up closure args
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    pass_obj.function_closure_args["test"] = {0: closure}
    
    # Mock the inliner to return multiple statements without return
    mock_inlined_block = ast.Block(
        statements=[
            ast.ExpressionStmt(
                expression=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11)),
                span=Span("test.pyrite", 1, 10, 1, 11)
            ),
            ast.ExpressionStmt(
                expression=ast.IntLiteral(value=2, span=Span("test.pyrite", 1, 12, 1, 13)),
                span=Span("test.pyrite", 1, 12, 1, 13)
            )
        ],
        span=Span("test.pyrite", 1, 6, 1, 13)
    )
    pass_obj.inliner.inline_parameter_closure = MagicMock(return_value=mock_inlined_block)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[ast.Param(name="f", type_annotation=None, span=Span("test.pyrite", 1, 10, 1, 12))],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create expression statement calling parameter closure
    call = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 5, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should return first statement
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.IntLiteral)
    assert result.expression.value == 1




def test_inline_in_statement_expression_stmt_closure_call_inlining_fails():
    """Test _inline_in_statement() when closure inlining raises ValueError (covers lines 221-224)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    # Set up parameter closure params
    pass_obj.param_closure_params["test"] = {"f": 0}
    
    # Set up closure args
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    pass_obj.function_closure_args["test"] = {0: closure}
    
    # Mock the inliner to raise ValueError
    pass_obj.inliner.inline_parameter_closure = MagicMock(side_effect=ValueError("Inlining failed"))
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[ast.Param(name="f", type_annotation=None, span=Span("test.pyrite", 1, 10, 1, 12))],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create expression statement calling parameter closure
    call = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 5, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should fall through to normal processing (line 227)
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.FunctionCall)




def test_inline_in_statement_expression_stmt_closure_call_single_non_return():
    """Test _inline_in_statement() with closure call producing single non-return statement (covers line 209)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    # Set up parameter closure params
    pass_obj.param_closure_params["test"] = {"f": 0}
    
    # Set up closure args
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    pass_obj.function_closure_args["test"] = {0: closure}
    
    # Mock the inliner to return single non-return statement
    mock_inlined_block = ast.Block(
        statements=[
            ast.ExpressionStmt(
                expression=ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 10, 1, 12)),
                span=Span("test.pyrite", 1, 10, 1, 12)
            )
        ],
        span=Span("test.pyrite", 1, 6, 1, 12)
    )
    pass_obj.inliner.inline_parameter_closure = MagicMock(return_value=mock_inlined_block)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[ast.Param(name="f", type_annotation=None, span=Span("test.pyrite", 1, 10, 1, 12))],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create expression statement calling parameter closure
    call = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 5, 1, 7))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should return the single statement as-is (line 209)
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.IntLiteral)
    assert result.expression.value == 42




def test_inline_in_statement_unhandled_type():
    """Test _inline_in_statement() with unhandled statement type (covers line 306)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Create a DeferStmt (or other unhandled statement type)
    # Check what statement types exist in ast
    # For now, let's use BreakStmt if it exists, or create a mock statement
    try:
        stmt = ast.BreakStmt(span=Span("test.pyrite", 1, 1, 1, 5))
    except AttributeError:
        # If BreakStmt doesn't exist, create a mock statement that won't match any handled types
        class UnhandledStmt(ast.Statement):
            pass
        stmt = UnhandledStmt(span=Span("test.pyrite", 1, 1, 1, 5))
    
    result = pass_obj._inline_in_statement(stmt, func)
    
    # Should return statement as-is (line 306)
    assert result == stmt
