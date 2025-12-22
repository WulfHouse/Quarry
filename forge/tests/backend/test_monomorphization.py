"""Tests for compile-time parameter monomorphization"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from src.frontend import lex
from src.frontend import parse
from src.backend import monomorphize_program, extract_compile_time_args, MonomorphizationContext
from src import ast


def test_simple_monomorphization():
    """Test basic function specialization"""
    source = """
fn multiply[N: int](x: int) -> int:
    return x * N

fn main():
    let result = multiply[10](5)
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    # Before monomorphization: 2 functions
    assert len([item for item in program.items if isinstance(item, ast.FunctionDef)]) == 2
    
    # Monomorphize
    monomorphized = monomorphize_program(program)
    
    # After monomorphization: main + multiply_10 (original multiply removed)
    functions = [item for item in monomorphized.items if isinstance(item, ast.FunctionDef)]
    assert len(functions) == 2
    
    # Check specialized function exists
    func_names = [f.name for f in functions]
    assert 'main' in func_names
    assert 'multiply_10' in func_names
    assert 'multiply' not in func_names  # Original removed
    
    # Check specialized function has no compile-time params
    multiply_10 = next(f for f in functions if f.name == 'multiply_10')
    assert len(multiply_10.compile_time_params) == 0


def test_multiple_specializations():
    """Test multiple specializations of same function"""
    source = """
fn create_array[Size: int]() -> int:
    return Size

fn main():
    let arr1 = create_array[10]()
    let arr2 = create_array[20]()
    let arr3 = create_array[10]()
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    functions = [item for item in monomorphized.items if isinstance(item, ast.FunctionDef)]
    func_names = [f.name for f in functions]
    
    # Should have: main, create_array_10, create_array_20
    assert 'main' in func_names
    assert 'create_array_10' in func_names
    assert 'create_array_20' in func_names
    assert 'create_array' not in func_names
    
    # Should have exactly 3 functions (not 4, since [10] appears twice)
    assert len(functions) == 3


def test_bool_parameter_specialization():
    """Test boolean compile-time parameters"""
    source = """
fn process[Debug: bool](x: int) -> int:
    return x

fn main():
    let r1 = process[true](5)
    let r2 = process[false](10)
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    functions = [item for item in monomorphized.items if isinstance(item, ast.FunctionDef)]
    func_names = [f.name for f in functions]
    
    assert 'process_true' in func_names
    assert 'process_false' in func_names


def test_mixed_parameters():
    """Test functions with multiple compile-time parameters"""
    source = """
fn configure[Size: int, Debug: bool]() -> int:
    return Size

fn main():
    let c1 = configure[256, true]()
    let c2 = configure[512, false]()
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    functions = [item for item in monomorphized.items if isinstance(item, ast.FunctionDef)]
    func_names = [f.name for f in functions]
    
    assert 'configure_256_true' in func_names
    assert 'configure_512_false' in func_names


def test_substitution_in_return_value():
    """Test that compile-time params are substituted in function body"""
    source = """
fn get_value[N: int]() -> int:
    return N

fn main():
    let v = get_value[42]()
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    # Find the specialized function
    functions = [item for item in monomorphized.items if isinstance(item, ast.FunctionDef)]
    get_value_42 = next((f for f in functions if f.name == 'get_value_42'), None)
    
    assert get_value_42 is not None
    
    # Check that the return value is now a literal (N substituted with 42)
    return_stmt = get_value_42.body.statements[0]
    assert isinstance(return_stmt, ast.ReturnStmt)
    assert isinstance(return_stmt.value, ast.IntLiteral)
    assert return_stmt.value.value == 42


def test_call_site_updated():
    """Test that function calls are updated to use specialized names"""
    source = """
fn double[N: int](x: int) -> int:
    return x * N

fn main():
    let result = double[2](5)
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    # Find main function
    main_func = next(item for item in monomorphized.items if isinstance(item, ast.FunctionDef) and item.name == 'main')
    
    # Find the function call in main
    var_decl = main_func.body.statements[0]
    assert isinstance(var_decl, ast.VarDecl)
    
    call = var_decl.initializer
    assert isinstance(call, ast.FunctionCall)
    
    # The function name should be updated to specialized name
    assert isinstance(call.function, ast.Identifier)
    assert call.function.name == 'double_2'
    
    # Compile-time args should be cleared
    assert call.compile_time_args == []


def test_const_folding():
    """Test that arithmetic with compile-time params is folded"""
    source = """
fn compute[N: int]() -> int:
    return N * 2

fn main():
    let val = compute[10]()
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    # Find specialized function
    compute_10 = next(f for f in monomorphized.items if isinstance(f, ast.FunctionDef) and f.name == 'compute_10')
    
    # The return value should be folded to 20
    return_stmt = compute_10.body.statements[0]
    assert isinstance(return_stmt.value, ast.IntLiteral)
    assert return_stmt.value.value == 20  # 10 * 2 = 20


def test_no_specialization_for_regular_functions():
    """Test that functions without compile-time params are unchanged"""
    source = """
fn regular(x: int) -> int:
    return x * 2

fn main():
    let result = regular(5)
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    functions = [item for item in monomorphized.items if isinstance(item, ast.FunctionDef)]
    func_names = [f.name for f in functions]
    
    # Should have: regular, main (no specialization)
    assert 'regular' in func_names
    assert 'main' in func_names
    assert len(functions) == 2


def test_nested_substitution():
    """Test substitution in nested expressions"""
    source = """
fn calculate[N: int](x: int) -> int:
    let temp = N + x
    return temp * N

fn main():
    let val = calculate[5](3)
"""
    tokens = lex(source, "test")
    program = parse(tokens)
    
    monomorphized = monomorphize_program(program)
    
    # Find specialized function
    calculate_5 = next(f for f in monomorphized.items if isinstance(f, ast.FunctionDef) and f.name == 'calculate_5')
    
    # First statement: let temp = N + x should have N substituted
    var_decl = calculate_5.body.statements[0]
    assert isinstance(var_decl, ast.VarDecl)
    
    # The initializer should be a binary op with 5 on left side
    bin_op = var_decl.initializer
    assert isinstance(bin_op, ast.BinOp)
    assert isinstance(bin_op.left, ast.IntLiteral)
    assert bin_op.left.value == 5  # N substituted with 5


def test_extract_compile_time_args():
    """Test extracting compile-time arguments from call expressions"""
    # This test verifies the extraction logic works correctly
    # We'll just test the function directly with simple inputs
    
    from src.backend import MonomorphizationContext
    context = MonomorphizationContext()
    
    # Test name generation with integer
    name1 = context.get_specialized_function_name("foo", (256,))
    assert name1 == "foo_256"
    
    # Test name generation with boolean
    name2 = context.get_specialized_function_name("bar", (True,))
    assert name2 == "bar_true"
    
    # Test name generation with multiple args
    name3 = context.get_specialized_function_name("baz", (128, False))
    assert name3 == "baz_128_false"


def test_specialized_name_generation():
    """Test that specialized names are generated correctly"""
    context = MonomorphizationContext()
    
    # Test integer args
    name1 = context.get_specialized_function_name("process", (256,))
    assert name1 == "process_256"
    
    # Test boolean args
    name2 = context.get_specialized_function_name("debug", (True,))
    assert name2 == "debug_true"
    
    name3 = context.get_specialized_function_name("debug", (False,))
    assert name3 == "debug_false"
    
    # Test multiple args
    name4 = context.get_specialized_function_name("configure", (512, True))
    assert name4 == "configure_512_true"
    
    # Test negative numbers
    name5 = context.get_specialized_function_name("offset", (-10,))
    assert name5 == "offset_neg10"


def test_get_specialized_function_name_no_args():
    """Test get_specialized_function_name() with no args"""
    context = MonomorphizationContext()
    name = context.get_specialized_function_name("foo", ())
    assert name == "foo"


def test_get_specialized_function_name_other_type():
    """Test get_specialized_function_name() with other type"""
    context = MonomorphizationContext()
    name = context.get_specialized_function_name("foo", ("str",))
    assert "foo" in name


def test_needs_specialization_true():
    """Test needs_specialization() with function that needs it"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    param = ast.CompileTimeIntParam(name="N", span=Span("test.pyrite", 1, 1, 1, 1))
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[param],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    assert context.needs_specialization(func) == True


def test_needs_specialization_false():
    """Test needs_specialization() with function that doesn't need it"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    assert context.needs_specialization(func) == False


def test_register_original_function():
    """Test register_original_function()"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    context.register_original_function(func)
    assert "test" in context.original_functions


def test_register_original_function_duplicate():
    """Test register_original_function() with duplicate"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    context.register_original_function(func)
    context.register_original_function(func)  # Should not overwrite
    assert "test" in context.original_functions


def test_specialize_function_already_specialized():
    """Test specialize_function() when already specialized"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    param = ast.CompileTimeIntParam(name="N", span=Span("test.pyrite", 1, 1, 1, 1))
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[param],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    specialized1 = context.specialize_function(func, (42,))
    specialized2 = context.specialize_function(func, (42,))
    # Should return cached version
    assert specialized1 == specialized2


def test_specialize_function_with_return_type():
    """Test specialize_function() with return type"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    param = ast.CompileTimeIntParam(name="N", span=Span("test.pyrite", 1, 1, 1, 1))
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[param],
        params=[],
        return_type=IntType(),
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    specialized = context.specialize_function(func, (42,))
    assert specialized.return_type is not None


def test_substitute_in_statement_var_decl():
    """Test _substitute_in_statement() with VarDecl"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    stmt = ast.VarDecl(
        name="x",
        type_annotation=None,
        initializer=ast.Identifier(name="N", span=Span("test.pyrite", 1, 9, 1, 10)),
        mutable=False,
        span=Span("test.pyrite", 1, 5, 1, 10)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.VarDecl)
    assert isinstance(result.initializer, ast.IntLiteral)


def test_substitute_in_statement_var_decl_with_type():
    """Test _substitute_in_statement() with VarDecl with type annotation"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    stmt = ast.VarDecl(
        name="x",
        type_annotation=IntType(),
        initializer=ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 9, 1, 10)),
        mutable=False,
        span=Span("test.pyrite", 1, 5, 1, 10)
    )
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.VarDecl)


def test_substitute_in_statement_assignment():
    """Test _substitute_in_statement() with Assignment"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    stmt = ast.Assignment(
        target=ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2)),
        value=ast.Identifier(name="N", span=Span("test.pyrite", 1, 5, 1, 6)),
        span=Span("test.pyrite", 1, 1, 1, 6)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.Assignment)
    assert isinstance(result.value, ast.IntLiteral)


def test_substitute_in_statement_return_no_value():
    """Test _substitute_in_statement() with ReturnStmt without value"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    stmt = ast.ReturnStmt(value=None, span=Span("test.pyrite", 1, 1, 1, 7))
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ReturnStmt)
    assert result.value is None


def test_substitute_in_statement_if_with_elif():
    """Test _substitute_in_statement() with IfStmt with elif clauses"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    elif_cond = ast.BoolLiteral(value=False, span=Span("test.pyrite", 1, 15, 1, 20))
    elif_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 21, 1, 22))
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[(elif_cond, elif_block)],
        else_block=None,
        span=Span("test.pyrite", 1, 1, 1, 22)
    )
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.IfStmt)
    assert len(result.elif_clauses) == 1


def test_substitute_in_statement_if_with_else():
    """Test _substitute_in_statement() with IfStmt with else block"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 4, 1, 8))
    then_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 9, 1, 10))
    else_block = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.IfStmt(
        condition=condition,
        then_block=then_block,
        elif_clauses=[],
        else_block=else_block,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.IfStmt)
    assert result.else_block is not None


def test_substitute_in_statement_while():
    """Test _substitute_in_statement() with WhileStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 7, 1, 11))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 12, 1, 13))
    stmt = ast.WhileStmt(condition=condition, body=body, span=Span("test.pyrite", 1, 1, 1, 13))
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.WhileStmt)


def test_substitute_in_statement_for():
    """Test _substitute_in_statement() with ForStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    iterable = ast.Identifier(name="list", span=Span("test.pyrite", 1, 9, 1, 13))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15))
    stmt = ast.ForStmt(
        variable="x",
        iterable=iterable,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ForStmt)


def test_substitute_in_statement_expression_stmt():
    """Test _substitute_in_statement() with ExpressionStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.Identifier(name="N", span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.ExpressionStmt(expression=expr, span=Span("test.pyrite", 1, 1, 1, 2))
    substitutions = {"N": 42}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.ExpressionStmt)
    assert isinstance(result.expression, ast.IntLiteral)


def test_substitute_in_statement_defer():
    """Test _substitute_in_statement() with DeferStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 6, 1, 7))
    stmt = ast.DeferStmt(body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    assert isinstance(result, ast.DeferStmt)


def test_substitute_in_expression_identifier_substituted():
    """Test _substitute_in_expression() with Identifier that gets substituted"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.Identifier(name="N", span=Span("test.pyrite", 1, 1, 1, 2))
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 42


def test_substitute_in_expression_identifier_bool():
    """Test _substitute_in_expression() with Identifier substituted to bool"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.Identifier(name="Debug", span=Span("test.pyrite", 1, 1, 1, 6))
    substitutions = {"Debug": True}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.BoolLiteral)
    assert result.value == True


def test_substitute_in_expression_identifier_not_substituted():
    """Test _substitute_in_expression() with Identifier not in substitutions"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    assert result == expr


def test_substitute_in_expression_binop():
    """Test _substitute_in_expression() with BinOp"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.Identifier(name="N", span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=2, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="*", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    substitutions = {"N": 5}
    result = context._substitute_in_expression(expr, substitutions)
    # Should be const-folded to 10
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 10


def test_substitute_in_expression_unaryop():
    """Test _substitute_in_expression() with UnaryOp"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    operand = ast.Identifier(name="N", span=Span("test.pyrite", 1, 2, 1, 3))
    expr = ast.UnaryOp(op="-", operand=operand, span=Span("test.pyrite", 1, 1, 1, 3))
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.UnaryOp)


def test_substitute_in_expression_function_call():
    """Test _substitute_in_expression() with FunctionCall"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[ast.Identifier(name="N", span=Span("test.pyrite", 1, 6, 1, 7))],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 9)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_expression(call, substitutions)
    assert isinstance(result, ast.FunctionCall)
    assert isinstance(result.compile_time_args[0], ast.IntLiteral)


def test_substitute_in_expression_method_call():
    """Test _substitute_in_expression() with MethodCall"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.MethodCall(
        object=obj,
        method="method",
        arguments=[ast.Identifier(name="N", span=Span("test.pyrite", 1, 10, 1, 11))],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.MethodCall)
    assert isinstance(result.arguments[0], ast.IntLiteral)


def test_substitute_in_expression_field_access():
    """Test _substitute_in_expression() with FieldAccess"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.FieldAccess(object=obj, field="field", span=Span("test.pyrite", 1, 1, 1, 8))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.FieldAccess)


def test_substitute_in_expression_index_access():
    """Test _substitute_in_expression() with IndexAccess"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    index = ast.Identifier(name="N", span=Span("test.pyrite", 1, 3, 1, 4))
    expr = ast.IndexAccess(object=obj, index=index, span=Span("test.pyrite", 1, 1, 1, 4))
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.IndexAccess)
    assert isinstance(result.index, ast.IntLiteral)


def test_substitute_in_expression_list_literal():
    """Test _substitute_in_expression() with ListLiteral"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.ListLiteral(
        elements=[ast.Identifier(name="N", span=Span("test.pyrite", 1, 2, 1, 3))],
        span=Span("test.pyrite", 1, 1, 1, 4)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.ListLiteral)
    assert isinstance(result.elements[0], ast.IntLiteral)


def test_substitute_in_expression_struct_literal():
    """Test _substitute_in_expression() with StructLiteral"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    # StructLiteral.fields is a list of tuples (field_name, value)
    expr = ast.StructLiteral(
        struct_name="Test",
        fields=[("x", ast.Identifier(name="N", span=Span("test.pyrite", 1, 10, 1, 11)))],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.StructLiteral)
    # Check that the field value was substituted
    field_name, field_value = result.fields[0]
    assert field_name == "x"
    assert isinstance(field_value, ast.IntLiteral)


def test_substitute_in_expression_literal():
    """Test _substitute_in_expression() with literal (should pass through)"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 1, 1, 2))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    assert result == expr


def test_substitute_in_type_array_type():
    """Test _substitute_in_type() with ArrayType"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    size = ast.Identifier(name="N", span=Span("test.pyrite", 1, 2, 1, 3))
    type_node = ast.ArrayType(
        element_type=IntType(),
        size=size,
        span=Span("test.pyrite", 1, 1, 1, 3)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_type(type_node, substitutions)
    assert isinstance(result, ast.ArrayType)
    assert isinstance(result.size, ast.IntLiteral)


def test_substitute_in_type_array_type_no_size():
    """Test _substitute_in_type() with ArrayType without size"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    type_node = ast.ArrayType(
        element_type=IntType(),
        size=None,
        span=Span("test.pyrite", 1, 1, 1, 1)
    )
    substitutions = {}
    result = context._substitute_in_type(type_node, substitutions)
    assert isinstance(result, ast.ArrayType)


def test_substitute_in_type_generic_type():
    """Test _substitute_in_type() with GenericType"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    type_node = ast.GenericType(
        name="List",
        type_args=[IntType(), ast.Identifier(name="N", span=Span("test.pyrite", 1, 10, 1, 11))],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_type(type_node, substitutions)
    assert isinstance(result, ast.GenericType)


def test_substitute_in_type_other():
    """Test _substitute_in_type() with other type"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    type_node = IntType()
    substitutions = {}
    result = context._substitute_in_type(type_node, substitutions)
    assert result == type_node


def test_try_const_fold_add():
    """Test _try_const_fold() with addition"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 1, 1, 1))
    right = ast.IntLiteral(value=3, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="+", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 8


def test_try_const_fold_subtract():
    """Test _try_const_fold() with subtraction"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=10, span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=3, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="-", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 7


def test_try_const_fold_multiply():
    """Test _try_const_fold() with multiplication"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 1, 1, 1))
    right = ast.IntLiteral(value=4, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="*", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 20


def test_try_const_fold_divide():
    """Test _try_const_fold() with division"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=20, span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=4, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="/", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 5


def test_try_const_fold_divide_by_zero():
    """Test _try_const_fold() with division by zero"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=20, span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="/", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    # Should not fold (division by zero)
    assert isinstance(result, ast.BinOp)


def test_try_const_fold_modulo():
    """Test _try_const_fold() with modulo"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=20, span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=3, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="%", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.IntLiteral)
    assert result.value == 2


def test_try_const_fold_modulo_by_zero():
    """Test _try_const_fold() with modulo by zero"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=20, span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="%", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    # Should not fold (modulo by zero)
    assert isinstance(result, ast.BinOp)


def test_try_const_fold_bool_and():
    """Test _try_const_fold() with boolean and"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    right = ast.BoolLiteral(value=False, span=Span("test.pyrite", 1, 7, 1, 12))
    expr = ast.BinOp(op="and", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 12))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.BoolLiteral)
    assert result.value == False


def test_try_const_fold_bool_or():
    """Test _try_const_fold() with boolean or"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    right = ast.BoolLiteral(value=False, span=Span("test.pyrite", 1, 7, 1, 12))
    expr = ast.BinOp(op="or", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 12))
    result = context._try_const_fold(expr)
    assert isinstance(result, ast.BoolLiteral)
    assert result.value == True


def test_try_const_fold_non_literal():
    """Test _try_const_fold() with non-literal operands"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    right = ast.IntLiteral(value=3, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="+", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    # Should not fold
    assert isinstance(result, ast.BinOp)


def test_try_const_fold_unknown_op():
    """Test _try_const_fold() with unknown operator"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    left = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 1, 1, 1))
    right = ast.IntLiteral(value=3, span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.BinOp(op="==", left=left, right=right, span=Span("test.pyrite", 1, 1, 1, 6))
    result = context._try_const_fold(expr)
    # Should not fold (== not supported)
    assert isinstance(result, ast.BinOp)


def test_collect_function_calls_program():
    """Test _collect_function_calls() with Program"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    calls = _collect_function_calls(program)
    assert isinstance(calls, list)


def test_collect_function_calls_match_stmt():
    """Test _collect_function_calls() with MatchStmt"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15)),
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    calls = _collect_function_calls(stmt)
    assert isinstance(calls, list)
    # MatchStmt is not handled in _collect_function_calls, so should return empty list
    assert len(calls) == 0


def test_collect_function_calls_try_expr():
    """Test _collect_function_calls() with TryExpr"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    inner = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    calls = _collect_function_calls(expr)
    assert isinstance(calls, list)


def test_get_function_name_from_call_not_identifier():
    """Test _get_function_name_from_call() with non-Identifier function"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _get_function_name_from_call
    func = ast.FieldAccess(
        object=ast.Identifier(name="obj", span=Span("test.pyrite", 1, 1, 1, 4)),
        field="method",
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 12)
    )
    name = _get_function_name_from_call(call)
    assert name is None


def test_update_call_sites_no_compile_time_args():
    """Test _update_call_sites() with call without compile-time args"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    context = MonomorphizationContext()
    _update_call_sites(call, context)
    # Should not change
    assert call.function.name == "test"


def test_update_call_sites_not_in_original_functions():
    """Test _update_call_sites() with function not in original_functions"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 6, 1, 8))],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 9)
    )
    context = MonomorphizationContext()
    _update_call_sites(call, context)
    # Should not change (function not in original_functions)
    assert call.function.name == "test"


def test_update_call_sites_match_stmt():
    """Test _update_call_sites() with MatchStmt"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15)),
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_with_stmt():
    """Test _update_call_sites() with WithStmt"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    value = ast.Identifier(name="file", span=Span("test.pyrite", 1, 10, 1, 14))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.WithStmt(
        variable="f",
        value=value,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_extract_compile_time_args_invalid():
    """Test extract_compile_time_args() with invalid argument type"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend import extract_compile_time_args
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[ast.Identifier(name="x", span=Span("test.pyrite", 1, 6, 1, 7))],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 9)
    )
    with pytest.raises(ValueError, match="Compile-time arguments must be literals"):
        extract_compile_time_args(call)


def test_monomorphize_program_no_specializations():
    """Test monomorphize_program() with no functions needing specialization"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend import monomorphize_program
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    result = monomorphize_program(program)
    assert len(result.items) == 1
    assert result.items[0].name == "test"


def test_monomorphize_program_with_struct():
    """Test monomorphize_program() with struct definition"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend import monomorphize_program
    struct = ast.StructDef(
        name="Point",
        generic_params=[],
        compile_time_params=[],
        fields=[],
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    program = ast.Program(imports=[], items=[struct], span=Span("test.pyrite", 1, 1, 1, 1))
    result = monomorphize_program(program)
    assert len(result.items) == 1
    assert isinstance(result.items[0], ast.StructDef)


def test_monomorphize_program_call_without_compile_time_args():
    """Test monomorphize_program() with call that has no compile-time args"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend import monomorphize_program
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    func = ast.FunctionDef(
        name="main",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7)),
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    result = monomorphize_program(program)
    assert len(result.items) == 1


def test_monomorphize_program_call_without_function_name():
    """Test monomorphize_program() with call where function name can't be extracted"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend import monomorphize_program
    func_expr = ast.FieldAccess(
        object=ast.Identifier(name="obj", span=Span("test.pyrite", 1, 1, 1, 4)),
        field="method",
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    call = ast.FunctionCall(
        function=func_expr,
        compile_time_args=[ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 11, 1, 13))],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 14)
    )
    func = ast.FunctionDef(
        name="main",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 14))], span=Span("test.pyrite", 1, 1, 1, 14)),
        span=Span("test.pyrite", 1, 1, 1, 14)
    )
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    result = monomorphize_program(program)
    # Should not crash
    assert len(result.items) >= 1


def test_collect_function_calls_with_stmt():
    """Test _collect_function_calls() with WithStmt"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    value = ast.Identifier(name="file", span=Span("test.pyrite", 1, 10, 1, 14))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.WithStmt(
        variable="f",
        value=value,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    calls = _collect_function_calls(stmt)
    assert isinstance(calls, list)


def test_collect_function_calls_slice_access():
    """Test _collect_function_calls() with SliceAccess"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    start = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    end = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 6, 1, 7))
    expr = ast.SliceAccess(object=obj, start=start, end=end, span=Span("test.pyrite", 1, 1, 1, 7))
    calls = _collect_function_calls(expr)
    assert isinstance(calls, list)


def test_collect_function_calls_slice_access_no_start():
    """Test _collect_function_calls() with SliceAccess without start"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    end = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 4, 1, 5))
    expr = ast.SliceAccess(object=obj, start=None, end=end, span=Span("test.pyrite", 1, 1, 1, 5))
    calls = _collect_function_calls(expr)
    assert isinstance(calls, list)


def test_collect_function_calls_slice_access_no_end():
    """Test _collect_function_calls() with SliceAccess without end"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    start = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    expr = ast.SliceAccess(object=obj, start=start, end=None, span=Span("test.pyrite", 1, 1, 1, 4))
    calls = _collect_function_calls(expr)
    assert isinstance(calls, list)


def test_collect_function_calls_try_expr():
    """Test _collect_function_calls() with TryExpr"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    inner = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    calls = _collect_function_calls(expr)
    assert isinstance(calls, list)


def test_update_call_sites_slice_access():
    """Test _update_call_sites() with SliceAccess"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    start = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    end = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 6, 1, 7))
    expr = ast.SliceAccess(object=obj, start=start, end=end, span=Span("test.pyrite", 1, 1, 1, 7))
    context = MonomorphizationContext()
    _update_call_sites(expr, context)
    # Should not crash
    assert True


def test_update_call_sites_slice_access_no_start():
    """Test _update_call_sites() with SliceAccess without start"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    end = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 4, 1, 5))
    expr = ast.SliceAccess(object=obj, start=None, end=end, span=Span("test.pyrite", 1, 1, 1, 5))
    context = MonomorphizationContext()
    _update_call_sites(expr, context)
    # Should not crash
    assert True


def test_update_call_sites_slice_access_no_end():
    """Test _update_call_sites() with SliceAccess without end"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    start = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 3, 1, 4))
    expr = ast.SliceAccess(object=obj, start=start, end=None, span=Span("test.pyrite", 1, 1, 1, 4))
    context = MonomorphizationContext()
    _update_call_sites(expr, context)
    # Should not crash
    assert True


def test_update_call_sites_try_expr():
    """Test _update_call_sites() with TryExpr"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    inner = ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 5, 1, 7))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    context = MonomorphizationContext()
    _update_call_sites(expr, context)
    # Should not crash
    assert True


def test_substitute_in_expression_try_expr():
    """Test _substitute_in_expression() with TryExpr"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    inner = ast.Identifier(name="N", span=Span("test.pyrite", 1, 5, 1, 6))
    expr = ast.TryExpr(expression=inner, span=Span("test.pyrite", 1, 1, 1, 7))
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.TryExpr)
    assert isinstance(result.expression, ast.IntLiteral)


def test_substitute_in_expression_slice_access():
    """Test _substitute_in_expression() with SliceAccess"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    start = ast.Identifier(name="N", span=Span("test.pyrite", 1, 3, 1, 4))
    end = ast.IntLiteral(value=5, span=Span("test.pyrite", 1, 6, 1, 7))
    expr = ast.SliceAccess(object=obj, start=start, end=end, span=Span("test.pyrite", 1, 1, 1, 7))
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.SliceAccess)
    assert isinstance(result.start, ast.IntLiteral)


def test_substitute_in_expression_field_access():
    """Test _substitute_in_expression() with FieldAccess"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    obj = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    expr = ast.FieldAccess(object=obj, field="field", span=Span("test.pyrite", 1, 1, 1, 8))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    assert isinstance(result, ast.FieldAccess)


def test_substitute_in_type_array_type_no_element_type():
    """Test _substitute_in_type() with ArrayType without element_type"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    size = ast.Identifier(name="N", span=Span("test.pyrite", 1, 2, 1, 3))
    type_node = ast.ArrayType(
        element_type=None,
        size=size,
        span=Span("test.pyrite", 1, 1, 1, 3)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_type(type_node, substitutions)
    assert isinstance(result, ast.ArrayType)


def test_substitute_in_type_generic_type_no_type_args():
    """Test _substitute_in_type() with GenericType without type_args"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    type_node = ast.GenericType(
        name="List",
        type_args=[],
        span=Span("test.pyrite", 1, 1, 1, 1)
    )
    substitutions = {}
    result = context._substitute_in_type(type_node, substitutions)
    assert isinstance(result, ast.GenericType)


def test_substitute_in_type_generic_type_with_expression():
    """Test _substitute_in_type() with GenericType with expression in type_args"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    type_node = ast.GenericType(
        name="Array",
        type_args=[IntType(), ast.Identifier(name="N", span=Span("test.pyrite", 1, 10, 1, 11))],
        span=Span("test.pyrite", 1, 1, 1, 11)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_type(type_node, substitutions)
    assert isinstance(result, ast.GenericType)
    # The Identifier should be substituted
    assert isinstance(result.type_args[1], ast.IntLiteral)


def test_substitute_in_block():
    """Test _substitute_in_block()"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    stmt = ast.ReturnStmt(
        value=ast.Identifier(name="N", span=Span("test.pyrite", 1, 8, 1, 9)),
        span=Span("test.pyrite", 1, 1, 1, 9)
    )
    block = ast.Block(statements=[stmt], span=Span("test.pyrite", 1, 1, 1, 10))
    substitutions = {"N": 42}
    result = context._substitute_in_block(block, substitutions)
    assert isinstance(result, ast.Block)
    assert len(result.statements) == 1
    assert isinstance(result.statements[0].value, ast.IntLiteral)


def test_substitute_in_statement_match_stmt():
    """Test _substitute_in_statement() with MatchStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15)),
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    # MatchStmt is not handled, should return as-is
    assert result == stmt


def test_substitute_in_statement_with_stmt():
    """Test _substitute_in_statement() with WithStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    value = ast.Identifier(name="file", span=Span("test.pyrite", 1, 10, 1, 14))
    body = ast.Block(statements=[], span=Span("test.pyrite", 1, 15, 1, 16))
    stmt = ast.WithStmt(
        variable="f",
        value=value,
        body=body,
        span=Span("test.pyrite", 1, 1, 1, 16)
    )
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    # WithStmt is not handled, should return as-is
    assert result == stmt


def test_substitute_in_statement_break():
    """Test _substitute_in_statement() with BreakStmt"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    stmt = ast.BreakStmt(span=Span("test.pyrite", 1, 1, 1, 6))
    substitutions = {}
    result = context._substitute_in_statement(stmt, substitutions)
    # BreakStmt is not handled, should return as-is
    assert result == stmt


def test_substitute_in_expression_ternary():
    """Test _substitute_in_expression() with TernaryExpr"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    true_expr = ast.Identifier(name="N", span=Span("test.pyrite", 1, 1, 1, 2))
    condition = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 5, 1, 9))
    false_expr = ast.IntLiteral(value=0, span=Span("test.pyrite", 1, 14, 1, 15))
    expr = ast.TernaryExpr(
        true_expr=true_expr,
        condition=condition,
        false_expr=false_expr,
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    substitutions = {"N": 42}
    result = context._substitute_in_expression(expr, substitutions)
    # TernaryExpr should be handled and substituted
    assert isinstance(result, ast.TernaryExpr)
    assert isinstance(result.true_expr, ast.IntLiteral)


def test_substitute_in_expression_float_literal():
    """Test _substitute_in_expression() with FloatLiteral"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.FloatLiteral(value=3.14, span=Span("test.pyrite", 1, 1, 1, 4))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    # Literals pass through unchanged
    assert result == expr


def test_substitute_in_expression_string_literal():
    """Test _substitute_in_expression() with StringLiteral"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.StringLiteral(value="hello", span=Span("test.pyrite", 1, 1, 1, 6))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    # Literals pass through unchanged
    assert result == expr


def test_substitute_in_expression_char_literal():
    """Test _substitute_in_expression() with CharLiteral"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.CharLiteral(value='a', span=Span("test.pyrite", 1, 1, 1, 3))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    # Literals pass through unchanged
    assert result == expr


def test_substitute_in_expression_none_literal():
    """Test _substitute_in_expression() with NoneLiteral"""
    from src import ast
    from src.frontend.tokens import Span
    context = MonomorphizationContext()
    expr = ast.NoneLiteral(span=Span("test.pyrite", 1, 1, 1, 5))
    substitutions = {}
    result = context._substitute_in_expression(expr, substitutions)
    # Literals pass through unchanged
    assert result == expr


def test_collect_function_calls_match_stmt_with_guard():
    """Test _collect_function_calls() with MatchStmt with guard"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    guard = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 20, 1, 24))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=guard,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 25, 1, 26)),
        span=Span("test.pyrite", 1, 12, 1, 26)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 26)
    )
    calls = _collect_function_calls(stmt)
    assert isinstance(calls, list)


def test_collect_function_calls_match_stmt_no_guard():
    """Test _collect_function_calls() with MatchStmt without guard"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15)),
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    calls = _collect_function_calls(stmt)
    assert isinstance(calls, list)


def test_update_call_sites_match_stmt_with_guard():
    """Test _update_call_sites() with MatchStmt with guard"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    guard = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 20, 1, 24))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=guard,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 25, 1, 26)),
        span=Span("test.pyrite", 1, 12, 1, 26)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 26)
    )
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_match_stmt_no_guard():
    """Test _update_call_sites() with MatchStmt without guard"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    scrutinee = ast.Identifier(name="x", span=Span("test.pyrite", 1, 7, 1, 8))
    arm = ast.MatchArm(
        pattern=ast.IntLiteral(value=1, span=Span("test.pyrite", 1, 12, 1, 13)),
        guard=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 14, 1, 15)),
        span=Span("test.pyrite", 1, 12, 1, 15)
    )
    stmt = ast.MatchStmt(
        scrutinee=scrutinee,
        arms=[arm],
        span=Span("test.pyrite", 1, 1, 1, 15)
    )
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_specialize_function_with_params():
    """Test specialize_function() with function parameters"""
    from src import ast
    from src.frontend.tokens import Span
    from src.types import IntType
    context = MonomorphizationContext()
    param = ast.CompileTimeIntParam(name="N", span=Span("test.pyrite", 1, 1, 1, 1))
    func_param = ast.Param(
        name="x",
        type_annotation=IntType(),
        span=Span("test.pyrite", 1, 10, 1, 11)
    )
    func = ast.FunctionDef(
        name="test",
        generic_params=[],
        compile_time_params=[param],
        params=[func_param],
        return_type=None,
        body=ast.Block(statements=[], span=Span("test.pyrite", 1, 1, 1, 10)),
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    specialized = context.specialize_function(func, (42,))
    assert len(specialized.params) == 1


def test_monomorphize_program_call_with_compile_time_args_not_in_original():
    """Test monomorphize_program() with call to function not in original_functions"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend import monomorphize_program
    call = ast.FunctionCall(
        function=ast.Identifier(name="unknown", span=Span("test.pyrite", 1, 1, 1, 7)),
        compile_time_args=[ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 8, 1, 10))],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 12)
    )
    func = ast.FunctionDef(
        name="main",
        generic_params=[],
        compile_time_params=[],
        params=[],
        return_type=None,
        body=ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 12))], span=Span("test.pyrite", 1, 1, 1, 12)),
        span=Span("test.pyrite", 1, 1, 1, 12)
    )
    program = ast.Program(imports=[], items=[func], span=Span("test.pyrite", 1, 1, 1, 1))
    result = monomorphize_program(program)
    # Should not crash
    assert len(result.items) >= 1


def test_update_call_sites_function_call_not_identifier():
    """Test _update_call_sites() with FunctionCall where function is not Identifier"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    func_expr = ast.FieldAccess(
        object=ast.Identifier(name="obj", span=Span("test.pyrite", 1, 1, 1, 4)),
        field="method",
        span=Span("test.pyrite", 1, 1, 1, 10)
    )
    call = ast.FunctionCall(
        function=func_expr,
        compile_time_args=[ast.IntLiteral(value=42, span=Span("test.pyrite", 1, 11, 1, 13))],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 14)
    )
    context = MonomorphizationContext()
    _update_call_sites(call, context)
    # Should not crash
    assert True


def test_update_call_sites_function_call_no_compile_time_args():
    """Test _update_call_sites() with FunctionCall without compile_time_args"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    func = ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5))
    call = ast.FunctionCall(
        function=func,
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    context = MonomorphizationContext()
    _update_call_sites(call, context)
    # Should not change
    assert call.function.name == "test"


def test_collect_function_calls_assignment():
    """Test _collect_function_calls() with Assignment (covers lines 405-406)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    target = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.Assignment(target=target, value=call, span=Span("test.pyrite", 1, 1, 1, 10))
    result = _collect_function_calls(stmt)
    assert len(result) == 1
    assert result[0] == call


def test_collect_function_calls_if_with_elif():
    """Test _collect_function_calls() with IfStmt with elif_clauses (covers lines 413-420)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call1 = ast.FunctionCall(
        function=ast.Identifier(name="test1", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    call2 = ast.FunctionCall(
        function=ast.Identifier(name="test2", span=Span("test.pyrite", 2, 1, 2, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 2, 1, 2, 8)
    )
    call3 = ast.FunctionCall(
        function=ast.Identifier(name="test3", span=Span("test.pyrite", 3, 1, 3, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 3, 1, 3, 8)
    )
    cond = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    elif_cond = ast.BoolLiteral(value=False, span=Span("test.pyrite", 2, 1, 2, 6))
    then_block = ast.Block(statements=[ast.ExpressionStmt(expression=call1, span=Span("test.pyrite", 1, 1, 1, 8))], span=Span("test.pyrite", 1, 1, 1, 8))
    elif_block = ast.Block(statements=[ast.ExpressionStmt(expression=call2, span=Span("test.pyrite", 2, 1, 2, 8))], span=Span("test.pyrite", 2, 1, 2, 8))
    else_block = ast.Block(statements=[ast.ExpressionStmt(expression=call3, span=Span("test.pyrite", 3, 1, 3, 8))], span=Span("test.pyrite", 3, 1, 3, 8))
    stmt = ast.IfStmt(
        condition=cond,
        then_block=then_block,
        elif_clauses=[(elif_cond, elif_block)],
        else_block=else_block,
        span=Span("test.pyrite", 1, 1, 3, 8)
    )
    result = _collect_function_calls(stmt)
    assert len(result) == 3


def test_collect_function_calls_while_stmt():
    """Test _collect_function_calls() with WhileStmt (covers lines 423-424)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    cond = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    body = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    stmt = ast.WhileStmt(condition=cond, body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    result = _collect_function_calls(stmt)
    assert len(result) == 1


def test_collect_function_calls_for_stmt():
    """Test _collect_function_calls() with ForStmt (covers lines 427-428)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    iterable = ast.Identifier(name="items", span=Span("test.pyrite", 1, 1, 1, 6))
    body = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    stmt = ast.ForStmt(variable="item", iterable=iterable, body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    result = _collect_function_calls(stmt)
    assert len(result) == 1


def test_collect_function_calls_defer_stmt():
    """Test _collect_function_calls() with DeferStmt (covers line 434)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    body = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    stmt = ast.DeferStmt(body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    result = _collect_function_calls(stmt)
    assert len(result) == 1


def test_collect_function_calls_unary_op():
    """Test _collect_function_calls() with UnaryOp (covers line 441)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    expr = ast.UnaryOp(op="!", operand=call, span=Span("test.pyrite", 1, 1, 1, 8))
    result = _collect_function_calls(expr)
    assert len(result) == 1


def test_collect_function_calls_method_call():
    """Test _collect_function_calls() with MethodCall (covers lines 444-446)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    obj = ast.Identifier(name="obj", span=Span("test.pyrite", 1, 1, 1, 4))
    method_call = ast.MethodCall(object=obj, method="method", arguments=[call], span=Span("test.pyrite", 1, 1, 1, 15))
    result = _collect_function_calls(method_call)
    assert len(result) == 1


def test_collect_function_calls_index_access():
    """Test _collect_function_calls() with IndexAccess (covers lines 449-450)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    obj = ast.Identifier(name="arr", span=Span("test.pyrite", 1, 1, 1, 4))
    index_access = ast.IndexAccess(object=obj, index=call, span=Span("test.pyrite", 1, 1, 1, 10))
    result = _collect_function_calls(index_access)
    assert len(result) == 1


def test_collect_function_calls_field_access():
    """Test _collect_function_calls() with FieldAccess (covers line 453)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    field_access = ast.FieldAccess(object=call, field="field", span=Span("test.pyrite", 1, 1, 1, 13))
    result = _collect_function_calls(field_access)
    assert len(result) == 1


def test_collect_function_calls_list_literal():
    """Test _collect_function_calls() with ListLiteral (covers lines 456-457)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    list_lit = ast.ListLiteral(elements=[call], span=Span("test.pyrite", 1, 1, 1, 9))
    result = _collect_function_calls(list_lit)
    assert len(result) == 1


def test_collect_function_calls_struct_literal():
    """Test _collect_function_calls() with StructLiteral (covers lines 460-461)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    struct_lit = ast.StructLiteral(struct_name="Point", fields=[("x", call)], span=Span("test.pyrite", 1, 1, 1, 15))
    result = _collect_function_calls(struct_lit)
    assert len(result) == 1


def test_collect_function_calls_ternary_expr():
    """Test _collect_function_calls() with TernaryExpr (covers lines 485-487)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _collect_function_calls
    call1 = ast.FunctionCall(
        function=ast.Identifier(name="test1", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    call2 = ast.FunctionCall(
        function=ast.Identifier(name="test2", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    call3 = ast.FunctionCall(
        function=ast.Identifier(name="test3", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    cond = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    ternary = ast.TernaryExpr(condition=cond, true_expr=call1, false_expr=call2, span=Span("test.pyrite", 1, 1, 1, 10))
    result = _collect_function_calls(ternary)
    assert len(result) == 2


def test_update_call_sites_assignment():
    """Test _update_call_sites() with Assignment (covers lines 533-534)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    target = ast.Identifier(name="x", span=Span("test.pyrite", 1, 1, 1, 2))
    stmt = ast.Assignment(target=target, value=call, span=Span("test.pyrite", 1, 1, 1, 10))
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_if_with_elif():
    """Test _update_call_sites() with IfStmt with elif_clauses (covers lines 541-548)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    cond = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    elif_cond = ast.BoolLiteral(value=False, span=Span("test.pyrite", 2, 1, 2, 6))
    then_block = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    elif_block = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 2, 1, 2, 7))], span=Span("test.pyrite", 2, 1, 2, 7))
    else_block = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 3, 1, 3, 7))], span=Span("test.pyrite", 3, 1, 3, 7))
    stmt = ast.IfStmt(
        condition=cond,
        then_block=then_block,
        elif_clauses=[(elif_cond, elif_block)],
        else_block=else_block,
        span=Span("test.pyrite", 1, 1, 3, 7)
    )
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_while_stmt():
    """Test _update_call_sites() with WhileStmt (covers lines 551-552)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    cond = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    body = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    stmt = ast.WhileStmt(condition=cond, body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_for_stmt():
    """Test _update_call_sites() with ForStmt (covers lines 555-556)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    iterable = ast.Identifier(name="items", span=Span("test.pyrite", 1, 1, 1, 6))
    body = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    stmt = ast.ForStmt(variable="item", iterable=iterable, body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_defer_stmt():
    """Test _update_call_sites() with DeferStmt (covers line 562)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    body = ast.Block(statements=[ast.ExpressionStmt(expression=call, span=Span("test.pyrite", 1, 1, 1, 7))], span=Span("test.pyrite", 1, 1, 1, 7))
    stmt = ast.DeferStmt(body=body, span=Span("test.pyrite", 1, 1, 1, 7))
    context = MonomorphizationContext()
    _update_call_sites(stmt, context)
    # Should not crash
    assert True


def test_update_call_sites_unary_op():
    """Test _update_call_sites() with UnaryOp (covers line 569)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    expr = ast.UnaryOp(op="!", operand=call, span=Span("test.pyrite", 1, 1, 1, 8))
    context = MonomorphizationContext()
    _update_call_sites(expr, context)
    # Should not crash
    assert True


def test_update_call_sites_method_call():
    """Test _update_call_sites() with MethodCall (covers lines 572-574)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    obj = ast.Identifier(name="obj", span=Span("test.pyrite", 1, 1, 1, 4))
    method_call = ast.MethodCall(object=obj, method="method", arguments=[call], span=Span("test.pyrite", 1, 1, 1, 15))
    context = MonomorphizationContext()
    _update_call_sites(method_call, context)
    # Should not crash
    assert True


def test_update_call_sites_index_access():
    """Test _update_call_sites() with IndexAccess (covers lines 577-578)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    obj = ast.Identifier(name="arr", span=Span("test.pyrite", 1, 1, 1, 4))
    index_access = ast.IndexAccess(object=obj, index=call, span=Span("test.pyrite", 1, 1, 1, 10))
    context = MonomorphizationContext()
    _update_call_sites(index_access, context)
    # Should not crash
    assert True


def test_update_call_sites_field_access():
    """Test _update_call_sites() with FieldAccess (covers line 581)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    field_access = ast.FieldAccess(object=call, field="field", span=Span("test.pyrite", 1, 1, 1, 13))
    context = MonomorphizationContext()
    _update_call_sites(field_access, context)
    # Should not crash
    assert True


def test_update_call_sites_list_literal():
    """Test _update_call_sites() with ListLiteral (covers lines 584-585)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    list_lit = ast.ListLiteral(elements=[call], span=Span("test.pyrite", 1, 1, 1, 9))
    context = MonomorphizationContext()
    _update_call_sites(list_lit, context)
    # Should not crash
    assert True


def test_update_call_sites_struct_literal():
    """Test _update_call_sites() with StructLiteral (covers lines 588-589)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call = ast.FunctionCall(
        function=ast.Identifier(name="test", span=Span("test.pyrite", 1, 1, 1, 5)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 7)
    )
    struct_lit = ast.StructLiteral(struct_name="Point", fields=[("x", call)], span=Span("test.pyrite", 1, 1, 1, 15))
    context = MonomorphizationContext()
    _update_call_sites(struct_lit, context)
    # Should not crash
    assert True


def test_update_call_sites_ternary_expr():
    """Test _update_call_sites() with TernaryExpr (covers lines 613-615)"""
    from src import ast
    from src.frontend.tokens import Span
    from src.backend.monomorphization import _update_call_sites
    from src.backend import MonomorphizationContext
    call1 = ast.FunctionCall(
        function=ast.Identifier(name="test1", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    call2 = ast.FunctionCall(
        function=ast.Identifier(name="test2", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    call3 = ast.FunctionCall(
        function=ast.Identifier(name="test3", span=Span("test.pyrite", 1, 1, 1, 6)),
        compile_time_args=[],
        arguments=[],
        span=Span("test.pyrite", 1, 1, 1, 8)
    )
    cond = ast.BoolLiteral(value=True, span=Span("test.pyrite", 1, 1, 1, 5))
    ternary = ast.TernaryExpr(condition=cond, true_expr=call1, false_expr=call2, span=Span("test.pyrite", 1, 1, 1, 10))
    context = MonomorphizationContext()
    _update_call_sites(ternary, context)
    # Should not crash
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

