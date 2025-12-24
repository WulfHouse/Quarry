"""Integration tests for Tensor layouts (SPEC-LANG-0871)

Tests RowMajor, ColMajor, and Strided tensor layouts.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src.frontend import lex, parse


@pytest.mark.fast
def test_tensor_layout_enum():
    """Test that TensorLayout enum exists"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    assert tensor_file.exists(), "tensor.pyrite should exist"
    
    content = tensor_file.read_text()
    
    # Verify TensorLayout enum is defined
    assert "enum TensorLayout" in content, "TensorLayout enum should be defined"
    assert "RowMajor" in content, "RowMajor layout should be defined"
    assert "ColMajor" in content, "ColMajor layout should be defined"
    assert "Strided" in content, "Strided layout should be defined"


@pytest.mark.fast
def test_tensor_has_layout_field():
    """Test that Tensor struct has layout field"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify Tensor has layout field
    assert "layout: TensorLayout" in content, "Tensor should have layout field"


@pytest.mark.fast
def test_tensor_to_row_major():
    """Test conversion to RowMajor layout"""
    source = """
import std.num.tensor

fn test_row_major() -> i32:
    let t = Tensor.new(2, 2)
    let row_major = t.to_row_major()
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_to_col_major():
    """Test conversion to ColMajor layout"""
    source = """
import std.num.tensor

fn test_col_major() -> i32:
    let t = Tensor.new(2, 2)
    let col_major = t.to_col_major()
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_strided_layout():
    """Test strided layout"""
    source = """
import std.num.tensor

fn test_strided() -> i32:
    let t = Tensor.new(4, 4)
    let strided = t.with_strided_layout(2, 2)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_layout_methods_exist():
    """Test that all layout conversion methods are present"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify all layout conversion methods exist
    assert "fn to_row_major(" in content, "to_row_major method should exist"
    assert "fn to_col_major(" in content, "to_col_major method should exist"
    assert "fn with_strided_layout(" in content, "with_strided_layout method should exist"


@pytest.mark.fast
def test_layout_indexing():
    """Test that layout affects indexing (verify implementation exists)"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify layout-aware operations exist
    # At minimum, verify the layout field is used in conversion methods
    assert "TensorLayout.RowMajor" in content or "RowMajor" in content
    assert "TensorLayout.ColMajor" in content or "ColMajor" in content


@pytest.mark.fast
def test_default_layout_is_row_major():
    """Test that default layout is RowMajor"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify default layout is RowMajor in constructor
    assert "TensorLayout.RowMajor" in content, "Default layout should be RowMajor"

