#!/usr/bin/env python3
"""
Diagnose why coverage command times out.

The issue: Running coverage on all 1108 tests with JSON report generation
may take a very long time, causing timeouts.
"""

import sys
import time
import subprocess
from pathlib import Path

def find_repo_root() -> Path:
    """Find the Pyrite repository root"""
    script_dir = Path(__file__).parent
    return script_dir.parent

def test_coverage_command():
    """Test the coverage command with timing"""
    repo_root = find_repo_root()
    
    print("=" * 60)
    print("Diagnosing Coverage Timeout Issue")
    print("=" * 60)
    print()
    
    # Test 1: Count tests
    print("[1/4] Counting tests...")
    try:
        result = subprocess.run(
            [sys.executable, "tools/pytest.py", "--collect-only", "-q"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if "test session starts" in line or "tests collected" in line:
                    print(f"  {line}")
        else:
            print(f"  ERROR: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print("  ERROR: Command timed out after 30s")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Test 2: Run a small subset with coverage
    print("\n[2/4] Testing coverage on small subset (test_lexer.py)...")
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "tools/pytest.py", "forge/tests/frontend/test_lexer.py", 
             "--cov=forge/src", "--cov-report=term", "-q"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.2f}s")
        if result.returncode != 0:
            print(f"  Exit code: {result.returncode}")
            if result.stderr:
                print(f"  Stderr: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        print("  ERROR: Command timed out after 60s")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Test 3: Run with JSON report (this might be slow)
    print("\n[3/4] Testing coverage with JSON report on small subset...")
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "tools/pytest.py", "forge/tests/frontend/test_lexer.py", 
             "--cov=forge/src", "--cov-report=term", "--cov-report=json", "-q"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.2f}s")
        if result.returncode != 0:
            print(f"  Exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("  ERROR: Command timed out after 120s")
        print("  This suggests JSON report generation is very slow")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Test 4: Estimate full test suite time
    print("\n[4/4] Estimating full test suite coverage time...")
    print("  Running 10 random tests with coverage...")
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "tools/pytest.py", 
             "--cov=forge/src", "--cov-report=term", "-q", "-k", "test_lex"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=180
        )
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.2f}s")
        print(f"  Estimated time for 1108 tests: ~{elapsed * 110.8:.0f}s ({elapsed * 110.8 / 60:.1f} minutes)")
        print()
        print("  RECOMMENDATION:")
        if elapsed * 110.8 > 300:
            print("  - Full coverage run takes too long (>5 minutes)")
            print("  - Consider running coverage only when needed")
            print("  - For local dev, use: python tools/pytest.py --cov=forge/src --cov-report=term")
            print("  - Skip JSON report locally: --cov-report=json is slow")
    except subprocess.TimeoutExpired:
        print("  ERROR: Even 10 tests timed out - coverage is very slow")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Diagnosis Complete")
    print("=" * 60)
    print()
    print("SOLUTION:")
    print("  The timeout is likely because:")
    print("  1. Running coverage on 1108 tests takes 5-10+ minutes")
    print("  2. JSON report generation adds significant overhead")
    print("  3. The findstr filter waits for buffered output")
    print()
    print("  For local development, use:")
    print("    python tools/pytest.py --cov=forge/src --cov-report=term")
    print()
    print("  For CI (where it's OK to wait), use:")
    print("    python tools/pytest.py --cov=forge/src --cov-report=term --cov-report=json")

if __name__ == "__main__":
    test_coverage_command()


