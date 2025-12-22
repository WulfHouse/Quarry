"""Tests for runtime closure code generation"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.middle import TypeChecker
from src.middle import SymbolTable
from src.backend import LLVMCodeGen


def compile_runtime_closure(source: str):
    """Compile a simple program with runtime closure"""
    from src.frontend import lex
    from src.frontend import parse
    
    tokens = lex(source, "<test>")
    ast = parse(tokens)
    
    from src.middle import type_check
    type_checker = type_check(ast)
    
    codegen = LLVMCodeGen()
    codegen.type_checker = type_checker
    codegen.compile_program(ast)
    
    return codegen


class TestRuntimeClosureCodegen:
    """Test runtime closure code generation"""
    
    def test_simple_runtime_closure_no_captures(self):
        """Test simple runtime closure with no captures"""
        source = """
fn main():
    let f = fn(x: int) -> int: x * 2
    let result = f(5)
"""
        codegen = compile_runtime_closure(source)
        
        # Should have generated closure function
        closure_funcs = [f for f in codegen.module.functions if f.name.startswith("__closure_")]
        assert len(closure_funcs) > 0
        
        # Closure with no captures should return function pointer directly
        # (not a struct)
        # This is handled in gen_runtime_closure
    
    def test_runtime_closure_with_capture(self):
        """Test runtime closure with captured variable"""
        source = """
fn main():
    let threshold = 10
    let filter_fn = fn(x: int) -> bool: x > threshold
    let result = filter_fn(15)
"""
        codegen = compile_runtime_closure(source)
        
        # Should have generated closure function
        closure_funcs = [f for f in codegen.module.functions if f.name.startswith("__closure_")]
        assert len(closure_funcs) > 0
        
        # Should have environment struct type
        assert len(codegen.closure_environments) > 0
        
        # Closure function should have environment pointer as first parameter
        closure_func = closure_funcs[0]
        assert len(closure_func.args) > 0
        # First arg should be environment pointer (if captures exist)
    
    def test_runtime_closure_multiple_captures(self):
        """Test runtime closure with multiple captures"""
        source = """
fn main():
    let a = 5
    let b = 10
    let add = fn(x: int) -> int: x + a + b
    let result = add(3)
"""
        codegen = compile_runtime_closure(source)
        
        # Should have generated closure function
        closure_funcs = [f for f in codegen.module.functions if f.name.startswith("__closure_")]
        assert len(closure_funcs) > 0
        
        # Should have environment with multiple fields
        assert len(codegen.closure_environments) > 0
    
    def test_runtime_closure_call(self):
        """Test calling a runtime closure"""
        source = """
fn main():
    let multiplier = 3
    let times = fn(x: int) -> int: x * multiplier
    let result = times(4)
"""
        codegen = compile_runtime_closure(source)
        
        # Should compile without errors
        assert codegen.module is not None
        
        # Should have closure function
        closure_funcs = [f for f in codegen.module.functions if f.name.startswith("__closure_")]
        assert len(closure_funcs) > 0
    
    def test_runtime_closure_stored_in_variable(self):
        """Test storing runtime closure in variable"""
        # Note: Assignment in closure body requires block syntax which may not be supported yet
        # For now, test with a simpler closure
        source = """
fn main():
    let count = 0
    let get_count = fn() -> int: count
    let result = get_count()
"""
        codegen = compile_runtime_closure(source)
        
        # Should compile without errors
        assert codegen.module is not None
        
        # Should have closure function
        closure_funcs = [f for f in codegen.module.functions if f.name.startswith("__closure_")]
        assert len(closure_funcs) > 0


    def test_runtime_closure_stored_in_collection(self):
        """Test storing runtime closures in collections (conceptual test)"""
        # Note: This tests the code generation infrastructure
        # Full collection support requires List/Map implementations
        source = """
fn main():
    let multiplier = 3
    let times = fn(x: int) -> int: x * multiplier
    # Closure can be stored (conceptually)
    # let closures = [times, times]  # Would work if List supports closures
"""
        codegen = compile_runtime_closure(source)
        
        # Should compile without errors
        assert codegen.module is not None
        
        # Should have closure function
        closure_funcs = [f for f in codegen.module.functions if f.name.startswith("__closure_")]
        assert len(closure_funcs) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

