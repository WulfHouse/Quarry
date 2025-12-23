#!/usr/bin/env python3
"""
Local development test runner - optimized for speed.

This script runs tests with coverage but skips slow operations:
- No HTML report generation (use --cov-report=term only)
- Optional parallel execution
- Quick feedback for local development

Usage:
    python tools/run_tests_local.py                    # All tests, term report only
    python tools/run_tests_local.py -n auto            # Parallel execution
    python tools/run_tests_local.py test_lexer.py      # Specific test file
    python tools/run_tests_local.py --no-cov           # Skip coverage (fastest)
"""

import sys
import subprocess
from pathlib import Path


def find_repo_root() -> Path:
    """Find repository root"""
    current = Path.cwd().resolve()
    for path in [current] + list(current.parents):
        if (path / "forge").exists():
            return path
    return Path.cwd()


def main():
    """Main entry point"""
    repo_root = find_repo_root()
    
    # Parse arguments
    args = sys.argv[1:]
    use_coverage = "--no-cov" not in args
    use_parallel = "-n" in args or "--numprocesses" in args
    
    # Build command
    cmd = [sys.executable, "tools/testing/pytest.py"]
    
    # Add coverage if requested
    if use_coverage:
        cmd.extend([
            "--cov=forge/src",
            "--cov-report=term",  # Terminal only - no HTML/JSON
        ])
    
    # Add parallel execution if requested
    if use_parallel:
        # Check if pytest-xdist is available
        try:
            import pytest_xdist
            # -n auto will use all CPU cores
            if "-n" not in args and "--numprocesses" not in args:
                cmd.append("-n")
                cmd.append("auto")
        except ImportError:
            print("WARNING: pytest-xdist not installed. Install with: pip install pytest-xdist")
            print("         Running tests sequentially...")
    
    # Add remaining arguments
    for arg in args:
        if arg != "--no-cov":  # Skip this flag, we handled it
            cmd.append(arg)
    
    # Run tests
    print("=" * 70)
    print("LOCAL TEST RUNNER")
    print("=" * 70)
    print(f"Command: {' '.join(cmd)}")
    if use_coverage:
        print("Coverage: Enabled (term report only - no HTML)")
    else:
        print("Coverage: Disabled (fastest)")
    if use_parallel:
        print("Parallel: Enabled")
    print("=" * 70)
    print()
    
    result = subprocess.run(cmd, cwd=repo_root)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
