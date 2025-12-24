"""Tests for match expressions without case keyword"""

import pytest
from src.frontend import lex, parse
from src import ast


def test_match_without_case_keyword():
    """Test match expression with Python-like syntax (no case keyword)"""
    source = """fn test_match(x: Option[int]) -> Option[int]:
    match x:
        Option::Some(val):
            return Option.Some(val)
        None:
            return Option.None
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    match_stmt = func.body.statements[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert len(match_stmt.arms) == 2
    # First arm should have pattern without case keyword
    assert match_stmt.arms[0].pattern is not None


def test_match_with_case_keyword():
    """Test match expression with case keyword (still supported)"""
    source = """fn test_match(x: int) -> int:
    match x:
        case 1:
            return 10
        case 2:
            return 20
        case _:
            return 0
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    match_stmt = func.body.statements[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert len(match_stmt.arms) == 3


def test_match_mixed_syntax():
    """Test that both syntaxes can be used (though not recommended)"""
    source = """fn test_match(x: int) -> int:
    match x:
        case 1:
            return 10
        2:  # Without case
            return 20
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    match_stmt = func.body.statements[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert len(match_stmt.arms) == 2

