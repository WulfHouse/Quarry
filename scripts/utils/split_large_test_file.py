#!/usr/bin/env python3
"""
Split large test files into smaller, more manageable modules.

This script splits test_closure_inline_pass.py (2,219 lines) into logical modules:
- test_closure_inline_pass_basic.py - Initialization and basic functionality
- test_closure_inline_pass_collect.py - Collection tests
- test_closure_inline_pass_inline.py - Inlining tests
- test_closure_inline_pass_edge_cases.py - Complex scenarios
"""

import re
from pathlib import Path


def split_test_file(test_file: Path, output_dir: Path):
    """Split a large test file into smaller modules"""
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract header (imports and docstring)
    header_match = re.match(r'(.*?)(def test_|class Test)', content, re.DOTALL)
    if not header_match:
        print(f"ERROR: Could not find test functions in {test_file}")
        return False
    
    header = header_match.group(1)
    
    # Split into test functions
    test_pattern = r'(def test_[^\n]+\([^)]*\):.*?)(?=def test_|class Test|\Z)'
    tests = re.findall(test_pattern, content, re.DOTALL)
    
    # Categorize tests
    basic_tests = []
    collect_tests = []
    inline_tests = []
    edge_case_tests = []
    
    for test in tests:
        test_name = re.search(r'def (test_\w+)', test).group(1) if re.search(r'def (test_\w+)', test) else ""
        
        if 'init' in test_name or 'empty' in test_name:
            basic_tests.append(test)
        elif 'collect' in test_name:
            collect_tests.append(test)
        elif 'inline' in test_name:
            inline_tests.append(test)
        else:
            edge_case_tests.append(test)
    
    # Write split files
    modules = [
        ('test_closure_inline_pass_basic.py', basic_tests, 'Initialization and basic functionality tests'),
        ('test_closure_inline_pass_collect.py', collect_tests, 'Collection tests for closure inline pass'),
        ('test_closure_inline_pass_inline.py', inline_tests, 'Inlining tests for closure inline pass'),
        ('test_closure_inline_pass_edge_cases.py', edge_case_tests, 'Edge cases and complex scenarios'),
    ]
    
    for filename, test_list, description in modules:
        if not test_list:
            continue
        
        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'"""{description}"""\n\n')
            f.write(header)
            f.write('\n\n'.join(test_list))
            if not test_list[-1].endswith('\n'):
                f.write('\n')
        
        print(f"Created {output_file} with {len(test_list)} tests")
    
    return True


def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.parent
    test_file = repo_root / "forge" / "tests" / "passes" / "test_closure_inline_pass.py"
    output_dir = repo_root / "forge" / "tests" / "passes"
    
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return 1
    
    print(f"Splitting {test_file}...")
    if split_test_file(test_file, output_dir):
        print(f"\n[SUCCESS] Successfully split test file")
        print(f"   Original: {test_file}")
        print(f"   Split into 4 modules in {output_dir}")
        print(f"\n[NOTE] Original file still exists. Review split files and delete original when ready.")
        return 0
    else:
        print("❌ Failed to split test file")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
