"""Tests for @safety_critical attribute parsing (SPEC-LANG-0408)"""

import pytest
from forge.src.frontend import lex, parse
from forge.src import ast

def test_parse_safety_critical_attribute():
    """Test that @safety_critical attribute is correctly parsed"""
    source = """
@safety_critical
@requires(x > 0)
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.attributes) == 2
    
    # Check that @safety_critical is parsed
    safety_critical_attr = None
    for attr in func.attributes:
        if attr.name == "safety_critical":
            safety_critical_attr = attr
            break
    
    assert safety_critical_attr is not None
    assert safety_critical_attr.name == "safety_critical"
    assert len(safety_critical_attr.args) == 0  # @safety_critical takes no arguments

def test_safety_critical_with_contracts():
    """Test that @safety_critical can be combined with contract attributes"""
    source = """
@safety_critical
@requires(ptr != null)
@ensures(result > 0)
fn sensitive_op(ptr: *u8) -> i64:
    return 42
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    
    # Check that all attributes are present
    attr_names = [attr.name for attr in func.attributes]
    assert "safety_critical" in attr_names
    assert "requires" in attr_names
    assert "ensures" in attr_names

