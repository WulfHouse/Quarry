"""Helper functions for writing compiler tests"""

from typing import NamedTuple, Optional
from src.frontend import lex
from src.frontend import parse
from src.backend import generate_llvm, CodeGenError


class CompilationResult(NamedTuple):
    """Result of compiling a Pyrite code snippet"""
    success: bool
    llvm_ir: Optional[str] = None
    error: Optional[Exception] = None
    error_message: Optional[str] = None


def compile_snippet(code: str, deterministic: bool = False) -> CompilationResult:
    """Compile a Pyrite code snippet and return compilation result
    
    Args:
        code: Pyrite source code as string
        deterministic: Enable deterministic builds (default: False)
        
    Returns:
        CompilationResult with:
            - success: True if compilation succeeded
            - llvm_ir: Generated LLVM IR (if successful)
            - error: Exception that occurred (if failed)
            - error_message: Error message string (if failed)
    
    Example:
        >>> result = compile_snippet('fn main(): return 42')
        >>> assert result.success
        >>> assert "define" in result.llvm_ir
        >>> assert "main" in result.llvm_ir
    """
    try:
        # Lex
        tokens = lex(code)
        
        # Parse
        ast = parse(tokens)
        
        # Generate LLVM IR
        llvm_ir = generate_llvm(ast, deterministic=deterministic)
        
        return CompilationResult(
            success=True,
            llvm_ir=llvm_ir,
            error=None,
            error_message=None
        )
    except CodeGenError as e:
        return CompilationResult(
            success=False,
            llvm_ir=None,
            error=e,
            error_message=str(e)
        )
    except Exception as e:
        return CompilationResult(
            success=False,
            llvm_ir=None,
            error=e,
            error_message=str(e)
        )
