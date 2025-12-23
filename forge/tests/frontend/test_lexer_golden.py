import pytest
import os
from src.frontend import lex
from src.frontend.tokens import TokenType

def test_lexer_golden_sample():
    """Golden test for lexer on a sample file"""
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "lexer", "sample.pyrite")
    with open(fixture_path, "r") as f:
        source = f.read()
    
    tokens = lex(source, filename="sample.pyrite")
    
    # Basic verification
    assert tokens[0].type == TokenType.FN
    assert any(t.type == TokenType.STRING for t in tokens)
    assert any(t.type == TokenType.INDENT for t in tokens)
    assert tokens[-1].type == TokenType.EOF
    
    # Verify that we don't have any ERROR tokens
    assert all(t.type != TokenType.ERROR for t in tokens)

