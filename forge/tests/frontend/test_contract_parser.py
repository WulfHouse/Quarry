"""Tests for contract parsing (@requires, @ensures)"""

import pytest
from forge.src.frontend import lex, parse
from forge.src import ast

def test_parse_requires_attribute():
    """Test that @requires attribute is correctly parsed with expressions"""
    source = """
@requires(x > 0)
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.attributes) == 1
    
    attr = func.attributes[0]
    assert attr.name == "requires"
    assert len(attr.args) == 1
    assert isinstance(attr.args[0], ast.BinOp)
    assert attr.args[0].op == ">"

def test_parse_multiple_requires():
    """Test multiple @requires attributes"""
    source = """
@requires(x > 0)
@requires(y < 10)
fn test(x: i64, y: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert len(func.attributes) == 2
    assert func.attributes[0].name == "requires"
    assert func.attributes[1].name == "requires"

def test_parse_ensures_attribute():
    """Test that @ensures attribute is correctly parsed"""
    source = """
@ensures(result > 0)
fn test(x: i64) -> i64:
    return x
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert func.attributes[0].name == "ensures"
    assert isinstance(func.attributes[0].args[0], ast.BinOp)
    assert func.attributes[0].args[0].left.name == "result"

def test_parse_loop_invariant():
    """Test that @invariant attribute is correctly parsed on loops"""
    source = """
fn test():
    @invariant(i >= 0)
    while i < 10:
        pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    while_stmt = func.body.statements[0]
    assert isinstance(while_stmt, ast.WhileStmt)
    assert len(while_stmt.attributes) == 1
    assert while_stmt.attributes[0].name == "invariant"

def test_parse_struct_invariant():
    """Test that @invariant attribute is correctly parsed on structs"""
    source = """
@invariant(self.x > 0)
struct Point:
    x: i64
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    struct = program.items[0]
    assert isinstance(struct, ast.StructDef)
    assert len(struct.attributes) == 1
    assert struct.attributes[0].name == "invariant"

