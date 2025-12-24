"""Tests for struct field named 'type'"""

import pytest
from src.frontend import lex, parse
from src import ast


def test_struct_field_named_type():
    """Test struct with field named 'type' (keyword used as identifier)"""
    source = """struct Token:
    type: TokenType
    value: Option[String]
    span: Span
"""
    tokens = lex(source)
    program = parse(tokens)
    
    struct_def = program.items[0]
    assert isinstance(struct_def, ast.StructDef)
    assert struct_def.name == "Token"
    assert len(struct_def.fields) == 3
    # First field should be named 'type'
    assert struct_def.fields[0].name == "type"
    assert struct_def.fields[1].name == "value"
    assert struct_def.fields[2].name == "span"

