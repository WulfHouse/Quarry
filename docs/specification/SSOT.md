# Pyrite + Quarry SDK Specification

> **⚠️ ALPHA v1.1 STATUS**
> 
> This project is currently in **Alpha v1.1**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0.

> **⚠️ IMPORTANT: This specification is aspirational and forward-looking**
> 
> This document is a **high-level master specification overview** and **hypothetical wishlist** for what the Pyrite programming language and Quarry SDK are intended to eventually become. It represents the vision and goals for the project, not necessarily the current implementation state.
> 
> **The SSOT may not accurately convey the current state of the project and monorepo.** For information about what is currently implemented, see:
> - [LIMITATIONS.md](../LIMITATIONS.md) - Known limitations and incomplete features
>
> - [CHANGELOG.md](../CHANGELOG.md) - What has actually been released
>
> - [README.md](../README.md) - Current project status
>
> - Source code and tests - Actual implementation

This is the complete high-level specification for the Pyrite programming language and Quarry SDK. The specification is organized into modules for easier navigation and maintenance.

For complete technical, itemized specifications with detailed implementation guidance, see [`technical-ssot.md`](../technical-ssot.md). That document provides a zero-to-final map of every feature, decomposed recursively until each item is implementable in a single PR-sized chunk with objective Definition of Done and tests.

## Table of Contents

1. [Design Goals and Philosophy](01-design-philosophy.md)

2. [Compiler Diagnostics and Error Messages](02-diagnostics.md)

3. [Syntax Overview](03-syntax.md)

4. [Types and Type System](04-type-system.md)

5. [Memory Management and Ownership](05-memory-model.md)

6. [Control Flow](06-control-flow.md)

7. [Advanced Features (Traits, Generics, and More)](07-advanced-features.md)

8. [Tooling: Quarry Build System](08-tooling.md)

9. [Standard Library and Ecosystem](09-standard-library.md)

10. [Pyrite Playground and Learning Experience](10-playground.md)

11. [Foreign Function Interface (FFI) and Interoperability](11-ffi.md)

12. [Marketing and Positioning](12-marketing.md)

13. [Security and Reliability](13-security.md)

14. [Implementation Roadmap](14-roadmap.md)

15. [High-ROI Features Summary](15-high-roi.md)

16. [Formal Semantics and Verification](16-formal-semantics.md)

17. [Conclusion](17-conclusion.md)

## Quick Navigation

### Core Language

- [Design Philosophy](01-design-philosophy.md) - Design goals and principles

- [Syntax Overview](03-syntax.md) - Language syntax and grammar

- [Type System](04-type-system.md) - Types and type checking

- [Memory Model](05-memory-model.md) - Ownership and memory management

- [Control Flow](06-control-flow.md) - Control structures

### Advanced Features

- [Advanced Features](07-advanced-features.md) - Traits, generics, metaprogramming

- [FFI](11-ffi.md) - Foreign function interface

### Tooling and Ecosystem

- [Compiler Diagnostics](02-diagnostics.md) - Error messages and diagnostics

- [Quarry Build System](08-tooling.md) - Build system and package manager

- [Standard Library](09-standard-library.md) - Standard library documentation

- [Playground](10-playground.md) - Interactive learning environment

### Additional Topics

- [Security](13-security.md) - Security and reliability

- [Formal Semantics](16-formal-semantics.md) - Formal verification

- [Roadmap](14-roadmap.md) - Implementation roadmap

## About This Specification

This specification is the Single Source of Truth (SSOT) for the **intended design and vision** of the Pyrite programming language. It describes the **aspirational goals** for:

- Language syntax and semantics

- Type system and memory model

- Standard library APIs

- Tooling and build system

- Best practices and design patterns

**Important:** This specification represents the **target state** and **vision** for Pyrite, not necessarily what is currently implemented. Features described here may be:

- ✅ Fully implemented

- 🚧 Partially implemented

- 📋 Planned but not yet implemented

- 💡 Aspirational/hypothetical

For the current implementation status, see [LIMITATIONS.md](../LIMITATIONS.md) and the actual source code.

The specification is maintained as modular markdown files for easier navigation and maintenance. The original monolithic `SSOT.txt` file is preserved as a backup.

## Contributing

When updating the specification:

1. Edit the relevant module file in `docs/specification/`

2. Update cross-references if needed

3. Regenerate `SSOT.txt` if required (using `scripts/regenerate_ssot.py`)

## See Also

- [technical-ssot.md](./technical-ssot.md) - Complete technical, itemized specifications with zero-to-final implementation guidance

- [SSOT_DISCLAIMER.md](../SSOT_DISCLAIMER.md) - Important information about this specification

- [Compiler Source](../forge/src/README.md) - Compiler implementation

- [Bootstrap Guide](../bootstrap.md) - Self-hosting process
