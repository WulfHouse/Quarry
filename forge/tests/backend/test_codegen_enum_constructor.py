"""Tests for enum constructor codegen with fields"""

import pytest

pytestmark = pytest.mark.integration

from src.frontend import lex
from src.frontend import parse
from src.backend import generate_llvm, LLVMCodeGen
from src.middle import type_check


def test_enum_constructor_no_fields():
    """Test enum constructor with no fields"""
    source = """
enum Color:
    Red
    Green
    Blue

fn get_red() -> Color:
    return Color.Red
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
    assert "get_red" in llvm_ir_str
    assert "ret" in llvm_ir_str


def test_enum_constructor_one_field():
    """Test enum constructor with one field"""
    source = """
enum Result:
    Ok(value: int)
    Err

fn get_ok() -> Result:
    return Result.Ok(42)
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
    assert "get_ok" in llvm_ir_str
    assert "ret" in llvm_ir_str


def test_enum_constructor_multiple_fields():
    """Test enum constructor with multiple fields"""
    source = """
enum Type:
    IntType(width: int, signed: bool)
    BoolType

fn get_int_type() -> Type:
    return Type.IntType(32, true)
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
    assert "get_int_type" in llvm_ir_str
    assert "ret" in llvm_ir_str


def test_enum_constructor_mixed_variants():
    """Test enum with both variants with and without fields"""
    source = """
enum Option:
    Some(value: int)
    None

fn get_some() -> Option:
    return Option.Some(100)

fn get_none() -> Option:
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
    assert "get_some" in llvm_ir_str
    assert "get_none" in llvm_ir_str
    assert "ret" in llvm_ir_str
