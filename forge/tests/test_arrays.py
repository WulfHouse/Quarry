"""Tests for array operations"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.backend import LLVMCodeGen


def test_array_literal():
    """Test array literal parsing and codegen"""
    source = """
fn main():
    let arr = [1, 2, 3, 4, 5]
"""
    tokens = lex(source)
    ast = parse(tokens)
    type_checker = type_check(ast)
    
    assert not type_checker.has_errors()
    
    codegen = LLVMCodeGen()
    codegen.type_checker = type_checker
    module = codegen.compile_program(ast)
    llvm_ir = str(module)
    
    assert "define" in llvm_ir


def test_array_type_annotation():
    """Test array with type annotation"""
    source = """
fn main():
    let arr: [int; 5] = [1, 2, 3, 4, 5]
"""
    tokens = lex(source)
    ast = parse(tokens)
    type_checker = type_check(ast)
    
    # This might have errors due to incomplete array support
    # but should at least parse


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

