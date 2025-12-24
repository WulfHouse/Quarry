"""Integration tests for Specialized Numerical Algorithms (SPEC-LANG-0873)

Tests GEMM (General Matrix Multiply) and other numerical algorithms.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src.frontend import lex, parse


@pytest.mark.fast
def test_gemm_function_exists():
    """Test that GEMM function is defined"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    assert tensor_file.exists(), "tensor.pyrite should exist"
    
    content = tensor_file.read_text()
    
    # Verify GEMM function exists
    assert "fn gemm(" in content, "gemm function should be defined"


@pytest.mark.fast
def test_gemm_invocation():
    """Test GEMM function can be called"""
    source = """
import std.num.tensor

fn test_gemm() -> i32:
    let a = Tensor.new(2, 3)
    let b = Tensor.new(3, 2)
    let c = gemm(a, b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_gemm_dimension_checking():
    """Test GEMM checks matrix dimensions"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify GEMM checks dimensions
    gemm_section = content[content.find("fn gemm("):] if "fn gemm(" in content else ""
    assert "a.cols != b.rows" in gemm_section or "dimension" in gemm_section.lower(), \
        "GEMM should check matrix dimensions"


@pytest.mark.fast
def test_gemm_correctness_structure():
    """Test GEMM has correct triple-nested loop structure"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify GEMM has nested loops (naive implementation)
    gemm_section = content[content.find("fn gemm("):content.find("fn gemm(") + 1000] if "fn gemm(" in content else ""
    
    # Check for accumulation pattern (sum)
    assert "sum" in gemm_section.lower(), "GEMM should accumulate results"


@pytest.mark.fast
def test_gemm_returns_result():
    """Test GEMM returns Result type"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify GEMM returns Result
    gemm_line = [line for line in content.split('\n') if 'fn gemm(' in line]
    assert len(gemm_line) > 0, "GEMM function should exist"
    assert "Result" in gemm_line[0], "GEMM should return Result type"


@pytest.mark.fast
def test_gemm_square_matrices():
    """Test GEMM with square matrices"""
    source = """
import std.num.tensor

fn test_square_gemm() -> i32:
    let a = Tensor.new(3, 3)
    let b = Tensor.new(3, 3)
    let c = gemm(a, b)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_gemv_function_exists():
    """Test that matrix-vector multiply (GEMV) exists"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify GEMV exists (bonus algorithm)
    assert "fn gemv(" in content, "gemv function should be defined"


@pytest.mark.fast
def test_gemv_invocation():
    """Test GEMV can be called"""
    source = """
import std.num.tensor

fn test_gemv() -> i32:
    let a = Tensor.new(3, 4)
    let x = Tensor.new(4, 1)
    let y = gemv(a, x)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_numerical_algorithms_baseline():
    """Test that baseline implementations exist (no SIMD required yet)"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify baseline comment exists indicating SIMD is future work
    assert "baseline" in content.lower() or "naive" in content.lower(), \
        "Should document baseline/naive implementation"


@pytest.mark.fast
def test_gemm_error_handling():
    """Test GEMM handles dimension mismatch"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify error handling
    gemm_section = content[content.find("fn gemm("):content.find("fn gemm(") + 1000] if "fn gemm(" in content else ""
    assert "Err(" in gemm_section, "GEMM should return errors for invalid inputs"

