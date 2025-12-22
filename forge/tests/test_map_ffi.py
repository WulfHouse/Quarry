"""Tests for Map FFI integration"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker
from src import ast


def test_map_ffi_extern_declarations():
    """Test extern declarations for Map C functions"""
    source = """extern "C" fn map_new(key_size: i64, value_size: i64) -> Map
extern "C" fn map_insert(map: *mut Map, key: *const void, value: *const void)
extern "C" fn map_get(map: *const Map, key: *const void) -> *const void
extern "C" fn map_contains(map: *const Map, key: *const void) -> i8
extern "C" fn map_length(map: *const Map) -> i64
extern "C" fn map_drop(map: *mut Map)
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 6
    assert all(isinstance(item, ast.FunctionDef) and item.is_extern for item in program.items)
    assert program.items[0].name == "map_new"
    assert program.items[1].name == "map_insert"
    assert program.items[2].name == "map_get"
    assert program.items[3].name == "map_contains"
    assert program.items[4].name == "map_length"
    assert program.items[5].name == "map_drop"


def test_map_struct_definition():
    """Test Map struct definition"""
    source = """struct Map[K, V]:
    _c_map: *mut void
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    struct = program.items[0]
    assert isinstance(struct, ast.StructDef)
    assert struct.name == "Map"
    assert len(struct.generic_params) == 2


def test_map_struct_definition():
    """Test Map struct with generic parameters"""
    source = """struct Map[K, V]:
    _c_map: *mut void
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    struct = program.items[0]
    assert isinstance(struct, ast.StructDef)
    assert struct.name == "Map"
    assert len(struct.generic_params) == 2


def test_map_ffi_function_pointers():
    """Test that Map FFI functions can use function pointers if needed"""
    source = """extern "C" fn map_new(key_size: i64, value_size: i64) -> Map
extern "C" fn map_with_callback(callback: fn(*const void) -> i64) -> Map
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    assert all(isinstance(item, ast.FunctionDef) and item.is_extern for item in program.items)


def test_map_ffi_completeness():
    """Test that all required Map FFI functions are declared"""
    source = """extern "C" fn map_new(key_size: i64, value_size: i64) -> Map
extern "C" fn map_insert(map: *mut Map, key: *const void, value: *const void)
extern "C" fn map_get(map: *const Map, key: *const void) -> *const void
extern "C" fn map_contains(map: *const Map, key: *const void) -> i8
extern "C" fn map_length(map: *const Map) -> i64
extern "C" fn map_drop(map: *mut Map)
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    # All FFI functions should parse
    assert len(program.items) == 6
    func_names = [item.name for item in program.items]
    assert "map_new" in func_names
    assert "map_insert" in func_names
    assert "map_get" in func_names
    assert "map_contains" in func_names
    assert "map_length" in func_names
    assert "map_drop" in func_names
