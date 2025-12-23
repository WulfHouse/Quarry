"""Script mode for Pyrite - compile and run single files"""

import sys
import os
import hashlib
import subprocess
from pathlib import Path
from src.compiler import compile_source


def get_cache_dir() -> Path:
    """Get cache directory for script mode"""
    if os.name == 'nt':  # Windows
        cache_base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    else:  # Unix-like
        cache_base = Path.home() / '.cache'
    
    cache_dir = cache_base / 'pyrite' / 'scripts'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def compute_hash(source: str, compiler_version: str = "1.0.0-alpha") -> str:
    """Compute hash of source + compiler version"""
    content = f"{compiler_version}\n{source}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def run_script(script_path: str, args: list = None, no_run: bool = False):
    """Run a Pyrite script with caching"""
    if args is None:
        args = []
    
    # Read source
    script_file = Path(script_path)
    if not script_file.exists():
        print(f"Error: File not found: {script_path}")
        return 1
    
    source = script_file.read_text(encoding='utf-8')
    
    # Compute hash
    source_hash = compute_hash(source)
    
    # Check cache
    cache_dir = get_cache_dir()
    cache_entry = cache_dir / source_hash
    cached_ll = cache_entry / "output.ll"
    cached_exe = cache_entry / "output.exe" if os.name == 'nt' else cache_entry / "output"
    
    # Check if cached and fresh
    if cached_ll.exists() and cached_exe.exists():
        # Use cached version
        if not no_run:
            print(f"[Cached] Running {script_path}")
    else:
        # Compile
        if not no_run:
            print(f"[Compiling] {script_path}")
        cache_entry.mkdir(parents=True, exist_ok=True)
        
        # Compile to executable
        success = compile_source(
            source,
            str(script_file),
            str(cached_exe),
            emit_llvm=False  # Compile to executable
        )
        
        if not success:
            return 1
    
    if no_run:
        print(str(cached_exe.resolve()))
        return 0

    # Execute the program
    if cached_exe.exists():
        # Run cached executable
        import subprocess
        result = subprocess.run([str(cached_exe)] + args)
        return result.returncode
    else:
        print(f"\n[Note] Cached compilation found but executable missing")
        print(f"[Note] To execute, compile with: gcc {cached_ll} -o {cached_exe}")
        return 1


def show_help():
    """Show helpful usage information"""
    print("Pyrite - Memory-safe systems programming with Python syntax")
    print()
    print("Usage:")
    print("  pyrite <file.pyrite>       Compile and run a Pyrite file")
    print("  pyrite --no-run <file>     Compile and print exe path without running")
    print("  pyrite <file> -- [args]    Forward args to program")
    print("  pyrite --help              Show this help message")
    print("  pyrite --version           Show version information")
    print()
    print("Examples:")
    print("  pyrite hello.pyrite        Run hello.pyrite")
    print("  pyrite script.pyrite arg1  Run with arguments")
    print()
    print("For project management, use 'quarry':")
    print("  quarry new myproject       Create a new project")
    print("  quarry build               Build the project")
    print("  quarry run                 Build and run")
    print()

def main():
    """Main entry point for pyrite run"""
    if len(sys.argv) < 2:
        show_help()
        return 0  # Help is a successful operation
    
    # Handle flags
    if sys.argv[1] in ['--help', '-h']:
        show_help()
        return 0
    
    if sys.argv[1] in ['--version', '-v']:
        print("Pyrite 1.0.0-alpha")
        print("Memory-safe systems programming with Python syntax")
        return 0
    
    no_run = False
    args = sys.argv[1:]
    
    if "--no-run" in args:
        no_run = True
        args.remove("--no-run")
    
    if not args:
        show_help()
        return 1

    script_path = args[0]
    script_args = []
    
    # Handle -- for args forwarding
    if "--" in args:
        idx = args.index("--")
        script_args = args[idx+1:]
        # File is before -- or after flags
        if idx > 0:
            script_path = args[0] if args[0] != "--" else args[1]
    else:
        script_args = args[1:]
    
    return run_script(script_path, script_args, no_run=no_run)


if __name__ == "__main__":
    sys.exit(main())

