#!/usr/bin/env python3
"""
Quarry build system wrapper - works from anywhere in the repo
Auto-detects repo root and sets up paths correctly
"""

import sys
import os
from pathlib import Path


def find_repo_root() -> Path:
    """Find the Pyrite repository root by looking for quarry directory"""
    current = Path.cwd().resolve()
    
    # Walk up the directory tree looking for quarry
    for path in [current] + list(current.parents):
        if (path / "quarry").exists() and (path / "quarry" / "main.py").exists():
            return path
    
    # Fallback: if we're in the repo, try relative to script location
    script_dir = Path(__file__).parent.resolve()
    # If script is in tools/, go up one level to get repo root
    if (script_dir.parent / "quarry" / "main.py").exists():
        return script_dir.parent
    
    print("Error: Could not find Pyrite repository root.")
    print("Please run this script from within the Pyrite repository.")
    sys.exit(1)


def main():
    """Main entry point"""
    repo_root = find_repo_root()
    
    # Add forge to Python path (for quarry imports from forge)
    forge_path = repo_root / "forge"
    if str(forge_path) not in sys.path:
        sys.path.insert(0, str(forge_path))
    
    # Import and run the actual quarry/main.py
    quarry_path = repo_root / "quarry" / "main.py"
    if not quarry_path.exists():
        print(f"Error: Could not find quarry/main.py")
        sys.exit(1)
    
    # Execute the actual script by importing and calling its main
    original_cwd = os.getcwd()
    original_path = sys.path[:]
    try:
        # For commands that need project context, preserve working directory
        # For other commands, change to repo root so relative paths work correctly
        project_commands = ["publish", "resolve", "install", "build", "run", "test", "fmt", "fix"]
        if len(sys.argv) > 1 and sys.argv[1] in project_commands:
            # Keep current directory for project commands
            pass
        else:
            # Change to repo root for other commands
            os.chdir(repo_root)
        
        # Import the module
        import importlib.util
        spec = importlib.util.spec_from_file_location("quarry_main", quarry_path)
        if spec is None or spec.loader is None:
            print(f"Error: Could not load quarry main module")
            sys.exit(1)
        
        quarry_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(quarry_main)
        
        # Call main with original argv
        sys.exit(quarry_main.main())
    finally:
        os.chdir(original_cwd)
        sys.path[:] = original_path


if __name__ == "__main__":
    main()

