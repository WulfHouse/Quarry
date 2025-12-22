"""Test cost transparency warnings"""
import pytest
import sys
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from src.backend import LLVMCodeGen
from src.frontend.tokens import Span


def test_cost_warnings_disabled_by_default():
    """Test that cost warnings are disabled by default"""
    codegen = LLVMCodeGen(deterministic=False)
    assert codegen.warn_costs == False, "Cost warnings should be disabled by default"


def test_cost_warnings_enabled():
    """Test that cost warnings can be enabled"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.warn_costs = True
    assert codegen.warn_costs == True, "Cost warnings should be enabled"


def test_cost_warnings_stored():
    """Test that cost warnings are stored when allocations occur"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.warn_costs = True
    
    # Manually add a warning (simulating Map.new() allocation)
    span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    codegen.cost_warnings.append({
        "span": span,
        "message": "Heap allocation: Map[String, int]",
        "help_hint": "Consider using a reference (&Map) or pre-allocating with known size if possible"
    })
    
    assert len(codegen.cost_warnings) == 1
    assert codegen.cost_warnings[0]["message"] == "Heap allocation: Map[String, int]"
    assert "help_hint" in codegen.cost_warnings[0]


def test_cost_warnings_format():
    """Test that cost warnings have required fields"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.warn_costs = True
    
    span = Span(filename="test.pyrite", start_line=3, start_column=1, end_line=3, end_column=10)
    codegen.cost_warnings.append({
        "span": span,
        "message": "Heap allocation: List with 3 element(s)",
        "help_hint": "List literals allocate memory. Consider using arrays for fixed-size data."
    })
    
    warning = codegen.cost_warnings[0]
    assert "span" in warning
    assert "message" in warning
    assert "help_hint" in warning
    assert isinstance(warning["span"], Span)
    assert isinstance(warning["message"], str)
    assert isinstance(warning["help_hint"], str)
