"""Tests for ast.py (Python AST module)"""

import pytest

pytestmark = pytest.mark.fast  # Fast unit tests

from src import ast
from src.frontend.tokens import Span


def test_struct_def_has_attribute():
    """Test StructDef.has_attribute() (covers line 102)"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    
    # Create struct with attributes
    attr1 = ast.Attribute(name="repr", args=["C"], span=span)
    attr2 = ast.Attribute(name="derive", args=["Clone"], span=span)
    struct = ast.StructDef(
        name="Test",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        attributes=[attr1, attr2],
        span=span
    )
    
    assert struct.has_attribute("repr") == True
    assert struct.has_attribute("derive") == True
    assert struct.has_attribute("nonexistent") == False


def test_struct_def_is_repr_c():
    """Test StructDef.is_repr_c() (covers line 106)"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    
    # Create struct with #[repr(C)] attribute
    attr = ast.Attribute(name="repr", args=["C"], span=span)
    struct = ast.StructDef(
        name="Test",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        attributes=[attr],
        span=span
    )
    
    assert struct.is_repr_c() == True
    
    # Test without repr(C) attribute
    struct2 = ast.StructDef(
        name="Test2",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        attributes=[],
        span=span
    )
    assert struct2.is_repr_c() == False
    
    # Test with repr attribute but wrong args
    attr3 = ast.Attribute(name="repr", args=["Rust"], span=span)
    struct3 = ast.StructDef(
        name="Test3",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        attributes=[attr3],
        span=span
    )
    assert struct3.is_repr_c() == False


def test_attribute_post_init():
    """Test Attribute.__post_init__() (covers lines 119-120)"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    
    # Create attribute without args (should default to [])
    attr = ast.Attribute(name="derive", args=None, span=span)
    assert attr.args == []


def test_trait_def_post_init():
    """Test TraitDef.__post_init__() (covers line 157)"""
    span = Span("test.pyrite", 1, 1, 1, 10)
    
    # Create trait without where_clause (should default to [])
    trait = ast.TraitDef(
        name="Test",
        generic_params=[],
        methods=[],
        associated_types=[],
        where_clause=None,
        span=span
    )
    assert trait.where_clause == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
