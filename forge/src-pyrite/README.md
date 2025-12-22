# Pyrite Self-Hosting Compiler

## Overview

This directory contains the Pyrite compiler written in Pyrite itself. This is the self-hosting compiler (Stage1/Stage2) that will eventually replace the Python compiler (Stage0) in `src/`.

## Purpose

The self-hosting compiler demonstrates that Pyrite is capable of compiling itself, which is a key milestone for language maturity. The compiler in this directory is compiled by the Python compiler in `src/`.

## Files

- `main.pyrite` - Main compiler entry point
- `ast.pyrite` - AST definitions (Pyrite version)
- `types.pyrite` - Type system definitions (Pyrite version)
- `tokens.pyrite` - Token definitions (Pyrite version)
- `symbol_table.pyrite` - Symbol table (Pyrite version)
- `diagnostics.pyrite` - Error diagnostics (Pyrite version)
- `build_graph.pyrite` - Build graph utilities
- `dep_fingerprint.pyrite` - Dependency fingerprinting
- `dep_source.pyrite` - Dependency source tracking
- `locked_validate.pyrite` - Locked validation
- `lockfile.pyrite` - Lockfile handling
- `path_utils.pyrite` - Path utilities
- `toml.pyrite` - TOML parsing
- `version.pyrite` - Version handling

## Bootstrap Process

1. **Stage0 (Python)** - `src/` compiles `src-pyrite/` → Stage1 compiler
2. **Stage1 (Pyrite)** - Stage1 compiler compiles `src-pyrite/` → Stage2 compiler
3. **Verification** - Stage1 and Stage2 outputs are compared for determinism

See `docs/bootstrap.md` for detailed bootstrap instructions.

## Status

The self-hosting compiler is in active development. Not all features from the Python compiler are yet implemented in Pyrite.

## See Also

- `src/` - Python compiler (Stage0)
- `docs/bootstrap.md` - Bootstrap documentation
- `plans/self-hosting/` - Self-hosting plans and status
