"""Integration tests for compound assignment operators"""

import pytest
from src.frontend import lex, parse
from src.middle import type_check
from src.backend import generate_llvm
import subprocess
import os
from pathlib import Path


@pytest.mark.integration
def test_plus_eq_integration():
    """Test += operator end-to-end"""
    source = """fn main() -> int:
    var x = 5
    x += 3
    return x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that add instruction is present
    assert "add i32" in llvm_ir or "add nsw i32" in llvm_ir
    # Check that store is present
    assert "store i32" in llvm_ir


@pytest.mark.integration
def test_minus_eq_integration():
    """Test -= operator end-to-end"""
    source = """fn main() -> int:
    var x = 10
    x -= 3
    return x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that sub instruction is present
    assert "sub i32" in llvm_ir or "sub nsw i32" in llvm_ir


@pytest.mark.integration
def test_star_eq_integration():
    """Test *= operator end-to-end"""
    source = """fn main() -> int:
    var x = 5
    x *= 4
    return x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that mul instruction is present
    assert "mul i32" in llvm_ir or "mul nsw i32" in llvm_ir


@pytest.mark.integration
def test_slash_eq_integration():
    """Test /= operator end-to-end"""
    source = """fn main() -> int:
    var x = 20
    x /= 4
    return x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that sdiv instruction is present
    assert "sdiv i32" in llvm_ir


@pytest.mark.integration
def test_compound_assignment_float():
    """Test compound assignment with float types"""
    source = """fn main() -> f64:
    var x: f64 = 5.0
    x += 3.5
    return x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Check that fadd instruction is present for floats
    assert "fadd double" in llvm_ir


@pytest.mark.integration
def test_compound_assignment_with_expression():
    """Test compound assignment with expression on right side"""
    source = """fn main() -> int:
    var x = 5
    x += 2 + 3
    return x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Should have multiple add instructions
    assert llvm_ir.count("add") >= 2 or llvm_ir.count("add nsw") >= 2


@pytest.mark.integration
def test_compound_assignment_field():
    """Test compound assignment on struct field"""
    source = """struct Point:
    x: int
    y: int

fn main() -> int:
    var p = Point{x: 1, y: 2}
    p.x += 5
    return p.x
"""
    tokens = lex(source)
    ast_program = parse(tokens)
    type_checker = type_check(ast_program)
    assert not type_checker.has_errors(), f"Type errors: {type_checker.errors}"
    
    llvm_ir = generate_llvm(ast_program, type_checker=type_checker)
    
    # Should have add and insertvalue for field assignment
    assert "add i32" in llvm_ir or "add nsw i32" in llvm_ir
    assert "insertvalue" in llvm_ir

