import pytest
from src.middle import type_check
from src.frontend import lex, parse

def test_constant_expression_eval():
    """Test constant expression evaluation for const (SPEC-LANG-0216)"""
    source = """const X: int = 2 + 3 * 4
"""
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    
    assert not checker.has_errors()
    # Check the symbol table for 'X' in global scope
    symbol = checker.resolver.global_scope.lookup("X")
    assert symbol is not None
    # We don't evaluate the VALUE of the const yet in type checker, 
    # but we evaluate the TYPE and any expression used in TYPE (like array size)
    from src.types import INT
    assert symbol.type == INT

def test_constant_expression_array_size():
    """Test constant expression evaluation for array size (SPEC-LANG-0216)"""
    source = """const arr: [int; 2 + 3] = [1, 2, 3, 4, 5]
"""
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    
    assert not checker.has_errors()
    from src.types import ArrayType, INT
    # Check global scope for 'arr'
    symbol = checker.resolver.global_scope.lookup("arr")
    assert symbol is not None
    assert isinstance(symbol.type, ArrayType)
    assert symbol.type.size == 5
    assert symbol.type.element == INT

def test_constant_expression_negative_size():
    """Test error for negative array size"""
    source = """fn test():
    let arr: [int; 2 - 5] = [1]
"""
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    
    assert checker.has_errors()
    assert any("negative" in err.message for err in checker.errors)

def test_constant_expression_div_zero():
    """Test error for division by zero in constant expression"""
    source = """fn test():
    let arr: [int; 10 / 0] = [1]
"""
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    
    assert checker.has_errors()
    assert any("Division by zero" in err.message for err in checker.errors)

