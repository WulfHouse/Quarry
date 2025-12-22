"""Tests for ast_bridge.py - FFI bridge for AST module

This module tests that ast_bridge.py correctly re-exports all AST symbols
from the Python ast.py implementation. Once FFI bindings are implemented,
these tests will verify the bridge works correctly.
"""

import pytest

pytestmark = pytest.mark.fast  # Fast unit tests - simple imports and checks

from src.bridge import ast_bridge


def test_ast_bridge_all_exports_accessible():
    """Test that all symbols in __all__ are accessible from ast_bridge"""
    # Get all exported symbols
    exported_symbols = set(ast_bridge.__all__)
    
    # Verify each symbol is accessible
    for symbol_name in exported_symbols:
        assert hasattr(ast_bridge, symbol_name), f"{symbol_name} should be accessible from ast_bridge"
        symbol = getattr(ast_bridge, symbol_name)
        assert symbol is not None, f"{symbol_name} should not be None"


def test_ast_bridge_all_matches_exports():
    """Test that __all__ matches what's actually exported"""
    # Get all public attributes (not starting with _)
    public_attrs = {
        name for name in dir(ast_bridge)
        if not name.startswith('_') and name not in ['sys', 'typing', 'dataclasses']
    }
    
    # __all__ should contain all public exports
    exported_symbols = set(ast_bridge.__all__)
    
    # All exported symbols should be in public attrs
    for symbol in exported_symbols:
        assert symbol in public_attrs, f"{symbol} in __all__ should be a public attribute"


def test_ast_bridge_core_classes_importable():
    """Test that core AST classes can be imported and are the correct types"""
    # Test a few key classes to ensure they're properly re-exported
    assert ast_bridge.ASTNode is not None
    assert ast_bridge.Program is not None
    assert ast_bridge.FunctionDef is not None
    assert ast_bridge.Expression is not None
    assert ast_bridge.Statement is not None
    assert ast_bridge.Type is not None


def test_ast_bridge_literals_importable():
    """Test that literal types can be imported"""
    assert ast_bridge.IntLiteral is not None
    assert ast_bridge.FloatLiteral is not None
    assert ast_bridge.StringLiteral is not None
    assert ast_bridge.BoolLiteral is not None
    assert ast_bridge.NoneLiteral is not None


def test_ast_bridge_types_importable():
    """Test that type classes can be imported"""
    assert ast_bridge.PrimitiveType is not None
    assert ast_bridge.ReferenceType is not None
    assert ast_bridge.PointerType is not None
    assert ast_bridge.ArrayType is not None
    assert ast_bridge.GenericType is not None


def test_ast_bridge_imports_from_ast():
    """Test that ast_bridge imports from the correct module (ast.py)"""
    # Verify that the symbols come from ast module
    from src import ast as ast_module
    
    # Check a few key symbols are the same objects
    assert ast_bridge.ASTNode is ast_module.ASTNode
    assert ast_bridge.Program is ast_module.Program
    assert ast_bridge.FunctionDef is ast_module.FunctionDef
