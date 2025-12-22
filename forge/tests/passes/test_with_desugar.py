"""Tests for with statement desugaring"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.passes.with_desugar_pass import WithDesugarPass
from src import ast


def test_with_desugars_to_let_and_defer():
    """Test that with statement desugars to let + defer"""
    source = """
fn main():
    with file = try File.open("test.txt"):
        print(file)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Desugar
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    # Check that with statement is gone
    func = desugared.items[0]
    assert isinstance(func, ast.FunctionDef)
    
    # Should have: let, defer, print
    assert len(func.body.statements) >= 3
    
    # First should be let
    assert isinstance(func.body.statements[0], ast.VarDecl)
    let_stmt = func.body.statements[0]
    assert let_stmt.name == "file"
    assert not let_stmt.mutable  # let is immutable
    
    # Second should be defer
    assert isinstance(func.body.statements[1], ast.DeferStmt)
    defer_stmt = func.body.statements[1]
    assert len(defer_stmt.body.statements) == 1
    assert isinstance(defer_stmt.body.statements[0], ast.ExpressionStmt)
    
    # Defer should call file.close()
    expr_stmt = defer_stmt.body.statements[0]
    assert isinstance(expr_stmt.expression, ast.MethodCall)
    method_call = expr_stmt.expression
    assert isinstance(method_call.object, ast.Identifier)
    assert method_call.object.name == "file"
    assert method_call.method == "close"


def test_nested_with_desugars():
    """Test nested with statements desugar correctly"""
    source = """
fn main():
    with file = try File.open("test.txt"):
        with conn = try Database.connect():
            process(file, conn)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Desugar
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    # Should have: let file, defer file.close(), let conn, defer conn.close(), process
    assert len(func.body.statements) >= 5
    
    # Check first with (file)
    assert isinstance(func.body.statements[0], ast.VarDecl)
    assert func.body.statements[0].name == "file"
    assert isinstance(func.body.statements[1], ast.DeferStmt)
    
    # Check second with (conn) - should be in the body of the first with
    # Actually, after desugaring, the second with's statements are inlined
    # So we should have: let file, defer file.close(), let conn, defer conn.close(), process
    assert isinstance(func.body.statements[2], ast.VarDecl)
    assert func.body.statements[2].name == "conn"


def test_with_in_if_desugars():
    """Test with statement inside if desugars"""
    source = """
fn main():
    if true:
        with file = try File.open("test.txt"):
            print(file)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Desugar
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    if_stmt = func.body.statements[0]
    assert isinstance(if_stmt, ast.IfStmt)
    
    # Then block should have: let, defer, print
    assert len(if_stmt.then_block.statements) >= 3
    assert isinstance(if_stmt.then_block.statements[0], ast.VarDecl)
    assert isinstance(if_stmt.then_block.statements[1], ast.DeferStmt)


def test_with_in_if_with_else_desugars():
    """Test with statement inside if with else block desugars (covers line 80-81)"""
    source = """
fn main():
    if true:
        with file = try File.open("test.txt"):
            print(file)
    else:
        print("no file")
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    if_stmt = func.body.statements[0]
    assert isinstance(if_stmt, ast.IfStmt)
    assert if_stmt.else_block is not None


def test_with_in_if_with_elif_desugars():
    """Test with statement inside if with elif clauses desugars (covers line 78)"""
    source = """
fn main():
    if false:
        pass
    elif true:
        with file = try File.open("test.txt"):
            print(file)
    else:
        pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    if_stmt = func.body.statements[0]
    assert isinstance(if_stmt, ast.IfStmt)
    assert len(if_stmt.elif_clauses) > 0
    # Check that elif block has desugared with statement
    elif_block = if_stmt.elif_clauses[0][1]
    assert len(elif_block.statements) >= 3  # let, defer, print


def test_with_in_while_desugars():
    """Test with statement inside while loop desugars (covers line 90-94)"""
    source = """
fn main():
    while true:
        with file = try File.open("test.txt"):
            print(file)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    while_stmt = func.body.statements[0]
    assert isinstance(while_stmt, ast.WhileStmt)
    assert len(while_stmt.body.statements) >= 3  # let, defer, print


def test_with_in_for_desugars():
    """Test with statement inside for loop desugars (covers line 97-102)"""
    source = """
fn main():
    for i in 0..10:
        with file = try File.open("test.txt"):
            print(file)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    for_stmt = func.body.statements[0]
    assert isinstance(for_stmt, ast.ForStmt)
    assert len(for_stmt.body.statements) >= 3  # let, defer, print


def test_with_in_match_desugars():
    """Test with statement inside match statement desugars (covers line 105-117)"""
    source = """
fn main():
    match x:
        1:
            with file = try File.open("test.txt"):
                print(file)
        _:
            pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    match_stmt = func.body.statements[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    # First arm should have desugared with statement
    assert len(match_stmt.arms[0].body.statements) >= 3  # let, defer, print


def test_with_in_unsafe_block_desugars():
    """Test with statement inside unsafe block desugars (covers line 119-124)"""
    source = """
fn main():
    unsafe:
        with file = try File.open("test.txt"):
            print(file)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    desugar_pass = WithDesugarPass()
    desugared = desugar_pass.desugar_program(program)
    
    func = desugared.items[0]
    unsafe_block = func.body.statements[0]
    assert isinstance(unsafe_block, ast.UnsafeBlock)
    assert len(unsafe_block.body.statements) >= 3  # let, defer, print


def test_desugar_program_with_non_function_items():
    """Test desugar_program() with non-function items (covers line 34)"""
    from src.frontend.tokens import Span
    desugar_pass = WithDesugarPass()
    
    # Create program with struct (non-function item)
    struct_def = ast.StructDef(
        name="Test",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    program = ast.Program(
        imports=[],
        items=[struct_def],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    desugared = desugar_pass.desugar_program(program)
    # Struct should be preserved
    assert len(desugared.items) == 1
    assert isinstance(desugared.items[0], ast.StructDef)


def test_desugar_function_preserves_attributes():
    """Test _desugar_function() preserves function attributes (covers lines 52-54)"""
    from src.frontend.tokens import Span
    desugar_pass = WithDesugarPass()
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        is_unsafe=True,
        is_extern=True,
        extern_abi="C",
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    desugared = desugar_pass._desugar_function(func)
    assert desugared.is_unsafe == True
    assert desugared.is_extern == True
    assert desugared.extern_abi == "C"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

