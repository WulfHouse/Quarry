"""Tests for symbol_table.py - Symbol table and name resolution

This module tests the SymbolTable and NameResolver classes for edge cases
and uncovered paths to improve test coverage.
"""

import pytest

pytestmark = pytest.mark.fast  # Fast unit tests - simple data structure operations

from src.middle import SymbolTable, Symbol, NameResolver
from src.types import Type, INT, STRING, FunctionType, UNKNOWN, UnknownType
from src.frontend.tokens import Span, TokenType, Token


def test_symbol_table_init():
    """Test SymbolTable initialization"""
    table = SymbolTable()
    assert table.parent is None
    assert table.symbols == {}
    assert table.functions == {}
    assert table.types == {}


def test_symbol_table_init_with_parent():
    """Test SymbolTable initialization with parent"""
    parent = SymbolTable()
    child = SymbolTable(parent=parent)
    assert child.parent is parent


def test_symbol_table_enter_scope():
    """Test entering a new scope"""
    parent = SymbolTable()
    child = parent.enter_scope()
    assert child.parent is parent
    assert child.symbols == {}


def test_symbol_table_exit_scope_with_parent():
    """Test exiting scope when parent exists"""
    parent = SymbolTable()
    child = parent.enter_scope()
    result = child.exit_scope()
    assert result is parent


def test_symbol_table_exit_scope_no_parent():
    """Test exiting scope when no parent (root scope)"""
    root = SymbolTable()
    result = root.exit_scope()
    assert result is None


def test_symbol_table_define():
    """Test defining a symbol"""
    table = SymbolTable()
    symbol = Symbol(name="x", type=INT)
    result = table.define("x", symbol)
    assert result is True
    assert table.symbols["x"] is symbol


def test_symbol_table_define_duplicate():
    """Test defining a duplicate symbol (should return False)"""
    table = SymbolTable()
    symbol1 = Symbol(name="x", type=INT)
    symbol2 = Symbol(name="x", type=STRING)
    assert table.define("x", symbol1) is True
    assert table.define("x", symbol2) is False
    assert table.symbols["x"] is symbol1  # Original should remain


def test_symbol_table_define_function():
    """Test defining a function"""
    table = SymbolTable()
    func_type = FunctionType(param_types=[], return_type=INT)
    symbol = Symbol(name="foo", type=func_type)
    result = table.define_function("foo", symbol)
    assert result is True
    assert table.functions["foo"] is symbol


def test_symbol_table_define_function_duplicate():
    """Test defining a duplicate function (should return False)"""
    table = SymbolTable()
    func_type = FunctionType(param_types=[], return_type=INT)
    symbol1 = Symbol(name="foo", type=func_type)
    symbol2 = Symbol(name="foo", type=func_type)
    assert table.define_function("foo", symbol1) is True
    assert table.define_function("foo", symbol2) is False
    assert table.functions["foo"] is symbol1


def test_symbol_table_define_type():
    """Test defining a type"""
    table = SymbolTable()
    result = table.define_type("MyType", INT)
    assert result is True
    assert table.types["MyType"] is INT


def test_symbol_table_define_type_duplicate():
    """Test defining a duplicate type (should return False)"""
    table = SymbolTable()
    assert table.define_type("MyType", INT) is True
    assert table.define_type("MyType", STRING) is False
    assert table.types["MyType"] is INT  # Original should remain


def test_symbol_table_lookup_in_current_scope():
    """Test looking up a symbol in current scope"""
    table = SymbolTable()
    symbol = Symbol(name="x", type=INT)
    table.define("x", symbol)
    result = table.lookup("x")
    assert result is symbol


def test_symbol_table_lookup_in_parent_scope():
    """Test looking up a symbol in parent scope"""
    parent = SymbolTable()
    symbol = Symbol(name="x", type=INT)
    parent.define("x", symbol)
    
    child = parent.enter_scope()
    result = child.lookup("x")
    assert result is symbol


def test_symbol_table_lookup_not_found():
    """Test looking up a non-existent symbol"""
    table = SymbolTable()
    result = table.lookup("nonexistent")
    assert result is None


def test_symbol_table_lookup_function():
    """Test looking up a function"""
    table = SymbolTable()
    func_type = FunctionType(param_types=[], return_type=INT)
    symbol = Symbol(name="foo", type=func_type)
    table.define_function("foo", symbol)
    result = table.lookup_function("foo")
    assert result is symbol


def test_symbol_table_lookup_function_in_parent():
    """Test looking up a function in parent scope"""
    parent = SymbolTable()
    func_type = FunctionType(param_types=[], return_type=INT)
    symbol = Symbol(name="foo", type=func_type)
    parent.define_function("foo", symbol)
    
    child = parent.enter_scope()
    result = child.lookup_function("foo")
    assert result is symbol


def test_symbol_table_lookup_function_not_found():
    """Test looking up a non-existent function"""
    table = SymbolTable()
    result = table.lookup_function("nonexistent")
    assert result is None


def test_symbol_table_lookup_type():
    """Test looking up a type"""
    table = SymbolTable()
    table.define_type("MyType", INT)
    result = table.lookup_type("MyType")
    assert result is INT


def test_symbol_table_lookup_type_in_parent():
    """Test looking up a type in parent scope"""
    parent = SymbolTable()
    parent.define_type("MyType", INT)
    
    child = parent.enter_scope()
    result = child.lookup_type("MyType")
    assert result is INT


def test_symbol_table_lookup_type_not_found():
    """Test looking up a non-existent type"""
    table = SymbolTable()
    result = table.lookup_type("nonexistent")
    assert result is None


def test_symbol_table_is_defined_in_current_scope_symbol():
    """Test is_defined_in_current_scope for symbols"""
    table = SymbolTable()
    symbol = Symbol(name="x", type=INT)
    table.define("x", symbol)
    assert table.is_defined_in_current_scope("x") is True
    assert table.is_defined_in_current_scope("y") is False


def test_symbol_table_is_defined_in_current_scope_function():
    """Test is_defined_in_current_scope for functions"""
    table = SymbolTable()
    func_type = FunctionType(param_types=[], return_type=INT)
    symbol = Symbol(name="foo", type=func_type)
    table.define_function("foo", symbol)
    assert table.is_defined_in_current_scope("foo") is True


def test_symbol_table_is_defined_in_current_scope_not_in_parent():
    """Test is_defined_in_current_scope doesn't check parent"""
    parent = SymbolTable()
    symbol = Symbol(name="x", type=INT)
    parent.define("x", symbol)
    
    child = parent.enter_scope()
    assert child.is_defined_in_current_scope("x") is False  # Not in current scope


def test_symbol_table_get_all_symbols():
    """Test get_all_symbols includes parent symbols"""
    parent = SymbolTable()
    symbol1 = Symbol(name="x", type=INT)
    parent.define("x", symbol1)
    
    child = parent.enter_scope()
    symbol2 = Symbol(name="y", type=STRING)
    child.define("y", symbol2)
    
    all_symbols = child.get_all_symbols()
    assert "x" in all_symbols
    assert "y" in all_symbols
    assert all_symbols["x"] is symbol1
    assert all_symbols["y"] is symbol2


def test_symbol_table_get_all_symbols_child_overrides_parent():
    """Test get_all_symbols with child overriding parent symbol"""
    parent = SymbolTable()
    symbol1 = Symbol(name="x", type=INT)
    parent.define("x", symbol1)
    
    child = parent.enter_scope()
    symbol2 = Symbol(name="x", type=STRING)
    child.define("x", symbol2)
    
    all_symbols = child.get_all_symbols()
    assert all_symbols["x"] is symbol2  # Child should override parent


def test_name_resolver_init():
    """Test NameResolver initialization"""
    resolver = NameResolver()
    assert resolver.global_scope is not None
    assert resolver.current_scope is resolver.global_scope
    assert resolver.errors == []


def test_name_resolver_error_with_span():
    """Test error recording with span"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    resolver.error("Test error", span)
    assert len(resolver.errors) == 1
    assert "test.py" in resolver.errors[0]
    assert "Test error" in resolver.errors[0]


def test_name_resolver_error_without_span():
    """Test error recording without span"""
    resolver = NameResolver()
    resolver.error("Test error")
    assert len(resolver.errors) == 1
    assert resolver.errors[0] == "Test error"


def test_name_resolver_enter_scope():
    """Test entering a new scope"""
    resolver = NameResolver()
    original_scope = resolver.current_scope
    resolver.enter_scope()
    assert resolver.current_scope is not original_scope
    assert resolver.current_scope.parent is original_scope


def test_name_resolver_exit_scope():
    """Test exiting a scope"""
    resolver = NameResolver()
    original_scope = resolver.current_scope
    resolver.enter_scope()
    resolver.exit_scope()
    assert resolver.current_scope is original_scope


def test_name_resolver_exit_scope_at_root():
    """Test exiting scope at root (should not crash)"""
    resolver = NameResolver()
    # Try to exit root scope - should not crash
    resolver.exit_scope()
    assert resolver.current_scope is resolver.global_scope


def test_name_resolver_define_variable():
    """Test defining a variable"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    result = resolver.define_variable("x", INT, mutable=False, span=span)
    assert result is True
    symbol = resolver.current_scope.lookup("x")
    assert symbol is not None
    assert symbol.name == "x"
    assert symbol.type is INT
    assert symbol.mutable is False
    assert symbol.definition_span is span


def test_name_resolver_define_variable_duplicate():
    """Test defining a duplicate variable (should error)"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    resolver.define_variable("x", INT, mutable=False, span=span)
    result = resolver.define_variable("x", STRING, mutable=False, span=span)
    assert result is False
    assert len(resolver.errors) == 1
    assert "already defined" in resolver.errors[0].lower()


def test_name_resolver_define_variable_duplicate_in_parent():
    """Test defining variable that shadows parent (should succeed)"""
    resolver = NameResolver()
    resolver.define_variable("x", INT, mutable=False)
    resolver.enter_scope()
    # Should be able to shadow parent variable
    result = resolver.define_variable("x", STRING, mutable=False)
    assert result is True


def test_name_resolver_define_function():
    """Test defining a function"""
    resolver = NameResolver()
    func_type = FunctionType(param_types=[], return_type=INT)
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    result = resolver.define_function("foo", func_type, span=span)
    assert result is True
    symbol = resolver.global_scope.lookup_function("foo")
    assert symbol is not None
    assert symbol.name == "foo"
    assert symbol.type is func_type


def test_name_resolver_define_function_duplicate():
    """Test defining a duplicate function (should error)"""
    resolver = NameResolver()
    func_type = FunctionType(param_types=[], return_type=INT)
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    resolver.define_function("foo", func_type, span=span)
    result = resolver.define_function("foo", func_type, span=span)
    assert result is False
    assert len(resolver.errors) == 1
    assert "already defined" in resolver.errors[0].lower()


def test_name_resolver_define_type():
    """Test defining a type"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    result = resolver.define_type("MyType", INT, span=span)
    assert result is True
    typ = resolver.global_scope.lookup_type("MyType")
    assert typ is INT


def test_name_resolver_define_type_duplicate():
    """Test defining a duplicate type (should error)"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    resolver.define_type("MyType", INT, span=span)
    result = resolver.define_type("MyType", STRING, span=span)
    assert result is False
    assert len(resolver.errors) == 1
    assert "already defined" in resolver.errors[0].lower()


def test_name_resolver_define_type_overrides_unknown():
    """Test defining a type that overrides UNKNOWN placeholder"""
    resolver = NameResolver()
    # First define UNKNOWN as placeholder
    resolver.global_scope.define_type("MyType", UNKNOWN)
    
    # Now define the real type - should succeed
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    result = resolver.define_type("MyType", INT, span=span)
    assert result is True
    typ = resolver.global_scope.lookup_type("MyType")
    assert typ is INT
    assert typ is not UNKNOWN


def test_name_resolver_define_type_overrides_unknown_type_instance():
    """Test defining a type that overrides UnknownType instance"""
    resolver = NameResolver()
    # Create an UnknownType instance (not the singleton)
    unknown_instance = UnknownType()
    resolver.global_scope.define_type("MyType", unknown_instance)
    
    # Now define the real type - should succeed (isinstance check)
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    result = resolver.define_type("MyType", INT, span=span)
    assert result is True
    typ = resolver.global_scope.lookup_type("MyType")
    assert typ is INT


def test_name_resolver_lookup_variable():
    """Test looking up a variable"""
    resolver = NameResolver()
    resolver.define_variable("x", INT, mutable=False)
    symbol = resolver.lookup_variable("x")
    assert symbol is not None
    assert symbol.name == "x"
    assert symbol.type is INT


def test_name_resolver_lookup_variable_not_found():
    """Test looking up a non-existent variable (should error)"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    symbol = resolver.lookup_variable("nonexistent", span=span)
    assert symbol is None
    assert len(resolver.errors) == 1
    assert "undefined" in resolver.errors[0].lower()


def test_name_resolver_lookup_variable_in_parent_scope():
    """Test looking up a variable in parent scope"""
    resolver = NameResolver()
    resolver.define_variable("x", INT, mutable=False)
    resolver.enter_scope()
    symbol = resolver.lookup_variable("x")
    assert symbol is not None
    assert symbol.name == "x"


def test_name_resolver_lookup_function():
    """Test looking up a function"""
    resolver = NameResolver()
    func_type = FunctionType(param_types=[], return_type=INT)
    resolver.define_function("foo", func_type)
    symbol = resolver.lookup_function("foo")
    assert symbol is not None
    assert symbol.name == "foo"


def test_name_resolver_lookup_function_not_found_falls_back_to_variable():
    """Test lookup_function falls back to variable lookup"""
    resolver = NameResolver()
    # Define as variable (function pointer)
    func_type = FunctionType(param_types=[], return_type=INT)
    resolver.define_variable("foo", func_type, mutable=False)
    
    # Lookup as function should find the variable
    symbol = resolver.lookup_function("foo")
    assert symbol is not None
    assert symbol.name == "foo"
    assert symbol.type is func_type


def test_name_resolver_lookup_function_not_found():
    """Test looking up a non-existent function"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    symbol = resolver.lookup_function("nonexistent", span=span)
    assert symbol is None
    # Should error from variable lookup fallback
    assert len(resolver.errors) == 1


def test_name_resolver_lookup_type():
    """Test looking up a type"""
    resolver = NameResolver()
    resolver.define_type("MyType", INT)
    typ = resolver.lookup_type("MyType")
    assert typ is INT


def test_name_resolver_lookup_type_not_found():
    """Test looking up a non-existent type (should error)"""
    resolver = NameResolver()
    span = Span(filename="test.py", start_line=1, start_column=1, end_line=1, end_column=5)
    typ = resolver.lookup_type("nonexistent", span=span)
    assert typ is None
    assert len(resolver.errors) == 1
    assert "undefined" in resolver.errors[0].lower()


def test_name_resolver_has_errors():
    """Test has_errors method"""
    resolver = NameResolver()
    assert resolver.has_errors() is False
    resolver.error("Test error")
    assert resolver.has_errors() is True


def test_name_resolver_nested_scopes():
    """Test nested scope resolution"""
    resolver = NameResolver()
    resolver.define_variable("x", INT, mutable=False)
    resolver.enter_scope()
    resolver.define_variable("y", STRING, mutable=False)
    resolver.enter_scope()
    resolver.define_variable("z", INT, mutable=False)
    
    # Should find all variables
    assert resolver.lookup_variable("x") is not None
    assert resolver.lookup_variable("y") is not None
    assert resolver.lookup_variable("z") is not None
    
    resolver.exit_scope()
    # z should not be found in parent scope
    assert resolver.lookup_variable("z") is None
    assert resolver.lookup_variable("y") is not None
