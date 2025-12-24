"""Tests for enum variant construction ownership"""

import pytest
from src.frontend import lex, parse
from src.middle import type_check, OwnershipAnalyzer
from src import ast


def test_enum_variant_construction_no_move_error():
    """Test that constructing enum variants doesn't trigger move errors"""
    source = """enum Type:
    BoolType
    CharType
    StringType

fn bool_type() -> Type:
    return Type.BoolType

fn char_type() -> Type:
    return Type.CharType

fn string_type() -> Type:
    return Type.StringType
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Type check
    checker = type_check(program)
    
    # Build type environment from type checker
    type_env = {}
    for item in program.items:
        if isinstance(item, ast.FunctionDef):
            # Collect parameter types
            for param in item.params:
                if param.type_annotation:
                    param_type = checker.resolve_type(param.type_annotation)
                    type_env[param.name] = param_type
    
    # Ownership check should not error on enum variant construction
    analyzer = OwnershipAnalyzer()
    analyzer.type_checker = checker
    analyzer.analyze_program(program, type_env)
    
    # Should complete without errors
    assert len(analyzer.errors) == 0, f"Ownership errors: {[str(e) for e in analyzer.errors]}"

