#!/usr/bin/env python3
"""
Clean Checkout Verification: Verify self-hosting works from scratch

This script verifies that the Pyrite compiler can bootstrap itself from a clean
checkout by:
1. Optionally cleaning build/bootstrap/ directory
2. Building Stage1 from Python compiler
3. Building Stage2 from Stage1
4. Validating Stage2 can compile itself
5. Verifying all artifacts exist

Prerequisites:
- Python 3.8+ with llvmlite installed
- clang or gcc available in PATH
- LLVM toolchain (for object file generation)

Usage:
    python scripts/bootstrap/verify_clean_checkout.py
    python scripts/bootstrap/verify_clean_checkout.py --clean
    python scripts/bootstrap/verify_clean_checkout.py --skip-stage1
    python scripts/bootstrap/verify_clean_checkout.py --skip-stage2
"""

import sys
import os
import subprocess
import argparse
import shutil
from pathlib import Path

# Add forge to path
script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
compiler_dir = repo_root / "forge"
build_dir = repo_root / "build" / "bootstrap"
stage1_dir = build_dir / "stage1"
stage2_dir = build_dir / "stage2"


def verify_prerequisites():
    """Verify prerequisites are available"""
    print("\n[0/5] Verifying prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("  [FAIL] Python 3.8+ required")
        return False
    print(f"  [OK] Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check llvmlite
    try:
        import llvmlite
        print(f"  [OK] llvmlite available")
    except ImportError:
        print("  [FAIL] llvmlite not installed")
        print("    Install with: pip install llvmlite")
        return False
    
    # Check clang/gcc (optional warning)
    clang_available = shutil.which("clang") is not None
    gcc_available = shutil.which("gcc") is not None
    if not clang_available and not gcc_available:
        print("  [WARN] clang/gcc not found in PATH")
        print("    Linking may fail, but compilation will proceed")
    else:
        compiler = "clang" if clang_available else "gcc"
        print(f"  [OK] {compiler} available")
    
    return True


def clean_build_directory():
    """Clean build/bootstrap/ directory"""
    print("\n[0.5/5] Cleaning build/bootstrap/ directory...")
    if build_dir.exists():
        try:
            shutil.rmtree(build_dir)
            print(f"  [OK] Removed {build_dir}")
        except Exception as e:
            print(f"  [FAIL] Failed to remove {build_dir}: {e}")
            return False
    else:
        print(f"  [OK] {build_dir} does not exist (already clean)")
    return True


def run_bootstrap_stage1():
    """Run bootstrap_stage1.py"""
    print("\n[1/5] Building Stage1...")
    stage1_script = script_dir / "bootstrap_stage1.py"
    
    if not stage1_script.exists():
        print(f"  [FAIL] {stage1_script} not found")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(stage1_script)],
            cwd=str(repo_root),
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  [FAIL] Stage1 build failed (exit code {result.returncode})")
            return False
        
        print("  [OK] Stage1 build completed")
        return True
    except Exception as e:
        print(f"  [FAIL] Error running Stage1 build: {e}")
        return False


def run_bootstrap_stage2():
    """Run bootstrap_stage2.py"""
    print("\n[2/5] Building Stage2...")
    stage2_script = script_dir / "bootstrap_stage2.py"
    
    if not stage2_script.exists():
        print(f"  [FAIL] {stage2_script} not found")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(stage2_script)],
            cwd=str(repo_root),
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  [FAIL] Stage2 build failed (exit code {result.returncode})")
            return False
        
        print("  [OK] Stage2 build completed")
        return True
    except Exception as e:
        print(f"  [FAIL] Error running Stage2 build: {e}")
        return False


def run_validation():
    """Run validate_self_hosting.py"""
    print("\n[3/5] Validating self-hosting...")
    validation_script = script_dir / "validate_self_hosting.py"
    
    if not validation_script.exists():
        print(f"  [FAIL] {validation_script} not found")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(validation_script)],
            cwd=str(repo_root),
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  [FAIL] Self-hosting validation failed (exit code {result.returncode})")
            return False
        
        print("  [OK] Self-hosting validation passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Error running validation: {e}")
        return False


def verify_artifacts():
    """Verify required artifacts exist"""
    print("\n[4/5] Verifying artifacts...")
    
    # Check Stage1 executable
    stage1_exe = stage1_dir / "pyritec"
    if sys.platform == "win32":
        stage1_exe = stage1_dir / "pyritec.exe"
    
    if not stage1_exe.exists():
        print(f"  [FAIL] Stage1 executable not found: {stage1_exe}")
        return False
    print(f"  [OK] Stage1 executable: {stage1_exe}")
    
    # Check Stage2 executable
    stage2_exe = stage2_dir / "pyritec"
    if sys.platform == "win32":
        stage2_exe = stage2_dir / "pyritec.exe"
    
    if not stage2_exe.exists():
        print(f"  [FAIL] Stage2 executable not found: {stage2_exe}")
        return False
    print(f"  [OK] Stage2 executable: {stage2_exe}")
    
    # Check object files exist
    stage1_objects = list(stage1_dir.glob("*.o"))
    stage2_objects = list(stage2_dir.glob("*.o"))
    
    if not stage1_objects:
        print(f"  [WARN] No Stage1 object files found in {stage1_dir}")
    else:
        print(f"  [OK] Stage1 object files: {len(stage1_objects)}")
    
    if not stage2_objects:
        print(f"  [WARN] No Stage2 object files found in {stage2_dir}")
    else:
        print(f"  [OK] Stage2 object files: {len(stage2_objects)}")
    
    return True


def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(
        description="Verify self-hosting works from clean checkout",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build/bootstrap/ directory before starting"
    )
    parser.add_argument(
        "--skip-stage1",
        action="store_true",
        help="Skip Stage1 build (assume it exists)"
    )
    parser.add_argument(
        "--skip-stage2",
        action="store_true",
        help="Skip Stage2 build (assume it exists)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Clean Checkout Verification")
    print("=" * 60)
    
    # Verify prerequisites
    if not verify_prerequisites():
        print("\n[FAIL] Prerequisites not met")
        return 1
    
    # Clean if requested
    if args.clean:
        if not clean_build_directory():
            print("\n[FAIL] Failed to clean build directory")
            return 1
    
    # Build Stage1 (unless skipped)
    if not args.skip_stage1:
        if not run_bootstrap_stage1():
            print("\n[FAIL] Stage1 build failed")
            return 1
    else:
        print("\n[SKIP] Skipping Stage1 build")
    
    # Build Stage2 (unless skipped)
    if not args.skip_stage2:
        if not run_bootstrap_stage2():
            print("\n[FAIL] Stage2 build failed")
            return 1
    else:
        print("\n[SKIP] Skipping Stage2 build")
    
    # Run validation
    if not run_validation():
        print("\n[FAIL] Self-hosting validation failed")
        return 1
    
    # Verify artifacts
    if not verify_artifacts():
        print("\n[FAIL] Artifact verification failed")
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print("[OK] Clean checkout verification passed")
    print(f"  Stage1 executable: {stage1_dir / ('pyritec.exe' if sys.platform == 'win32' else 'pyritec')}")
    print(f"  Stage2 executable: {stage2_dir / ('pyritec.exe' if sys.platform == 'win32' else 'pyritec')}")
    print("\n[OK] Self-hosting is repeatable from clean checkout")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
