"""Tests for FFI (Foreign Function Interface)"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src import ast


def test_parse_extern_c_function():
    """Test parsing extern C function declaration"""
    source = """extern "C" fn strlen(s: *const u8) -> int
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.is_extern == True
    assert func.extern_abi == "C"
    assert func.name == "strlen"
    assert len(func.params) == 1
    assert func.params[0].name == "s"


def test_parse_extern_without_abi():
    """Test extern without ABI string defaults to C"""
    source = """extern fn malloc(size: int) -> *mut void
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.is_extern == True
    assert func.extern_abi == "C"  # Default


def test_parse_extern_no_return_type():
    """Test extern function with no return type (void)"""
    source = """extern "C" fn free(ptr: *mut void)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.is_extern == True
    assert func.return_type is None  # void


def test_parse_multiple_extern_functions():
    """Test multiple extern declarations"""
    source = """extern "C" fn strlen(s: *const u8) -> int
extern "C" fn strcmp(s1: *const u8, s2: *const u8) -> int
extern "C" fn free(ptr: *mut void)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 3
    assert all(func.is_extern for func in program.items)
    assert program.items[0].name == "strlen"
    assert program.items[1].name == "strcmp"
    assert program.items[2].name == "free"


def test_extern_function_type_checking():
    """Test that extern functions are registered in symbol table"""
    source = """extern "C" fn strlen(s: *const u8) -> int

fn main():
    let len = strlen("hello".as_ptr())
    print(len)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check should register extern function
    checker = type_check(program)
    
    # Verify strlen is registered
    strlen_symbol = checker.resolver.lookup_function("strlen")
    assert strlen_symbol is not None


def test_extern_with_struct_params():
    """Test extern function with struct parameters"""
    source = """struct Point:
    x: int
    y: int

extern "C" fn distance(p1: Point, p2: Point) -> f64
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Should parse without errors
    assert len(program.items) == 2
    func = program.items[1]
    assert func.is_extern == True
    assert len(func.params) == 2

