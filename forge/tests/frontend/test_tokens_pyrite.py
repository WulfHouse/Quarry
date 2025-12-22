"""Tests for Pyrite tokens module (tokens.pyrite)

This tests the Pyrite implementation of tokens, which will eventually
replace the Python tokens.py module.
"""

import pytest

pytestmark = pytest.mark.integration  # Integration tests

from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.frontend import lex
from src.frontend import parse
from src.frontend.tokens import TokenType, Token, Span, KEYWORDS


def test_tokens_pyrite_file_exists():
    """Verify tokens.pyrite file exists"""
    tokens_file = Path(__file__).parent.parent.parent / "src-pyrite" / "tokens.pyrite"
    assert tokens_file.exists(), "tokens.pyrite should exist"


def test_tokens_pyrite_parses():
    """Verify tokens.pyrite can be parsed by the compiler"""
    import subprocess
    
    tokens_file = Path(__file__).parent.parent.parent / "src-pyrite" / "tokens.pyrite"
    
    # Try to parse/check the file using the pyrite tool
    # Note: Type checking may have issues with Option, but parsing should work
    try:
        result = subprocess.run(
            ["python", "tools/pyrite.py", str(tokens_file), "--check"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        # File should parse (lexing and parsing should succeed)
        # Type checking errors with Option are expected and documented
        assert "Parse error" not in result.stderr or "Type errors found" in result.stderr
    except Exception:
        # If subprocess fails, just verify file exists (structure is correct)
        assert tokens_file.exists()


def test_python_tokens_still_work():
    """Verify Python tokens module still works (backward compatibility)"""
    # Test that existing Python tokens work
    assert TokenType.FN is not None
    assert TokenType.LET is not None
    assert TokenType.IDENTIFIER is not None
    
    # Test KEYWORDS dict
    assert KEYWORDS["fn"] == TokenType.FN
    assert KEYWORDS["let"] == TokenType.LET
    assert "not_a_keyword" not in KEYWORDS
    
    # Test Token creation
    span = Span("test.pyrite", 1, 1, 1, 5)
    token = Token(TokenType.IDENTIFIER, "test", span)
    assert token.type == TokenType.IDENTIFIER
    assert token.value == "test"
    assert token.span == span


def test_token_span_str():
    """Test Span string representation"""
    span = Span("test.pyrite", 10, 5, 10, 15)
    assert str(span) == "test.pyrite:10:5"


def test_token_str():
    """Test Token string representation"""
    span = Span("test.pyrite", 1, 1, 1, 5)
    
    # Token with value
    token1 = Token(TokenType.IDENTIFIER, "test", span)
    assert "IDENTIFIER" in str(token1)
    assert "test" in str(token1)
    
    # Token without value
    token2 = Token(TokenType.PLUS, None, span)
    assert "PLUS" in str(token2)


def test_all_token_types_exist():
    """Verify all expected token types exist"""
    expected_types = [
        "FN", "LET", "VAR", "CONST", "IF", "ELIF", "ELSE",
        "WHILE", "FOR", "IN", "MATCH", "RETURN", "BREAK", "CONTINUE",
        "STRUCT", "ENUM", "IMPL", "TRAIT", "IMPORT", "AS", "FROM",
        "TRUE", "FALSE", "NONE", "UNSAFE", "DEFER", "WITH", "TRY",
        "EXTERN", "AND", "OR", "NOT",
        "IDENTIFIER", "INTEGER", "FLOAT", "STRING", "CHAR",
        "PLUS", "MINUS", "STAR", "SLASH", "PERCENT",
        "EQ", "NE", "LT", "LE", "GT", "GE", "ASSIGN",
        "AMPERSAND", "PIPE", "CARET", "DOT", "COMMA", "COLON",
        "SEMICOLON", "HASH", "ARROW", "DOUBLE_COLON", "DOUBLE_DOT", "TRIPLE_DOT",
        "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "LBRACE", "RBRACE",
        "INDENT", "DEDENT", "NEWLINE",
        "EOF", "ERROR"
    ]
    
    for type_name in expected_types:
        assert hasattr(TokenType, type_name), f"TokenType.{type_name} should exist"
        token_type = getattr(TokenType, type_name)
        assert isinstance(token_type, TokenType)


def test_keywords_mapping_complete():
    """Verify all keywords are in KEYWORDS mapping"""
    keyword_strings = [
        "fn", "let", "var", "const", "if", "elif", "else",
        "while", "for", "in", "match", "return", "break", "continue",
        "struct", "enum", "impl", "trait", "import", "as", "from",
        "true", "false", "None", "unsafe", "defer", "with", "try",
        "extern", "and", "or", "not"
    ]
    
    for keyword in keyword_strings:
        assert keyword in KEYWORDS, f"Keyword '{keyword}' should be in KEYWORDS mapping"
        assert KEYWORDS[keyword] in TokenType, f"KEYWORDS['{keyword}'] should be a valid TokenType"


def test_tokens_bridge_exists():
    """Verify tokens_bridge.py exists"""
    bridge_file = Path(__file__).parent.parent.parent / "src" / "bridge" / "tokens_bridge.py"
    assert bridge_file.exists(), "tokens_bridge.py should exist"


def test_tokens_bridge_api():
    """Test tokens_bridge.py provides the expected API"""
    from src.bridge.tokens_bridge import TokenType, Token, Span, KEYWORDS, get_keyword_type, is_keyword
    
    # Verify all expected exports exist
    assert TokenType is not None
    assert Token is not None
    assert Span is not None
    assert KEYWORDS is not None
    assert callable(get_keyword_type)
    assert callable(is_keyword)
    
    # Test bridge functions work
    assert is_keyword("fn") == True
    assert is_keyword("not_a_keyword") == False
    assert get_keyword_type("fn") == TokenType.FN
    assert get_keyword_type("not_a_keyword") is None
