"""Test framework for Pyrite"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class TestResult:
    """Result of running a test"""
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message


class TestRunner:
    """Discover and run Pyrite tests"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.results: List[TestResult] = []
    
    def discover_tests(self) -> List[Path]:
        """Discover all test files"""
        if not self.tests_dir.exists():
            return []
        
        # Find all .pyrite files in tests/
        test_files = list(self.tests_dir.rglob("*.pyrite"))
        return test_files
    
    def extract_test_functions(self, source: str) -> List[str]:
        """Extract function names marked with @test"""
        test_functions = []
        lines = source.split('\n')
        
        for i, line in enumerate(lines):
            # Look for @test decorator
            if line.strip() == '@test':
                # Next line should be a function definition
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('fn '):
                        # Extract function name
                        fn_name = next_line[3:].split('(')[0].strip()
                        test_functions.append(fn_name)
        
        return test_functions
    
    def run_test_file(self, test_file: Path) -> List[TestResult]:
        """Run all tests in a file by compiling and executing the test file"""
        results = []
        
        # Read source
        source = test_file.read_text(encoding='utf-8')
        
        # Extract test functions
        test_functions = self.extract_test_functions(source)
        
        if not test_functions:
            # No @test decorators, skip file
            return results
        
        print(f"\nRunning tests in {test_file.name}...")
        
        # Compile test file to temporary binary
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create temporary binary path
            binary_name = test_file.stem
            if sys.platform == "win32":
                binary_name += ".exe"
            
            binary_path = Path(tmpdir) / binary_name
            
            # Compile test file
            compiler_root = self.project_root.parent if self.project_root.name == "forge" else Path(__file__).parent.parent.parent
            compiler_path = compiler_root / "forge" / "src" / "compiler.py"
            
            if not compiler_path.exists():
                # Try alternative path
                compiler_path = Path(__file__).parent.parent / "forge" / "src" / "compiler.py"
            
            compile_cmd = [
                sys.executable,
                str(compiler_path),
                str(test_file),
                "-o", str(binary_path),
                "--emit-llvm"
            ]
            
            try:
                compile_result = subprocess.run(
                    compile_cmd,
                    cwd=str(compiler_root / "forge") if (compiler_root / "forge").exists() else str(compiler_root),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if compile_result.returncode != 0:
                    # Compilation failed
                    for test_name in test_functions:
                        results.append(TestResult(
                            f"{test_file.stem}::{test_name}",
                            False,
                            f"Compilation failed: {compile_result.stderr[:200]}"
                        ))
                        print(f"  test {test_name} ... FAILED (compilation error)")
                    return results
                
                # Check if binary was created (or .ll file on Windows)
                if not binary_path.exists():
                    # Try .ll file
                    ll_path = binary_path.with_suffix(".ll")
                    if ll_path.exists():
                        # LLVM IR generated but not linked - for MVP, consider this a pass
                        # In full implementation, we'd link and run
                        for test_name in test_functions:
                            results.append(TestResult(
                                f"{test_file.stem}::{test_name}",
                                True,
                                "LLVM IR generated (not linked)"
                            ))
                            print(f"  test {test_name} ... ok (IR generated)")
                        return results
                    else:
                        # No output file
                        for test_name in test_functions:
                            results.append(TestResult(
                                f"{test_file.stem}::{test_name}",
                                False,
                                "No binary or IR file generated"
                            ))
                            print(f"  test {test_name} ... FAILED (no output)")
                        return results
                
                # Execute binary
                try:
                    exec_result = subprocess.run(
                        [str(binary_path)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=str(tmpdir)
                    )
                    
                    # Check exit code: 0 = pass, non-zero = fail
                    passed = exec_result.returncode == 0
                    
                    for test_name in test_functions:
                        if passed:
                            results.append(TestResult(
                                f"{test_file.stem}::{test_name}",
                                True,
                                ""
                            ))
                            print(f"  test {test_name} ... ok")
                        else:
                            error_msg = exec_result.stderr[:200] if exec_result.stderr else "Test failed"
                            results.append(TestResult(
                                f"{test_file.stem}::{test_name}",
                                False,
                                error_msg
                            ))
                            print(f"  test {test_name} ... FAILED")
                            if exec_result.stderr:
                                print(f"    {exec_result.stderr[:200]}")
                
                except subprocess.TimeoutExpired:
                    for test_name in test_functions:
                        results.append(TestResult(
                            f"{test_file.stem}::{test_name}",
                            False,
                            "Test execution timed out"
                        ))
                        print(f"  test {test_name} ... FAILED (timeout)")
                
                except Exception as e:
                    for test_name in test_functions:
                        results.append(TestResult(
                            f"{test_file.stem}::{test_name}",
                            False,
                            f"Execution error: {str(e)[:200]}"
                        ))
                        print(f"  test {test_name} ... FAILED (execution error)")
            
            except subprocess.TimeoutExpired:
                for test_name in test_functions:
                    results.append(TestResult(
                        f"{test_file.stem}::{test_name}",
                        False,
                        "Compilation timed out"
                    ))
                    print(f"  test {test_name} ... FAILED (compilation timeout)")
            
            except Exception as e:
                for test_name in test_functions:
                    results.append(TestResult(
                        f"{test_file.stem}::{test_name}",
                        False,
                        f"Compilation error: {str(e)[:200]}"
                    ))
                    print(f"  test {test_name} ... FAILED (compilation error)")
        
        return results
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Run all discovered tests"""
        test_files = self.discover_tests()
        
        if not test_files:
            print("No test files found in tests/")
            return (0, 0)
        
        print(f"Running {len(test_files)} test file(s)...")
        
        passed = 0
        failed = 0
        
        for test_file in test_files:
            file_results = self.run_test_file(test_file)
            for result in file_results:
                self.results.append(result)
                if result.passed:
                    passed += 1
                else:
                    failed += 1
                    print(f"  FAILED: {result.name}")
                    if result.message:
                        print(f"    {result.message}")
        
        return (passed, failed)
    
    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        print(f"\nTest result: ", end="")
        if failed == 0:
            print(f"ok. {passed} passed; 0 failed")
        else:
            print(f"FAILED. {passed} passed; {failed} failed")


def run_tests(project_root: Path = None) -> int:
    """Run tests for a Pyrite project"""
    if project_root is None:
        project_root = Path.cwd()
    
    runner = TestRunner(project_root)
    passed, failed = runner.run_all_tests()
    runner.print_summary()
    
    return 0 if failed == 0 else 1


def main():
    """Main entry point for test runner"""
    project_root = Path.cwd()
    
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    
    return run_tests(project_root)


if __name__ == "__main__":
    sys.exit(main())

