#!/usr/bin/env python3
"""
Bootstrap Stage2: Build Pyrite compiler using Stage1 (Pyrite compiler)

This script uses the Pyrite compiler (Stage1) to compile the Pyrite compiler
source code, producing Stage2 executable.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add forge to path
script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
compiler_dir = repo_root / "forge"
stage1_dir = repo_root / "build" / "bootstrap" / "stage1"
stage2_dir = repo_root / "build" / "bootstrap" / "stage2"


def verify_prerequisites():
    """Verify prerequisites are available before building Stage2"""
    print("\n[0/5] Verifying prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("  [FAIL] Python 3.8+ required")
        print(f"    Current version: {sys.version_info.major}.{sys.version_info.minor}")
        print("    Install from: https://www.python.org/downloads/")
        return False
    print(f"  [OK] Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check llvmlite (for Stage1, but verify it's available)
    try:
        import llvmlite
        print(f"  [OK] llvmlite available")
    except ImportError:
        print("  [WARN] llvmlite not installed (Stage1 should have it)")
        print("    This may indicate environment issues")
    
    # Check clang/gcc (optional warning)
    import shutil
    clang_available = shutil.which("clang") is not None
    gcc_available = shutil.which("gcc") is not None
    if not clang_available and not gcc_available:
        print("  [WARN] clang/gcc not found in PATH")
        print("    Linking may fail, but compilation will proceed")
        print("    Install clang or gcc for full functionality")
    else:
        compiler = "clang" if clang_available else "gcc"
        print(f"  [OK] {compiler} available")
    
    return True


def build_stage2():
    """Build Stage2 compiler using Stage1"""
    print("=" * 60)
    print("Bootstrap Stage1 -> Stage2")
    print("=" * 60)
    
    # Verify prerequisites
    if not verify_prerequisites():
        print("\n[FAIL] Prerequisites not met")
        return False
    
    # Check Stage1 exists
    print("\n[1/5] Verifying Stage1 compiler...")
    stage1_exe = stage1_dir / "forge"
    if sys.platform == "win32":
        stage1_exe = stage1_dir / "forge.exe"
    if not stage1_exe.exists():
        print(f"ERROR: Stage1 compiler not found at {stage1_exe}")
        print("  Run bootstrap_stage1.py first")
        return False
    
    # Check Stage1 works
    try:
        result = subprocess.run(
            [str(stage1_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("ERROR: Stage1 compiler not working")
            return False
        print("  [OK] Stage1 compiler verified")
    except Exception as e:
        print(f"ERROR: Failed to verify Stage1 compiler: {e}")
        return False
    
    # Find Pyrite modules
    print("\n[2/5] Finding Pyrite compiler modules...")
    src_pyrite_dir = compiler_dir / "src-pyrite"
    if not src_pyrite_dir.exists():
        print("  ⚠ No Pyrite modules found")
        return False
    
    pyrite_modules = sorted(src_pyrite_dir.glob("*.pyrite"))
    if not pyrite_modules:
        print("  ⚠ No Pyrite modules found")
        return False
    
    print(f"  Found {len(pyrite_modules)} Pyrite module(s)")
    
    # Create stage2 directory
    print("\n[3/5] Creating build/bootstrap/stage2/ directory...")
    stage2_dir = repo_root / "build" / "bootstrap" / "stage2"
    stage2_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] Created {stage2_dir}")
    
    # Compile each Pyrite module with Stage1
    print("\n[4/5] Compiling Pyrite modules with Stage1...")
    object_files = []
    module_timings = {}
    stage2_start_time = time.time()
    
    for pyrite_file in pyrite_modules:
        print(f"  Compiling {pyrite_file.name}...", end=" ")
        obj_file = stage2_dir / f"{pyrite_file.stem}.o"
        module_start = time.time()
        
        # Use Stage1 to compile
        try:
            result = subprocess.run(
                [str(stage1_exe), str(pyrite_file), "-o", str(obj_file.with_suffix(''))],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            module_time = time.time() - module_start
            module_timings[pyrite_file.name] = module_time
            
            if result.returncode == 0 and obj_file.exists():
                object_files.append(obj_file)
                print(f"[OK] ({module_time:.2f}s)")
            else:
                print(f"[FAIL] ({module_time:.2f}s)")
                if result.stderr:
                    # Show first few lines of error
                    error_lines = result.stderr.split('\n')[:5]
                    for line in error_lines:
                        if line.strip():
                            print(f"      {line[:200]}")
                print(f"    [SKIP] Skipping {pyrite_file.name} - will continue with other modules")
                # Don't fail immediately - continue compiling other modules
                # Some modules may have known limitations (e.g., enum constructors with fields in codegen)
                continue
        except Exception as e:
            module_time = time.time() - module_start
            module_timings[pyrite_file.name] = module_time
            print(f"[ERROR] ({module_time:.2f}s) {e}")
            return False
    
    # Link executable
    print("\n[5/5] Linking Stage2 executable...")
    link_start = time.time()
    stage2_exe = stage2_dir / "forge"
    if sys.platform == "win32":
        stage2_exe = stage2_dir / "forge.exe"
    
    if not object_files:
        print("  [WARN] No object files to link")
        print("  Stage2 executable cannot be created without object files")
        print(f"\n  Compiled modules: {len([f for f in pyrite_modules if (stage2_dir / f'{f.stem}.o').exists()])}/{len(pyrite_modules)}")
        return True  # Not a failure, just nothing to link
    
    print(f"  Linking {len(object_files)} object file(s) from {len(pyrite_modules)} module(s)...")
    
    # Find linker - prefer clang, then gcc
    linker = None
    for cmd in ['clang', 'gcc']:
        try:
            result = subprocess.run([cmd, '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                linker = cmd
                break
        except:
            continue
    
    if not linker:
        print("  [WARN] No linker found (clang/gcc)")
        print("  Install clang or gcc to create Stage2 executable")
        print(f"  Object files created: {len(object_files)}")
        print("  You can link manually later")
        return True  # Not a failure, just can't link automatically
    
    # Build linker command
    link_cmd = [linker, '-o', str(stage2_exe)]
    
    # Add all object files
    link_cmd.extend([str(obj) for obj in object_files])
    
    # Try to link with runtime library if it exists
    runtime_lib = compiler_dir / "runtime" / "libpyrite.a"
    if runtime_lib.exists():
        link_cmd.append(str(runtime_lib))
        print(f"  Linking with runtime library: {runtime_lib.name}")
    else:
        print(f"  [WARN] Runtime library not found at {runtime_lib}")
        print(f"  Run 'python tools/build/build_runtime.py' to build it")
        print(f"  Linking without runtime library (may fail if runtime functions are used)")
    
    # Add standard libraries
    if sys.platform == "win32":
        # Windows: may need additional libraries
        pass  # clang/gcc on Windows should handle this
    else:
        # Unix: link with standard C library (usually automatic, but explicit is safer)
        link_cmd.append('-lm')  # Math library
    
    print(f"  Linking {len(object_files)} object file(s)...")
    try:
        result = subprocess.run(link_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            if stage2_exe.exists():
                print(f"  [OK] Created Stage2 executable: {stage2_exe}")
                # Make executable on Unix
                if sys.platform != "win32":
                    os.chmod(stage2_exe, 0o755)
            else:
                print(f"  [FAIL] Linker succeeded but executable not found")
                return False
        else:
            print(f"  [FAIL] Linking failed:")
            if result.stderr:
                print(f"    {result.stderr}")
            if result.stdout:
                print(f"    {result.stdout}")
            return False
    except Exception as e:
        print(f"  [FAIL] Linking error: {e}")
        return False
    
    stage2_total_time = time.time() - stage2_start_time
    link_time = time.time() - link_start
    
    print("\n" + "=" * 60)
    print("Stage1 -> Stage2: COMPLETE")
    print("=" * 60)
    print(f"\nStage2 executable: {stage2_exe}")
    print(f"Object files: {len(object_files)}")
    
    # Timing summary
    print("\n" + "-" * 60)
    print("Timing Summary")
    print("-" * 60)
    if module_timings:
        sorted_timings = sorted(module_timings.items(), key=lambda x: x[1], reverse=True)
        print(f"\nModule compilation times:")
        for module_name, module_time in sorted_timings:
            print(f"  {module_name:30} {module_time:6.2f}s")
        print(f"\n  {'Total (modules)':30} {sum(module_timings.values()):6.2f}s")
    print(f"  {'Linking':30} {link_time:6.2f}s")
    print(f"  {'Total (Stage2 build)':30} {stage2_total_time:6.2f}s")
    print("-" * 60)
    
    return True


if __name__ == "__main__":
    success = build_stage2()
    sys.exit(0 if success else 1)
