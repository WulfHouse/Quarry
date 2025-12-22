"""Tests for associated types in traits"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker
from src import ast


def test_trait_with_associated_type():
    """Test trait definition with associated type"""
    source = """trait Iterator:
    type Item
    fn next(&self) -> Option[Self::Item]
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    trait = program.items[0]
    assert isinstance(trait, ast.TraitDef)
    assert trait.name == "Iterator"
    assert len(trait.associated_types) == 1
    assert trait.associated_types[0].name == "Item"


def test_associated_type_in_method_signature():
    """Test using associated type in trait method signature"""
    source = """trait Iterator:
    type Item
    fn next(&self) -> Option[Self::Item]
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    trait = program.items[0]
    assert len(trait.methods) == 1
    method = trait.methods[0]
    assert method.return_type is not None
    # Return type should be GenericType with AssociatedTypeRef
    assert isinstance(method.return_type, ast.GenericType)


def test_impl_with_associated_type():
    """Test impl block with associated type implementation"""
    source = """trait Iterator:
    type Item
    fn next(&self) -> Option[Self::Item]

impl Iterator for List[int]:
    type Item = int
    fn next(&self) -> Option[int]:
        return None
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert impl.trait_name == "Iterator"
    assert len(impl.associated_type_impls) == 1
    assert impl.associated_type_impls[0][0] == "Item"


def test_associated_type_parsing_trait_colon_colon():
    """Test parsing Trait::Item syntax in type annotations"""
    source = """trait Iterator:
    type Item

fn process[T: Iterator](iter: T) -> Iterator::Item:
    return None
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[1]
    assert isinstance(func, ast.FunctionDef)
    assert func.return_type is not None
    # Return type should be AssociatedTypeRef
    assert isinstance(func.return_type, ast.AssociatedTypeRef)
    assert func.return_type.trait_name == "Iterator"
    assert func.return_type.associated_type_name == "Item"


def test_associated_type_type_checking():
    """Test type checking validates associated type implementations"""
    source = """trait Iterator:
    type Item
    fn next(&self) -> Option[Self::Item]

impl Iterator for List[int]:
    type Item = int
    fn next(&self) -> Option[int]:
        return Option.None
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors related to associated types
    # (may have other errors, but associated type validation should pass)
    assoc_type_errors = [e for e in type_checker.errors if "associated type" in str(e).lower()]
    assert len(assoc_type_errors) == 0, f"Associated type errors: {assoc_type_errors}"


def test_associated_type_missing_implementation():
    """Test that missing associated type implementation is caught"""
    source = """trait Iterator:
    type Item
    fn next(&self) -> Option[Self::Item]

impl Iterator for List[int]:
    fn next(&self) -> Option[int]:
        return None
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should have type error: missing associated type implementation
    assert type_checker.has_errors(), "Expected type error for missing associated type"
    errors = [str(e) for e in type_checker.errors]
    assert any("associated type" in err.lower() for err in errors), f"Expected associated type error, got: {errors}"


def test_associated_type_invalid_name():
    """Test that invalid associated type name in impl is caught"""
    source = """trait Iterator:
    type Item

impl Iterator for List[int]:
    type Invalid = int
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should have type error: invalid associated type name
    assert type_checker.has_errors(), "Expected type error for invalid associated type name"
    errors = [str(e) for e in type_checker.errors]
    assert any("not declared" in err.lower() for err in errors), f"Expected 'not declared' error, got: {errors}"
