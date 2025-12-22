"""Tests for trait code generation"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.backend import LLVMCodeGen


def compile_trait_program(source: str):
    """Compile a program with traits"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    type_checker = type_check(program)
    if type_checker.has_errors():
        return None, type_checker
    
    try:
        codegen = LLVMCodeGen()
        codegen.type_checker = type_checker
        module = codegen.compile_program(program)
        return module, type_checker
    except Exception as e:
        # Return None on error for now
        import traceback
        print(f"Compilation error: {e}")
        traceback.print_exc()
        return None, type_checker


def test_trait_method_dispatch():
    """Test that trait methods are dispatched correctly"""
    source = """
trait Display:
    fn to_string(&self) -> String

struct Point:
    x: int
    y: int

impl Display for Point:
    fn to_string(&self) -> String:
        return "Point"

fn main():
    let p = Point { x: 1, y: 2 }
    let s = p.to_string()
"""
    
    module, type_checker = compile_trait_program(source)
    
    # Should compile without errors
    assert module is not None
    assert type_checker is not None
    
    # Should have generated method function
    # Method name format: Type_Trait_method
    method_funcs = [f for f in module.functions if "to_string" in f.name]
    assert len(method_funcs) > 0


def test_inherent_method_dispatch():
    """Test that inherent methods are dispatched correctly"""
    source = """
struct Point:
    x: int
    y: int

impl Point:
    fn new(x: int, y: int) -> Point:
        return Point { x: x, y: y }

fn main():
    let p = Point.new(1, 2)
"""
    
    module, type_checker = compile_trait_program(source)
    
    # Should compile without errors
    assert module is not None
    assert type_checker is not None
    
    # Should have generated method function
    method_funcs = [f for f in module.functions if "new" in f.name]
    assert len(method_funcs) > 0


def test_trait_implementation_completeness():
    """Test that incomplete trait implementations are detected"""
    source = """
trait Display:
    fn to_string(&self) -> String
    fn print(&self)

struct Point:
    x: int
    y: int

impl Display for Point:
    fn to_string(&self) -> String:
        return "Point"
    # Missing print() method
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    type_checker = type_check(program)
    
    # Should have error about missing method
    assert type_checker.has_errors()
    error_messages = [str(e) for e in type_checker.errors]
    assert any("requires implementation" in msg for msg in error_messages)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

