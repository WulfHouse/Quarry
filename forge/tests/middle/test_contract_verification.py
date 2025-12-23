"""Tests for compile-time contract verification (SPEC-LANG-0406)"""

import pytest
from forge.src.frontend import lex, parse
from forge.src.middle.type_checker import type_check, TypeCheckError

def test_prove_true_precondition():
    """Test that proven true preconditions don't cause errors"""
    source = """
@requires(1 == 1)
fn test():
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    assert not tc.has_errors()
    
    # Check that it was marked as proven
    func = program.items[0]
    assert func.attributes[0].args[0].is_proven == True

def test_prove_false_precondition():
    """Test that proven false preconditions cause type errors"""
    source = """
@requires(1 == 2)
fn test():
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    assert tc.has_errors()
    assert any("Precondition will always fail" in str(e) for e in tc.errors)

def test_prove_true_loop_invariant():
    """Test proven true loop invariant"""
    source = """
fn test():
    @invariant(true)
    while true:
        pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    assert not tc.has_errors()
    
    # Check proven flag
    func = program.items[0]
    while_stmt = func.body.statements[0]
    assert while_stmt.attributes[0].args[0].is_proven == True

def test_prove_false_loop_invariant():
    """Test proven false loop invariant"""
    source = """
fn test():
    @invariant(false)
    while true:
        pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    assert tc.has_errors()
    assert any("Loop invariant will always fail" in str(e) for e in tc.errors)

