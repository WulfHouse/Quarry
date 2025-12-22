"""Compiler passes and transformations.

This package contains optional transformation passes that modify the AST
before code generation.

Modules:
    closure_inline_pass: Closure inlining optimization pass
    closure_inlining: Closure inlining utilities
    with_desugar_pass: `with` statement desugaring pass

See Also:
    compiler: Main compiler driver
    backend: Code generation
"""

from .closure_inline_pass import ClosureInlinePass
from .closure_inlining import ClosureInliner
from .with_desugar_pass import WithDesugarPass

__all__ = ['ClosureInlinePass', 'ClosureInliner', 'WithDesugarPass']
