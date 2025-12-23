---
title: "Implementation Roadmap"
section: 14
order: 14
---

# Implementation Roadmap

To achieve widespread developer adoption, Pyrite must deliver on both technical
excellence and developer experience. This section outlines the prioritized 
roadmap focused on reaching Beta Release (self-hosting capability).

## 14.1 Alpha Release: MVP (Minimum Viable Product)

**Goal:** Prove the core concept with a usable, safe systems language

**Status:** ✅ COMPLETE (1794 passing tests, Alpha v1.1, December 23, 2025)

### Core Language

- Ownership and borrowing system (memory safety) ✓

- Basic types (integers, floats, bool, arrays, structs, enums) ✓

- Control flow (if, loops, match, functions) ✓

- Module system (imports, visibility) ✓

- Error handling (Result types, try operator) ✓

- Tuple literals and destructuring (Alpha v1.1) ✓

- Field and index assignment (Alpha v1.1) ✓

### Compiler

- Error messages with WHAT/WHY/HOW format (section 2) ✓

- Basic --explain system for common errors ✓

- Ownership error diagnostics with timeline views ✓

- Compile to native code (LLVM or MLIR backend) ✓
  - LLVM: Proven, mature optimization infrastructure

  - MLIR: Better for heterogeneous computing (CPU+GPU)

  - Decision: Implementation detail, doesn't affect user-visible semantics

  - Both paths viable: Choose based on compiler team expertise and GPU timeline

#### Note on Compiler Backend Choice

The choice between LLVM and MLIR is an **implementation question**, not a 
language design question:

**LLVM (Traditional Path):**

Pros:

- Mature optimization passes (proven in Clang, Rust, Swift)

- Extensive documentation and community support

- Excellent code generation for CPU targets

- Well-understood by compiler engineers

Cons:

- GPU support requires more infrastructure work

- Less flexible for custom dialects

- Hetereogeneous computing requires more glue code

**MLIR (Modern Path):**

Pros:

- Built for heterogeneous computing (CPU+GPU unified)

- Mojo proves it works for systems + ML domains

- Better for custom optimization passes

- Reusable infrastructure for domain-specific compilers

- Natural fit for tensor operations and GPU kernels

Cons:

- Steeper learning curve for compiler implementation

- Smaller community than LLVM

- May constrain future flexibility in unexpected ways

**Recommendation:**

- **For Beta Release:** LLVM (simpler, proven, sufficient for self-hosting)

- **For GPU (Stable Release):** Consider MLIR if heterogeneous computing is priority

- **If uncertain:** Start with LLVM, migrate later if needed

**Key insight:** This choice affects **how** the compiler is built, not **what** 
Pyrite looks like to users. All language features, semantics, and guarantees 
remain identical regardless of backend.

User-visible behavior (ownership, contracts, SIMD, blame tracking) is defined 
by Pyrite's semantics, not by LLVM or MLIR. The backend is an engineering 
decision for the compiler team, not a language design constraint.

**For this specification:** We assume LLVM for examples (proven path), but MLIR 
is equally valid if compiler team has expertise or GPU support is accelerated.

### Tooling

- quarry new/build/run (basic workflow) ✓

- pyrite run (script mode - single file compilation with caching) HIGH IMPACT ✓
  - Zero-configuration single-file workflow

  - Automatic compilation and caching

  - Shebang support (#!/usr/bin/env pyrite)
  
  - Critical for "first 60 seconds" experience

- quarry test (inline testing) ✓

- quarry fmt (official formatter, zero config) ✓

### Standard Library (Core)

- Collections: List, Map, Set (Generic support in v1.1) ✓

- String and StringBuilder ✓

- File I/O (read/write) ✓

- Basic math ✓

- JSON and TOML support (Alpha v1.1) ✓

- Tensor support (Alpha v1.1) ✓

- TCP Networking (Alpha v1.1) ✓

> **Note:** Script mode was prioritized in Alpha because it addresses the biggest 
> adoption friction point for Python developers. The "first impression" workflow 
> must feel familiar and frictionless.

## 14.2 Beta Release: Self-Hosting Capability

**Goal:** Enable Pyrite compiler to be rewritten in Pyrite itself, eliminating Python dependency

**Critical Requirements for Beta:**

1. Language features sufficient for compiler implementation

2. 100% automated test coverage with all tests passing

3. Cross-platform stability (Windows, Mac, Linux)

4. No critical bugs in any environment

### Language Features (CRITICAL for self-hosting)

- Result[T, E] and Option[T] types BLOCKING ✓
  - Full error handling for compiler error reporting

  - try operator for error propagation

  - Pattern matching on Result/Option

  - Essential for all compiler passes

- Traits and implementations BLOCKING ✓
  - Interface definitions (Display, Clone, Debug)

  - Method dispatch for compiler abstractions

  - Generic trait bounds (T: Display)

  - Required for extensible architecture

- Advanced generics BLOCKING ✓
  - Associated types for collections

  - Where clauses for complex bounds

  - Higher-kinded types (if needed)

  - Compiler uses heavily for type representations

- Full FFI support BLOCKING ✓
  - extern fn declarations for LLVM API

  - Struct layout compatibility with C

  - Function pointer types for callbacks

  - Required for LLVM bindings

- defer and with statements CORE PYRITE ✓
  - Guaranteed cleanup for resource management

  - Python-familiar with statement

  - Required for file handling in compiler

- Compile-time parameterization ALREADY IMPLEMENTED ✓
  - [N: int] syntax working

  - Function specialization working

  - Used for fixed-size buffers

- Two-tier closure model FOUNDATIONAL ✓
  - Parameter closures (fn[...]) for algorithmic helpers

  - Runtime closures (fn(...)) for callbacks

  - Enables zero-cost abstractions

### Compiler Enhancements

- Incremental compilation CRITICAL FOR PRODUCTIVITY ✓
  - Module-level caching with dependency tracking

  - 15-27x faster rebuilds essential for large codebase

  - Rewriting compiler will be ~10K lines, needs fast iteration

- Cost transparency warnings HELPFUL ✓
  - Heap allocations, large copies

  - Performance lints

- Expanded --explain coverage QUALITY ✓
  - All error codes documented

- Enhanced ownership visualizations NICE TO HAVE ✓
  - Flow diagrams with --visual flag

### Language Features (REQUIRED for compiler implementation)

- Full Result[T, E] and Option[T] implementation BLOCKING ✓
  - Error handling throughout compiler

  - try operator for error propagation

  - Comprehensive pattern matching

  - Integration with ownership system

- Traits and trait implementations BLOCKING ✓
  - Define interfaces (Display, Clone, Debug, Iterator)

  - Implement traits for all AST node types

  - Method dispatch for polymorphic code

  - Trait bounds in generics (T: Display)

- Advanced generics BLOCKING ✓
  - Generic structs for compiler data structures

  - Generic enums for Result/Option

  - Associated types (Iterator::Item)

  - Where clauses for complex bounds

- Improved FFI support BLOCKING ✓
  - extern fn with full ABI control

  - Opaque types for C pointers

  - Function pointers for LLVM callbacks

  - Required for LLVM bindings throughout compiler

- String manipulation BLOCKING ✓
  - String formatting (format!() macro or equivalent)

  - String concatenation and slicing

  - UTF-8 handling for source code

  - Required for error messages and code generation

- File I/O (enhanced) BLOCKING ✓
  - Read/write source files

  - Directory traversal for module system

  - Path manipulation for cross-platform

  - Required for multi-file compilation

- HashMap/Dictionary BLOCKING ✓
  - Symbol tables (name → type mapping)

  - Type environment (variable → ownership state)

  - Module registry (path → AST)

  - Essential for all compiler passes

- defer and with statements ALREADY IMPLEMENTED ✓
  - Scope-based cleanup (~95% complete)

  - File resource management (with files)

  - Part of Core Pyrite

- Compile-time parameters ALREADY IMPLEMENTED ✓
  - [N: int] syntax functional

  - Used for compiler optimizations

- Two-tier closures FOUNDATIONAL ✓
  - Parameter closures working

  - Runtime closures functional

  - Required for compiler abstractions

### Compiler Quality

- Incremental compilation CRITICAL ✓
  - Fast rebuilds for 10K+ line compiler codebase

  - Module-level caching required

- Enhanced error messages MAINTAINED ✓
  - WHAT/WHY/HOW format continues

  - All error codes documented

- Full test coverage 100% REQUIRED ✓
  - Every compiler pass tested

  - All language features covered

  - Cross-platform test suite (Windows, Mac, Linux)

  - Zero failing tests before beta

### Tooling (ESSENTIAL for development)

- quarry build/run/test/fmt/clean WORKING ✓
  - Core workflow already functional

- quarry cost HELPFUL ✓
  - Identify performance issues in new compiler

- quarry bloat HELPFUL ✓
  - Track compiler binary size

- quarry fix --interactive NICE TO HAVE ✓
  - Auto-fix for common errors

- quarry explain-type HELPFUL ✓
  - Type introspection during development

### Standard Library (REQUIRED for compiler)

- Collections: List, Map, Set ALREADY IMPLEMENTED ✓
  - Compiler uses extensively

- String and StringBuilder ALREADY IMPLEMENTED ✓
  - Source code manipulation

- File I/O (enhanced) NEEDS WORK ✓
  - Multi-file reading

  - Directory operations

  - Path handling

- JSON/TOML parsing OPTIONAL ✓
  - For Quarry.toml if needed

- HashMap[K, V] CRITICAL ✓
  - Symbol tables

  - Type environments

## 14.3 Stable Release: Advanced Features and Ecosystem

**Goal:** Production-ready for all domains + advanced optimization features

### Advanced Language Features

- Cost transparency attributes (@noalloc, @nocopy, @nosyscall) ✓

- @cost_budget attribute (performance contracts) ✓
  - Compile-time enforcement of cycles/allocs/stack budgets

  - Critical for real-time and safety-critical systems

  - Transforms requirements into compiler-verified contracts

- @noalias attribute for non-aliasing assertions ✓
  - Enables aggressive compiler optimizations

  - Checked at compile-time when possible, runtime in debug

  - 5-15% speedups for memory-bound operations

  - Expert-level feature for performance-critical code

- Compile-time execution (const functions, comptime evaluation) ✓

- Async/await with structured concurrency ✓
  - async with blocks ensure no leaked tasks

  - Addresses Rust's main async criticism

  - Inspired by Swift/Kotlin structured concurrency

- Design by Contract support ✓
  - @requires, @ensures, @invariant for logical correctness

  - Compile-time verification when provable

  - Runtime checking in debug builds (zero cost in release)

  - Integration with SMT solvers (Z3, CVC5)

  - Required for highest safety certification levels

### Advanced Tooling

- pyrite repl ADOPTION ACCELERATOR ✓
  - Interactive development for learning

  - Ownership visualization

  - Instant feedback

- quarry learn LEARNING SYSTEM ✓
  - Interactive exercises

  - Progressive tutorials

- quarry bench (benchmarking framework) ✓

- quarry audit (security vulnerability scanning) ✓

- quarry bindgen (C header → Pyrite bindings) ✓
  - Automatic binding generation from C headers

  - Zig-style header parsing (no manual declarations)

  - Critical for ecosystem bootstrapping

  - Enables effortless use of existing C libraries

- quarry energy UNIQUE DIFFERENTIATOR ✓
  - Energy profiling and battery-life optimization

  - Sustainability awareness (no competitor has this)

  - Critical for mobile, IoT, green computing

  - Platform-specific power measurement APIs

- quarry dev --hot-reload DEVELOPER JOY ✓
  - Live code updates without restart

  - State preservation across reloads

  - Accelerates iteration for games, web, data processing

- quarry perf with Perf.lock PERFORMANCE TRACKING ✓
  - Flamegraph profiling

  - Regression detection

  - Assembly diffs

- quarry tune OPTIMIZATION HELPER ✓
  - Intelligent suggestions

  - Automated fixes

- quarry fix --interactive UX ENHANCEMENT ✓
  - Numbered fix selection

  - Learning through fixing

- quarry layout / explain-aliasing ADVANCED INTROSPECTION ✓
  - Cache-line analysis

  - Padding visualization

  - Aliasing assumptions

- Community metrics dashboard (aspirational: quarry.dev/metrics) ✓
  - Public, real-time performance and adoption data

  - Makes developer adoption metrics measurable

  - Evidence-based advocacy enabler

- Internationalized error messages ✓
  - Native language compiler diagnostics

  - Chinese, Spanish, Hindi, Japanese, and more

  - Professional translations by native speakers

- LSP with full hover/goto/completion ✓

- Debugger integration (lldb/gdb support) ✓

### Standard Library Expansion

- JSON and TOML parsing ✓
  - Configuration file handling

- HTTP client ✓
  - Network operations

- Basic HTTP server ✓
  - Simple server applications

- DateTime and Duration ✓
  - Time handling

- Regex support ✓
  - Pattern matching

- CLI argument parsing ✓
  - Command-line tools

- Async runtime with structured concurrency ✓
  - High-concurrency applications

- Observability (logs, traces, metrics) ✓
  - Production monitoring

- Database drivers (common DBs) ✓
  - Data persistence

- Compression (gzip, etc.) ✓
  - Data compression

- Cryptography (hashing, encryption) ✓
  - Security primitives

- Tensor type for numerical computing (std::numerics) ✓
  - Compile-time shape checking (Tensor[T, (M, N), Layout])

  - Explicit layout control (RowMajor, ColMajor, Strided)

  - Zero-cost slicing through borrowing (TensorView)

  - Integration with SIMD, tiling, and parallelization

  - Fixed-size (stack) and dynamic-size (heap) variants

  - Not a full ML framework - memory layout + indexing foundation

- SIMD module (std::simd) ✓
  - Portable vector types (Vec2, Vec4, Vec8, Vec16)

  - Platform-specific SIMD width detection

  - Explicit SIMD operations (no auto-vectorization magic)

  - Integration with compile-time parameterization

  - CPU multi-versioning (@multi_version attribute)
    - Ship single binary, run fast everywhere

    - Automatic runtime dispatch (SSE2/AVX2/AVX-512/NEON)

    - 2-4x speedup on modern CPUs vs baseline

    - Extended beyond SIMD: POPCNT, BMI2, AES-NI, etc.

    - Cross-architecture support (x86-64, ARM64, RISC-V)

    - Feature-specific optimization variants

- Algorithmic helpers (std::algorithm) ✓
  - vectorize[width=auto] - Ergonomic SIMD loop generation

  - parallelize[workers=auto] - Structured parallel execution

  - tile[block_size=auto] - Cache-aware blocking

  - All use parameter closures (fn[...]) for verified zero-cost abstraction

  - Compose naturally (parallel + SIMD + tiling)

  - Maintains cost transparency (still explicit, now with guaranteed zero-cost)

- Inline storage containers ✓
  - SmallVec[T, N] - Stack-allocated up to N elements

  - SmallString[N] - Small string optimization (SSO)

  - InlineMap[K, V, N] - Inline hash map for small collections

### Ecosystem

- Pyrite Playground (aspirational: play.pyrite-lang.org) ✓
  - Browser-based experimentation

- 1000+ packages on Quarry Registry ✓
  - Community contributions

- Real-world case studies ✓
  - Production deployments

- Corporate adoption stories ✓
  - Enterprise validation

- Supply-chain security tooling ✓
  - quarry audit - Vulnerability scanning with CVE database

  - quarry vet - Dependency review workflow

  - quarry sign/verify - Cryptographic package signing

  - quarry sbom - Software Bill of Materials

### Formal Methods

- Formal semantics specification (Section 15) ✓
  - Operational semantics for ownership and memory model

  - Axiomatic semantics for verification

  - Memory safety theorem and proof sketch

  - Undefined behavior catalog

  - Required for DO-178C Level A, Common Criteria EAL 7

  - Enables external verification tools (Coq, Isabelle, Lean)

  - Academic research foundation

## 14.4 Future Release: Heterogeneous Computing (GPU Support)

**Goal:** Extend Pyrite's "fast everywhere" promise from CPU to GPU

### Language Features

- @kernel attribute for GPU-executable functions FLAGSHIP FEATURE ✓
  - Kernel contract enforcement (@noalloc, @no_panic, @no_recursion)

  - Call-graph blame tracking for GPU constraints

  - Single-source CPU/GPU code with same safety guarantees

  - Explicit kernel boundaries (no automatic offloading)

- GPU memory management primitives ✓
  - Explicit host ↔ device memory transfer

  - Device pointer types (distinct from host pointers)

  - RAII wrappers for automatic cleanup

- GPU launch API ✓
  - Explicit kernel launch with thread/block configuration

  - Synchronization primitives

  - Multi-GPU support

### Compiler

- GPU backend: CUDA (NVIDIA) PRIORITY 1 ✓
  - 80% GPU market share
  - PTX code generation via LLVM
  - CUDA runtime integration

- GPU backend: HIP (AMD) PRIORITY 2 ✓
  - ROCm support for AMD GPUs
  - Shared implementation with CUDA where possible

- GPU backend: Metal (Apple) PRIORITY 3 ✓
  - Apple Silicon GPU support
  - Metal Shading Language generation

- GPU backend: Vulkan Compute CROSS-VENDOR ✓
  - Portable compute shaders
  - Runs on any Vulkan-capable GPU

### Tooling

- quarry build --gpu=cuda/hip/metal/vulkan ✓

- GPU profiling integration (nvprof, rocprof, Instruments) ✓

- Kernel performance analysis tools ✓

### Standard Library

- std::gpu module ✓
  - Launch primitives

  - Memory management

  - Device pointer types

  - Multi-GPU abstractions

- Python interoperability (std::python) STRATEGIC ✓
  - Call Python from Pyrite with explicit GIL boundaries

  - Generate Python extension modules (quarry pyext)

  - Type-safe conversions at boundaries (explicit, cost-transparent)

  - Zero-copy where possible (NumPy array ↔ Pyrite slice)

  - Optional dependency (Python runtime not required for core Pyrite)

  - Adoption wedge for numerical computing (migrate Python bottlenecks)

### Why Future Release (Not Beta/Stable)

GPU support is delayed because:

1. Requires stable CPU-side language (ownership, contracts, blame tracking)

2. Needs mature tooling (quarry cost, quarry perf, error diagnostics)

3. GPU APIs are complex-rushing leads to poor design

4. CPU-only Pyrite already serves 90%+ of use cases

5. Not required for self-hosting compiler

By waiting, Pyrite can apply lessons learned from CPU development to GPU:

- Contract system is proven on CPU → extends naturally to GPU

- Blame tracking teaches CPU restrictions → same for GPU restrictions

- Performance tooling is mature → adapts to GPU profiling

The result: GPU support that feels like "more Pyrite" rather than "different 
language on GPU."

### Impact

GPU support positions Pyrite as: "The systems language that scales from 
embedded microcontrollers to GPU computing, with the same safety and explicitness 
everywhere."

This capability opens use cases not addressed in Beta/Stable:

- Deep learning inference/training

- Scientific computing at scale

- Real-time graphics

- Cryptographic acceleration

- Financial modeling

## 14.5 Success Metrics

### Tracking Progress Toward "Most Admired"

**Quantitative:**

- Stack Overflow survey ranking (target: top 10 admired within 5 years)

- GitHub stars (target: 50k+ within 3 years)

- Quarry Registry packages (target: 10k+ within 5 years)

- Active contributors (target: 500+ within 3 years)

- Production deployments (target: 1000+ companies within 5 years)

**Qualitative:**

- "Compiler errors taught me ownership" (learning indicator)

- "Moved from Rust because syntax is clearer" (differentiation success)

- "Built a kernel in Pyrite, no memory bugs" (safety validation)

- "Faster than C, safer than Rust, easier than both" (positioning achieved)

### Critical Success Factors

The difference between "interesting experiment" and widespread developer adoption is:

1. **Compiler diagnostics quality** (highest ROI)
   Poor errors = frustration, abandonment
   Great errors = learning, delight, advocacy

2. **Tooling excellence** (Quarry must match Cargo)
   Bad tooling = friction, slow adoption
   Great tooling = "it just works," viral growth

3. **Standard library breadth** (batteries included)
   Missing stdlib = dependency hell, decision fatigue
   Complete stdlib = ship real projects immediately

4. **Documentation and learning path** (Playground, tutorials)
   Hard to learn = niche adoption, experts only
   Easy to learn = broad adoption, beginners welcome

5. **Performance delivery** (match C in real benchmarks)
   Slow code = "safety has a cost" narrative loses
   Fast code = "no compromises" narrative wins

All five must be excellent. Excellence in four of five yields "good language." 
Excellence in all five yields a language that achieves widespread developer adoption.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Security and Reliability](13-security.md)

**Next**: [High-ROI Features Summary](15-high-roi.md)
