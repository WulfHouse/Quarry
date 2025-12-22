"""Test Path operations"""
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


def test_path_extern_declarations():
    """Test that Path extern declarations parse"""
    source = """extern "C" fn path_join(base: *const u8, other: *const u8) -> String
extern "C" fn path_parent(path: *const u8) -> String
extern "C" fn path_file_name(path: *const u8) -> String
extern "C" fn path_exists(path: *const u8) -> i8
extern "C" fn path_is_file(path: *const u8) -> i8
extern "C" fn path_is_dir(path: *const u8) -> i8

fn test_path():
    # Would test path operations here when FFI is working
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 6


def test_path_struct_declaration():
    """Test that Path struct can be declared"""
    source = """struct Path:
    data: String

fn test_path_struct():
    # Would test Path struct here
    return
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) >= 1


def test_path_impl_declaration():
    """Test that Path impl block can be declared"""
    source = """struct Path:
    data: String

impl Path:
    fn new(path: String) -> Path:
        return Path { data: path }
    
    fn join(&self, other: &String) -> Path:
        return Path { data: string_new("") }
    
    fn exists(&self) -> bool:
        return false
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    # Should have struct and impl
    assert len(program.items) >= 2
