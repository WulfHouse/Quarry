# Pyrite Language Specification Modules

> **⚠️ IMPORTANT: Aspirational Specification**
> 
> This specification represents the **intended design and vision** for Pyrite, not necessarily the current implementation state. It is a **high-level master specification overview** and **hypothetical wishlist** for what the project is intended to eventually become.
> 
> **The SSOT may not accurately convey the current state of the project and monorepo.** For current implementation status, see [LIMITATIONS.md](../../LIMITATIONS.md) and the source code.

This directory contains the modularized Pyrite programming language specification. The specification has been split into logical modules for easier navigation, maintenance, and traversal.

## Structure

The specification is organized into 17 modules:

### Core Language
- **01-design-philosophy.md** - Design goals and principles
- **03-syntax.md** - Language syntax and grammar
- **04-type-system.md** - Types and type checking
- **05-memory-model.md** - Ownership and memory management
- **06-control-flow.md** - Control structures

### Advanced Features
- **07-advanced-features.md** - Traits, generics, metaprogramming
- **11-ffi.md** - Foreign function interface

### Tooling and Ecosystem
- **02-diagnostics.md** - Error messages and diagnostics
- **08-tooling.md** - Quarry build system and package manager
- **09-standard-library.md** - Standard library documentation
- **10-playground.md** - Interactive learning environment

### Additional Topics
- **12-marketing.md** - Marketing and positioning
- **13-security.md** - Security and reliability
- **14-roadmap.md** - Implementation roadmap
- **15-high-roi.md** - High-ROI features summary
- **16-formal-semantics.md** - Formal verification
- **17-conclusion.md** - Conclusion and vision

## Navigation

- **Main Index**: [SSOT.md](../SSOT.md) - Complete table of contents and navigation
- **Original File**: [SSOT.txt](../SSOT.txt) - Preserved as backup/archive

## Module Format

Each module file includes:
- **Frontmatter**: Metadata (title, section number, order)
- **Content**: Specification content from original SSOT.txt
- **Navigation**: Links to previous/next sections

## Benefits of Modularization

1. **Easier Navigation**: Find specific topics quickly
2. **Better Maintenance**: Update individual sections without editing huge file
3. **Version Control**: Smaller, focused diffs
4. **AI Agent Traversal**: Clear structure, easy to navigate
5. **Collaboration**: Multiple people can work on different sections
6. **Performance**: Faster to load/edit individual sections
7. **Searchability**: Better search results in smaller files

## Contributing

When updating the specification:
1. Edit the relevant module file
2. Update cross-references if needed
3. Test links work correctly
4. Update main index (SSOT.md) if adding new sections

## See Also

- [SSOT_DISCLAIMER.md](../SSOT_DISCLAIMER.md) - Important information about this specification
- [Main Specification Index](../SSOT.md)
- [LIMITATIONS.md](../../LIMITATIONS.md) - Current implementation status
- [Compiler Source](../../forge/src/README.md)
- [Bootstrap Guide](../bootstrap.md)
