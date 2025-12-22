#!/usr/bin/env python3
"""
Test runner with explicit progress indicators for long-running test suites.

This wrapper ensures progress is visible during long test runs by:
- Showing test names as they execute (verbose mode)
- Displaying periodic progress updates
- Showing slowest tests at the end
- Preventing the appearance of hanging

Usage:
    python tools/run_tests_with_progress.py                    # Full suite with progress
    python tools/run_tests_with_progress.py test_lexer.py      # Specific file
    python tools/run_tests_with_progress.py --cov=forge/src  # With coverage
"""

import sys
import subprocess
import time
import threading
from pathlib import Path


def find_repo_root() -> Path:
    """Find repository root"""
    current = Path.cwd().resolve()
    for path in [current] + list(current.parents):
        if (path / "forge").exists():
            return path
    return Path.cwd()


def show_progress_indicator(process, start_time):
    """Show periodic progress updates while process runs"""
    last_update = time.time()
    update_interval = 10.0  # Update every 10 seconds
    
    while process.poll() is None:
        time.sleep(1.0)
        elapsed = time.time() - start_time
        
        # Show progress every 10 seconds
        if time.time() - last_update >= update_interval:
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            print(f"\n[PROGRESS] Tests still running... ({elapsed_min}m {elapsed_sec}s elapsed)", 
                  flush=True, file=sys.stderr)
            last_update = time.time()


def main():
    """Main entry point"""
    repo_root = find_repo_root()
    args = sys.argv[1:]
    
    # Build pytest command
    cmd = [sys.executable, "tools/pytest.py"]
    
    # For full suite, ensure we have progress indicators
    is_full_suite = not any(
        arg.endswith('.py') and 'test_' in arg 
        for arg in args 
        if not arg.startswith('-')
    )
    
    # Add progress options if not already specified (before other args)
    if is_full_suite:
        if '-v' not in args and '--verbose' not in args and '-q' not in args:
            # Use verbose mode to show progress (test names as they run)
            cmd.append('-v')
        if '--durations' not in ' '.join(args):
            cmd.append('--durations=10')
        if '--tb=' not in ' '.join(args):
            cmd.append('--tb=short')
    
    # Add remaining arguments
    cmd.extend(args)
    
    print("=" * 70)
    print("TEST RUNNER WITH PROGRESS")
    print("=" * 70)
    print(f"Command: {' '.join(cmd)}")
    if is_full_suite:
        print("Mode: Full suite (progress indicators enabled)")
    print("=" * 70)
    print()
    
    # Start process
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        cwd=repo_root,
        stdout=None,  # Let output stream directly
        stderr=None,
        text=True
    )
    
    # Start progress indicator thread
    if is_full_suite:
        progress_thread = threading.Thread(
            target=show_progress_indicator,
            args=(process, start_time),
            daemon=True
        )
        progress_thread.start()
    
    # Wait for completion
    try:
        returncode = process.wait()
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        
        print()
        print("=" * 70)
        print(f"TESTS COMPLETED in {elapsed_min}m {elapsed_sec}s")
        print("=" * 70)
        
        sys.exit(returncode)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Terminating test run...", file=sys.stderr)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        sys.exit(130)


if __name__ == "__main__":
    main()
