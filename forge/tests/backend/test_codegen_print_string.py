"""Tests for print() function with string literals code generation"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests (IR generation)

from test_helpers import compile_snippet


def test_print_string_literal():
    """Test generating code for print() with string literal"""
    source = """fn main():
    print("Hello, world!")
"""
    result = compile_snippet(source)
    
    # Check that compilation succeeded
    assert result.success, f"Compilation failed: {result.error_message}"
    assert result.llvm_ir is not None
    
    # Check that IR was generated
    assert "define" in result.llvm_ir
    assert "main" in result.llvm_ir
    # Should have printf call
    assert "printf" in result.llvm_ir.lower()


def test_print_string_variable():
    """Test generating code for print() with string variable"""
    source = """fn main():
    let msg = "Test message"
    print(msg)
"""
    result = compile_snippet(source)
    
    # Check that compilation succeeded
    assert result.success, f"Compilation failed: {result.error_message}"
    assert result.llvm_ir is not None
    
    # Check that IR was generated
    assert "define" in result.llvm_ir
    assert "main" in result.llvm_ir
    assert "printf" in result.llvm_ir.lower()


def test_print_multiple_strings():
    """Test generating code for multiple print() calls with strings"""
    source = """fn main():
    print("First")
    print("Second")
    print("Third")
"""
    result = compile_snippet(source)
    
    # Check that compilation succeeded
    assert result.success, f"Compilation failed: {result.error_message}"
    assert result.llvm_ir is not None
    
    # Check that IR was generated
    assert "define" in result.llvm_ir
    assert "main" in result.llvm_ir
    # Should have multiple printf calls
    assert result.llvm_ir.lower().count("printf") >= 3
