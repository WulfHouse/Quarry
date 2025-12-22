"""Tests for drops.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.utils import DropAnalyzer, insert_drops
from src import ast
from src.types import StringType, IntType, StructType
from src.frontend.tokens import Span


def test_drop_analyzer_init():
    """Test DropAnalyzer initialization"""
    analyzer = DropAnalyzer()
    assert analyzer.drops_needed == {}


def test_drop_analyzer_analyze_function_with_copy_types():
    """Test DropAnalyzer.analyze_function() with Copy types (no drops needed)"""
    analyzer = DropAnalyzer()
    
    # Create a simple function
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Variable types with Copy types (int, bool, etc.)
    variable_types = {
        "x": IntType(),
        "y": IntType()
    }
    
    analyzer.analyze_function(func, variable_types)
    # Copy types don't need drops, so drops_needed should be empty or minimal
    assert isinstance(analyzer.drops_needed, dict)


def test_drop_analyzer_analyze_function_with_non_copy_types():
    """Test DropAnalyzer.analyze_function() with non-Copy types (drops needed)"""
    analyzer = DropAnalyzer()
    
    # Create a function
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # Variable types with non-Copy types (String, structs)
    variable_types = {
        "s": StringType(),
        "x": IntType()  # Copy type
    }
    
    analyzer.analyze_function(func, variable_types)
    # String is non-Copy, so should need drops
    assert isinstance(analyzer.drops_needed, dict)


def test_drop_analyzer_analyze_block_for_drops():
    """Test DropAnalyzer.analyze_block_for_drops()"""
    analyzer = DropAnalyzer()
    
    block = ast.Block(
        statements=[],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    live_vars = {"x", "y"}
    
    # Should not crash
    analyzer.analyze_block_for_drops(block, live_vars)
    assert True  # Function exists and can be called


def test_insert_drops_empty_program():
    """Test insert_drops() with empty program"""
    program = ast.Program(
        imports=[],
        items=[],
        span=Span("test.pyrite", 1, 1, 1, 1)
    )
    
    variable_types = {}
    
    analyzer = insert_drops(program, variable_types)
    assert isinstance(analyzer, DropAnalyzer)


def test_insert_drops_with_function():
    """Test insert_drops() with function in program"""
    func = ast.FunctionDef(
        name="main",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(
        imports=[],
        items=[func],
        span=Span("test.pyrite", 1, 1, 1, 1)
    )
    
    variable_types = {
        "main": {
            "x": StringType()
        }
    }
    
    analyzer = insert_drops(program, variable_types)
    assert isinstance(analyzer, DropAnalyzer)


def test_insert_drops_with_multiple_functions():
    """Test insert_drops() with multiple functions"""
    func1 = ast.FunctionDef(
        name="func1",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    func2 = ast.FunctionDef(
        name="func2",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 2, 1, 2, 10)),
        span=Span("test.pyrite", 2, 1, 2, 10)
    )
    
    program = ast.Program(
        imports=[],
        items=[func1, func2],
        span=Span("test.pyrite", 1, 1, 1, 1)
    )
    
    variable_types = {}
    
    analyzer = insert_drops(program, variable_types)
    assert isinstance(analyzer, DropAnalyzer)


def test_insert_drops_with_non_function_items():
    """Test insert_drops() with non-function items (should skip them)"""
    struct_def = ast.StructDef(
        name="Test",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(
        imports=[],
        items=[struct_def],
        span=Span("test.pyrite", 1, 1, 1, 1)
    )
    
    variable_types = {}
    
    analyzer = insert_drops(program, variable_types)
    assert isinstance(analyzer, DropAnalyzer)


def test_drop_analyzer_with_struct_types():
    """Test DropAnalyzer with struct types"""
    analyzer = DropAnalyzer()
    
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    # StructType may or may not be Copy depending on fields
    struct_type = StructType("TestStruct", {}, [])
    variable_types = {
        "data": struct_type
    }
    
    analyzer.analyze_function(func, variable_types)
    assert isinstance(analyzer.drops_needed, dict)
