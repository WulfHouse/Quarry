#!/usr/bin/env python3
"""Extract uncovered lines for a specific file from coverage.json"""

import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/get_uncovered_lines.py <filename>")
        print("Example: python tools/get_uncovered_lines.py codegen.py")
        return 1
    
    filename = sys.argv[1]
    repo_root = Path(__file__).parent.parent
    # Check build/ first, then root for backwards compatibility
    coverage_file = repo_root / "build" / "coverage.json"
    if not coverage_file.exists():
        coverage_file = repo_root / "coverage.json"
    
    if not coverage_file.exists():
        print("coverage.json not found", file=sys.stderr)
        return 1
    
    with open(coverage_file) as f:
        data = json.load(f)
    
    # Find the file in coverage data
    files = data.get('files', {})
    target_file = None
    
    for filepath, file_data in files.items():
        # Normalize path separators
        normalized_path = filepath.replace('\\', '/')
        if filename in normalized_path and 'forge/src' in normalized_path:
            target_file = (filepath, file_data)
            break
    
    if not target_file:
        print(f"File {filename} not found in coverage data", file=sys.stderr)
        return 1
    
    filepath, file_data = target_file
    missing_lines = file_data.get('missing_lines', [])
    summary = file_data.get('summary', {})
    coverage = summary.get('percent_covered', 0)
    num_statements = summary.get('num_statements', 0)
    
    print(f"File: {filepath}")
    print(f"Coverage: {coverage:.1f}%")
    print(f"Statements: {num_statements}")
    print(f"Missing lines: {len(missing_lines)}")
    print(f"\nUncovered lines:")
    # Limit output to first 50 lines to avoid overwhelming output
    sorted_lines = sorted(missing_lines)
    for line_num in sorted_lines[:50]:
        print(f"  Line {line_num}")
    if len(sorted_lines) > 50:
        print(f"  ... and {len(sorted_lines) - 50} more lines")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
