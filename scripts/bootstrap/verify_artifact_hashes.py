#!/usr/bin/env python3
"""
Artifact Hash Verification: Verify bootstrap artifacts are stable

This script computes SHA256 hashes of Stage1 and Stage2 executables and
object files, enabling verification that artifacts are stable across rebuilds.

Usage:
    python scripts/bootstrap/verify_artifact_hashes.py --update  # Store hashes
    python scripts/bootstrap/verify_artifact_hashes.py --verify  # Verify against stored hashes
"""

import sys
import argparse
import hashlib
import json
from pathlib import Path

script_dir = Path(__file__).parent
repo_root = script_dir.parent.parent
build_dir = repo_root / "build" / "bootstrap"
stage1_dir = build_dir / "stage1"
stage2_dir = build_dir / "stage2"
hashes_file = build_dir / "artifact_hashes.json"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file"""
    if not file_path.exists():
        return None
    
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def collect_artifact_hashes() -> dict:
    """Collect hashes of all bootstrap artifacts"""
    hashes = {
        "stage1": {},
        "stage2": {}
    }
    
    # Stage1 executable
    stage1_exe = stage1_dir / "pyritec.exe" if sys.platform == "win32" else stage1_dir / "pyritec"
    if stage1_exe.exists():
        hashes["stage1"]["executable"] = compute_file_hash(stage1_exe)
    
    # Stage1 object files
    stage1_objects = sorted(stage1_dir.glob("*.o"))
    hashes["stage1"]["object_files"] = {}
    for obj_file in stage1_objects:
        hashes["stage1"]["object_files"][obj_file.name] = compute_file_hash(obj_file)
    
    # Stage2 executable
    stage2_exe = stage2_dir / "pyritec.exe" if sys.platform == "win32" else stage2_dir / "pyritec"
    if stage2_exe.exists():
        hashes["stage2"]["executable"] = compute_file_hash(stage2_exe)
    
    # Stage2 object files
    stage2_objects = sorted(stage2_dir.glob("*.o"))
    hashes["stage2"]["object_files"] = {}
    for obj_file in stage2_objects:
        hashes["stage2"]["object_files"][obj_file.name] = compute_file_hash(obj_file)
    
    return hashes


def update_hashes():
    """Update stored artifact hashes"""
    print("=" * 60)
    print("Updating Artifact Hashes")
    print("=" * 60)
    
    hashes = collect_artifact_hashes()
    
    # Ensure build directory exists
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Save hashes
    with open(hashes_file, 'w') as f:
        json.dump(hashes, f, indent=2)
    
    print(f"\n[OK] Hashes saved to {hashes_file}")
    print(f"\nStage1 executable: {hashes['stage1'].get('executable', 'not found')[:16]}...")
    print(f"Stage1 object files: {len(hashes['stage1'].get('object_files', {}))}")
    print(f"Stage2 executable: {hashes['stage2'].get('executable', 'not found')[:16]}...")
    print(f"Stage2 object files: {len(hashes['stage2'].get('object_files', {}))}")
    
    return True


def verify_hashes():
    """Verify current artifacts against stored hashes"""
    print("=" * 60)
    print("Verifying Artifact Hashes")
    print("=" * 60)
    
    if not hashes_file.exists():
        print(f"\n[FAIL] Hash file not found: {hashes_file}")
        print("  Run with --update first to store hashes")
        return False
    
    # Load stored hashes
    with open(hashes_file, 'r') as f:
        stored_hashes = json.load(f)
    
    # Collect current hashes
    current_hashes = collect_artifact_hashes()
    
    all_match = True
    
    # Verify Stage1 executable
    print("\n[1/4] Verifying Stage1 executable...")
    stored_exe_hash = stored_hashes.get("stage1", {}).get("executable")
    current_exe_hash = current_hashes.get("stage1", {}).get("executable")
    if stored_exe_hash and current_exe_hash:
        if stored_exe_hash == current_exe_hash:
            print(f"  [OK] Stage1 executable hash matches: {current_exe_hash[:16]}...")
        else:
            print(f"  [FAIL] Stage1 executable hash differs")
            print(f"    Stored:  {stored_exe_hash[:16]}...")
            print(f"    Current: {current_exe_hash[:16]}...")
            all_match = False
    elif not stored_exe_hash:
        print("  [WARN] No stored hash for Stage1 executable")
    elif not current_exe_hash:
        print("  [FAIL] Stage1 executable not found")
        all_match = False
    
    # Verify Stage1 object files
    print("\n[2/4] Verifying Stage1 object files...")
    stored_objs = stored_hashes.get("stage1", {}).get("object_files", {})
    current_objs = current_hashes.get("stage1", {}).get("object_files", {})
    if stored_objs and current_objs:
        all_objs_match = True
        for obj_name in set(list(stored_objs.keys()) + list(current_objs.keys())):
            stored_hash = stored_objs.get(obj_name)
            current_hash = current_objs.get(obj_name)
            if stored_hash and current_hash:
                if stored_hash == current_hash:
                    print(f"  [OK] {obj_name}: hash matches")
                else:
                    print(f"  [FAIL] {obj_name}: hash differs")
                    all_objs_match = False
                    all_match = False
            elif stored_hash and not current_hash:
                print(f"  [FAIL] {obj_name}: file missing")
                all_match = False
            elif not stored_hash and current_hash:
                print(f"  [WARN] {obj_name}: new file (not in stored hashes)")
        if all_objs_match:
            print(f"  [OK] All {len(stored_objs)} Stage1 object files match")
    else:
        print("  [WARN] No object files to verify")
    
    # Verify Stage2 executable
    print("\n[3/4] Verifying Stage2 executable...")
    stored_exe_hash = stored_hashes.get("stage2", {}).get("executable")
    current_exe_hash = current_hashes.get("stage2", {}).get("executable")
    if stored_exe_hash and current_exe_hash:
        if stored_exe_hash == current_exe_hash:
            print(f"  [OK] Stage2 executable hash matches: {current_exe_hash[:16]}...")
        else:
            print(f"  [FAIL] Stage2 executable hash differs")
            print(f"    Stored:  {stored_exe_hash[:16]}...")
            print(f"    Current: {current_exe_hash[:16]}...")
            all_match = False
    elif not stored_exe_hash:
        print("  [WARN] No stored hash for Stage2 executable")
    elif not current_exe_hash:
        print("  [FAIL] Stage2 executable not found")
        all_match = False
    
    # Verify Stage2 object files
    print("\n[4/4] Verifying Stage2 object files...")
    stored_objs = stored_hashes.get("stage2", {}).get("object_files", {})
    current_objs = current_hashes.get("stage2", {}).get("object_files", {})
    if stored_objs and current_objs:
        all_objs_match = True
        for obj_name in set(list(stored_objs.keys()) + list(current_objs.keys())):
            stored_hash = stored_objs.get(obj_name)
            current_hash = current_objs.get(obj_name)
            if stored_hash and current_hash:
                if stored_hash == current_hash:
                    print(f"  [OK] {obj_name}: hash matches")
                else:
                    print(f"  [FAIL] {obj_name}: hash differs")
                    all_objs_match = False
                    all_match = False
            elif stored_hash and not current_hash:
                print(f"  [FAIL] {obj_name}: file missing")
                all_match = False
            elif not stored_hash and current_hash:
                print(f"  [WARN] {obj_name}: new file (not in stored hashes)")
        if all_objs_match:
            print(f"  [OK] All {len(stored_objs)} Stage2 object files match")
    else:
        print("  [WARN] No object files to verify")
    
    # Summary
    print("\n" + "=" * 60)
    if all_match:
        print("Hash Verification: PASSED")
        print("=" * 60)
        print("\nAll artifacts match stored hashes.")
        print("\nNote: Hash stability expectations:")
        print("  - Executables: Should be byte-identical (or functionally equivalent)")
        print("  - Object files: May differ in metadata/timestamps but should be functionally equivalent")
        print("  - Rebuilds should produce identical or equivalent artifacts")
        return True
    else:
        print("Hash Verification: FAILED")
        print("=" * 60)
        print("\nSome artifacts differ from stored hashes.")
        print("This may indicate:")
        print("  - Non-deterministic compilation")
        print("  - Source code changes")
        print("  - Toolchain version differences")
        print("  - Acceptable metadata differences (in hash mode)")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Verify bootstrap artifacts are stable across rebuilds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update stored artifact hashes"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify current artifacts against stored hashes"
    )
    
    args = parser.parse_args()
    
    if not args.update and not args.verify:
        # Default: verify if hashes exist, otherwise update
        if hashes_file.exists():
            return 0 if verify_hashes() else 1
        else:
            print("No stored hashes found. Updating...")
            return 0 if update_hashes() else 1
    
    if args.update:
        return 0 if update_hashes() else 1
    
    if args.verify:
        return 0 if verify_hashes() else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
