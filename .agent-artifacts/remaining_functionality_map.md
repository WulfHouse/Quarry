# Remaining Functionality Map
**Generated:** 2025-12-23  
**Source:** `docs/specification/technical-ssot.md` (SSOT)  
**Current State:** M11 in progress (SPEC-LANG-0409 complete, next: SPEC-LANG-0510)

## Executive Summary

Based on the SSOT analysis:
- **Total SPECs:** ~343 (41 NODEs, 302 LEAFs)
- **Current Progress:** M11 partially complete
- **Remaining:** M11-M15 (Beta + Stabilization phases)

## Current Status (from memory.txt)

- **Milestone:** M11 (Language Features & Verification)
- **Last Completed:** SPEC-LANG-0409 (SMT Solver Integration)
- **Next:** SPEC-LANG-0510 (Algorithmic Helpers via Parameter Closures)
- **Test Status:** 552/552 tests passing (fast suite)

---

## Remaining Functionality by Milestone

### M11: Language Features & Verification (IN PROGRESS)

**Goal:** Design by Contract and advanced compiler passes

**Status:** Partially complete
- ✅ SPEC-LANG-0401: Design by Contract (DBC) - EXISTS-TODAY
- ✅ SPEC-LANG-0402: @requires preconditions - EXISTS-TODAY  
- ✅ SPEC-LANG-0403: @ensures postconditions - EXISTS-TODAY
- ✅ SPEC-LANG-0404: @invariant class invariants - EXISTS-TODAY
- ✅ SPEC-LANG-0405: Compound assignment operators - DONE
- ✅ SPEC-LANG-0406: Compile-time contract verification - EXISTS-TODAY
- ✅ SPEC-LANG-0407: Contract propagation and blame - EXISTS-TODAY
- ✅ SPEC-LANG-0408: @safety_critical attribute - EXISTS-TODAY
- ✅ SPEC-LANG-0409: SMT Solver Integration - DONE
- ⏳ **SPEC-LANG-0510: Algorithmic helpers via parameter closures** - IN PROGRESS (blocked on parameter closure type support in function signatures)
- ⏳ SPEC-LANG-0511: Stdlib Closure Guidelines - PLANNED
- ⏳ SPEC-LANG-1101: Observability hooks - PLANNED
- ⏳ SPEC-LANG-1102: Allocation tracking - PLANNED
- ⏳ SPEC-LANG-1103: Performance counters - PLANNED
- ⏳ SPEC-LANG-1104: Debug assertions - PLANNED
- ⏳ SPEC-LANG-1201: FFI safety checks - PLANNED
- ⏳ SPEC-LANG-1203: C ABI compatibility - PLANNED
- ⏳ SPEC-LANG-1501: Formal verification support - PLANNED
- ⏳ SPEC-FORGE-0201: Contract codegen - PLANNED
- ⏳ SPEC-FORGE-0202: Performance governance - PLANNED
- ⏳ SPEC-FORGE-0203: Allocation tracking pass - PLANNED
- ⏳ SPEC-FORGE-0204: Optimization passes - PLANNED
- ⏳ SPEC-FORGE-0207: Dead code elimination - PLANNED
- ⏳ SPEC-FORGE-0208: Constant propagation - PLANNED
- ⏳ SPEC-QUARRY-0031: Contract testing framework - PLANNED
- ⏳ SPEC-QUARRY-0032: Performance regression detection - PLANNED
- ⏳ SPEC-QUARRY-0307: Security audit integration - PLANNED
- ⏳ SPEC-QUARRY-0308: Vulnerability scanning - PLANNED

**Remaining in M11:** ~24 SPECs

---

### M12: Learning & Exploration Tools (NOT STARTED)

**Goal:** Interactive tools for developer onboarding and visualization

**All PLANNED:**
- SPEC-QUARRY-0201: REPL (Read-Eval-Print Loop)
- SPEC-QUARRY-0202: Ownership visualization
- SPEC-QUARRY-0203: Type inference visualization
- SPEC-QUARRY-0204: Interactive tutorials
- SPEC-QUARRY-0205: Code playground
- SPEC-QUARRY-0007: Documentation generation
- SPEC-QUARRY-0025: Example projects
- SPEC-QUARRY-0030: Auto-fix suggestions
- SPEC-QUARRY-0033: Learning exercises
- SPEC-QUARRY-0034: Progress tracking
- SPEC-QUARRY-0035: Achievement system
- SPEC-QUARRY-0401: Ecosystem analytics
- SPEC-QUARRY-0402: Package registry API
- SPEC-QUARRY-0403: Dependency graph visualization
- SPEC-QUARRY-0404: Community metrics
- SPEC-QUARRY-0405: Package search
- SPEC-QUARRY-0406: Version compatibility checker
- SPEC-QUARRY-0501: LSP server foundation
- SPEC-QUARRY-0502: LSP hover information
- SPEC-QUARRY-0503: LSP code completion
- SPEC-QUARRY-0504: LSP go-to-definition
- SPEC-QUARRY-0505: LSP diagnostics
- SPEC-LANG-1301: Documentation comments
- SPEC-LANG-1302: Doc test framework

**Total in M12:** 24 SPECs

---

### M13: Performance Analysis Tooling (NOT STARTED)

**Goal:** Tooling for static and runtime performance analysis

**All PLANNED:**
- SPEC-QUARRY-0101: Performance profiling
- SPEC-QUARRY-0102: Cost analysis tool
- SPEC-QUARRY-0103: Memory profiling
- SPEC-QUARRY-0104: Benchmark framework
- SPEC-QUARRY-0108: Performance regression tests
- SPEC-QUARRY-0110: Hotspot detection
- SPEC-QUARRY-0111: Call graph analysis
- SPEC-QUARRY-0112: Performance budgets
- SPEC-QUARRY-0113: Optimization suggestions
- SPEC-QUARRY-0114: Cross-platform benchmarking
- SPEC-QUARRY-0115: Performance lockfile
- SPEC-QUARRY-0036: Build performance tracking
- SPEC-LANG-0601: SIMD vector types
- SPEC-LANG-0602: SIMD operations
- SPEC-LANG-0603: SIMD intrinsics
- SPEC-LANG-0604: Vectorization hints
- SPEC-LANG-0605: SIMD codegen
- SPEC-LANG-0901: Memory pool allocators
- SPEC-LANG-0902: Custom allocators
- SPEC-LANG-0903: Allocation strategies
- SPEC-FORGE-0305: Inlining optimization
- SPEC-FORGE-0306: Loop optimization
- SPEC-FORGE-0307: Register allocation
- SPEC-FORGE-0308: Instruction scheduling

**Total in M13:** 24 SPECs

---

### M14: Concurrency & Parallelism (NOT STARTED)

**Goal:** Safe multi-threading and structured concurrency

**All PLANNED:**
- SPEC-LANG-1001: Thread primitives
- SPEC-LANG-1002: Mutex and locks
- SPEC-LANG-1003: Channels (message passing)
- SPEC-LANG-1004: Async/await syntax
- SPEC-LANG-1005: Structured concurrency
- SPEC-LANG-0701: GPU compute kernels
- SPEC-LANG-0702: GPU memory management
- SPEC-LANG-0703: GPU synchronization
- SPEC-LANG-0704: GPU codegen
- SPEC-LANG-0808: Parallel collections
- SPEC-LANG-0809: Work-stealing scheduler
- SPEC-LANG-0810: Concurrent data structures

**Total in M14:** 12 SPECs

---

### M15: Supply-Chain Security (NOT STARTED)

**Goal:** Verifiable builds and dependency auditing

**All PLANNED:**
- SPEC-QUARRY-0301: Dependency vulnerability scanning
- SPEC-QUARRY-0302: SBOM (Software Bill of Materials) generation
- SPEC-QUARRY-0303: Signed packages
- SPEC-QUARRY-0304: Package integrity verification
- SPEC-QUARRY-0305: Security policy enforcement
- SPEC-QUARRY-0306: Audit logging

**Total in M15:** 6 SPECs

---

## Summary Statistics

### By Status
- **EXISTS-TODAY/DONE:** ~150 SPECs (M0-M10 mostly complete, M11 partial)
- **PLANNED:** ~193 SPECs (M11-M15)
- **Total:** ~343 SPECs

### By Phase
- **Phase 0 (Foundations):** ✅ Complete (M0-M1)
- **Phase 1 (Self-hosting):** ✅ Complete (M2-M4)
- **Phase 2 (Alpha):** ✅ Complete (M5-M8)
- **Phase 3 (Beta):** 🔄 In Progress
  - M9: ✅ Complete
  - M10: ✅ Complete
  - M11: 🔄 ~42% complete (10/33 SPECs)
  - M12: ⏳ Not started (0/24 SPECs)
- **Phase 4 (Stabilization):** ⏳ Not started
  - M13: ⏳ Not started (0/24 SPECs)
  - M14: ⏳ Not started (0/12 SPECs)
  - M15: ⏳ Not started (0/6 SPECs)

### Remaining Work Breakdown

**Immediate (M11):**
- 23 SPECs remaining in current milestone
- Focus: Algorithmic helpers (blocked on type system), Result types, observability, FFI safety

**Short-term (M12):**
- 24 SPECs for developer tooling
- Focus: REPL, visualization, LSP, documentation

**Medium-term (M13):**
- 24 SPECs for performance
- Focus: Profiling, SIMD, optimization passes

**Long-term (M14-M15):**
- 18 SPECs for concurrency and security
- Focus: Threading, async, GPU, supply-chain security

---

## Critical Path Items (High Priority)

### Blocking Stage2 Self-Hosting
1. **SPEC-LANG-0510:** Algorithmic helpers (blocked on parameter closure type support in function signatures)
2. **SPEC-LANG-0510/0511:** Result types and try operator (error handling)
3. **SPEC-FORGE-0201:** Contract codegen (runtime contract checking)

### Blocking Beta Release
1. **M12:** All learning tools (REPL, LSP, docs)
2. **M13:** Performance tooling (profiling, optimization)
3. **M14:** Concurrency primitives
4. **M15:** Security tooling

### Nice-to-Have (Post-Beta)
- GPU compute (SPEC-LANG-0701-0704)
- Advanced SIMD (SPEC-LANG-0601-0605)
- Formal verification (SPEC-LANG-1501)

---

## Implementation Notes

### Current Blocker
- **Stage2 Build:** Stage1 successfully built, but cannot yet compile all Pyrite modules
- **Reason:** Stage1 is minimal compiler; needs more language features to compile full compiler
- **Solution:** Complete remaining M11 SPECs, especially contract inheritance and Result types

### Test Coverage
- **Current:** 1964/1967 tests passing (99.8%)
- **Target:** 100% for Beta release
- **Gap:** 3 failing tests (bootstrap-related, now fixed for Stage1)

### Next Steps
1. Complete SPEC-LANG-0510 (Algorithmic helpers - needs parameter closure type support in parser/type checker)
2. Implement Result types (SPEC-LANG-0510, 0511)
3. Add contract codegen (SPEC-FORGE-0201)
4. Verify Stage2 can build
5. Proceed to M12 (Learning tools)

### Recent Completions
- **SPEC-LANG-0409:** SMT Solver Integration - Implemented `quarry verify` command with Z3/CVC5 support for formal contract verification. Added SMT-LIB translation for Pyrite contract expressions. 14 unit tests added, all passing.

---

## Dependencies Graph

```
M11 (current) → M12 → M13
     ↓           ↓      ↓
   Stage2    LSP/Docs  Perf
     ↓           ↓      ↓
   M14 ←─────────┴──────┘
     ↓
   M15
```

**Key Dependencies:**
- M12 depends on M11 (contracts needed for tooling)
- M13 depends on M10 (benchmarking needs stdlib)
- M14 depends on M6 (ownership for thread safety)
- M15 depends on M4 (dependency resolution)

---

*This map is generated from the SSOT and should be updated as SPECs are completed.*

