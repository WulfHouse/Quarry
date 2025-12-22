"""Test error explanations coverage"""
import pytest
import sys
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from src.utils.error_explanations import ERROR_EXPLANATIONS, get_explanation, list_error_codes


def test_all_error_codes_have_explanations():
    """Verify all error codes have explanations"""
    # All codes in ERROR_EXPLANATIONS should have valid explanations
    for code in ERROR_EXPLANATIONS.keys():
        assert code in ERROR_EXPLANATIONS, f"Code {code} should be in ERROR_EXPLANATIONS"


def test_explanation_format():
    """Verify explanations have required fields"""
    for code, exp in ERROR_EXPLANATIONS.items():
        assert "title" in exp, f"{code}: missing 'title'"
        assert "description" in exp, f"{code}: missing 'description'"
        assert isinstance(exp["title"], str), f"{code}: 'title' must be string"
        assert isinstance(exp["description"], str), f"{code}: 'description' must be string"


def test_get_explanation_returns_string():
    """Verify get_explanation returns formatted string"""
    for code in ERROR_EXPLANATIONS.keys():
        explanation = get_explanation(code)
        assert isinstance(explanation, str), f"{code}: explanation must be string"
        assert len(explanation) > 0, f"{code}: explanation must not be empty"
        assert code in explanation, f"{code}: explanation must contain error code"


def test_get_explanation_unknown_code():
    """Verify get_explanation handles unknown codes gracefully"""
    explanation = get_explanation("P9999")
    assert "not found" in explanation.lower() or "available" in explanation.lower()
    assert "P9999" in explanation


def test_explanation_has_examples():
    """Verify explanations have examples where appropriate"""
    # At least some explanations should have examples
    explanations_with_examples = sum(
        1 for exp in ERROR_EXPLANATIONS.values() if "examples" in exp
    )
    assert explanations_with_examples > 0, "At least some explanations should have examples"


def test_ownership_errors_explained():
    """Verify all ownership errors have explanations"""
    ownership_codes = ["P0234", "P0382", "P0499", "P0502", "P0503", "P0505"]
    for code in ownership_codes:
        assert code in ERROR_EXPLANATIONS, f"Ownership error {code} must have explanation"
        exp = ERROR_EXPLANATIONS[code]
        desc_lower = exp["description"].lower()
        # Check for ownership-related keywords
        has_ownership_keyword = any(
            keyword in desc_lower 
            for keyword in ["ownership", "borrow", "move", "reference", "dangling", "lifetime", "mutable", "immutable"]
        )
        assert has_ownership_keyword, \
            f"{code}: explanation should mention ownership/borrow/move/reference/lifetime"
