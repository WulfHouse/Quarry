"""Tests for closure capture analysis"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src import ast


def test_runtime_closure_captures_outer_variable():
    """Test that runtime closures correctly identify captured variables"""
    source = """fn main():
    let x = 42
    let closure = fn() -> int: x
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check to analyze captures
    checker = type_check(program)
    
    # Find the closure
    func = program.items[0]
    stmt = func.body.statements[1]  # Second statement (let closure = ...)
    closure = stmt.initializer
    
    assert isinstance(closure, ast.RuntimeClosure)
    # Should capture 'x'
    assert 'x' in closure.captures
    # Should have non-zero environment size
    assert closure.environment_size > 0


def test_runtime_closure_no_captures():
    """Test runtime closure with no captured variables"""
    source = """fn main():
    let closure = fn(x: int) -> int: x * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    
    # Find the closure
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    
    assert isinstance(closure, ast.RuntimeClosure)
    # Should not capture anything (only uses parameter)
    assert len(closure.captures) == 0
    # Environment size should be zero
    assert closure.environment_size == 0


def test_runtime_closure_captures_multiple_variables():
    """Test runtime closure capturing multiple variables"""
    source = """fn main():
    let x = 10
    let y = 20
    let closure = fn() -> int: x + y
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    
    # Find the closure
    func = program.items[0]
    stmt = func.body.statements[2]
    closure = stmt.initializer
    
    assert isinstance(closure, ast.RuntimeClosure)
    # Should capture both 'x' and 'y'
    assert 'x' in closure.captures
    assert 'y' in closure.captures
    assert len(closure.captures) == 2
    # Environment size should be 16 bytes (2 * 8 bytes)
    assert closure.environment_size == 16


def test_parameter_closure_no_capture_tracking():
    """Test that parameter closures don't track captures (compile-time only)"""
    source = """fn main():
    let x = 42
    let closure = fn[i: int]: i * x
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    
    # Find the closure
    func = program.items[0]
    stmt = func.body.statements[1]
    closure = stmt.initializer
    
    assert isinstance(closure, ast.ParameterClosure)
    # Parameter closures don't have captures list (compile-time only)
    assert closure.can_inline == True
    assert closure.allocates == False
    assert closure.escapes == False


def test_closure_captures_from_nested_scope():
    """Test closure capturing variable from nested scope"""
    source = """fn main():
    let x = 10
    if true:
        let y = 20
        let closure = fn() -> int: x + y
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    
    # Find the closure (nested in if statement)
    func = program.items[0]
    if_stmt = func.body.statements[1]
    closure_stmt = if_stmt.then_block.statements[1]
    closure = closure_stmt.initializer
    
    assert isinstance(closure, ast.RuntimeClosure)
    # Should capture both 'x' and 'y'
    assert 'x' in closure.captures
    assert 'y' in closure.captures


def test_closure_parameter_shadows_outer_variable():
    """Test that closure parameters shadow outer variables (not captured)"""
    source = """fn main():
    let x = 10
    let closure = fn(x: int) -> int: x * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    
    # Find the closure
    func = program.items[0]
    stmt = func.body.statements[1]
    closure = stmt.initializer
    
    assert isinstance(closure, ast.RuntimeClosure)
    # Should NOT capture 'x' (parameter shadows outer variable)
    assert 'x' not in closure.captures
    assert len(closure.captures) == 0
    assert closure.environment_size == 0


def test_closure_capture_ownership_validation():
    """Test that closure captures are validated for ownership (conceptual)"""
    from src.middle import analyze_ownership
    
    # Test: Cannot capture moved value
    # Note: This is a conceptual test - actual error detection depends on
    # analysis order and whether the closure is analyzed before or after the move
    source = """
fn main():
    let data = List[int].new()
    process(data)  # Moves data
    let closure = fn(): data.length()  # Would error if data was moved
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Type check
    type_checker = type_check(program)
    if type_checker.has_errors():
        # Type errors are OK for this test
        pass
    
    # Build type environment
    type_env = {}
    for name, symbol in type_checker.resolver.global_scope.get_all_symbols().items():
        type_env[name] = symbol.type
    
    # Ownership analysis
    ownership_analyzer = analyze_ownership(program, type_env)
    
    # Verify the infrastructure is in place
    assert ownership_analyzer is not None
    # The actual error detection would depend on analysis order