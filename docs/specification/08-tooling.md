---
title: "Tooling: Quarry Build System"
section: 8
order: 8
---

# Tooling: Quarry Build System

================================================================================

Pyrite's official build system and package manager is Quarry. The design 
philosophy mirrors Cargo (Rust's beloved build tool): provide one obvious 
workflow that handles everything, eliminate configuration complexity, and make 
the right thing the easy thing.

Developer surveys consistently show that great tooling is essential for language 
adoption. Quarry is designed as a first-class component of Pyrite, not an 
afterthought.

8.1 Core Quarry Workflow
--------------------------------------------------------------------------------

Single Command Philosophy
~~~~~~~~~~~~~~~~~~~~~~~~~

Quarry provides one intuitive command for each common task:

    quarry new myproject          # Create new project
    quarry build                  # Compile (debug mode)
    quarry build --release        # Compile (optimized)
    quarry run                    # Build and execute
    quarry test                   # Run all tests
    quarry bench                  # Run benchmarks
    quarry doc                    # Generate documentation
    quarry fmt                    # Format all code
    quarry lint                   # Run linter
    quarry clean                  # Remove build artifacts
    quarry publish                # Publish to package registry

No makefiles, no build scripts, no configuration hell. It just works.

Script Mode: Single-File Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For rapid prototyping, learning, and simple scripts, Pyrite supports a 
zero-configuration single-file workflow that feels like Python but compiles to 
native code:

    pyrite run hello.pyrite       # Compile and execute single file
    pyrite build hello.pyrite     # Compile to executable
    pyrite hello.pyrite           # Shorthand for 'run'

No project structure required. No Quarry.toml needed. Just write code and run it.

Example workflow:

    # Create a simple script
    $ cat > hello.pyrite
    fn main():
        print("Hello, Pyrite!")
    ^D
    
    # Run it immediately
    $ pyrite run hello.pyrite
    Hello, Pyrite!
    
    # Compile to standalone executable
    $ pyrite build hello.pyrite
    Compiling hello.pyrite → hello (or hello.exe on Windows)
    
    $ ./hello
    Hello, Pyrite!

Shebang Support
~~~~~~~~~~~~~~~

On Unix-like systems, Pyrite scripts can use shebang lines for direct execution:

    #!/usr/bin/env pyrite
    
    fn main():
        print("Executable Pyrite script!")

Make the file executable and run:

    $ chmod +x script.pyrite
    $ ./script.pyrite
    Executable Pyrite script!

Script Mode Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Script mode is implemented as intelligent caching:

  1. **First run:** Compiles to ~/.cache/pyrite/scripts/<hash>/binary
  2. **Subsequent runs:** Reuses cached binary if source unchanged
  3. **Automatic recompilation:** Detects source changes and recompiles
  4. **Full ownership checking:** Script mode uses the same compiler with all 
     safety guarantees
  5. **Zero runtime overhead:** Cached binaries are native executables, not 
     interpreted

This means script mode has the convenience of Python's `python script.py` with 
the performance of compiled native code.

Cache management:

    pyrite cache clean            # Remove all cached scripts
    pyrite cache list             # Show cached scripts
    pyrite cache clear hello.pyrite  # Remove specific script cache

Why Script Mode Matters
~~~~~~~~~~~~~~~~~~~~~~~~

Script mode eliminates the biggest friction point for Python developers trying 
Pyrite:

  • **Instant gratification:** Write code, run code, see results
  • **No ceremony:** No project structure until you need it
  • **Natural progression:** Start with scripts, graduate to projects
  • **Learning-friendly:** Beginners can experiment immediately
  • **Still fast:** Caching means second run is instant

This addresses the "first 60 seconds" problem: a Python developer's first 
experience with Pyrite should feel familiar, not foreign.

Comparison:

    # Python
    $ python script.py           # Interpreted, ~100ms startup
    
    # Pyrite script mode
    $ pyrite run script.pyrite   # Compiled + cached, ~1ms after first run
    
    # Pyrite project mode
    $ cd project && quarry run   # Full build system

All three workflows coexist. Use the right tool for the job.

Migration Path
~~~~~~~~~~~~~~

When a script grows complex enough to need dependencies, migrate to project mode:

    $ quarry init              # Convert current directory to Quarry project
    $ mv script.pyrite src/main.pyrite
    $ quarry add dependency-name
    $ quarry build

Quarry detects single-file scripts and can auto-generate appropriate Quarry.toml.

Project Structure
~~~~~~~~~~~~~~~~~

quarry new creates a standard layout:

    myproject/
    ├── Quarry.toml        # Project manifest
    ├── src/
    │   └── main.pyrite    # Entry point
    ├── tests/
    │   └── test_main.pyrite
    └── docs/
        └── README.md

Quarry.toml example:

    [package]
    name = "myproject"
    version = "0.1.0"
    authors = ["Your Name <you@example.com>"]
    edition = "2025"
    
    [dependencies]
    json = "1.2"
    http-client = "3.0"
    
    [dev-dependencies]
    test-utils = "0.5"

8.2 Dependency Management
--------------------------------------------------------------------------------

Declarative Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

Dependencies are declared in Quarry.toml with semantic versioning:

    [dependencies]
    crypto = "2.1"          # Any 2.x version >= 2.1
    parser = "=1.5.3"       # Exact version
    utils = { git = "https://github.com/user/utils.git", branch = "main" }

quarry build automatically:
  • Downloads dependencies
  • Resolves version conflicts
  • Generates Quarry.lock (lockfile for reproducibility)
  • Caches builds for speed

Reproducible Builds
~~~~~~~~~~~~~~~~~~~

Quarry.lock ensures every developer/CI system builds identical binaries:

    [[package]]
    name = "crypto"
    version = "2.1.4"
    checksum = "a8f39d..."
    
    [[package]]
    name = "parser"
    version = "1.5.3"
    checksum = "b3c82f..."

Lockfile committed to version control guarantees reproducibility across 
environments and time.

8.3 Official Package Registry
--------------------------------------------------------------------------------

Pyrite packages are published to the official Quarry Registry (quarry.dev):

    quarry publish

Publishing requirements:
  • Semantic versioning
  • Documentation for public APIs
  • Passing tests (quarry test must succeed)
  • License declaration
  • Security audit for unsafe code (optional but recommended)

Discovery and search:

    quarry search "json parser"
    quarry info json-parser

Registry provides:
  • API documentation (auto-generated)
  • Download statistics
  • Security advisories
  • Dependency graphs
  • Version compatibility matrices

8.4 Testing Framework
--------------------------------------------------------------------------------

Built-in Test Support
~~~~~~~~~~~~~~~~~~~~~

Tests are first-class in Pyrite:

    # In src/math.pyrite
    fn add(a: int, b: int) -> int:
        return a + b
    
    @test
    fn test_add():
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
    
    @test
    fn test_add_overflow():
        # Tests can use Result types
        match add(MAX_INT, 1):
            Err(_):
                pass  # Expected overflow in debug mode
            Ok(_):
                fail("Should have overflowed")

Run tests:

    quarry test                    # All tests
    quarry test test_add          # Specific test
    quarry test --verbose         # Detailed output

Benchmark Support
~~~~~~~~~~~~~~~~~

Performance testing built-in:

    @bench
    fn bench_parse_json(b: &mut Bencher):
        let data = load_test_data()
        b.iter(fn():
            parse_json(data)
        )

Run benchmarks:

    quarry bench                   # Run all benchmarks
    quarry bench --save baseline   # Save baseline for comparison

8.5 Code Formatting
--------------------------------------------------------------------------------

Official Formatter
~~~~~~~~~~~~~~~~~~

quarry fmt formats all code according to official style guide:

    quarry fmt                     # Format entire project
    quarry fmt src/parser.pyrite   # Format specific file
    quarry fmt --check             # Check without modifying (for CI)

No configuration options. Zero style debates. One canonical format.

Formatting rules:
  • 4 spaces for indentation (enforced)
  • Maximum line length: 100 characters
  • Consistent spacing around operators
  • Idiomatic pattern for common constructs

Example transformation:

    # Before
    fn   foo(x:int,y:int)->int:
        return    x+y

    # After quarry fmt
    fn foo(x: int, y: int) -> int:
        return x + y

8.6 Learning Profile Mode
--------------------------------------------------------------------------------

To support Pyrite's goal of being approachable to beginners, Quarry provides a 
"Learning Profile" that packages beginner-friendly defaults into a one-command 
setup:

    quarry new --learning my_project

This creates a project configured for gentle onboarding:

  • Enables --core-only mode (rejects advanced features)
  • Sets beginner lint level (quarry lint --level=beginner)
  • Includes extra IDE hover help
  • Forbids unsafe blocks by default
  • Configures progressive learning paths in tooling
  • Adds commented examples in generated files

The Learning Profile is purely a packaging of existing features - no new semantics, 
just a curated "beginner bundle" that grows with the developer:

Configuration (Quarry.toml):

    [profile.learning]
    core-only = true
    lint-level = "beginner"
    unsafe-forbidden = true
    extra-diagnostics = true
    suggest-alternatives = true

Migration path:

    # After mastering basics, disable learning mode
    quarry config set learning false
    
    # Or migrate incrementally
    quarry config set core-only false  # Enable advanced features
    quarry config set lint-level intermediate

Benefits:
  • Zero new language complexity (just configuration)
  • One-command setup for educators and self-learners
  • Natural graduation path as skills advance
  • All code remains valid Pyrite (no dialect fragmentation)

Marketing impact: "Pyrite has a beginner mode" is a powerful message for 
Python developers exploring systems programming.

Implementation: Beta Release (after core compiler and lints are stable)

8.7 Interactive REPL (Beta Release)
--------------------------------------------------------------------------------

To deliver on Pyrite's promise of Python-like approachability, the language 
provides an interactive Read-Eval-Print Loop (REPL) with ownership visualization 
and cost transparency built in. This is essential for the "Pythonic" claim - 
Python developers expect instant experimentation.

Command Usage
~~~~~~~~~~~~~

    pyrite repl                      # Launch interactive shell
    pyrite repl --explain            # Enhanced mode with ownership visualization
    pyrite repl --script=setup.py    # Load script before interactive session

Basic REPL Workflow
~~~~~~~~~~~~~~~~~~~

    $ pyrite repl
    
    Pyrite 1.0.0 (2025-12-18)
    Type :help for help, :quit to exit
    
    >>> let x = 5
    let x: int = 5
    
    >>> let data = List[int]([1, 2, 3])
    let data: List[int] = List[int]([1, 2, 3])
    [Heap] [Move] Stack: 24B, Heap: 12B
    
    >>> data.push(4)
    error[P0594]: cannot borrow 'data' as mutable
      = note: 'data' declared with 'let' (immutable)
      = help: Use 'var data' to allow mutation
    
    >>> var mutable_data = List[int]([1, 2, 3])
    var mutable_data: List[int] = List[int]([1, 2, 3])
    
    >>> mutable_data.push(4)
    () ← pushed successfully
    
    >>> mutable_data
    List[int]([1, 2, 3, 4])

Enhanced REPL Commands
~~~~~~~~~~~~~~~~~~~~~~~

The REPL provides special commands for exploration:

    >>> :type data
    Type: List[int]
    Badges: [Heap] [Move] [MayAlloc]
    Stack: 24 bytes, Heap: 16 bytes (capacity for 4 elements)
    Owner: 'data', Not moved, Not borrowed
    
    >>> :ownership data
    Ownership State for 'data'
    ==========================
    Owner: 'data' (line 5)
    Moved: No
    Borrowed: No active borrows
    
    Next operations:
      ✓ Can read: data.length(), data[0], etc.
      ✓ Can mutate: data.push(), data.clear(), etc.
      ⚠️  Passing to function will move (use &data to borrow)
    
    >>> :cost
    Session Cost Analysis
    =====================
    Allocations: 2 (40 bytes)
      • Line 5: List[int].new() - 24 bytes
      • Line 8: mutable_data.push(4) - 16 bytes (reallocation)
    
    Copies: 0
    Total memory: 40 bytes
    
    >>> :explain P0234
    [Opens detailed error explanation for P0234]
    
    >>> :clear
    [Clears session, resets state]

Ownership Visualization Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With --explain flag, REPL shows ownership changes in real-time:

    $ pyrite repl --explain
    
    >>> let data = List[int]([1, 2, 3])
    
    ┌─────┐
    │data │ ← OWNER (owns heap allocation)
    └─────┘
    
    >>> process(data)
    
    data ──[MOVED]──> process()
    
    >>> data.length()
    
    error: Cannot use moved value
    
    ┌─────┐
    │data │ ← INVALID (moved on line 2)
    └─────┘
    
    Fix suggestions:
      1. process(&data)  # Borrow instead
      2. data.clone()    # Copy before moving

This real-time visualization makes ownership tangible - learning happens 
immediately, not after compilation.

Function Definitions
~~~~~~~~~~~~~~~~~~~~

Define functions interactively:

    >>> fn add(a: int, b: int) -> int:
    ...     return a + b
    ... 
    fn add(a: int, b: int) -> int
    
    >>> add(5, 3)
    8
    
    >>> fn process[N: int](arr: [int; N]) -> int:
    ...     var sum = 0
    ...     for x in arr:
    ...         sum += x
    ...     return sum
    ... 
    fn process[N: int](arr: [int; N]) -> int
    
    >>> process[3]([1, 2, 3])
    6

Multi-Line Editing
~~~~~~~~~~~~~~~~~~

REPL supports multi-line constructs with intelligent continuation:

    >>> for i in 0..5:
    ...     print(i)
    ... 
    0
    1
    2
    3
    4

Session Management
~~~~~~~~~~~~~~~~~~

    :save session.pyr               # Save session to file
    :load session.pyr               # Load previous session
    :history                        # Show command history
    :clear                          # Reset session state

Import Support
~~~~~~~~~~~~~~

Import modules during interactive session:

    >>> import math
    >>> math.sqrt(16.0)
    4.0
    
    >>> import json
    >>> json.parse('{"key": "value"}')
    Ok(Object({"key": "value"}))

Performance Mode
~~~~~~~~~~~~~~~~

For performance-critical experimentation:

    >>> :perf start                 # Begin performance tracking
    >>> expensive_computation()
    >>> :perf stop
    
    Performance Profile
    ===================
    Duration: 234ms
    Allocations: 1,247 (1.2 MB)
    Peak memory: 2.4 MB

Why REPL Is Essential
~~~~~~~~~~~~~~~~~~~~~

The absence of a REPL would be a **critical gap** for Pyrite's positioning:

**Python developers expect it:**
  • REPL is 50% of Python's "instant gratification" appeal
  • Exploration-driven learning is how beginners understand concepts
  • "Just try it" is more powerful than "read about it"
  • Without REPL, "Pythonic systems language" claim feels hollow

**Learning acceleration:**
  • Try ownership patterns instantly without compilation
  • See borrow checker feedback in real-time
  • Experiment with types, memory layout, costs interactively
  • Reduce friction from "change code → compile → run" to "just try"

**Competitive necessity:**
  • Rust: Has REPL (evcxr) but third-party, not built-in
  • Python: REPL is flagship feature
  • JavaScript: Node.js REPL is critical to adoption
  • Swift: Has REPL (swift repl) for iOS development
  • Mojo: Has REPL (mojo repl) with instant feedback

**Teaching impact:**
  • Instructors can demonstrate concepts live
  • Students experiment during lectures
  • Ownership becomes interactive ("try moving it, see what happens")
  • Reduces "scary compiler" perception

Implementation Approach
~~~~~~~~~~~~~~~~~~~~~~~

REPL compiles each expression/statement incrementally:

  • JIT compilation for speed (LLVM OrcJIT or similar)
  • Ownership tracking persists across statements
  • Type inference works across session
  • Memory is actual (not simulated)-real allocations, real costs

Safety in REPL:
  • Same safety guarantees as compiled code
  • Unsafe blocks still require unsafe marker
  • Ownership rules enforced (prevents use-after-free even in REPL)

Integration with Teaching:
  • quarry learn can open REPL for specific exercises
  • Compiler errors link to REPL examples: "Try this in REPL"
  • Documentation examples include REPL transcripts

Example Teaching Session:

    $ pyrite repl --explain
    
    Pyrite Interactive Shell (Learning Mode)
    ========================================
    
    Try this exercise: Create a list, move it, observe the error
    
    >>> let data = List[int]([1, 2, 3])
    
    ✓ Created owner 'data'
    
    >>> process(data)
    
    ⚠️  'data' moved to 'process'
    
    >>> data.length()
    
    ✗ Error: 'data' was moved on line 2
    
    What happened?
      • Line 1: 'data' owned the list
      • Line 2: Ownership transferred to 'process()'
      • Line 3: 'data' no longer valid
    
    Fix: Use &data to borrow instead
    
    >>> # Try again...

This transforms abstract concepts into interactive, visual understanding. The 
REPL is not just a nice-to-have - it's **essential for Pyrite's identity** as the 
"Pythonic systems language."

Implementation: Beta Release (high priority, high impact)
Complexity: Moderate (JIT compilation, incremental state management)
Impact: Critical (without REPL, Python developers feel the gap immediately)

8.8 Automatic Code Fixes
--------------------------------------------------------------------------------

quarry fix - Apply Compiler Suggestions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite's compiler doesn't just identify problems - it suggests concrete fixes. The 
quarry fix command automatically applies safe, mechanical transformations that 
the compiler recommends.

Usage:

    quarry fix                     # Apply all safe fixes in project
    quarry fix src/main.pyrite     # Fix specific file
    quarry fix --preview           # Show fixes without applying
    quarry fix --interactive       # Prompt before each fix

Interactive Ownership Error Resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When quarry fix encounters ownership/borrowing errors, it presents numbered, 
selectable fixes that teach the concepts while solving the problem:

Example compilation error:

    error[P0234]: cannot use moved value 'data'
      ----> main.py:15:10
       |
    12 |     let data = List[int]([1, 2, 3])
       |         -------- value allocated here
    13 |     process(data)
       |             -------- value moved here (ownership transferred to 'process')
    15 |     print(data.length())
       |          ^^^^ cannot use 'data' after it was moved
       |
       = help: Run 'quarry fix --interactive' to choose a solution

Running quarry fix --interactive presents:

    Found ownership error at main.py:15:10
    
    'data' was moved on line 13 and cannot be used again.
    
    Select a fix:
      1. Pass a reference to 'process' instead
         - Change: process(data) → process(&data)
         - Effect: 'data' remains usable after the call
         - When to use: Function only needs to read the data
      
      2. Clone the value before moving
         - Change: process(data) → process(data.clone())
         - Effect: 'data' remains usable (original retained)
         - When to use: Function needs ownership but you need the data later
         - Cost: Allocates and copies the entire list
      
      3. Restructure to return ownership
         - Change: data = process(data)
         - Effect: 'process' gives ownership back
         - When to use: Function transforms data and you need result
      
      4. Skip this fix
    
    Choice (1-4): _

This interactive mode:
  • **Teaches patterns:** Each option explains when to use it
  • **Shows trade-offs:** Performance implications visible (e.g., "allocates")
  • **Builds intuition:** Repeated fixes teach ownership patterns organically
  • **Safe by default:** Only presents compiler-verified transformations

Non-interactive mode (quarry fix) applies the safest/cheapest fix automatically 
(typically option 1: borrow instead of move).

Ownership Error Coverage:
  • Move-after-use: Offer borrow, clone, or restructure
  • Borrow conflicts: Suggest scope reduction or explicit drop
  • Lifetime issues: Add lifetime annotations or restructure
  • Double move: Clone first move or restructure logic

Types of automatic fixes:

1. **Ownership fixes:**
   
   Before:
       let data = List[int]([1, 2, 3])
       process(data)
       print(data.length())  # ERROR: value moved
   
   After quarry fix:
       let data = List[int]([1, 2, 3])
       process(data.clone())  # Added .clone()
       print(data.length())

2. **Borrowing fixes:**
   
   Before:
       fn process(list: List[int]) -> int:  # Takes ownership
           list.length()
   
   After quarry fix:
       fn process(list: &List[int]) -> int:  # Borrows instead
           list.length()

3. **Performance fixes:**
   
   Before:
       for i in 0..1000:
           let v = List[int].new()  # Allocates in loop
   
   After quarry fix:
       let v = List[int].with_capacity(10)
       for i in 0..1000:
           v.clear()

4. **Type annotations:**
   
   Before:
       let x = parse(input)  # Ambiguous type
   
   After quarry fix:
       let x: Result[Config, Error] = parse(input)

5. **Import cleanup:**
   - Remove unused imports
   - Add missing imports
   - Sort and organize imports

6. **Lifetime annotations (advanced):**
   - Add explicit lifetime annotations where inference fails
   - Only for complex generic code

Why quarry fix is transformative:

  • **Accelerates learning:** Beginners see the pattern of correct code
  • **Reduces friction:** Fix 10 borrow errors in seconds, not minutes
  • **Builds intuition:** Repeated fixes teach ownership patterns
  • **Safe:** Only applies mechanical, verified transformations
  • **IDE integration:** Real-time "Quick Fix" in editors

Safety guarantees:
  • Never changes program semantics incorrectly
  • Only applies fixes the compiler marks as "safe mechanical change"
  • Preserves code comments and formatting
  • Can be undone with version control

This is the natural evolution of Pyrite's teaching compiler: diagnose, explain, 
AND fix. It's what makes Elm, rust-analyzer, and go fmt feel magical.

8.9 Fuzzing and Sanitizers
--------------------------------------------------------------------------------

To make Pyrite a production-ready systems language and achieve widespread developer 
adoption, 
runtime verification tools are essential for catching bugs that static analysis 
misses. These tools cost zero at runtime (only used during testing) but multiply 
reliability dramatically.

quarry fuzz - Coverage-Guided Fuzzing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatic test generation that explores edge cases:

    quarry fuzz                         # Fuzz all fuzzable functions
    quarry fuzz parse_packet            # Fuzz specific function
    quarry fuzz --duration=1h           # Run for 1 hour
    quarry fuzz --corpus=./inputs       # Use seed inputs

How it works:
  • Identifies functions marked @fuzz or with fuzz_ prefix
  • Generates random inputs based on parameter types
  • Tracks code coverage and prioritizes unexplored paths
  • Saves crash-inducing inputs for reproduction

Example fuzzable function:

    @fuzz
    fn parse_packet(data: &[u8]) -> Result[Packet, Error]:
        # Fuzzer generates thousands of random byte arrays
        # Finds inputs that panic, overflow, or violate assertions
        ...

Fuzzing output:

    $ quarry fuzz parse_packet --duration=10m
    
    Fuzzing: parse_packet
    =====================
    
    Progress:
      • Iterations: 1,247,892
      • Coverage: 89% of function body
      • Unique paths: 234
      • Crashes found: 2
    
    🔴 CRASH #1: Integer overflow
       Input: [0xff, 0xff, 0xff, 0xff, 0x01]
       Location: src/parser.py:234
       
       thread 'fuzzer' panicked at 'attempt to multiply with overflow'
         length = u32::from_bytes([0xff, 0xff, 0xff, 0xff])  # 4,294,967,295
         total_size = length * FIELD_SIZE  # Overflows!
       
       Fix: Use checked arithmetic:
         let total_size = length.checked_mul(FIELD_SIZE)?
       
       Saved to: fuzz/crashes/crash-1.bin
       Reproduce: quarry test --fuzz-input=fuzz/crashes/crash-1.bin
    
    🔴 CRASH #2: Slice index out of bounds
       Input: [0x00, 0x05]  # Claims 5 fields, provides 0
       Location: src/parser.py:267
       [Details...]
    
    Summary:
      ✓ Found 2 bugs that unit tests missed
      ✓ Corpus saved to fuzz/corpus/ (1,247 interesting inputs)
      ✓ Add these to regression tests

Integration with CI:

    # Run fuzzing in CI for 5 minutes
    quarry fuzz --ci --duration=5m
    
    # Exit 0 if no crashes, exit 1 if crashes found

Why Fuzzing Matters:
  • Finds edge cases humans miss (off-by-one, overflow, malformed inputs)
  • Generates regression tests automatically (save crash inputs)
  • Industry standard for security-critical code
  • Minimal setup cost (just mark functions with @fuzz)

Fuzz Testing Best Practices:

    @fuzz
    @cost_budget(cycles=10000, allocs=2)  # Budgets still enforced
    fn parse_header(data: &[u8]) -> Result[Header, Error]:
        # Fuzzer explores all code paths
        # Cost budget prevents infinite loops or excessive allocation
        ...

Implementation: Beta Release (after core test framework is stable)

quarry sanitize - Runtime Error Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compiler-integrated sanitizers detect undefined behavior and memory errors at 
runtime (debug/test builds only):

    quarry sanitize --asan              # AddressSanitizer
    quarry sanitize --tsan              # ThreadSanitizer  
    quarry sanitize --ubsan             # UndefinedBehaviorSanitizer
    quarry sanitize --msan              # MemorySanitizer
    quarry sanitize --all               # All sanitizers

AddressSanitizer (ASan) - Memory Error Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detects memory safety violations at runtime:

    quarry sanitize --asan
    quarry test  # Tests run with ASan instrumentation

Catches:
  • Use-after-free
  • Heap buffer overflow
  • Stack buffer overflow
  • Memory leaks
  • Use of uninitialized memory

Example output:

    $ quarry sanitize --asan
    $ quarry test
    
    Running tests with AddressSanitizer...
    
    test test_parse_large ... ok
    test test_edge_cases ... FAILED
    
    ══════════════════════════════════════════════════════════
    AddressSanitizer: heap-buffer-overflow
    ══════════════════════════════════════════════════════════
    
    READ of size 4 at 0x60300000eff4 thread T0
        #0 process_buffer src/processor.py:234
        #1 test_edge_cases tests/test_parser.py:45
    
    0x60300000eff4 is located 4 bytes after 1024-byte region
    allocated by thread T0:
        #0 malloc
        #1 List::with_capacity src/std/collections.py:89
        #2 test_edge_cases tests/test_parser.py:42
    
    SUMMARY: AddressSanitizer: heap-buffer-overflow
    
    ═══════════════════════════════════════════════════════════
    
    Fix: Buffer accessed beyond allocated size
      Line 234: buffer[1024] when buffer.len() == 1024
      Index 1024 is out of bounds (valid: 0..1023)

ThreadSanitizer (TSan) - Data Race Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detects concurrent memory access violations:

    quarry sanitize --tsan
    quarry test

Catches:
  • Data races (unsynchronized concurrent access)
  • Lock order inversions (potential deadlocks)
  • Destroyed mutex still in use
  • Thread leaks

Example output:

    ══════════════════════════════════════════════════════════
    ThreadSanitizer: data race
    ══════════════════════════════════════════════════════════
    
    Write of size 8 at 0x7b0400001234 by thread T2:
        #0 update_counter src/stats.py:156
        #1 worker_thread src/main.py:89
    
    Previous write of size 8 at 0x7b0400001234 by thread T1:
        #0 update_counter src/stats.py:156
        #1 worker_thread src/main.py:89
    
    Location: counter (global variable)
    
    SUMMARY: ThreadSanitizer: data race
    
    ═══════════════════════════════════════════════════════════
    
    Fix: Use atomic operations or mutex:
      
      Option 1 (Atomic):
        static COUNTER: AtomicU64 = AtomicU64::new(0)
        COUNTER.fetch_add(1, Ordering::Relaxed)
      
      Option 2 (Mutex):
        static COUNTER: Mutex<u64> = Mutex::new(0)
        *COUNTER.lock() += 1

UndefinedBehaviorSanitizer (UBSan) - UB Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Catches undefined behavior even in safe-looking code:

    quarry sanitize --ubsan
    quarry test

Catches:
  • Integer overflow (in release mode if checks disabled)
  • Misaligned pointer access
  • Invalid enum discriminant values
  • Shift by negative or >= width
  • Division by zero

Example:

    ══════════════════════════════════════════════════════════
    UndefinedBehaviorSanitizer: signed integer overflow
    ══════════════════════════════════════════════════════════
    
    src/math.py:456:18: runtime error:
      signed integer overflow: 2147483647 + 1 cannot be represented in type 'i32'
    
    Fix: Use checked arithmetic:
      let result = a.checked_add(b)?

Integration with CI
~~~~~~~~~~~~~~~~~~~

Run all sanitizers in continuous integration:

    # .github/workflows/ci.yml
    - name: Run sanitizers
      run: |
        quarry sanitize --asan && quarry test
        quarry sanitize --tsan && quarry test
        quarry sanitize --ubsan && quarry test

Sanitizer builds are slow (2-5x overhead) but catch bugs that slip through 
static analysis and normal testing.

quarry miri - Interpreter-Based UB Detection (Future)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Long-term goal: Rust's Miri-equivalent for Pyrite. An interpreter that catches 
ALL undefined behavior, even in unsafe code:

    quarry miri

Detects:
  • All memory safety violations
  • Uninitialized memory reads
  • Invalid pointer arithmetic
  • Violating unsafe invariants
  • Even bugs sanitizers miss

Slower than sanitizers (10-100x) but exhaustive. Perfect for auditing unsafe 
code blocks.

Why Sanitizers Matter
~~~~~~~~~~~~~~~~~~~~~

This is table-stakes for "serious systems language":

  • Rust has Miri and sanitizer integration
  • C++ has ASan/TSan/UBSan (industry standard)
  • Go has race detector (built-in)
  • Zig is working toward similar tooling

Without sanitizers, Pyrite would seem "less serious" than competitors. With 
them, Pyrite becomes: "Memory-safe by design, verified by runtime checks, 
auditable with interpreters."

Real-world impact:
  • Chromium: ASan found 3,000+ bugs that code review missed
  • Rust: Miri caught soundness bugs in stdlib
  • Industry: Sanitizers are non-negotiable for security-critical code

Cost:
  • Zero runtime cost (only enabled for testing)
  • High confidence multiplier (catch what static analysis can't)
  • Required for safety certification in many domains

Implementation: Beta Release (fuzzing + ASan/TSan/UBSan via LLVM)
             Stable Release (Miri-equivalent interpreter)

8.10 Linting
--------------------------------------------------------------------------------

Multi-Level Linter
~~~~~~~~~~~~~~~~~~

quarry lint provides progressive strictness:

    quarry lint --level=beginner   # Gentle warnings, teaching mode
    quarry lint --level=standard   # Default, balanced
    quarry lint --level=pedantic   # Maximum strictness
    quarry lint --level=performance  # Focus on performance issues

Linter categories:

    Correctness:
      • Unused variables
      • Unreachable code
      • Type mismatches (if inference is ambiguous)
      • Pattern match exhaustiveness
    
    Style:
      • Naming conventions (snake_case, CamelCase)
      • Module organization
      • Public API documentation coverage
    
    Performance:
      • Heap allocations (see section 4.5)
      • Large copies
      • Unnecessary clones
      • Inefficient algorithms (e.g., O(n²) where O(n) available)
    
    Safety:
      • Unsafe block auditing
      • FFI boundary checks
      • Concurrency patterns (potential deadlocks, etc.)

Customization
~~~~~~~~~~~~~

Project-level lint configuration in Quarry.toml:

    [lints]
    level = "standard"
    allow = ["large_copy"]      # Suppress specific warnings
    deny = ["heap_in_loop"]     # Elevate warnings to errors

8.10.1 Code Expansion: quarry expand
--------------------------------------------------------------------------------

To demystify compiler transformations and teach how high-level constructs desugar, 
Quarry provides quarry expand to show generated code:

Command Usage
~~~~~~~~~~~~~

    quarry expand file.pyrite              # Show all expansions
    quarry expand file.pyrite --function=foo  # Expand specific function
    quarry expand --closure-expansion      # Show parameter closure inlining

Use Cases
~~~~~~~~~

1. **Parameter closure expansion** - See how fn[...] is inlined:

   Source code:
       algorithm.vectorize[width=8](data.len(), fn[i: int]:
           data[i] = data[i] * 2.0
       )
   
   Expanded (quarry expand):
       const WIDTH = 8
       var i = 0
       
       # SIMD loop (parameter closure body inlined here)
       while i + WIDTH <= data.len():
           let vec = simd::Vec[f32, 8]::load(&data[i])
           let scaled = vec * 2.0
           scaled.store(&mut data[i])
           i += WIDTH
       
       # Remainder loop (parameter closure body inlined here)
       while i < data.len():
           data[i] = data[i] * 2.0  # Original closure body
           i += 1

2. **with statement desugaring** - See try + defer expansion:

   Source:
       with file = try File.open("config.txt"):
           process(file)
   
   Expanded:
       let file = try File.open("config.txt")
       defer:
           file.close()
       process(file)

3. **Compile-time parameter specialization:**

   Source:
       fn process[N: int](data: [u8; N]) -> int:
           # ...
       process[16](buffer)
   
   Expanded:
       # Specialized version for N=16
       fn process_16(data: [u8; 16]) -> int:
           # ... with N replaced by 16 ...

Teaching Benefits
~~~~~~~~~~~~~~~~~

quarry expand transforms abstract concepts into concrete code:

  • **Parameter closures:** "Here's exactly how it inlines"
  • **Zero-cost abstractions:** "See? No allocation, no indirection"
  • **Syntactic sugar:** "with desugars to try + defer"
  • **Compile-time params:** "Each [N] creates a specialized version"

Integration with Learning
~~~~~~~~~~~~~~~~~~~~~~~~~

Compiler errors suggest using expand:

    error[P0801]: cannot store parameter closure
      ...
      = help: Parameter closures are compile-time only (inlined)
      = explain: Run 'quarry expand --help closure-types' to see the difference
      = visual: Run 'quarry expand src/main.pyr --function=process' to see expansion

quarry learn exercises include expansion:

    Exercise: Understand Parameter Closures
    
    Run: quarry expand examples/vectorize.pyr
    
    See how the fn[i: int] closure is inlined into the SIMD loop.
    Notice: No function call, no allocation, just direct code insertion.

This makes abstract transformations concrete, accelerating learning.

Implementation: Beta Release (after parameter closures and sugar constructs are stable)

8.11 Documentation Generation
--------------------------------------------------------------------------------

Auto-Generated Docs
~~~~~~~~~~~~~~~~~~~

quarry doc generates HTML documentation from code and doc comments:

    """
    Parses a JSON string into a structured value.
    
    # Arguments
    * `input` - The JSON string to parse
    
    # Returns
    * `Ok(Value)` - Parsed JSON value
    * `Err(ParseError)` - Parse failure with error details
    
    # Examples
    ```pyrite
    let json = parse_json('{"key": "value"}')
    match json:
        Ok(val):
            print(val)
        Err(e):
            print("Parse error:", e)
    ```
    """
    fn parse_json(input: String) -> Result[Value, ParseError]:
        # Implementation

Generated docs include:
  • Public API reference
  • Example code (tested as part of doc tests)
  • Cross-links between related items
  • Search functionality
  • Source code links

8.12 Cross-Compilation
--------------------------------------------------------------------------------

First-Class Cross-Compilation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quarry makes cross-compilation trivial:

    quarry build --target=aarch64-linux      # ARM64 Linux
    quarry build --target=x86_64-windows     # Windows x64
    quarry build --target=wasm32             # WebAssembly
    quarry build --target=arm-none-eabi      # Bare metal ARM

No separate toolchain setup required. Quarry downloads target-specific 
components automatically.

List available targets:

    quarry target list

Add target support:

    quarry target add riscv64-linux

Zero-Allocation Mode
~~~~~~~~~~~~~~~~~~~~

For embedded systems and safety-critical applications that require provable 
no-heap behavior, Quarry provides a zero-allocation build mode:

    quarry build --no-alloc
    
    # Or configure in Quarry.toml:
    [profile.embedded]
    no-alloc = true

In this mode, the compiler errors on any heap allocation:

    error[P0601]: heap allocation in no-alloc mode
      ----> src/main.pyr:42:13
       |
    42 |     let v = List[int].new()  # <---- allocates on heap
        |             ^^^^^^^^^^^^^^
        |
        = note: Build configured with --no-alloc
        = help: Use fixed-size array: [int; N]
        = help: Or pass pre-allocated buffer as parameter

What is forbidden:
  • List, Map, Set, String creation (heap containers)
  • Box[T], Rc[T], Arc[T] (heap allocation)
  • Dynamic trait objects (Box<dyn Trait>)
  • Any function marked with @may_alloc attribute

What is allowed:
  • Stack arrays: [int; 100]
  • Structs and enums (stack allocated)
  • References and slices
  • Static data and constants
  • Functions marked @noalloc

Example: Embedded firmware

    # Cargo.toml configuration
    [profile.embedded]
    no-alloc = true
    panic = "abort"
    opt-level = "z"  # Size optimization
    
    # main.pyrite
    @noalloc
    fn process_sensor_data(readings: &[u16; 32]) -> u32:
        var sum: u32 = 0
        for reading in readings:
            sum += reading as u32
        return sum / 32
    
    fn main():
        const BUFFER: [u16; 32] = [0; 32]
        loop:
            read_sensors(&mut BUFFER)
            let average = process_sensor_data(&BUFFER)
            display(average)

Benefits:
  • **Provable no-heap:** Compiler guarantees
  • **Safety certification:** Required for aerospace, medical devices
  • **Predictable memory:** No allocator = no allocation failures
  • **Minimal footprint:** No allocator code in binary

Integration with stdlib:
  • core:: namespace works in no-alloc mode
  • std:: namespace requires allocator
  • Clear documentation: "@requires alloc" on API docs

Use cases:
  • Microcontroller firmware (no MMU, limited RAM)
  • Real-time systems (deterministic memory)
  • Safety-critical software (aerospace, medical)
  • Bootloaders and kernels

This makes Pyrite credible for the most constrained embedded environments. 
Beta Release feature.

8.13 Cost Analysis and Performance Profiling
--------------------------------------------------------------------------------

Static Cost Analysis: quarry cost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond inline warnings, Pyrite provides structured cost analysis for IDE 
integration, CI/CD gates, and performance tracking.

Usage:

    quarry cost                     # Analyze entire project
    quarry cost --json              # Machine-readable output
    quarry cost --baseline=v1.json  # Compare against baseline
    quarry cost --threshold=warn    # Only show significant costs

Multi-Level Cost Reporting
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The quarry cost command supports progressive detail levels that match developer 
experience, teaching performance intuition gradually:

    quarry cost --level=beginner       # Gentle introduction
    quarry cost --level=intermediate   # Standard detail (default)
    quarry cost --level=advanced       # Comprehensive analysis

This mirrors the existing quarry lint --level pattern, creating a consistent 
mental model across tooling.

Beginner Level (--level=beginner)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shows only high-level, actionable insights without overwhelming detail:

    Performance Analysis (Beginner)
    ================================
    
    🔹 Your code allocates memory 12 times
       Most significant:
         • Line 234: Creates a list in a loop (runs 1000 times)
           → Consider creating the list once before the loop
         • Line 156: Map grows dynamically
           → Tip: Maps start small and grow as needed
    
    🔹 Your code copies large data 3 times
         • Line 567: ImageBuffer (4 KB)
           → Consider using a reference: &ImageBuffer
    
    💡 Learn more: run 'quarry cost --level=intermediate' for details

Beginner output characteristics:
  • Plain language (avoids jargon like "heap allocation", "amortized O(1)")
  • Only shows operations that matter (>1KB allocations, copies in loops)
  • Focuses on "what to do" not "why it happens"
  • Limits output to top 3-5 issues to avoid overwhelm

Intermediate Level (--level=intermediate, default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Standard developer view with counts, sizes, and loop multiplication:

    Performance Analysis
    ====================
    
    Allocations: 12 sites (estimated 47 KB)
      
      🔴 Hot path (in loop):
        Line 234: List[Token].new()
          • Loop iterations: 1000
          • Per-call cost: 24 bytes (initial capacity)
          • Total cost: ~24 KB (may trigger 3-4 reallocations)
          • Suggestion: List[Token].with_capacity(100)
      
      🟡 Moderate:
        Line 156: Map[String, Config].insert()
          • Map capacity growth: 3 reallocations likely
          • Suggestion: with_capacity(estimated_entries)
    
    Copies: 3 sites (12 KB)
      Line 567: ImageBuffer (4096 bytes)
        • Passed by value to process_image()
        • Suggestion: Pass by reference (&ImageBuffer)
    
    💡 Run 'quarry cost --level=advanced' for dispatch and syscall analysis

Intermediate output characteristics:
  • Shows counts and sizes
  • Multiplies by loop iteration counts
  • Groups by severity (hot paths vs moderate)
  • Includes concrete suggestions with code examples

Advanced Level (--level=advanced)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive analysis for performance-critical code:

    Performance Analysis (Advanced)
    ================================
    
    Allocations: 12 sites (47 KB estimated, 125 KB worst-case)
      
      🔴 Critical (hot path):
        src/parser.py:234:9 - List[Token].new()
          Function: parse_tokens() [called from 3 sites]
          Loop context: 0..1000 (bounded)
          Initial capacity: 24 bytes (6 elements)
          Growth pattern: 2x reallocation (typical usage: 15 elements)
          Expected reallocations: 2 (24→48→96 bytes)
          Total allocation cost: ~24 KB + 2 reallocations
          Suggestion: with_capacity(20) eliminates reallocations
          Allocator: DefaultHeap
      
      🟡 Moderate:
        src/cache.py:156:13 - Map[String, Config].insert()
          Growth: 0→16→32→64 entries (3 reallocations observed)
          Total cost: ~12 KB
          Frequency: Once per application startup
          Suggestion: with_capacity(50) if typical load known
    
    Copies: 3 sites (12 KB)
      src/renderer.py:567:14 - ImageBuffer
        Size: 4096 bytes
        Call chain: main() → render_frame() → process_image()
        Copy occurs: process_image(img: ImageBuffer)
        Suggestion: process_image(img: &ImageBuffer)
        Impact: 4KB memcpy per frame (60 FPS = 240 KB/sec)
    
    Dynamic Dispatch: 5 sites
      src/plugins.py:89:5 - Plugin::execute()
        Trait object: &dyn Plugin
        Virtual call overhead: ~2-3 cycles (indirect branch)
        Alternatives: enum dispatch, monomorphization
      
      src/events.py:234:10 - EventHandler::handle()
        Trait object: Box<dyn EventHandler>
        Pointer indirection: vtable lookup
        Context: Event loop (called frequently)
        Note: Acceptable cost for plugin architecture
    
    Syscalls: 23 sites
      File operations: 15 sites
        src/config.py:45 - File::open("/etc/app.conf")
        src/logger.py:89 - File::write() [buffered, ~10 syscalls/sec]
      
      Network operations: 8 sites
        src/api.py:156 - TcpStream::connect()
        src/api.py:234 - stream.read() [blocking I/O]
    
    Locking: 4 sites
      src/cache.py:67 - Mutex::lock()
        Hold time: <1μs typical
        Contention: Low (single writer pattern)

Advanced output characteristics:
  • Full call chains and context
  • Detailed memory growth patterns
  • Allocator identification
  • Dynamic dispatch with vtable overhead estimates
  • Syscall breakdown by category
  • Lock contention analysis
  • Performance implications (e.g., "60 FPS = 240 KB/sec")

Level Selection Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

The tool automatically suggests level progression:
  • Beginner → Intermediate: After user has addressed top issues
  • Intermediate → Advanced: When optimizing hot paths or performance-critical code

IDE integration can show different levels in different contexts:
  • Inline hints: Beginner-level messages
  • Hover tooltips: Intermediate-level detail
  • "Show full analysis": Advanced-level deep dive

JSON Output Format:

    {
      "allocations": [
        {
          "location": "src/parser.py:234:9",
          "function": "parse_tokens",
          "type": "heap_allocation",
          "estimated_bytes": 1024,
          "frequency": "per_call",
          "suggestions": [
            "Pre-allocate with List.with_capacity(estimated_size)",
            "Reuse buffer across calls"
          ]
        }
      ],
      "copies": [
        {
          "location": "src/renderer.py:567:14",
          "bytes": 4096,
          "type": "ImageBuffer",
          "suggestion": "Pass by reference: &ImageBuffer"
        }
      ],
      "dynamic_dispatch": [
        {
          "location": "src/plugins.py:89:5",
          "trait": "Plugin",
          "method": "execute",
          "note": "Indirect call via vtable"
        }
      ],
      "syscalls": [
        {
          "location": "src/main.py:45:10",
          "operation": "file_open",
          "path": "/etc/config"
        }
      ],
      "summary": {
        "total_allocations": 47,
        "total_bytes_allocated": 125440,
        "total_copies": 12,
        "total_bytes_copied": 98304,
        "dynamic_dispatch_sites": 8,
        "syscall_sites": 23
      }
    }

IDE Integration:

IDEs can consume the JSON output to show inline cost hints:

    let tokens = List[Token].new()  💰 1KB heap allocation
                                     ⚡ Hint: with_capacity(100)

CI/CD Integration:

Enforce performance budgets in continuous integration:

    # .github/workflows/ci.yml
    - name: Check performance budget
      run: |
        quarry cost --json > current.json
        quarry cost --baseline=baseline.json --threshold=error
        # Fails if allocations increased by >10%

Baseline tracking:

    quarry cost --save=baseline.json      # Save current as baseline
    quarry cost --compare=baseline.json   # Show differences

Example output:

    Performance Analysis
    ====================
    
    Allocations: 47 sites (125 KB estimated)
      ↑ +3 sites since baseline
      ↑ +12 KB since baseline
    
    Largest allocations:
      1. src/parser.py:234    8 KB  (in loop, 1000 iterations = 8 MB)
      2. src/cache.py:156     4 KB  (Map growth)
      3. src/buffer.py:89     2 KB  (String concatenation)
    
    Copies: 12 sites (96 KB total)
      → src/renderer.py:567   4 KB  ImageBuffer
      → src/config.py:123     8 KB  ConfigData
    
    Dynamic dispatch: 8 sites
      → All in plugin system (expected)
    
    Syscalls: 23 sites
      → 15 file operations
      → 8 network operations

Use Cases:

1. **Performance debugging:** Find unexpected allocations
2. **CI gates:** Prevent performance regressions
3. **Optimization tracking:** Measure improvement over time
4. **IDE hints:** Show costs inline while coding
5. **Code review:** Highlight performance-sensitive changes

This completes Pyrite's cost-transparency story: from inline warnings (for 
developers) to structured reports (for tools and CI systems).

Runtime Performance Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Static analysis (quarry cost) shows what *could* be expensive. Runtime profiling 
shows what *is* expensive in actual execution. Quarry provides integrated 
profiling commands that complement static cost analysis:

quarry perf - Flamegraph Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integrated CPU profiling with flamegraph visualization:

    quarry perf                         # Profile with default settings
    quarry perf --release               # Profile optimized build
    quarry perf --output=profile.svg    # Export flamegraph
    quarry perf --duration=30s          # Profile for 30 seconds

Under the hood:
  • Linux: Wraps perf with optimal sampling settings
  • macOS: Wraps Instruments DTrace profiler
  • Windows: Wraps ETW (Event Tracing for Windows)
  • Generates interactive flamegraph SVG automatically

Output shows:
  • CPU time spent in each function
  • Call stack context (who called what)
  • Hot paths highlighted
  • Standard flamegraph format (widely recognized)

Example workflow:

    $ quarry perf --release
    Profiling myapp (optimized build)...
    Captured 45,234 samples over 10.2 seconds
    
    Top functions by CPU time:
      34.2%  process_data
      18.5%  parse_input
      12.3%  allocate_buffers
    
    Flamegraph saved to: target/profile.svg
    Open in browser to explore call stacks

quarry alloc - Allocation Profiling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track heap allocations with call stack context:

    quarry alloc                        # Profile allocations
    quarry alloc --threshold=1KB        # Only show allocations > 1KB
    quarry alloc --json                 # Machine-readable output

Shows:
  • Every heap allocation with size
  • Call stack that triggered allocation
  • Allocation hot spots (frequency × size)
  • Reallocation events (growth patterns)

Example output:

    Allocation Profile
    ==================
    
    Total allocations: 1,247 (2.4 MB)
    
    Hot spots (by total bytes):
      1. src/parser.py:234 - List[Token].new()
         • 1,000 allocations (24 KB each = 24 MB total)
         • Call chain: parse() → tokenize() → List::new()
         • Suggestion: Pre-allocate with with_capacity(1000)
      
      2. src/cache.py:156 - Map[String, Config].insert()
         • 47 allocations (growth: 16→32→64→128 entries)
         • Total: 12 KB
         • Suggestion: with_capacity(128) eliminates reallocations
    
    Allocation timeline:
      0-1s:    234 allocations (456 KB)
      1-2s:    189 allocations (378 KB)
      2-3s:    824 allocations (1.6 MB) ← spike here

Integration with quarry cost:
  • Static analysis predicts allocations
  • Runtime profiling confirms actual behavior
  • Cross-reference: "quarry cost predicted 12 sites, profiler found 11"

quarry pgo - Profile-Guided Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One-command PGO pipeline automates the 3-step process:

    quarry pgo                          # Build → train → rebuild
    quarry pgo --workload=bench         # Use benchmarks as training
    quarry pgo --workload="./train.sh"  # Custom training script

Manual PGO Workflow (Full Control)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For custom training workloads or complex scenarios, use the explicit 3-step workflow:

    # Step 1: Build instrumented binary
    $ quarry pgo generate
    Building instrumented binary for PGO training...
    ✓ Built: target/pgo-instrument/myapp
    ✓ Profile output: target/pgo-data/default.profraw
    
    Instrumentation:
      • Functions: 1,247 instrumented
      • Basic blocks: 12,456 tracked
      • Binary size: 3.2 MB (1.5x larger than release)
    
    Next: Run your training workload with this binary
          ./target/pgo-instrument/myapp [your args]
    
    # Step 2: Run training workload (your application-specific usage)
    $ ./target/pgo-instrument/myapp --benchmark
    # Or: ./target/pgo-instrument/myapp < typical_input.txt
    # Or: python run_training_suite.py
    # (Profile data automatically written to target/pgo-data/)
    
    # Step 3: Build optimized binary with profile data
    $ quarry pgo optimize
    Building with profile-guided optimization...
    ✓ Analyzed profile data: target/pgo-data/default.profraw
    ✓ Built: target/release/myapp
    
    PGO Optimizations Applied:
      • Functions inlined: 89 (based on hot paths)
      • Functions outlined: 45 (based on cold paths)
      • Branch weights: 1,234 basic blocks reordered
      • Code layout: Hot code grouped for cache locality
    
    Performance improvement:
      • Estimated: 15-30% faster on training workload
      • Binary size: 2.0 MB (cold code moved out-of-line)
    
    Next: Benchmark the optimized binary
          quarry bench --compare-to=baseline

Multiple Training Runs:

    # Collect profile data from multiple workloads
    $ quarry pgo generate
    
    $ ./target/pgo-instrument/myapp --workload=web_server
    # Profile data: target/pgo-data/run1.profraw
    
    $ ./target/pgo-instrument/myapp --workload=batch_processing
    # Profile data: target/pgo-data/run2.profraw
    
    $ ./target/pgo-instrument/myapp --workload=interactive
    # Profile data: target/pgo-data/run3.profraw
    
    # Merge all profiles and optimize
    $ quarry pgo optimize --merge-all
    Merging 3 profile datasets...
    ✓ Combined profile represents all workloads
    Building optimized binary...

Clean up profile data:

    quarry pgo clean                       # Remove profile data
    quarry pgo reset                       # Reset and start over

Automated PGO Workflow (One Command)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For simple cases with standard workloads:

    quarry pgo                          # Build → train → rebuild
    quarry pgo --workload=bench         # Use benchmarks as training
    quarry pgo --workload="./train.sh"  # Custom training script

Automated workflow:
  1. quarry pgo
     → Builds instrumented binary
     → Runs typical workload (or prompts for one)
     → Rebuilds optimized binary
     → Reports performance improvement

Example:

    $ quarry pgo --workload=bench
    
    Step 1/3: Building instrumented binary...
    ✓ Built target/pgo-instrument/myapp
    
    Step 2/3: Running training workload (benchmarks)...
    ✓ Collected profile data from 5 benchmarks
    
    Step 3/3: Rebuilding with profile-guided optimization...
    ✓ Built target/release/myapp
    
    Performance improvement:
      • 15% faster on parse_large_file benchmark
      • 8% faster on compute_heavy benchmark
      • Binary size: 2.1 MB → 2.0 MB (branch pruning)

Why PGO matters:
  • Optimizes for actual code paths (not theoretical ones)
  • Better inlining decisions (inline hot paths, not cold ones)
  • Better branch prediction hints
  • Can yield 10-30% performance improvement

Quarry automates the tedious parts while giving control when needed.

LTO and Combined Optimization Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Link-Time Optimization (LTO) enables cross-translation-unit optimization by 
deferring code generation to link time. Quarry provides first-class LTO support 
with simple flags:

    quarry build --release --lto        # Full LTO (maximum optimization)
    quarry build --release --lto=thin   # Thin LTO (faster builds, good optimization)

LTO modes:
  • --lto or --lto=full - Full link-time optimization
    • Optimizes across all translation units
    • Slowest build times (minutes for large projects)
    • Best optimization (5-15% improvement typical)
    • Use for: Final release builds, benchmarking
  
  • --lto=thin - Thin LTO (recommended default for --release)
    • Fast incremental builds with cross-module optimization
    • 80% of full LTO benefit at 20% of compile time cost
    • Enables parallel optimization
    • Use for: Iterative optimization, CI builds
  
  • No LTO - Fastest builds, per-module optimization only
    • Use for: Debug builds, development iteration

Combined workflow for maximum performance:

    quarry build --release --lto=thin --pgo=./workload.sh
    
    # Combines:
    # 1. Release optimizations (--O3 equivalent)
    # 2. Thin LTO (cross-module inlining and optimization)
    # 3. Profile-guided optimization (optimize for actual usage)
    
    Typical results:
      • Release alone: 10x faster than debug
      • + Thin LTO: 15-25% additional improvement
      • + PGO: 10-30% additional improvement
      • Combined: 15-50% faster than plain release

One-command peak performance:

    quarry build --peak
    
    # Equivalent to: --release --lto --pgo=bench
    # Automatically:
    #   1. Builds with thin LTO + instrumentation
    #   2. Runs benchmark suite as PGO training
    #   3. Rebuilds with full LTO + PGO data
    #   4. Reports achieved optimization levels
    
    Output:
      Peak Performance Build
      ======================
      
      Step 1/3: Building instrumented binary (thin LTO)...
      ✓ Built in 2m 34s
      
      Step 2/3: Training with benchmark workload...
      ✓ Collected profile from 12 benchmarks (45s)
      
      Step 3/3: Final build (full LTO + PGO)...
      ✓ Built in 8m 12s
      
      Optimizations applied:
        • Release optimizations: baseline
        • Thin LTO (training): +18% performance
        • Full LTO (final): +7% performance
        • PGO: +23% performance
        • Total improvement: +55% vs release
      
      Binary: target/peak/myapp (2.3 MB)
      Recommended for: Production deployment

Build profiles can configure defaults:

    # Quarry.toml
    [profile.release]
    opt-level = 3
    lto = "thin"        # Enable thin LTO for release builds
    pgo = false         # Manual PGO only
    
    [profile.peak]
    inherits = "release"
    lto = "full"        # Full LTO for peak builds
    pgo = true          # Always run PGO
    pgo-workload = "bench"

Comparison table:

    | Build Mode         | Time | Binary Size | Performance | Use Case               |
    |--------------------|------|-------------|-------------|------------------------|
    | Debug              | 10s  | 5 MB        | 1x          | Development            |
    | --release          | 30s  | 2 MB        | 10x         | Testing                |
    | --release --lto    | 2m   | 1.8 MB      | 12x         | Distribution           |
    | --release --pgo    | 5m   | 2 MB        | 13x         | Optimized for workload |
    | --peak             | 10m  | 1.8 MB      | 15x         | Production max perf    |

When to use each:
  • Debug: Iteration, debugging
  • Release: QA, most users
  • Release + thin LTO: Distribution default (good balance)
  • Peak: Mission-critical services, performance benchmarking

Cost transparency:

    quarry cost shows optimization decisions:
      
      Build: --release --lto --pgo
      
      Optimizations applied:
        • 1,234 functions inlined (cross-module via LTO)
        • 89 cold paths moved out-of-line (via PGO)
        • 234 branches reordered (via PGO branch weights)
        • 45 functions specialized (hot path variants)
      
      Estimated improvements:
        • LTO: +18% (reduced call overhead)
        • PGO: +23% (optimized for actual workload)

Why this matters:

LTO and PGO are proven optimizations that yield 20-50% improvements in real-world 
applications, but are often tedious to configure. Quarry makes them one-command 
operations, and --peak mode makes "absolute best performance" a single flag.

Beta Release feature (LTO support). Beta Release enhancement (--peak command).

quarry tune - Intelligent Optimization Suggestions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Correlates static analysis (quarry cost) with runtime profiling (quarry perf, 
quarry alloc) to suggest specific, high-impact optimizations:

    quarry tune                         # Analyze and suggest
    quarry tune --apply                 # Apply safe suggestions automatically
    quarry tune --interactive           # Review each suggestion

Example output:

    Performance Tuning Suggestions
    ===============================
    
    Based on static analysis and runtime profiling:
    
    🔴 HIGH IMPACT (3 suggestions)
    
    1. Pre-allocate List in hot loop
       Location: src/parser.py:234
       
       Current code:
         for line in lines:              # 1000 iterations
             let tokens = List[Token].new()
       
       Issue:
         • Static analysis: Allocates in loop (1000 times)
         • Runtime profile: 24 MB allocated, 3-4 reallocations per list
         • CPU time: 12% of total runtime
       
       Suggested fix:
         let tokens = List[Token].with_capacity(20)
         for line in lines:
             tokens.clear()
             # ... use tokens ...
       
       Expected improvement:
         • Eliminates 1000 allocations
         • Removes all reallocations
         • Estimated speedup: 15-20%
       
       [Apply] [Skip] [Explain]
    
    2. Pass ImageBuffer by reference
       Location: src/renderer.py:567
       
       Current code:
         fn process_image(img: ImageBuffer):  # Takes ownership, copies 4 KB
       
       Issue:
         • Static analysis: 4 KB copy on every call
         • Runtime profile: Called 60 times/second (240 KB/sec copied)
         • CPU time: 8% of total runtime
       
       Suggested fix:
         fn process_image(img: &ImageBuffer):  # Borrows, no copy
       
       Expected improvement:
         • Eliminates 4 KB copy per frame
         • Estimated speedup: 8-10%
       
       [Apply] [Skip] [Explain]
    
    🟡 MEDIUM IMPACT (5 suggestions)
    
    3. Use SmallVec for small arrays
       Location: src/ast.py:89
       [Details...]
    
    [Show all] [Apply all safe fixes] [Cancel]

How quarry tune works:
  1. Runs static cost analysis (quarry cost)
  2. Runs runtime profiling (quarry perf + quarry alloc)
  3. Correlates findings: "This allocation was predicted and IS a hot spot"
  4. Ranks by impact: CPU time × memory × frequency
  5. Suggests specific, actionable fixes
  6. Can apply safe transformations automatically

Why this is transformative:
  • Beginners: "Just run quarry tune" → get specific guidance
  • Experts: Saves manual correlation work
  • Actionable: Not generic advice, specific line numbers + code changes
  • Measurable: Estimates improvement (based on profiling data)

This completes the performance tooling story:
  • quarry cost: Static "what could be expensive"
  • quarry perf: Runtime "what is expensive (CPU)"
  • quarry alloc: Runtime "what is expensive (memory)"
  • quarry pgo: Optimize for actual workloads
  • quarry tune: Correlate all data, suggest fixes

Performance Lockfile: Enforced "Fast Forever"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The performance lockfile workflow transforms Pyrite's cost transparency from 
"measure performance" to "enforce performance stays constant." This is the 
missing piece that turns "Pyrite is fast" into "Pyrite stays fast forever."

Command Usage
~~~~~~~~~~~~~

    quarry perf --baseline              # Write Perf.lock
    quarry perf --check                 # Fail CI if regressed
    quarry perf --check --threshold=5%  # Custom regression tolerance
    quarry perf --diff                  # Show differences vs baseline

Performance Lockfile Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate a baseline snapshot of performance characteristics:

    $ quarry perf --baseline
    
    Profiling optimized build...
    Running benchmark suite (12 benchmarks)...
    
    Performance Baseline Generated
    ===============================
    
    Hot Functions (saved to Perf.lock):
      • process_data: 1247ms (34.2% total time)
        - SIMD width: 8 (AVX2)
        - Inlined: 23 callsites
        - Allocation sites: 3
      
      • parse_input: 674ms (18.5% total time)
        - Call count: 10,247
        - Allocation sites: 12
        - Stack usage: 4 KB
      
      • allocate_buffers: 448ms (12.3% total time)
        - Heap allocations: 47 sites
        - Total allocated: 125 KB
    
    Optimization Baseline:
      • Total allocations: 47 sites (125 KB)
      • SIMD width used: 8 (AVX2)
      • Inlining decisions: 1,234 functions
      • Code generation: optimized
    
    Baseline saved to: Perf.lock
    Commit this file to track performance over time

Perf.lock Format
~~~~~~~~~~~~~~~~

The lockfile stores concrete, measurable performance metrics:

    # Perf.lock (YAML format for readability)
    version: "1.0"
    generated: "2025-12-18T10:30:00Z"
    build: "--release --lto=thin"
    platform: "x86_64-linux"
    
    hot_functions:
      - name: "process_data"
        time_ms: 1247
        time_percent: 34.2
        simd_width: 8
        inlined_calls: 23
        alloc_sites: 3
      
      - name: "parse_input"
        time_ms: 674
        time_percent: 18.5
        call_count: 10247
        alloc_sites: 12
        stack_bytes: 4096
    
    allocations:
      total_sites: 47
      total_bytes: 125440
      hot_spots:
        - location: "src/parser.py:234"
          count: 1000
          bytes_per: 24
    
    optimizations:
      functions_inlined: 1234
      simd_vectorized: 67
      loops_unrolled: 23

CI Integration and Regression Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In continuous integration, enforce performance constraints:

    $ quarry perf --check
    
    Checking performance against baseline (Perf.lock)...
    
    ✗ PERFORMANCE REGRESSION DETECTED
    
    Regressions (threshold: 5%):
    
      🔴 CRITICAL: process_data regressed by 18%
         Baseline: 1247ms → Current: 1471ms (+224ms)
         
         Analysis:
           • SIMD width changed: 8 (AVX2) → 4 (SSE2)
           • Reason: Alignment check now fails
           • Affected code: src/process.py:156-189
         
         Run 'quarry perf --explain process_data' for details
      
      🟡 WARNING: parse_input regressed by 6.2%
         Baseline: 674ms → Current: 716ms (+42ms)
         
         Analysis:
           • New allocation added: src/parser.py:241
           • Inlining stopped: tokenize() no longer inlined
           • Reason: Function grew beyond inlining threshold
         
         Run 'quarry perf --explain parse_input' for details
    
    Summary:
      • 2 functions regressed
      • 0 functions improved
      • Overall regression: 11.3% slower
    
    CI FAILURE: Performance regressions exceed threshold
    Exit code: 1

This output is actionable: developers know exactly which function regressed, 
by how much, and WHY (SIMD width changed, inlining stopped, allocation added).

Explaining Regressions
~~~~~~~~~~~~~~~~~~~~~~~

Deep-dive into why performance changed:

    $ quarry perf --explain process_data
    
    Performance Regression Analysis: process_data
    ==============================================
    
    Baseline: 1247ms (34.2% of runtime)
    Current:  1471ms (38.9% of runtime)
    Change:   +224ms (+18% slower) ⚠️
    
    Root Causes:
    
    1. SIMD Width Reduced (PRIMARY CAUSE)
       
       Baseline: 8-wide SIMD (AVX2)
         • Vectorized loop at line 156
         • Processes 8 f32 per iteration
         • Generated: vfmadd231ps (AVX2 FMA instruction)
       
       Current: 4-wide SIMD (SSE2)
         • Same loop now uses SSE2
         • Processes 4 f32 per iteration
         • Generated: mulps + addps (SSE2 instructions)
       
       Why the change?
         • Buffer alignment changed from 32-byte to 16-byte
         • Change introduced in: commit abc123f
         • File: src/buffers.py:89
         • Old: #[align(32)] → New: #[align(16)]
       
       Fix:
         Restore 32-byte alignment for AVX2:
           struct Buffer:
               #[align(32)]  # Required for 8-wide SIMD
               data: [f32; 1024]
    
    2. Inlining Stopped (SECONDARY CAUSE)
       
       Baseline: compute_kernel() inlined at 23 callsites
       Current:  compute_kernel() NOT inlined (function call overhead)
       
       Why?
         • Function body grew from 45 → 89 instructions
         • Exceeded inlining threshold (80 instructions)
         • Change: Added debug logging in commit def456
       
       Fix:
         Remove debug logging in hot path, or use:
           @always_inline
           fn compute_kernel(...):

Assembly Diff (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~

For expert debugging, show assembly differences:

    $ quarry perf --diff-asm process_data
    
    Assembly Diff: process_data (Baseline vs Current)
    ==================================================
    
    Baseline (AVX2, 8-wide SIMD):
      vmovups ymm0, [rdi + 0]      ; Load 8 f32
      vmovups ymm1, [rsi + 0]      ; Load 8 f32
      vfmadd231ps ymm0, ymm1, ymm2 ; FMA: ymm0 += ymm1 * ymm2
      vmovups [rdx + 0], ymm0      ; Store 8 f32
      add rdi, 32                  ; Advance pointer
      add rsi, 32
      add rdx, 32
    
    Current (SSE2, 4-wide SIMD):
      movups xmm0, [rdi + 0]       ; Load 4 f32
      movups xmm1, [rsi + 0]       ; Load 4 f32
      mulps xmm1, xmm2             ; Multiply
      addps xmm0, xmm1             ; Add
      movups [rdx + 0], xmm0       ; Store 4 f32
      add rdi, 16                  ; Advance pointer
      add rsi, 16
      add rdx, 16
    
    Analysis:
      • Twice as many loop iterations (8→4 elements per iter)
      • No FMA instruction (requires 2 ops instead of 1)
      • Estimated: 2x slower per element processed

IR Diff (Alternative)
~~~~~~~~~~~~~~~~~~~~~~

For compiler developers, show LLVM IR differences:

    $ quarry perf --diff-ir process_data
    
    Shows side-by-side LLVM IR with:
      • Vectorization decisions
      • Inlining decisions
      • Optimization passes applied
      • Differences highlighted

Why Performance Lockfile Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This workflow addresses the critical "performance decay" problem:

Without lockfile:
  • Performance regressions silent until users complain
  • Root cause requires manual profiling and assembly inspection
  • Team doesn't know WHICH commit caused slowdown
  • Optimization decisions lost to history

With lockfile:
  • CI fails immediately on regression
  • Exact function and root cause identified
  • Assembly/IR diff shows what changed
  • Actionable fix suggestions provided
  • Performance becomes a first-class requirement like tests

Real-World Impact:
  • Chromium: 20% of commits have measurable performance impact
  • Without gates: Performance decays 2-3% per month (death by 1000 cuts)
  • With gates: Performance stays constant or improves

This is how you turn "Pyrite is fast" (snapshot) into "Pyrite stays fast 
forever" (guarantee). It's the missing enforcement layer for cost transparency.

Implementation Strategy
~~~~~~~~~~~~~~~~~~~~~~~

Beta Release addition (after quarry cost and quarry perf are stable):

1. **Baseline generation:** Extend quarry perf to save structured snapshot
2. **CI checking:** Add --check mode that compares against Perf.lock
3. **Regression analysis:** Correlate with compiler optimization decisions
4. **Assembly diff:** Use objdump + diff for concrete evidence
5. **IR diff:** Optional LLVM IR comparison for compiler developers

Storage format:
  • Perf.lock committed to version control (like Cargo.lock)
  • Machine-readable (YAML or JSON) for tooling
  • Human-readable for code review

Threshold configuration:

    # Quarry.toml
    [perf]
    threshold = 5              # Fail CI if >5% slower
    threshold-critical = 10    # Hard failure threshold
    baseline = "Perf.lock"     # Default baseline file
    
    [perf.functions]
    "process_data" = 2         # Critical function: 2% tolerance
    "parse_input" = 10         # Less critical: 10% tolerance

This provides the highest-leverage addition to Pyrite's existing performance 
tooling.

8.14 Interactive Learning: quarry learn
--------------------------------------------------------------------------------

Pyrite includes a built-in interactive learning system inspired by Rustlings. 
The quarry learn command provides structured exercises that teach concepts 
through practice.

Command Usage
~~~~~~~~~~~~~

    quarry learn                   # Start interactive tutorial
    quarry learn ownership         # Jump to specific topic
    quarry learn --list            # Show all available topics
    quarry learn --reset           # Reset progress

Topics covered:
  • Basics: Variables, functions, control flow
  • Ownership: Moves, borrowing, lifetimes
  • Types: Structs, enums, pattern matching
  • Collections: List, Map, iteration
  • Error handling: Result types, try operator
  • Concurrency: Threads, channels, mutexes
  • Performance: SIMD, vectorization, profiling
  • Advanced: Generics, traits, metaprogramming

Interactive Exercise Format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each exercise presents broken code that the learner must fix:

    $ quarry learn ownership
    
    ============================================================
    Exercise: Ownership 3/12 - Borrowing Rules
    ============================================================
    
    Fix the code below to satisfy the borrow checker.
    The function should process data without taking ownership.
    
    File: exercises/ownership_03.pyrite
    
        fn main():
            let data = List[int]([1, 2, 3])
            process(data)
            print(data.length())  # Error: value was moved
        
        fn process(list: List[int]):
            print("Processing...")
    
    ============================================================
    
    Try to fix it! Then run:
      quarry learn check
    
    Hint: Use & to borrow instead of moving
    Stuck? Run: quarry learn hint

Workflow:
  1. Read exercise description
  2. Edit exercise file in your editor
  3. Run quarry learn check to verify solution
  4. Get instant feedback (pass/fail + explanation)
  5. Move to next exercise automatically

Example check output:

    $ quarry learn check
    
    ✓ Code compiles successfully!
    ✓ Ownership rules satisfied
    ✓ Test cases pass
    
    Great job! You've learned:
      • How to borrow data with &T
      • When to use borrowing vs. moving
      • How to keep data usable after function calls
    
    Key concept:
      Borrowing (&) lets functions access data without taking ownership.
      The original owner retains the value and can use it after the call.
    
    Next exercise: ownership_04.pyrite (mutable borrowing)
    
    Progress: 3/12 ownership exercises complete
    Run 'quarry learn next' to continue

Hints System
~~~~~~~~~~~~

Progressive hints prevent frustration without spoiling solutions:

    $ quarry learn hint
    
    Hint 1/3:
      The problem is that 'process' takes ownership of 'list'.
      After the call, 'data' is no longer valid in 'main'.
    
    Press Enter for next hint, or Ctrl+C to try again...
    
    Hint 2/3:
      Change the function signature to borrow instead:
        fn process(list: &List[int])
    
    Press Enter for next hint...
    
    Hint 3/3 (SOLUTION):
      Change line 5 to:
        fn process(list: &List[int]):
      
      And line 3 to:
        process(&data)

Hints are spaced to encourage thinking before revealing solutions.

Progress Tracking
~~~~~~~~~~~~~~~~~

Learners can track their journey:

    $ quarry learn status
    
    Your Pyrite Learning Progress
    ==============================
    
    ✓ Basics          [████████████] 12/12 (100%)
    ✓ Ownership       [████████░░░░]  8/12 (67%)
    ░ Types           [██░░░░░░░░░░]  2/10 (20%)
    ░ Collections     [░░░░░░░░░░░░]  0/8  (0%)
    ░ Error Handling  [░░░░░░░░░░░░]  0/6  (0%)
    
    Current: ownership_09.pyrite (Lifetime basics)
    
    Estimated time to complete Ownership: 1.5 hours
    
    Run 'quarry learn next' to continue

Progress saved locally (~/.cache/pyrite/learn/progress.json).

Topic Deep-Dives
~~~~~~~~~~~~~~~~

Some topics include mini-projects:

    $ quarry learn ownership --project
    
    ============================================================
    Ownership Final Project: Build a Simple Text Editor Buffer
    ============================================================
    
    Apply everything you've learned to build a text buffer that:
      • Stores lines of text efficiently
      • Allows insertion and deletion
      • Provides undo/redo functionality
      • Manages memory safely without leaks
    
    Starter code: exercises/projects/text_buffer/
    
    Requirements:
      ✓ Pass all 15 test cases
      ✓ No memory leaks (quarry test --leak-check)
      ✓ No unsafe code blocks
      ✓ Efficient (< 100ms for 10,000 operations)
    
    This project synthesizes:
      • Ownership and borrowing
      • Mutable references
      • Collections (Vec, String)
      • Error handling
    
    Good luck! Run 'quarry test' to check your implementation.

Projects provide synthesis opportunities and build confidence.

Integration with Error Messages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The learning system connects to the compiler:

When you encounter error P0234 in real code:

    error[P0234]: cannot use moved value 'data'
      ...
      = learn: Run 'quarry learn ownership' for interactive practice
      = explain: Run 'pyritec --explain P0234' for detailed explanation

This creates a learning loop:
  1. Hit error in real code
  2. Compiler suggests relevant exercises
  3. Practice concept in isolation
  4. Return to real code with understanding

Why quarry learn Matters
~~~~~~~~~~~~~~~~~~~~~~~~~

Interactive learning addresses the "Rust is hard" perception:

  • **Structured path:** Clear progression from basics to advanced
  • **Hands-on practice:** Learn by fixing code, not reading theory
  • **Immediate feedback:** Know instantly if you got it right
  • **Progressive hints:** Never stuck, never spoiled
  • **Synthesis projects:** Apply concepts in realistic scenarios

Research shows interactive practice > passive reading for systems concepts. 
Rustlings (Rust's equivalent) is consistently praised as the best way to learn 
ownership.

Pyrite adopts this proven approach as a first-class feature, making the learning 
curve feel manageable instead of insurmountable.

Stable Release Feature
~~~~~~~~~~~~~~~

quarry learn is implemented in Stable Release (Developer Experience) after the core 
compiler and error messages are stable. It depends on:
  • Excellent error messages (to teach through failures)
  • quarry test framework (to verify solutions)
  • pyritec --explain system (for deep dives)

Once available, it becomes the recommended path for all newcomers: "Install 
Pyrite, run quarry learn, build real projects with confidence."

8.15 Integration and CI/CD
--------------------------------------------------------------------------------

CI-Friendly Commands
~~~~~~~~~~~~~~~~~~~~

Quarry provides non-interactive, CI-optimized commands:

    quarry build --locked          # Fail if Quarry.lock is outdated
    quarry test --no-fail-fast     # Run all tests, report all failures
    quarry fmt --check             # Verify formatting without changes
    quarry audit                   # Check for security vulnerabilities

Example GitHub Actions workflow:

    name: CI
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v2
          - uses: pyrite-lang/setup-quarry@v1
          - run: quarry fmt --check
          - run: quarry lint
          - run: quarry test
          - run: quarry build --release

8.16 Edition System and Stability
--------------------------------------------------------------------------------

Pyrite uses an Edition system to enable language evolution without breaking 
existing code. This is a critical trust signal for developers betting careers 
and projects on the language.

What are Editions?
~~~~~~~~~~~~~~~~~~

Editions are opt-in milestones that introduce backward-compatible changes to 
syntax, lints, and language defaults. Code written in one edition continues to 
work with newer compilers indefinitely.

Key principles:

  • **Backward compatibility:** Pyrite 2028 compiler compiles 2025 code
  • **Forward migration:** Automated tools upgrade code between editions
  • **Semantic versioning:** Editions released every 3 years (2025, 2028, 2031...)
  • **ABI stability:** Editions never break binary compatibility
  • **Interoperability:** Libraries from different editions work together

Declaring Edition
~~~~~~~~~~~~~~~~~

Projects declare their edition in Quarry.toml:

    [package]
    name = "myproject"
    version = "0.1.0"
    edition = "2025"          # Explicitly declares edition

Scripts without Quarry.toml use the latest stable edition at compilation time.

What Can Change Between Editions?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Editions can introduce:

1. **New syntax sugar:**
   - Edition 2025: `&T` for references
   - Edition 2028: Might add `?T` sugar for `Optional[T]`
   - Old code still uses `Optional[T]`, new code can choose

2. **New keywords:**
   - Edition 2028 might reserve `async` as keyword
   - 2025 code using `async` as identifier still compiles in 2025 mode

3. **Lint defaults:**
   - Edition 2028 might make certain warnings errors by default
   - 2025 code still uses 2025 lint levels

4. **Standard library additions:**
   - New modules available in all editions
   - Backward compatible only

What CANNOT Change:
  ✗ Core semantics (ownership rules remain stable)
  ✗ Type system fundamentals
  ✗ ABI/calling conventions
  ✗ Binary format
  ✗ Unsafe behavior definitions

Migration Between Editions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quarry provides automatic migration tooling:

    # Check if code is ready for new edition
    quarry edition check --target=2028
    
    # Preview migration changes
    quarry edition migrate --edition=2028 --dry-run
    
    # Apply migration
    quarry edition migrate --edition=2028
    
    # Fix any remaining issues interactively
    quarry fix --edition=2028

Migration is typically straightforward:
  • Rename identifiers that became keywords
  • Apply automatic syntax transformations
  • Update lint suppressions if needed

Example migration output:

    Migrating from Edition 2025 to Edition 2028
    ============================================
    
    Found 3 changes needed:
    
    1. src/main.pyrite:45
       Identifier 'async' is now a keyword
       → Rename to 'async_operation'
    
    2. src/parser.pyrite:123
       Deprecated syntax: match x: case 1: ...
       → New syntax: match x { 1 => ... }
    
    3. Lints now error by default:
       - unused_variables (was warning)
       - large_copy (was allow)
    
    Apply changes? [Y/n]

Mixed-Edition Projects
~~~~~~~~~~~~~~~~~~~~~~

Dependencies can use different editions:

    [package]
    edition = "2028"
    
    [dependencies]
    parser = "1.0"      # Uses edition 2025 internally
    json = "2.0"        # Uses edition 2028

The compiler bridges editions automatically. Binary interfaces remain 
compatible.

Edition Schedule
~~~~~~~~~~~~~~~~

Planned edition cadence:

  • **2025:** Launch edition (baseline)
  • **2028:** First evolution edition
  • **2031:** Second evolution edition
  • Continue every 3 years...

Each edition has:
  • 6-month beta period for community testing
  • Automated migration tools ready at launch
  • LTS support for at least 2 prior editions (6 years minimum)

Support Policy
~~~~~~~~~~~~~~

  • **Current edition:** Full support, all new features
  • **Previous edition:** Security fixes, critical bugs
  • **Two editions back:** Security fixes only
  • **Older editions:** Best-effort compatibility (compiler still accepts)

Example timeline for edition 2028:

    2028-01: Edition 2028 stable launch
    2031-01: Edition 2031 launch (2028 becomes "previous")
    2034-01: Edition 2034 launch (2028 becomes "two back")
    2037-01: Edition 2037 launch (2028 moves to best-effort)

Even after active support ends, the compiler continues to accept old editions.

Why Editions Matter
~~~~~~~~~~~~~~~~~~~

The edition system addresses the "stability vs evolution" dilemma:

  • **For established projects:** Guaranteed stability, no forced churn
  • **For new projects:** Access to latest improvements
  • **For the ecosystem:** Gradual, coordinated evolution
  • **For developers:** Confidence to invest in Pyrite

This is inspired by Rust's edition system, which successfully enabled language 
evolution (async/await, new keywords) without breaking millions of lines of 
existing code.

Trust Signal
~~~~~~~~~~~~

The edition system is a promise: "Your Pyrite code will compile in 10 years."

This commitment differentiates Pyrite from languages that break compatibility 
frequently (Python 2→3) or stagnate to avoid breaking changes. Pyrite evolves 
without breaking.

8.17 Supply-Chain Security and Trust
--------------------------------------------------------------------------------

For production systems and security-critical applications, supply-chain security 
is non-negotiable. Pyrite makes dependency trust and verification first-class 
features, not afterthoughts. This addresses the growing industry concern about 
software supply-chain attacks and dependency vulnerabilities.

Design Philosophy
~~~~~~~~~~~~~~~~~

Pyrite's approach to supply-chain security:
  • **Explicit verification:** Developers actively audit dependencies
  • **Reproducible builds:** Lockfiles and checksums prevent tampering
  • **Package signing:** Cryptographic verification of package authors
  • **Vulnerability scanning:** Automated detection of known CVEs
  • **Review manifests:** Organizations track trusted versions
  • **Minimal dependencies:** Batteries-included stdlib reduces attack surface

This makes Pyrite suitable for industries with strict security requirements 
(aerospace, medical devices, financial services, government).

quarry audit - Vulnerability Scanning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automated scanning for known security vulnerabilities in dependencies:

    quarry audit                           # Scan all dependencies
    quarry audit --json                    # Machine-readable output
    quarry audit --fix                     # Update to patched versions

Example output:

    $ quarry audit
    
    Security Audit Report
    =====================
    
    Scanning 47 dependencies...
    
    🔴 CRITICAL (2 vulnerabilities)
    
    1. CVE-2025-1234: Buffer overflow in json-parser 1.2.3
       Package: json-parser
       Installed: 1.2.3
       Fixed in: 1.2.4, 1.3.0
       Severity: CRITICAL (CVSS 9.8)
       
       Vulnerability:
         • Type: Heap buffer overflow
         • Component: JSON string parser
         • Exploitable: Remote code execution
         • Affected: parse_string() function
       
       Impact on your code:
         • Used in: src/api.py:156 (parse_json_request)
         • Exposure: User-supplied JSON input
         • Risk: High (external input, network-facing)
       
       Fix:
         Update to patched version:
           quarry update json-parser --version=1.2.4
         
         Or remove dependency if not critical:
           quarry remove json-parser
    
    🟡 WARNING (3 vulnerabilities)
    
    2. CVE-2024-5678: Denial of service in http-client 2.1.0
       [Details...]
    
    Summary:
      • 5 vulnerabilities found (2 critical, 3 warning)
      • 2 packages need updates
      • Run 'quarry audit --fix' to automatically update
    
    Last audit: 3 days ago
    Run 'quarry audit' regularly or enable in CI

CI Integration:

    # Fail CI if critical vulnerabilities found
    quarry audit --fail-on=critical
    
    # Fail on any vulnerability
    quarry audit --fail-on=any
    
    # Check and update automatically
    quarry audit --fix --ci

Audit database:
  • Quarry maintains central vulnerability database (quarry.dev/advisories)
  • Updated continuously from multiple sources (CVE, NVD, security researchers)
  • Community-reported vulnerabilities via quarry report-vuln

Benefits:
  • Continuous monitoring of known vulnerabilities
  • Automated detection in CI (no manual tracking)
  • Immediate notification of critical issues
  • One-command remediation (quarry audit --fix)

quarry vet - Dependency Review and Trust
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For organizations with strict security requirements, quarry vet provides 
dependency review and approval workflows inspired by cargo-vet:

    quarry vet                             # Show unvetted dependencies
    quarry vet review json-parser          # Review specific package
    quarry vet certify json-parser 1.2.4   # Mark version as trusted
    quarry vet import-audits --from=org    # Import organization audits

How it works:

1. **Track trusted versions:** Maintain manifest of reviewed dependencies
2. **Block unvetted packages:** Fail build if dependency not reviewed
3. **Share trust:** Organizations publish review manifests
4. **Continuous verification:** CI enforces vet requirements

Example workflow for security-critical organization:

    $ quarry vet
    
    Dependency Review Status
    ========================
    
    Unvetted dependencies (4):
    
    🔴 json-parser 1.2.4
       • Added: 2 days ago
       • Used by: src/api.py
       • Risk: Parses external input (network-facing)
       • Lines of unsafe code: 234 (12% of crate)
       • Previous version vetted: 1.2.3
       
       Action required:
         1. Review changes: quarry vet diff json-parser 1.2.3 1.2.4
         2. Audit unsafe blocks: quarry vet show-unsafe json-parser
         3. Certify if safe: quarry vet certify json-parser 1.2.4
    
    🟡 http-client 3.0.1
       • Added: 1 week ago
       • Used by: src/fetch.py
       • Risk: Network operations
       • Community reviews: 47 organizations vetted this version
       
       Quick certify (trusted by community):
         quarry vet certify http-client 3.0.1 --trust-community

Review process:

    $ quarry vet review json-parser 1.2.4
    
    Reviewing: json-parser 1.2.4
    ============================
    
    Package information:
      • Authors: security-team@example.com (verified)
      • Downloads: 1.2M last month
      • Stars: 3,400
      • Open issues: 12 (0 security-related)
    
    Changes since 1.2.3 (last vetted):
      • 15 commits
      • +234 lines, -89 lines
      • 2 unsafe blocks modified
    
    [Show diff] [Show unsafe code] [Check CVEs]
    
    Audit questions:
      1. Does it handle untrusted input safely? [Y/n]
      2. Are unsafe blocks justified and correct? [Y/n]
      3. Are dependencies vetted? [Y/n]
      4. Is error handling robust? [Y/n]
    
    Certify this version? [y/N]

Certification levels:

    quarry vet certify pkg 1.0 --level=full
      # Full audit: All code reviewed, all unsafe blocks verified
    
    quarry vet certify pkg 1.0 --level=safe-to-deploy
      # Safe for production: No known vulnerabilities, trusted author
    
    quarry vet certify pkg 1.0 --level=safe-to-run
      # Safe for development: No immediate security concerns

Import organization audits:

    # Use your organization's pre-vetted packages
    quarry vet import-audits --from=https://security.mycompany.com/pyrite-audits
    
    # Trust Mozilla's security team audits
    quarry vet import-audits --from=mozilla
    
    # Trust community consensus (50+ organizations)
    quarry vet import-audits --from=community --min-reviewers=50

Configuration (Quarry.toml):

    [vet]
    required = true                        # Fail build if unvetted deps
    import-audits = ["mozilla", "myorg"]   # Trust these sources
    allow-community = true                 # Trust community consensus
    min-community-reviews = 50             # Minimum reviewers for auto-trust

Benefits:
  • **Reduces supply-chain risk:** Every dependency explicitly reviewed
  • **Scales across organization:** Share audits, don't duplicate work
  • **Continuous verification:** CI enforces vet requirements
  • **Community trust:** Leverage collective security review efforts
  • **Audit trail:** Know who reviewed what and when

Use cases:
  • Aerospace: DO-178C requires dependency verification
  • Medical: IEC 62304 mandates security review
  • Finance: SOC 2 compliance requires supply-chain controls
  • Government: Executive Order 14028 mandates SBOM and verification

quarry sign - Package Signing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cryptographic signing of packages ensures authenticity and prevents tampering:

    # As package author
    quarry sign                            # Sign package with your key
    quarry publish --signed                # Publish with signature
    
    # As package consumer
    quarry install pkg --verify-sig        # Require valid signature
    quarry config set verify-signatures always  # Enforce for all installs

Key management:

    quarry keygen                          # Generate signing keypair
    quarry key publish                     # Publish public key to registry
    quarry key import author@example.com   # Import author's public key

Package signature verification:

    $ quarry verify json-parser
    
    Signature Verification: json-parser 1.2.4
    =========================================
    
    ✓ Package signed by: security-team@example.com
    ✓ Signature valid (RSA-4096)
    ✓ Public key verified (published 2023-04-15)
    ✓ Checksum matches: a8f39d...
    ✓ No tampering detected
    
    Author reputation:
      • 47 packages published
      • 12M total downloads
      • 0 reported vulnerabilities
      • Verified email domain

Quarry.toml configuration:

    [security]
    require-signatures = true              # Only install signed packages
    trusted-authors = [
        "security-team@example.com",
        "mozilla-team@mozilla.org"
    ]
    verify-checksums = true                # Always verify SHA-256
    reject-unsigned = true                 # Fail on unsigned packages

Registry enforcement:
  • Quarry Registry (quarry.dev) encourages signing (badged packages)
  • Security-sensitive packages require signing for featured status
  • Signature verification integrated into quarry install by default

Reproducible Builds and SBOM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Software Bill of Materials (SBOM) generation for supply-chain transparency:

    quarry sbom                            # Generate SBOM for project
    quarry sbom --format=spdx              # SPDX format
    quarry sbom --format=cyclonedx         # CycloneDX format

Example SBOM output:

    {
      "bomFormat": "CycloneDX",
      "version": "1.4",
      "components": [
        {
          "name": "json-parser",
          "version": "1.2.4",
          "purl": "pkg:quarry/json-parser@1.2.4",
          "hashes": [{"alg": "SHA-256", "content": "a8f39d..."}],
          "licenses": ["MIT"],
          "supplier": {"name": "security-team@example.com"},
          "signature": "----------BEGIN SIGNATURE----------..."
        },
        // ... all dependencies ...
      ],
      "dependencies": [
        {"ref": "json-parser", "dependsOn": ["string-utils"]}
      ]
    }

Reproducible build verification:

    quarry build --reproducible            # Enable reproducible build mode
    quarry verify-build --sbom=project.sbom  # Verify build matches SBOM

Benefits:
  • Compliance: Meet regulatory requirements (executive orders, standards)
  • Transparency: Complete visibility into dependency tree
  • Verification: Confirm what's in the binary matches declared dependencies
  • Incident response: Quickly identify affected systems when CVE announced

Use cases:
  • Government contracts (SBOM required)
  • Healthcare (FDA guidance on software dependencies)
  • Finance (audit requirements)
  • Enterprise (security policy compliance)

Integration with CI/CD
~~~~~~~~~~~~~~~~~~~~~~

Complete supply-chain security pipeline:

    # .github/workflows/security.yml
    name: Security CI
    
    jobs:
      supply-chain:
        steps:
          - name: Audit dependencies
            run: quarry audit --fail-on=critical
          
          - name: Verify all dependencies are vetted
            run: quarry vet --enforce
          
          - name: Verify signatures
            run: quarry verify --all
          
          - name: Generate SBOM
            run: quarry sbom --format=spdx --output=sbom.json
          
          - name: Upload SBOM for compliance
            uses: actions/upload-artifact@v2
            with:
              name: software-bill-of-materials
              path: sbom.json

Dashboard integration:

    quarry security-dashboard
    
    Shows:
      • Dependency vulnerability count over time
      • Unvetted dependencies requiring review
      • Signature verification status
      • SBOM compliance status
      • Audit trail (who reviewed what)

Why Supply-Chain Security Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Supply-chain attacks are increasing (SolarWinds, Log4Shell, XZ Utils backdoor). 
Languages that make security an afterthought lose trust. Pyrite makes it 
first-class:

**Industry trends:**
  • Executive Order 14028 (2021): U.S. government mandates SBOM for software
  • EU Cyber Resilience Act: Requires vulnerability disclosure and updates
  • Open source supply-chain attacks: Up 650% from 2021-2024

**Pyrite's competitive advantage:**
  • Built-in tooling (not third-party bolted on)
  • Zero-friction security (quarry audit is one command)
  • Scalable verification (import organization audits)
  • Compliance-ready (SBOM generation standard)

**Real-world impact:**
  • Rust: cargo-vet adoption growing in security-critical orgs
  • npm: Signature verification added after multiple attacks
  • Go: SBOM support added in response to executive order
  • Pyrite: Ships with all of this on day one

For embedded-first strategy, supply-chain security is **table stakes**:
  • Aerospace: Supply-chain verification required for DO-178C
  • Medical: FDA guidance mandates software composition analysis
  • Automotive: ISO 26262 requires dependency security analysis
  • Industrial: IEC 62443 mandates secure development practices

Without supply-chain security: "Just another language"
With supply-chain security: "Enterprise-ready from day one"

This is a **love multiplier** - it costs implementation time, not language 
complexity, but makes Pyrite feel "serious" and "production-ready" to 
organizations evaluating systems languages for critical infrastructure.

Implementation Timeline
~~~~~~~~~~~~~~~~~~~~~~~

Stable Release:
  • quarry audit - Vulnerability database and scanning
  • quarry sign/verify - Package signing and verification
  • Basic SBOM generation
  • quarry vet - Full review workflow with organization audits
  • Advanced SBOM features (dependency graphs, license compliance)
  • Integration with enterprise security tools

Cost: Implementation time only (no language complexity)
Impact: Trust and adoption multiplier for security-critical domains
ROI: High (required for aerospace/medical/government adoption)

8.18 Binary Size Profiling (Beta Release)
--------------------------------------------------------------------------------

For embedded systems where flash memory is constrained (32KB-512KB typical), 
binary size transparency is as critical as performance profiling. The quarry bloat 
command provides detailed analysis of what's consuming binary space, enabling 
systematic size optimization.

Command Usage
~~~~~~~~~~~~~

    quarry bloat                     # Analyze binary size
    quarry bloat --sections          # Per-section breakdown
    quarry bloat --functions         # Per-function breakdown
    quarry bloat --compare=v1.0      # Track size over time
    quarry bloat --crates            # Per-dependency breakdown

Example Output
~~~~~~~~~~~~~~

    $ quarry bloat
    
    Binary Size Analysis
    ====================
    
    Target: ARM Cortex-M4 (256 KB flash budget)
    Binary: target/thumbv7em-none-eabi/release/firmware.elf
    
    Total: 47,234 bytes (46.1 KB)
    Available: 262,144 bytes (256 KB)
    Used: 18% of flash budget ✓
    
    Largest Contributors:
    
    Section          Size      Percent
    ──────────────────────────────────
    .text (code)     38,456    81.4%
    .rodata (data)   6,234     13.2%
    .data            1,544     3.3%
    .bss             1,000     2.1%
    
    Top 10 Functions by Size:
    
    Function                          Size      Percent   Crate
    ────────────────────────────────────────────────────────────
    1. std::fmt::format_args          4,234     9.0%      std
    2. core::panic::panic_fmt         3,456     7.3%      core
    3. sensor::read_and_process       2,890     6.1%      app
    4. json::parse                    2,456     5.2%      json-parser
    5. List[u8]::grow                 1,234     2.6%      std
    6. uart::write_formatted          1,123     2.4%      hal
    7. String::fmt                    987       2.1%      std
    8. f32::to_string                 856       1.8%      core
    9. network::handle_packet         734       1.6%      app
    10. crypto::verify_signature      689       1.5%      crypto-lib
    
    Optimization Suggestions:
    
    🔴 HIGH IMPACT (save 14 KB):
    
      1. Replace std::fmt with core::fmt_minimal
         Current: 4,234 bytes (full formatting)
         Minimal: 856 bytes (basic formatting only)
         Savings: 3,378 bytes (7.1%)
         
         Change: Use --features=minimal-fmt
         Trade-off: Less flexible format strings
      
      2. Use --panic=abort instead of unwind
         Current: Panic handler + unwind = 3,456 bytes
         Abort: 234 bytes (just abort)
         Savings: 3,222 bytes (6.8%)
         
         Change: panic = "abort" in Quarry.toml
         Trade-off: No panic message on device (use debugger)
    
    🟡 MEDIUM IMPACT (save 4 KB):
    
      3. Remove unused generic instantiations
         List[u8], List[u16], List[u32] all present
         Code uses only List[u8]
         Savings: 2,468 bytes (5.2%)
         
         Run: quarry build --gc-sections (removes unused)

Comparison Mode
~~~~~~~~~~~~~~~

Track binary size over development:

    $ quarry bloat --compare=baseline.json
    
    Binary Size Comparison
    ======================
    
    Baseline: 42,156 bytes (v1.0.0)
    Current:  47,234 bytes (main branch)
    Change:   +5,078 bytes (+12.0%) ⚠️
    
    New code added:
      • sensor::read_and_process: +2,890 bytes
      • json::parse dependency: +2,456 bytes
      • Formatting changes: +856 bytes
    
    Removed code:
      • Old sensor code: -1,124 bytes
    
    Regressions (unintended size increases):
      • List[u8]::grow: 1,234 → 1,456 bytes (+222)
        Reason: New bounds checking logic added
        Consider: --no-bounds-check for release

Section Analysis
~~~~~~~~~~~~~~~~

Detailed per-section breakdown:

    $ quarry bloat --sections
    
    .text (Code) - 38,456 bytes
    ════════════════════════════════
    
    By module:
      app code:        12,345 bytes (32.1%)
      std library:     15,234 bytes (39.6%)
      dependencies:    8,456 bytes (22.0%)
      startup code:    2,421 bytes (6.3%)
    
    .rodata (Read-Only Data) - 6,234 bytes
    ════════════════════════════════════════
    
    String literals:  4,567 bytes (73.3%)
      • Error messages: 2,345 bytes
      • Log messages: 1,234 bytes
      • Config strings: 988 bytes
    
    Constants:        1,234 bytes (19.8%)
    Lookup tables:    433 bytes (6.9%)
    
    Suggestions:
      • Use --strip-strings to remove debug strings
      • Move config to external flash if available

Dependency Analysis
~~~~~~~~~~~~~~~~~~~

Show which dependencies contribute to binary size:

    $ quarry bloat --crates
    
    Size by Dependency
    ==================
    
    Crate               Size      Percent   Unused
    ─────────────────────────────────────────────
    std                 15,234    32.2%     2,345
    json-parser         8,456     17.9%     0
    crypto-lib          3,456     7.3%      567
    hal (hardware)      2,890     6.1%      0
    app (your code)     12,345    26.1%     0
    Other               4,853     10.3%     1,234
    
    Unused code: 4,146 bytes (8.8%)
      → Run with --gc-sections to remove

CI Integration
~~~~~~~~~~~~~~

Enforce size budgets in continuous integration:

    # Quarry.toml
    [build]
    max-binary-size = "64KB"        # Fail if exceeded
    warn-binary-size = "60KB"       # Warn approaching limit
    
    # CI runs:
    $ quarry bloat --check
    
    ✓ Binary size: 46.1 KB (under 64 KB limit)
    ⚠️  Warning: 76% of limit (approaching 60 KB warning threshold)

Size Optimization Modes
~~~~~~~~~~~~~~~~~~~~~~~

Embedded-specific optimization flags:

    quarry build --optimize=size     # Aggressive size optimization
    quarry build --strip-all         # Remove all debug info, symbols
    quarry build --minimal-panic     # Smallest panic handler
    quarry build --no-strings        # Remove all string literals

Example optimization progression:

    # Default release
    $ quarry build --release
    Binary: 124 KB
    
    # Size-optimized
    $ quarry build --release --optimize=size
    Binary: 87 KB (30% reduction)
    
    # Minimal embedded
    $ quarry build --release --optimize=size --strip-all --minimal-panic
    Binary: 52 KB (58% reduction)

Integration with Cost Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Binary size correlates with quarry cost static analysis:

    $ quarry bloat --explain json::parse
    
    Function: json::parse
    =====================
    Size: 2,456 bytes
    
    Breakdown:
      • String parsing: 1,234 bytes (50%)
      • Number parsing: 567 bytes (23%)
      • Error handling: 432 bytes (18%)
      • Whitespace handling: 223 bytes (9%)
    
    Why this is large:
      • Generic over multiple integer types (4 instantiations)
      • Comprehensive error messages (345 bytes strings)
      • Bounds checking for all array accesses
    
    Alternatives:
      • json::parse_minimal - 856 bytes (no error messages)
      • json::parse_streaming - 1,123 bytes (lower memory, larger code)

Why Binary Size Profiling Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is **essential for embedded-first strategy credibility:**

**Embedded constraints:**
  • STM32F103: 64 KB flash (common microcontroller)
  • Arduino Uno: 32 KB flash
  • ESP8266: 4 MB flash (large, but code + data + OTA = tight)
  • Every byte counts when targeting resource-constrained devices

**Competitive requirement:**
  • C/C++: Manual tracking, no tooling
  • Rust: cargo bloat (excellent, must match this)
  • Zig: Excellent size transparency
  • Pyrite: Must match or exceed Rust's bloat tool

**Trust factor:**
  • Embedded developers evaluate binary size immediately
  • "How big is 'Hello World'?" is first question
  • Visible bloat = "not serious about embedded"
  • Transparent profiling = "understands our constraints"

**Real-world validation:**
  • Rust's cargo bloat widely praised in embedded community
  • Binary size is top 3 concern for embedded (after correctness, performance)
  • Transparent tooling = confidence to adopt

Without quarry bloat, Pyrite's embedded-first positioning is incomplete. With it, 
Pyrite demonstrates: "We understand embedded constraints at the tooling level, 
not just language level."

Implementation: Beta Release (after core compilation is stable)
Priority: Critical for embedded-first strategy
Complexity: Low (parse ELF/PE/Mach-O symbols, sum sizes)
Impact: High (required for embedded credibility)

8.19 Deterministic and Reproducible Builds (Beta Release)
--------------------------------------------------------------------------------

To complete Pyrite's supply-chain security story and enable verifiable builds, 
Quarry provides deterministic compilation where identical source and 
configuration produce bit-for-bit identical binaries across all machines and 
environments.

Command Usage
~~~~~~~~~~~~~

    quarry build --deterministic     # Enable deterministic mode
    quarry build --reproducible      # Alias for --deterministic
    quarry verify-build              # Verify binary matches manifest
    quarry build-hash                # Generate content-addressable hash

Deterministic Mode
~~~~~~~~~~~~~~~~~~

When enabled, the compiler ensures reproducibility:

    $ quarry build --deterministic
    
    Building in deterministic mode...
    ✓ Source hash: a8f39d4e...
    ✓ Quarry.lock hash: b3c82f1a...
    ✓ Compiler version: 1.0.0
    ✓ Target: x86_64-linux
    
    Deterministic constraints enforced:
      • Fixed timestamps (SOURCE_DATE_EPOCH=1640000000)
      • Sorted symbol tables
      • Deterministic random seeds for layout randomization
      • Stable iteration order for codegen
    
    Binary: target/release/myapp
    Build hash: 7d5e9c8b3a4f2d1e... (SHA-256)
    
    Verification:
      quarry verify-build --hash=7d5e9c8b3a4f2d1e...

Configuration
~~~~~~~~~~~~~

Enable determinism by default:

    # Quarry.toml
    [build]
    deterministic = true             # All builds reproducible
    source-date-epoch = 1640000000   # Fixed timestamp
    
    [profile.release]
    deterministic = true             # Release builds always reproducible

Verification Workflow
~~~~~~~~~~~~~~~~~~~~~

Verify that a binary matches declared sources:

    $ quarry verify-build myapp --manifest=BuildManifest.toml
    
    Verifying: myapp
    ================
    
    Checking:
      ✓ Source files match manifest (SHA-256 hashes)
      ✓ Dependencies match Quarry.lock
      ✓ Compiler version: 1.0.0 (expected: 1.0.0)
      ✓ Build flags: --release --deterministic
      ✓ Target: x86_64-linux
    
    Rebuilding to verify...
    ✓ Rebuild complete
    ✓ Binary hash matches: 7d5e9c8b3a4f2d1e...
    
    VERIFIED: Binary is reproducible from declared sources

Build Manifest Format
~~~~~~~~~~~~~~~~~~~~~

Generated for every deterministic build:

    # BuildManifest.toml (committed alongside binary)
    [build]
    hash = "7d5e9c8b3a4f2d1e..."
    timestamp = "2025-12-18T10:30:00Z"
    compiler = "1.0.0"
    target = "x86_64-linux"
    flags = ["--release", "--deterministic"]
    
    [sources]
    "src/main.pyrite" = { hash = "a8f39d4e...", size = 1234 }
    "src/lib.pyrite" = { hash = "b3c82f1a...", size = 5678 }
    
    [dependencies]
    "json-parser" = { version = "1.2.4", hash = "c4d93e2b..." }
    "http-client" = { version = "3.0.1", hash = "d5e04f3c..." }

Integration with Supply-Chain Security
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reproducible builds complete the supply-chain story:

    # Verify everything about a binary
    $ quarry verify-supply-chain myapp
    
    Supply-Chain Verification
    ==========================
    
    ✓ Binary reproducible from sources
    ✓ All dependencies signed and verified
    ✓ No known CVEs in dependency tree
    ✓ All dependencies vetted by organization
    ✓ SBOM generated and matches binary
    
    Trust level: ✓✓✓✓✓ (5/5) - Fully verified

CI Enforcement
~~~~~~~~~~~~~~

Ensure builds remain reproducible:

    # .github/workflows/ci.yml
    - name: Verify reproducible build
      run: |
        quarry build --deterministic
        quarry verify-build --strict
        # Fails if build is non-deterministic

Content-Addressable Builds
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For maximum security, store binaries by content hash:

    $ quarry build-hash
    
    Content Hash: 7d5e9c8b3a4f2d1e0c9f8a7b6d5e4f3a2b1c0d9e8f7
    
    Storage path:
      ~/.cache/quarry/builds/7d/5e/9c/7d5e9c8b.../myapp
    
    Reproduce:
      quarry build-from-hash 7d5e9c8b...

Why Deterministic Builds Matter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is **essential for supply-chain security** (incomplete without it):

**Security requirements:**
  • Can't verify "this binary came from this source" without reproducibility
  • Supply-chain attacks undetectable without build verification
  • Debian, Arch Linux, F-Droid all require reproducible builds
  • Government/military: Build verification mandatory

**Competitive landscape:**
  • Rust: Reproducible by default (proven)
  • Go: Reproducible with flags
  • Zig: Strong emphasis on reproducibility
  • Pyrite: **Must match this** for credibility

**Real-world impact:**
  • SolarWinds attack: Non-reproducible builds hid backdoor
  • XZ Utils backdoor: Reproducible builds would have caught it earlier
  • Industry trend: Reproducibility becoming standard requirement

**Trust multiplier:**
  • "You can verify the binary you run" → confidence
  • "Build hash is proof" → auditable
  • "No hidden modifications" → trustworthy

**Integration with existing features:**
  • quarry sign signs the BuildManifest + binary hash
  • quarry vet verifies dependencies' build hashes
  • quarry audit checks CVEs based on verified source versions
  • quarry sbom includes build hash for traceability

Without deterministic builds, supply-chain security (Section 8.17) is incomplete. 
With it, Pyrite offers the complete package: audit + vet + sign + verify + 
reproducible. This is **table-stakes for aerospace, medical, and government 
contracts.**

Implementation: Beta Release (high priority for supply-chain security)
Complexity: Moderate (requires compiler determinism work)
Impact: Critical (required for security certification and trust)

8.20 Energy Profiling (Stable Release)
--------------------------------------------------------------------------------

To address sustainability concerns and optimize for battery-powered devices, 
Pyrite provides built-in energy profiling that makes power consumption visible 
and optimizable. This is a **unique differentiator** - no other systems language 
has first-class energy awareness.

Command Usage
~~~~~~~~~~~~~

    quarry energy                    # Profile energy consumption
    quarry energy --duration=60s     # Profile for 60 seconds
    quarry energy --compare=baseline # Detect energy regressions
    quarry energy --json             # Machine-readable output

Example Output
~~~~~~~~~~~~~~

    $ quarry energy
    
    Energy Profile (30s run, Intel i9-12900K)
    ==========================================
    
    Total energy: 45.2 joules
    Average power: 1.51 watts
    Peak power: 8.3 watts
    
    Energy Hot Spots (by component):
    
    Component            Energy    Power    Percent
    ────────────────────────────────────────────────
    CPU cores            28.4 J    0.95 W   62.8%
    DRAM                 9.2 J     0.31 W   20.4%
    CPU package          5.6 J     0.19 W   12.4%
    GPU (idle)           2.0 J     0.07 W   4.4%
    
    Top Energy-Consuming Functions:
    
    Function                Energy    CPU Time   Efficiency
    ──────────────────────────────────────────────────────────
    1. matrix_multiply      18.2 J    5.2s       3.5 J/s
       • AVX-512 active (high power draw)
       • 12 cores utilized
       • Suggestion: Lower SIMD width for battery mode
    
    2. network_poll         12.4 J    15.8s      0.78 J/s
       • Polling every 10ms (prevents CPU sleep)
       • 1,580 wake-ups
       • Suggestion: Adaptive polling (100ms when idle)
       • Energy savings: 60%
    
    3. json_parse           8.6 J     3.1s       2.8 J/s
       • Memory-intensive (high DRAM power)
       • 4,567 allocations
       • Suggestion: Pre-allocate buffers

Battery Mode Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

Build with energy-aware optimizations:

    quarry build --optimize=battery
    
    # Or in Quarry.toml:
    [profile.battery]
    opt-level = 2                    # Balance speed and power
    simd-width = 4                   # Use SSE2, not AVX-512
    adaptive-polling = true          # Longer sleep periods
    cpu-frequency = "powersave"      # Hint to OS scheduler

Energy Budget Enforcement
~~~~~~~~~~~~~~~~~~~~~~~~~~

For battery-powered devices, enforce energy constraints:

    @energy_budget(joules=0.5, duration_s=1.0)
    fn process_sensor_reading(data: &[u8]) -> Result[Reading, Error]:
        # Compiler warns if energy budget exceeded
        # Based on hardware model + instruction costs
        ...

Example enforcement:

    warning[P1501]: energy budget may be exceeded
      ----> src/sensor.py:45:5
       |
    43 | @energy_budget(joules=0.5, duration_s=1.0)
    44 | fn process_sensor_reading(data: &[u8]) -> Result[Reading, Error]:
    45 |     let result = expensive_fft(data)
       |                  ^^^^^^^^^^^^^^^^^^^ estimated 0.8 J (exceeds 0.5 J)
       |
       = note: FFT on 1024 samples estimated at 0.8 joules
       = help: Consider:
               1. Reduce sample size: fft(&data[0..512])
               2. Use lower-power algorithm: fast_approximation()
               3. Increase budget if justified

Platform Support
~~~~~~~~~~~~~~~~

Energy profiling requires platform-specific APIs:

  • **Linux:** RAPL (Running Average Power Limit) via perf
  • **macOS:** powermetrics (requires sudo)
  • **Windows:** ETW (Event Tracing for Windows) power events
  • **Embedded:** Hardware-specific power monitors (STM32 power profiler, etc.)
  • **Android/iOS:** Platform battery APIs

Fallback for unsupported platforms:
  • Estimate based on instruction costs + hardware models
  • Warn: "Energy profiling unavailable, showing estimates"

Battery-Life Estimation
~~~~~~~~~~~~~~~~~~~~~~~

For mobile/embedded applications:

    $ quarry energy --battery=2500mAh --voltage=3.7V
    
    Battery Life Estimate
    =====================
    
    Battery capacity: 2500 mAh × 3.7 V = 9.25 Wh = 33,300 J
    Average power: 1.51 W
    
    Estimated battery life:
      • Continuous operation: 6.1 hours
      • With sleep mode (90% idle): 48 hours
    
    Breakdown:
      • Active processing: 1.51 W × 10% = 0.151 W
      • Sleep mode: 0.05 W × 90% = 0.045 W
      • Average: 0.196 W
      • Battery life: 33,300 J / 0.196 W / 3600 = 47.2 hours

Why Energy Profiling Is a Differentiator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**No systems language has built-in energy profiling:**
  • C/C++: External tools only (Intel VTune, etc.)
  • Rust: No energy tooling
  • Zig: No energy tooling
  • Go: No energy tooling
  • Mojo: No energy tooling
  • **Pyrite: First-class feature**

**Growing importance:**
  • **Sustainability:** Green software movement (reduce data center energy)
  • **Mobile:** Battery life is primary UX constraint
  • **Embedded IoT:** Coin-cell batteries (years of operation required)
  • **Cloud costs:** Energy = money (AWS/Azure charge for power)
  • **Regulatory:** EU energy efficiency requirements for devices

**Marketing message:**
  • "The energy-aware systems language"
  • "Optimize for battery life, not just speed"
  • "Sustainability by design"

**Practical value:**
  • IoT devices: Optimize for coin-cell battery (10+ years target)
  • Mobile apps: "Our app uses 40% less battery" (competitive advantage)
  • Data centers: Reduce cooling costs (energy efficiency)
  • Laptops: Longer battery life = better UX

**Integration with existing tools:**
  • quarry cost shows allocations → correlate with DRAM power
  • quarry perf shows CPU usage → correlate with CPU power
  • quarry energy synthesizes: "This allocation costs 0.2 mJ"

This positions Pyrite as forward-thinking: not just fast and safe, but 
**responsible**. Sustainability-conscious developers (growing demographic) will 
appreciate that Pyrite considers the environmental impact of software.

Implementation: Stable Release (requires platform-specific power APIs)
Priority: Medium (unique differentiator, growing importance)
Complexity: Moderate (platform-specific integrations)
Impact: High (unique positioning, sustainability appeal)

8.21 Dead Code Analysis and Elimination (Beta Release)
--------------------------------------------------------------------------------

To optimize binary size and maintainability, Quarry provides comprehensive dead 
code detection and removal tooling.

Command Usage
~~~~~~~~~~~~~

    quarry deadcode                  # Find unused code
    quarry deadcode --remove         # Remove dead code automatically
    quarry build --gc-sections       # Link-time dead code elimination

Example Output
~~~~~~~~~~~~~~

    $ quarry deadcode
    
    Dead Code Analysis
    ==================
    
    Found 23 unused items (3,456 bytes in binary)
    
    Unused functions (18):
      • src/utils.py:45 - old_algorithm() [234 bytes]
        Last used: Never
        Suggestion: Remove or mark @deprecated
      
      • src/parser.py:123 - parse_legacy_format() [567 bytes]
        Last used: Removed in v1.2.0
        Suggestion: Remove (format no longer supported)
    
    Unused types (3):
      • src/types.py:89 - struct LegacyConfig [145 bytes]
        Never instantiated
        Suggestion: Remove or document why kept
    
    Unused imports (2):
      • src/main.py:5 - import old_crypto
        Module imported but never used
    
    Generic instantiations never called (5):
      • List[u16] instantiated but never used [1,234 bytes]
      • Map[i8, String] instantiated but never used [876 bytes]
    
    Total savings if removed: 3,456 bytes (7.3% of binary)
    
    Run 'quarry deadcode --remove' to apply

Automatic Removal
~~~~~~~~~~~~~~~~~

    $ quarry deadcode --remove --dry-run
    
    Would remove:
      • 18 unused functions
      • 3 unused types
      • 2 unused imports
      • 5 generic instantiations
    
    Apply? [y/N]

Link-Time Optimization
~~~~~~~~~~~~~~~~~~~~~~

    quarry build --gc-sections
    
    # Linker removes unreferenced sections
    # Effective for:
    #   • Generic instantiations never called
    #   • Library functions never used
    #   • Debug code in release builds

Integration with CI
~~~~~~~~~~~~~~~~~~~

    # Fail CI if dead code exceeds threshold
    quarry deadcode --threshold=1KB --fail
    
    error: Dead code exceeds 1KB threshold
      Current: 3.456 KB unused
      Threshold: 1 KB
    
    CI FAILURE: Remove dead code before merging

Why Dead Code Analysis Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Binary size optimization:**
  • Embedded: Every byte of flash matters
  • Distribution: Smaller binaries download faster
  • Security: Less code = smaller attack surface

**Code quality:**
  • Dead code is technical debt
  • Confuses new contributors
  • May hide bugs (code not tested because never called)

**Maintenance:**
  • Clear signal: "This code isn't used, safe to remove"
  • Prevents accumulation of cruft
  • Keeps codebase lean

Implementation: Beta Release (after core compilation is stable)
Priority: Medium-High (valuable for embedded + maintainability)
Complexity: Low (static analysis + symbol table inspection)
Impact: Medium-High (binary size + code quality)

8.22 Dependency License Compliance (Stable Release)
--------------------------------------------------------------------------------

For organizations with legal requirements, Quarry provides license compatibility 
checking and reporting to ensure dependency licenses are compatible with project 
requirements.

Command Usage
~~~~~~~~~~~~~

    quarry license-check             # Verify license compatibility
    quarry license-report            # Generate license report
    quarry sbom --licenses           # Include in SBOM

License Configuration
~~~~~~~~~~~~~~~~~~~~~

    # Quarry.toml
    [package]
    license = "MIT"
    
    [licenses]
    allowed = ["MIT", "Apache-2.0", "BSD-3-Clause"]
    denied = ["GPL-3.0", "AGPL-3.0"]  # Copyleft incompatible with MIT
    warn = ["LGPL-2.1"]                # Requires review

Example Output
~~~~~~~~~~~~~~

    $ quarry license-check
    
    License Compatibility Report
    =============================
    
    Your project: MIT License
    
    Dependencies: 47 packages
    
    ✓ Compatible: 44 packages
      • 32 packages: MIT
      • 8 packages: Apache-2.0
      • 4 packages: BSD-3-Clause
    
    ⚠️  Requires Review: 2 packages
      • json-parser 1.2.4: LGPL-2.1
        Note: LGPL requires dynamic linking or source distribution
        Your usage: Static linking
        Risk: License violation
        
        Options:
          1. Switch to MIT-licensed alternative: json-fast 2.0
          2. Use dynamic linking (--crate-type=dylib)
          3. Provide source distribution (LGPL compliance)
      
      • crypto-lib 3.0: ISC
        Note: ISC is MIT-compatible but not in allowed list
        Action: Add "ISC" to allowed licenses if acceptable
    
    ✗ INCOMPATIBLE: 1 package
      • legacy-parser 0.8: GPL-3.0
        Conflict: GPL-3.0 is copyleft, incompatible with MIT
        Your project cannot use this dependency
        
        Fix:
          1. Remove dependency: quarry remove legacy-parser
          2. Find alternative with compatible license
          3. Relicense your project (if all contributors agree)
    
    CI FAILURE: Incompatible licenses detected

CI Enforcement
~~~~~~~~~~~~~~

    # .github/workflows/ci.yml
    - name: Check license compatibility
      run: quarry license-check --fail-on=incompatible

License Report Generation
~~~~~~~~~~~~~~~~~~~~~~~~~

    $ quarry license-report --format=markdown
    
    # Generated: LICENSES.md
    
    # Third-Party Licenses
    
    This project includes the following dependencies:
    
    ## MIT License (32 packages)
    - json-parser 1.2.4
    - http-client 3.0.1
    [... full license text ...]
    
    ## Apache-2.0 (8 packages)
    - crypto-lib 3.0
    [... full license text ...]

Integration with SBOM
~~~~~~~~~~~~~~~~~~~~~

    $ quarry sbom --licenses --format=spdx
    
    {
      "components": [
        {
          "name": "json-parser",
          "version": "1.2.4",
          "licenses": ["LGPL-2.1"],
          "license-text": "...",
          "license-url": "https://opensource.org/licenses/LGPL-2.1"
        }
      ]
    }

Why License Compliance Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Legal requirements:**
  • Enterprises: Legal departments require license audits
  • Open source: GPL contamination prevents commercial use
  • Distribution: App stores require license disclosure

**Competitive feature:**
  • Rust: cargo-license (third-party, not built-in)
  • Go: go-licenses (third-party)
  • Pyrite: First-class built-in feature

**Trust signal:**
  • Shows Pyrite understands enterprise needs
  • Reduces legal risk for adopters
  • Makes Pyrite "enterprise-ready"

Implementation: Stable Release (extends SBOM work)
Priority: Medium (enterprise adoption enabler)
Complexity: Low (parse license metadata, check compatibility)
Impact: Medium (removes adoption barrier for regulated industries)

8.23 Hot Reloading for Rapid Iteration (Stable Release)
--------------------------------------------------------------------------------

For long-running processes during development, Quarry provides hot reloading that 
updates code without restarting the application, dramatically accelerating the 
iteration cycle for certain workflows.

Command Usage
~~~~~~~~~~~~~

    quarry dev                       # Watch mode with hot reload
    quarry dev --preserve-state      # Reload code, keep data structures
    quarry dev --functions-only      # Only reload function bodies

How It Works
~~~~~~~~~~~~

    $ quarry dev
    
    Starting development server...
    Watching: src/**/*.pyrite
    
    ✓ Initial build complete
    ✓ Application running (PID 12345)
    ✓ Hot reload enabled
    
    Press Ctrl+C to stop, Ctrl+R to force reload
    
    [10:30:15] File changed: src/renderer.pyrite
    [10:30:15] Recompiling renderer module...
    [10:30:16] ✓ Hot reloaded in 847ms
    [10:30:16] Application state preserved

Example Use Cases
~~~~~~~~~~~~~~~~~

**Game development:**

    # Game running at 60 FPS
    # Developer changes enemy AI logic
    # Hot reload updates AI without restarting game
    # Player position, score, etc. all preserved

**Web development:**

    # Server running, handling requests
    # Developer fixes bug in route handler
    # Hot reload updates handler function
    # Active connections preserved, no downtime

**Data processing:**

    # Processing large dataset (30 minutes expected)
    # Developer spots bug in processing function
    # Hot reload fixes bug mid-run
    # Already-processed data not re-computed

Restrictions and Safety
~~~~~~~~~~~~~~~~~~~~~~~

Hot reloading only works for certain changes:

    ✓ Function bodies (logic changes)
    ✓ Method implementations
    ✓ Constants and static data
    ✓ Module-level functions
    
    ✗ Type definitions (struct fields, enum variants)
    ✗ Function signatures (parameters, return types)
    ✗ Unsafe blocks (requires full recompilation)
    ✗ Dependency changes (requires restart)

When incompatible change detected:

    [10:35:42] File changed: src/types.pyrite
    [10:35:42] ✗ Cannot hot reload (struct fields changed)
    [10:35:42] Restart required: quarry dev --restart

Safety Guarantees
~~~~~~~~~~~~~~~~~

Hot reloading maintains safety:
  • Ownership rules still enforced (can't hot-reload into invalid state)
  • Type changes rejected (would break memory layout assumptions)
  • Unsafe changes rejected (require audit)
  • Only safe, compatible changes allowed

Implementation Approach
~~~~~~~~~~~~~~~~~~~~~~~

    1. Monitor source files for changes
    2. Incremental recompilation of changed module
    3. Dynamic library loading (dlopen) for new code
    4. Atomic function pointer swap (single instruction)
    5. Old code GC'd when no longer referenced

State Preservation
~~~~~~~~~~~~~~~~~~

Developer controls what state persists:

    @hot_reload(preserve_state = true)
    static mut CACHE: Map[String, Data] = Map::new()
    
    fn process(key: &str) -> Data:
        # CACHE survives hot reload
        # Function body can be updated

Configuration
~~~~~~~~~~~~~

    # Quarry.toml
    [dev]
    hot-reload = true
    preserve-state = ["CACHE", "CONNECTIONS"]
    watch-paths = ["src/**/*.pyrite"]
    ignore-paths = ["src/generated/**"]

Why Hot Reloading Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Developer joy:**
  • Game dev: Tweak gameplay without losing session
  • Web dev: See changes instantly (no restart)
  • Data science: Iterate on algorithms mid-computation
  • Learning: Faster experimentation ("what if I change this?")

**Competitive parity:**
  • Rust: rust-analyzer supports limited hot reload
  • Erlang/Elixir: Hot code swapping is flagship feature
  • JavaScript: Hot Module Replacement (HMR) standard
  • Python: importlib.reload() for modules

**Productivity multiplier:**
  • Restart time: 5-30 seconds typical
  • Hot reload: <1 second
  • 100 iteration cycles: 8-50 minutes saved per session

**Limitations:**
  • Debug builds only (not for production)
  • Requires explicit design (not all code hot-reloadable)
  • Best effort (some changes still require restart)

Implementation: Stable Release (after incremental compilation is stable)
Priority: Medium (developer experience enhancement)
Complexity: High (dynamic loading, state management)
Impact: Medium-High (productivity boost for certain workflows)

8.24 Incremental Compilation (Beta Release)
--------------------------------------------------------------------------------

Fast rebuilds are essential for developer productivity. Quarry implements 
incremental compilation to cache unchanged modules and recompile only what's 
necessary.

Command Usage
~~~~~~~~~~~~~

    quarry build --incremental       # Enable incremental compilation (default)
    quarry build --no-incremental    # Force full rebuild
    quarry clean --incremental       # Clear incremental cache

How It Works
~~~~~~~~~~~~

    $ quarry build --incremental
    
    Checking incremental cache...
    ✓ Cached: 234 modules (unchanged)
    ✓ Recompiling: 3 modules (modified)
    ✓ Relinking: target/debug/myapp
    
    Finished in 1.8s (full build: 28s, 15.5x faster)

Incremental Strategy
~~~~~~~~~~~~~~~~~~~~

Compiler tracks:
  • Source file hashes (detect changes)
  • Dependency graph (what depends on what)
  • Module interface fingerprints (detect API changes)
  • Cached compilation artifacts per module

Rebuild decision tree:
  • File unchanged → use cached artifact
  • File changed, interface unchanged → recompile, no downstream rebuilds
  • File changed, interface changed → recompile + all dependents

Example:

    src/utils.pyrite:
      - Changed: Implementation only (private function)
      - Interface: Unchanged (public API same)
      - Action: Recompile utils.pyrite only
      - Dependents: No rebuild needed
    
    src/types.pyrite:
      - Changed: Added struct field
      - Interface: Changed (public API modified)
      - Action: Recompile types.pyrite + all dependents
      - Dependents: main.pyrite, parser.pyrite, renderer.pyrite (all rebuild)

Performance Characteristics
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Typical rebuild times:

    | Project Size      | Full Build | Incremental | Speedup |
    |-------------------|------------|-------------|---------|
    | Small (10K LOC)   | 3s         | 0.5s        | 6x      |
    | Medium (100K)     | 28s        | 1.8s        | 15x     |
    | Large (1M)        | 320s       | 12s         | 27x     |

Cache Management
~~~~~~~~~~~~~~~~

    quarry cache info                # Show cache statistics
    quarry cache clean               # Remove stale cache entries
    quarry cache purge               # Delete entire cache

Example cache info:

    Incremental Cache Statistics
    =============================
    
    Location: ~/.cache/quarry/incremental
    Size: 1.2 GB (234 projects cached)
    
    Current project:
      • Cached modules: 234
      • Cache size: 45 MB
      • Last full build: 2025-12-18 10:30:00
      • Incremental builds: 147 since last full build
      • Average incremental time: 1.2s

Why Incremental Compilation Is Essential
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Developer experience:**
  • Fast iteration = more experimentation
  • Slow rebuilds = frustration, context switching
  • 1-2s rebuilds feel instant, 30s rebuilds feel slow

**Competitive requirement:**
  • Rust: Incremental compilation standard (expected)
  • Go: Fast compilation by default
  • C++: ccache, distcc for incremental builds
  • **Without this, Pyrite feels slow even if compiler is fast**

**Learning impact:**
  • Beginners iterate more when feedback is instant
  • "Change → test" loop should be <5s
  • Slow rebuilds discourage experimentation

**Real-world data:**
  • Google: 30% productivity increase with faster builds
  • Rust: Incremental compilation adoption correlated with satisfaction
  • Developer survey: "Fast builds" in top 5 language features

Implementation: Beta Release (essential for developer experience)
Priority: Critical (expected feature, high impact on satisfaction)
Complexity: Moderate (requires module dependency tracking)
Impact: High (productivity multiplier for all developers)

8.25 Community Transparency Dashboard (Stable Release)
--------------------------------------------------------------------------------

To make Pyrite's goal of widespread developer adoption measurable rather than purely 
aspirational, the ecosystem provides a public metrics dashboard at quarry.dev/metrics that 
displays real-time, verifiable data about language performance, safety, 
learning, and adoption.

Dashboard Contents
~~~~~~~~~~~~~~~~~~

**Performance Metrics (User-Submitted Benchmarks):**

    Pyrite vs Competitors (1,247 benchmarks)
    ========================================
    
    Average performance relative to C:
      • Pyrite: 98.3% of C speed
      • Rust: 97.1% of C speed
      • Zig: 99.1% of C speed
      • Go: 82.4% of C speed
    
    Compilation speed:
      • Pyrite: 1.2s average (100K LOC project)
      • Rust: 8.4s average
      • C++: 12.3s average
      • Go: 0.8s average
    
    Binary size (Hello World):
      • Pyrite: 312 KB
      • Rust: 387 KB
      • C (dynamic): 8 KB
      • C (static): 2.1 MB
      • Go: 2.0 MB

**Safety Metrics (CVE Tracking):**

    Memory Safety CVEs (2020-2025)
    ===============================
    
    Language    Total CVEs    Memory-Related    Percentage
    ──────────────────────────────────────────────────────
    C           1,247         892               71.5%
    C++         1,089         654               60.1%
    Rust        23            0                 0%
    Go          89            4                 4.5%
    Pyrite      0             0                 0%
    
    Data races:
      • C/C++: Not preventable by language
      • Rust: 0 (prevented by type system)
      • Go: 12 (race detector catches at runtime)
      • Pyrite: 0 (prevented by ownership system)

**Learning Metrics (quarry learn Data):**

    Learning Curve Analysis
    =======================
    
    Exercise completion rates:
      • Ownership exercises: 82% complete all 12
      • SIMD exercises: 67% complete
      • Concurrency: 74% complete
    
    Comparison with Rust:
      • Rust ownership exercises: 64% complete
      • Pyrite advantage: 28% higher completion
    
    Time to productivity:
      • Pyrite: 2.3 weeks average (first PR)
      • Rust: 4.1 weeks average
      • C++: 6.8 weeks average
    
    quarry fix usage:
      • 89% of beginners use quarry fix --interactive
      • Average fixes per developer: 147
      • Adoption: "Compiler taught me ownership" - 94%

**Ecosystem Health:**

    Quarry Registry Metrics
    =======================
    
    Total packages: 15,247
    Growth: +23% month-over-month
    
    Package categories:
      • Embedded/HAL: 3,456 packages
      • Web frameworks: 2,345 packages
      • CLI tools: 1,890 packages
      • Crypto/security: 1,234 packages
    
    Active maintainers: 2,340 (↑ 18% MoM)
    Security audits: 1,456 packages vetted
    
    Dependency health:
      • 94% of packages updated in last 6 months
      • Average dependencies: 4.2 (vs Rust: 8.7)
      • Batteries-included stdlib reduces dependency hell

**Compile-Time Safety:**

    Bugs Caught at Compile Time
    ============================
    
    (Data from user error reports)
    
    Error category               Frequency   C/C++ equivalent
    ──────────────────────────────────────────────────────────
    Use-after-move              34.2%       Use-after-free (segfault)
    Borrow conflicts            23.5%       Data races (UB)
    Type mismatches             18.7%       Type punning (UB)
    Unhandled errors            12.4%       Unchecked returns (bugs)
    Lifetime violations         11.2%       Dangling pointers (segfault)
    
    Estimated bugs prevented: 3,247 per 100K LOC
    (Compared to typical C/C++ project with same code structure)

**Adoption Metrics:**

    Production Deployments
    ======================
    
    Companies using Pyrite: 1,247
    Industries:
      • Embedded/IoT: 34%
      • Web services: 28%
      • Gaming: 15%
      • Finance: 12%
      • Other: 11%
    
    Lines of code in production: 47M
    Developer satisfaction: 8.7/10
    Would recommend: 89%

Public API
~~~~~~~~~~

Dashboard data accessible via API:

    # Query metrics programmatically
    curl https://quarry.dev/api/metrics/performance
    
    # Embed in documentation
    <script src="https://quarry.dev/widgets/metrics.js"></script>

Community Contribution
~~~~~~~~~~~~~~~~~~~~~~

Users can submit benchmark data:

    quarry bench --upload            # Upload benchmark to metrics
    quarry bench --compare=community # Compare with community average

Privacy and opt-in:
  • Anonymous by default (no personal data)
  • Opt-in for benchmark submission
  • Aggregated statistics only (no individual user data)

Why Transparency Dashboard Is Transformative
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Makes developer adoption measurable:**

  • Not subjective claim, but verifiable data
  • "98% of C speed" with proof, not promises
  • "82% complete ownership exercises" shows teachability
  • Real-world evidence beats marketing claims

**Competitive positioning:**
  • Direct comparison with C/Rust/Zig/Mojo
  • Show strengths objectively (compile speed, safety, learning curve)
  • Acknowledge trade-offs honestly (ecosystem size, maturity)

**Trust multiplier:**
  • "See the data yourself" builds confidence
  • Open data = transparent community
  • Track progress over time (metrics improve as language matures)

**Gamification:**
  • Package maintainers compete for "most-used" ranking
  • Contributors see impact ("my PR improved compile time 12%")
  • Community engagement through visible metrics

**Evidence-based advocacy:**
  • "Pyrite caught 3,247 bugs per 100K LOC" → share with CTO
  • "15x faster compilation than Rust" → share with team
  • "28% higher learning success rate" → share with educators

**Example impact:**
  • Rust doesn't have public dashboard → metrics scattered
  • Go has limited metrics → not comprehensive
  • Pyrite dashboard → one place for all evidence
  • Result: "Just look at quarry.dev/metrics" becomes standard response

This transforms subjective claims into objective evidence. The path to "most 
admired" becomes visible: watch metrics improve over time, celebrate milestones 
publicly, demonstrate progress to skeptics.

Implementation: Stable Release (after core language is stable)
Priority: High (trust multiplier, advocacy enabler)
Complexity: Moderate (web dashboard, data aggregation, privacy)
Impact: High (makes success measurable, enables evidence-based marketing)

8.26 Why Quarry Matters
--------------------------------------------------------------------------------

Developer Experience = Language Adoption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stack Overflow surveys correlate Rust's growth with Cargo's excellence. Quarry 
delivers similar experience:

  • Zero configuration for common cases
  • One obvious way to do things
  • Fast, reliable builds with caching
  • Reproducible across environments
  • Integrated testing, docs, formatting
  • Frictionless dependency management
  • Cross-compilation out of the box
  • Script mode for rapid prototyping
  • Edition system for long-term stability

Quarry transforms Pyrite from "interesting language" to "practical tool I want 
to use daily." Great tooling is the difference between languages that are 
admired in theory versus loved in practice.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Advanced Features (Traits, Generics, and More)](07-advanced-features.md)

**Next**: [Standard Library and Ecosystem](09-standard-library.md)
