#!/usr/bin/env python3
"""
Regression test to verify coverage safety fixes.

This script verifies that:
1. Coverage scope is correctly limited to forge/src
2. Pytest collection is limited to forge/tests
3. Safe wrapper can run without crashing
4. Resource usage stays within reasonable bounds
"""

import sys
import subprocess
import time
from pathlib import Path


def find_repo_root() -> Path:
    """Find repository root"""
    script_dir = Path(__file__).parent
    return script_dir.parent


def run_command(cmd: list, description: str, timeout: int = 120) -> tuple[bool, str]:
    """Run command and return (success, output)"""
    repo_root = find_repo_root()
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, f"Error: {e}"


def test_pytest_collection_scope():
    """Test that pytest only collects from forge/tests"""
    cmd = [sys.executable, "tools/pytest.py", "--collect-only", "-q"]
    success, output = run_command(cmd, "Pytest collection scope check", timeout=60)
    
    if not success:
        return False, f"Collection failed: {output[:500]}"
    
    # Check that we're not collecting from vscode-pyrite or other large dirs
    bad_patterns = ["vscode-pyrite", "node_modules", ".venv"]
    for pattern in bad_patterns:
        if pattern in output:
            return False, f"Collection includes {pattern} - should be excluded"
    
    # Check that we ARE collecting from forge/tests
    if "forge/tests" not in output and "test_" not in output:
        return False, "Not collecting from forge/tests"
    
    return True, "Collection scope is correct"


def test_coverage_scope():
    """Test that coverage only measures forge/src"""
    cmd = [
        sys.executable,
        "tools/pytest.py",
        "forge/tests/frontend/test_lexer.py",
        "--cov=forge/src",
        "--cov-report=term",
        "-q"
    ]
    success, output = run_command(cmd, "Coverage scope check (small test)", timeout=60)
    
    if not success:
        return False, f"Coverage test failed: {output[:500]}"
    
    # Check that coverage report shows files from forge/src
    if "forge/src" not in output and "Name" not in output:
        return False, "Coverage report doesn't show expected format"
    
    # Check that we're not seeing coverage for excluded directories
    bad_patterns = ["vscode-pyrite", "node_modules", "tools/", "scripts/"]
    for pattern in bad_patterns:
        if f"{pattern}/" in output or f"{pattern}\\" in output:
            return False, f"Coverage includes {pattern} - should be excluded"
    
    return True, "Coverage scope is correct"


def test_safe_wrapper():
    """Test that safe wrapper works"""
    safe_wrapper = find_repo_root() / "tools" / "run_tests_safe.py"
    if not safe_wrapper.exists():
        return False, "Safe wrapper not found"
    
    cmd = [
        sys.executable,
        str(safe_wrapper),
        "--max-seconds=30",
        "--max-rss-mb=1024",
        "--",
        sys.executable,
        "tools/pytest.py",
        "forge/tests/frontend/test_lexer.py",
        "-q"
    ]
    success, output = run_command(cmd, "Safe wrapper functionality", timeout=45)
    
    if not success:
        return False, f"Safe wrapper test failed: {output[:500]}"
    
    # Check that metrics were mentioned
    if "metrics" not in output.lower() and "PROCESS COMPLETED" not in output:
        return False, "Safe wrapper didn't produce expected output"
    
    return True, "Safe wrapper works correctly"


def main():
    """Run all regression tests"""
    repo_root = find_repo_root()
    os.chdir(repo_root)
    
    print("=" * 70)
    print("COVERAGE SAFETY REGRESSION TESTS")
    print("=" * 70)
    
    tests = [
        ("Pytest collection scope", test_pytest_collection_scope),
        ("Coverage scope", test_coverage_scope),
        ("Safe wrapper", test_safe_wrapper),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success, message = test_func()
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"\n{name}: {status}")
            print(f"  {message}")
            results.append((name, success, message))
        except Exception as e:
            print(f"\n{name}: ❌ ERROR")
            print(f"  {e}")
            results.append((name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All regression tests passed!")
        return 0
    else:
        print("\n❌ Some regression tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    import os
    sys.exit(main())
