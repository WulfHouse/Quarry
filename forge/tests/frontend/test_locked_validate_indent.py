"""Test for indentation in locked_validate.pyrite"""

import pytest
from src.frontend import lex, parse
from src import ast


def test_locked_validate_parses():
    """Test that locked_validate.pyrite parses correctly"""
    # Use textwrap.dedent to handle indentation in triple-quoted strings
    import textwrap
    source = textwrap.dedent("""\
        # Locked validation operations for Quarry
        #
        # This module provides validation of lockfile consistency.
        # This is the Pyrite implementation replacing Python validation logic in:
        # - quarry/main.py: cmd_build() validation when --locked flag is set
        #
        # Implementation note: Requires JSON parsing for dependency data.
        # The core logic is implemented in C (locked_validate.c) and called via FFI.
        # This Pyrite module provides the FFI declarations and wrapper functions.

        # FFI declarations for C implementation
        # Validate lockfile matches TOML dependencies (structural checks only)
        # Version constraint checking is done in Python bridge (calls version_bridge)
        # Input: toml_deps_json (JSON string: {"name": DependencySource, ...})
        #        lockfile_deps_json (JSON string: {"name": DependencySource, ...})
        # Output: Writes validation result JSON to result buffer, sets result_len
        #         Result: {"valid": true/false, "errors": [...], "warnings": [...]}
        # Returns: 0 on success, -1 on error
        extern "C" fn validate_locked_deps_c(toml_deps_json: *const u8, toml_json_len: i64,
                                              lockfile_deps_json: *const u8, lockfile_json_len: i64,
                                              result: *mut u8, result_cap: i64, result_len: *mut i64) -> i32

        # Public API: Validate locked dependencies
        extern "C" fn validate_locked_deps(toml_deps_json: *const u8, toml_json_len: i64,
                                            lockfile_deps_json: *const u8, lockfile_json_len: i64,
                                            result: *mut u8, result_cap: i64, result_len: *mut i64) -> i32:
            return validate_locked_deps_c(toml_deps_json, toml_json_len, lockfile_deps_json, lockfile_json_len, result, result_cap, result_len)
        """)
    tokens = lex(source)
    program = parse(tokens)
    
    # Should have 2 items: 2 extern functions
    assert len(program.items) == 2
    assert isinstance(program.items[0], ast.FunctionDef)
    assert isinstance(program.items[1], ast.FunctionDef)
    assert program.items[0].is_extern == True
    assert program.items[1].is_extern == True
    # First one has no body (declaration only)
    assert len(program.items[0].body.statements) == 0
    # Second one has a body
    assert len(program.items[1].body.statements) == 1
    assert isinstance(program.items[1].body.statements[0], ast.ReturnStmt)

