"""Forge - Pyrite Compiler (Stage0 - Python Implementation)

Forge is the Pyrite compiler. This package contains the Stage0 implementation written in Python.
Forge transforms Pyrite source code into LLVM IR and native machine code.

This is part of the Quarry development suite for the Pyrite programming language.

Created by Alexander Rose Wulf (also known as Aeowulf and WulfHouse)

Main Entry Point:
    compiler: Main compiler driver (compile_source, compile_file)

Compiler Pipeline:
    frontend: Lexical analysis and parsing (lexer, parser, tokens)
    middle: Type checking and analysis (type_checker, ownership, borrow_checker)
    backend: Code generation and linking (codegen, linker, monomorphization)
    passes: Compiler passes (closure_inline_pass, with_desugar_pass)
    bridge: Pyrite↔Python interop (ast_bridge, tokens_bridge)
    utils: Utilities and diagnostics (diagnostics, error_formatter, incremental)

See Also:
    src-pyrite: Self-hosting Pyrite compiler (Stage1/Stage2)
    quarry: Build system and package manager
    stdlib: Standard library
"""
# Forge - Pyrite Compiler - Alpha v1.1
__version__ = "1.1.0-alpha"

