#!/usr/bin/env python3
"""Extract coverage percentage from coverage.json"""

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
        print("coverage.json not found", file=sys.stderr)
        return 1
    
    with open(coverage_file) as f:
        data = json.load(f)
    
    totals = data.get('totals', {})
    total_coverage = totals.get('percent_covered', 0)
    
    print(f"{total_coverage:.2f}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
