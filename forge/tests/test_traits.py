"""Tests for trait system"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src import ast


def test_parse_basic_trait():
    """Test parsing basic trait definition"""
    source = """trait Display:
    fn to_string(&self) -> String
"""
    tokens = lex(source)
    program = parse(tokens)
    
    trait = program.items[0]
    assert isinstance(trait, ast.TraitDef)
    assert trait.name == "Display"
    assert len(trait.methods) == 1
    assert trait.methods[0].name == "to_string"


def test_parse_trait_with_default_method():
    """Test parsing trait with default method implementation"""
    source = """trait Printable:
    fn to_string(&self) -> String
    
    fn print(&self):
        print("test")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    trait = program.items[0]
    assert isinstance(trait, ast.TraitDef)
    assert len(trait.methods) == 2
    # First method has no default
    assert trait.methods[0].default_body is None
    # Second method has default
    assert trait.methods[1].default_body is not None


def test_parse_trait_implementation():
    """Test parsing trait implementation"""
    source = """struct Point:
    x: int
    y: int

impl Display for Point:
    fn to_string(&self) -> String:
        return "Point"
"""
    tokens = lex(source)
    program = parse(tokens)
    
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert impl.trait_name == "Display"
    assert impl.type_name == "Point"
    assert len(impl.methods) == 1


def test_parse_inherent_impl():
    """Test parsing inherent implementation (no trait)"""
    source = """struct Point:
    x: int

impl Point:
    fn new(x: int) -> Point:
        return Point { x: x }
"""
    tokens = lex(source)
    program = parse(tokens)
    
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert impl.trait_name is None  # Inherent impl
    assert impl.type_name == "Point"


def test_parse_generic_trait():
    """Test parsing generic trait"""
    source = """trait Container[T]:
    fn insert(&mut self, item: T)
    fn len(&self) -> int
"""
    tokens = lex(source)
    program = parse(tokens)
    
    trait = program.items[0]
    assert isinstance(trait, ast.TraitDef)
    assert len(trait.generic_params) == 1
    assert trait.generic_params[0].name == "T"


def test_parse_generic_impl():
    """Test parsing generic trait implementation"""
    source = """struct List[T]:
    data: int

impl[T] Display for List[T]:
    fn to_string(&self) -> String:
        return "List"
"""
    tokens = lex(source)
    program = parse(tokens)
    
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert len(impl.generic_params) == 1
    assert impl.generic_params[0].name == "T"


def test_parse_impl_with_where_clause():
    """Test parsing impl with where clause"""
    source = """struct Wrapper[T]:
    value: T

impl[T] Display for Wrapper[T] where T: Display:
    fn to_string(&self) -> String:
        return "Wrapper"
"""
    tokens = lex(source)
    program = parse(tokens)
    
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert len(impl.where_clause) == 1
    assert impl.where_clause[0][0] == "T"  # Type parameter
    assert "Display" in impl.where_clause[0][1]  # Trait bound

