"""Tests for context-sensitive keywords (exists, forall) as identifiers"""

import pytest

pytestmark = pytest.mark.fast  # All tests in this file are fast unit tests

from src.frontend import lex, parse
from src import ast


def test_exists_as_function_name():
    """Test that 'exists' can be used as a function name"""
    source = """fn exists(path: String) -> bool:
    return false
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "exists"


def test_forall_as_function_name():
    """Test that 'forall' can be used as a function name"""
    source = """fn forall(items: List[i64]) -> bool:
    return true
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert isinstance(func, ast.FunctionDef)
    assert func.name == "forall"


def test_exists_as_method_name():
    """Test that 'exists' can be used as a method name in impl blocks"""
    source = """struct Path:
    data: String

impl Path:
    fn exists(&self) -> bool:
        return false
"""
    tokens = lex(source)
    program = parse(tokens)
    
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert len(impl.methods) == 1
    assert impl.methods[0].name == "exists"


def test_forall_as_method_name():
    """Test that 'forall' can be used as a method name"""
    source = """struct Validator:
    items: List[i64]

impl Validator:
    fn forall(&self) -> bool:
        return true
"""
    tokens = lex(source)
    program = parse(tokens)
    
    impl = program.items[1]
    assert isinstance(impl, ast.ImplBlock)
    assert impl.methods[0].name == "forall"


def test_exists_still_works_as_keyword():
    """Test that 'exists' still works as a keyword in quantified expressions"""
    source = """fn test() -> bool:
    let list = [1, 2, 3]
    return exists x in list: x == 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    return_stmt = func.body.statements[1]
    assert isinstance(return_stmt, ast.ReturnStmt)
    assert isinstance(return_stmt.value, ast.QuantifiedExpr)
    assert return_stmt.value.quantifier == "exists"


def test_forall_still_works_as_keyword():
    """Test that 'forall' still works as a keyword in quantified expressions"""
    source = """fn test() -> bool:
    let list = [1, 2, 3]
    return forall x in list: x > 0
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    return_stmt = func.body.statements[1]
    assert isinstance(return_stmt, ast.ReturnStmt)
    assert isinstance(return_stmt.value, ast.QuantifiedExpr)
    assert return_stmt.value.quantifier == "forall"


def test_function_named_exists_calling_quantified_exists():
    """Test that a function named 'exists' can use 'exists' as a keyword"""
    source = """fn exists(path: String) -> bool:
    let list = [1, 2, 3]
    return exists x in list: x == 2
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.name == "exists"
    return_stmt = func.body.statements[1]
    assert isinstance(return_stmt.value, ast.QuantifiedExpr)
    assert return_stmt.value.quantifier == "exists"


def test_function_named_forall_calling_quantified_forall():
    """Test that a function named 'forall' can use 'forall' as a keyword"""
    source = """fn forall(items: List[i64]) -> bool:
    let list = [1, 2, 3]
    return forall x in list: x > 0
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.name == "forall"
    return_stmt = func.body.statements[1]
    assert isinstance(return_stmt.value, ast.QuantifiedExpr)
    assert return_stmt.value.quantifier == "forall"


def test_both_exists_and_forall_as_functions():
    """Test that both exists and forall can be function names in the same scope"""
    source = """fn exists(path: String) -> bool:
    return false

fn forall(items: List[i64]) -> bool:
    return true
"""
    tokens = lex(source)
    program = parse(tokens)
    
    assert len(program.items) == 2
    assert program.items[0].name == "exists"
    assert program.items[1].name == "forall"


def test_exists_function_with_parameters():
    """Test that exists function can have parameters"""
    source = """fn exists(path: String, check_dir: bool) -> bool:
    return false
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.name == "exists"
    assert len(func.params) == 2


def test_forall_function_with_generics():
    """Test that forall function can have generic parameters"""
    source = """fn forall[T](items: List[T]) -> bool:
    return true
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.name == "forall"
    assert len(func.generic_params) == 1


def test_exists_in_contract_attribute():
    """Test that exists works in contract attributes even when there's a function named exists"""
    source = """@requires(forall x in list: x > 0)
fn exists(list: List[i64]) -> bool:
    return exists x in list: x == 42
"""
    tokens = lex(source)
    program = parse(tokens)
    
    func = program.items[0]
    assert func.name == "exists"
    # Check that @requires has a quantified expression
    requires_attr = None
    for attr in func.attributes:
        if attr.name == "requires":
            requires_attr = attr
            break
    assert requires_attr is not None
    assert isinstance(requires_attr.args[0], ast.QuantifiedExpr)
    assert requires_attr.args[0].quantifier == "forall"


def test_function_call_to_exists():
    """Test that we can call a function named 'exists'"""
    source = """fn exists(path: String) -> bool:
    return false

fn test():
    let result = exists("test")
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Should parse successfully
    assert len(program.items) == 2
    assert program.items[0].name == "exists"
    
    # Check the function call
    test_func = program.items[1]
    var_decl = test_func.body.statements[0]
    assert isinstance(var_decl.initializer, ast.FunctionCall)
    assert isinstance(var_decl.initializer.function, ast.Identifier)
    assert var_decl.initializer.function.name == "exists"


def test_method_call_to_exists():
    """Test that we can call a method named 'exists'"""
    source = """struct Path:
    data: String

impl Path:
    fn exists(&self) -> bool:
        return false

fn test():
    var p = Path { data: "test" }
    let result = p.exists()
"""
    tokens = lex(source)
    program = parse(tokens)
    
    # Should parse successfully
    impl = program.items[1]
    assert impl.methods[0].name == "exists"
    
    # Check the method call
    test_func = program.items[2]
    var_decl = test_func.body.statements[1]
    assert isinstance(var_decl.initializer, ast.MethodCall)
    # MethodCall uses 'method' field which is a string
    assert var_decl.initializer.method == "exists"

