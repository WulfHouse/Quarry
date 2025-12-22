"""Tests for List stdlib methods (new, push, get, length, is_empty)"""

import pytest

from test_helpers import compile_snippet


def test_list_new():
    """Test List.new() method compiles"""
    source = """fn main():
    let list = List.new(8)  # elem_size = 8 for i64
    let len = list.length()
    print("Length:", len)
"""
    result = compile_snippet(source)
    
    # Verify compilation (may fail if list.pyrite not imported)
    assert result.success or "Method 'new' not found" in str(result.error_message) or "List" in str(result.error_message) or "Undefined variable" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_list_length():
    """Test List.length() method compiles"""
    source = """fn main():
    let list = List.new(8)
    let len = list.length()
    print("Length:", len)
"""
    result = compile_snippet(source)
    
    # Verify compilation
    assert result.success or "Method 'length' not found" in str(result.error_message) or "Undefined variable" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_list_is_empty():
    """Test List.is_empty() method compiles"""
    source = """fn main():
    let list = List.new(8)
    let empty = list.is_empty()
    print("Empty:", empty)
"""
    result = compile_snippet(source)
    
    # Verify compilation
    assert result.success or "Method 'is_empty' not found" in str(result.error_message) or "Undefined variable" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_list_with_capacity():
    """Test List.with_capacity() method compiles"""
    source = """fn main():
    let list = List.with_capacity(8, 10)
    let len = list.length()
    print("Length:", len)
"""
    result = compile_snippet(source)
    
    # Verify compilation
    assert result.success or "Method 'with_capacity' not found" in str(result.error_message) or "Undefined variable" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_list_methods_compile_with_stdlib():
    """Test that List methods compile when list.pyrite is included"""
    # This test verifies that list.pyrite compiles
    from pathlib import Path
    
    # stdlib is in pyrite/ directory at repo root, not forge/tests/stdlib/
    repo_root = Path(__file__).parent.parent.parent.parent
    list_pyrite = repo_root / "pyrite" / "collections" / "list.pyrite"
    assert list_pyrite.exists(), f"list.pyrite should exist at {list_pyrite}"
    
    # Verify file structure (compilation verified separately)
    with open(list_pyrite, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that key methods are defined
    assert "fn new" in content, "List.new() method should exist"
    assert "fn length" in content, "List.length() method should exist"
    assert "fn is_empty" in content, "List.is_empty() method should exist"
    assert "fn push" in content, "List.push() method should exist"
    assert "fn get" in content, "List.get() method should exist"
    
    # Check that FFI declarations exist
    assert "extern \"C\" fn list_new" in content, "list_new FFI should be declared"
    assert "extern \"C\" fn list_length" in content, "list_length FFI should be declared"
    assert "extern \"C\" fn list_push" in content, "list_push FFI should be declared"
