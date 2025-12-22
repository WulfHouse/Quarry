#!/usr/bin/env python3
"""
Debug script for try operator type resolution issues.

This script runs a minimal try operator test with tracing enabled
to diagnose UNKNOWN type resolution problems.
"""

import os
import sys
from pathlib import Path

# Add forge to path
script_dir = Path(__file__).parent
repo_root = script_dir.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

# Enable tracing
os.environ['PYRITE_DEBUG_TYPE_RESOLUTION'] = '1'

# Import test utilities
from src.type_checker import TypeChecker
from src.parser import Parser
from src.lexer import Lexer

def test_minimal_try_operator():
    """Test minimal try operator case"""
    source = """
enum Result[T, E]:
    Ok(value: T)
    Err(error: E)

fn get_value() -> Result[int, String]:
    return Result.Ok(42)
"""
    
    print("=" * 60)
    print("Debug Try Operator - Minimal Test")
    print("=" * 60)
    print()
    
    # Parse
    print("[1/3] Parsing...")
    lexer = Lexer(source, '<input>')
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse_program()
    print("  [OK] Parsed successfully")
    
    # Inspect AST for Result.Ok(42)
    if program.items:
        for item in program.items:
            if hasattr(item, 'name') and item.name == 'get_value':
                if hasattr(item, 'body') and hasattr(item.body, 'statements'):
                    for stmt in item.body.statements:
                        if hasattr(stmt, 'value'):
                            print(f"  Return statement value type: {type(stmt.value).__name__}")
                            if hasattr(stmt.value, 'function'):
                                print(f"    Function type: {type(stmt.value.function).__name__}")
                                if hasattr(stmt.value.function, 'object'):
                                    print(f"      Object type: {type(stmt.value.function.object).__name__}")
                                    if hasattr(stmt.value.function.object, 'name'):
                                        print(f"        Object name: {stmt.value.function.object.name}")
                                if hasattr(stmt.value.function, 'field'):
                                    print(f"      Field: {stmt.value.function.field}")
    print()
    
    # Type check
    print("[2/3] Type checking...")
    type_checker = TypeChecker()
    type_checker.check_program(program)
    print()
    
    # Report
    print("[3/3] Results:")
    if type_checker.has_errors():
        print(f"  [FAIL] {len(type_checker.errors)} type errors:")
        for error in type_checker.errors:
            print(f"    - {error}")
    else:
        print("  [OK] No type errors")
    
    print()
    print("=" * 60)
    print("Trace complete")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_minimal_try_operator()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
