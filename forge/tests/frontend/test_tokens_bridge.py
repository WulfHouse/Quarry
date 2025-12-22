"""Tests for tokens_bridge.py - FFI bridge for tokens module

This module tests that tokens_bridge.py correctly re-exports tokens and
provides the bridge functions (get_keyword_type, is_keyword).
"""

import pytest

pytestmark = pytest.mark.fast  # Fast unit tests - simple function calls

from src.bridge import tokens_bridge
from src.frontend.tokens import TokenType, KEYWORDS


def test_tokens_bridge_all_exports_accessible():
    """Test that all symbols in __all__ are accessible from tokens_bridge"""
    exported_symbols = set(tokens_bridge.__all__)
    
    for symbol_name in exported_symbols:
        assert hasattr(tokens_bridge, symbol_name), f"{symbol_name} should be accessible from tokens_bridge"
        symbol = getattr(tokens_bridge, symbol_name)
        assert symbol is not None, f"{symbol_name} should not be None"


def test_tokens_bridge_re_exports():
    """Test that re-exported symbols match the original tokens module"""
    assert tokens_bridge.TokenType is TokenType
    assert tokens_bridge.Token is not None
    assert tokens_bridge.Span is not None
    assert tokens_bridge.KEYWORDS is KEYWORDS


def test_get_keyword_type_valid_keywords():
    """Test get_keyword_type with valid keyword strings"""
    # Test a few common keywords
    assert tokens_bridge.get_keyword_type("fn") == TokenType.FN
    assert tokens_bridge.get_keyword_type("let") == TokenType.LET
    assert tokens_bridge.get_keyword_type("if") == TokenType.IF
    assert tokens_bridge.get_keyword_type("else") == TokenType.ELSE
    assert tokens_bridge.get_keyword_type("return") == TokenType.RETURN
    assert tokens_bridge.get_keyword_type("struct") == TokenType.STRUCT
    assert tokens_bridge.get_keyword_type("enum") == TokenType.ENUM


def test_get_keyword_type_invalid_keywords():
    """Test get_keyword_type with invalid keyword strings"""
    # Non-keywords should return None
    assert tokens_bridge.get_keyword_type("notakeyword") is None
    assert tokens_bridge.get_keyword_type("xyz") is None
    assert tokens_bridge.get_keyword_type("") is None
    assert tokens_bridge.get_keyword_type("hello") is None


def test_get_keyword_type_all_keywords():
    """Test get_keyword_type with all known keywords"""
    # Test that all keywords in KEYWORDS dict work
    for keyword, expected_type in KEYWORDS.items():
        result = tokens_bridge.get_keyword_type(keyword)
        assert result == expected_type, f"get_keyword_type('{keyword}') should return {expected_type}"


def test_is_keyword_valid_keywords():
    """Test is_keyword with valid keyword strings"""
    # Test a few common keywords
    assert tokens_bridge.is_keyword("fn") is True
    assert tokens_bridge.is_keyword("let") is True
    assert tokens_bridge.is_keyword("if") is True
    assert tokens_bridge.is_keyword("else") is True
    assert tokens_bridge.is_keyword("return") is True
    assert tokens_bridge.is_keyword("struct") is True
    assert tokens_bridge.is_keyword("enum") is True


def test_is_keyword_invalid_keywords():
    """Test is_keyword with invalid keyword strings"""
    # Non-keywords should return False
    assert tokens_bridge.is_keyword("notakeyword") is False
    assert tokens_bridge.is_keyword("xyz") is False
    assert tokens_bridge.is_keyword("hello") is False
    assert tokens_bridge.is_keyword("world") is False


def test_is_keyword_empty_string():
    """Test is_keyword with empty string"""
    assert tokens_bridge.is_keyword("") is False


def test_is_keyword_all_keywords():
    """Test is_keyword with all known keywords"""
    # Test that all keywords in KEYWORDS dict return True
    for keyword in KEYWORDS.keys():
        assert tokens_bridge.is_keyword(keyword) is True, f"is_keyword('{keyword}') should return True"


def test_is_keyword_case_sensitive():
    """Test that is_keyword is case-sensitive"""
    # Keywords should be case-sensitive
    assert tokens_bridge.is_keyword("fn") is True
    assert tokens_bridge.is_keyword("Fn") is False
    assert tokens_bridge.is_keyword("FN") is False
    assert tokens_bridge.is_keyword("let") is True
    assert tokens_bridge.is_keyword("Let") is False
    assert tokens_bridge.is_keyword("LET") is False
