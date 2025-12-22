# Pyrite Examples

This directory contains example Pyrite programs demonstrating language features and usage patterns.

## Directory Structure

- **`basic/`** - Simple single-file examples demonstrating individual language features
- **`projects/`** - Full project examples with multiple files and Quarry.toml configuration
- **`test/`** - Test/example files used for testing specific features

## Basic Examples

Simple examples that demonstrate core language features:

- `hello.pyrite` - Hello World
- `arithmetic.pyrite` - Arithmetic operations
- `borrowing.pyrite` - Borrowing and ownership
- `closures.pyrite` - Closures and higher-order functions
- `structs.pyrite` - Struct definitions and usage
- `enums.pyrite` - Enum definitions and pattern matching
- `traits.pyrite` - Trait definitions and implementations
- `generics.pyrite` - Generic types and functions
- `methods.pyrite` - Method definitions
- `ownership.pyrite` - Ownership examples
- `factorial.pyrite` - Recursive functions
- `fizzbuzz.pyrite` - Control flow examples

## Project Examples

Full project examples demonstrating real-world usage:

- **`file_processor/`** - Multi-module project with workspace configuration
  - Demonstrates project structure, dependencies, and testing
  - Includes `processor/`, `utils/`, and `test-consumer/` modules

- **`learned_project/`** - Example project structure
  - Shows Quarry.toml configuration
  - Demonstrates build system usage

## Test Examples

Examples used for testing specific compiler features:

- `test_defer_execution.pyrite` - Defer statement testing
- `test_hover.pyrite` - LSP hover functionality
- `test_monomorphization.pyrite` - Generic monomorphization
- `test_parameter_closure_simple.pyrite` - Parameter closure testing

## Running Examples

### Basic Examples

```bash
# Compile and run a basic example
python tools/runtime/pyrite.py examples/basic/hello.pyrite
```

### Project Examples

```bash
# Navigate to project directory
cd examples/projects/file_processor/processor

# Build with Quarry
python tools/runtime/quarry.py build

# Run
python tools/runtime/quarry.py run
```

## See Also

- `docs/SSOT.md` - Language specification (modular)
- `docs/specification/` - Specification modules
- `forge/src/README.md` - Compiler documentation
- `quarry/README.md` - Build system documentation
