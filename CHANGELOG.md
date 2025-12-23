# Changelog

> **⚠️ ALPHA v1.1 STATUS**
> 
> This project is currently in **Alpha v1.1**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0.

All notable changes to Pyrite (the programming language), Quarry (Pyrite SDK) and Forge (Pyrite compiler) will be documented in this file.

## Alpha v1.1 (Latest)

**Released:** December 23, 2025

### Added
- **JSON Support**: New `pyrite/serialize/json.pyrite` and `pyrite/serialize/json.c` for JSON parsing and serialization.

- **Tensor Support**: New `pyrite/num/tensor.pyrite` and `pyrite/num/tensor.c` for numerical computations.

- **Socket/TCP Support**: New `pyrite/net/tcp.pyrite` and `pyrite/net/socket.c` for networking.

- **Generic Collections**: Enhanced `List`, `Map`, and `Set` with better generic support and performance.

- **Shell Scripts**: Replaced PowerShell scripts with cross-platform Shell scripts (`.sh`) for better compatibility on Unix-like systems and Git Bash.

- **Compiler Improvements**: Significant updates to codegen and parser to support new features.

- **New Tests**: Added extensive tests for JSON, Tensors, and generic collections.

### Changed
- Migrated setup and build scripts from PowerShell (`.ps1`) to Shell (`.sh`).

- Updated `codegen.py` for improved LLVM IR generation.

- Improved parser and type checker for better generic handling.

## Alpha v1.0

**Released:** December 22, 2025

### Added
- Initial alpha release

- Basic compiler functionality

- Core language features

- Standard library foundation

- Tuple patterns in variable declarations (e.g., `let (a, b) = value`)

- Tuple literal syntax (e.g., `(1, 2, 3)`)

- Pattern matching support in variable declarations

---

## Version History

- **1.1.0-alpha** - Second alpha release (December 23, 2025) - **Current Status**

- **1.0.0-alpha** - Initial alpha release (December 22, 2025)

## Release Notes

### Alpha Release (1.1.0-alpha) - 2025 - Latest

**Current Status:** This is the current alpha release of Pyrite, the Quarry SDK and Forge (the Pyrite compiler).

**Key Highlights:**

- **Standard Library Expansion**: Added JSON, Tensor, and TCP Socket support.

- **Improved Generics**: Better support for generic collections (List, Map, Set).

- **Cross-Platform Scripts**: Shifted to Shell scripts for better portability.

- **Compiler Stability**: Numerous bug fixes and improvements in codegen and parsing.

### Alpha Release (1.0.0-alpha) - 2025

**Status:** Initial release.

**Key Highlights:**
- Initial Quarry SDK (Forge compiler, build system, package manager, tools)

- Basic Forge compiler pipeline from source to executable

- Memory-safe systems programming with ownership system (in progress)

- Python-like syntax with C-level performance

- Self-hosting Forge compiler (in progress)

- Standard library foundation

- Quarry build system and package manager (in progress)

**Known Limitations:**
See LIMITATIONS.md for a complete list of known limitations and incomplete features.

**Contributing:**
See README.md for development setup and contribution guidelines.

### Beta Release (1.0.0-beta) - 2026 (Planned)

**Status:** Planned for 2026. This section describes goals and targets for the beta release, not current implementation status.

**Planned Features:**
- Complete Quarry SDK (Forge compiler, build system, package manager, tools)

- Complete Forge compiler pipeline from source to executable

- Full memory-safe systems programming with ownership system

- Python-like syntax with C-level performance

- Self-hosting Forge compiler

- Comprehensive standard library

- Complete Quarry build system and package manager

**Note:** The beta release is a future milestone. Current status is Alpha v1.1. See [LIMITATIONS.md](LIMITATIONS.md) for what is currently implemented.
