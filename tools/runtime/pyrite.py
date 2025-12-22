#!/usr/bin/env python3
"""
Pyrite compiler wrapper - works from anywhere in the repo
Auto-detects repo root and sets up paths correctly

Supports two modes:
1. Script mode (default): python tools/pyrite.py file.pyrite
   - Compiles and runs the file immediately
   
2. Compiler mode (when flags present): python tools/pyrite.py file.pyrite -o output.exe
   - Direct compilation with full control over output
   - Flags: -o, --emit-llvm, --deterministic, --explain
"""

import sys
import os
from pathlib import Path


def find_repo_root() -> Path:
    """Find the Pyrite repository root by looking for forge directory"""
    current = Path.cwd().resolve()
    
    # Walk up the directory tree looking for forge
    for path in [current] + list(current.parents):
        if (path / "forge").exists() and (path / "forge" / "src").exists():
            return path
    
    # Fallback: if we're in the repo, try relative to script location
    script_dir = Path(__file__).parent.resolve()
    # If script is in tools/, go up one level to get repo root
    if (script_dir.parent / "forge").exists():
        return script_dir.parent
    
    print("Error: Could not find Pyrite repository root.")
    print("Please run this script from within the Pyrite repository.")
    sys.exit(1)


def is_compiler_mode() -> bool:
    """Detect if we should use compiler mode based on flags"""
    # Check if first argument (after script name) is a flag
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        compiler_flags = ['-o', '--emit-llvm', '--deterministic', '--explain', '--help', '-h']
        if first_arg.startswith('-') or any(flag in sys.argv for flag in compiler_flags):
            return True
    return False


def run_compiler_mode(repo_root: Path):
    """Run in compiler mode (python -m src.compiler)"""
    compiler_path = repo_root / "forge"
    if str(compiler_path) not in sys.path:
        sys.path.insert(0, str(compiler_path))
    
    # Resolve file paths to absolute before changing directories
    # This allows relative paths to work from any directory
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg and not arg.startswith('-') and i == 1:
            # First non-flag argument is the input file
            if not Path(arg).is_absolute():
                abs_path = Path.cwd() / arg
                sys.argv[i] = str(abs_path.resolve())
        elif arg == '-o' and i + 1 < len(sys.argv):
            # Output file path
            output_file = sys.argv[i + 1]
            if not Path(output_file).is_absolute():
                abs_path = Path.cwd() / output_file
                sys.argv[i + 1] = str(abs_path.resolve())
    
    original_cwd = os.getcwd()
    original_path = sys.path[:]
    try:
        # Change to repo root so relative paths work correctly
        os.chdir(repo_root)
        
        # Import and run the compiler module
        from src.compiler import main as compiler_main
        sys.exit(compiler_main())
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_path


def run_script_mode(repo_root: Path):
    """Run in script mode (tools/pyrite_run.py)"""
    compiler_path = repo_root / "forge"
    if str(compiler_path) not in sys.path:
        sys.path.insert(0, str(compiler_path))
    
    # Resolve file paths to absolute before changing directories
    # This allows relative paths to work from any directory
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        file_arg = sys.argv[1]
        if not Path(file_arg).is_absolute():
            # Resolve relative to current working directory
            abs_path = Path.cwd() / file_arg
            sys.argv[1] = str(abs_path.resolve())
    
    # Import and run the actual pyrite_run.py (sibling in tools/runtime/)
    tools_dir = repo_root / "tools" / "runtime"
    pyrite_run_path = tools_dir / "pyrite_run.py"
    if not pyrite_run_path.exists():
        print(f"Error: Could not find tools/pyrite_run.py in repository root")
        sys.exit(1)
    
    # Execute the actual script by importing and calling its main
    original_cwd = os.getcwd()
    original_path = sys.path[:]
    try:
        # Change to repo root so relative paths work correctly
        os.chdir(repo_root)
        
        # Import the module
        import importlib.util
        spec = importlib.util.spec_from_file_location("pyrite_run", pyrite_run_path)
        if spec is None or spec.loader is None:
            print(f"Error: Could not load pyrite_run module")
            sys.exit(1)
        
        pyrite_run = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pyrite_run)
        
        # Call main with original argv (now with resolved paths)
        sys.exit(pyrite_run.main())
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_path


def main():
    """Main entry point - auto-detects mode based on flags"""
    # Handle --help and -h specially before mode detection
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("Pyrite - Memory-safe systems programming with Python syntax")
        print()
        print("Usage:")
        print("  python tools/pyrite.py <file.pyrite>              # Compile and run (script mode)")
        print("  python tools/pyrite.py <file.pyrite> -o output    # Compile to executable (compiler mode)")
        print("  python tools/pyrite.py --explain CODE             # Show error explanation")
        print()
        print("Script Mode (default):")
        print("  python tools/pyrite.py hello.pyrite               # Compile and run immediately")
        print()
        print("Compiler Mode (with flags):")
        print("  python tools/pyrite.py hello.pyrite -o hello.exe   # Compile to executable")
        print("  python tools/pyrite.py file.pyrite --emit-llvm    # Output LLVM IR")
        print("  python tools/pyrite.py --explain P0234            # Error explanations")
        print()
        print("For project management, use 'quarry':")
        print("  python tools/quarry.py new myproject")
        print("  python tools/quarry.py build")
        return 0
    
    repo_root = find_repo_root()
    
    # Detect mode: compiler mode if flags present, otherwise script mode
    if is_compiler_mode():
        run_compiler_mode(repo_root)
    else:
        run_script_mode(repo_root)


if __name__ == "__main__":
    main()

