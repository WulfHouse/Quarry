"""Initialization and basic functionality tests"""

"""Tests for closure_inline_pass.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from unittest.mock import MagicMock, Mock
from src.passes.closure_inline_pass import ClosureInlinePass
from src import ast
from src.types import FunctionType, IntType, StringType
from src.frontend.tokens import Span


def test_closure_inline_pass_init():
    """Test ClosureInlinePass initialization"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    assert pass_obj.type_checker == type_checker
    assert pass_obj.function_closure_args == {}
    assert pass_obj.param_closure_params == {}
    assert pass_obj.inliner is not None




def test_inline_closures_in_program_empty():
    """Test inline_closures_in_program() with empty program"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    program = ast.Program(imports=[], items=[], span=Span("test.pyrite", 1, 1, 1, 1))
    result = pass_obj.inline_closures_in_program(program)
    
    assert result == program




def test_collect_in_statement_var_decl_with_initializer():
    """Test _collect_in_statement() with VarDecl that has initializer (covers line 63)"""
    type_checker = MagicMock()
    pass_obj = ClosureInlinePass(type_checker)
    
    init = ast.FunctionCall(
        function=ast.Identifier(name="f", span=Span("test.pyrite", 1, 5, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 5, 1, 7)
    )
    stmt = ast.VarDecl(
        name="x",
        type_annotation=None,
        initializer=init,
        mutable=False,
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    
    pass_obj._collect_in_statement(stmt)
    # Should not crash
    assert True


