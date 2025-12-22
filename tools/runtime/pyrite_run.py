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


def run_script(script_path: str, args: list = None):
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
    if cached_ll.exists():
        # Use cached version
        print(f"[Cached] Running {script_path}")
    else:
        # Compile
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
    
    script_path = sys.argv[1]
    script_args = sys.argv[2:]
    
    return run_script(script_path, script_args)


if __name__ == "__main__":
    sys.exit(main())

