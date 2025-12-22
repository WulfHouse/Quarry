#!/usr/bin/env python3
"""Find dead/unreachable code using coverage data

This script analyzes coverage.json to identify code that is never executed
and may be dead code. It helps improve coverage measurement accuracy.
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple


def find_dead_code(coverage_file: Path) -> List[Tuple[str, List[int], float]]:
    """Find files with 0% coverage that might be dead code"""
    with open(coverage_file) as f:
        data = json.load(f)
    
    dead_code = []
    
    for filepath, file_data in data.get('files', {}).items():
        # Normalize path separators
        normalized_path = filepath.replace('\\', '/')
        
        # Only check source files (not tests, tools, etc.)
        if 'forge/src' not in normalized_path:
            continue
        
        summary = file_data.get('summary', {})
        coverage = summary.get('percent_covered', 0)
        missing_lines = file_data.get('missing_lines', [])
        num_statements = summary.get('num_statements', 0)
        
        # Files with 0% coverage and statements are candidates for dead code
        if coverage == 0.0 and num_statements > 0:
            dead_code.append((normalized_path, missing_lines, coverage))
    
    return dead_code


def verify_code_is_reachable(filepath: str, missing_lines: List[int]) -> bool:
    """Verify if code is truly unreachable (not just untested)"""
    # This is a simple check - in practice, you'd want more sophisticated analysis
    # For now, we'll flag files with 0% coverage for manual review
    
    # Check if file exists
    path = Path(filepath)
    if not path.exists():
        return False  # File doesn't exist, definitely dead
    
    # Files with 0% coverage and multiple statements are suspicious
    # But we should verify they're not just untested
    return len(missing_lines) > 0


def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.parent
    # Check build/ first, then root for backwards compatibility
    coverage_file = repo_root / "build" / "coverage.json"
    if not coverage_file.exists():
        coverage_file = repo_root / "coverage.json"
    
    if not coverage_file.exists():
        print("Error: coverage.json not found")
        print("Run coverage first to generate coverage.json")
        return 1
    
    dead_code = find_dead_code(coverage_file)
    
    if not dead_code:
        print("No dead code found (0% coverage files)")
        print("All source files have at least some coverage.")
        return 0
    
    print("Potential dead code (0% coverage files):")
    print("=" * 80)
    print()
    print("WARNING: These files have 0% coverage.")
    print("   They may be dead code, or they may just be untested.")
    print("   Review each file manually before deleting.")
    print()
    
    for filepath, missing_lines, coverage in dead_code:
        rel_path = filepath.replace('forge/src/', '')
        print(f"  {rel_path}")
        print(f"    Coverage: {coverage:.1f}%")
        print(f"    Missing lines: {len(missing_lines)}")
        if len(missing_lines) <= 20:
            print(f"    Lines: {missing_lines}")
        else:
            print(f"    Lines: {missing_lines[:20]}... (and {len(missing_lines) - 20} more)")
        print()
    
    print("=" * 80)
    print(f"Total: {len(dead_code)} file(s) with 0% coverage")
    print()
    print("Next steps:")
    print("1. Review each file to determine if it's truly dead code")
    print("2. Check if code is called from anywhere (grep, static analysis)")
    print("3. Check if code is part of public API (should be tested)")
    print("4. If confirmed dead, delete the code")
    print("5. If not dead, add tests to cover it")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
