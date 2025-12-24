"""Tests for extern functions with bodies"""

import pytest
from src.frontend import lex, parse
from src import ast


def test_extern_function_with_body():
    """Test extern function with body (FFI wrapper)"""
    source = """extern "C" fn compare_versions(v1: *const u8, v1_len: i64, v2: *const u8, v2_len: i64) -> i32:
    return version_compare_c(v1, v1_len, v2, v2_len)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.is_extern == True
    assert func.extern_abi == "C"
    assert func.name == "compare_versions"
    assert len(func.body.statements) == 1
    assert isinstance(func.body.statements[0], ast.ReturnStmt)


def test_extern_function_declaration_only():
    """Test extern function without body (declaration only)"""
    source = """extern "C" fn strlen(s: *const u8) -> int
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.is_extern == True
    assert len(func.body.statements) == 0  # Empty body for declaration


def test_extern_function_mixed():
    """Test mix of extern declarations and extern functions with bodies"""
    source = """extern "C" fn strlen(s: *const u8) -> int
extern "C" fn wrapper(x: i32) -> i32:
    return x + 1
extern "C" fn free(ptr: *mut void)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 3
    assert program.items[0].is_extern == True
    assert len(program.items[0].body.statements) == 0  # Declaration only
    assert program.items[1].is_extern == True
    assert len(program.items[1].body.statements) == 1  # Has body
    assert program.items[2].is_extern == True
    assert len(program.items[2].body.statements) == 0  # Declaration only

