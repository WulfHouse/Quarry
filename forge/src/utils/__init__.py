"""Compiler utilities and diagnostics.

This package contains utility modules for error handling, diagnostics,
and incremental compilation.

Modules:
    diagnostics: Error diagnostics
    error_formatter: Error message formatting
    error_explanations: Error explanation system
    incremental: Incremental compilation support
    drops: Drop analysis

See Also:
    compiler: Main compiler driver
    middle: Type checking (uses diagnostics)
"""

from .diagnostics import *
from .error_formatter import ErrorFormatter, Colors, format_error_message
from .error_explanations import ERROR_EXPLANATIONS, get_explanation, list_error_codes
from .drops import DropAnalyzer, insert_drops
from .incremental import *

__all__ = [
    'ErrorFormatter', 'Colors', 'format_error_message',
    'ERROR_EXPLANATIONS', 'get_explanation', 'list_error_codes',
    'DropAnalyzer', 'insert_drops'
]
