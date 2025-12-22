"""Tests for where clauses"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker
from src import ast


def test_function_with_where_clause():
    """Test function definition with where clause"""
    source = """trait Display:
    fn display(&self)

trait Clone:
    fn clone(&self) -> Self

fn process[T]() where T: Display + Clone:
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 3
    func = program.items[2]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "process"
    assert len(func.where_clause) == 1
    assert func.where_clause[0][0] == "T"
    assert "Display" in func.where_clause[0][1]
    assert "Clone" in func.where_clause[0][1]


def test_struct_with_where_clause():
    """Test struct definition with where clause"""
    source = """trait Display:
    fn display(&self)

struct Container[T] where T: Display:
    value: T
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    struct = program.items[1]
    assert isinstance(struct, ast.StructDef)
    assert struct.name == "Container"
    assert len(struct.where_clause) == 1
    assert struct.where_clause[0][0] == "T"
    assert "Display" in struct.where_clause[0][1]


def test_impl_with_where_clause():
    """Test impl block with where clause"""
    source = """trait Display:
    fn display(&self)

struct Container[T]:
    value: T

impl[T] Display for Container[T] where T: Display:
    fn display(&self):
        pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 3
    impl = program.items[2]
    assert isinstance(impl, ast.ImplBlock)
    assert impl.trait_name == "Display"
    assert len(impl.where_clause) == 1
    assert impl.where_clause[0][0] == "T"
    assert "Display" in impl.where_clause[0][1]


def test_trait_with_where_clause():
    """Test trait definition with where clause"""
    source = """trait Display:
    fn display(&self)

trait Iterator[T] where T: Display:
    type Item
    fn next(&self) -> Option[Self::Item]
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    trait = program.items[1]
    assert isinstance(trait, ast.TraitDef)
    assert trait.name == "Iterator"
    assert len(trait.where_clause) == 1
    assert trait.where_clause[0][0] == "T"
    assert "Display" in trait.where_clause[0][1]


def test_where_clause_multiple_bounds():
    """Test where clause with multiple trait bounds"""
    source = """trait Display:
    fn display(&self)

trait Clone:
    fn clone(&self) -> Self

fn process[T]() where T: Display + Clone:
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[2]
    assert len(func.where_clause[0][1]) == 2
    assert "Display" in func.where_clause[0][1]
    assert "Clone" in func.where_clause[0][1]


def test_where_clause_multiple_type_params():
    """Test where clause with multiple type parameters"""
    source = """trait Display:
    fn display(&self)

trait Clone:
    fn clone(&self) -> Self

fn process[T, U]() where T: Display, U: Clone:
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[2]
    assert len(func.where_clause) == 2
    assert func.where_clause[0][0] == "T"
    assert func.where_clause[1][0] == "U"


def test_where_clause_parsing():
    """Test that where clause parses correctly"""
    source = """fn test[T]() where T: Display:
    pass
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert program is not None
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.where_clause) > 0
