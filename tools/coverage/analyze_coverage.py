#!/usr/bin/env python3
"""Analyze coverage.json to identify gaps"""

import json
import sys
from pathlib import Path

def main():
    repo_root = Path(__file__).parent.parent
    # Check build/ first, then root for backwards compatibility
    coverage_file = repo_root / "build" / "coverage.json"
    if not coverage_file.exists():
        coverage_file = repo_root / "coverage.json"
    
    if not coverage_file.exists():
        print("coverage.json not found")
        return 1
    
    with open(coverage_file) as f:
        data = json.load(f)
    
    totals = data.get('totals', {})
    total_coverage = totals.get('percent_covered', 0)
    
    print(f"Total coverage: {total_coverage:.2f}%\n")
    
    # Get all source files
    files = []
    for filepath, file_data in data.get('files', {}).items():
        # Normalize path separators
        normalized_path = filepath.replace('\\', '/')
        if 'forge/src' in normalized_path:
            rel_path = normalized_path.replace('forge/src/', '')
            summary = file_data.get('summary', {})
            coverage = summary.get('percent_covered', 0)
            num_statements = summary.get('num_statements', 0)
            num_missing = len(file_data.get('missing_lines', []))
            num_covered = summary.get('covered_lines', 0)
            files.append((rel_path, coverage, num_statements, num_missing, num_covered))
    
    # Sort by coverage (lowest first)
    files.sort(key=lambda x: x[1])
    
    print("All source files (sorted by coverage):")
    print("-" * 80)
    for rel_path, coverage, num_statements, num_missing, num_covered in files:
        print(f"  {coverage:6.1f}% - {rel_path:40s} ({num_missing}/{num_statements} missing, {num_covered} covered)")
    
    # Check for files with 0% coverage
    zero_coverage = [f for f in files if f[1] == 0.0]
    if zero_coverage:
        print(f"\n\nFiles with 0% coverage ({len(zero_coverage)}):")
        for rel_path, _, num_statements, num_missing, _ in zero_coverage:
            print(f"  - {rel_path} ({num_statements} statements, {num_missing} missing)")
    
    # Check for bridge files specifically
    bridge_files = [f for f in files if 'bridge' in f[0]]
    if bridge_files:
        print(f"\n\nBridge files:")
        for rel_path, coverage, num_statements, num_missing, num_covered in bridge_files:
            print(f"  {coverage:6.1f}% - {rel_path:40s} ({num_missing}/{num_statements} missing, {num_covered} covered)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
