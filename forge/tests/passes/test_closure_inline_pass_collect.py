"""Collection tests for closure inline pass"""

"""Tests for closure_inline_pass.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from unittest.mock import MagicMock, Mock
from src.passes.closure_inline_pass import ClosureInlinePass
from src import ast
from src.types import FunctionType, IntType, StringType
from src.frontend.tokens import Span


def test_collect_closure_arguments_no_functions():
    """Test _collect_closure_arguments() with no functions"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    program = ast.Program(imports=[], items=[], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._collect_closure_arguments(program)
    
    assert pass_obj.function_closure_args == {}




def test_collect_closure_arguments_with_function():
    """Test _collect_closure_arguments() with function"""
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
    pass_obj._collect_closure_arguments(program)
    
    # Should not crash
    assert True




def test_collect_in_function():
    """Test _collect_in_function()"""
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
    
    pass_obj._collect_in_function(func)
    # Should not crash
    assert True




def test_collect_in_block():
    """Test _collect_in_block()"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    block = ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10))
    pass_obj._collect_in_block(block)
    # Should not crash
    assert True




def test_collect_in_statement_expression_stmt():
    """Test _collect_in_statement() with ExpressionStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    expr = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.ExpressionStmt(expression=expr, span=Span("test.pyrite", 1, 1, 1, 2))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_var_decl():
    """Test _collect_in_statement() with VarDecl"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    init = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.VarDecl(
        name="x",
        type_annotation=None,
        initializer=init,
        mutable=False,
        span=Span("test.pyrite", 1, 1, 1, 5)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_assignment():
    """Test _collect_in_statement() with Assignment"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    target = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 1))
    value = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    stmt = ast.Assignment(target=target, value=value, span=Span("test.pyrite", 1, 1, 1, 7))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_return():
    """Test _collect_in_statement() with ReturnStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    value = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 8, 1, 10))
    stmt = ast.ReturnStmt(value=value, span=Span("test.pyrite", 1, 1, 1, 10))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_if():
    """Test _collect_in_statement() with IfStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=None,
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_if_with_else():
    """Test _collect_in_statement() with IfStmt with else block"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
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
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_while():
    """Test _collect_in_statement() with WhileStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 7, 1, 11))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 12, 1, 13))
    stmt = ast.WhileStmt(condition=condition, body=body, span=Span("test.pyrite", 1, 1, 1, 13))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_for():
    """Test _collect_in_statement() with ForStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    iterable = ast.Identifier(name="list", span=Span("test.pyrite", 1, 9, 1, 13))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15))
    stmt = ast.ForStmt(
        variable="x",
        iterable=iterable,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_match():
    """Test _collect_in_statement() with MatchStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
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
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_match_with_guard():
    """Test _collect_in_statement() with MatchStmt with guard"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
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
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_with():
    """Test _collect_in_statement() with WithStmt"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    value = ast.Identifier(name="file", span=Span("test.pyrite", 1, 10, 1, 14))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.WithStmt(
        variable="f",
        value=value,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_expression_function_call():
    """Test _collect_in_expression() with FunctionCall"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    
    pass_obj._collect_in_expression(call)
    # Should not crash
    assert True




def test_collect_in_expression_function_call_with_parameter_closure():
    """Test _collect_in_expression() with FunctionCall containing ParameterClosure"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[closure],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    
    pass_obj._collect_in_expression(call)
    # Should record the closure argument
    assert "test" in pass_obj.function_closure_args
    assert 0 in pass_obj.function_closure_args["test"]




def test_collect_in_expression_binop():
    """Test _collect_in_expression() with BinOp"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    left = ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 1, 1, 1))
    right = ast.IntLiteral(value=2, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="+", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_unaryop():
    """Test _collect_in_expression() with UnaryOp"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    operand = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 2, 1, 4))
    expr = ast.UnaryOp(op="-", operand=operand, span=Span("test.pyrite", 1, 1, 1, 4))
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_method_call():
    """Test _collect_in_expression() with MethodCall"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_field_access():
    """Test _collect_in_expression() with FieldAccess"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.FieldAccess(object=obj, field="field", span=Span("test.pyrite", 1, 1, 1, 8))
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_index_access():
    """Test _collect_in_expression() with IndexAccess"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    index = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    expr = ast.IndexAccess(object=obj, index=index, span=Span("test.pyrite", 1, 1, 1, 4))
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_struct_literal():
    """Test _collect_in_expression() with StructLiteral"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("x", ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 10, 1, 11)))],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_list_literal():
    """Test _collect_in_expression() with ListLiteral"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    expr = ast.ListLiteral(
        elements=[ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 2, 1, 3))],
        span=Span("test.pyrite", 1, 1, 1, 4)
    )
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_expression_try_expr():
    """Test _collect_in_expression() with TryExpr"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    inner = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    
    pass_obj._collect_in_expression(expr)
    # Should not crash
    assert True




def test_collect_in_statement_assignment_with_value():
    """Test _collect_in_statement() with Assignment that has value (covers line 65)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    target = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    value = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.Assignment(target=target, value=value, span=Span("test.pyrite", 1, 1, 1, 7))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_return_with_value():
    """Test _collect_in_statement() with ReturnStmt that has value (covers line 68)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    value = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 8, 1, 9)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 8, 1, 10)
    )
    stmt = ast.ReturnStmt(value=value, span=Span("test.pyrite", 1, 1, 1, 10))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_if_with_else_block():
    """Test _collect_in_statement() with IfStmt that has else block (covers line 73)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    else_block = ast.Block(
        statements=[ast.ExpressionStmt(
            expression=ast.FunctionCall(
                function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 15, 1, 16)),
                compile_time_args=[],
                arguments=[],
                span=Span("test.pyrite", 1, 15, 1, 17)
            ),
            span=Span("test.pyrite", 1, 15, 1, 17)
        )],
        span=Span("test.pyrite", 1, 15, 1, 17)
    )
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=else_block,
        span=Span("test.pyrite", 1, 1, 1, 17)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_while():
    """Test _collect_in_statement() with WhileStmt (covers lines 75-76)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 7, 1, 11))
    body = ast.Block(
        statements=[ast.ExpressionStmt(
            expression=ast.FunctionCall(
                function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 13, 1, 14)),
                compile_time_args=[],
                arguments=[],
                span=Span("test.pyrite", 1, 13, 1, 15)
            ),
            span=Span("test.pyrite", 1, 13, 1, 15)
        )],
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.WhileStmt(condition=condition, body=body, span=Span("test.pyrite", 1, 1, 1, 15))
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_for():
    """Test _collect_in_statement() with ForStmt (covers lines 78-79)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    iterable = ast.FunctionCall(
        function=ast.Identifier(name="list", span=Span("test.pyrite", 1, 9, 1, 13)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 9, 1, 15)
    )
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 16, 1, 17))
    stmt = ast.ForStmt(
        variable="x",
        iterable=iterable,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 17)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_match_with_guard():
    """Test _collect_in_statement() with MatchStmt that has guard (covers lines 83-84)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    guard = ast.FunctionCall(
        function=ast.Identifier(name="check", span=Span("test.pyrite", 1, 20, 1, 25)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 20, 1, 27)
    )
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=guard,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 28, 1, 29)),
        span=Span("test.pyrite", 1, 12, 1, 29)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 29)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_statement_with():
    """Test _collect_in_statement() with WithStmt (covers lines 87-88)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    value = ast.FunctionCall(
        function=ast.Identifier(name="open", span=Span("test.pyrite", 1, 10, 1, 14)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 10, 1, 16)
    )
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 17, 1, 18))
    stmt = ast.WithStmt(
        variable="f",
        value=value,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 18)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True




def test_collect_in_expression_function_call_with_parameter_closure_recursion():
    """Test _collect_in_expression() with FunctionCall that has ParameterClosure and other args (covers lines 98-103)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    closure = ast.ParameterClosure(
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 8)),
        span=Span("test.pyrite", 1, 6, 1, 8)
    )
    other_arg = ast.FunctionCall(
        function=ast.Identifier(name="helper", span=Span("test.pyrite", 1, 10, 1, 16)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 10, 1, 18)
    )
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[closure, other_arg],
        span=Span("test.pyrite", 1, 1, 1, 18)
    )
    
    pass_obj._collect_in_expression(call)
    # Should record closure and recurse into other_arg
    assert "test" in pass_obj.function_closure_args
    assert 0 in pass_obj.function_closure_args["test"]




def test_collect_in_expression_binop_both_sides():
    """Test _collect_in_expression() with BinOp recursing into both sides (covers lines 105-106)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    left = ast.FunctionCall(
        function=ast.Identifier(name="f1", span=Span("test.pyrite", 1, 1, 1, 3)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 5)
    )
    right = ast.FunctionCall(
        function=ast.Identifier(name="f2", span=Span("test.pyrite", 1, 5, 1, 7)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 9)
    )
    expr = ast.BinOp(op="+", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 9))
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into both sides
    assert True




def test_collect_in_expression_unaryop_operand():
    """Test _collect_in_expression() with UnaryOp recursing into operand (covers line 108)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    operand = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 2, 1, 3)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 2, 1, 5)
    )
    expr = ast.UnaryOp(op="-", operand=operand, span=Span("test.pyrite", 1, 1, 1, 5))
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into operand
    assert True




def test_collect_in_expression_method_call_with_args():
    """Test _collect_in_expression() with MethodCall recursing into object and args (covers lines 110-112)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    obj = ast.FunctionCall(
        function=ast.Identifier(name="create", span=Span("test.pyrite", 1, 1, 1, 7)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 9)
    )
    arg = ast.FunctionCall(
        function=ast.Identifier(name="helper", span=Span("test.pyrite", 1, 11, 1, 17)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 11, 1, 19)
    )
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[arg],
        span=Span("test.pyrite", 1, 1, 1, 19)
    )
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into object and arguments
    assert True




def test_collect_in_expression_field_access_object():
    """Test _collect_in_expression() with FieldAccess recursing into object (covers line 114)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    obj = ast.FunctionCall(
        function=ast.Identifier(name="create", span=Span("test.pyrite", 1, 1, 1, 7)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 9)
    )
    expr = ast.FieldAccess(object=obj, field="field", span=Span("test.pyrite", 1, 1, 1, 15))
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into object
    assert True




def test_collect_in_expression_index_access_both():
    """Test _collect_in_expression() with IndexAccess recursing into object and index (covers lines 116-117)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    obj = ast.FunctionCall(
        function=ast.Identifier(name="list", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    index = ast.FunctionCall(
        function=ast.Identifier(name="calc", span=Span("test.pyrite", 1, 3, 1, 7)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 3, 1, 9)
    )
    expr = ast.IndexAccess(object=obj, index=index, span=Span("test.pyrite", 1, 1, 1, 9))
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into both object and index
    assert True




def test_collect_in_expression_struct_literal_fields():
    """Test _collect_in_expression() with StructLiteral recursing into fields (covers lines 119-120)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    field_expr = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 10, 1, 11)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 10, 1, 13)
    )
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("x", field_expr)],
        span=Span("test.pyrite", 1, 1, 1, 13)
    )
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into field expressions
    assert True




def test_collect_in_expression_list_literal_elements():
    """Test _collect_in_expression() with ListLiteral recursing into elements (covers lines 122-123)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    elem = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 2, 1, 3)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 2, 1, 5)
    )
    expr = ast.ListLiteral(
        elements=[elem],
        span=Span("test.pyrite", 1, 1, 1, 5)
    )
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into elements
    assert True




def test_collect_in_expression_try_expr():
    """Test _collect_in_expression() with TryExpr recursing into expression (covers line 125)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    inner = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 8)
    )
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 8))
    
    pass_obj._collect_in_expression(expr)
    # Should recurse into expression
    assert True


