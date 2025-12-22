import pytest
from src.frontend import lex, parse
from src.middle import type_check
from src.backend import generate_llvm
import subprocess
import os
from pathlib import Path

@pytest.mark.integration
def test_struct_field_assignment():
    """Test that we can assign to a struct field"""
    source = """struct Point:
    x: int
    y: int

fn main() -> int:
    var p = Point{x: 1, y: 2}
    p.x = 10
    return p.x - 10
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    # Pass the type checker to the codegen
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that insert_value is in the IR
    assert "insertvalue" in llvm_ir

@pytest.mark.integration
def test_array_index_assignment():
    """Test that we can assign to an array index"""
    source = """fn main() -> int:
    var a = [1, 2, 3]
    a[0] = 10
    return a[0] - 10
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    # Pass the type checker to the codegen
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that store to array element is in the IR
    # (Note: For Lists it uses extract_value + gep + store)
    assert "store i32 10," in llvm_ir
