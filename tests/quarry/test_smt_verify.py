"""Tests for SMT solver integration (SPEC-LANG-0409)"""

import pytest
from pathlib import Path
import tempfile
import sys

# Add forge to path
_repo_root = Path(__file__).parent.parent.parent
_forge_path = _repo_root / "forge"
if str(_forge_path) not in sys.path:
    sys.path.insert(0, str(_forge_path))

from forge.src.frontend import lex, parse
from forge.src import ast
from quarry.smt_verify import SMTVerifier, SMTTranslationError, cmd_verify


def test_translate_bool_literal():
    """Test translation of boolean literals"""
    verifier = SMTVerifier()
    
    true_lit = ast.BoolLiteral(value=True, span=None)
    false_lit = ast.BoolLiteral(value=False, span=None)
    
    assert verifier._translate_expression(true_lit) == "true"
    assert verifier._translate_expression(false_lit) == "false"


def test_translate_int_literal():
    """Test translation of integer literals"""
    verifier = SMTVerifier()
    
    int_lit = ast.IntLiteral(value=42, span=None)
    assert verifier._translate_expression(int_lit) == "42"


def test_translate_identifier():
    """Test translation of identifiers"""
    verifier = SMTVerifier()
    
    ident = ast.Identifier(name="x", span=None)
    assert verifier._translate_expression(ident) == "x"


def test_translate_binary_operators():
    """Test translation of binary operators"""
    verifier = SMTVerifier()
    
    # Test ==
    left = ast.Identifier(name="x", span=None)
    right = ast.IntLiteral(value=5, span=None)
    binop = ast.BinOp(left=left, op="==", right=right, span=None)
    assert verifier._translate_expression(binop) == "(= x 5)"
    
    # Test <
    binop_lt = ast.BinOp(left=left, op="<", right=right, span=None)
    assert verifier._translate_expression(binop_lt) == "(< x 5)"
    
    # Test and
    left_bool = ast.BoolLiteral(value=True, span=None)
    right_bool = ast.BoolLiteral(value=False, span=None)
    binop_and = ast.BinOp(left=left_bool, op="and", right=right_bool, span=None)
    assert verifier._translate_expression(binop_and) == "(and true false)"


def test_translate_unary_operators():
    """Test translation of unary operators"""
    verifier = SMTVerifier()
    
    # Test not
    operand = ast.BoolLiteral(value=True, span=None)
    unary_not = ast.UnaryOp(op="not", operand=operand, span=None)
    assert verifier._translate_expression(unary_not) == "(not true)"
    
    # Test unary minus
    int_operand = ast.IntLiteral(value=5, span=None)
    unary_minus = ast.UnaryOp(op="-", operand=int_operand, span=None)
    assert verifier._translate_expression(unary_minus) == "(- 5)"


def test_translate_unsupported_operator():
    """Test that unsupported operators raise error"""
    verifier = SMTVerifier()
    
    left = ast.Identifier(name="x", span=None)
    right = ast.Identifier(name="y", span=None)
    binop = ast.BinOp(left=left, op="%", right=right, span=None)  # Unsupported
    
    with pytest.raises(SMTTranslationError, match="Unsupported operator"):
        verifier._translate_expression(binop)


def test_verify_function_with_requires():
    """Test verifying a function with @requires contract"""
    verifier = SMTVerifier()
    
    # Create a simple function with @requires
    source = """
@requires(x > 0)
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify
    success, messages = verifier.verify_function_contracts(program, "test")
    
    # Should find the function and attempt verification
    assert isinstance(success, bool)
    assert isinstance(messages, list)
    assert len(messages) > 0


def test_verify_function_with_ensures():
    """Test verifying a function with @ensures contract"""
    verifier = SMTVerifier()
    
    source = """
@ensures(result > 0)
fn test(x: i64) -> i64:
    return x
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    success, messages = verifier.verify_function_contracts(program, "test")
    
    assert isinstance(success, bool)
    assert isinstance(messages, list)


def test_verify_function_not_found():
    """Test verifying a non-existent function"""
    verifier = SMTVerifier()
    
    source = """
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    success, messages = verifier.verify_function_contracts(program, "nonexistent")
    
    assert success is False
    assert len(messages) > 0
    assert "not found" in messages[0].lower()


def test_verify_function_no_contracts():
    """Test verifying a function without contracts"""
    verifier = SMTVerifier()
    
    source = """
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    success, messages = verifier.verify_function_contracts(program, "test")
    
    assert success is True
    assert "No contracts" in messages[0]


def test_cmd_verify_with_file(tmp_path):
    """Test cmd_verify with a file"""
    # Create a test file
    test_file = tmp_path / "test.pyrite"
    test_file.write_text("""
@requires(x > 0)
fn test(x: i64):
    pass
""")
    
    # Change to temp directory
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # This will attempt to verify (may fail if Z3 not installed, but should not crash)
        result = cmd_verify(function_name="test", file_path=str(test_file))
        # Should return 0 or 1 (not crash)
        assert result in [0, 1]
    finally:
        os.chdir(old_cwd)


def test_cmd_verify_file_not_found():
    """Test cmd_verify with non-existent file"""
    result = cmd_verify(file_path="nonexistent.pyrite")
    assert result == 1


def test_smt_verifier_initialization():
    """Test SMTVerifier initialization"""
    verifier_z3 = SMTVerifier(solver="z3")
    assert verifier_z3.solver_name == "z3"
    
    verifier_cvc5 = SMTVerifier(solver="cvc5")
    assert verifier_cvc5.solver_name == "cvc5"
    
    # Case insensitive
    verifier_upper = SMTVerifier(solver="Z3")
    assert verifier_upper.solver_name == "z3"


def test_translate_complex_expression():
    """Test translation of a more complex expression"""
    verifier = SMTVerifier()
    
    # x > 0 and y < 10
    x = ast.Identifier(name="x", span=None)
    y = ast.Identifier(name="y", span=None)
    zero = ast.IntLiteral(value=0, span=None)
    ten = ast.IntLiteral(value=10, span=None)
    
    gt = ast.BinOp(left=x, op=">", right=zero, span=None)
    lt = ast.BinOp(left=y, op="<", right=ten, span=None)
    and_expr = ast.BinOp(left=gt, op="and", right=lt, span=None)
    
    result = verifier._translate_expression(and_expr)
    # Should produce nested SMT-LIB expression
    assert "and" in result
    assert "x" in result
    assert "y" in result

