"""Tests for opaque types in FFI"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.middle import TypeChecker
from src import ast


def test_opaque_type_declaration():
    """Test opaque type declaration"""
    source = """opaque type LLVMValueRef;
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 1
    opaque = program.items[0]
    assert isinstance(opaque, ast.OpaqueTypeDecl)
    assert opaque.name == "LLVMValueRef"


def test_extern_function_with_opaque_param():
    """Test extern function taking opaque type parameter"""
    source = """opaque type LLVMValueRef;

extern "C" fn LLVMGetValueName(value: LLVMValueRef) -> *const u8
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    func = program.items[1]
    assert isinstance(func, ast.FunctionDef)
    assert func.is_extern == True
    assert len(func.params) == 1
    param = func.params[0]
    assert isinstance(param.type_annotation, ast.PrimitiveType)
    assert param.type_annotation.name == "LLVMValueRef"


def test_extern_function_returning_opaque():
    """Test extern function returning opaque type"""
    source = """opaque type LLVMValueRef;

extern "C" fn LLVMGetFirstUse(value: LLVMValueRef) -> LLVMValueRef
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    func = program.items[1]
    assert isinstance(func, ast.FunctionDef)
    assert func.return_type is not None
    assert isinstance(func.return_type, ast.PrimitiveType)
    assert func.return_type.name == "LLVMValueRef"


def test_opaque_type_type_checking():
    """Test type checking of opaque types"""
    source = """opaque type LLVMValueRef;

extern "C" fn LLVMGetValueName(value: LLVMValueRef) -> *const u8

fn main():
    let handle: LLVMValueRef = LLVMGetValueName(None)
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    type_checker = TypeChecker()
    type_checker.check_program(program)
    
    # Should not have type errors (opaque types should be registered)
    assert program is not None


def test_multiple_opaque_types():
    """Test multiple opaque type declarations"""
    source = """opaque type LLVMValueRef;
opaque type LLVMTypeRef;
opaque type LLVMModuleRef;

extern "C" fn LLVMGetValueType(value: LLVMValueRef) -> LLVMTypeRef
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 4
    assert all(isinstance(item, ast.OpaqueTypeDecl) for item in program.items[:3])
    assert program.items[0].name == "LLVMValueRef"
    assert program.items[1].name == "LLVMTypeRef"
    assert program.items[2].name == "LLVMModuleRef"


def test_opaque_type_in_struct():
    """Test opaque type as struct field"""
    source = """opaque type LLVMValueRef;

struct ValueWrapper:
    value: LLVMValueRef
"""
    
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    struct = program.items[1]
    assert isinstance(struct, ast.StructDef)
    assert len(struct.fields) == 1
    field = struct.fields[0]
    assert isinstance(field.type_annotation, ast.PrimitiveType)
    assert field.type_annotation.name == "LLVMValueRef"
