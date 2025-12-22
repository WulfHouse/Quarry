#!/usr/bin/env python3
"""
Safe test runner with resource limits and monitoring.

This wrapper prevents test/coverage runs from crashing the machine by:
- Enforcing time limits (MAX_SECONDS)
- Enforcing memory limits (MAX_RSS_MB)
- Monitoring resource usage over time
- Logging metrics to JSONL for analysis
- Enabling faulthandler for crash diagnostics
- Gracefully killing runaway processes

Usage:
    python tools/run_tests_safe.py -- pytest ...
    python tools/run_tests_safe.py --max-rss-mb=2048 -- pytest --cov=forge/src ...
    python tools/run_tests_safe.py --max-seconds=300 -- pytest --collect-only
"""

import sys
import os
import subprocess
import time
import json
import signal
import threading
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Try to import psutil for better resource monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("WARNING: psutil not available. Install with: pip install psutil")
    print("         Falling back to basic monitoring (may be less accurate)")

# Try to enable faulthandler early
try:
    import faulthandler
    faulthandler.enable(all_threads=True)
    FAULTHANDLER_ENABLED = True
except Exception:
    FAULTHANDLER_ENABLED = False
    print("WARNING: faulthandler not available")


class ResourceMonitor:
    """Monitor process resource usage"""
    
    def __init__(self, process: subprocess.Popen, metrics_file: Path):
        self.process = process
        self.metrics_file = metrics_file
        self.monitoring = False
        self.metrics: List[Dict] = []
        self.start_time = time.time()
        
    def get_process_metrics(self) -> Optional[Dict]:
        """Get current process metrics"""
        try:
            if HAS_PSUTIL:
                proc = psutil.Process(self.process.pid)
                with proc.oneshot():
                    rss_mb = proc.memory_info().rss / (1024 * 1024)
                    cpu_percent = proc.cpu_percent()
                    num_threads = proc.num_threads()
                    return {
                        'rss_mb': round(rss_mb, 2),
                        'cpu_percent': round(cpu_percent, 2),
                        'num_threads': num_threads,
                    }
            else:
                # Fallback: try to get basic info from process
                # On Windows, this is limited
                return {
                    'rss_mb': None,
                    'cpu_percent': None,
                    'num_threads': None,
                }
        except (psutil.NoSuchProcess, ProcessLookupError):
            return None
    
    def monitor_loop(self, interval: float = 2.0):
        """Monitor process in background thread"""
        self.monitoring = True
        while self.monitoring and self.process.poll() is None:
            elapsed = time.time() - self.start_time
            metrics = self.get_process_metrics()
            if metrics:
                record = {
                    'timestamp': datetime.now().isoformat(),
                    'elapsed_seconds': round(elapsed, 2),
                    **metrics
                }
                self.metrics.append(record)
                
                # Write to JSONL file
                try:
                    with open(self.metrics_file, 'a') as f:
                        f.write(json.dumps(record) + '\n')
                except Exception as e:
                    print(f"WARNING: Failed to write metrics: {e}", file=sys.stderr)
            
            time.sleep(interval)
    
    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.metrics:
            return {}
        
        rss_values = [m['rss_mb'] for m in self.metrics if m.get('rss_mb') is not None]
        cpu_values = [m['cpu_percent'] for m in self.metrics if m.get('cpu_percent') is not None]
        
        summary = {
            'total_samples': len(self.metrics),
            'duration_seconds': round(time.time() - self.start_time, 2),
        }
        
        if rss_values:
            summary['rss_mb'] = {
                'min': round(min(rss_values), 2),
                'max': round(max(rss_values), 2),
                'avg': round(sum(rss_values) / len(rss_values), 2),
                'final': round(rss_values[-1], 2) if rss_values else None,
            }
        
        if cpu_values:
            summary['cpu_percent'] = {
                'min': round(min(cpu_values), 2),
                'max': round(max(cpu_values), 2),
                'avg': round(sum(cpu_values) / len(cpu_values), 2),
            }
        
        return summary


def parse_args():
    """Parse command line arguments"""
    args = sys.argv[1:]
    
    # Handle help early, before any other processing
    if '-h' in args or '--help' in args:
        print(__doc__)
        sys.exit(0)
    
    max_seconds = 600  # 10 minutes default
    max_rss_mb = 4096  # 4GB default
    metrics_file = None
    command_start = 0
    
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--':
            command_start = i + 1
            break
        elif arg.startswith('--max-seconds='):
            max_seconds = int(arg.split('=', 1)[1])
        elif arg.startswith('--max-rss-mb='):
            max_rss_mb = int(arg.split('=', 1)[1])
        elif arg.startswith('--metrics-file='):
            metrics_file = Path(arg.split('=', 1)[1])
        i += 1
    
    if command_start == 0:
        print("ERROR: Command not found. Use '--' to separate options from command.")
        print("Example: python tools/run_tests_safe.py -- pytest ...")
        print("\nFor help: python tools/run_tests_safe.py --help")
        sys.exit(1)
    
    command = args[command_start:]
    if not command:
        print("ERROR: No command provided after '--'")
        sys.exit(1)
    
    # If command starts with 'pytest', convert to use pytest wrapper
    if command[0] == 'pytest':
        repo_root = find_repo_root()
        pytest_wrapper = repo_root / "tools" / "pytest.py"
        command = [sys.executable, str(pytest_wrapper)] + command[1:]
    elif not Path(command[0]).is_absolute() and not command[0].startswith('-'):
        # If first arg is not absolute and not a flag, try to find it
        # This handles cases like "python tools/pytest.py"
        pass  # Let subprocess handle it
    
    if metrics_file is None:
        # Default: create metrics file in repo root
        repo_root = find_repo_root()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metrics_file = repo_root / f"test_metrics_{timestamp}.jsonl"
    
    return max_seconds, max_rss_mb, metrics_file, command


def find_repo_root() -> Path:
    """Find repository root"""
    current = Path.cwd().resolve()
    for path in [current] + list(current.parents):
        if (path / "forge").exists():
            return path
    # Fallback to script location
    script_dir = Path(__file__).parent.parent.resolve()
    if (script_dir / "forge").exists():
        return script_dir
    return Path.cwd()


def check_limits(monitor: ResourceMonitor, max_seconds: int, max_rss_mb: int) -> Optional[str]:
    """Check if limits are exceeded, return reason if so"""
    elapsed = time.time() - monitor.start_time
    if elapsed > max_seconds:
        return f"Time limit exceeded: {elapsed:.1f}s > {max_seconds}s"
    
    if monitor.metrics:
        latest = monitor.metrics[-1]
        rss = latest.get('rss_mb')
        if rss is not None and rss > max_rss_mb:
            return f"Memory limit exceeded: {rss:.1f}MB > {max_rss_mb}MB"
    
    return None


def main():
    """Main entry point"""
    max_seconds, max_rss_mb, metrics_file, command = parse_args()
    
    repo_root = find_repo_root()
    os.chdir(repo_root)
    
    # Set environment for faulthandler
    if not FAULTHANDLER_ENABLED:
        os.environ['PYTHONFAULTHANDLER'] = '1'
    
    print("=" * 70)
    print("SAFE TEST RUNNER")
    print("=" * 70)
    print(f"Command: {' '.join(command)}")
    print(f"Time limit: {max_seconds}s")
    print(f"Memory limit: {max_rss_mb}MB")
    print(f"Metrics file: {metrics_file}")
    print(f"Faulthandler: {'enabled' if FAULTHANDLER_ENABLED else 'via env var'}")
    print("=" * 70)
    print()
    
    # Start the process - don't capture output to avoid deadlocks
    # Instead, let it inherit stdout/stderr so output appears in real-time
    # For long runs, add progress indicators if not already present
    command_str = ' '.join(command).lower()
    is_likely_long_run = (
        'pytest' in command_str and 
        ('forge/tests' in ' '.join(command) or 
         'tests/' in ' '.join(command) or
         len([a for a in command if not a.startswith('-') and not a.startswith('--')]) == 0)
    )
    
    # Add progress options for long runs if not already specified
    if is_likely_long_run and '-v' not in command and '--verbose' not in command and '-q' not in command:
        # Find where to insert (after python executable and pytest script, before other args)
        # Command format: [python, 'tools/pytest.py', ...args]
        insert_idx = 2  # After python and pytest.py
        if insert_idx < len(command):
            command.insert(insert_idx, '-v')
            command.insert(insert_idx + 1, '--durations=10')
    
    try:
        process = subprocess.Popen(
            command,
            cwd=repo_root,
            stdout=None,  # Inherit stdout (print to terminal)
            stderr=None,  # Inherit stderr (print to terminal)
            text=True
        )
    except Exception as e:
        print(f"ERROR: Failed to start process: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Start monitoring
    monitor = ResourceMonitor(process, metrics_file)
    monitor_thread = threading.Thread(target=monitor.monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Check limits periodically
    limit_check_interval = 5.0  # Check every 5 seconds
    last_check = time.time()
    
    try:
        # Wait for process and check limits
        while process.poll() is None:
            time.sleep(0.5)
            
            # Check limits periodically
            if time.time() - last_check >= limit_check_interval:
                reason = check_limits(monitor, max_seconds, max_rss_mb)
                if reason:
                    print(f"\n⚠️  LIMIT EXCEEDED: {reason}", file=sys.stderr)
                    print("Terminating process...", file=sys.stderr)
                    
                    # Try graceful termination first
                    try:
                        if sys.platform == 'win32':
                            process.terminate()
                        else:
                            process.send_signal(signal.SIGTERM)
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill
                        print("Force killing process...", file=sys.stderr)
                        process.kill()
                        process.wait()
                    
                    monitor.stop()
                    print_metrics_summary(monitor, metrics_file)
                    sys.exit(124)  # Exit code 124 = resource limit exceeded
                
                last_check = time.time()
        
        # Process finished normally
        monitor.stop()
        monitor_thread.join(timeout=2.0)
        
        # Print summary
        print()
        print("=" * 70)
        print("PROCESS COMPLETED")
        print("=" * 70)
        print_metrics_summary(monitor, metrics_file)
        print("=" * 70)
        
        sys.exit(process.returncode)
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user", file=sys.stderr)
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        monitor.stop()
        print_metrics_summary(monitor, metrics_file)
        sys.exit(130)  # Exit code 130 = interrupted
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        try:
            process.kill()
        except:
            pass
        monitor.stop()
        sys.exit(1)


def print_metrics_summary(monitor: ResourceMonitor, metrics_file: Path):
    """Print summary of metrics"""
    summary = monitor.get_summary()
    if summary:
        print(f"Duration: {summary.get('duration_seconds', 0):.1f}s")
        if 'rss_mb' in summary:
            rss = summary['rss_mb']
            print(f"Memory (RSS): min={rss['min']:.1f}MB, max={rss['max']:.1f}MB, "
                  f"avg={rss['avg']:.1f}MB, final={rss['final']:.1f}MB")
        if 'cpu_percent' in summary:
            cpu = summary['cpu_percent']
            print(f"CPU: min={cpu['min']:.1f}%, max={cpu['max']:.1f}%, avg={cpu['avg']:.1f}%")
        print(f"Metrics logged to: {metrics_file}")
    else:
        print("No metrics collected")


if __name__ == "__main__":
    main()
