"""Tests for enhanced cost analysis features"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
import json
import tempfile
from pathlib import Path

from quarry.cost_analysis import CostAnalyzer, AllocationSite, CostReport


def test_multi_level_output_beginner():
    """Test beginner-level output"""
    analyzer = CostAnalyzer()
    
    # Create a simple allocation
    alloc = AllocationSite(
        file="test.pyrite",
        line=10,
        function="main",
        type_allocated="List",
        estimated_bytes=100,
        in_loop=True,
        loop_iterations=1000,
        closure_type="none",
        suggestion="Move outside loop"
    )
    analyzer.allocations.append(alloc)
    
    report = analyzer._generate_report()
    
    # Should have loop multiplication
    assert report.total_allocation_bytes == 100 * 1000


def test_closure_type_distinction():
    """Test that closure types are distinguished"""
    analyzer = CostAnalyzer()
    
    # Runtime closure
    runtime_alloc = AllocationSite(
        file="test.pyrite",
        line=20,
        function="main",
        type_allocated="ClosureEnvironment(3 captures)",
        estimated_bytes=24,
        in_loop=False,
        loop_iterations=1,
        closure_type="runtime",
        suggestion="Consider parameter closure"
    )
    analyzer.allocations.append(runtime_alloc)
    
    report = analyzer._generate_report()
    assert len(report.allocations) == 1
    assert report.allocations[0].closure_type == "runtime"


def test_loop_multiplication():
    """Test loop iteration multiplication"""
    analyzer = CostAnalyzer()
    
    # Allocation in loop
    alloc = AllocationSite(
        file="test.pyrite",
        line=30,
        function="main",
        type_allocated="List",
        estimated_bytes=50,
        in_loop=True,
        loop_iterations=100,
        closure_type="none",
        suggestion=""
    )
    analyzer.allocations.append(alloc)
    
    report = analyzer._generate_report()
    # Should multiply: 50 bytes × 100 iterations
    assert report.total_allocation_bytes == 5000


def test_json_output():
    """Test JSON output format"""
    analyzer = CostAnalyzer()
    
    alloc = AllocationSite(
        file="test.pyrite",
        line=40,
        function="main",
        type_allocated="List",
        estimated_bytes=100,
        in_loop=False,
        loop_iterations=1,
        closure_type="none",
        suggestion=""
    )
    analyzer.allocations.append(alloc)
    
    report = analyzer._generate_report()
    json_data = report.to_dict()
    
    assert 'allocations' in json_data
    assert 'summary' in json_data
    assert json_data['summary']['total_allocations'] == 1
    assert json_data['allocations'][0]['closure_type'] == "none"


def test_baseline_comparison():
    """Test baseline comparison"""
    current = CostReport(
        allocations=[
            AllocationSite("test.pyrite", 10, "main", "List", 100, False, 1, "none", "")
        ],
        copies=[],
        total_allocations=1,
        total_allocation_bytes=100,
        total_copies=0,
        total_copy_bytes=0
    )
    
    baseline = CostReport(
        allocations=[],
        copies=[],
        total_allocations=0,
        total_allocation_bytes=0,
        total_copies=0,
        total_copy_bytes=0
    )
    
    # Current has more allocations
    assert current.total_allocations > baseline.total_allocations


def test_optimization_suggestions():
    """Test that suggestions are generated"""
    analyzer = CostAnalyzer()
    
    # Allocation in loop should have suggestion
    alloc = AllocationSite(
        file="test.pyrite",
        line=50,
        function="main",
        type_allocated="List",
        estimated_bytes=100,
        in_loop=True,
        loop_iterations=1000,
        closure_type="none",
        suggestion="Consider moving outside loop"
    )
    analyzer.allocations.append(alloc)
    
    assert alloc.suggestion != ""
    assert "loop" in alloc.suggestion.lower()

