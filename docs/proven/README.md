# Proven Documentation

This directory contains **proven-only** documentation for Pyrite and Quarry. Every feature, syntax element, and command documented here is backed by evidence from the repository.

## Purpose

This documentation serves as a **ground truth reference** for what is actually implemented and working in the current repository. Unlike the aspirational SSOT specification, this documentation only includes features that can be proven through:

- Passing automated tests
- Runnable examples that compile/run successfully
- Unambiguous code-path evidence (e.g., CLI commands that exist in the command registry)

## Standards

### Evidence Requirements

A claim is considered "proven" only if at least one of the following is true:

1. **Test Evidence**: There is a passing automated test demonstrating the feature
2. **Example Evidence**: There is a runnable example in-repo that compiles/runs successfully
3. **Code Evidence**: There is unambiguous code-path evidence (e.g., parser rule exists and is exercised, CLI subcommand exists in command registry)

### Documentation Structure

Each document in this directory includes:

- **Purpose**: What the document covers
- **Content**: The proven features/syntax/commands
- **Evidence**: Required for each major section or item, including:
  - File paths and symbol/function names
  - Exact commands used to validate (when feasible)
- **Caveats**: Only when necessary (e.g., partial implementation, known limitations)

## Legend

When status indicators are used:

- ✅ **Supported**: Feature is fully implemented and proven to work
- ⚠️ **Partial**: Feature is partially implemented (documented limitations apply)
- ❌ **Not Supported**: Feature is explicitly absent or marked as TODO in repository

## Files

- **language_syntax.md**: Proven syntax elements accepted by the parser/compiler
- **cli_commands.md**: Proven CLI commands and flags that exist and work
- **features.md**: Feature list with status indicators and evidence
- **status_matrix.md**: Compact table of area → supported? → evidence pointer

## Relationship to Other Documentation

- **SSOT** (`docs/SSOT.md`, `docs/SSOT.txt`): Aspirational specification - may describe features not yet implemented
- **LIMITATIONS.md**: Known limitations and incomplete features
- **CHANGELOG.md**: What has actually been released
- **README.md**: Current project status

This proven documentation complements these by providing a **strictly evidence-based** reference for what works today.

## Validation

This documentation is maintained to reflect the current repository state. When features are added or removed, this documentation should be updated accordingly.

To validate claims in this documentation:

1. Check the evidence pointers (file paths, test names)
2. Run the referenced tests: `python tools/testing/pytest_fast.py`
3. Try the referenced examples: `python tools/runtime/pyrite.py <example>.pyrite`
4. Verify CLI commands: `python tools/runtime/quarry.py --help`
