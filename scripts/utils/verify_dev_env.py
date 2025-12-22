#!/usr/bin/env python3
"""
Development Environment Verification Script

Verifies that the dev environment is properly set up to resume execution
of the self-hosting plan (SELF_HOSTING_PLAN_DELTA.md).

Checks:
1. Python version and dependencies
2. Test infrastructure
3. Coverage tools
4. Compiler functionality
5. Bootstrap scripts
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def check_mark(passed: bool) -> str:
    """Return checkmark or X based on status"""
    # Use ASCII-safe characters for Windows compatibility
    return f"{GREEN}[OK]{RESET}" if passed else f"{RED}[FAIL]{RESET}"

def print_header(text: str):
    """Print a section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def check_python_version() -> Tuple[bool, str]:
    """Check Python version is 3.9+"""
    try:
        version = sys.version_info
        if version.major == 3 and version.minor >= 9:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        return False, f"Python {version.major}.{version.minor}.{version.micro} (need 3.9+)"
    except Exception as e:
        return False, f"Error checking version: {e}"

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check required dependencies are installed"""
    required = {
        'pytest': 'pytest>=7.0.0',
        'pytest_cov': 'pytest-cov>=4.0.0',
        'llvmlite': 'llvmlite>=0.40.0',
    }
    missing = []
    
    for module, requirement in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(requirement)
    
    return len(missing) == 0, missing

def check_test_infrastructure() -> Tuple[bool, str]:
    """Check test infrastructure works"""
    try:
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        pytest_script = repo_root / "tools" / "pytest.py"
        
        if not pytest_script.exists():
            return False, "tools/pytest.py not found"
        
        # Try to run pytest --version
        result = subprocess.run(
            [sys.executable, str(pytest_script), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "Test infrastructure OK"
        return False, f"pytest script failed: {result.stderr}"
    except Exception as e:
        return False, f"Error: {e}"

def check_compiler() -> Tuple[bool, str]:
    """Check compiler can compile a simple program"""
    try:
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        compiler_dir = repo_root / "forge"
        example_file = compiler_dir / "examples" / "hello.pyrite"
        
        if not example_file.exists():
            return False, "examples/hello.pyrite not found"
        
        # Try to compile
        result = subprocess.run(
            [sys.executable, "-m", "src.compiler", str(example_file), "-o", "test_verify.out"],
            cwd=compiler_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Clean up
            test_out = compiler_dir / "test_verify.out"
            if test_out.exists():
                test_out.unlink()
            test_obj = compiler_dir / "test_verify.out.o"
            if test_obj.exists():
                test_obj.unlink()
            return True, "Compiler works"
        return False, f"Compilation failed: {result.stderr[:200]}"
    except Exception as e:
        return False, f"Error: {e}"

def check_coverage_tools() -> Tuple[bool, str]:
    """Check coverage tools are available"""
    try:
        import coverage
        return True, "Coverage tools available"
    except ImportError:
        return False, "coverage module not found (install pytest-cov)"

def check_bootstrap_scripts() -> Tuple[bool, List[str]]:
    """Check bootstrap scripts exist"""
    script_dir = Path(__file__).parent
    required_scripts = [
        "bootstrap_stage1.py",
        "bootstrap_stage2.py",
        "check_bootstrap_determinism.py",
    ]
    missing = []
    
    for script in required_scripts:
        if not (script_dir / script).exists():
            missing.append(script)
    
    return len(missing) == 0, missing

# CI workflows check removed - workflows are no longer used

def check_pyrite_modules() -> Tuple[bool, int]:
    """Check existing Pyrite compiler modules"""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    src_pyrite = repo_root / "forge" / "src-pyrite"
    
    if not src_pyrite.exists():
        return False, 0
    
    pyrite_files = list(src_pyrite.glob("*.pyrite"))
    return True, len(pyrite_files)

def main():
    """Run all checks"""
    print_header("Pyrite Development Environment Verification")
    
    all_passed = True
    results = []
    
    # Python version
    print("Checking Python version...")
    passed, msg = check_python_version()
    print(f"  {check_mark(passed)} {msg}")
    results.append(("Python Version", passed))
    if not passed:
        all_passed = False
    
    # Dependencies
    print("\nChecking dependencies...")
    passed, missing = check_dependencies()
    if passed:
        print(f"  {check_mark(True)} All dependencies installed")
    else:
        print(f"  {check_mark(False)} Missing: {', '.join(missing)}")
        print(f"    Install with: pip install -r forge/requirements.txt")
    results.append(("Dependencies", passed))
    if not passed:
        all_passed = False
    
    # Test infrastructure
    print("\nChecking test infrastructure...")
    passed, msg = check_test_infrastructure()
    print(f"  {check_mark(passed)} {msg}")
    results.append(("Test Infrastructure", passed))
    if not passed:
        all_passed = False
    
    # Compiler
    print("\nChecking compiler...")
    passed, msg = check_compiler()
    print(f"  {check_mark(passed)} {msg}")
    results.append(("Compiler", passed))
    if not passed:
        all_passed = False
    
    # Coverage tools
    print("\nChecking coverage tools...")
    passed, msg = check_coverage_tools()
    print(f"  {check_mark(passed)} {msg}")
    results.append(("Coverage Tools", passed))
    if not passed:
        all_passed = False
    
    # Bootstrap scripts
    print("\nChecking bootstrap scripts...")
    passed, missing = check_bootstrap_scripts()
    if passed:
        print(f"  {check_mark(True)} All bootstrap scripts exist")
    else:
        print(f"  {check_mark(False)} Missing: {', '.join(missing)}")
    results.append(("Bootstrap Scripts", passed))
    if not passed:
        all_passed = False
    
    # CI workflows check removed - workflows are no longer used
    if not passed:
        all_passed = False
    
    # Pyrite modules
    print("\nChecking Pyrite compiler modules...")
    passed, count = check_pyrite_modules()
    if passed:
        print(f"  {check_mark(True)} Found {count} Pyrite module(s) in src-pyrite/")
        if count == 0:
            print(f"    {YELLOW}Note: This is expected - modules will be created during migration{RESET}")
    else:
        print(f"  {check_mark(False)} src-pyrite/ directory not found")
    results.append(("Pyrite Modules", passed))
    
    # Summary
    print_header("Summary")
    for name, passed in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status} {name}")
    
    print()
    if all_passed:
        print(f"{GREEN}[PASS] All critical checks passed!{RESET}")
        print(f"\n{YELLOW}Next steps:{RESET}")
        print("  1. Review SELF_HOSTING_PLAN_DELTA.md for execution plan")
        print("  2. Start with Milestone A: Make Coverage a Real Gate (SH-A-T1)")
        print("  3. Run tests: python tools/pytest.py")
        print("  4. Check coverage: python tools/pytest.py --cov=forge/src --cov-report=term")
        print(f"\n{YELLOW}Note on coverage commands:{RESET}")
        print("  - Full coverage with JSON report takes ~3-4 minutes (1108 tests)")
        print("  - For quick local checks, skip JSON: --cov-report=term only")
        print("  - For CI/full reports, use: --cov-report=term --cov-report=json")
        print("  - If command times out, it's likely due to large test suite size")
        return 0
    else:
        print(f"{RED}[FAIL] Some checks failed. Please fix issues above before proceeding.{RESET}")
        print(f"\n{YELLOW}Common fixes:{RESET}")
        print("  - Install dependencies: pip install -r forge/requirements.txt")
        print("  - Ensure you're in the repository root")
        print("  - Check Python version: python --version (need 3.9+)")
        return 1

if __name__ == "__main__":
    sys.exit(main())

