"""Performance lockfile system - enforce "fast forever" """

import sys
import json
import time
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class FunctionProfile:
    """Performance profile for a function"""
    name: str
    time_ms: float
    time_percent: float
    call_count: int
    alloc_sites: int
    simd_width: Optional[int] = None  # SIMD vectorization width
    inlined_calls: Optional[int] = None  # Number of inlined call sites
    stack_bytes: Optional[int] = None  # Stack usage


@dataclass
class PerformanceLockfile:
    """Performance baseline for regression detection"""
    version: str
    generated: str
    build_config: str
    platform: str
    hot_functions: List[FunctionProfile]
    total_time_ms: float
    
    def to_dict(self) -> Dict:
        return {
            'version': self.version,
            'generated': self.generated,
            'build_config': self.build_config,
            'platform': self.platform,
            'hot_functions': [asdict(f) for f in self.hot_functions],
            'total_time_ms': self.total_time_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PerformanceLockfile':
        # Handle optional fields in FunctionProfile
        functions = []
        for f in data['hot_functions']:
            func_data = {
                'name': f['name'],
                'time_ms': f['time_ms'],
                'time_percent': f['time_percent'],
                'call_count': f.get('call_count', 0),
                'alloc_sites': f.get('alloc_sites', 0),
            }
            # Add optional fields if present
            if 'simd_width' in f:
                func_data['simd_width'] = f['simd_width']
            if 'inlined_calls' in f:
                func_data['inlined_calls'] = f['inlined_calls']
            if 'stack_bytes' in f:
                func_data['stack_bytes'] = f['stack_bytes']
            functions.append(FunctionProfile(**func_data))
        
        return cls(
            version=data['version'],
            generated=data['generated'],
            build_config=data['build_config'],
            platform=data['platform'],
            hot_functions=functions,
            total_time_ms=data['total_time_ms']
        )


class PerformanceProfiler:
    """Profile code performance"""
    
    def __init__(self):
        self.platform = platform.system().lower()
    
    def profile_binary(self, binary_path: Path) -> Optional[PerformanceLockfile]:
        """Profile a binary and generate lockfile"""
        if not binary_path.exists():
            print(f"Error: Binary not found: {binary_path}")
            return None
        
        print("Profiling binary...")
        
        # Try platform-specific profilers
        lockfile = None
        if self.platform == "linux":
            lockfile = self._profile_linux(binary_path)
        elif self.platform == "darwin":
            lockfile = self._profile_macos(binary_path)
        elif self.platform == "windows":
            lockfile = self._profile_windows(binary_path)
        else:
            # Fallback: simple timing
            lockfile = self._profile_simple(binary_path)
        
        # Try to extract optimization decisions from binary
        if lockfile:
            self._extract_optimizations(binary_path, lockfile)
        
        return lockfile
    
    def _profile_linux(self, binary_path: Path) -> Optional[PerformanceLockfile]:
        """Profile using Linux perf"""
        try:
            # Check if perf is available
            result = subprocess.run(
                ['perf', '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                print("Warning: perf not available, using simple timing")
                return self._profile_simple(binary_path)
            
            # Run perf record with better options
            perf_data = Path("perf.data")
            print("Running perf record...")
            result = subprocess.run(
                ['perf', 'record', '-g', '--call-graph', 'dwarf', '-F', '1000', 
                 '-o', str(perf_data), '--', str(binary_path)],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"Warning: perf record failed: {result.stderr.decode()}")
                return self._profile_simple(binary_path)
            
            # Parse perf report with better options
            print("Parsing perf data...")
            result = subprocess.run(
                ['perf', 'report', '--stdio', '--no-children', '-i', str(perf_data)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                print(f"Warning: perf report failed: {result.stderr.decode()}")
                return self._profile_simple(binary_path)
            
            # Parse perf output to extract function timings
            functions = self._parse_perf_report(result.stdout)
            
            # Try to get actual execution time from perf stat
            total_time = 1000  # Default
            try:
                stat_result = subprocess.run(
                    ['perf', 'stat', '-x', ',', str(binary_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if stat_result.returncode == 0:
                    # Parse "task-clock" or "duration_time" from output
                    for line in stat_result.stdout.split('\n'):
                        if 'task-clock' in line or 'duration_time' in line:
                            parts = line.split(',')
                            if len(parts) >= 1:
                                try:
                                    # Value is in milliseconds
                                    total_time = float(parts[0].strip())
                                    break
                                except ValueError:
                                    pass
            except Exception:
                pass
            
            # If we couldn't get real time, estimate from percentages
            if total_time == 1000 and functions:
                # Use the function with highest percentage to estimate
                max_func = max(functions, key=lambda f: f.time_percent)
                if max_func.time_percent > 0:
                    total_time = (max_func.time_ms / max_func.time_percent) * 100
            
            # Calculate percentages
            for func in functions:
                func.time_percent = (func.time_ms / total_time) * 100 if total_time > 0 else 0
            
            lockfile = PerformanceLockfile(
                version="1.0",
                generated=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                build_config="release",
                platform="linux",
                hot_functions=functions[:20],  # Top 20 functions
                total_time_ms=total_time
            )
            
            # Try to generate flamegraph
            try:
                self._generate_flamegraph(perf_data, Path("flamegraph.svg"))
            except Exception as e:
                print(f"Note: Could not generate flamegraph: {e}")
            
            # Clean up
            if perf_data.exists():
                perf_data.unlink()
            
            return lockfile
            
        except FileNotFoundError:
            print("Warning: perf not found, using simple timing")
            return self._profile_simple(binary_path)
        except Exception as e:
            print(f"Warning: perf profiling failed: {e}, using simple timing")
            return self._profile_simple(binary_path)
    
    def _parse_perf_report(self, perf_output: str) -> List[FunctionProfile]:
        """Parse perf report output to extract function profiles"""
        functions = []
        lines = perf_output.split('\n')
        
        # Track total samples for better time estimation
        total_samples = 0
        sample_rate = 1000  # Default: 1000 Hz
        
        for line in lines:
            # Perf report format examples:
            # "  34.23%  main  program  [.] process_data"
            # "  12.45%  1234  main  [.] function_name"
            if '%' in line and '[' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        percent = float(parts[0].rstrip('%'))
                        
                        # Find function name - it's usually before the [.] marker
                        func_name = "unknown"
                        for i, part in enumerate(parts):
                            if part.startswith('[') and '.' in part:
                                # Function name is usually the part before this
                                if i > 0:
                                    func_name = parts[i-1]
                                break
                        
                        # If we couldn't find it, try the last part before [
                        if func_name == "unknown" and len(parts) >= 2:
                            for i in range(len(parts)-1, -1, -1):
                                if '[' in parts[i]:
                                    if i > 0:
                                        func_name = parts[i-1]
                                    break
                        
                        # Estimate time (will be refined with total time)
                        time_ms = percent * 10  # Rough estimate
                        
                        functions.append(FunctionProfile(
                            name=func_name,
                            time_ms=time_ms,
                            time_percent=percent,
                            call_count=0,
                            alloc_sites=0
                        ))
                    except (ValueError, IndexError):
                        continue
        
        return sorted(functions, key=lambda f: f.time_ms, reverse=True)
    
    def _generate_flamegraph(self, perf_data: Path, output_path: Path) -> None:
        """Generate flamegraph SVG from perf data"""
        try:
            # Try to use perf script + stackcollapse + flamegraph.pl
            # First check if we can use perf script
            script_output = Path("perf.script")
            result = subprocess.run(
                ['perf', 'script', '-i', str(perf_data)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Write script output
                script_output.write_text(result.stdout)
                
                # Try to use flamegraph.pl if available
                # Check common locations
                flamegraph_paths = [
                    'flamegraph.pl',
                    '/usr/local/bin/flamegraph.pl',
                    '/usr/bin/flamegraph.pl',
                    '~/.cargo/bin/flamegraph',
                ]
                
                flamegraph_cmd = None
                for path in flamegraph_paths:
                    expanded = Path(path).expanduser()
                    if expanded.exists() and expanded.is_file():
                        flamegraph_cmd = str(expanded)
                        break
                
                if flamegraph_cmd:
                    # Use flamegraph.pl
                    result = subprocess.run(
                        [flamegraph_cmd, str(script_output)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        output_path.write_text(result.stdout)
                        print(f"✓ Flamegraph generated: {output_path}")
                    else:
                        print(f"Warning: flamegraph.pl failed: {result.stderr}")
                else:
                    # Generate simple SVG manually
                    self._generate_simple_flamegraph(script_output, output_path)
                
                # Clean up
                if script_output.exists():
                    script_output.unlink()
        except FileNotFoundError:
            # perf script not available, skip flamegraph
            pass
        except Exception as e:
            print(f"Warning: Flamegraph generation failed: {e}")
    
    def _generate_simple_flamegraph(self, script_file: Path, output_path: Path) -> None:
        """Generate a simple flamegraph SVG from perf script output"""
        # Parse perf script output to build call stack
        stacks = {}  # stack -> count
        
        try:
            content = script_file.read_text()
            for line in content.split('\n'):
                if not line.strip():
                    continue
                # Simple parsing: extract function names from stack traces
                # This is a simplified version - full implementation would parse properly
                parts = line.split()
                if len(parts) > 0:
                    # Extract function names (simplified)
                    stack_key = ';'.join(parts[:5])  # First 5 parts as stack
                    stacks[stack_key] = stacks.get(stack_key, 0) + 1
        except Exception:
            return
        
        if not stacks:
            return
        
        # Generate simple SVG
        svg_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800">',
            '<style>',
            '  .frame { fill: #1e90ff; stroke: #000; }',
            '  .frame:hover { fill: #4169e1; }',
            '</style>',
        ]
        
        # Simple bar chart representation
        max_count = max(stacks.values()) if stacks else 1
        y = 20
        for stack, count in sorted(stacks.items(), key=lambda x: x[1], reverse=True)[:50]:
            width = (count / max_count) * 1000
            svg_lines.append(
                f'<rect class="frame" x="10" y="{y}" width="{width}" height="15" />'
            )
            svg_lines.append(
                f'<text x="15" y="{y+12}" font-size="10">{stack[:50]}</text>'
            )
            y += 20
        
        svg_lines.append('</svg>')
        output_path.write_text('\n'.join(svg_lines))
        print(f"✓ Simple flamegraph generated: {output_path}")
    
    def _extract_optimizations(self, binary_path: Path, lockfile: PerformanceLockfile) -> None:
        """Extract optimization decisions (SIMD width, inlining) from binary"""
        # This is a placeholder - full implementation would:
        # 1. Use objdump/readelf to extract assembly
        # 2. Detect SIMD instructions (SSE, AVX, NEON)
        # 3. Detect inlined functions (no call instructions)
        # 4. Map back to source functions
        
        # For now, we'll try to detect SIMD width from objdump if available
        if self.platform == "linux":
            try:
                result = subprocess.run(
                    ['objdump', '-d', str(binary_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Look for SIMD instructions
                    asm = result.stdout
                    for func in lockfile.hot_functions:
                        # Count SIMD instructions (simplified detection)
                        # Look for function name in assembly
                        func_asm = []
                        in_func = False
                        for line in asm.split('\n'):
                            if func.name in line and '<' in line and '>:' in line:
                                in_func = True
                            elif in_func and (line.strip().startswith('ret') or 
                                            (line.strip() and not line.strip()[0].isspace() and ':' in line)):
                                if line.strip().startswith('ret'):
                                    break
                                in_func = False
                            
                            if in_func:
                                func_asm.append(line)
                        
                        # Detect SIMD width from instructions
                        simd_width = None
                        func_asm_str = '\n'.join(func_asm)
                        if 'vpxor' in func_asm_str or 'vmovdqa' in func_asm_str:
                            # AVX-512 (512-bit = 64 bytes = 8x int64)
                            if 'zmm' in func_asm_str:
                                simd_width = 8
                            # AVX-256 (256-bit = 32 bytes = 4x int64)
                            elif 'ymm' in func_asm_str:
                                simd_width = 4
                            # SSE (128-bit = 16 bytes = 2x int64)
                            elif 'xmm' in func_asm_str:
                                simd_width = 2
                        
                        if simd_width:
                            func.simd_width = simd_width
                        
                        # Detect inlining (no call instructions in function)
                        if func_asm and 'call' not in func_asm_str.lower():
                            # Function appears to be inlined (no calls)
                            # Count how many times this function appears inlined
                            # This is simplified - would need call graph analysis
                            func.inlined_calls = 1  # Placeholder
            except FileNotFoundError:
                pass
            except Exception:
                pass
    
    def _profile_macos(self, binary_path: Path) -> Optional[PerformanceLockfile]:
        """Profile using macOS Instruments (dtrace)"""
        # Try using dtrace or sample command
        try:
            # Use sample command (built-in macOS profiler)
            sample_output = Path("sample.txt")
            print("Running sample profiler...")
            result = subprocess.run(
                ['sample', str(binary_path), '1', '-f', str(sample_output)],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and sample_output.exists():
                # Parse sample output
                functions = self._parse_sample_output(sample_output.read_text())
                
                total_time = sum(f.time_ms for f in functions) if functions else 1000
                if total_time == 0:
                    total_time = 1000
                
                for func in functions:
                    func.time_percent = (func.time_ms / total_time) * 100 if total_time > 0 else 0
                
                lockfile = PerformanceLockfile(
                    version="1.0",
                    generated=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    build_config="release",
                    platform="darwin",
                    hot_functions=functions[:20],
                    total_time_ms=total_time
                )
                
                sample_output.unlink()
                return lockfile
        except Exception as e:
            print(f"Warning: macOS profiling failed: {e}, using simple timing")
        
        return self._profile_simple(binary_path)
    
    def _parse_sample_output(self, sample_output: str) -> List[FunctionProfile]:
        """Parse macOS sample command output"""
        functions = []
        lines = sample_output.split('\n')
        
        for line in lines:
            # Sample output format varies, try to extract function names and percentages
            if '%' in line and ('[' in line or '0x' in line):
                parts = line.split()
                try:
                    # Look for percentage
                    for part in parts:
                        if '%' in part:
                            percent = float(part.rstrip('%'))
                            # Find function name (usually before address or after percentage)
                            func_name = "unknown"
                            for i, p in enumerate(parts):
                                if p == part and i + 1 < len(parts):
                                    func_name = parts[i + 1]
                                    break
                            
                            if func_name != "unknown":
                                functions.append(FunctionProfile(
                                    name=func_name,
                                    time_ms=percent * 10,  # Estimate
                                    time_percent=percent,
                                    call_count=0,
                                    alloc_sites=0
                                ))
                            break
                except (ValueError, IndexError):
                    continue
        
        return sorted(functions, key=lambda f: f.time_ms, reverse=True)
    
    def _profile_windows(self, binary_path: Path) -> Optional[PerformanceLockfile]:
        """Profile using Windows ETW or WPR"""
        # Try using Windows Performance Recorder (WPR) if available
        try:
            # Check if wpr.exe is available
            result = subprocess.run(
                ['wpr', '-?'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0 or 'Windows Performance Recorder' in result.stderr.decode('utf-8', errors='ignore'):
                print("Note: WPR detected but full integration requires ETW analysis tools")
                print("Falling back to simple timing for now")
        except FileNotFoundError:
            pass
        except Exception:
            pass
        
        # For now, fall back to simple timing
        # Full ETW integration would require:
        # 1. WPR to record ETW events
        # 2. WPA (Windows Performance Analyzer) or custom parser to analyze
        # 3. Extract function timings from ETW call stacks
        print("Warning: Windows profiling not fully implemented, using simple timing")
        return self._profile_simple(binary_path)
    
    def _profile_simple(self, binary_path: Path) -> Optional[PerformanceLockfile]:
        """Simple profiling using timing"""
        # Ensure we have an absolute path
        binary_path = binary_path.resolve()
        
        start = time.time()
        try:
            result = subprocess.run(
                [str(binary_path)],
                capture_output=True,
                timeout=10,
                cwd=binary_path.parent  # Run from binary's directory
            )
            elapsed = time.time() - start
        except Exception as e:
            print(f"Error running binary: {e}")
            return None
        
        # Create basic profile
        lockfile = PerformanceLockfile(
            version="1.0",
            generated=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            build_config="debug",
            platform=sys.platform,
            hot_functions=[
                FunctionProfile(
                    name="main",
                    time_ms=elapsed * 1000,
                    time_percent=100.0,
                    call_count=1,
                    alloc_sites=0
                )
            ],
            total_time_ms=elapsed * 1000
        )
        
        return lockfile
    
    def check_regression(self, current: PerformanceLockfile, baseline: PerformanceLockfile, threshold: float = 5.0) -> bool:
        """Check for performance regression"""
        print(f"\nChecking performance against baseline (threshold: {threshold}%)")
        print("=" * 60)
        
        regressions = []
        
        # Compare total time
        time_change = ((current.total_time_ms - baseline.total_time_ms) / baseline.total_time_ms) * 100
        
        if time_change > threshold:
            print(f"\n🔴 REGRESSION: Total time increased by {time_change:.1f}%")
            print(f"   Baseline: {baseline.total_time_ms:.1f}ms")
            print(f"   Current:  {current.total_time_ms:.1f}ms")
            regressions.append(("total_time", time_change))
        elif time_change < -threshold:
            print(f"\n✅ IMPROVEMENT: Total time decreased by {abs(time_change):.1f}%")
            print(f"   Baseline: {baseline.total_time_ms:.1f}ms")
            print(f"   Current:  {current.total_time_ms:.1f}ms")
        else:
            print(f"\n✓ Performance stable (change: {time_change:+.1f}%)")
        
        # Compare individual functions
        baseline_funcs = {f.name: f for f in baseline.hot_functions}
        current_funcs = {f.name: f for f in current.hot_functions}
        
        function_regressions = []
        for func_name, current_func in current_funcs.items():
            if func_name in baseline_funcs:
                baseline_func = baseline_funcs[func_name]
                func_change = ((current_func.time_ms - baseline_func.time_ms) / baseline_func.time_ms) * 100
                
                if func_change > threshold:
                    function_regressions.append((func_name, func_change, baseline_func, current_func))
        
        if function_regressions:
            print(f"\n🔴 Function-level regressions:")
            for func_name, change, baseline_func, current_func in function_regressions:
                print(f"   • {func_name}: {change:+.1f}% slower")
                print(f"     Baseline: {baseline_func.time_ms:.1f}ms ({baseline_func.time_percent:.1f}%)")
                print(f"     Current:  {current_func.time_ms:.1f}ms ({current_func.time_percent:.1f}%)")
                regressions.append((func_name, change))
        
        return len(regressions) == 0
    
    def explain_regression(self, current: PerformanceLockfile, baseline: PerformanceLockfile) -> List[str]:
        """Explain why a regression occurred (root cause analysis)"""
        explanations = []
        
        # Compare function timings
        baseline_funcs = {f.name: f for f in baseline.hot_functions}
        current_funcs = {f.name: f for f in current.hot_functions}
        
        for func_name, current_func in current_funcs.items():
            if func_name in baseline_funcs:
                baseline_func = baseline_funcs[func_name]
                change = ((current_func.time_ms - baseline_func.time_ms) / baseline_func.time_ms) * 100
                
                if change > 5.0:  # Regression threshold
                    # Check SIMD width changes
                    if baseline_func.simd_width and current_func.simd_width:
                        if baseline_func.simd_width != current_func.simd_width:
                            explanations.append(
                                f"{func_name}: SIMD width changed from {baseline_func.simd_width} to {current_func.simd_width}"
                            )
                    
                    # Check inlining changes
                    if baseline_func.inlined_calls is not None and current_func.inlined_calls is not None:
                        if baseline_func.inlined_calls > current_func.inlined_calls:
                            explanations.append(
                                f"{func_name}: Inlining decreased from {baseline_func.inlined_calls} to {current_func.inlined_calls} call sites"
                            )
                    
                    # Check allocation changes
                    if current_func.alloc_sites > baseline_func.alloc_sites:
                        explanations.append(
                            f"{func_name}: Allocation sites increased from {baseline_func.alloc_sites} to {current_func.alloc_sites}"
                        )
        
        return explanations


def cmd_perf_baseline():
    """Generate performance baseline (Perf.lock)"""
    binary_path = Path("target/release/main").resolve()
    if not binary_path.exists():
        binary_path = Path("target/debug/main").resolve()
    
    if not binary_path.exists():
        print("Error: No binary found. Run 'quarry build' first.")
        return 1
    
    profiler = PerformanceProfiler()
    lockfile = profiler.profile_binary(binary_path)
    
    if not lockfile:
        return 1
    
    # Save to Perf.lock
    perf_lock_path = Path("Perf.lock")
    perf_lock_path.write_text(json.dumps(lockfile.to_dict(), indent=2))
    
    print(f"\n✓ Performance baseline saved to Perf.lock")
    print(f"  Total time: {lockfile.total_time_ms:.1f}ms")
    print(f"  Functions profiled: {len(lockfile.hot_functions)}")
    
    return 0


def cmd_perf_check(threshold: float = 5.0):
    """Check performance against baseline"""
    # Load baseline
    perf_lock_path = Path("Perf.lock")
    if not perf_lock_path.exists():
        print("Error: Perf.lock not found. Run 'quarry perf --baseline' first.")
        return 1
    
    try:
        baseline_data = json.loads(perf_lock_path.read_text())
        baseline = PerformanceLockfile.from_dict(baseline_data)
    except Exception as e:
        print(f"Error loading Perf.lock: {e}")
        return 1
    
    # Profile current binary
    binary_path = Path("target/release/main")
    if not binary_path.exists():
        binary_path = Path("target/debug/main")
    
    if not binary_path.exists():
        print("Error: No binary found. Run 'quarry build' first.")
        return 1
    
    profiler = PerformanceProfiler()
    current = profiler.profile_binary(binary_path)
    
    if not current:
        return 1
    
    # Check for regressions
    no_regressions = profiler.check_regression(current, baseline, threshold)
    
    if no_regressions:
        print("\n✓ No performance regressions detected")
        return 0
    else:
        print("\n✗ Performance regressions detected")
        print("  CI should fail to prevent merging this change")
        return 1


def cmd_perf_diff_asm(function_name: str):
    """Show assembly diff for a function between baseline and current"""
    perf_lock_path = Path("Perf.lock")
    if not perf_lock_path.exists():
        print("Error: Perf.lock not found. Run 'quarry perf --baseline' first.")
        return 1
    
    print(f"Assembly diff for function: {function_name}")
    print("=" * 60)
    print()
    print("Note: Assembly diff requires objdump or similar tool.")
    print("This feature is not yet fully implemented.")
    print()
    print("To implement:")
    print("  1. Extract assembly for function from baseline binary")
    print("  2. Extract assembly for function from current binary")
    print("  3. Generate unified diff")
    print("  4. Highlight optimization differences")
    print()
    
    return 0


def cmd_perf_explain():
    """Explain performance regression root cause"""
    perf_lock_path = Path("Perf.lock")
    if not perf_lock_path.exists():
        print("Error: Perf.lock not found. Run 'quarry perf --baseline' first.")
        return 1
    
    try:
        baseline_data = json.loads(perf_lock_path.read_text())
        baseline = PerformanceLockfile.from_dict(baseline_data)
    except Exception as e:
        print(f"Error loading Perf.lock: {e}")
        return 1
    
    # Profile current binary
    binary_path = Path("target/release/main")
    if not binary_path.exists():
        binary_path = Path("target/debug/main")
    
    if not binary_path.exists():
        print("Error: No binary found. Run 'quarry build' first.")
        return 1
    
    profiler = PerformanceProfiler()
    current = profiler.profile_binary(binary_path)
    
    if not current:
        return 1
    
    # Check for regressions first
    has_regression = not profiler.check_regression(current, baseline, threshold=5.0)
    
    if has_regression:
        print("\n" + "=" * 60)
        print("Root Cause Analysis")
        print("=" * 60)
        
        explanations = profiler.explain_regression(current, baseline)
        
        if explanations:
            print("\nPossible causes:")
            for explanation in explanations:
                print(f"  • {explanation}")
        else:
            print("\nNo obvious optimization changes detected.")
            print("Regression may be due to:")
            print("  • Algorithm changes")
            print("  • Data structure changes")
            print("  • Compiler optimization differences")
            print("  • System load or environment differences")
    
    return 0


def cmd_perf(baseline: bool = False, check: bool = False, explain: bool = False, threshold: float = 5.0):
    """Performance profiling and regression detection"""
    if baseline:
        return cmd_perf_baseline()
    elif check:
        return cmd_perf_check(threshold)
    elif explain:
        return cmd_perf_explain()
    else:
        # Default: just profile
        return cmd_perf_baseline()


if __name__ == '__main__':
    import sys
    if '--baseline' in sys.argv:
        cmd_perf_baseline()
    elif '--check' in sys.argv:
        cmd_perf_check()
    elif '--explain' in sys.argv:
        cmd_perf_explain()
    else:
        cmd_perf_baseline()

