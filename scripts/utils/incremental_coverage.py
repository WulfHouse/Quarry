#!/usr/bin/env python3
"""
Incremental coverage - only measure coverage for changed files.

This script:
1. Detects changed Python files in forge/src
2. Runs tests with coverage only for those files
3. Generates a focused coverage report

Usage:
    python scripts/incremental_coverage.py                    # Changed files vs HEAD
    python scripts/incremental_coverage.py --base=origin/main  # Changed vs base branch
    python scripts/incremental_coverage.py --files=src/lexer.py,src/parser.py  # Specific files
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Set


def find_repo_root() -> Path:
    """Find repository root"""
    current = Path.cwd().resolve()
    for path in [current] + list(current.parents):
        if (path / "forge").exists():
            return path
    return Path.cwd()


def get_changed_files(base: str = "HEAD") -> Set[str]:
    """Get list of changed Python files in forge/src"""
    repo_root = find_repo_root()
    
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        changed = set()
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            path = Path(line)
            # Only include Python files in forge/src
            if path.parts[0] == "forge" and path.parts[1] == "src" and path.suffix == ".py":
                changed.add(str(path))
        
        return changed
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to get changed files: {e}", file=sys.stderr)
        return set()
    except FileNotFoundError:
        print("ERROR: git not found. Is this a git repository?", file=sys.stderr)
        return set()


def get_specific_files(files_arg: str) -> Set[str]:
    """Parse comma-separated file list"""
    files = set()
    for f in files_arg.split(','):
        f = f.strip()
        if f:
            # Normalize path
            if not f.startswith('forge/src/'):
                if f.startswith('src/'):
                    f = f"forge/{f}"
                else:
                    f = f"forge/src/{f}"
            files.add(f)
    return files


def run_incremental_coverage(files: Set[str], base: str = None) -> int:
    """Run coverage only for specified files"""
    if not files:
        print("No files to measure coverage for.")
        print("Use --files to specify files, or ensure you have uncommitted changes.")
        return 1
    
    repo_root = find_repo_root()
    
    # Convert to coverage source format (module paths)
    source_modules = []
    for file_path in sorted(files):
        # Convert forge/src/lexer.py -> forge/src
        # Coverage will measure all files in the source directory, but we'll filter the report
        source_dir = str(Path(file_path).parent)
        if source_dir not in source_modules:
            source_modules.append(source_dir)
    
    if not source_modules:
        print("ERROR: No valid source files found")
        return 1
    
    print("=" * 70)
    print("INCREMENTAL COVERAGE")
    print("=" * 70)
    print(f"Files to measure: {len(files)}")
    for f in sorted(files):
        print(f"  - {f}")
    print()
    
    # Build coverage command
    # Note: coverage.py doesn't support per-file source, so we use the whole src/
    # but filter the report to only show changed files
    cmd = [
        sys.executable,
        "tools/testing/pytest.py",
        "--cov=forge/src",
        "--cov-report=term",
        "-q"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, cwd=repo_root)
    
    if result.returncode == 0:
        print()
        print("=" * 70)
        print("COVERAGE REPORT (showing only changed files)")
        print("=" * 70)
        
        # Generate filtered report
        try:
            # Get coverage report and filter to changed files
            report_result = subprocess.run(
                [sys.executable, "-m", "coverage", "report"],
                cwd=repo_root,
                capture_output=True,
                text=True
            )
            
            if report_result.returncode == 0:
                lines = report_result.stdout.split('\n')
                # Filter to show only changed files
                print("Name", "Stmts", "Miss", "Cover", sep="\t")
                print("-" * 70)
                
                for line in lines:
                    # Coverage report format: Name    Stmts   Miss  Cover
                    for file_path in files:
                        # Extract module name from path
                        module_name = Path(file_path).stem
                        if module_name in line or file_path.replace('forge/src/', '').replace('.py', '') in line:
                            print(line)
                            break
            else:
                print("Could not generate filtered report. Run 'coverage report' manually.")
        except Exception as e:
            print(f"Could not filter report: {e}")
    
    return result.returncode


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run incremental coverage for changed files"
    )
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git base to compare against (default: HEAD)"
    )
    parser.add_argument(
        "--files",
        help="Comma-separated list of specific files to measure"
    )
    
    args = parser.parse_args()
    
    if args.files:
        files = get_specific_files(args.files)
    else:
        files = get_changed_files(args.base)
    
    return run_incremental_coverage(files, args.base)


if __name__ == "__main__":
    sys.exit(main())
