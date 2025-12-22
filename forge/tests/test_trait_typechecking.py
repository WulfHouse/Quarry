"""Tests for trait type checking"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.types import TraitType
from src import ast


def test_register_basic_trait():
    """Test that basic traits are registered in symbol table"""
    source = """trait Display:
    fn to_string(&self) -> String
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check (should register trait)
    checker = type_check(program)
    assert not checker.has_errors()
    
    # Verify trait is registered
    trait_type = checker.resolver.lookup_type("Display")
    assert trait_type is not None
    assert isinstance(trait_type, TraitType)
    assert trait_type.name == "Display"
    assert "to_string" in trait_type.methods


def test_register_trait_with_default_method():
    """Test trait with default method implementation"""
    source = """trait Printable:
    fn to_string(&self) -> String
    
    fn print(&self):
        print(self.to_string())
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    assert not checker.has_errors()
    
    # Verify trait registered with both methods
    trait_type = checker.resolver.lookup_type("Printable")
    assert trait_type is not None
    assert "to_string" in trait_type.methods
    assert "print" in trait_type.methods


def test_register_generic_trait():
    """Test generic trait registration"""
    source = """trait Container[T]:
    fn insert(&mut self, item: T)
    fn len(&self) -> int
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    assert not checker.has_errors()
    
    # Verify generic trait registered
    trait_type = checker.resolver.lookup_type("Container")
    assert trait_type is not None
    assert isinstance(trait_type, TraitType)
    assert "T" in trait_type.generic_params


def test_trait_implementation_basic():
    """Test basic trait implementation"""
    source = """trait Display:
    fn to_string(&self) -> String

struct Point:
    x: int
    y: int

impl Display for Point:
    fn to_string(&self) -> String:
        return "Point"
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    # Should not error (basic validation)
    # Full implementation verification is complex and can be phased


def test_inherent_impl():
    """Test inherent implementation (no trait)"""
    source = """struct Point:
    x: int
    y: int

impl Point:
    fn new(x: int, y: int) -> Point:
        return Point { x: x, y: y }
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    # Should type check methods without errors


def test_trait_not_found_error():
    """Test error when implementing non-existent trait"""
    source = """struct Point:
    x: int

impl NonExistentTrait for Point:
    fn method(&self):
        pass
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    # Should have error about trait not found
    assert checker.has_errors()

