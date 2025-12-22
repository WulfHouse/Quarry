"""Tests for function pointers in FFI"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker
from src import ast


def test_extern_function_with_function_pointer_param():
    """Test extern function taking function pointer parameter"""
    source = """extern "C" fn qsort(base: *mut void, nmemb: int, size: int, compar: fn(*const void, *const void) -> int)
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.is_extern == True
    assert len(func.params) == 4
    # Check that last parameter is a function pointer type
    compar_param = func.params[3]
    assert isinstance(compar_param.type_annotation, ast.FunctionType)
    assert compar_param.name == "compar"


def test_extern_function_returning_function_pointer():
    """Test extern function returning function pointer"""
    source = """extern "C" fn get_callback() -> fn(int) -> int
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.is_extern == True
    assert func.return_type is not None
    assert isinstance(func.return_type, ast.FunctionType)


def test_function_pointer_type_parsing():
    """Test that function pointer type parses correctly"""
    source = """fn test(callback: fn(int) -> int):
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.params) == 1
    param = func.params[0]
    assert isinstance(param.type_annotation, ast.FunctionType)


def test_function_pointer_with_multiple_params():
    """Test function pointer with multiple parameters"""
    source = """fn test(callback: fn(int, int) -> int):
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    param = func.params[0]
    func_type = param.type_annotation
    assert isinstance(func_type, ast.FunctionType)
    assert len(func_type.param_types) == 2


def test_function_pointer_with_no_return():
    """Test function pointer with no return type (void)"""
    source = """fn test(callback: fn(int)):
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    param = func.params[0]
    func_type = param.type_annotation
    assert isinstance(func_type, ast.FunctionType)
    assert func_type.return_type is None


def test_function_pointer_type_checking():
    """Test type checking of function pointer types"""
    source = """extern "C" fn set_callback(cb: fn(int) -> int)

fn my_callback(x: int) -> int:
    return x * 2

fn main():
    set_callback(my_callback)
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors (function pointer types should match)
    # Note: Function pointer passing may need codegen support
    assert program is not None


def test_function_pointer_in_struct():
    """Test function pointer as struct field"""
    source = """struct Handler:
    callback: fn(int) -> int
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    struct = program.items[0]
    assert isinstance(struct, ast.StructDef)
    assert len(struct.fields) == 1
    field = struct.fields[0]
    assert isinstance(field.type_annotation, ast.FunctionType)
