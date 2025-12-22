"""Tests for try operator (error propagation)"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.fast]  # Integration tests that are fast enough for fast lane
from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker
from src.types import GenericType, INT, STRING


def test_try_operator_with_result_ok():
    """Test try operator with Result.Ok value"""
    source = """enum Result[T, E]:
    Ok(value: T)
    Err(error: E)

fn get_value() -> Result[int, String]:
    return Result.Ok(42)

fn main():
    let x = try get_value()
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"


def test_try_operator_with_result_err():
    """Test try operator with Result.Err value"""
    source = """enum Result[T, E]:
    Ok(value: T)
    Err(error: E)

fn get_error() -> Result[int, String]:
    return Result.Err("error")

fn main():
    let x = try get_error()
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors (try unwraps Result)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"


def test_try_operator_type_inference():
    """Test that try operator returns the Ok type (T) from Result[T, E]"""
    source = """enum Result[T, E]:
    Ok(value: T)
    Err(error: E)

fn get_int() -> Result[int, String]:
    return Result.Ok(42)

fn main():
    let x = try get_int()
    # x should be int, not Result[int, String]
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"


def test_try_operator_error_on_non_result():
    """Test that try operator errors on non-Result types"""
    source = """fn get_int() -> int:
    return 42

fn main():
    let x = try get_int()
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should have type error: try can only be used on Result types
    assert type_checker.has_errors(), "Expected type error for try on non-Result type"
    errors = [str(e) for e in type_checker.errors]
    assert any("Result" in err for err in errors), f"Expected Result-related error, got: {errors}"


def test_try_operator_in_nested_function():
    """Test try operator in nested function that returns Result"""
    source = """enum Result[T, E]:
    Ok(value: T)
    Err(error: E)

fn inner() -> Result[int, String]:
    return Result.Ok(10)

fn outer() -> Result[int, String]:
    let x = try inner()
    return Result.Ok(x + 5)

fn main():
    let result = outer()
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"


def test_try_operator_with_different_result_types():
    """Test try operator with different Result type parameters"""
    source = """enum Result[T, E]:
    Ok(value: T)
    Err(error: E)

fn get_string() -> Result[String, int]:
    return Result.Ok("hello")

fn get_int() -> Result[int, String]:
    return Result.Ok(42)

fn main():
    let s = try get_string()
    let i = try get_int()
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"


def test_try_operator_parsing():
    """Test that try operator parses correctly"""
    source = """fn test():
    let x = try some_function()
"""
    
    tokens = lex(source)
    
    # Check that TRY token is present
    try_tokens = [t for t in tokens if t.type.name == "TRY"]
    assert len(try_tokens) > 0, "TRY token should be present"
    
    program = parse(tokens)
    
    # Should parse without errors
    assert program is not None
