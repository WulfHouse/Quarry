"""Edge cases and complex scenarios"""

"""Tests for closure_inline_pass.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from unittest.mock import MagicMock, Mock
from src.passes.closure_inline_pass import ClosureInlinePass
from src import ast
from src.types import FunctionType, IntType, StringType
from src.frontend.tokens import Span


def test_identify_closure_parameters_no_functions():
    """Test _identify_closure_parameters() with no functions"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    program = ast.Program(imports=[], items=[], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._identify_closure_parameters(program)
    
    assert pass_obj.param_closure_params == {}




def test_identify_closure_parameters_with_function_no_closure_params():
    """Test _identify_closure_parameters() with function without closure params"""
    type_checker = MagicMock()
    type_checker.resolve_type = MagicMock(return_value=IntType())
    pass_obj = ClosureInlinePass(type_checker)
    
    # param.type_annotation is a Type object, not an AST node
    param = ast.Param(
        name="x",
        type_annotation=IntType(),  # Use Type object directly
        span=Span("test.pyrite", 1, 10, 1, 13)
    )
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[param],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._identify_closure_parameters(program)
    
    # Should not have closure params (IntType is not FunctionType)
    assert "test" not in pass_obj.param_closure_params or pass_obj.param_closure_params["test"] == {}




def test_identify_closure_parameters_with_closure_param():
    """Test _identify_closure_parameters() with function with closure param"""
    type_checker = MagicMock()
    func_type = FunctionType([IntType()], IntType())
    type_checker.resolve_type = MagicMock(return_value=func_type)
    pass_obj = ClosureInlinePass(type_checker)
    
    # param.type_annotation is a Type object
    param = ast.Param(
        name="f",
        type_annotation=func_type,  # Use FunctionType directly
        span=Span("test.pyrite", 1, 10, 1, 12)
    )
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[param],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._identify_closure_parameters(program)
    
    # Should identify closure param
    assert "test" in pass_obj.param_closure_params
    assert "f" in pass_obj.param_closure_params["test"]




def test_identify_closure_parameters_no_type_annotation():
    """Test _identify_closure_parameters() with param without type annotation"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    param = ast.Param(
        name="x",
        type_annotation=None,
        span=Span("test.pyrite", 1, 10, 1, 11)
    )
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[param],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._identify_closure_parameters(program)
    
    # Should not identify as closure param (no type annotation)
    assert "test" not in pass_obj.param_closure_params or pass_obj.param_closure_params["test"] == {}




def test_identify_closure_parameters_with_function_type():
    """Test _identify_closure_parameters() identifies FunctionType as closure param (covers lines 143, 146)"""
    type_checker = MagicMock()
    func_type = FunctionType([IntType()], IntType())
    type_checker.resolve_type = MagicMock(return_value=func_type)
    pass_obj = ClosureInlinePass(type_checker)
    
    param = ast.Param(
        name="f",
        type_annotation=func_type,
        span=Span("test.pyrite", 1, 10, 1, 12)
    )
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[param],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    pass_obj._identify_closure_parameters(program)
    
    # Should identify closure param
    assert "test" in pass_obj.param_closure_params
    assert "f" in pass_obj.param_closure_params["test"]
    assert pass_obj.param_closure_params["test"]["f"] == 0


