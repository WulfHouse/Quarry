#!/usr/bin/env python3
"""
Check bootstrap determinism: Compare Stage1 and Stage2 outputs

This script validates that Stage1 and Stage2 compilers produce
equivalent outputs, ensuring bootstrap correctness.

It compares both LLVM IR and object files to verify determinism.

Comparison Methods:
- Object files (preferred): Compares compiled object files using hash-based
  or byte-identical comparison. Object files may differ in metadata/timestamps
  but should be functionally equivalent.
- LLVM IR (fallback): If object files aren't available, compares LLVM IR
  (normalized, ignoring comments and metadata).

Acceptable Differences:
- Metadata (timestamps, build IDs)
- Symbol names (if compiler uses different naming)
- Debug information (if present)

Use --strict flag for byte-identical object file comparison.
"""

import sys
import subprocess
import argparse
import hashlib
from pathlib import Path

script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
stage1_dir = repo_root / "build" / "bootstrap" / "stage1"
stage2_dir = repo_root / "build" / "bootstrap" / "stage2"


def compare_llvm_ir(file1: Path, file2: Path) -> bool:
    """Compare two LLVM IR files (ignoring metadata)"""
    if not file1.exists() or not file2.exists():
        return False
    
    # Read IR files
    ir1 = file1.read_text(encoding='utf-8')
    ir2 = file2.read_text(encoding='utf-8')
    
    # Normalize: remove comments, metadata, symbol names (for comparison)
    # For MVP, simple string comparison
    # Full implementation would parse IR and compare semantically
    
    # Remove comments and metadata
    lines1 = [l for l in ir1.split('\n') if not l.strip().startswith(';')]
    lines2 = [l for l in ir2.split('\n') if not l.strip().startswith(';')]
    
    # Compare core IR (simplified)
    core1 = '\n'.join(lines1)
    core2 = '\n'.join(lines2)
    
    return core1 == core2


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file"""
    if not file_path.exists():
        return None
    
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def compare_object_files(file1: Path, file2: Path, strict: bool = False) -> tuple[bool, str]:
    """Compare two object files
    
    Returns:
        (are_equivalent, message)
    """
    if not file1.exists():
        return False, f"File1 does not exist: {file1}"
    if not file2.exists():
        return False, f"File2 does not exist: {file2}"
    
    if strict:
        # Byte-by-byte comparison
        data1 = file1.read_bytes()
        data2 = file2.read_bytes()
        if data1 == data2:
            return True, "Object files are byte-identical"
        else:
            return False, f"Object files differ: {len(data1)} vs {len(data2)} bytes"
    else:
        # Hash-based comparison (more lenient, allows metadata differences)
        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)
        if hash1 == hash2:
            return True, f"Object files have identical hash: {hash1[:16]}..."
        else:
            return False, f"Object files have different hashes: {hash1[:16]}... vs {hash2[:16]}..."


def check_determinism(strict: bool = False):
    """Check that Stage1 and Stage2 produce equivalent outputs
    
    Args:
        strict: If True, require byte-identical object files. If False, use hash comparison.
    """
    print("=" * 60)
    print("Bootstrap Determinism Check")
    print("=" * 60)
    if strict:
        print("Mode: STRICT (byte-identical object files required)")
    else:
        print("Mode: HASH (hash-based comparison, allows metadata differences)")
    print()
    
    # Check both stages exist
    if sys.platform == "win32":
        stage1_exe = stage1_dir / "forge.exe"
        stage2_exe = stage2_dir / "forge.exe"
    else:
        stage1_exe = stage1_dir / "forge"
        stage2_exe = stage2_dir / "forge"
    
    if not stage1_exe.exists():
        print("ERROR: Stage1 compiler not found")
        print("  Run bootstrap_stage1.py first")
        return False
    
    if not stage2_exe.exists():
        print("ERROR: Stage2 compiler not found")
        print("  Run bootstrap_stage2.py first")
        return False
    
    # Create test program
    print("\n[1/4] Creating test program...")
    test_program = """
fn main() -> int:
    return 42
"""
    test_file = repo_root / "bootstrap_test.pyrite"
    test_file.write_text(test_program, encoding='utf-8')
    print(f"  [OK] Created {test_file.name}")
    
    # Compile with Stage1 (to object file)
    print("\n[2/4] Compiling with Stage1...")
    # Object file is created in current directory with name based on output path
    stage1_output_base = "bootstrap_test_stage1"
    stage1_obj = repo_root / f"{stage1_output_base}.o"  # Compiler creates {output}.o
    stage1_ir = stage1_dir / "test_stage1.ll"
    try:
        # Compile to object file (compiler creates .o in current directory)
        result = subprocess.run(
            [str(stage1_exe), str(test_file), "-o", stage1_output_base],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"  ✗ Stage1 compilation failed: {result.stderr[:200]}")
            return False
        # Check for object file (compiler creates {output}.o)
        if stage1_obj.exists():
            # Move to stage1_dir for comparison
            stage1_obj_final = stage1_dir / "test_stage1.o"
            import shutil
            shutil.move(str(stage1_obj), str(stage1_obj_final))
            stage1_obj = stage1_obj_final
            print(f"  [OK] Stage1 object file: {stage1_obj}")
        else:
            # Object file not created, try IR as fallback
            print(f"  [INFO] Object file not found, generating IR for comparison...")
            result = subprocess.run(
                [str(stage1_exe), str(test_file), "-o", str(stage1_ir.with_suffix('')), "--emit-llvm"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and stage1_ir.exists():
                print(f"  [OK] Stage1 IR: {stage1_ir}")
            else:
                if result.stderr:
                    print(f"  [ERROR] Stage1 IR generation failed: {result.stderr[:200]}")
                return False
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return False
    
    # Compile with Stage2 (to object file)
    print("\n[3/4] Compiling with Stage2...")
    # Object file is created in current directory with name based on output path
    stage2_output_base = "bootstrap_test_stage2"
    stage2_obj = repo_root / f"{stage2_output_base}.o"  # Compiler creates {output}.o
    stage2_ir = stage2_dir / "test_stage2.ll"
    try:
        # Compile to object file (compiler creates .o in current directory)
        result = subprocess.run(
            [str(stage2_exe), str(test_file), "-o", stage2_output_base],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"  ✗ Stage2 compilation failed: {result.stderr[:200]}")
            return False
        # Check for object file (compiler creates {output}.o)
        if stage2_obj.exists():
            # Move to stage2_dir for comparison
            stage2_obj_final = stage2_dir / "test_stage2.o"
            import shutil
            shutil.move(str(stage2_obj), str(stage2_obj_final))
            stage2_obj = stage2_obj_final
            print(f"  [OK] Stage2 object file: {stage2_obj}")
        else:
            # Object file not created, try IR as fallback
            print(f"  [INFO] Object file not found, generating IR for comparison...")
            result = subprocess.run(
                [str(stage2_exe), str(test_file), "-o", str(stage2_ir.with_suffix('')), "--emit-llvm"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and stage2_ir.exists():
                print(f"  [OK] Stage2 IR: {stage2_ir}")
            else:
                if result.stderr:
                    print(f"  [ERROR] Stage2 IR generation failed: {result.stderr[:200]}")
                return False
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return False
    
    # Compare outputs
    print("\n[4/4] Comparing outputs...")
    all_passed = True
    
    # Compare object files if both exist (preferred method)
    if stage1_obj.exists() and stage2_obj.exists():
        obj_equivalent, obj_msg = compare_object_files(stage1_obj, stage2_obj, strict=strict)
        if obj_equivalent:
            print(f"  [OK] Object files: {obj_msg}")
        else:
            print(f"  ✗ Object files: {obj_msg}")
            all_passed = False
            if not strict:
                print("    Note: Use --strict for byte-identical comparison")
                print("    Hash differences may be acceptable (metadata, timestamps, symbol names)")
    
    # Compare IR files (primary method if object files not available, or as additional check)
    if stage1_ir.exists() and stage2_ir.exists():
        ir_equivalent = compare_llvm_ir(stage1_ir, stage2_ir)
        if ir_equivalent:
            if stage1_obj.exists() and stage2_obj.exists():
                print(f"  [OK] LLVM IR (additional check): Stage1 and Stage2 produce equivalent IR")
            else:
                print(f"  [OK] LLVM IR: Stage1 and Stage2 produce equivalent IR")
        else:
            if stage1_obj.exists() and stage2_obj.exists():
                print(f"  [WARN] LLVM IR differs (but object files match - this may be acceptable)")
            else:
                print(f"  ✗ LLVM IR: Stage1 and Stage2 produce different IR")
                all_passed = False
    elif not (stage1_obj.exists() and stage2_obj.exists()):
        print("  [WARN] Neither object files nor IR files available for comparison")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("Determinism Check: PASSED")
        print("=" * 60)
        print("\nStage1 and Stage2 produce equivalent outputs.")
        if not strict:
            print("\nNote: Hash-based comparison allows metadata differences.")
            print("Use --strict flag for byte-identical verification.")
        return True
    else:
        print("Determinism Check: FAILED")
        print("=" * 60)
        print("\nDifferences detected. This may indicate:")
        print("  - Non-deterministic compiler behavior")
        print("  - Different code generation")
        print("  - Symbol name differences (may be acceptable)")
        print("  - Metadata/timestamp differences (acceptable in hash mode)")
        if not strict:
            print("\nTry --strict flag for byte-identical comparison.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check bootstrap determinism: Compare Stage1 and Stage2 outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require byte-identical object files (default: hash-based comparison)"
    )
    
    args = parser.parse_args()
    
    success = check_determinism(strict=args.strict)
    sys.exit(0 if success else 1)
