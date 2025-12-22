#!/usr/bin/env python3
"""
Pyrite fast test runner - runs only fast tests (Lane 1)
This is a safe entrypoint that cannot accidentally run the full legacy suite.

Usage:
    python tools/pytest_fast.py                    # Run only fast tests
    python tools/pytest_fast.py -v                 # Verbose output
    python tools/pytest_fast.py --allow-slow       # Override: allow slow tests (for Lane 2/3)
"""

import sys
import os
import subprocess
from pathlib import Path


def find_repo_root() -> Path:
    """Find the Pyrite repository root by looking for forge directory"""
    current = Path.cwd().resolve()
    
    # Walk up the directory tree looking for forge
    for path in [current] + list(current.parents):
        if (path / "forge").exists() and (path / "forge" / "src").exists():
            return path
    
    # Fallback: if we're in the repo, try relative to script location
    script_dir = Path(__file__).parent.resolve()
    # If script is in tools/, go up one level to get repo root
    if (script_dir.parent / "forge").exists():
        return script_dir.parent
    
    print("Error: Could not find Pyrite repository root.")
    print("Please run this script from within the Pyrite repository.")
    sys.exit(1)


def main():
    """Main entry point"""
    # Handle help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Pyrite Fast Test Runner (Lane 1)")
        print()
        print("This runner executes only fast tests (marked with @pytest.mark.fast).")
        print("It is designed to run in 2-5 minutes and catch critical bugs.")
        print()
        print("Usage:")
        print("  python tools/pytest_fast.py                    # Run only fast tests")
        print("  python tools/pytest_fast.py -v                 # Verbose output")
        print("  python tools/pytest_fast.py --allow-slow       # Override: allow slow tests")
        print()
        print("Lanes:")
        print("  Lane 1 (fast):     Core compiler tests (lexer, parser, type_checker)")
        print("                     Target: 2-5 minutes")
        print("  Lane 2 (integration): Full pipeline tests, module system")
        print("                     Target: 10-20 minutes")
        print("  Lane 3 (slow):     Bootstrap, LSP, E2E tests")
        print("                     Target: 30-60 minutes (nightly)")
        print()
        print("Common pytest options:")
        print("  -v, --verbose          Verbose output")
        print("  -k EXPRESSION          Run tests matching expression")
        print("  -x, --exitfirst        Exit on first failure")
        print("  --tb=short             Shorter traceback format")
        print()
        return 0
    
    repo_root = find_repo_root()
    
    # Add forge to Python path
    compiler_path = repo_root / "forge"
    if str(compiler_path) not in sys.path:
        sys.path.insert(0, str(compiler_path))
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("Error: pytest is not installed.")
        print("Install it with: pip install pytest")
        sys.exit(1)
    
    # Parse arguments
    allow_slow = '--allow-slow' in sys.argv
    if allow_slow:
        sys.argv.remove('--allow-slow')
    
    # Resolve test paths to absolute if they're relative
    test_args = []
    original_cwd = Path.cwd()
    
    for arg in sys.argv[1:]:
        if not arg.startswith('-') and not arg.startswith('--'):
            # Might be a test path
            if not Path(arg).is_absolute():
                # First try relative to current directory
                abs_path = original_cwd / arg
                if abs_path.exists():
                    test_args.append(str(abs_path.resolve()))
                else:
                    # Try relative to forge/tests
                    test_path = compiler_path / "tests" / arg
                    if test_path.exists():
                        test_args.append(str(test_path.resolve()))
                    else:
                        # Try just the filename in tests directory
                        test_path = compiler_path / "tests" / Path(arg).name
                        if test_path.exists():
                            test_args.append(str(test_path.resolve()))
                        else:
                            # Pass through as-is (pytest will handle it)
                            test_args.append(arg)
            else:
                test_args.append(arg)
        else:
            test_args.append(arg)
    
    # If no test paths specified, default to forge/tests
    has_test_path = any(not arg.startswith('-') and not arg.startswith('--') for arg in test_args)
    if not has_test_path:
        test_args.insert(0, str(compiler_path / "tests"))
    
    # Add marker filter: only fast tests by default
    if not allow_slow:
        # Check if -m flag is already present
        has_marker = any(arg.startswith('-m') or arg.startswith('--markers') for arg in test_args)
        if not has_marker:
            test_args.insert(0, '-m')
            test_args.insert(1, 'fast')  # Fast tests
    
    # Add parallelization by default (unless explicitly disabled)
    has_n_flag = any(arg.startswith('-n') or arg == '--numprocesses' for arg in test_args)
    if not has_n_flag:
        # Check if user explicitly wants to disable parallelization
        if '-n' not in sys.argv and '--numprocesses' not in sys.argv:
            test_args.append('-n')
            test_args.append('auto')
    
    # Change to repo root for consistent behavior
    original_cwd = os.getcwd()
    original_pythonpath = os.environ.get('PYTHONPATH', '')
    try:
        os.chdir(repo_root)
        
        # Set PYTHONPATH to include forge for imports
        pythonpath = str(compiler_path)
        if original_pythonpath:
            pythonpath = f"{pythonpath}{os.pathsep}{original_pythonpath}"
        os.environ['PYTHONPATH'] = pythonpath
        
        # Skip collection check by default to avoid hangs
        # The marker filter (-m fast) will handle test selection
        # If no fast tests exist, pytest will report it clearly
        
        # Use subprocess to run pytest to avoid recursion issues
        # This ensures pytest runs as a separate process
        cmd = [sys.executable, '-m', 'pytest'] + test_args
        result = subprocess.run(cmd, cwd=repo_root)
        sys.exit(result.returncode)
    finally:
        os.chdir(original_cwd)
        if original_pythonpath:
            os.environ['PYTHONPATH'] = original_pythonpath
        elif 'PYTHONPATH' in os.environ:
            del os.environ['PYTHONPATH']


if __name__ == "__main__":
    main()
