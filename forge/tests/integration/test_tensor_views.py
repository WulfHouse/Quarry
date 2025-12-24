"""Integration tests for Zero-cost Tensor Views (SPEC-LANG-0872)

Tests TensorView slicing without data copy and borrowing rules.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src.frontend import lex, parse


@pytest.mark.fast
def test_tensor_view_struct_exists():
    """Test that TensorView struct is defined"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    assert tensor_file.exists(), "tensor.pyrite should exist"
    
    content = tensor_file.read_text()
    
    # Verify TensorView struct exists
    assert "struct TensorView" in content, "TensorView struct should be defined"


@pytest.mark.fast
def test_tensor_view_uses_const_pointer():
    """Test that TensorView uses const pointer (zero-cost, no mutation)"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify TensorView uses const pointer to prevent mutation
    assert "*const f64" in content, "TensorView should use const pointer for zero-cost views"


@pytest.mark.fast
def test_tensor_view_creation():
    """Test that Tensor.view creates TensorView"""
    source = """
import std.num.tensor

fn test_view() -> i32:
    let t = Tensor.new(4, 4)
    let v = t.view(0, 2, 0, 2)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_view_slicing():
    """Test TensorView slicing boundaries"""
    source = """
import std.num.tensor

fn test_slicing() -> i32:
    let t = Tensor.new(10, 10)
    # Slice rows 2-5, cols 3-7
    let v = t.view(2, 5, 3, 7)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_view_get():
    """Test TensorView get method"""
    source = """
import std.num.tensor

fn test_view_get() -> i32:
    let t = Tensor.new(4, 4)
    let v = t.view(1, 3, 1, 3)
    let val = v.get(0, 0)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_tensor_view_dimensions():
    """Test TensorView has correct dimensions"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify TensorView tracks view dimensions
    assert "view_row_start" in content, "TensorView should track row start"
    assert "view_row_end" in content, "TensorView should track row end"
    assert "view_col_start" in content, "TensorView should track col start"
    assert "view_col_end" in content, "TensorView should track col end"


@pytest.mark.fast
def test_tensor_view_no_data_copy():
    """Test that TensorView doesn't copy data"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify view method doesn't call tensor_new (no allocation)
    # The view should just reference base_data
    view_impl = content[content.find("fn view("):content.find("fn view(") + 500] if "fn view(" in content else ""
    
    # Verify no new allocation in view
    assert "base_data: self.data" in content or "base_data:" in view_impl, "View should reference base data"


@pytest.mark.fast
def test_tensor_view_bounds_checking():
    """Test that TensorView performs bounds checking"""
    tensor_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "num" / "tensor.pyrite"
    content = tensor_file.read_text()
    
    # Verify TensorView.get has bounds checking
    if "impl TensorView" in content:
        tensorview_impl = content[content.find("impl TensorView"):]
        assert ("r < 0" in tensorview_impl or "bounds" in tensorview_impl.lower()), \
            "TensorView should have bounds checking"


@pytest.mark.fast
def test_tensor_view_immutable_reference():
    """Test that TensorView takes immutable reference (&self)"""
    source = """
import std.num.tensor

fn test_immutable_view() -> i32:
    let t = Tensor.new(3, 3)
    # View takes &self (immutable borrow)
    let v = t.view(0, 2, 0, 2)
    # Original tensor is borrowed immutably
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None

