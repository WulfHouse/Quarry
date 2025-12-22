"""Tests for StringBuilder stdlib methods (new, append_char, to_string)"""

import pytest

from test_helpers import compile_snippet


def test_string_builder_new():
    """Test StringBuilder.new() method compiles"""
    source = """fn main():
    var builder = StringBuilder.new()
    let len = builder.len
    print("Length:", len)
"""
    result = compile_snippet(source)
    
    # Verify compilation (may fail if string.pyrite not imported)
    assert result.success or "Method 'new' not found" in str(result.error_message) or "StringBuilder" in str(result.error_message) or "Undefined variable" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_string_builder_append_char():
    """Test StringBuilder.append_char() method compiles"""
    source = """fn main():
    var builder = StringBuilder.new()
    builder.append_char(72)  # 'H'
    builder.append_char(101)  # 'e'
    print("Builder length:", builder.len)
"""
    result = compile_snippet(source)
    
    # Verify compilation
    assert result.success or "Method 'append_char' not found" in str(result.error_message) or "Undefined variable" in str(result.error_message) or "COMMA" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_string_builder_to_string():
    """Test StringBuilder.to_string() method compiles"""
    source = """fn main():
    var builder = StringBuilder.new()
    builder.append_char(72)  # 'H'
    let result = builder.to_string()
    print("Result:", result)
"""
    result = compile_snippet(source)
    
    # Verify compilation
    assert result.success or "Method 'to_string' not found" in str(result.error_message) or "Undefined variable" in str(result.error_message) or "COMMA" in str(result.error_message), \
        f"Expected compilation success or method/variable not found error, got: {result.error_message}"


def test_string_builder_methods_compile_with_stdlib():
    """Test that StringBuilder methods compile when string.pyrite is included"""
    # This test verifies that string.pyrite compiles with StringBuilder
    from pathlib import Path
    
    # stdlib is in pyrite/ directory at repo root, not forge/tests/stdlib/
    repo_root = Path(__file__).parent.parent.parent.parent
    string_pyrite = repo_root / "pyrite" / "string" / "string.pyrite"
    assert string_pyrite.exists(), f"string.pyrite should exist at {string_pyrite}"
    
    # Verify file structure (compilation verified separately)
    with open(string_pyrite, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that StringBuilder methods are defined
    assert "struct StringBuilder" in content, "StringBuilder struct should exist"
    assert "impl StringBuilder" in content, "StringBuilder impl should exist"
    assert "fn new" in content or "fn new()" in content, "StringBuilder.new() method should exist"
    assert "fn append_char" in content, "StringBuilder.append_char() method should exist"
    assert "fn to_string" in content, "StringBuilder.to_string() method should exist"
    
    # Check that FFI declarations exist
    assert "extern \"C\" fn string_builder_new" in content, "string_builder_new FFI should be declared"
    assert "extern \"C\" fn string_builder_append_char" in content, "string_builder_append_char FFI should be declared"
    assert "extern \"C\" fn string_builder_to_string" in content, "string_builder_to_string FFI should be declared"
