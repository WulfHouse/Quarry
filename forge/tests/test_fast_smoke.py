"""Minimal fast smoke test for Lane 1 validation"""

import pytest

pytestmark = pytest.mark.fast  # All tests in this file are fast unit tests

from src.frontend import lex
from src.frontend import parse
from src.middle import type_check


def test_smoke_lex_parse_typecheck():
    """Minimal end-to-end test: lex → parse → typecheck"""
    source = """fn main() -> int:
    return 42
"""
    # Lex
    tokens = lex(source)
    assert len(tokens) > 0
    
    # Parse
    program = parse(tokens)
    assert program is not None
    assert len(program.items) > 0
    
    # Type check
    checker = type_check(program)
    assert not checker.has_errors()
