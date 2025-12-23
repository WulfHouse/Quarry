import pytest
from src.frontend import lex, parse
from src import ast

def test_parse_move_runtime_closure():
    """Test parsing move runtime closure (SPEC-LANG-0505)"""
    source = """fn test():
    let f = move fn(x: int) -> int: x * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt.initializer, ast.RuntimeClosure)
    assert stmt.initializer.is_move == True

def test_parse_move_parameter_closure():
    """Test parsing move parameter closure (SPEC-LANG-0505)"""
    source = """fn test():
    let f = move fn[i: int]: i * 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    stmt = func.body.statements[0]
    assert isinstance(stmt.initializer, ast.ParameterClosure)
    assert stmt.initializer.is_move == True

