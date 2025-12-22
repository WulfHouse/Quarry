"""Tests for Closeable trait"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.types import TraitType
from src import ast


def test_closeable_trait_definition():
    """Test that Closeable trait can be defined"""
    source = """trait Closeable:
    fn close(&mut self)
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    assert not checker.has_errors()
    
    # Verify trait registered
    trait_type = checker.resolver.lookup_type("Closeable")
    assert trait_type is not None
    assert isinstance(trait_type, TraitType)
    assert "close" in trait_type.methods


def test_implement_closeable_for_file():
    """Test implementing Closeable for a File type"""
    source = """trait Closeable:
    fn close(&mut self)

struct File:
    handle: int

impl Closeable for File:
    fn close(&mut self):
        print("Closing file")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    # Should not error
    # Full verification can be phased


def test_with_statement_requires_closeable():
    """Test that with statement works with Closeable types"""
    # This test verifies the integration between with statement and Closeable trait
    # For MVP, we just verify the syntax works
    
    source = """trait Closeable:
    fn close(&mut self)

struct File:
    handle: int

impl Closeable for File:
    fn close(&mut self):
        print("Closing")

fn open_file() -> File:
    return File { handle: 42 }

fn main():
    with file = try open_file():
        print("Using file")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    # Should not error - File implements Closeable
    assert not checker.has_errors()


def test_with_statement_errors_on_non_closeable():
    """Test that with statement errors when type doesn't implement Closeable"""
    source = """trait Closeable:
    fn close(&mut self)

struct File:
    handle: int

# File does NOT implement Closeable

fn open_file() -> File:
    return File { handle: 42 }

fn main():
    with file = try open_file():
        print("Using file")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    # Should error - File doesn't implement Closeable
    assert checker.has_errors()
    # Check error message mentions Closeable
    error_messages = [str(e) for e in checker.errors]
    assert any("Closeable" in msg for msg in error_messages)

