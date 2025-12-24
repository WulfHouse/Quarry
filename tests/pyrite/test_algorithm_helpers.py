"""Tests for algorithmic helpers (SPEC-LANG-0510)"""

import pytest
from pathlib import Path
import sys

# Add forge to path
_repo_root = Path(__file__).parent.parent.parent
_forge_path = _repo_root / "forge"
if str(_forge_path) not in sys.path:
    sys.path.insert(0, str(_forge_path))

from forge.src.frontend import lex, parse
from forge.src import ast


def test_parse_vectorize_function():
    """Test that vectorize function can be parsed"""
    source = """
fn vectorize[width: int, unroll: int](
    count: int,
    body: fn[i: int]:
):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "vectorize"
    assert len(func.compile_time_params) == 2
    assert len(func.params) == 2
    # Second param should be a parameter closure
    assert isinstance(func.params[1].type_annotation, ast.FunctionType)


def test_parse_parallelize_function():
    """Test that parallelize function can be parsed"""
    source = """
fn parallelize[workers: int, chunk_size: int](
    count: int,
    body: fn[i: int]:
):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "parallelize"


def test_parse_tile_function():
    """Test that tile function can be parsed"""
    source = """
fn tile[block_size: int](
    dim1: int,
    dim2: int,
    body: fn[i_block: int, j_block: int]:
):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "tile"
    assert len(func.compile_time_params) == 1
    assert len(func.params) == 3


def test_parse_vectorize_call():
    """Test that vectorize can be called with parameter closure"""
    source = """
fn test():
    vectorize[8, 4](100, fn[i: int]:
        i * 2
    )
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert len(func.body.statements) == 1
    stmt = func.body.statements[0]
    assert isinstance(stmt, ast.ExpressionStmt)
    call = stmt.expression
    assert isinstance(call, ast.FunctionCall)
    assert call.function.name == "vectorize"
    # Should have parameter closure as argument
    assert len(call.arguments) == 2
    assert isinstance(call.arguments[1], ast.ParameterClosure)


def test_parse_parallelize_call():
    """Test that parallelize can be called with parameter closure"""
    source = """
fn test():
    parallelize[4, 10](100, fn[i: int]:
        process(i)
    )
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    call = func.body.statements[0].expression
    assert isinstance(call, ast.FunctionCall)
    assert call.function.name == "parallelize"
    assert isinstance(call.arguments[1], ast.ParameterClosure)


def test_parse_tile_call():
    """Test that tile can be called with parameter closure"""
    source = """
fn test():
    tile[64](100, 200, fn[i_block: int, j_block: int]:
        compute(i_block, j_block)
    )
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert len(program.items) == 1
    func = program.items[0]
    call = func.body.statements[0].expression
    assert isinstance(call, ast.FunctionCall)
    assert call.function.name == "tile"
    assert isinstance(call.arguments[2], ast.ParameterClosure)
    # Parameter closure should have 2 params
    assert len(call.arguments[2].params) == 2

