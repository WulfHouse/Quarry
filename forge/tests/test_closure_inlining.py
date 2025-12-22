"""Tests for parameter closure inlining"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.passes import ClosureInliner
from src import ast
from src.types import IntType
from src.frontend.tokens import Span


def test_simple_parameter_substitution():
    """Test that parameter closures can substitute parameters with arguments"""
    # Create a simple parameter closure: fn[i: int]: i * 2
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="i", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(
            statements=[
                ast.ReturnStmt(
                    value=ast.BinOp(
                        op="*",
                        left=ast.Identifier(name="i", span=span),
                        right=ast.IntLiteral(value=2, span=span),
                        span=span
                    ),
                    span=span
                )
            ],
            span=span
        ),
        span=span
    )
    
    # Create argument: 5
    argument = ast.IntLiteral(value=5, span=span)
    
    # Inline the closure
    inliner = ClosureInliner()
    inlined = inliner.inline_parameter_closure(closure, [argument])
    
    # The inlined body should have i replaced with 5
    # So it should be: return 5 * 2
    assert len(inlined.statements) == 1
    return_stmt = inlined.statements[0]
    assert isinstance(return_stmt, ast.ReturnStmt)
    assert isinstance(return_stmt.value, ast.BinOp)
    assert return_stmt.value.op == "*"
    # The left side should be the literal 5 (substituted)
    assert isinstance(return_stmt.value.left, ast.IntLiteral)
    assert return_stmt.value.left.value == 5
    # The right side should still be 2
    assert isinstance(return_stmt.value.right, ast.IntLiteral)
    assert return_stmt.value.right.value == 2


def test_multiple_parameters():
    """Test inlining with multiple parameters"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="x", type_annotation=IntType(), span=span),
            ast.Param(name="y", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(
            statements=[
                ast.ReturnStmt(
                    value=ast.BinOp(
                        op="+",
                        left=ast.Identifier(name="x", span=span),
                        right=ast.Identifier(name="y", span=span),
                        span=span
                    ),
                    span=span
                )
            ],
            span=span
        ),
        span=span
    )
    
    # Arguments: 3 and 4
    args = [
        ast.IntLiteral(value=3, span=span),
        ast.IntLiteral(value=4, span=span)
    ]
    
    inliner = ClosureInliner()
    inlined = inliner.inline_parameter_closure(closure, args)
    
    # Should be: return 3 + 4
    assert len(inlined.statements) == 1
    return_stmt = inlined.statements[0]
    assert isinstance(return_stmt.value, ast.BinOp)
    assert return_stmt.value.op == "+"
    assert isinstance(return_stmt.value.left, ast.IntLiteral)
    assert return_stmt.value.left.value == 3
    assert isinstance(return_stmt.value.right, ast.IntLiteral)
    assert return_stmt.value.right.value == 4


def test_parameter_count_mismatch():
    """Test that parameter count mismatch raises error"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="x", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(statements=[], span=span),
        span=span
    )
    
    # Wrong number of arguments
    args = [
        ast.IntLiteral(value=1, span=span),
        ast.IntLiteral(value=2, span=span)
    ]
    
    inliner = ClosureInliner()
    with pytest.raises(ValueError, match="Parameter count mismatch"):
        inliner.inline_parameter_closure(closure, args)


def test_nested_expressions():
    """Test that nested expressions are properly substituted"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="i", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(
            statements=[
                ast.ReturnStmt(
                    value=ast.BinOp(
                        op="*",
                        left=ast.BinOp(
                            op="+",
                            left=ast.Identifier(name="i", span=span),
                            right=ast.IntLiteral(value=1, span=span),
                            span=span
                        ),
                        right=ast.IntLiteral(value=2, span=span),
                        span=span
                    ),
                    span=span
                )
            ],
            span=span
        ),
        span=span
    )
    
    argument = ast.IntLiteral(value=5, span=span)
    
    inliner = ClosureInliner()
    inlined = inliner.inline_parameter_closure(closure, [argument])
    
    # Should be: return (5 + 1) * 2
    return_stmt = inlined.statements[0]
    assert isinstance(return_stmt.value, ast.BinOp)
    assert return_stmt.value.op == "*"
    # Left side should be (5 + 1)
    assert isinstance(return_stmt.value.left, ast.BinOp)
    assert return_stmt.value.left.op == "+"
    assert isinstance(return_stmt.value.left.left, ast.IntLiteral)
    assert return_stmt.value.left.left.value == 5


def test_max_inlining_depth():
    """Test that inlining depth is limited to prevent infinite recursion"""
    # Create a closure that would cause deep nesting if not limited
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="x", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(
            statements=[
                ast.ReturnStmt(
                    value=ast.Identifier(name="x", span=span),
                    span=span
                )
            ],
            span=span
        ),
        span=span
    )
    
    inliner = ClosureInliner()
    # Set a low max depth for testing
    inliner.max_inlining_depth = 3
    
    # Should work fine for normal depth
    arg = ast.IntLiteral(value=5, span=span)
    result = inliner.inline_parameter_closure(closure, [arg])
    assert len(result.statements) == 1
    
    # Test that depth tracking works (can't easily test overflow without recursion)


def test_max_inlining_depth_exceeded():
    """Test that exceeding max inlining depth raises error"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="x", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(
            statements=[
                ast.ReturnStmt(
                    value=ast.Identifier(name="x", span=span),
                    span=span
                )
            ],
            span=span
        ),
        span=span
    )
    
    inliner = ClosureInliner()
    inliner.max_inlining_depth = 0  # Set to 0 to trigger error
    
    arg = ast.IntLiteral(value=5, span=span)
    with pytest.raises(ValueError, match="Maximum inlining depth"):
        inliner.inline_parameter_closure(closure, [arg])


def test_code_size_estimate():
    """Test that inlining doesn't create unreasonably large code"""
    # Create a simple closure
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="i", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(
            statements=[
                ast.ReturnStmt(
                    value=ast.BinOp(
                        op="*",
                        left=ast.Identifier(name="i", span=span),
                        right=ast.IntLiteral(value=2, span=span),
                        span=span
                    ),
                    span=span
                )
            ],
            span=span
        ),
        span=span
    )
    
    inliner = ClosureInliner()
    arg = ast.IntLiteral(value=10, span=span)
    inlined = inliner.inline_parameter_closure(closure, [arg])
    
    # Inlined code should be reasonable size (just the substituted expression)
    assert len(inlined.statements) == 1
    # The inlined expression should be simple (not nested deeply)
    return_stmt = inlined.statements[0]
    assert isinstance(return_stmt, ast.ReturnStmt)
    # Should be: return 10 * 2
    assert isinstance(return_stmt.value, ast.BinOp)


def test_code_size_too_large():
    """Test that closures that are too large raise error"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    # Create a closure with many statements
    statements = []
    for i in range(1001):  # Exceed max_inlined_statements (1000)
        statements.append(ast.ReturnStmt(
            value=ast.IntLiteral(value=i, span=span),
            span=span
        ))
    
    closure = ast.ParameterClosure(
        params=[
            ast.Param(name="i", type_annotation=IntType(), span=span)
        ],
        return_type=None,
        body=ast.Block(statements=statements, span=span),
        span=span
    )
    
    inliner = ClosureInliner()
    arg = ast.IntLiteral(value=5, span=span)
    
    with pytest.raises(ValueError, match="Closure body too large"):
        inliner.inline_parameter_closure(closure, [arg])


def test_substitute_return_stmt_no_value():
    """Test _substitute_in_statement() with ReturnStmt without value"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    stmt = ast.ReturnStmt(value=None, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ReturnStmt)
    assert result.value is None


def test_substitute_expression_stmt():
    """Test _substitute_in_statement() with ExpressionStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    expr = ast.IntLiteral(value=42, span=span)
    stmt = ast.ExpressionStmt(expression=expr, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ExpressionStmt)


def test_substitute_var_decl():
    """Test _substitute_in_statement() with VarDecl"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    init = ast.IntLiteral(value=42, span=span)
    stmt = ast.VarDecl(
        pattern=ast.IdentifierPattern(name="x", span=span),
        type_annotation=None,
        initializer=init,
        mutable=False,
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.VarDecl)
    assert result.name == "x"


def test_substitute_assignment():
    """Test _substitute_in_statement() with Assignment"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    target = ast.Identifier(name="x", span=span)
    value = ast.IntLiteral(value=42, span=span)
    stmt = ast.Assignment(target=target, value=value, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.Assignment)


def test_substitute_if_stmt():
    """Test _substitute_in_statement() with IfStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    condition = ast.BoolLiteral(value=True, span=span)
    then_block = ast.Block(statements=[], span=span)
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=None,
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.IfStmt)


def test_substitute_if_stmt_with_else():
    """Test _substitute_in_statement() with IfStmt with else block"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    condition = ast.BoolLiteral(value=True, span=span)
    then_block = ast.Block(statements=[], span=span)
    else_block = ast.Block(statements=[], span=span)
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=else_block,
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.IfStmt)
    assert result.else_block is not None


def test_substitute_while_stmt():
    """Test _substitute_in_statement() with WhileStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    condition = ast.BoolLiteral(value=True, span=span)
    body = ast.Block(statements=[], span=span)
    stmt = ast.WhileStmt(condition=condition, body=body, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.WhileStmt)


def test_substitute_for_stmt():
    """Test _substitute_in_statement() with ForStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    iterable = ast.Identifier(name="list", span=span)
    body = ast.Block(statements=[], span=span)
    stmt = ast.ForStmt(
        variable="x",
        iterable=iterable,
        body=body,
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ForStmt)


def test_substitute_match_stmt():
    """Test _substitute_in_statement() with MatchStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    scrutinee = ast.Identifier(name="x", span=span)
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=span),
        guard=None,
        body=ast.Block(statements=[], span=span),
        span=span
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.MatchStmt)


def test_substitute_match_stmt_with_guard():
    """Test _substitute_in_statement() with MatchStmt with guard"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    scrutinee = ast.Identifier(name="x", span=span)
    guard = ast.BoolLiteral(value=True, span=span)
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=span),
        guard=guard,
        body=ast.Block(statements=[], span=span),
        span=span
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.MatchStmt)
    assert result.arms[0].guard is not None


def test_substitute_identifier_with_substitution():
    """Test _substitute_in_expression() with Identifier that needs substitution"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    identifier = ast.Identifier(name="x", span=span)
    substitution = ast.IntLiteral(value=42, span=span)
    substitutions = {"x": substitution}
    
    result = inliner._substitute_in_expression(identifier, substitutions)
    # Should return the substituted expression
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 42


def test_substitute_identifier_no_substitution():
    """Test _substitute_in_expression() with Identifier that doesn't need substitution"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    identifier = ast.Identifier(name="x", span=span)
    substitutions = {}  # No substitution for "x"
    
    result = inliner._substitute_in_expression(identifier, substitutions)
    # Should return the original identifier
    assert result == identifier


def test_substitute_binop():
    """Test _substitute_in_expression() with BinOp"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    left = ast.IntLiteral(value=1, span=span)
    right = ast.IntLiteral(value=2, span=span)
    expr = ast.BinOp(op="+", left=left, right=right, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.BinOp)
    assert result.op == "+"


def test_substitute_unaryop():
    """Test _substitute_in_expression() with UnaryOp"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    operand = ast.IntLiteral(value=42, span=span)
    expr = ast.UnaryOp(op="-", operand=operand, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.UnaryOp)
    assert result.op == "-"


def test_substitute_function_call():
    """Test _substitute_in_expression() with FunctionCall"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    func = ast.Identifier(name="test", span=span)
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_expression(call, substitutions)
    assert isinstance(result, ast.FunctionCall)


def test_substitute_method_call():
    """Test _substitute_in_expression() with MethodCall"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    obj = ast.Identifier(name="x", span=span)
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.MethodCall)


def test_substitute_field_access():
    """Test _substitute_in_expression() with FieldAccess"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    obj = ast.Identifier(name="x", span=span)
    expr = ast.FieldAccess(object=obj, field="field", span=span)
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.FieldAccess)


def test_substitute_index_access():
    """Test _substitute_in_expression() with IndexAccess"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    obj = ast.Identifier(name="x", span=span)
    index = ast.IntLiteral(value=0, span=span)
    expr = ast.IndexAccess(object=obj, index=index, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.IndexAccess)


def test_substitute_struct_literal():
    """Test _substitute_in_expression() with StructLiteral"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("x", ast.IntLiteral(value=1, span=span))],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.StructLiteral)


def test_substitute_list_literal():
    """Test _substitute_in_expression() with ListLiteral"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    expr = ast.ListLiteral(
        elements=[ast.IntLiteral(value=1, span=span)],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.ListLiteral)


def test_substitute_try_expr():
    """Test _substitute_in_expression() with TryExpr"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    inner = ast.IntLiteral(value=42, span=span)
    expr = ast.TryExpr(expression=inner, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.TryExpr)


def test_substitute_literal():
    """Test _substitute_in_expression() with literal (should return as-is)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    expr = ast.IntLiteral(value=42, span=span)
    substitutions = {}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    # Literals don't need substitution
    assert result == expr


def test_clone_expression():
    """Test _clone_expression()"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    expr = ast.IntLiteral(value=42, span=span)
    
    result = inliner._clone_expression(expr)
    # For now, just returns the expression (shallow clone)
    assert result == expr


def test_estimate_block_size_simple():
    """Test _estimate_block_size() with simple block"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    block = ast.Block(
        statements=[
            ast.ReturnStmt(value=ast.IntLiteral(value=42, span=span), span=span)
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    assert size == 1


def test_estimate_block_size_with_if():
    """Test _estimate_block_size() with IfStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    then_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.IfStmt(
                condition=ast.BoolLiteral(value=True, span=span),
                then_block=then_block,
                elif_clauses=[],
                else_block=None,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count the if statement + statements in then_block
    assert size >= 2


def test_estimate_block_size_with_if_else():
    """Test _estimate_block_size() with IfStmt with else block"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    then_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    else_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=2, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.IfStmt(
                condition=ast.BoolLiteral(value=True, span=span),
                then_block=then_block,
                elif_clauses=[],
                else_block=else_block,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count if + then + else
    assert size >= 3


def test_estimate_block_size_with_while():
    """Test _estimate_block_size() with WhileStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.WhileStmt(
                condition=ast.BoolLiteral(value=True, span=span),
                body=body,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    assert size >= 2


def test_estimate_block_size_with_for():
    """Test _estimate_block_size() with ForStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.ForStmt(
                variable="x",
                iterable=ast.Identifier(name="list", span=span),
                body=body,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    assert size >= 2


def test_estimate_block_size_with_match():
    """Test _estimate_block_size() with MatchStmt"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    arm_body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=span),
        guard=None,
        body=arm_body,
        span=span
    )
    block = ast.Block(
        statements=[
            ast.MatchStmt(
                scrutinee=ast.Identifier(name="x", span=span),
                arms=[arm],
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    assert size >= 2


def test_substitute_block():
    """Test _substitute_in_block()"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    block = ast.Block(
        statements=[
            ast.ReturnStmt(value=ast.IntLiteral(value=42, span=span), span=span)
        ],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_block(block, substitutions)
    assert isinstance(result, ast.Block)
    assert len(result.statements) == 1


def test_estimate_block_size_with_elif():
    """Test _estimate_block_size() with IfStmt with elif clauses"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    then_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    elif_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=2, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.IfStmt(
                condition=ast.BoolLiteral(value=True, span=span),
                then_block=then_block,
                elif_clauses=[(ast.BoolLiteral(value=False, span=span), elif_block)],
                else_block=None,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count if + then + elif (elif clauses are not currently counted in _estimate_block_size)
    # But the method should not crash
    assert size >= 1


def test_substitute_function_call_with_compile_time_args():
    """Test _substitute_in_expression() with FunctionCall with compile_time_args"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    func = ast.Identifier(name="test", span=span)
    ct_arg = ast.IntLiteral(value=1, span=span)
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[ct_arg],
        arguments=[],
        span=span
    )
    substitutions = {}
    
    result = inliner._substitute_in_expression(call, substitutions)
    assert isinstance(result, ast.FunctionCall)
    # compile_time_args should be substituted
    assert len(result.compile_time_args) == 1


def test_substitute_other_statement_type():
    """Test _substitute_in_statement() with statement type that doesn't need substitution (line 172)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    # Use BreakStmt as an example of a statement that doesn't need substitution
    stmt = ast.BreakStmt(span=span)
    substitutions = {}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    # Should return as-is for statement types that don't need substitution
    assert result == stmt


def test_substitute_return_stmt_with_value_and_substitution():
    """Test _substitute_in_statement() with ReturnStmt that has value needing substitution (covers line 96)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    value = ast.Identifier(name="x", span=span)
    stmt = ast.ReturnStmt(value=value, span=span)
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ReturnStmt)
    assert isinstance(result.value, ast.IntLiteral)
    assert result.value.value == 42


def test_substitute_expression_stmt_with_substitution():
    """Test _substitute_in_statement() with ExpressionStmt needing substitution (covers line 101)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    expr = ast.Identifier(name="x", span=span)
    stmt = ast.ExpressionStmt(expression=expr, span=span)
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.IntLiteral)
    assert result.expression.value == 42


def test_substitute_var_decl_with_substitution():
    """Test _substitute_in_statement() with VarDecl needing substitution (covers line 105)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    init = ast.Identifier(name="x", span=span)
    stmt = ast.VarDecl(
        pattern=ast.IdentifierPattern(name="y", span=span),
        type_annotation=None,
        initializer=init,
        mutable=False,
        span=span
    )
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.VarDecl)
    assert result.name == "y"
    assert isinstance(result.initializer, ast.IntLiteral)
    assert result.initializer.value == 42


def test_substitute_assignment_with_substitutions():
    """Test _substitute_in_statement() with Assignment needing substitutions (covers lines 115-116)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    target = ast.Identifier(name="x", span=span)
    value = ast.Identifier(name="y", span=span)
    stmt = ast.Assignment(target=target, value=value, span=span)
    substitutions = {
        "x": ast.Identifier(name="a", span=span),
        "y": ast.IntLiteral(value=42, span=span)
    }
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.Assignment)
    assert isinstance(result.target, ast.Identifier)
    assert isinstance(result.value, ast.IntLiteral)
    assert result.value.value == 42


def test_substitute_if_stmt_with_substitutions():
    """Test _substitute_in_statement() with IfStmt needing substitutions (covers lines 120-124)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    condition = ast.Identifier(name="x", span=span)
    then_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.Identifier(name="y", span=span), span=span)],
        span=span
    )
    else_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.Identifier(name="z", span=span), span=span)],
        span=span
    )
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=else_block,
        span=span
    )
    substitutions = {
        "x": ast.BoolLiteral(value=True, span=span),
        "y": ast.IntLiteral(value=1, span=span),
        "z": ast.IntLiteral(value=2, span=span)
    }
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.IfStmt)
    assert isinstance(result.condition, ast.BoolLiteral)
    assert result.else_block is not None


def test_substitute_while_stmt_with_substitution():
    """Test _substitute_in_statement() with WhileStmt needing substitution (covers lines 134-135)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    condition = ast.Identifier(name="x", span=span)
    body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.Identifier(name="y", span=span), span=span)],
        span=span
    )
    stmt = ast.WhileStmt(condition=condition, body=body, span=span)
    substitutions = {
        "x": ast.BoolLiteral(value=True, span=span),
        "y": ast.IntLiteral(value=42, span=span)
    }
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.WhileStmt)
    assert isinstance(result.condition, ast.BoolLiteral)


def test_substitute_for_stmt_with_substitution():
    """Test _substitute_in_statement() with ForStmt needing substitution (covers lines 143-144)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    iterable = ast.Identifier(name="x", span=span)
    body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.Identifier(name="y", span=span), span=span)],
        span=span
    )
    stmt = ast.ForStmt(
        variable="i",
        iterable=iterable,
        body=body,
        span=span
    )
    substitutions = {
        "x": ast.Identifier(name="list", span=span),
        "y": ast.IntLiteral(value=42, span=span)
    }
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ForStmt)
    assert isinstance(result.iterable, ast.Identifier)


def test_substitute_match_stmt_with_substitutions():
    """Test _substitute_in_statement() with MatchStmt needing substitutions (covers lines 153-165)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    scrutinee = ast.Identifier(name="x", span=span)
    guard = ast.Identifier(name="y", span=span)
    arm_body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.Identifier(name="z", span=span), span=span)],
        span=span
    )
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=span),
        guard=guard,
        body=arm_body,
        span=span
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=span
    )
    substitutions = {
        "x": ast.IntLiteral(value=1, span=span),
        "y": ast.BoolLiteral(value=True, span=span),
        "z": ast.IntLiteral(value=42, span=span)
    }
    
    result = inliner._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.MatchStmt)
    assert isinstance(result.scrutinee, ast.IntLiteral)
    assert result.arms[0].guard is not None
    assert isinstance(result.arms[0].guard, ast.BoolLiteral)


def test_substitute_identifier_in_substitutions():
    """Test _substitute_in_expression() with Identifier that is in substitutions (covers line 184)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    identifier = ast.Identifier(name="x", span=span)
    substitution = ast.IntLiteral(value=42, span=span)
    substitutions = {"x": substitution}
    
    result = inliner._substitute_in_expression(identifier, substitutions)
    # Should return cloned substitution
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 42


def test_substitute_binop_with_substitutions():
    """Test _substitute_in_expression() with BinOp needing substitutions (covers lines 189-195)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    left = ast.Identifier(name="x", span=span)
    right = ast.Identifier(name="y", span=span)
    expr = ast.BinOp(op="+", left=left, right=right, span=span)
    substitutions = {
        "x": ast.IntLiteral(value=1, span=span),
        "y": ast.IntLiteral(value=2, span=span)
    }
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.BinOp)
    assert result.op == "+"
    assert isinstance(result.left, ast.IntLiteral)
    assert result.left.value == 1
    assert isinstance(result.right, ast.IntLiteral)
    assert result.right.value == 2


def test_substitute_unaryop_with_substitution():
    """Test _substitute_in_expression() with UnaryOp needing substitution (covers lines 199-203)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    operand = ast.Identifier(name="x", span=span)
    expr = ast.UnaryOp(op="-", operand=operand, span=span)
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.UnaryOp)
    assert result.op == "-"
    assert isinstance(result.operand, ast.IntLiteral)
    assert result.operand.value == 42


def test_substitute_function_call_with_substitutions():
    """Test _substitute_in_expression() with FunctionCall needing substitutions (covers lines 207-221)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    func = ast.Identifier(name="x", span=span)
    arg = ast.Identifier(name="y", span=span)
    ct_arg = ast.Identifier(name="z", span=span)
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[ct_arg],
        arguments=[arg],
        span=span
    )
    substitutions = {
        "x": ast.Identifier(name="f", span=span),
        "y": ast.IntLiteral(value=1, span=span),
        "z": ast.IntLiteral(value=2, span=span)
    }
    
    result = inliner._substitute_in_expression(call, substitutions)
    assert isinstance(result, ast.FunctionCall)
    assert len(result.arguments) == 1
    assert isinstance(result.arguments[0], ast.IntLiteral)
    assert result.arguments[0].value == 1
    assert len(result.compile_time_args) == 1
    assert isinstance(result.compile_time_args[0], ast.IntLiteral)
    assert result.compile_time_args[0].value == 2


def test_substitute_method_call_with_substitutions():
    """Test _substitute_in_expression() with MethodCall needing substitutions (covers lines 225-234)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    obj = ast.Identifier(name="x", span=span)
    arg = ast.Identifier(name="y", span=span)
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[arg],
        span=span
    )
    substitutions = {
        "x": ast.Identifier(name="obj", span=span),
        "y": ast.IntLiteral(value=42, span=span)
    }
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.MethodCall)
    assert result.method == "method"
    assert len(result.arguments) == 1
    assert isinstance(result.arguments[0], ast.IntLiteral)
    assert result.arguments[0].value == 42


def test_substitute_field_access_with_substitution():
    """Test _substitute_in_expression() with FieldAccess needing substitution (covers lines 238-242)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    obj = ast.Identifier(name="x", span=span)
    expr = ast.FieldAccess(object=obj, field="field", span=span)
    substitutions = {"x": ast.Identifier(name="obj", span=span)}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.FieldAccess)
    assert result.field == "field"
    assert isinstance(result.object, ast.Identifier)
    assert result.object.name == "obj"


def test_substitute_index_access_with_substitutions():
    """Test _substitute_in_expression() with IndexAccess needing substitutions (covers lines 246-251)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    obj = ast.Identifier(name="x", span=span)
    index = ast.Identifier(name="y", span=span)
    expr = ast.IndexAccess(object=obj, index=index, span=span)
    substitutions = {
        "x": ast.Identifier(name="list", span=span),
        "y": ast.IntLiteral(value=0, span=span)
    }
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.IndexAccess)
    assert isinstance(result.object, ast.Identifier)
    assert result.object.name == "list"
    assert isinstance(result.index, ast.IntLiteral)
    assert result.index.value == 0


def test_substitute_struct_literal_with_substitution():
    """Test _substitute_in_expression() with StructLiteral needing substitution (covers lines 255-262)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    field_expr = ast.Identifier(name="x", span=span)
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("field", field_expr)],
        span=span
    )
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.StructLiteral)
    assert result.struct_name == "Test"
    assert len(result.fields) == 1
    assert result.fields[0][0] == "field"
    assert isinstance(result.fields[0][1], ast.IntLiteral)
    assert result.fields[0][1].value == 42


def test_substitute_list_literal_with_substitution():
    """Test _substitute_in_expression() with ListLiteral needing substitution (covers lines 266-272)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    elem = ast.Identifier(name="x", span=span)
    expr = ast.ListLiteral(
        elements=[elem],
        span=span
    )
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.ListLiteral)
    assert len(result.elements) == 1
    assert isinstance(result.elements[0], ast.IntLiteral)
    assert result.elements[0].value == 42


def test_substitute_try_expr_with_substitution():
    """Test _substitute_in_expression() with TryExpr needing substitution (covers lines 276-279)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    inner = ast.Identifier(name="x", span=span)
    expr = ast.TryExpr(expression=inner, span=span)
    substitutions = {"x": ast.IntLiteral(value=42, span=span)}
    
    result = inliner._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.TryExpr)
    assert isinstance(result.expression, ast.IntLiteral)
    assert result.expression.value == 42


def test_estimate_block_size_with_if_else():
    """Test _estimate_block_size() with IfStmt that has else block (covers line 300)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    then_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    else_block = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=2, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.IfStmt(
                condition=ast.BoolLiteral(value=True, span=span),
                then_block=then_block,
                elif_clauses=[],
                else_block=else_block,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count if (1) + then (1) + else (1) = 3
    assert size == 3


def test_estimate_block_size_with_while():
    """Test _estimate_block_size() with WhileStmt (covers line 303)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.WhileStmt(
                condition=ast.BoolLiteral(value=True, span=span),
                body=body,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count while (1) + body (1) = 2
    assert size == 2


def test_estimate_block_size_with_for():
    """Test _estimate_block_size() with ForStmt (covers line 305)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    block = ast.Block(
        statements=[
            ast.ForStmt(
                variable="x",
                iterable=ast.Identifier(name="list", span=span),
                body=body,
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count for (1) + body (1) = 2
    assert size == 2


def test_estimate_block_size_with_match():
    """Test _estimate_block_size() with MatchStmt (covers lines 307-308)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    arm1_body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=1, span=span), span=span)],
        span=span
    )
    arm2_body = ast.Block(
        statements=[ast.ReturnStmt(value=ast.IntLiteral(value=2, span=span), span=span)],
        span=span
    )
    arm1 = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=span),
        guard=None,
        body=arm1_body,
        span=span
    )
    arm2 = ast.MatchArm(
        pattern=ast.IntLiteral(value=2, span=span),
        guard=None,
        body=arm2_body,
        span=span
    )
    block = ast.Block(
        statements=[
            ast.MatchStmt(
                scrutinee=ast.Identifier(name="x", span=span),
                arms=[arm1, arm2],
                span=span
            )
        ],
        span=span
    )
    
    size = inliner._estimate_block_size(block)
    # Should count match (1) + arm1 body (1) + arm2 body (1) = 3
    assert size == 3


def test_inline_parameter_closure_depth_tracking():
    """Test that inlining depth is properly tracked and decremented (covers lines 64, 70)"""
    inliner = ClosureInliner()
    span = Span("test.pyrite", 1, 1, 1, 10)
    closure = ast.ParameterClosure(
        params=[ast.Param(name="x", type_annotation=IntType(), span=span)],
        return_type=None,
        body=ast.Block(
            statements=[ast.ReturnStmt(value=ast.Identifier(name="x", span=span), span=span)],
            span=span
        ),
        span=span
    )
    
    # Depth should start at 0
    assert inliner.inlining_depth == 0
    
    arg = ast.IntLiteral(value=5, span=span)
    result = inliner.inline_parameter_closure(closure, [arg])
    
    # Depth should be back to 0 after inlining
    assert inliner.inlining_depth == 0
    assert len(result.statements) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

