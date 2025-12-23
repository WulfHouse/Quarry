import pytest

def test_set_remove():
    """Test Set.remove method (SPEC-LANG-0822)"""
    source = """struct Set[T]:
    buckets: *u8
    len: i64
    cap: i64
    elem_size: i64

impl Set[T]:
    fn new() -> Set[T]:
        pass
    fn insert(&mut self, elem: T):
        pass
    fn remove(&mut self, elem: T):
        pass
    fn contains(&self, elem: T) -> bool:
        return false
    fn length(&self) -> i64:
        return 0

fn main() -> int:
    var s = Set[int].new()
    s.insert(1)
    s.remove(1)
    return 0
"""
    # Note: This requires linking with stdlib C code which may not be easily available in unit tests.
    # But we can verify it compiles and produces the right LLVM IR.
    from src.frontend import lex, parse
    from src.middle import type_check
    from src.backend import generate_llvm
    
    tokens = lex(source)
    ast = parse(tokens)
    checker = type_check(ast)
    assert not checker.has_errors()
    
    llvm_ir = generate_llvm(ast, type_checker=checker)
    assert "set_remove" in llvm_ir

