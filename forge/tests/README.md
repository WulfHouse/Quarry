# Pyrite Compiler Tests

## Overview

This directory contains the test suite for the Pyrite compiler. Tests are organized to mirror the source code structure for easy navigation and maintenance.

## Test Organization

Tests are organized to mirror the source code structure for easy navigation:

- **`frontend/`** - Lexical analysis and parsing tests
  - `test_lexer.py`, `test_parser.py`, `test_tokens*.py`
  
- **`middle/`** - Type checking, ownership, and analysis tests
  - `test_type_checker.py`, `test_ownership*.py`, `test_borrow_checker.py`, `test_module_system.py`, `test_symbol_table.py`
  
- **`backend/`** - Code generation and linking tests
  - `test_codegen*.py`, `test_linker.py`, `test_monomorphization.py`
  
- **`passes/`** - Compiler pass/transformation tests
  - `test_closure_inline*.py`, `test_with_desugar.py`
  
- **`bridge/`** - Bridge/interop tests
  - `test_*_bridge.py`, `test_ast_bridge.py`, `test_tokens_bridge.py`
  
- **`utils/`** - Utility and diagnostic tests
  - `test_diagnostics.py`, `test_error_formatter.py`, `test_error_explanations.py`, `test_incremental*.py`, `test_drops.py`
  
- **`integration/`** - Integration and end-to-end tests
  - `test_integration.py`, `test_bootstrap.py`
  
- **`quarry/`** - Build system (Quarry) tests
  - `test_quarry*.py`, `test_build_graph*.py`, `test_workspace.py`, `test_dependency*.py`, etc.
  
- **`stdlib/`** - Standard library tests
  - `test_*_stdlib.py`, `test_list_stdlib.py`, `test_string_stdlib.py`, `test_file_io.py`, `test_path.py`
  
- **`fixtures/`** - Test fixtures and shared test data
- **`legacy/`** - Legacy tests (being phased out)

**Root-level tests**: Some general tests remain at the root level:
- `test_compiler.py` - End-to-end compiler tests
- `test_ast.py` - AST tests
- `test_types.py` - Type system tests
- `test_helpers.py` - Test helper utilities
- Other feature-specific tests (FFI, traits, closures, etc.)

## Running Tests

### Fast Test Suite

```bash
# Run only fast tests (< 1 minute)
python tools/testing/pytest_fast.py
```

### All Tests

```bash
# Run all tests
python tools/testing/pytest.py

# Run with coverage
python tools/testing/pytest.py --cov=forge/src --cov-report=term
```

### Specific Test Categories

```bash
# Run only frontend tests
python tools/testing/pytest.py forge/tests/frontend/

# Run only integration tests
python tools/testing/pytest.py forge/tests/integration/ -m integration
```

## Test Markers

Tests are marked with pytest markers for categorization:

- `@pytest.mark.fast` - Fast unit tests (< 100ms each)
- `@pytest.mark.integration` - Integration tests (< 1s each)
- `@pytest.mark.slow` - Slow tests (> 1s each)
- `@pytest.mark.bootstrap` - Bootstrap validation tests
- `@pytest.mark.e2e` - End-to-end tests

## Test Structure

Each test file should:
- Test a single module or closely related functionality
- Use descriptive test names
- Include docstrings explaining what is being tested
- Use fixtures from `fixtures/` when appropriate

## See Also

- `docs/testing/FAST_SUITE.md` - Fast test suite documentation
- `docs/testing/COVERAGE.md` - Coverage documentation
- `forge/src/README.md` - Compiler source documentation
