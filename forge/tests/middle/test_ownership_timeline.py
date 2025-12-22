"""Test ownership timeline visualizations"""
import pytest
import sys
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from src.middle import BorrowChecker, OwnershipEvent
from src.frontend.tokens import Span


def test_timeline_tracking_enabled():
    """Test that timeline tracking works when enabled"""
    checker = BorrowChecker(track_timeline=True)
    
    # Create a span
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    
    # Add timeline events
    checker.add_timeline_event("data", "borrow", "'data' borrowed", span)
    checker.add_timeline_event("data", "use", "'data' used", span)
    
    assert len(checker.ownership_timeline) == 2, "Should have 2 timeline events"
    assert checker.ownership_timeline[0].variable == "data"
    assert checker.ownership_timeline[0].event_type == "borrow"


def test_timeline_tracking_disabled():
    """Test that timeline tracking is disabled by default"""
    checker = BorrowChecker(track_timeline=False)
    
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    checker.add_timeline_event("data", "borrow", "'data' borrowed", span)
    
    assert len(checker.ownership_timeline) == 0, "Should not track events when disabled"


def test_format_timeline():
    """Test timeline formatting"""
    checker = BorrowChecker(track_timeline=True)
    
    span1 = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    span2 = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    checker.add_timeline_event("data", "borrow", "'data' borrowed", span1)
    checker.add_timeline_event("data", "use", "'data' used", span2)
    
    timeline = checker.format_timeline("data")
    assert "Ownership Timeline:" in timeline
    assert "Line 1" in timeline
    assert "Line 2" in timeline
    assert "BORROWED" in timeline
    assert "USED" in timeline


def test_format_timeline_all_variables():
    """Test timeline formatting for all variables"""
    checker = BorrowChecker(track_timeline=True)
    
    span1 = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    span2 = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    checker.add_timeline_event("data", "borrow", "'data' borrowed", span1)
    checker.add_timeline_event("other", "use", "'other' used", span2)
    
    timeline = checker.format_timeline()  # All variables
    assert "data" in timeline
    assert "other" in timeline


def test_get_timeline_for_variable():
    """Test getting timeline for specific variable"""
    checker = BorrowChecker(track_timeline=True)
    
    span1 = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    span2 = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    checker.add_timeline_event("data", "borrow", "'data' borrowed", span1)
    checker.add_timeline_event("other", "use", "'other' used", span2)
    
    data_timeline = checker.get_timeline_for_variable("data")
    assert len(data_timeline) == 1
    assert data_timeline[0].variable == "data"
    
    other_timeline = checker.get_timeline_for_variable("other")
    assert len(other_timeline) == 1
    assert other_timeline[0].variable == "other"
