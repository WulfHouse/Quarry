#!/usr/bin/env python3
"""
Bootstrap Stage1: Build Pyrite compiler using Stage0 (Python compiler)

This script uses the Python compiler (Stage0) to compile the Pyrite compiler
source code, producing Stage1 executable.
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
sys.path.insert(0, str(compiler_dir))

from src.compiler import compile_source
import shutil


def verify_prerequisites():
    """Verify prerequisites are available before building Stage1"""
    print("\n[0/5] Verifying prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("  [FAIL] Python 3.8+ required")
        print(f"    Current version: {sys.version_info.major}.{sys.version_info.minor}")
        print("    Install from: https://www.python.org/downloads/")
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
        print("    Install clang or gcc for full functionality")
    else:
        compiler = "clang" if clang_available else "gcc"
        print(f"  [OK] {compiler} available")
    
    return True


def find_pyrite_modules():
    """Find all Pyrite source files in src-pyrite/"""
    src_pyrite_dir = compiler_dir / "src-pyrite"
    if not src_pyrite_dir.exists():
        print("Warning: src-pyrite/ directory does not exist yet")
        print("  This is expected - Pyrite compiler modules will be created during migration")
        return []
    
    pyrite_files = list(src_pyrite_dir.glob("*.pyrite"))
    return sorted(pyrite_files)


def build_stage1():
    """Build Stage1 compiler from Pyrite source"""
    print("=" * 60)
    print("Bootstrap Stage0 -> Stage1")
    print("=" * 60)
    
    # Verify prerequisites
    if not verify_prerequisites():
        print("\n[FAIL] Prerequisites not met")
        return False
    
    # Check Stage0 compiler
    print("\n[1/5] Verifying Stage0 compiler...")
    try:
        # Try to import compiler module as verification
        from src.compiler import compile_source
        print("  [OK] Stage0 compiler verified (can import)")
    except Exception as e:
        print(f"ERROR: Failed to verify Stage0 compiler: {e}")
        return False
    
    # Find Pyrite modules
    print("\n[2/5] Finding Pyrite compiler modules...")
    pyrite_modules = find_pyrite_modules()
    if not pyrite_modules:
        print("  [WARN] No Pyrite modules found in src-pyrite/")
        print("  This is expected during early migration phases")
        print("  Stage1 build will be available once Pyrite modules are created")
        return True  # Not an error, just early in migration
    
    print(f"  Found {len(pyrite_modules)} Pyrite module(s):")
    for mod in pyrite_modules:
        print(f"    - {mod.name}")
    
    # Create stage1 directory
    print("\n[3/5] Creating build/bootstrap/stage1/ directory...")
    stage1_dir = repo_root / "build" / "bootstrap" / "stage1"
    stage1_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] Created {stage1_dir}")
    
    # Compile each Pyrite module
    print("\n[4/5] Compiling Pyrite modules with Stage0...")
    object_files = []
    module_timings = {}
    stage1_start_time = time.time()
    
    for pyrite_file in pyrite_modules:
        print(f"  Compiling {pyrite_file.name}...", end=" ")
        obj_file = stage1_dir / f"{pyrite_file.stem}.o"
        module_start = time.time()
        
        # Use Stage0 to compile
        success = compile_source(
            source=pyrite_file.read_text(encoding='utf-8'),
            filename=str(pyrite_file),
            output_path=str(obj_file.with_suffix('')),
            emit_llvm=False,
            deterministic=True
        )
        
        module_time = time.time() - module_start
        module_timings[pyrite_file.name] = module_time
        
        if success and obj_file.exists():
            object_files.append(obj_file)
            print(f"[OK] ({module_time:.2f}s)")
        else:
            print(f"[FAIL] ({module_time:.2f}s)")
            print(f"    [SKIP] Skipping {pyrite_file.name} - will continue with other modules")
            # Don't fail immediately - continue compiling other modules
            # Some modules may have known limitations (e.g., generic types)
            continue
    
    # Link executable
    print("\n[5/5] Linking Stage1 executable...")
    link_start = time.time()
    stage1_exe = stage1_dir / "pyritec"
    if sys.platform == "win32":
        stage1_exe = stage1_dir / "pyritec.exe"
    
    if not object_files:
        print("  [WARN] No object files to link")
        print("  Stage1 executable cannot be created without object files")
        print(f"\n  Compiled modules: {len([f for f in pyrite_modules if (stage1_dir / f'{f.stem}.o').exists()])}/{len(pyrite_modules)}")
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
        print("  Install clang or gcc to create Stage1 executable")
        print(f"  Object files created: {len(object_files)}")
        print("  You can link manually later")
        return True  # Not a failure, just can't link automatically
    
    # Build linker command
    link_cmd = [linker, '-o', str(stage1_exe)]
    
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
            if stage1_exe.exists():
                print(f"  [OK] Created Stage1 executable: {stage1_exe}")
                # Make executable on Unix
                if sys.platform != "win32":
                    os.chmod(stage1_exe, 0o755)
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
    
    stage1_total_time = time.time() - stage1_start_time
    link_time = time.time() - link_start
    
    print("\n" + "=" * 60)
    print("Stage0 -> Stage1: COMPLETE")
    print("=" * 60)
    print(f"\nStage1 executable: {stage1_exe}")
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
    print(f"  {'Total (Stage1 build)':30} {stage1_total_time:6.2f}s")
    print("-" * 60)
    
    return True


if __name__ == "__main__":
    success = build_stage1()
    sys.exit(0 if success else 1)
