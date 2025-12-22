#!/usr/bin/env python3
"""
Pyrite test runner wrapper - works from anywhere in the repo
Auto-detects repo root and sets up paths correctly

Usage:
    python tools/pytest.py                    # Run all tests
    python tools/pytest.py tests/test_lexer.py  # Run specific test file
    python tools/pytest.py -v                 # Verbose output
    python tools/pytest.py -k test_ownership  # Run tests matching pattern
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
        print("Pyrite Test Runner")
        print()
        print("Usage:")
        print("  python tools/pytest.py                    # Run all tests")
        print("  python tools/pytest.py tests/test_lexer.py  # Run specific test file")
        print("  python tools/pytest.py -v                 # Verbose output")
        print("  python tools/pytest.py -k test_ownership  # Run tests matching pattern")
        print("  python tools/pytest.py --timing           # Generate test_timing.json")
        print()
        print("Common pytest options:")
        print("  -v, --verbose          Verbose output")
        print("  -k EXPRESSION          Run tests matching expression")
        print("  -x, --exitfirst        Exit on first failure")
        print("  --tb=short             Shorter traceback format")
        print("  --cov=src              Show coverage report")
        print("  --timing                Generate test_timing.json with test durations")
        print()
        print("Examples:")
        print("  python tools/pytest.py tests/test_lexer.py -v")
        print("  python tools/pytest.py -k ownership")
        print("  python tools/pytest.py --cov=src --cov-report=html")
        print("  python tools/pytest.py --timing")
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
    
    # Check for --timing flag
    enable_timing = '--timing' in sys.argv
    if enable_timing:
        sys.argv.remove('--timing')
    
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
    
    # Add parallelization by default (unless explicitly disabled)
    has_n_flag = any(arg.startswith('-n') or arg == '--numprocesses' for arg in test_args)
    if not has_n_flag:
        # Check if user explicitly wants to disable parallelization
        if '-n' not in sys.argv and '--numprocesses' not in sys.argv:
            test_args.append('-n')
            test_args.append('auto')
    
    # Add timing instrumentation if requested
    if enable_timing:
        # Add --durations=0 to get all test durations
        if '--durations' not in ' '.join(test_args):
            test_args.append('--durations=0')
    
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
        
        # Use subprocess to run pytest to avoid recursion issues
        # This ensures pytest runs as a separate process
        cmd = [sys.executable, '-m', 'pytest'] + test_args
        
        if enable_timing:
            # Capture output for timing analysis
            result = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True
            )
            # Write output to stdout/stderr
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            
            # Parse timing and generate JSON
            try:
                # Import from tools/testing/test_timing.py
                import importlib.util
                test_timing_path = repo_root / "tools" / "testing" / "test_timing.py"
                spec = importlib.util.spec_from_file_location("test_timing", test_timing_path)
                test_timing = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_timing)
                
                timings = test_timing.parse_pytest_durations(result.stdout + result.stderr)
                timing_file = repo_root / "test_timing.json"
                test_timing.generate_timing_json(timings, timing_file)
            except Exception as e:
                print(f"\nWarning: Failed to generate timing JSON: {e}", file=sys.stderr)
            
            sys.exit(result.returncode)
        else:
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

