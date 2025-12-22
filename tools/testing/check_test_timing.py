#!/usr/bin/env python3
"""
Runtime budget enforcement tool for test lanes.
Reads test_timing.json and fails if runtime exceeds budget.

Usage:
    python tools/check_test_timing.py --max-seconds=300 test_timing.json
    python tools/check_test_timing.py --lane=1 test_timing.json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional


# Default budgets per lane (in seconds)
LANE_BUDGETS = {
    1: 300,   # Lane 1 (fast): 5 minutes
    2: 1200,  # Lane 2 (integration): 20 minutes
    3: 3600,  # Lane 3 (slow): 60 minutes
}


def load_timing_json(file_path: Path) -> Dict:
    """Load test timing JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Timing file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in timing file: {e}")
        sys.exit(1)


def calculate_total_time(timing_data: Dict) -> float:
    """Calculate total test runtime from timing data"""
    tests = timing_data.get('tests', {})
    if not tests:
        return 0.0
    
    # Sum all test durations
    total = sum(tests.values())
    return total


def check_budget(
    timing_file: Path,
    max_seconds: Optional[int] = None,
    lane: Optional[int] = None
) -> bool:
    """
    Check if test runtime exceeds budget.
    Returns True if within budget, False if exceeded.
    """
    timing_data = load_timing_json(timing_file)
    
    total_time = calculate_total_time(timing_data)
    test_count = len(timing_data.get('tests', {}))
    
    # Determine budget
    if max_seconds is not None:
        budget = max_seconds
        budget_source = f"--max-seconds={max_seconds}"
    elif lane is not None:
        budget = LANE_BUDGETS.get(lane)
        if budget is None:
            print(f"Error: Unknown lane: {lane}. Valid lanes: 1, 2, 3")
            sys.exit(1)
        budget_source = f"Lane {lane} budget"
    else:
        # Default to Lane 1 budget
        budget = LANE_BUDGETS[1]
        budget_source = "default (Lane 1)"
    
    # Print summary
    print(f"Test Timing Budget Check")
    print(f"  Timing file: {timing_file}")
    print(f"  Total tests: {test_count}")
    print(f"  Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    print(f"  Budget: {budget}s ({budget/60:.2f} minutes) [{budget_source}]")
    print()
    
    # Check budget
    if total_time > budget:
        overage = total_time - budget
        overage_pct = (overage / budget) * 100
        print(f"❌ BUDGET EXCEEDED")
        print(f"   Overage: {overage:.2f}s ({overage/60:.2f} minutes)")
        print(f"   Overage: {overage_pct:.1f}% over budget")
        print()
        print("To fix:")
        print("  1. Remove slow tests from this lane")
        print("  2. Optimize slow tests")
        print("  3. Split large tests into smaller ones")
        return False
    else:
        remaining = budget - total_time
        remaining_pct = (remaining / budget) * 100
        print(f"✅ BUDGET OK")
        print(f"   Remaining: {remaining:.2f}s ({remaining/60:.2f} minutes)")
        print(f"   Remaining: {remaining_pct:.1f}% of budget")
        return True


def check_regression(
    current_file: Path,
    baseline_file: Path,
    lane: Optional[int] = None
) -> bool:
    """
    Check if current runtime exceeds baseline by threshold.
    Returns True if within threshold, False if regression detected.
    """
    current_data = load_timing_json(current_file)
    baseline_data = load_timing_json(baseline_file)
    
    current_time = calculate_total_time(current_data)
    baseline_time = calculate_total_time(baseline_data)
    
    # Determine threshold based on lane
    if lane == 1:
        threshold = 0.20  # 20% for Lane 1
    elif lane == 2:
        threshold = 0.50  # 50% for Lane 2
    else:
        threshold = 1.00  # 100% for Lane 3 (more lenient)
    
    max_allowed = baseline_time * (1 + threshold)
    
    print(f"Runtime Regression Check")
    print(f"  Current timing: {current_file}")
    print(f"  Baseline timing: {baseline_file}")
    print(f"  Baseline time: {baseline_time:.2f}s ({baseline_time/60:.2f} minutes)")
    print(f"  Current time: {current_time:.2f}s ({current_time/60:.2f} minutes)")
    print(f"  Threshold: {threshold*100:.0f}%")
    print(f"  Max allowed: {max_allowed:.2f}s ({max_allowed/60:.2f} minutes)")
    print()
    
    if current_time > max_allowed:
        overage = current_time - max_allowed
        regression_pct = ((current_time - baseline_time) / baseline_time) * 100
        print(f"❌ REGRESSION DETECTED")
        print(f"   Regression: {regression_pct:.1f}% slower than baseline")
        print(f"   Overage: {overage:.2f}s ({overage/60:.2f} minutes) over threshold")
        print()
        print("To fix:")
        print("  1. Identify new slow tests")
        print("  2. Move slow tests to appropriate lane")
        print("  3. Optimize or split large tests")
        print("  4. Update baseline if regression is intentional: python tools/check_test_timing.py --update-baseline")
        return False
    else:
        improvement = baseline_time - current_time
        if improvement > 0:
            improvement_pct = (improvement / baseline_time) * 100
            print(f"✅ NO REGRESSION (Improved by {improvement_pct:.1f}%)")
        else:
            slowdown_pct = ((current_time - baseline_time) / baseline_time) * 100
            print(f"✅ NO REGRESSION (Within threshold, {slowdown_pct:.1f}% slower)")
        return True


def update_baseline(current_file: Path, baseline_file: Path) -> None:
    """Update baseline file with current timing data"""
    current_data = load_timing_json(current_file)
    
    # Create baseline structure
    baseline_data = {
        "tests": current_data.get("tests", {}),
        "summary": current_data.get("summary", {}),
        "timestamp": current_data.get("summary", {}).get("total_time", 0),
    }
    
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"Baseline updated: {baseline_file}")
    print(f"  Total time: {baseline_data['summary'].get('total_time', 0):.2f}s")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check test timing against runtime budget'
    )
    parser.add_argument(
        'timing_file',
        type=Path,
        help='Path to test_timing.json file'
    )
    parser.add_argument(
        '--max-seconds',
        type=int,
        help='Maximum runtime in seconds'
    )
    parser.add_argument(
        '--lane',
        type=int,
        choices=[1, 2, 3],
        help='Test lane (1=fast, 2=integration, 3=slow)'
    )
    parser.add_argument(
        '--baseline',
        type=Path,
        help='Path to baseline timing file for regression check'
    )
    parser.add_argument(
        '--update-baseline',
        action='store_true',
        help='Update baseline file with current timing'
    )
    
    args = parser.parse_args()
    
    if not args.timing_file.exists():
        print(f"Error: Timing file not found: {args.timing_file}")
        sys.exit(1)
    
    # Handle baseline update
    if args.update_baseline:
        if not args.baseline:
            # Default baseline location
            baseline_file = args.timing_file.parent / "test_timing_baseline.json"
        else:
            baseline_file = args.baseline
        update_baseline(args.timing_file, baseline_file)
        return
    
    # Handle regression check
    if args.baseline:
        if not args.baseline.exists():
            print(f"Error: Baseline file not found: {args.baseline}")
            sys.exit(1)
        passed = check_regression(
            args.timing_file,
            args.baseline,
            lane=args.lane
        )
        sys.exit(0 if passed else 1)
    
    # Handle budget check
    passed = check_budget(
        args.timing_file,
        max_seconds=args.max_seconds,
        lane=args.lane
    )
    
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
