"""Tests for compound assignment operators (+=, -=, *=, /=)"""

import pytest

pytestmark = pytest.mark.fast  # All tests in this file are fast unit tests

from src.frontend import lex, parse
from src import ast


def test_parse_plus_eq():
    """Test parsing += operator"""
    source = """fn main():
    var x = 5
    x += 3
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.body.statements) == 2
    
    # Check the assignment statement
    assign = func.body.statements[1]
    assert isinstance(assign, ast.Assignment)
    assert assign.op == "+"
    assert isinstance(assign.target, ast.Identifier)
    assert assign.target.name == "x"
    assert isinstance(assign.value, ast.IntLiteral)
    assert assign.value.value == 3


def test_parse_minus_eq():
    """Test parsing -= operator"""
    source = """fn main():
    var x = 10
    x -= 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assign = func.body.statements[1]
    assert isinstance(assign, ast.Assignment)
    assert assign.op == "-"


def test_parse_star_eq():
    """Test parsing *= operator"""
    source = """fn main():
    var x = 5
    x *= 4
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assign = func.body.statements[1]
    assert isinstance(assign, ast.Assignment)
    assert assign.op == "*"


def test_parse_slash_eq():
    """Test parsing /= operator"""
    source = """fn main():
    var x = 20
    x /= 4
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assign = func.body.statements[1]
    assert isinstance(assign, ast.Assignment)
    assert assign.op == "/"


def test_parse_regular_assignment_no_op():
    """Test that regular assignment has op=None"""
    source = """fn main():
    var x = 5
    x = 10
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assign = func.body.statements[1]
    assert isinstance(assign, ast.Assignment)
    assert assign.op is None


def test_parse_compound_assignment_with_expression():
    """Test compound assignment with expression on right side"""
    source = """fn main():
    var x = 5
    x += 2 + 3
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assign = func.body.statements[1]
    assert isinstance(assign, ast.Assignment)
    assert assign.op == "+"
    assert isinstance(assign.value, ast.BinOp)
    assert assign.value.op == "+"

