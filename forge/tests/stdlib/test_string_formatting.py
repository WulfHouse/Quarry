"""Test string formatting"""
import pytest
import sys
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker


def test_format_extern_declaration():
    """Test that string_format extern declaration parses"""
    source = """extern "C" fn string_format(fmt: *const u8, argc: int, argv: *const *const u8) -> String

fn test_format():
    # Would test format here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "string_format"


def test_format_string_parsing():
    """Test that format string with {} placeholders can be parsed"""
    source = """fn format_example():
    let fmt = "Hello {}, value: {}"
    return fmt
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None


def test_string_from_int_declaration():
    """Test that string_from_int extern declaration parses"""
    source = """extern "C" fn string_from_int(value: i64) -> String

fn test_int():
    # Would test int to string conversion here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "string_from_int"


def test_string_from_float_declaration():
    """Test that string_from_float extern declaration parses"""
    source = """extern "C" fn string_from_float(value: f64) -> String

fn test_float():
    # Would test float to string conversion here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "string_from_float"


def test_string_from_bool_declaration():
    """Test that string_from_bool extern declaration parses"""
    source = """extern "C" fn string_from_bool(value: i8) -> String

fn test_bool():
    # Would test bool to string conversion here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "string_from_bool"
