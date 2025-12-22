"""Test cost analysis functionality"""
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


def test_codegen_tracks_allocations():
    """Test that codegen tracks allocations when enabled"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.track_costs = True
    
    # Initially no allocations
    report = codegen.get_cost_report()
    assert report["summary"]["total_allocations"] == 0
    
    # Manually add an allocation (simulating Map.new() call)
    codegen.allocation_sites.append({
        "function": "main",
        "line": 5,
        "type": "Map",
        "bytes": 64,
        "description": "Map[String, int]"
    })
    
    report = codegen.get_cost_report()
    assert report["summary"]["total_allocations"] == 1
    assert report["summary"]["total_allocation_bytes"] == 64
    assert len(report["allocations"]) == 1
    assert report["allocations"][0]["type"] == "Map"


def test_codegen_cost_tracking_disabled():
    """Test that cost tracking is disabled by default"""
    codegen = LLVMCodeGen(deterministic=False)
    assert codegen.track_costs == False, "Cost tracking should be disabled by default"


def test_codegen_get_cost_report_format():
    """Test that get_cost_report returns correct format"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.track_costs = True
    
    # Add some allocations
    codegen.allocation_sites.append({
        "function": "test",
        "line": 1,
        "type": "List",
        "bytes": 24,
        "description": "List[int]"
    })
    codegen.allocation_sites.append({
        "function": "test",
        "line": 2,
        "type": "Map",
        "bytes": 64,
        "description": "Map[String, int]"
    })
    
    report = codegen.get_cost_report()
    
    assert "allocations" in report
    assert "copies" in report
    assert "summary" in report
    assert report["summary"]["total_allocations"] == 2
    assert report["summary"]["total_allocation_bytes"] == 88
    assert len(report["allocations"]) == 2


def test_codegen_tracks_list_allocations():
    """Test that List allocations are tracked"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.track_costs = True
    
    # Simulate list allocation tracking
    codegen.allocation_sites.append({
        "function": "main",
        "line": 3,
        "type": "List",
        "bytes": 48,
        "description": "List with 3 element(s)"
    })
    
    report = codegen.get_cost_report()
    assert report["summary"]["total_allocations"] == 1
    allocations = report["allocations"]
    assert allocations[0]["type"] == "List"
    assert allocations[0]["bytes"] == 48


def test_codegen_tracks_map_allocations():
    """Test that Map allocations are tracked"""
    codegen = LLVMCodeGen(deterministic=False)
    codegen.track_costs = True
    
    # Simulate Map allocation tracking
    codegen.allocation_sites.append({
        "function": "main",
        "line": 5,
        "type": "Map",
        "bytes": 64,
        "description": "Map[String, int]"
    })
    
    report = codegen.get_cost_report()
    assert report["summary"]["total_allocations"] == 1
    allocations = report["allocations"]
    assert allocations[0]["type"] == "Map"
    assert allocations[0]["bytes"] == 64
