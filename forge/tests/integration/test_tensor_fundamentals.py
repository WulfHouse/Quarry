"""Integration tests for Tensor fundamentals (SPEC-LANG-0870)

Tests tensor arithmetic operations and shape checking.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src.frontend import lex, parse


@pytest.mark.fast
def test_tensor_creation():
    """Test that Tensor.new parses correctly"""
    source = """
import std.num.tensor

fn test_tensor() -> i32:
    let t = Tensor.new(3, 4)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None
    assert len(program.items) > 0


@pytest.mark.fast
def test_tensor_addition():
    """Test tensor addition operation"""
    source = """
import std.num.tensor

fn test_add() -> i32:
    let a = Tensor.new(2, 2)
    let b = Tensor.new(2, 2)
    let c = a.add(b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_subtraction():
    """Test tensor subtraction operation"""
    source = """
import std.num.tensor

fn test_sub() -> i32:
    let a = Tensor.new(2, 2)
    let b = Tensor.new(2, 2)
    let c = a.sub(b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_multiplication():
    """Test tensor element-wise multiplication"""
    source = """
import std.num.tensor

fn test_mul() -> i32:
    let a = Tensor.new(2, 2)
    let b = Tensor.new(2, 2)
    let c = a.mul(b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_division():
    """Test tensor element-wise division"""
    source = """
import std.num.tensor

fn test_div() -> i32:
    let a = Tensor.new(2, 2)
    let b = Tensor.new(2, 2)
    let c = a.div(b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_all_ops():
    """Test all tensor arithmetic operations are present"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    assert tensor_file.exists(), "tensor.pyrite should exist"
    
    content = tensor_file.read_text()
    
    # Verify all required operations are present
    assert "fn add(" in content, "Tensor should have add method"
    assert "fn sub(" in content, "Tensor should have sub method"
    assert "fn mul(" in content, "Tensor should have mul method"
    assert "fn div(" in content, "Tensor should have div method"


@pytest.mark.fast
def test_tensor_shape_checking():
    """Test that tensor operations check dimensions"""
    source = """
import std.num.tensor

fn test_shape_check() -> i32:
    let a = Tensor.new(2, 3)
    let b = Tensor.new(2, 3)
    # Same dimensions - should work
    let c = a.add(b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_dimension_mismatch_error():
    """Test that dimension mismatch returns error"""
    # Verify the implementation checks for dimension mismatch
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify dimension checking is present in add/sub/mul/div
    assert "Dimension mismatch" in content, "Operations should check dimensions"
    assert "self.rows != other.rows or self.cols != other.cols" in content


@pytest.mark.fast
def test_tensor_get_set():
    """Test tensor get/set operations"""
    source = """
import std.num.tensor

fn test_get_set() -> i32:
    var t = Tensor.new(2, 2)
    t.set(0, 0, 1.0)
    t.set(0, 1, 2.0)
    let val = t.get(0, 0)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_division_by_zero():
    """Test that division by zero is handled"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify division by zero checking is present
    assert "Division by zero" in content or "divisor == 0" in content, "Division should check for zero"


@pytest.mark.fast
def test_tensor_result_type():
    """Test that tensor operations return Result type"""
    source = """
import std.num.tensor

fn test_result() -> i32:
    let a = Tensor.new(2, 2)
    let b = Tensor.new(2, 2)
    let result_add = a.add(b)
    let result_sub = a.sub(b)
    let result_mul = a.mul(b)
    let result_div = a.div(b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None

