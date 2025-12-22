"""FFI Bridge for Pyrite tokens module

This module provides a Python interface to the Pyrite tokens.pyrite module.
Once tokens.pyrite is compiled to a shared library, this bridge will load
and call the Pyrite functions via FFI.

For now, this is a placeholder that maintains the Python tokens.py API
while we work on the compilation and FFI infrastructure.

TODO:
1. Compile tokens.pyrite to shared library (.so/.dll)
2. Load library using ctypes
3. Define function signatures
4. Create Python wrappers that match tokens.py API
5. Update imports to use bridge instead of direct tokens.py
"""

# For now, re-export from tokens.py to maintain compatibility
# Once FFI is implemented, this will call Pyrite functions instead
from ..frontend.tokens import (
    TokenType,
    Token,
    Span,
    KEYWORDS,
)

__all__ = [
    'TokenType',
    'Token',
    'Span',
    'KEYWORDS',
    'get_keyword_type',
    'is_keyword',
]


def get_keyword_type(s: str):
    """Get TokenType for a keyword string (bridge to Pyrite)"""
    # TODO: Call Pyrite get_keyword_type() via FFI
    # For now, use Python implementation
    return KEYWORDS.get(s)


def is_keyword(s: str) -> bool:
    """Check if string is a keyword (bridge to Pyrite)"""
    # TODO: Call Pyrite is_keyword() via FFI
    # For now, use Python implementation
    return s in KEYWORDS
