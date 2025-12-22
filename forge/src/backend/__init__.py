"""Backend compiler modules.

This package contains code generation, linking, and optimization components.

Modules:
    codegen: LLVM IR code generation
    linker: Linking with standard library
    monomorphization: Generic instantiation

See Also:
    frontend: Lexical analysis and parsing
    middle: Type checking and analysis
    compiler: Main compiler driver
"""

from .codegen import generate_llvm, compile_to_executable, LLVMCodeGen, CodeGenError
from .linker import link_with_stdlib, link_llvm_ir, link_object_files, LinkerError, find_clang, find_gcc, compile_stdlib_c
from .monomorphization import monomorphize_program, extract_compile_time_args, MonomorphizationContext

__all__ = [
    'generate_llvm', 'compile_to_executable', 'LLVMCodeGen', 'CodeGenError',
    'link_with_stdlib', 'link_llvm_ir', 'link_object_files', 'LinkerError', 'find_clang', 'find_gcc', 'compile_stdlib_c',
    'monomorphize_program', 'extract_compile_time_args', 'MonomorphizationContext'
]
