"""Integration tests for contract code generation (@requires)"""

import pytest
from forge.src.frontend import lex, parse
from forge.src.middle.type_checker import type_check
from forge.src.backend.codegen import LLVMCodeGen

def test_requires_codegen():
    """Test that @requires generates LLVM check"""
    source = """
fn pyrite_fail(msg: String):
    pass

@requires(x > 0)
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    # Check for precondition blocks and call to pyrite_fail
    assert "precondition_fail" in llvm_ir
    assert "ContractViolation: Precondition failed: (x > 0)" in llvm_ir
    assert "pyrite_fail" in llvm_ir

def test_ensures_codegen():
    """Test that @ensures generates LLVM check with 'result'"""
    source = """
fn pyrite_fail(msg: String):
    pass

@ensures(result > 0)
fn abs(x: i64) -> i64:
    if x < 0:
        return -x
    return x
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    # Check for postcondition blocks
    assert "postcondition_fail" in llvm_ir
    assert "ContractViolation: Postcondition failed: (result > 0)" in llvm_ir
    assert "pyrite_fail" in llvm_ir

def test_loop_invariant_codegen():
    """Test that @invariant generates loop checks"""
    source = """
fn pyrite_fail(msg: String):
    pass

fn test():
    var i = 0
    @invariant(i >= 0)
    while i < 10:
        i = i + 1
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    assert "invariant_fail" in llvm_ir
    assert "ContractViolation: Loop invariant failed: (i >= 0)" in llvm_ir

def test_struct_invariant_codegen():
    """Test that @invariant generates struct checks in methods"""
    source = """
fn pyrite_fail(msg: String):
    pass

@invariant(true)
struct Counter:
    x: i64

impl Counter:
    fn inc(&mut self):
        pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    assert "invariant_ok" in llvm_ir

def test_old_expression_codegen():
    """Test that old() captures value at entry"""
    source = """
fn pyrite_fail(msg: String):
    pass

@ensures(x == old(x) + 1)
fn inc(x: int) -> int:
    return x + 1
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    # Check that x is loaded at the beginning (for old(x)) and again later
    # The first load is for old(x) capture
    assert "postcondition_fail" in llvm_ir
    assert "old(x)" in llvm_ir

def test_precondition_blame_tracking():
    """Test that precondition failures include blame: caller (SPEC-LANG-0407)"""
    source = """
fn pyrite_fail(msg: String):
    pass

@requires(x > 0)
fn test(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    # Check that error message includes blame information
    assert "blame: caller" in llvm_ir
    assert "ContractViolation: Precondition failed" in llvm_ir

def test_postcondition_blame_tracking():
    """Test that postcondition failures include blame: callee (SPEC-LANG-0407)"""
    source = """
fn pyrite_fail(msg: String):
    pass

@ensures(result > 0)
fn abs(x: i64) -> i64:
    if x < 0:
        return -x
    return x
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    # Check that error message includes blame information
    assert "blame: callee" in llvm_ir
    assert "callee (abs)" in llvm_ir
    assert "ContractViolation: Postcondition failed" in llvm_ir

def test_contract_propagation_across_functions():
    """Test that contracts are tracked across function boundaries (SPEC-LANG-0407)"""
    source = """
fn pyrite_fail(msg: String):
    pass

@requires(x > 0)
fn callee(x: i64):
    pass
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    tc = type_check(program)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = tc
    module = codegen.compile_program(program)
    
    llvm_ir = str(module)
    # Check that callee has precondition check with caller blame
    assert "blame: caller" in llvm_ir
    assert "callee" in llvm_ir  # Function name should be in the code

