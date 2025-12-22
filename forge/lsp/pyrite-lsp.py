#!/usr/bin/env python3
"""Pyrite LSP Server launcher"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lsp.server import main

if __name__ == '__main__':
    main()

