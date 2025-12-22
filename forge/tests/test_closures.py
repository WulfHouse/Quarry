"""Tests for two-tier closure model"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src import ast


def test_parse_parameter_closure_single_param():
    """Test parsing parameter closure with single parameter"""
    source = """fn main():
    let x = fn[i: int]: i * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    assert isinstance(closure, ast.ParameterClosure)
    assert len(closure.params) == 1
    assert closure.params[0].name == "i"


def test_parse_parameter_closure_with_return_type():
    """Test parsing parameter closure with explicit return type"""
    source = """fn main():
    let x = fn[i: int] -> int: i * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    assert isinstance(closure, ast.ParameterClosure)
    assert closure.return_type is not None


def test_parse_runtime_closure_single_param():
    """Test parsing runtime closure with single parameter"""
    source = """fn main():
    let filter = fn(x: int) -> bool: x > 10
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    assert isinstance(closure, ast.RuntimeClosure)
    assert len(closure.params) == 1
    assert closure.params[0].name == "x"


def test_parse_runtime_closure_no_params():
    """Test parsing runtime closure with no parameters"""
    source = """fn main():
    let callback = fn() -> int: 42
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    assert isinstance(closure, ast.RuntimeClosure)
    assert len(closure.params) == 0


def test_parse_parameter_closure_in_function_call():
    """Test parameter closure as function argument"""
    source = """fn main():
    vectorize(10, fn[i: int]: data[i])
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    call = stmt.expression
    assert isinstance(call, ast.FunctionCall)
    assert len(call.arguments) == 2
    # Second argument should be parameter closure
    assert isinstance(call.arguments[1], ast.ParameterClosure)


def test_parse_runtime_closure_in_function_call():
    """Test runtime closure as function argument"""
    source = """fn main():
    filter(data, fn(x: int) -> bool: x > 0)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    call = stmt.expression
    assert isinstance(call, ast.FunctionCall)
    assert len(call.arguments) == 2
    # Second argument should be runtime closure
    assert isinstance(call.arguments[1], ast.RuntimeClosure)


def test_parameter_closure_multiple_params():
    """Test parameter closure with multiple parameters"""
    source = """fn main():
    let f = fn[x: int, y: int]: x + y
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    assert isinstance(closure, ast.ParameterClosure)
    assert len(closure.params) == 2
    assert closure.params[0].name == "x"
    assert closure.params[1].name == "y"


def test_runtime_closure_multiple_params():
    """Test runtime closure with multiple parameters"""
    source = """fn main():
    let f = fn(x: int, y: int) -> int: x + y
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    closure = stmt.initializer
    assert isinstance(closure, ast.RuntimeClosure)
    assert len(closure.params) == 2


def test_distinguish_parameter_vs_runtime_closure():
    """Test that parser correctly distinguishes closure types"""
    source = """fn main():
    let param_closure = fn[i: int]: i * 2
    let runtime_closure = fn(x: int) -> int: x * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt1 = func.body.statements[0]
    stmt2 = func.body.statements[1]
    
    # First should be parameter closure
    assert isinstance(stmt1.initializer, ast.ParameterClosure)
    # Second should be runtime closure
    assert isinstance(stmt2.initializer, ast.RuntimeClosure)

