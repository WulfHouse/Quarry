import pytest
from src.middle import type_check
from src.frontend import lex, parse
from src.types import ReferenceType

def test_lifetime_elision_single_param():
    """Test basic lifetime elision (SPEC-LANG-0205)"""
    source = """fn first(s: &String) -> &String:
    return s
"""
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    
    assert not checker.has_errors()
    # Check the symbol table for 'first'
    symbol = checker.resolver.global_scope.lookup_function("first")
    assert symbol is not None
    func_type = symbol.type
    
    # Verify lifetimes were elided/inferred
    assert isinstance(func_type.param_types[0], ReferenceType)
    assert func_type.param_types[0].lifetime == "a"
    assert isinstance(func_type.return_type, ReferenceType)
    assert func_type.return_type.lifetime == "a"

def test_lifetime_elision_multiple_params_no_elision():
    """Test that no elision occurs with multiple reference parameters"""
    source = """fn choose(s1: &String, s2: &String) -> &String:
    return s1
"""
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    
    # In Rust this would be an error if return type is a reference
    # Our simple implementation doesn't error yet but shouldn't elide
    symbol = checker.resolver.global_scope.lookup_function("choose")
    assert symbol is not None
    func_type = symbol.type
    
    assert func_type.param_types[0].lifetime is None
    assert func_type.param_types[1].lifetime is None
    assert func_type.return_type.lifetime is None

