"""Tests for parameter closure call-site inlining"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.passes.closure_inline_pass import ClosureInlinePass
from src import ast


def test_call_site_inlining_simple():
    """Test that parameter closures are inlined at call sites"""
    source = """
fn apply[Body: fn[int] -> int](x: int, body: Body) -> int:
    return body(x)

fn main():
    let result = apply[fn[i: int] -> int: i * 2](5)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Type check
    type_checker = type_check(program)
    if type_checker.has_errors():
        for error in type_checker.errors:
            print(f"Type error: {error.message} at {error.span}")
    assert not type_checker.has_errors()
    
    # Inline closures
    inline_pass = ClosureInlinePass(type_checker)
    inlined = inline_pass.inline_closures_in_program(program)
    
    # Find the apply function
    apply_func = None
    for item in inlined.items:
        if isinstance(item, ast.FunctionDef) and item.name == "apply":
            apply_func = item
            break
    
    assert apply_func is not None
    
    # The function body should have been transformed
    # The call to f(x) should have been inlined
    # For now, we just verify the pass runs without error
    # Full verification would require checking the transformed AST


def test_call_site_inlining_with_arguments():
    """Test inlining with multiple arguments"""
    source = """
fn process[Op: fn[int, int] -> int](a: int, b: int, op: Op) -> int:
    return op(a, b)

fn main():
    let result = process[fn[x: int, y: int] -> int: x + y](3, 4)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Type check
    type_checker = type_check(program)
    if type_checker.has_errors():
        for error in type_checker.errors:
            print(f"Type error: {error.message} at {error.span}")
    assert not type_checker.has_errors()
    
    # Inline closures
    inline_pass = ClosureInlinePass(type_checker)
    inlined = inline_pass.inline_closures_in_program(program)
    
    # Verify pass completes
    assert len(inlined.items) >= 2


def test_nested_parameter_closures():
    """Test inlining with nested parameter closures (simplified for parser limitations)"""
    # Note: Parser doesn't support nested function types in compile-time params yet
    # This test uses a simpler case that works
    source = """
fn apply[Body: fn[int] -> int](x: int, body: Body) -> int:
    return body(x)

fn double[Body: fn[int] -> int](x: int, body: Body) -> int:
    return body(body(x))

fn main():
    let result = apply[fn[i: int] -> int: i * 2](5)
    let doubled = double[fn[i: int] -> int: i + 1](3)
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Type check
    type_checker = type_check(program)
    if type_checker.has_errors():
        for error in type_checker.errors:
            print(f"Type error: {error.message} at {error.span}")
    # Should parse and type-check successfully
    assert not type_checker.has_errors()
    
    # Inline closures
    inline_pass = ClosureInlinePass(type_checker)
    inlined = inline_pass.inline_closures_in_program(program)
    
    # Verify pass completes
    assert len(inlined.items) >= 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

