# Changelog

> **⚠️ ALPHA v1.0 STATUS**
> 
> This project is currently in **Alpha v1.0**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0.

All notable changes to Quarry (Pyrite SDK) and Forge (Pyrite compiler) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for Beta Release (1.0.0-beta) - 2026
- Complete iterator protocol implementation
- Result type error propagation
- Enhanced mutability checking
- FFI bindings for AST and tokens bridges

**Note:** The beta release (1.0.0-beta) is planned for 2026. The features listed above represent goals for the beta release, not current implementation status. See [LIMITATIONS.md](LIMITATIONS.md) for what is currently implemented.

## [1.0.0-alpha] - 2025

**Current Status:** Alpha v1.0

**First created:** December 12, 2025

**⚠️ Important:** This is an alpha release. All content in this repository is subject to change and may contain inconsistencies as development progresses toward Beta v1.0. APIs, documentation, code structure, and specifications may change without notice.

### Added
- Initial alpha release
- Basic compiler functionality
- Core language features
- Standard library foundation
- Tuple patterns in variable declarations (e.g., `let (a, b) = value`)
- Tuple literal syntax (e.g., `(1, 2, 3)`)
- Pattern matching support in variable declarations

### Acknowledgments

**Alpha Testing:**
- **Dylan Barras** - Alpha tester for the Pyrite language and Quarry SDK, Mac OS compatibility, Linux compatibility, and embedded systems programming

**Logo Design:**
- **Dylan Barras** - Creator and designer of the official Pyrite logo

---

## Version History

- **1.0.0-alpha** - Initial alpha release (2025, first created December 12, 2025) - **Current Status**
- **1.0.0-beta** - Beta release (planned for 2026) - **Future Release**

## Release Notes

### Alpha Release (1.0.0-alpha) - 2025

**Current Status:** This is the current alpha release of the Quarry SDK and Forge (the Pyrite compiler).

**Note:** Pyrite was first invented on December 12, 2025. This alpha release represents the initial public release of the project.

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

**Note:** The beta release is a future milestone. Current status is Alpha v1.0. See [LIMITATIONS.md](LIMITATIONS.md) for what is currently implemented.
