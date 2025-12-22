#!/usr/bin/env python3
"""
Helper module for test timing instrumentation.
Parses pytest output and generates test_timing.json.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def parse_pytest_durations(output: str) -> Dict[str, float]:
    """
    Parse pytest --durations=0 output to extract test durations.
    
    Expected format:
    =============== slowest test durations ===============
    10.50s setup    forge/tests/test_integration.py::test_full_pipeline
    5.23s call     forge/tests/test_lexer.py::test_lex_integer
    0.10s teardown forge/tests/test_parser.py::test_parse_function
    ...
    
    Returns dict mapping test names to durations in seconds.
    """
    timings: Dict[str, float] = {}
    
    # Pattern to match duration lines
    # Format: "DURATION TYPE    TEST_PATH::test_name"
    duration_pattern = re.compile(
        r'^\s*(\d+\.?\d*)\s*(s|ms|us)\s+(setup|call|teardown)\s+(.+)$',
        re.MULTILINE
    )
    
    # Find the "slowest test durations" section
    if "slowest test durations" not in output.lower():
        # If no durations section, try to parse from test results
        # Look for lines like: "test_name PASSED [0.12s]"
        result_pattern = re.compile(
            r'(\S+::\S+)\s+(PASSED|FAILED|SKIPPED).*?\[(\d+\.?\d*)\s*(s|ms|us)\]',
            re.MULTILINE
        )
        for match in result_pattern.finditer(output):
            test_name = match.group(1)
            duration_str = match.group(3)
            unit = match.group(4)
            duration = float(duration_str)
            if unit == 'ms':
                duration /= 1000.0
            elif unit == 'us':
                duration /= 1000000.0
            timings[test_name] = duration
        return timings
    
    # Parse duration lines
    for match in duration_pattern.finditer(output):
        duration_str = match.group(1)
        unit = match.group(2)
        phase = match.group(3)  # setup, call, or teardown
        test_name = match.group(4).strip()
        
        duration = float(duration_str)
        if unit == 'ms':
            duration /= 1000.0
        elif unit == 'us':
            duration /= 1000000.0
        
        # For each test, we want the total time (sum of setup + call + teardown)
        # But typically we care most about "call" time
        # Store both total and call time
        key = f"{test_name}::{phase}"
        timings[key] = duration
        
        # Also store just the test name with call time (most important)
        if phase == 'call':
            timings[test_name] = duration
    
    # If we have setup/call/teardown separately, sum them for total
    test_totals: Dict[str, float] = {}
    for key, duration in timings.items():
        if '::' in key and key.count('::') == 2:  # test_name::phase format
            test_name, phase = key.rsplit('::', 1)
            if test_name not in test_totals:
                test_totals[test_name] = 0.0
            test_totals[test_name] += duration
    
    # Merge totals back into timings
    for test_name, total in test_totals.items():
        if test_name not in timings or timings[test_name] < total:
            timings[f"{test_name}::total"] = total
    
    return timings


def parse_pytest_json_report(json_file: Path) -> Dict[str, float]:
    """
    Parse pytest JSON report (if --json-report is used).
    This is more reliable than parsing text output.
    """
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        timings: Dict[str, float] = {}
        for test in data.get('tests', []):
            test_name = test.get('nodeid', '')
            duration = test.get('duration', 0.0)
            if test_name:
                timings[test_name] = duration
        
        return timings
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


def generate_timing_json(
    timings: Dict[str, float],
    output_file: Path,
    summary: bool = True
) -> None:
    """
    Generate test_timing.json file with test durations.
    
    Format:
    {
        "tests": {
            "test_name": duration_seconds,
            ...
        },
        "summary": {
            "total_tests": N,
            "total_time": X,
            "min_time": Y,
            "max_time": Z,
            "avg_time": W
        }
    }
    """
    # Filter out phase-specific entries, keep only test names
    test_timings = {
        k: v for k, v in timings.items()
        if '::' not in k or k.endswith('::total')
    }
    
    # Remove ::total suffix for cleaner names
    cleaned_timings = {}
    for k, v in test_timings.items():
        if k.endswith('::total'):
            cleaned_key = k[:-7]  # Remove '::total'
            cleaned_timings[cleaned_key] = v
        elif '::' not in k:
            cleaned_timings[k] = v
    
    result = {
        "tests": cleaned_timings
    }
    
    if summary and cleaned_timings:
        durations = list(cleaned_timings.values())
        result["summary"] = {
            "total_tests": len(cleaned_timings),
            "total_time": sum(durations),
            "min_time": min(durations),
            "max_time": max(durations),
            "avg_time": sum(durations) / len(durations) if durations else 0.0
        }
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if summary and cleaned_timings:
        print(f"\nTest Timing Summary:")
        print(f"  Total tests: {result['summary']['total_tests']}")
        print(f"  Total time: {result['summary']['total_time']:.2f}s")
        print(f"  Min time: {result['summary']['min_time']:.3f}s")
        print(f"  Max time: {result['summary']['max_time']:.3f}s")
        print(f"  Avg time: {result['summary']['avg_time']:.3f}s")
        print(f"\nTiming data written to: {output_file}")


def main():
    """CLI entry point for parsing pytest output"""
    if len(sys.argv) < 3:
        print("Usage: python tools/test_timing.py <pytest_output_file> <output_json>")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, 'r') as f:
        output = f.read()
    
    timings = parse_pytest_durations(output)
    generate_timing_json(timings, output_file)


if __name__ == "__main__":
    main()
