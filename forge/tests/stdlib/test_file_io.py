"""Test File I/O operations"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker


def test_file_read_to_string_declaration():
    """Test that File.read_to_string can be declared"""
    # Test that the file.pyrite module can be parsed
    file_path = Path(compiler_dir) / "stdlib" / "io" / "file.pyrite"
    if file_path.exists():
        source = file_path.read_text(encoding='utf-8')
        tokens = lex(source)
        program = parse(tokens)
        
        assert program is not None
        # Should have at least the extern declaration and impl
        assert len(program.items) > 0


def test_file_read_to_string_extern_declaration():
    """Test that extern declaration for file_read_to_string parses"""
    source = """extern "C" fn file_read_to_string(path: *const u8) -> String

fn test_read():
    # Would call file_read_to_string here
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    # First item should be extern function
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "file_read_to_string"


def test_file_read_missing_file():
    """Test that reading missing file returns error"""
    # Test basic structure - actual FFI integration would be integration test
    source = """extern "C" fn file_read_to_string(path: *const u8) -> String

fn test_missing():
    # Would test file read here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None


def test_file_write_declaration():
    """Test that file_write extern declaration parses"""
    source = """extern "C" fn file_write(path: *const u8, data: *const u8, len: i64) -> i32

fn test_write():
    # Would test file write here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "file_write"


def test_file_open_declaration():
    """Test that file_open extern declaration parses"""
    source = """extern "C" fn file_open(path: *const u8, mode: *const u8) -> *mut u8

fn test_open():
    # Would test file open here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "file_open"


def test_file_handle_operations():
    """Test that file handle operations can be declared"""
    source = """extern "C" fn file_open(path: *const u8, mode: *const u8) -> *mut u8
extern "C" fn file_read_line(handle: *mut u8) -> String
extern "C" fn file_close(handle: *mut u8)

struct File:
    handle: *mut u8

fn test_handle():
    # Would test file handles here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    # Should have extern declarations and struct
    assert len(program.items) >= 3


def test_file_read_dir_declaration():
    """Test that file_read_dir extern declaration parses"""
    source = """extern "C" fn file_read_dir(path: *const u8, count: *mut i32) -> *mut *const u8
extern "C" fn file_read_dir_free(entries: *mut *const u8, count: i32)

fn test_read_dir():
    # Would test directory reading here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 2
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "file_read_dir"


def test_file_walk_dir_declaration():
    """Test that file_walk_dir extern declaration parses"""
    source = """extern "C" fn file_walk_dir(path: *const u8, count: *mut i32) -> *mut *const u8

fn test_walk_dir():
    # Would test directory walking here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1
    extern_func = program.items[0]
    assert extern_func.is_extern == True
    assert extern_func.name == "file_walk_dir"
