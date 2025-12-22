"""Tests for compile-time parameters"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src import ast


def test_parse_compile_time_int_param():
    """Test parsing function with compile-time integer parameter"""
    source = """fn create_buffer[Size: int]() -> int:
    return Size
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "create_buffer"
    assert len(func.compile_time_params) == 1
    assert isinstance(func.compile_time_params[0], ast.CompileTimeIntParam)
    assert func.compile_time_params[0].name == "Size"


def test_parse_compile_time_bool_param():
    """Test parsing function with compile-time boolean parameter"""
    source = """fn process[DebugMode: bool](data: &[u8]):
    if DebugMode:
        print("Debug")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.compile_time_params) == 1
    assert isinstance(func.compile_time_params[0], ast.CompileTimeBoolParam)
    assert func.compile_time_params[0].name == "DebugMode"


def test_parse_mixed_params():
    """Test parsing function with both type and compile-time params"""
    source = """fn process[T, N: int](data: [T; N]) -> T:
    return data[0]
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.generic_params) == 1
    assert func.generic_params[0].name == "T"
    assert len(func.compile_time_params) == 1
    assert func.compile_time_params[0].name == "N"


def test_parse_struct_with_compile_time_params():
    """Test parsing struct with compile-time parameters"""
    source = """struct Matrix[Rows: int, Cols: int]:
    data: [f32; Rows]
"""
    tokens = lex(source)
    program = parse(tokens)
    
    struct = program.items[0]
    assert isinstance(struct, ast.StructDef)
    assert struct.name == "Matrix"
    assert len(struct.compile_time_params) == 2
    assert struct.compile_time_params[0].name == "Rows"
    assert struct.compile_time_params[1].name == "Cols"


def test_parse_function_call_with_compile_time_args():
    """Test parsing function call with compile-time arguments"""
    source = """fn main():
    let buf = create_buffer[256]()
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt, ast.VarDecl)
    call = stmt.initializer
    assert isinstance(call, ast.FunctionCall)
    assert len(call.compile_time_args) == 1
    # The compile-time arg should be an integer literal expression
    assert isinstance(call.compile_time_args[0], ast.IntLiteral)
    assert call.compile_time_args[0].value == 256


def test_parse_function_call_with_multiple_compile_time_args():
    """Test parsing function call with multiple compile-time arguments"""
    source = """fn main():
    let result = process[256, true](data)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    call = stmt.initializer
    assert isinstance(call, ast.FunctionCall)
    assert len(call.compile_time_args) == 2
    assert isinstance(call.compile_time_args[0], ast.IntLiteral)
    assert call.compile_time_args[0].value == 256
    assert isinstance(call.compile_time_args[1], ast.BoolLiteral)
    assert call.compile_time_args[1].value == True


def test_parse_regular_function_call_still_works():
    """Test that regular function calls (without compile-time args) still work"""
    source = """fn main():
    let result = process(data)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    call = stmt.initializer
    assert isinstance(call, ast.FunctionCall)
    assert len(call.compile_time_args) == 0  # No compile-time args
    assert len(call.arguments) == 1


def test_compile_time_params_with_type_params():
    """Test mixing type parameters and compile-time parameters"""
    source = """fn vector_add[T, N: int](a: int, b: int) -> int:
    return a + b
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert len(func.generic_params) == 1
    assert func.generic_params[0].name == "T"
    assert len(func.compile_time_params) == 1
    assert func.compile_time_params[0].name == "N"

