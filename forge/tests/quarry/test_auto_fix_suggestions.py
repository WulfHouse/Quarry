"""Test auto-fix suggestion generation"""
import pytest
import sys
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from src.utils import Diagnostic, FixSuggestion
from src.frontend.tokens import Span


def test_suggest_fixes_p0234():
    """Test fix suggestions for P0234 (cannot use moved value)"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0234",
        message="cannot use moved value 'data'",
        span=span,
        var_name="data"
    )
    
    suggestions = diag.suggest_fixes()
    assert len(suggestions) > 0, "Should generate at least one suggestion for P0234"
    
    # Check that suggestions have required fields
    for fix in suggestions:
        assert isinstance(fix, FixSuggestion)
        assert fix.description
        assert fix.code_change
        assert fix.confidence in ["high", "medium", "low"]
    
    # Check for expected suggestions
    descriptions = [f.description for f in suggestions]
    assert any("reference" in desc.lower() or "borrow" in desc.lower() for desc in descriptions), \
        "Should suggest borrowing/reference fix"
    assert any("clone" in desc.lower() for desc in descriptions), \
        "Should suggest clone fix"


def test_suggest_fixes_p0502():
    """Test fix suggestions for P0502 (mutable borrow conflict)"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0502",
        message="cannot borrow as mutable while borrowed as immutable",
        span=span,
        var_name="data"
    )
    
    suggestions = diag.suggest_fixes()
    assert len(suggestions) > 0, "Should generate at least one suggestion for P0502"
    
    # Check for expected suggestions
    descriptions = [f.description for f in suggestions]
    assert any("clone" in desc.lower() for desc in descriptions), \
        "Should suggest clone fix"
    assert any("scope" in desc.lower() for desc in descriptions), \
        "Should suggest scope separation fix"


def test_suggest_fixes_p0308():
    """Test fix suggestions for P0308 (type mismatch)"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0308",
        message="type mismatch: expected int, found str",
        span=span
    )
    
    suggestions = diag.suggest_fixes()
    assert len(suggestions) > 0, "Should generate at least one suggestion for P0308"
    
    # Check for expected suggestions
    descriptions = [f.description for f in suggestions]
    assert any("cast" in desc.lower() for desc in descriptions), \
        "Should suggest type cast fix"
    assert any("type" in desc.lower() for desc in descriptions), \
        "Should suggest type change fix"


def test_suggest_fixes_p0382():
    """Test fix suggestions for P0382 (borrow of moved value)"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0382",
        message="borrow of moved value 'data'",
        span=span,
        var_name="data"
    )
    
    suggestions = diag.suggest_fixes()
    assert len(suggestions) > 0, "Should generate at least one suggestion for P0382"
    
    # Check for expected suggestions
    descriptions = [f.description for f in suggestions]
    assert any("borrow" in desc.lower() for desc in descriptions), \
        "Should suggest borrow fix"


def test_suggest_fixes_p0499():
    """Test fix suggestions for P0499 (cannot borrow as mutable more than once)"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0499",
        message="cannot borrow as mutable more than once",
        span=span,
        var_name="data"
    )
    
    suggestions = diag.suggest_fixes()
    assert len(suggestions) > 0, "Should generate at least one suggestion for P0499"
    
    # Check for expected suggestions
    descriptions = [f.description for f in suggestions]
    assert any("scope" in desc.lower() for desc in descriptions), \
        "Should suggest scope separation fix"


def test_suggest_fixes_p0505():
    """Test fix suggestions for P0505 (borrowed value does not live long enough)"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0505",
        message="borrowed value does not live long enough",
        span=span
    )
    
    suggestions = diag.suggest_fixes()
    assert len(suggestions) > 0, "Should generate at least one suggestion for P0505"
    
    # Check for expected suggestions
    descriptions = [f.description for f in suggestions]
    assert any("owned" in desc.lower() or "return" in desc.lower() for desc in descriptions), \
        "Should suggest returning owned value"


def test_suggestions_appear_in_format():
    """Test that suggestions appear in formatted error output"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0234",
        message="cannot use moved value 'data'",
        span=span,
        var_name="data"
    )
    
    source = "let data = List[int]([1, 2, 3])\nprocess(data)\nprint(data.length())"
    formatted = diag.format(source)
    
    # Check that fix suggestions appear in output
    assert "Fix 1:" in formatted or "fix 1:" in formatted.lower(), \
        "Formatted output should contain fix suggestions"
    assert "help" in formatted.lower(), \
        "Formatted output should contain help messages"


def test_suggestions_have_reasonable_content():
    """Test that suggestions have reasonable content"""
    span = Span(filename="test.pyrite", start_line=1, start_column=1, end_line=1, end_column=10)
    diag = Diagnostic(
        code="P0234",
        message="cannot use moved value 'data'",
        span=span,
        var_name="data"
    )
    
    suggestions = diag.suggest_fixes()
    for fix in suggestions:
        # Description should be meaningful
        assert len(fix.description) > 10, "Description should be meaningful"
        # Code change should be descriptive
        assert len(fix.code_change) > 5, "Code change should be descriptive"
        # Confidence should be valid
        assert fix.confidence in ["high", "medium", "low"], "Confidence should be valid"
