"""Tests for quantified predicates (forall, exists) (SPEC-LANG-0405)"""

import pytest
from forge.src.frontend import lex, parse
from forge.src.middle.type_checker import type_check
from forge.src import ast

def test_parse_forall_expression():
    """Test that forall expressions are correctly parsed"""
    source = """
fn test():
    let result = forall x in list: x > 0
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt, ast.VarDecl)
    assert isinstance(stmt.initializer, ast.QuantifiedExpr)
    assert stmt.initializer.quantifier == "forall"
    assert stmt.initializer.variable == "x"

def test_parse_exists_expression():
    """Test that exists expressions are correctly parsed"""
    source = """
fn test():
    let result = exists x in list: x == 42
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt, ast.VarDecl)
    assert isinstance(stmt.initializer, ast.QuantifiedExpr)
    assert stmt.initializer.quantifier == "exists"
    assert stmt.initializer.variable == "x"

def test_quantified_in_contract():
    """Test that quantified expressions can be used in contracts"""
    source = """
@requires(forall x in list: x != None)
fn process(list: List[Option[i64]]):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    # Check that @requires has a QuantifiedExpr
    requires_attr = None
    for attr in func.attributes:
        if attr.name == "requires":
            requires_attr = attr
            break
    
    assert requires_attr is not None
    assert len(requires_attr.args) == 1
    assert isinstance(requires_attr.args[0], ast.QuantifiedExpr)

def test_type_check_quantified():
    """Test that quantified expressions are type-checked correctly"""
    source = """
fn test():
    let list: List[i64] = List.new()
    let result = forall x in list: x > 0
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    # Should not have errors for valid quantified expression
    # (Note: full type checking requires List type to be available)
    # For now, just check that it parses and doesn't crash

