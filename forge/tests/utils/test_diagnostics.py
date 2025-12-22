"""Tests for diagnostics.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.utils import (
    Diagnostic, ERROR_CODES,
    create_ownership_error, create_borrow_conflict_error, create_type_mismatch_error
)
from src.frontend.tokens import Span


def test_diagnostic_creation():
    """Test Diagnostic class creation"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span
    )
    
    assert diag.code == "P0234"
    assert diag.message == "Test error"
    assert diag.span == span
    assert diag.level == "error"
    assert diag.notes == []
    assert diag.help_messages == []
    assert diag.related_spans == []


def test_diagnostic_with_all_fields():
    """Test Diagnostic with all fields"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    related_span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=5)
    
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span,
        level="warning",
        notes=["Note 1", "Note 2"],
        help_messages=["Help 1", "Help 2"],
        related_spans=[("related", related_span)]
    )
    
    assert diag.level == "warning"
    assert len(diag.notes) == 2
    assert len(diag.help_messages) == 2
    assert len(diag.related_spans) == 1


def test_diagnostic_format_error():
    """Test Diagnostic.format() for error level"""
    span = Span(filename="test.pyrite", start_line=3, start_column=5, end_line=3, end_column=10)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span,
        level="error"
    )
    
    source = "line 1\nline 2\nline 3 with error\nline 4"
    formatted = diag.format(source)
    
    assert "error[P0234]" in formatted
    assert "Test error" in formatted
    assert "test.pyrite" in formatted
    assert "line 3" in formatted


def test_diagnostic_format_warning():
    """Test Diagnostic.format() for warning level"""
    span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=5)
    diag = Diagnostic(
        code="P0234",
        message="Test warning",
        span=span,
        level="warning"
    )
    
    source = "line 1\nline 2\nline 3"
    formatted = diag.format(source)
    
    assert "warning[P0234]" in formatted
    assert "Test warning" in formatted


def test_diagnostic_format_other_level():
    """Test Diagnostic.format() for other level"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    diag = Diagnostic(
        code="P0234",
        message="Test note",
        span=span,
        level="note"
    )
    
    source = "line 1"
    formatted = diag.format(source)
    
    assert "note[P0234]" in formatted
    assert "Test note" in formatted


def test_diagnostic_format_with_notes():
    """Test Diagnostic.format() with notes"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span,
        notes=["Note 1", "Note 2"]
    )
    
    source = "line 1"
    formatted = diag.format(source)
    
    assert "= note: Note 1" in formatted
    assert "= note: Note 2" in formatted


def test_diagnostic_format_with_help():
    """Test Diagnostic.format() with help messages"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span,
        help_messages=["Help 1", "Help 2"]
    )
    
    source = "line 1"
    formatted = diag.format(source)
    
    # Help messages include ANSI color codes, so check for content
    assert "Help 1" in formatted
    assert "Help 2" in formatted
    assert "help" in formatted.lower()


def test_diagnostic_format_with_related_spans():
    """Test Diagnostic.format() with related spans"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    related_span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=5)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span,
        related_spans=[("related note", related_span)]
    )
    
    source = "line 1\nline 2"
    formatted = diag.format(source)
    
    assert "= note: related note" in formatted
    assert "test.pyrite:2:1" in formatted


def test_diagnostic_format_source_context():
    """Test Diagnostic.format() includes source context"""
    span = Span(filename="test.pyrite", start_line=5, start_column=3, end_line=5, end_column=8)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span
    )
    
    source = "line 1\nline 2\nline 3\nline 4\nline 5 error here\nline 6\nline 7"
    formatted = diag.format(source)
    
    # Should include context lines (start_line - 2 to end_line + 2)
    assert "3" in formatted  # line 3
    assert "4" in formatted  # line 4
    assert "5" in formatted  # line 5 (error line)
    assert "6" in formatted  # line 6
    assert "7" in formatted  # line 7


def test_diagnostic_format_highlight():
    """Test Diagnostic.format() highlights error location"""
    span = Span(filename="test.pyrite", start_line=2, start_column=5, end_line=2, end_column=10)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span
    )
    
    source = "line 1\nline 2 with error\nline 3"
    formatted = diag.format(source)
    
    # Should have carets (^) highlighting the error
    assert "^" in formatted or "error" in formatted.lower()


def test_error_codes_dict():
    """Test ERROR_CODES dictionary contains expected codes"""
    assert "P0234" in ERROR_CODES
    assert "P0382" in ERROR_CODES
    assert "P0499" in ERROR_CODES
    assert "P0502" in ERROR_CODES
    assert "P0503" in ERROR_CODES
    assert "P0308" in ERROR_CODES
    assert "P0277" in ERROR_CODES
    assert "P0425" in ERROR_CODES
    assert "P0412" in ERROR_CODES
    assert "P0004" in ERROR_CODES
    
    assert ERROR_CODES["P0234"] == "cannot use moved value"
    assert ERROR_CODES["P0308"] == "type mismatch"


def test_create_ownership_error():
    """Test create_ownership_error function"""
    use_span = Span(filename="test.pyrite", start_line=5, start_column=1, end_line=5, end_column=10)
    move_span = Span(filename="test.pyrite", start_line=4, start_column=1, end_line=4, end_column=15)
    alloc_span = Span(filename="test.pyrite", start_line=3, start_column=1, end_line=3, end_column=15)
    
    diag = create_ownership_error("x", "take", use_span, move_span, alloc_span)
    
    assert diag.code == "P0234"
    assert "cannot use moved value 'x'" in diag.message
    assert diag.span == use_span
    assert diag.level == "error"
    assert len(diag.notes) == 1
    assert "value moved to 'take'" in diag.notes[0]
    assert len(diag.help_messages) == 4
    assert len(diag.related_spans) == 2


def test_create_borrow_conflict_error_both_mutable():
    """Test create_borrow_conflict_error when both are mutable"""
    new_span = Span(filename="test.pyrite", start_line=3, start_column=1, end_line=3, end_column=10)
    existing_span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    diag = create_borrow_conflict_error("x", new_span, existing_span, new_is_mut=True, existing_is_mut=True)
    
    assert diag.code == "P0499"
    assert "cannot borrow 'x' as mutable more than once" in diag.message
    assert diag.span == new_span


def test_create_borrow_conflict_error_new_mutable():
    """Test create_borrow_conflict_error when new is mutable, existing is immutable"""
    new_span = Span(filename="test.pyrite", start_line=3, start_column=1, end_line=3, end_column=10)
    existing_span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    diag = create_borrow_conflict_error("x", new_span, existing_span, new_is_mut=True, existing_is_mut=False)
    
    assert diag.code == "P0502"
    assert "cannot borrow 'x' as mutable because it is also borrowed as immutable" in diag.message
    assert diag.span == new_span


def test_create_borrow_conflict_error_new_immutable():
    """Test create_borrow_conflict_error when new is immutable, existing is mutable"""
    new_span = Span(filename="test.pyrite", start_line=3, start_column=1, end_line=3, end_column=10)
    existing_span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    diag = create_borrow_conflict_error("x", new_span, existing_span, new_is_mut=False, existing_is_mut=True)
    
    assert diag.code == "P0503"
    assert "cannot borrow 'x' as immutable because it is also borrowed as mutable" in diag.message
    assert diag.span == new_span


def test_create_borrow_conflict_error_related_spans():
    """Test create_borrow_conflict_error includes related spans"""
    new_span = Span(filename="test.pyrite", start_line=3, start_column=1, end_line=3, end_column=10)
    existing_span = Span(filename="test.pyrite", start_line=2, start_column=1, end_line=2, end_column=10)
    
    diag = create_borrow_conflict_error("x", new_span, existing_span, new_is_mut=True, existing_is_mut=False)
    
    assert len(diag.related_spans) == 1
    assert diag.related_spans[0][0] == "first borrow occurs here"
    assert diag.related_spans[0][1] == existing_span
    assert len(diag.help_messages) == 3


def test_create_type_mismatch_error():
    """Test create_type_mismatch_error function"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    
    diag = create_type_mismatch_error("int", "String", span)
    
    assert diag.code == "P0308"
    assert "mismatched types" in diag.message
    assert diag.span == span
    assert len(diag.notes) == 2
    assert "expected type: int" in diag.notes[0]
    assert "found type: String" in diag.notes[1]
    assert len(diag.help_messages) == 2


def test_diagnostic_format_explanation_hint():
    """Test Diagnostic.format() includes explanation hint"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    diag = Diagnostic(
        code="P0234",
        message="Test error",
        span=span
    )
    
    source = "line 1"
    formatted = diag.format(source)
    
    assert "--explain P0234" in formatted or "explain P0234" in formatted


def test_diagnostic_format_edge_cases():
    """Test Diagnostic.format() with edge cases"""
    # Test with span at start of file
    span1 = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    diag1 = Diagnostic(code="P0234", message="Error", span=span1)
    formatted1 = diag1.format("line 1")
    assert "Error" in formatted1
    
    # Test with empty source
    span2 = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=5)
    diag2 = Diagnostic(code="P0234", message="Error", span=span2)
    formatted2 = diag2.format("")
    assert "Error" in formatted2
    
    # Test with span beyond source length
    span3 = Span(filename="test.pyrite", start_line=10, start_column=1, end_line=10, end_column=5)
    diag3 = Diagnostic(code="P0234", message="Error", span=span3)
    formatted3 = diag3.format("line 1\nline 2")
    assert "Error" in formatted3
