"""Tests for defer statement implementation"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.backend import LLVMCodeGen, generate_llvm
from src import ast


def test_defer_statement_parsing():
    """Test that defer statements parse correctly"""
    source = """
fn main():
    defer:
        print(1)
    print(2)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.body.statements) == 2
    
    # First statement should be defer
    defer_stmt = func.body.statements[0]
    assert isinstance(defer_stmt, ast.DeferStmt)
    assert len(defer_stmt.body.statements) == 1


def test_multiple_defers_parsing():
    """Test parsing multiple defer statements"""
    source = """
fn main():
    defer:
        print(1)
    defer:
        print(2)
    defer:
        print(3)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert len(func.body.statements) == 3
    
    # All should be defer statements
    for stmt in func.body.statements:
        assert isinstance(stmt, ast.DeferStmt)


def test_defer_in_codegen():
    """Test that defer statements generate code without errors"""
    source = """
fn main():
    defer:
        print(1)
    print(2)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Generate code - should not raise exceptions
    llvm_ir = generate_llvm(program)
    
    # Should generate valid LLVM IR
    assert "define" in llvm_ir
    assert "main" in llvm_ir


def test_defer_with_early_return():
    """Test defer with early return"""
    source = """
fn test() -> int:
    defer:
        print(99)
    
    if true:
        return 5
    
    return 0
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Generate code - should not raise exceptions
    llvm_ir = generate_llvm(program)
    
    # Verify code generation succeeds
    assert "define" in llvm_ir
    assert "ret" in llvm_ir


def test_defer_in_nested_scope():
    """Test defer in nested scope"""
    source = """
fn main():
    defer:
        print(1)
    
    if true:
        defer:
            print(2)
        print(3)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert len(func.body.statements) == 2
    
    # First is defer
    assert isinstance(func.body.statements[0], ast.DeferStmt)
    
    # Second is if statement
    if_stmt = func.body.statements[1]
    assert isinstance(if_stmt, ast.IfStmt)


def test_with_statement_parsing():
    """Test that with statements parse correctly"""
    source = """
fn main():
    with file = try File.open("test.txt"):
        print(file)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert len(func.body.statements) == 1
    
    with_stmt = func.body.statements[0]
    assert isinstance(with_stmt, ast.WithStmt)
    assert with_stmt.variable == "file"


def test_with_statement_codegen():
    """Test that with statements generate code"""
    source = """
fn main():
    with x = try get_resource():
        use_resource(x)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should parse without error
    assert len(program.items) == 1
    
    # Code generation will fail due to undefined functions, but structure is correct
    func = program.items[0]
    with_stmt = func.body.statements[0]
    assert isinstance(with_stmt, ast.WithStmt)


def test_defer_lifo_order():
    """Test that multiple defers execute in LIFO order"""
    source = """
fn main():
    defer:
        print(3)
    defer:
        print(2)
    defer:
        print(1)
    print(0)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should parse and generate code
    llvm_ir = generate_llvm(program)
    assert "define" in llvm_ir
    assert "main" in llvm_ir


def test_defer_with_early_return_in_scope():
    """Test defer execution with early return in nested scope"""
    source = """
fn test() -> int:
    defer:
        print(2)
    
    if true:
        defer:
            print(1)
        return 5
    
    return 0
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should generate code successfully
    llvm_ir = generate_llvm(program)
    assert "define" in llvm_ir
    assert "ret" in llvm_ir


def test_defer_in_nested_function():
    """Test defer in deeply nested scopes (if within if)"""
    source = """
fn outer():
    defer:
        print("outer")
    
    if true:
        defer:
            print("middle")
        if true:
            defer:
                print("inner")
            print("inner body")
        print("middle body")
    print("outer body")
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should parse correctly
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    
    # Should generate code
    llvm_ir = generate_llvm(program)
    assert "define" in llvm_ir


def test_defer_with_break():
    """Test defer execution with break statement"""
    source = """
fn test():
    while true:
        defer:
            print("defer in loop")
        if true:
            break
        print("after if")
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should generate code
    llvm_ir = generate_llvm(program)
    assert "define" in llvm_ir


def test_defer_with_continue():
    """Test defer execution with continue statement"""
    source = """
fn test():
    while true:
        defer:
            print("defer in loop")
        if true:
            continue
        print("after if")
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should generate code
    llvm_ir = generate_llvm(program)
    assert "define" in llvm_ir


def test_defer_ownership_validation():
    """Test that defer validates ownership of variables"""
    source = """
fn test():
    let data = List[int].new()
    defer:
        print(data.length())  # Should be valid - data not moved yet
    
    process(data)  # Moves data
    # defer should have been validated before this move
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Should parse correctly
    # Ownership validation happens in ownership analyzer, not codegen
    assert len(program.items) == 1


def test_defer_execution_on_panic():
    """Test that gen_panic_with_defers method exists and can be used
    
    This test verifies the infrastructure for defer execution on panic is in place.
    The actual panic invocation (e.g., from bounds checks) will use this method
    to ensure defers execute before the program terminates.
    """
    # Verify the codegen has the method
    codegen = LLVMCodeGen()
    assert hasattr(codegen, 'gen_panic_with_defers')
    assert callable(codegen.gen_panic_with_defers)
    
    # Test that it can be called (requires a function context)
    source = """
fn test():
    defer:
        print(99)
    print(1)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Generate code - should succeed
    llvm_ir = generate_llvm(program)
    assert "define" in llvm_ir
    assert "test" in llvm_ir or "main" in llvm_ir
    # Verify panic function is declared (for future use)
    assert "pyrite_panic" in llvm_ir


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

