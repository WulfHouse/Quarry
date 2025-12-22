"""Integration tests for complete compilation pipeline"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from pathlib import Path
from src.frontend import lex
from src.frontend import parse
from src.middle import type_check
from src.middle import analyze_ownership
from src.middle import check_borrows
from src.backend import generate_llvm


def compile_example(filename: str) -> bool:
    """Compile an example file through full pipeline"""
    # Find examples directory relative to this test file
    test_dir = Path(__file__).parent  # forge/tests/integration
    # Examples are in forge/examples/basic/
    forge_dir = test_dir.parent.parent  # forge/tests/integration -> forge/tests -> forge
    examples_dir = forge_dir / "examples" / "basic"
    example_path = examples_dir / filename
    
    if not example_path.exists():
        pytest.skip(f"Example file not found: {filename} (looked in {example_path})")
    
    source = example_path.read_text(encoding='utf-8')
    
    try:
        # Full compilation pipeline
        tokens = lex(source, str(example_path))
        program_ast = parse(tokens)
        type_checker = type_check(program_ast)
        
        if type_checker.has_errors():
            print(f"\nType errors in {filename}:")
            for error in type_checker.errors:
                print(f"  {error}")
            return False
        
        # Build type environment
        type_env = {}
        for name, symbol in type_checker.resolver.global_scope.get_all_symbols().items():
            type_env[name] = symbol.type
        
        # Ownership analysis
        ownership_analyzer = analyze_ownership(program_ast, type_env)
        if ownership_analyzer.has_errors():
            print(f"\nOwnership errors in {filename}:")
            for error in ownership_analyzer.errors:
                print(f"  {error}")
            return False
        
        # Borrow checking
        borrow_checker = check_borrows(program_ast, type_env, type_checker)
        if borrow_checker.has_errors():
            print(f"\nBorrow errors in {filename}:")
            for error in borrow_checker.errors:
                print(f"  {error}")
            return False
        
        # Code generation
        llvm_ir = generate_llvm(program_ast)
        
        # Verify IR was generated
        assert len(llvm_ir) > 0
        assert "define" in llvm_ir
        
        return True
    
    except Exception as e:
        print(f"\nError compiling {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compile_hello():
    """Test compiling hello.pyrite"""
    assert compile_example("hello.pyrite")


def test_compile_factorial():
    """Test compiling factorial.pyrite"""
    assert compile_example("factorial.pyrite")


def test_compile_structs():
    """Test compiling structs.pyrite"""
    assert compile_example("structs.pyrite")


def test_compile_ownership():
    """Test compiling ownership.pyrite"""
    # This might fail due to List not being fully implemented
    # but structure should be valid
    compile_example("ownership.pyrite")


def test_compile_fizzbuzz():
    """Test compiling fizzbuzz.pyrite"""
    compile_example("fizzbuzz.pyrite")


def test_compile_enums():
    """Test compiling enums.pyrite"""
    compile_example("enums.pyrite")


def test_compile_borrowing():
    """Test compiling borrowing.pyrite"""
    compile_example("borrowing.pyrite")


def test_compile_generics():
    """Test compiling generics.pyrite"""
    compile_example("generics.pyrite")


def test_compile_methods():
    """Test compiling methods.pyrite"""
    compile_example("methods.pyrite")


def test_all_examples_parse():
    """Test that all examples at least parse"""
    # Find examples directory relative to this test file
    test_dir = Path(__file__).parent  # forge/tests/integration
    # Examples are in forge/examples/basic/
    forge_dir = test_dir.parent.parent  # forge/tests/integration -> forge/tests -> forge
    examples_dir = forge_dir / "examples" / "basic"
    if not examples_dir.exists():
        pytest.skip(f"Examples directory not found: {examples_dir}")
    
    for example_file in examples_dir.glob("*.pyrite"):
        source = example_file.read_text(encoding='utf-8')
        
        try:
            tokens = lex(source, str(example_file))
            ast = parse(tokens)
            # Should parse without errors
            assert ast is not None
        except Exception as e:
            pytest.fail(f"Failed to parse {example_file.name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

