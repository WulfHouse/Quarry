# Forge - Pyrite Compiler Source

## Overview

This directory contains **Forge**, the Pyrite compiler implementation (Stage0 - Python). Forge follows a traditional multi-pass architecture, transforming Pyrite source code into LLVM IR and then to native machine code.

**Forge** is part of the **Quarry** development suite for the **Pyrite** programming language.

## Compiler Pipeline

The compilation process follows these phases:

1. **Frontend** - Lexical analysis and parsing
   - `lexer.py` - Tokenizes Pyrite source code
   - `parser.py` - Parses tokens into an Abstract Syntax Tree (AST)
   - `tokens.py` - Token definitions and utilities

2. **Middle** - Type checking, ownership analysis, and symbol resolution
   - `type_checker.py` - Type checking and inference
   - `ownership.py` - Ownership analysis
   - `borrow_checker.py` - Borrow checking
   - `symbol_table.py` - Symbol table management
   - `module_system.py` - Module resolution and imports

3. **Backend** - Code generation, linking, and optimization
   - `codegen.py` - LLVM IR code generation
   - `linker.py` - Linking with standard library
   - `monomorphization.py` - Generic instantiation

4. **Passes** - Optional transformation passes
   - `closure_inline_pass.py` - Closure inlining optimization
   - `closure_inlining.py` - Closure inlining utilities
   - `with_desugar_pass.py` - `with` statement desugaring

5. **Bridge** - Pyrite↔Python interoperability
   - `ast_bridge.py` - AST bridge for Pyrite-compiled code
   - `tokens_bridge.py` - Tokens bridge for Pyrite-compiled code

6. **Utils** - Utilities and diagnostics
   - `diagnostics.py` - Error diagnostics
   - `error_formatter.py` - Error message formatting
   - `error_explanations.py` - Error explanation system
   - `incremental.py` - Incremental compilation support
   - `drops.py` - Drop analysis

## Entry Point

**`compiler.py`** - Main Forge compiler driver
- `compile_source()` - Compile Pyrite source code string
- `compile_file()` - Compile a Pyrite source file

## Key Shared Modules

- **`ast.py`** - Abstract Syntax Tree (AST) node definitions
- **`types.py`** - Type system definitions (Type, IntType, StringType, etc.)

## Compilation Flow

```
Source Code
    ↓
[Frontend] lexer.py → parser.py
    ↓
AST (ast.py)
    ↓
[Middle] type_checker.py → ownership.py → borrow_checker.py
    ↓
Typed AST
    ↓
[Passes] closure_inline_pass.py → with_desugar_pass.py
    ↓
[Backend] codegen.py → linker.py
    ↓
LLVM IR / Executable
```

## Dependencies

- **llvmlite** - LLVM bindings for code generation
- **Standard library** - `pyrite/` for runtime functions

## See Also

- `forge/src-pyrite/` - Self-hosting Forge (Stage1/Stage2)
- `quarry/` - Quarry build system (top-level)
- `docs/SSOT.md` - Pyrite language specification (modular)
- `docs/specification/` - Specification modules
- `docs/refactoring/FORGE_COMPILER_NAME.md` - Forge naming and details
