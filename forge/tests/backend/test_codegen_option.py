"""Tests for Option type codegen"""

import pytest

pytestmark = pytest.mark.integration

from src.frontend import lex
from src.frontend import parse
from src.backend import LLVMCodeGen
from src.middle import type_check


def test_option_some():
    """Test Option.Some() constructor"""
    source = """
fn get_some() -> Option[int]:
    return Option.Some(42)
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    # Type check to provide type information to codegen
    type_checker = type_check(ast)
    
    # Generate LLVM IR with type checker
    codegen = LLVMCodeGen(deterministic=True)
    codegen.type_checker = type_checker
    llvm_ir = codegen.compile_program(ast)
    llvm_ir_str = str(llvm_ir)
    
    assert "define" in llvm_ir_str
    assert "get_some" in llvm_ir_str
    assert "ret" in llvm_ir_str


def test_option_none():
    """Test Option.None constructor"""
    source = """
fn get_none() -> Option[int]:
    return Option.None
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    # Type check to provide type information to codegen
    type_checker = type_check(ast)
    
    # Generate LLVM IR with type checker
    codegen = LLVMCodeGen(deterministic=True)
    codegen.type_checker = type_checker
    llvm_ir = codegen.compile_program(ast)
    llvm_ir_str = str(llvm_ir)
    
    assert "define" in llvm_ir_str
    assert "get_none" in llvm_ir_str
    assert "ret" in llvm_ir_str


def test_option_with_enum():
    """Test Option with enum type"""
    source = """
enum TokenType:
    FN
    LET

fn get_token() -> Option[TokenType]:
    return Option.Some(TokenType.FN)
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    # Type check to provide type information to codegen
    type_checker = type_check(ast)
    
    # Generate LLVM IR with type checker
    codegen = LLVMCodeGen(deterministic=True)
    codegen.type_checker = type_checker
    llvm_ir = codegen.compile_program(ast)
    llvm_ir_str = str(llvm_ir)
    
    assert "define" in llvm_ir_str
    assert "get_token" in llvm_ir_str
    assert "ret" in llvm_ir_str


def test_option_with_enum_constructor():
    """Test Option with enum constructor that has fields"""
    source = """
enum Result:
    Ok(value: int)
    Err

fn get_result() -> Option[Result]:
    return Option.Some(Result.Ok(42))
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    # Type check to provide type information to codegen
    type_checker = type_check(ast)
    
    # Generate LLVM IR with type checker
    codegen = LLVMCodeGen(deterministic=True)
    codegen.type_checker = type_checker
    llvm_ir = codegen.compile_program(ast)
    llvm_ir_str = str(llvm_ir)
    
    assert "define" in llvm_ir_str
    assert "get_result" in llvm_ir_str
    assert "ret" in llvm_ir_str
