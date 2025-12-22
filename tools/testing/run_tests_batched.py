#!/usr/bin/env python3
"""Run tests in batches"""

import subprocess
import sys
from pathlib import Path

# Test batches - organized by complexity/size
BATCHES = [
    # Batch 1: Fast unit tests (lexer, tokens, types, ast)
    [
        "test_lexer.py",
        "test_tokens_bridge.py",
        "test_types.py",
        "test_ast.py",
        "test_ast_bridge.py",
        "test_diagnostics.py",
        "test_error_explanations.py",
        "test_error_formatter.py",
    ],
    
    # Batch 2: Parser and symbol table
    [
        "test_parser.py",
        "test_symbol_table.py",
        "test_try_operator.py",
    ],
    
    # Batch 3: Type checker
    [
        "test_type_checker.py",
        "test_where_clauses.py",
        "test_traits.py",
        "test_trait_typechecking.py",
        "test_associated_types.py",
    ],
    
    # Batch 4: Ownership and borrow checker
    [
        "test_ownership.py",
        "test_borrow_checker.py",
    ],
    
    # Batch 5: Codegen (larger tests)
    [
        "test_codegen.py",
        "test_codegen_advanced.py",
        "test_trait_codegen.py",
    ],
    
    # Batch 6: Compiler and integration
    [
        "test_compiler.py",
        "test_integration.py",
        "test_bootstrap.py",
    ],
    
    # Batch 7: Closures
    [
        "test_closures.py",
        "test_closure_captures.py",
        "test_closure_codegen.py",
        "test_closure_inlining.py",
        "test_closure_inline_pass.py",
        "test_closure_inline_pass_basic.py",
        "test_closure_inline_pass_collect.py",
        "test_closure_inline_pass_edge_cases.py",
        "test_closure_inline_pass_inline.py",
        "test_runtime_closure_codegen.py",
        "test_parameter_closure_call_site.py",
    ],
    
    # Batch 8: Advanced features
    [
        "test_monomorphization.py",
        "test_with_desugar.py",
        "test_defer.py",
        "test_arrays.py",
        "test_compile_time_params.py",
    ],
    
    # Batch 9: FFI and linking
    [
        "test_ffi.py",
        "test_ffi_function_pointers.py",
        "test_ffi_opaque.py",
        "test_linker.py",
        "test_map_ffi.py",
    ],
    
    # Batch 10: Module system and incremental
    [
        "test_module_system.py",
        "test_incremental.py",
        "test_incremental_default.py",
    ],
    
    # Batch 11: LSP and tools
    [
        "test_lsp.py",
        "test_lsp_hover_enhanced.py",
        "test_quarry_tools.py",
        "test_path.py",
    ],
    
    # Batch 12: Specialized features
    [
        "test_closeable_trait.py",
        "test_string_formatting.py",
        "test_file_io.py",
        "test_drops.py",
        "test_deterministic_build.py",
    ],
    
    # Batch 13: Performance and analysis
    [
        "test_perf_lock.py",
        "test_cost_analysis_enhanced.py",
        "test_binary_size.py",
    ],
    
    # Batch 14: Pyrite source tests
    [
        "test_ast_pyrite.py",
        "test_types_pyrite.py",
        "test_tokens_pyrite.py",
    ],
    
    # Batch 15: Miscellaneous
    [
        "test_fast_smoke.py",
        "test_auto_fix_interactive.py",
    ],
]


def run_batch(batch_num: int, test_files: list):
    """Run a batch of tests"""
    print(f"\n{'='*80}")
    print(f"BATCH {batch_num}/{len(BATCHES)}: {len(test_files)} test files")
    print(f"{'='*80}")
    
    repo_root = Path(__file__).parent.parent.parent
    test_dir = repo_root / "forge" / "tests"
    
    # Build test paths (relative to test_dir)
    test_paths = [f"forge/tests/{f}" for f in test_files]
    
    if not test_paths:
        print("No tests to run in this batch (all excluded)")
        return True
    
    # Use the pytest.py wrapper which handles PYTHONPATH correctly
    pytest_wrapper = repo_root / "tools" / "testing" / "pytest.py"
    
    # Run pytest with these test files
    cmd = [
        sys.executable,
        str(pytest_wrapper),
        "-ra",  # Show extra test summary info
        "--durations=10",  # Show 10 slowest tests
        "-v",  # Verbose
        "--timeout=30",  # Per-test timeout
        "-n", "0",  # Disable parallel execution for batched runs (safer)
    ] + test_paths
    
    print(f"Running: python tools/testing/pytest.py {' '.join(test_paths)}")
    print()
    
    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode == 0


def main():
    """Run all test batches"""
    if len(sys.argv) > 1:
        # Run specific batch
        batch_num = int(sys.argv[1])
        if 1 <= batch_num <= len(BATCHES):
            success = run_batch(batch_num, BATCHES[batch_num - 1])
            sys.exit(0 if success else 1)
        else:
            print(f"Invalid batch number. Must be between 1 and {len(BATCHES)}")
            sys.exit(1)
    
    # Run all batches
    print(f"Running {len(BATCHES)} batches of tests")
    print(f"Total test files: {sum(len(b) for b in BATCHES)}")
    
    failed_batches = []
    for i, batch in enumerate(BATCHES, 1):
        success = run_batch(i, batch)
        if not success:
            failed_batches.append(i)
        print(f"\nBatch {i} {'PASSED' if success else 'FAILED'}")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total batches: {len(BATCHES)}")
    print(f"Passed: {len(BATCHES) - len(failed_batches)}")
    print(f"Failed: {len(failed_batches)}")
    if failed_batches:
        print(f"Failed batches: {failed_batches}")
    
    sys.exit(0 if not failed_batches else 1)


if __name__ == "__main__":
    main()
