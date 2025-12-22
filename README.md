# Quarry - Pyrite SDK

> **⚠️ ALPHA v1.0 STATUS**
> 
> This project is currently in **Alpha v1.0**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0. Use at your own discretion.

**Quarry** is the official SDK for the **Pyrite** programming language. This repository contains the Quarry SDK (currently in Alpha v1.0), including **Forge** (the Pyrite compiler), build system, package manager, language server, and development tools.

**Pyrite** is a compiled systems programming language designed to combine the low-level power and performance of C with the readability and ease-of-use of Python, while integrating the safety of Rust and the simplicity of Zig.

**Created by Alexander Rose Wulf** (also known as **Aeowulf** and **WulfHouse**)

*Conceptualized: December 12, 2025*

*Published: December 22, 2025*

## Overview

**Pyrite** is a memory-safe systems programming language that compiles to native machine code via LLVM. It features:

- **Python-like syntax** - Easy to read and write
- **C-level performance** - Zero runtime overhead
- **Memory safety** - Ownership and borrowing system inspired by Rust
- **Simple and explicit** - No hidden surprises, minimal magic
- **Self-hosting compiler** - Forge is being rewritten in Pyrite itself (in progress)

## Quick Start

### Installation

**Unix/macOS:**
```bash
bash scripts/setup/install.sh
```

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/install.ps1
```

### Compile a Program

```bash
# Using the wrapper script (recommended)
python tools/runtime/pyrite.py hello.pyrite

# Using Forge (the compiler) directly
# Note: Run from repository root, or use the wrapper script
cd forge && python -m src.compiler hello.pyrite

# Using Quarry (build system)
python tools/runtime/quarry.py build
python tools/runtime/quarry.py run
```

### Run Tests

```bash
# Fast tests only (< 1 minute)
python tools/testing/pytest_fast.py

# All tests (batched)
python tools/testing/run_tests_batched.py

# Full test suite
python tools/testing/pytest.py
```

**Fast Suite**: The fast suite (`pytest_fast.py`) runs only fast tests for quick feedback during development. See [tools/testing/pytest_fast.py](tools/testing/pytest_fast.py) for details.

## Repository Structure

This is the **Quarry** SDK repository, containing the **Pyrite** toolchain: **Forge** (the Pyrite compiler), Quarry build system and package manager, language server, development tools, tests, and documentation.

```
pyrite/
├── build/                          # Build artifacts (safe to delete)
│   ├── bootstrap/                  # Bootstrap compiler artifacts
│   │   ├── stage1/                 # Forge Stage1 (Pyrite compiled by Python)
│   │   └── stage2/                 # Forge Stage2 (Pyrite compiled by Stage1)
│   ├── .coverage                   # Coverage data
│   ├── coverage.json               # Coverage JSON report
│   └── README.md                   # Build artifacts documentation
│
├── docs/                           # Documentation
│   ├── SSOT.md                     # Language Specification (modular index, aspirational)
│   ├── SSOT.txt                    # Original specification (preserved as backup, aspirational)
│   └── specification/              # Modular specification files (aspirational)
│   ├── bootstrap.md                # Bootstrap guide
│   ├── performance/                # Performance documentation
│   ├── quarry/                     # Quarry build system docs
│   └── testing/                    # Testing documentation
│
├── forge/                          # Forge compiler implementation
│   ├── src/                        # Forge Stage0 (Python implementation)
│   │   ├── README.md               # Compiler pipeline documentation
│   │   ├── compiler.py             # Main compiler entry point
│   │   ├── ast.py                  # Abstract Syntax Tree definitions
│   │   ├── types.py                # Type system definitions
│   │   ├── frontend/               # Lexical analysis & parsing
│   │   │   ├── lexer.py            # Tokenization
│   │   │   ├── parser.py           # Syntax parsing
│   │   │   └── tokens.py           # Token definitions
│   │   ├── middle/                 # Type checking & analysis
│   │   │   ├── type_checker.py     # Type checking
│   │   │   ├── ownership.py        # Ownership analysis
│   │   │   ├── borrow_checker.py   # Borrow checking
│   │   │   ├── symbol_table.py     # Symbol resolution
│   │   │   └── module_system.py    # Module resolution
│   │   ├── backend/                # Code generation & linking
│   │   │   ├── codegen.py          # LLVM IR generation
│   │   │   ├── linker.py           # Linking with stdlib
│   │   │   └── monomorphization.py # Generic instantiation
│   │   ├── passes/                 # Compiler passes
│   │   │   ├── closure_inline_pass.py
│   │   │   └── with_desugar_pass.py
│   │   ├── bridge/                 # Pyrite↔Python interop
│   │   │   ├── ast_bridge.py
│   │   │   └── tokens_bridge.py
│   │   ├── utils/                  # Utilities & diagnostics
│   │   │   ├── diagnostics.py
│   │   │   ├── error_formatter.py
│   │   │   └── incremental.py
│   ├── src-pyrite/                 # Forge Stage1/Stage2 (Pyrite implementation)
│   │   ├── diagnostics.pyrite
│   │   ├── ast.pyrite
│   │   ├── types.pyrite
│   │   ├── tokens.pyrite
│   │   └── symbol_table.pyrite
│   ├── runtime/                    # Runtime library
│   │   └── libpyrite.a             # Compiled runtime library
│   ├── tests/                      # Compiler tests
│   │   ├── README.md               # Test organization guide
│   │   ├── frontend/               # Frontend tests
│   │   ├── middle/                 # Middle-end tests
│   │   ├── backend/                # Backend tests
│   │   ├── passes/                 # Pass tests
│   │   ├── bridge/                 # Bridge tests
│   │   ├── utils/                  # Utility tests
│   │   ├── integration/            # Integration tests
│   │   ├── quarry/                 # Quarry tests
│   │   ├── stdlib/                 # Standard library tests
│   │   ├── fixtures/               # Test fixtures
│   │   └── legacy/                 # Legacy test files
│   ├── examples/                   # Example Pyrite programs
│   │   ├── README.md               # Examples guide
│   │   ├── basic/                  # Simple single-file examples
│   │   ├── projects/               # Full project examples
│   │   └── test/                   # Test/example files
│   └── lsp/                        # Language Server Protocol
│
├── quarry/                         # Quarry - Build system and package manager
│   ├── README.md                   # Quarry documentation
│   ├── main.py                     # Main entry point
│   ├── workspace.py                # Workspace management
│   ├── dependency.py               # Dependency resolution
│   ├── build_graph.py              # Build graph
│   └── bridge/                     # FFI bridges to Pyrite stdlib
│
├── pyrite/                         # Pyrite - Language-facing artifacts
│   ├── README.md                   # Standard library documentation
│   ├── core/                       # Core types and functions
│   ├── collections/                # Collections (List, Map, Set)
│   ├── io/                         # I/O operations
│   ├── string/                     # String operations
│   └── [other modules]             # Additional stdlib modules
│
├── scripts/                        # Utility scripts
│   ├── bootstrap/                  # Bootstrap scripts
│   │   ├── bootstrap_stage1.py     # Build Forge Stage1
│   │   ├── bootstrap_stage2.py     # Build Forge Stage2
│   │   └── check_bootstrap_determinism.py
│   ├── diagnostics/                # Diagnostic scripts
│   │   ├── diagnose_coverage_crash.py
│   │   └── diagnose_coverage_timeout.py
│   ├── setup/                      # Setup scripts
│   │   ├── install.sh              # Unix/macOS installer
│   │   ├── install.ps1             # Windows installer
│   │   └── setup-dev.ps1           # Development environment setup
│   ├── utils/                      # Utility scripts
│   │   ├── incremental_coverage.py
│   │   ├── split_large_test_file.py
│   │   ├── test_coverage_safety.py
│   │   └── verify_dev_env.py
│   └── [wrappers]                      # Entry point wrappers (pyrite, quarry, etc.)
│
├── tools/                              # Development tools
│   ├── coverage/                       # Coverage analysis tools
│   │   ├── analyze_coverage.py
│   │   ├── find_dead_code.py
│   │   ├── get_coverage_percentage.py
│   │   └── get_uncovered_lines.py
│   ├── testing/                        # Test runners
│   │   ├── pytest.py                   # Main test runner
│   │   ├── pytest_fast.py              # Fast test suite
│   │   ├── run_tests_batched.py
│   │   ├── run_tests_local.py
│   │   ├── run_tests_safe.py
│   │   ├── run_tests_with_progress.py
│   │   ├── test_timing.py
│   │   └── check_test_timing.py
│   ├── build/                          # Build tools
│   │   ├── build_runtime.py            # Build runtime library
│   │   └── rebuild.py                  # Rebuild Forge
│   ├── runtime/                        # Runtime tools
│   │   ├── pyrite.py                   # Forge compiler wrapper
│   │   ├── pyrite_lsp.py               # LSP server
│   │   ├── pyrite_run.py               # Run Pyrite programs
│   │   └── quarry.py                   # Quarry build system
│   ├── utils/                          # Utility tools
│   │   ├── debug_try_operator.py
│   │   ├── run_logged.ps1              # Command logging wrapper
│   │   ├── run_safe.ps1                # Convenience wrapper
│   │   └── validate_command_safety.ps1
│   └── docs/                           # Tool documentation
│       ├── DEVELOPER_COMMAND_POLICY.md
│       └── README_COMMAND_POLICY.md
│
├── tests/                               # Integration and acceptance tests
│   ├── acceptance/                      # Acceptance tests
│   ├── integration/                     # Integration tests
│   └── test-projects/                   # Test projects
│
├── test-consumer/                       # Test consumer project
│
├── vscode-pyrite/                       # VS Code extension
│   ├── src/                             # Extension source
│   ├── syntaxes/                        # Syntax highlighting
│   └── package.json                     # Extension manifest
│
├── .logs/                               # Developer execution logs
│
├── .coveragerc                          # Coverage configuration
├── .gitignore                           # Git ignore rules
└── pyproject.toml                       # Python project configuration
```

## Key Components

### Quarry SDK

**Quarry** is the official Pyrite SDK, including:

- **Forge** - The Pyrite compiler (compiles Pyrite source code to LLVM IR and native machine code)
- **Build System and Package Manager** - Incremental compilation, dependency management
- **Auto-Fix System** - Automatically fix common errors
- **Performance Analysis** - Cost transparency and profiling
- **Binary Size Analysis** - Understand what's consuming space
- **Language Server Protocol (LSP)** - IDE support
- **Development Tools** - Tools as specified in the SSOT (see LIMITATIONS.md for implementation status)

See `quarry/README.md` for details.

### Forge Compiler Stages

- **Stage0 (Python)**: Forge implementation in Python (`forge/src/`)
- **Stage1 (Pyrite)**: Forge compiled by Stage0 (`build/bootstrap/stage1/`)
- **Stage2 (Pyrite)**: Forge compiled by Stage1 (`build/bootstrap/stage2/`)

### Language Server

The Quarry LSP server provides IDE support for Pyrite:
- Syntax highlighting
- Error diagnostics
- Code completion
- Hover information

## Development Workflow

### Setting Up Development Environment

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts/setup/setup-dev.ps1

# Note: For Unix/macOS, manually add the tools/runtime directory to your PATH
# or create shell aliases for pyrite, quarry, etc.
```

### Building Forge

```bash
# Build runtime library
python tools/build/build_runtime.py

# Rebuild Forge compiler
python tools/build/rebuild.py
```

### Bootstrap Process

Forge (the Pyrite compiler) is working toward self-hosting. To bootstrap:

**Quick Start:**
```bash
# One-command bootstrap
python scripts/bootstrap.py
```

**Manual Steps:**
```bash
# Build Stage1 (Python Forge -> Pyrite Forge)
python scripts/bootstrap/bootstrap_stage1.py

# Build Stage2 (Stage1 Forge -> Pyrite Forge)
python scripts/bootstrap/bootstrap_stage2.py

# Verify determinism (Stage1 and Stage2 produce equivalent output)
python scripts/bootstrap/check_bootstrap_determinism.py
```

**Full Documentation:** See [docs/bootstrap.md](docs/bootstrap.md) for detailed prerequisites, troubleshooting, and verification steps.

**Note:** The bootstrap process requires Python 3.8+, llvmlite, and a C compiler (clang or gcc).

### Running Tests

```bash
# Fast tests (8 tests, ~3.2s)
python tools/testing/pytest_fast.py

# Batched tests (avoids system overload)
python tools/testing/run_tests_batched.py

# Full test suite
python tools/testing/pytest.py

# With coverage
python tools/testing/pytest.py --cov=forge/src --cov-report=term
```

### Coverage Analysis

```bash
# Get coverage percentage
python tools/coverage/get_coverage_percentage.py

# Analyze coverage gaps
python tools/coverage/analyze_coverage.py

# Find uncovered lines for a file
python tools/coverage/get_uncovered_lines.py codegen.py

# Find dead code (0% coverage)
python tools/coverage/find_dead_code.py
```

## Configuration Files

- **`pyproject.toml`**: Python project configuration (dependencies, pytest, coverage)
- **`.coveragerc`**: Coverage.py configuration (backup to pyproject.toml)
- **`.gitignore`**: Git ignore rules

## Documentation

- **Language Specification**: `docs/SSOT.md` - Aspirational specification and vision (may not reflect current implementation)
- **Bootstrap Guide**: `docs/bootstrap.md` - How to bootstrap Forge
- **Quarry SDK**: `quarry/README.md` - Quarry build system and package manager documentation

## Contributing

### Code Organization

This repository contains the Quarry SDK (in alpha):
- **Forge compiler source**: `forge/src/` (Python) and `forge/src-pyrite/` (Pyrite)
- **Quarry build system**: `quarry/` (top-level) - Build system and package manager
- **Standard library**: `pyrite/` (top-level) - Language-facing artifacts
- **Language Server**: `forge/lsp/` - LSP implementation
- **Tests**: `forge/tests/` (unit tests) and `tests/` (integration/acceptance)
- **Tools**: `tools/` organized by purpose (coverage, testing, build, runtime, utils)
- **Scripts**: `scripts/` organized by purpose (bootstrap, diagnostics, setup, utils)

### Build Artifacts

All build artifacts are in `build/` and can be safely deleted:
- `build/bootstrap/` - Bootstrap compiler artifacts
- `build/.coverage` - Coverage data
- `build/coverage.json` - Coverage reports

### Logs

Developer execution logs are in `.logs/` directory.

## Authors

- **Alexander Rose Wulf** (also known as **Aeowulf** and **WulfHouse**) - Creator and original developer

See [AUTHORS.md](AUTHORS.md) for complete authorship information, including contributors and alpha testers.

## License

This project is licensed under the **WulfHouse Source-Available Non-Compete License (WSANCL) v1.0** - see the [LICENSE.md](LICENSE.md) file for details.

**Note:** This is a source-available license, not an OSI-approved open-source license. It allows use, modification, and distribution for non-competing purposes, but restricts commercialization and competing uses of the toolchain itself. Code you build *with* Pyrite (Output) is unrestricted. See [LICENSE.md](LICENSE.md) for full terms.

Copyright (c) 2025 Alexander Rose Wulf (Aeowulf/WulfHouse)

## Legal Documents and Policies

This project is governed by the following legal documents:

- **[LICENSE.md](LICENSE.md)** - WulfHouse Source-Available Non-Compete License (WSANCL) v1.0
  - Governs use, modification, and distribution of the source code
  - Defines competing vs non-competing use restrictions
  - Code you build *with* Pyrite (Output) is unrestricted

- **[CONTRIBUTOR_AGREEMENT.md](CONTRIBUTOR_AGREEMENT.md)** - Pull Request Contributor Agreement (PRCA)
  - Applies when you submit contributions (pull requests, commits, etc.)
  - Grants copyright and patent licenses to WulfHouse
  - Automatically accepted when you submit a contribution

- **[TRADEMARK_POLICY.md](TRADEMARK_POLICY.md)** - WulfHouse Trademark Policy
  - Governs use of trademarks: WulfHouse, Pyrite, Quarry, and Forge
  - Defines what is allowed vs prohibited for third-party projects
  - **For third-party projects**: If you create tools, libraries, or services related to Pyrite/Quarry, you must follow the trademark policy and include appropriate disclaimers. See Section 6 of the trademark policy for required disclaimers.

## Links

- **Language Specification**: See `docs/SSOT.md` (modular) or `docs/specification/` for individual modules
  - **⚠️ Important:** The SSOT is a **high-level master specification overview** and **hypothetical wishlist** for what the project is intended to eventually become. It may not accurately convey the current state of the project and monorepo. See [docs/SSOT_DISCLAIMER.md](docs/SSOT_DISCLAIMER.md) and [LIMITATIONS.md](LIMITATIONS.md) for what's actually implemented.
- **Quarry SDK**: See `quarry/README.md` for build system and package manager
