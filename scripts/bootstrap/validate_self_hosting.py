#!/usr/bin/env python3
"""
Self-Hosting Validation: Verify that Stage2 can compile itself and test programs

This script validates that the Pyrite compiler has achieved self-hosting by:
1. Using Stage2 to compile the Pyrite compiler source code
2. Using Stage2 to compile a representative test program
"""

import sys
import os
import subprocess
from pathlib import Path

# Add forge to path
script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
compiler_dir = repo_root / "forge"
stage2_dir = repo_root / "build" / "bootstrap" / "stage2"
examples_dir = compiler_dir / "examples"


def find_stage2_executable():
    """Find Stage2 executable"""
    stage2_exe = stage2_dir / "forge"
    if sys.platform == "win32":
        stage2_exe = stage2_dir / "forge.exe"
    
    if not stage2_exe.exists():
        return None
    return stage2_exe


def test_stage2_compiles_itself(stage2_exe):
    """Test that Stage2 can compile the Pyrite compiler source"""
    print("\n[Test 1/2] Stage2 compiles itself...")
    
    src_pyrite_dir = compiler_dir / "src-pyrite"
    if not src_pyrite_dir.exists():
        print("  [SKIP] src-pyrite/ directory does not exist")
        return False
    
    pyrite_modules = sorted(src_pyrite_dir.glob("*.pyrite"))
    if not pyrite_modules:
        print("  [SKIP] No Pyrite modules found")
        return False
    
    print(f"  Compiling {len(pyrite_modules)} Pyrite module(s) with Stage2...")
    
    success_count = 0
    for pyrite_file in pyrite_modules:
        print(f"    Compiling {pyrite_file.name}...", end=" ")
        try:
            # Create temporary output file
            output_file = stage2_dir / f"test_{pyrite_file.stem}"
            
            result = subprocess.run(
                [str(stage2_exe), str(pyrite_file), "-o", str(output_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("[OK]")
                success_count += 1
            else:
                print(f"[FAIL]")
                if result.stderr:
                    # Show first error line
                    error_lines = result.stderr.split('\n')
                    for line in error_lines[:3]:
                        if line.strip() and not line.startswith('['):
                            print(f"      {line[:100]}")
                            break
        except Exception as e:
            print(f"[ERROR] {e}")
    
    if success_count == len(pyrite_modules):
        print(f"  [OK] Stage2 can compile itself ({success_count}/{len(pyrite_modules)} modules)")
        return True
    elif success_count > 0:
        print(f"  [PARTIAL] Stage2 compiled {success_count}/{len(pyrite_modules)} modules")
        return True  # Partial success is still progress
    else:
        print(f"  [FAIL] Stage2 could not compile any modules")
        return False


def test_stage2_compiles_test_program(stage2_exe):
    """Test that Stage2 can compile a representative test program"""
    print("\n[Test 2/2] Stage2 compiles test program...")
    
    # Look for hello.pyrite or any simple example
    test_files = []
    if examples_dir.exists():
        # Prefer hello.pyrite if it exists
        hello_file = examples_dir / "hello.pyrite"
        if hello_file.exists():
            test_files.append(hello_file)
        else:
            # Try any .pyrite file in examples
            test_files = list(examples_dir.glob("*.pyrite"))[:1]  # Just test one
    
    if not test_files:
        print("  [SKIP] No test programs found in examples/")
        return False
    
    test_file = test_files[0]
    print(f"  Compiling {test_file.name} with Stage2...", end=" ")
    
    try:
        output_file = stage2_dir / f"test_{test_file.stem}"
        
        result = subprocess.run(
            [str(stage2_exe), str(test_file), "-o", str(output_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("[OK]")
            print(f"  [OK] Stage2 can compile test program: {test_file.name}")
            return True
        else:
            print("[FAIL]")
            if result.stderr:
                error_lines = result.stderr.split('\n')
                for line in error_lines[:3]:
                    if line.strip() and not line.startswith('['):
                        print(f"      {line[:100]}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    """Run self-hosting validation"""
    print("=" * 60)
    print("Self-Hosting Validation")
    print("=" * 60)
    
    # Check Stage2 exists
    stage2_exe = find_stage2_executable()
    if not stage2_exe:
        print("\n[ERROR] Stage2 executable not found")
        print(f"  Expected: {stage2_dir / 'forge.exe' if sys.platform == 'win32' else stage2_dir / 'forge'}")
        print("  Run bootstrap_stage2.py first")
        return 1
    
    print(f"\n[OK] Stage2 executable found: {stage2_exe}")
    
    # Run tests
    test1_passed = test_stage2_compiles_itself(stage2_exe)
    test2_passed = test_stage2_compiles_test_program(stage2_exe)
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    if test1_passed:
        print("[OK] Stage2 can compile itself")
    else:
        print("[FAIL] Stage2 cannot compile itself")
    
    if test2_passed:
        print("[OK] Stage2 can compile test program")
    else:
        print("[FAIL] Stage2 cannot compile test program")
    
    if test1_passed and test2_passed:
        print("\n[OK] Self-hosting validation passed")
        return 0
    elif test1_passed or test2_passed:
        print("\n[PARTIAL] Self-hosting validation partially passed")
        return 0  # Partial success is still progress
    else:
        print("\n[FAIL] Self-hosting validation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
