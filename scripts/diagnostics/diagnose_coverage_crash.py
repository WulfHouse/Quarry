#!/usr/bin/env python3
"""
Systematic diagnosis of coverage crash issue.

Runs a 2x2 matrix to isolate the trigger:
1. pytest WITHOUT coverage
2. pytest WITH coverage
3. coverage report step alone (after small run)
4. pytest collection only

Records metrics for each run to identify the exact trigger.
"""

import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime


def find_repo_root() -> Path:
    """Find repository root"""
    script_dir = Path(__file__).parent
    return script_dir.parent


def run_safe_command(cmd: list, description: str, max_seconds: int = 600, max_rss_mb: int = 4096) -> dict:
    """Run command via safe wrapper and return results"""
    repo_root = find_repo_root()
    safe_wrapper = repo_root / "tools" / "run_tests_safe.py"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    metrics_file = repo_root / f"diagnostic_metrics_{timestamp}.jsonl"
    
    full_cmd = [
        str(sys.executable),
        str(safe_wrapper),
        f"--max-seconds={max_seconds}",
        f"--max-rss-mb={max_rss_mb}",
        f"--metrics-file={metrics_file}",
        "--",
    ] + cmd
    
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Metrics: {metrics_file}")
    print()
    
    start_time = time.time()
    try:
        result = subprocess.run(
            full_cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=max_seconds + 60  # Add buffer
        )
        elapsed = time.time() - start_time
        
        # Parse metrics
        metrics_summary = {}
        if metrics_file.exists():
            try:
                with open(metrics_file) as f:
                    metrics = [json.loads(line) for line in f if line.strip()]
                    if metrics:
                        rss_values = [m['rss_mb'] for m in metrics if m.get('rss_mb') is not None]
                        if rss_values:
                            metrics_summary = {
                                'rss_mb_peak': max(rss_values),
                                'rss_mb_final': rss_values[-1],
                                'samples': len(metrics),
                            }
            except Exception as e:
                print(f"WARNING: Failed to parse metrics: {e}")
        
        return {
            'description': description,
            'command': ' '.join(cmd),
            'exit_code': result.returncode,
            'elapsed_seconds': round(elapsed, 2),
            'stdout_lines': len(result.stdout.splitlines()),
            'stderr_lines': len(result.stderr.splitlines()),
            'metrics': metrics_summary,
            'success': result.returncode == 0,
            'timed_out': False,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return {
            'description': description,
            'command': ' '.join(cmd),
            'exit_code': -1,
            'elapsed_seconds': round(elapsed, 2),
            'timed_out': True,
            'success': False,
        }
    except Exception as e:
        return {
            'description': description,
            'command': ' '.join(cmd),
            'exit_code': -1,
            'error': str(e),
            'success': False,
        }


def check_coverage_files(repo_root: Path) -> dict:
    """Check size of coverage files"""
    coverage_files = {}
    
    # Check .coverage file
    coverage_file = repo_root / ".coverage"
    if coverage_file.exists():
        size_mb = coverage_file.stat().st_size / (1024 * 1024)
        coverage_files['.coverage'] = round(size_mb, 2)
    
    # Check .coverage.* files (parallel coverage)
    for f in repo_root.glob(".coverage.*"):
        size_mb = f.stat().st_size / (1024 * 1024)
        coverage_files[f.name] = round(size_mb, 2)
    
    # Check htmlcov directory
    htmlcov = repo_root / "htmlcov"
    if htmlcov.exists() and htmlcov.is_dir():
        total_size = sum(f.stat().st_size for f in htmlcov.rglob('*') if f.is_file())
        coverage_files['htmlcov_total_mb'] = round(total_size / (1024 * 1024), 2)
        coverage_files['htmlcov_file_count'] = len(list(htmlcov.rglob('*')))
    
    return coverage_files


def main():
    """Run diagnostic matrix"""
    repo_root = find_repo_root()
    os.chdir(repo_root)
    
    print("=" * 70)
    print("COVERAGE CRASH DIAGNOSIS")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print(f"Python: {sys.executable}")
    print()
    
    results = []
    
    # Test 1: pytest WITHOUT coverage
    print("\n" + "="*70)
    print("TEST 1: pytest WITHOUT coverage")
    print("="*70)
    result1 = run_safe_command(
        [sys.executable, "tools/testing/pytest.py", "-q"],
        "pytest without coverage",
        max_seconds=300,
        max_rss_mb=2048
    )
    results.append(result1)
    
    # Test 2: pytest WITH coverage
    print("\n" + "="*70)
    print("TEST 2: pytest WITH coverage")
    print("="*70)
    result2 = run_safe_command(
        [sys.executable, "tools/testing/pytest.py", "--cov=forge/src", "--cov-report=term", "-q"],
        "pytest with coverage (term report only)",
        max_seconds=600,
        max_rss_mb=4096
    )
    results.append(result2)
    coverage_files_after_test2 = check_coverage_files(repo_root)
    
    # Test 3: coverage report step alone (if we have .coverage file)
    if (repo_root / ".coverage").exists():
        print("\n" + "="*70)
        print("TEST 3: coverage report generation (HTML)")
        print("="*70)
        result3 = run_safe_command(
            [sys.executable, "-m", "coverage", "html"],
            "coverage html report generation",
            max_seconds=300,
            max_rss_mb=4096
        )
        results.append(result3)
        coverage_files_after_test3 = check_coverage_files(repo_root)
    else:
        print("\n" + "="*70)
        print("TEST 3: SKIPPED (no .coverage file)")
        print("="*70)
        result3 = {'description': 'coverage html (skipped)', 'skipped': True}
        results.append(result3)
        coverage_files_after_test3 = {}
    
    # Test 4: pytest collection only
    print("\n" + "="*70)
    print("TEST 4: pytest collection only")
    print("="*70)
    result4 = run_safe_command(
        [sys.executable, "tools/testing/pytest.py", "--collect-only", "-q"],
        "pytest collection only",
        max_seconds=120,
        max_rss_mb=2048
    )
    results.append(result4)
    
    # Print summary
    print("\n" + "="*70)
    print("DIAGNOSIS SUMMARY")
    print("="*70)
    
    for result in results:
        if result.get('skipped'):
            print(f"\n{result['description']}: SKIPPED")
            continue
        
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        if result.get('timed_out'):
            status = "⏱️  TIMEOUT"
        
        print(f"\n{result['description']}: {status}")
        print(f"  Exit code: {result.get('exit_code', 'N/A')}")
        print(f"  Elapsed: {result.get('elapsed_seconds', 0):.1f}s")
        if 'metrics' in result and result['metrics']:
            m = result['metrics']
            if 'rss_mb_peak' in m:
                print(f"  Peak RSS: {m['rss_mb_peak']:.1f}MB")
                print(f"  Final RSS: {m['rss_mb_final']:.1f}MB")
    
    # Coverage file sizes
    print("\n" + "="*70)
    print("COVERAGE FILE SIZES")
    print("="*70)
    if coverage_files_after_test2:
        print("\nAfter test 2 (pytest with coverage):")
        for name, size in coverage_files_after_test2.items():
            print(f"  {name}: {size}MB")
    if coverage_files_after_test3:
        print("\nAfter test 3 (coverage html):")
        for name, size in coverage_files_after_test3.items():
            print(f"  {name}: {size}MB")
    
    # Root cause analysis
    print("\n" + "="*70)
    print("ROOT CAUSE ANALYSIS")
    print("="*70)
    
    if result1.get('success') and not result2.get('success'):
        print("\n🔍 CONCLUSION: Coverage is the trigger")
        print("   - pytest without coverage: ✅ OK")
        print("   - pytest with coverage: ❌ FAILED")
        print("\n   Likely causes:")
        print("   1. Coverage tracing too much code (check source scope)")
        print("   2. Coverage data accumulation (check .coverage file size)")
        print("   3. Coverage report generation overhead")
    elif result4.get('timed_out') or (not result4.get('success') and result4.get('elapsed_seconds', 0) > 60):
        print("\n🔍 CONCLUSION: Test collection is the trigger")
        print("   - Collection is slow/failing")
        print("\n   Likely causes:")
        print("   1. Collecting from wrong directories (venv, node_modules, etc.)")
        print("   2. Too many test files")
        print("   3. Import errors during collection")
    elif result3.get('timed_out') or (not result3.get('success') and 'html' in result3.get('description', '')):
        print("\n🔍 CONCLUSION: HTML report generation is the trigger")
        print("   - Coverage HTML report generation is slow/failing")
        print("\n   Likely causes:")
        print("   1. HTML report includes too much data")
        print("   2. HTML report generation is memory-intensive")
    else:
        print("\n🔍 CONCLUSION: Inconclusive - need more investigation")
        print("   Review metrics files for detailed analysis")
    
    # Save results
    results_file = repo_root / f"diagnostic_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'coverage_files_after_test2': coverage_files_after_test2,
            'coverage_files_after_test3': coverage_files_after_test3,
        }, f, indent=2)
    
    print(f"\nFull results saved to: {results_file}")
    print("="*70)


if __name__ == "__main__":
    main()
