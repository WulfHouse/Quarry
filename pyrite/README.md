# Pyrite Standard Library

## Overview

The Pyrite standard library provides core functionality for Pyrite programs. It includes fundamental types, collections, I/O operations, and utilities.

## Organization

The standard library is organized into modules:

### Core (`core/`)
- `builtins.c` - Built-in functions and types
- `option.pyrite` - Option type (Some/None)
- `result.pyrite` - Result type (Ok/Err)
- `closeable.pyrite` - Closeable trait

### Collections (`collections/`)
- `list.pyrite` / `list.c` - Dynamic list implementation
- `map.pyrite` / `map.c` - Map/dictionary implementation
- `set.pyrite` / `set.c` - Set implementation

### I/O (`io/`)
- `file.pyrite` / `file.c` - File operations
- `path.pyrite` / `path.c` - Path manipulation

### String (`string/`)
- `string.pyrite` / `string.c` - String operations
- `format.pyrite` - String formatting

### Serialization (`serialize/`)
- `json.pyrite` / `json.c` - JSON parsing and serialization
- `toml.pyrite` / `toml.c` - TOML parsing

### Numerics (`num/`)
- `tensor.pyrite` / `tensor.c` - Tensor operations and numerical computing

### Networking (`net/`)
- `tcp.pyrite` / `socket.c` - TCP socket networking

### Utilities

- `build_graph/` - Build graph utilities
- `dep_fingerprint/` - Dependency fingerprinting
- `dep_source/` - Dependency source tracking
- `locked_validate/` - Locked validation
- `lockfile/` - Lockfile handling
- `path_utils/` - Path utilities
- `toml/` - TOML parsing (see `toml/README.md`)
- `version/` - Version handling

## Implementation

Most stdlib modules have both:
- **`.pyrite`** - Pyrite interface/API definitions
- **`.c`** - C implementation for runtime functions

This allows the standard library to be partially self-hosted while maintaining performance-critical C implementations.

## Usage

Standard library modules are automatically available in Pyrite programs:

```pyrite
use std::collections::List;
use std::io::file;

fn main():
    let list = List::new(10);
    // ...
```

## See Also

- `forge/src/backend/linker.py` - How stdlib is linked
- `docs/SSOT.md` - Language specification (modular)
- `docs/specification/09-standard-library.md` - Standard library specification
