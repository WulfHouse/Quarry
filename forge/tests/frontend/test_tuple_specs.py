"""Tests for SPEC-LANG-0101 (Tuple Literals) and SPEC-LANG-0111 (Tuple Destructuring)"""

import pytest

pytestmark = pytest.mark.fast

from src.frontend import lex, parse
from src import ast


def test_spec_lang_0101_tuple_literal():
    """SPEC-LANG-0101: Verify tuple literal parsing"""
    source = """fn main():
    let x = (1, "a")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt, ast.VarDecl)
    assert isinstance(stmt.initializer, ast.TupleLiteral)
    assert len(stmt.initializer.elements) == 2
    assert isinstance(stmt.initializer.elements[0], ast.IntLiteral)
    assert isinstance(stmt.initializer.elements[1], ast.StringLiteral)


def test_spec_lang_0111_tuple_destructuring():
    """SPEC-LANG-0111: Verify tuple destructuring in let statements"""
    source = """fn main():
    let (a, b) = (1, 2)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt, ast.VarDecl)
    assert isinstance(stmt.pattern, ast.TuplePattern)
    assert len(stmt.pattern.elements) == 2
    assert isinstance(stmt.pattern.elements[0], ast.IdentifierPattern)
    assert isinstance(stmt.pattern.elements[1], ast.IdentifierPattern)
    assert stmt.pattern.elements[0].name == "a"
    assert stmt.pattern.elements[1].name == "b"

