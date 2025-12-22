#!/usr/bin/env python3
"""
Pyrite LSP Server wrapper - works from anywhere in the repo
Auto-detects repo root and sets up paths correctly

Usage:
    python tools/pyrite_lsp.py              # Start LSP server (for testing/debugging)
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


def main():
    """Main entry point"""
    # Handle help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Pyrite Language Server Protocol (LSP) Server")
        print()
        print("Usage:")
        print("  python tools/pyrite_lsp.py              # Start LSP server")
        print()
        print("The LSP server communicates via stdin/stdout using JSON-RPC.")
        print("It's typically started by IDE extensions (VSCode, etc.)")
        print("but can be run manually for testing and debugging.")
        print()
        print("For IDE integration, configure your editor to use:")
        print("  python tools/pyrite_lsp.py")
        return 0
    
    repo_root = find_repo_root()
    
    # Add forge to Python path
    compiler_path = repo_root / "forge"
    if str(compiler_path) not in sys.path:
        sys.path.insert(0, str(compiler_path))
    
    # Import and run the LSP server
    try:
        from lsp.server import main as lsp_main
        
        # Start the server
        lsp_main()
    except ImportError as e:
        print(f"Error: Could not import LSP server module: {e}")
        print("Make sure you're in the Pyrite repository.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nLSP server stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()

