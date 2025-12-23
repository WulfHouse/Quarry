---
title: "Design Goals and Philosophy"
section: 1
order: 1
---

> **⚠️ Note:** This is part of the aspirational SSOT specification. It represents the intended design and vision for Pyrite, not necessarily the current implementation state. See [SSOT_DISCLAIMER.md](../SSOT_DISCLAIMER.md) for important information.

# Design Goals and Philosophy

================================================================================

Pyrite is a compiled systems programming language designed to combine the 
low-level power and performance of C with the readability and ease-of-use of 
Python, while integrating the safety of Rust and the simplicity of Zig. 

The core design goals of Pyrite are outlined below:

1.1 Simplicity and Minimalism by Default
--------------------------------------------------------------------------------

Pyrite's syntax and feature set are kept minimal and straightforward. A beginner 
should find Pyrite easy to learn and read, akin to Python. Advanced features are 
opt-in rather than mandatory, meaning they introduce no complexity or cost unless 
explicitly used. 

This follows the Python philosophy that "Explicit is better than implicit" and 
"Simple is better than complex". In practice, Pyrite favors clear, transparent 
constructs over "magic" or implicit behavior. There are no hidden surprises - 
what the code looks like is exactly what it will do when executed.

1.2 C-Level Performance, Zero Runtime Overhead
--------------------------------------------------------------------------------

Pyrite programs compile to efficient native machine code with performance on par 
with C. Every high-level construct in the language is designed as a zero-cost 
abstraction, compiling down to equivalent low-level code with no extra overhead 
beyond what a skilled C programmer might write. 

There is no heavyweight runtime or VM: no global interpreter loop, no JIT 
compilation, and no stop-the-world garbage collector. Pyrite has a minimal 
runtime footprint suitable for resource-constrained environments. Features that 
involve dynamic memory allocation or other expensive operations are never 
implicit - they only occur if the programmer explicitly uses them. If you don't 
use a feature, it imposes zero cost on the binary. 

This approach is validated by other modern languages: for example, Rust programs 
achieve memory-safe, high-level abstractions without sacrificing speed or 
introducing a GC, and emerging languages like Mojo have demonstrated that it is 
possible to achieve performance comparable to C++/Rust even with a high-level, 
Pythonic syntax by relying on static typing and compile-time optimization.

1.3 Memory Safety by Default (Manual Control Optional)
--------------------------------------------------------------------------------

A primary objective of Pyrite is to eliminate common memory bugs (buffer 
overflows, use-after-free, null pointer dereferences, data races, etc.) at 
compile time, without sacrificing performance. By default, Pyrite ensures memory 
safety through strict compile-time checks inspired by Rust's ownership model, so 
that well-typed Pyrite code cannot perform invalid memory accesses. 

In other words, safe Pyrite code is memory-safe and data race-free by 
construction, similar to Rust's guarantees. However, unlike purely managed 
languages, Pyrite also permits manual memory management when needed. Developers 
can drop down to low-level pointer manipulation or explicit allocate/free control 
for specialized use cases, but such code must be marked as unsafe or use special 
APIs. 

This provides an "escape hatch" for power users (much like Rust's unsafe blocks), 
while keeping safe code free of memory errors. In short, safe by default, unsafe 
by choice.

1.4 Pythonic, Readable Syntax
--------------------------------------------------------------------------------

Pyrite's syntax is heavily influenced by Python to lower the barrier to entry for 
beginners. Code uses indentation for blocks (significant whitespace) instead of 
curly braces or heavy punctuation. Keywords and control flow structures read like 
English. 

The goal is that someone with minimal coding experience can quickly grasp Pyrite 
code structure. For example, function definitions, loops, and conditionals use a 
clean, uncluttered syntax similar to Python. This emphasis on readability follows 
the Zen of Python's maxim that "Readability counts." At the same time, the syntax 
has been adapted to a statically-typed, compiled context in a way that feels 
natural and intuitive for systems programming.

1.5 Intuitive Memory Model for Learners
--------------------------------------------------------------------------------

Pyrite is designed to make low-level concepts like memory allocation, lifetimes, 
and data structure performance characteristics as transparent as possible, so 
that even beginners can understand what the code is doing under the hood. 

It should be apparent to the programmer whether a given data type or variable is 
allocated on the stack or on the heap, and what the implications are for 
performance. For instance, the language makes a clear distinction between value 
types allocated on the stack vs. heap-allocated objects, using syntax and 
semantics that convey the difference. 

Expensive operations (like copying a large structure or growing a dynamic array) 
are not hidden - they require an explicit action or are documented, so a learner 
can reason about cost. This explicitness echoes Python's clarity and Zig's 
philosophy of not hiding costly operations from the programmer. 

By designing the language in this way, even developers new to systems programming 
can intuitively learn how memory management works (whether via an ownership 
system or via manual malloc/free), and can develop a performance intuition from 
the start.

1.6 Complete Systems Programming Capabilities
--------------------------------------------------------------------------------

Pyrite is intended as a "do-anything" systems language. Anything you can do in 
C, you can do in Pyrite. This includes low-level hardware manipulation in 
embedded systems and OS kernels, as well as high-level application, game engine, 
and web server programming. 

The language imposes no runtime or library requirements that would hinder writing 
an OS kernel or interfacing directly with memory and devices. You can write 
bare-metal code with no operating system at all, or, at the other extreme, use 
Pyrite for high-level scripting and application development. 

This versatility is a key goal: Pyrite is meant to scale from microcontrollers to 
large distributed applications. Interfacing with existing C/C++ code is 
straightforward - Pyrite provides a foreign function interface (FFI) to call C 
functions directly, and Pyrite's compiler can produce binaries that conform to C 
ABI conventions for easy linking. 

In practice, this means you can gradually adopt Pyrite in existing C/C++ 
projects, or use Pyrite as a safer alternative for new modules, with minimal 
friction. (Interoperability is considered so important that Pyrite is designed to 
make conforming to the C ABI straightforward, similar to Zig's approach of 
treating C interop as a first-class requirement.)

1.7 Modern Features, Optional Complexity
--------------------------------------------------------------------------------

While keeping the core language simple, Pyrite doesn't shy away from powerful 
features that improve safety or developer ergonomics - it simply makes them 
optional. This includes things like generics (parametric polymorphism), algebraic 
data types and pattern matching, compile-time code execution (for metaprogramming 
and optimization), a built-in package/module system, and advanced concurrency 
primitives. 

These features are inspired by the successes of Rust and Zig: for example, Rust's 
trait system and pattern matching, or Zig's compile-time evaluation and explicit 
allocator model. Such features are available for use when needed to write 
high-level abstractions or libraries, but the average user can start with a much 
simpler subset of the language. 

Crucially, no feature is "magic" - each is designed to have predictable cost and 
behavior, aligning with the principle of explicitness. For instance, there are no 
implicit class destructors or unexpected operator overloads that hide control 
flow or allocate memory behind the scenes. If something significant (like 
allocation or locking) is happening, the code makes it obvious. 

This means the language can grow with the programmer: beginners can stick to the 
simple core (like variables, loops, and basic structs), while experts can opt-in 
to advanced patterns without runtime overhead. 

By adhering to these principles, Pyrite aims to be a language that developers 
truly enjoy using. It strives to be as approachable and fun as Python, as safe 
and robust as Rust, and as lightweight and transparent as Zig. In spirit, Pyrite 
tries to embody what developers admire most in those languages - for example, 
Rust's strong safety guarantees without needing a garbage collector, Python's 
elegant syntax and philosophy, and Zig's emphasis on explicit control - in one 
unified toolset.

1.8 Core Language Subset for Learning
--------------------------------------------------------------------------------

To support Pyrite's goal of being approachable to beginners while remaining 
powerful for experts, the language defines a semantic "Core" subset. This is NOT 
a separate syntax or dialect, but rather a well-defined subset of features that:

• Provides a complete, practical programming environment for learners
• Compiles to identical machine code as full Pyrite (no performance penalty)
• Desugars into full Pyrite semantics (zero runtime differences)
• Can be enforced via tooling (linter modes, compiler flags) rather than 
  language fragmentation

The Core subset philosophy:
  - Forbids or warns about advanced features: unsafe blocks, manual allocators, 
    complex lifetime annotations, advanced generic patterns
  - Includes all fundamental features: basic types, structs, enums, pattern 
    matching, ownership/borrowing basics, standard collections, defer, with
  - Enables real systems programming: Core code is production-ready, not a toy
  - Grows with the programmer: Code written in Core remains valid as developers 
    adopt advanced features

This is implemented through:
  • Compiler mode: pyritec --core-only rejects advanced features
  • Linter levels: quarry lint --beginner warns about complexity
  • Standard library tiers: core:: namespace vs std:: full library
  • Documentation paths: "Core Pyrite" learning track vs full language reference

By keeping Core as a semantic subset rather than syntactic variation, developers 
learn "real Pyrite" from day one, and all code remains compatible as skills 
advance. This avoids ecosystem fragmentation while maintaining approachability.

1.9 Target Audiences
--------------------------------------------------------------------------------

Pyrite is optimized primarily for **Python-first beginners with systems 
programming aspirations**, with a strong secondary audience of **Rust-curious 
developers seeking an easier path** to systems programming.

Primary Audience: Python Beginners
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These developers know Python's syntax and philosophy, but need:
  • C-level performance without C-level complexity
  • Understanding of memory management and performance
  • Type safety and compile-time error catching
  • Ability to write OS kernels, embedded systems, game engines

Pyrite's Pythonic syntax, explicit design, and teaching compiler make systems 
concepts accessible to this audience.

Secondary Audience: Rust-Curious Developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Developers who bounced off Rust's learning curve but appreciate its goals:
  • Already understand the value of ownership and memory safety
  • Found Rust's syntax or borrow checker too complex initially
  • Want the same safety guarantees with gentler onboarding
  • Appreciate Rust's performance but need faster productivity

Pyrite offers the same safety model with more familiar syntax and better 
pedagogical tooling (auto-fix, visual diagrams, explicit-by-default).

Design Tradeoff Philosophy
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When design decisions conflict between audiences, favor beginners. However, 
never alienate Rust-familiar developers:
  • Keep &str working alongside Text alias
  • Ownership model identical to Rust (familiar to experts)
  • Advanced features available but optional (growth path)

This ensures beginners get gentle onboarding while experts don't feel 
the language has been oversimplified at their expense.

1.10 Ultimate Vision
--------------------------------------------------------------------------------

Pyrite's ultimate goal is to become one of the most widely adopted and desired 
programming languages of its era - the kind of language that consistently ranks 
highly in developer surveys for satisfaction and preference. This goal underpins its 
design: by blending power and simplicity in a distinctive way, Pyrite aims to attract 
both low-level systems programmers and high-level application developers. 

(Notably, the Rust language has ranked as the most "loved" language on the Stack 
Overflow survey for multiple years, largely due to its combination of performance 
and safety. Pyrite seeks to match or exceed that level of developer admiration by 
offering similar benefits with an easier learning curve and more familiar syntax.)

The key to achieving widespread developer adoption lies not just in language features, 
but in the complete developer experience: world-class compiler diagnostics 
(including auto-fix and visual learning tools), frictionless tooling (Quarry 
build system with cost analysis), comprehensive standard library, and a thriving 
ecosystem. These elements transform Pyrite from merely a good language into one 
developers actively love using and recommend to others.

The following sections provide a thorough specification of Pyrite's syntax, 
semantics, and features - detailed enough to serve as a foundation for 
implementing a compiler and using the language effectively.

1.11 Unique Differentiators: What Makes Pyrite Special
--------------------------------------------------------------------------------

Pyrite combines proven ideas from multiple languages, but adds distinctive features 
that few other systems languages provide in combination. This section highlights the 
distinctive capabilities that position Pyrite to achieve widespread developer adoption.

Features No Other Systems Language Has
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Interactive REPL with Ownership Visualization (Section 8.7)**
   - Real-time ownership state displayed as you type
   - :cost, :type, :ownership commands for exploration
   - Makes abstract concepts tangible through direct interaction
   - Critical gap: Rust has third-party REPL, C/C++/Zig have none with ownership viz

2. **Energy Profiling Built-In (Section 8.20)**
   - quarry energy shows power consumption and battery impact
   - Optimize for sustainability and battery life
   - Few other systems languages provide built-in energy profiling
   - Growing importance: green software, mobile, IoT

3. **Two-Tier Closure Model with Explicit Syntax (Section 7.5)**
   - fn[...] = compile-time (zero-cost) vs fn(...) = runtime (may allocate)
   - Visual syntax makes cost explicit, not optimization-dependent
   - Enables verifiable --no-alloc mode
   - Mojo has similar concept but less explicit syntax

4. **Call-Graph Blame Tracking for Performance Contracts (Section 4.5)**
   - @noalloc violations show complete call chain
   - "Function A called B called C which allocated"
   - Actionable fixes at every level
   - Unique: performance contracts that compose across boundaries

5. **Community Transparency Dashboard (Section 8.25)**
   - Public real-time metrics: performance, safety, learning, adoption
   - Makes developer adoption metrics measurable, not just aspirational
   - Evidence-based advocacy (show data, not claims)
   - No competitor has comprehensive public metrics

6. **Internationalized Compiler Errors (Section 2.7)**
   - Native language diagnostics (Chinese, Spanish, Hindi, Japanese, etc.)
   - Professional translations, not machine translation
   - Critical for global adoption (60% non-native English)
   - Almost no compilers do this well

7. **Performance Lockfile with Regression Root Cause (Section 8.13)**
   - Perf.lock commits performance baseline to version control
   - CI fails on regression with assembly diff and root cause
   - "SIMD width changed from 8 to 4 due to alignment"
   - Prevents "death by 1000 cuts" performance decay

8. **Design by Contract Integrated with Ownership (Section 7.3)**
   - @requires, @ensures, @invariant for logical correctness
   - Compose with ownership (memory safety) and @cost_budget (performance)
   - First systems language with ownership + contracts + performance contracts
   - Enables highest safety certification levels

Features That Match Best-in-Class (Competitive Parity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  • Memory safety (equal to Rust)
  • Zero-cost abstractions (equal to Rust/C++)
  • Compile-time evaluation (equal to Zig)
  • Borrow checking (equal to Rust, better error messages)
  • Cross-compilation (equal to Zig)
  • Package manager (equal to Cargo)
  • Fuzzing + sanitizers (equal to Rust/Go)
  • Supply-chain security (equal to or better than Rust cargo-vet)

Features That Exceed Competitors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  • **Learning curve:** Gentler than Rust (Pythonic syntax, interactive tools)
  • **Error messages:** More visual than Rust (ownership flow diagrams)
  • **Cost transparency:** More explicit than Zig (multi-level reporting)
  • **Tooling integration:** More comprehensive than any competitor (50+ features)
  • **Binary size tools:** Equal to Rust cargo bloat (critical for embedded)
  • **Deterministic builds:** Equal to Rust (essential for security)
  • **Formal semantics:** Better than Rust (mathematical specification)

The "Most Admired" Formula
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most languages excel in 2-3 dimensions. Pyrite excels in 8:

  1. **Safety** → Ownership + contracts + formal verification
  2. **Performance** → Zero-cost + profiling + optimization + energy
  3. **Learning** → REPL + Playground + exercises + visual errors + native language
  4. **Productivity** → Incremental builds + hot reload + auto-fix + great diagnostics
  5. **Transparency** → Cost + size + energy + public metrics
  6. **Security** → Audit + vet + sign + reproducible + formal methods
  7. **Production** → Observability + testing + debugging + certification
  8. **Global** → Internationalization + accessibility + evidence

This represents the difference between a good language and one that achieves 
widespread developer adoption and satisfaction.

**Complete, not fragmented.** No external tools required. No complex configuration 
requirements. No need to piece together solutions from multiple sources. Everything 
is integrated, consistent, and well-designed.

This approach to improving developer experience focuses on removing every friction 
point, delivering every expected feature, and adding unique capabilities that 
competitors may not provide. Pyrite aims to match or exceed the best systems 
languages while being more accessible.

Quick Feature Comparison Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| Feature                        | Pyrite | Rust | Zig | C/C++ | Go  | Mojo |
|--------------------------------|--------|------|-----|-------|-----|------|
| **Core Language**              |        |      |     |       |     |      |
| Memory safety by default       | Y      | Y    | N   | N     | Y   | Y    |
| Zero-cost abstractions         | Y      | Y    | Y   | Y     | N   | Y    |
| No garbage collector           | Y      | Y    | Y   | Y     | N   | N    |
| No runtime overhead            | Y      | Y    | Y   | Y     | N   | N    |
| Pythonic syntax                | Y      | N    | N   | N     | P   | Y    |
| **Learning & Productivity**    |        |      |     |       |     |      |
| Interactive REPL               | Y      | 3rd  | N   | N     | N   | Y    |
| Ownership visualization        | Y      | N    | N/A | N/A   | N/A | N    |
| Interactive exercises          | Y      | 3rd  | N   | N     | N   | N    |
| Multilingual errors            | Y      | P    | N   | N     | N   | N    |
| Auto-fix suggestions           | Y      | Y    | N   | N     | Y   | N    |
| **Performance & Analysis**     |        |      |     |       |     |      |
| Cost transparency              | Y      | P    | Y   | N     | N   | P    |
| Binary size profiling          | Y      | Y    | Y   | N     | N   | N    |
| Energy profiling               | Y      | N    | N   | N     | N   | N    |
| Performance lockfile           | Y      | N    | N   | N     | N   | N    |
| Call-graph blame tracking      | Y      | N    | N   | N     | N   | N    |
| Incremental compilation        | Y      | Y    | P   | P     | Y   | Y    |
| **Security & Verification**    |        |      |     |       |     |      |
| Deterministic builds           | Y      | Y    | Y   | N     | P   | N    |
| Supply-chain security          | Y      | Y    | N   | N     | P   | N    |
| Fuzzing built-in               | Y      | Y    | N   | N     | Y   | N    |
| Sanitizers integrated          | Y      | Y    | P   | 3rd   | Y   | N    |
| Design by Contract             | Y      | N    | N   | N     | N   | N    |
| Formal semantics               | Y      | P    | N   | Y     | N   | N    |
| **Production & Deployment**    |        |      |     |       |     |      |
| Built-in observability         | Y      | 3rd  | N   | N     | Y   | N    |
| Hot reloading                  | Y      | 3rd  | N   | N     | N   | N    |
| Cross-compilation              | Y      | Y    | Y   | P     | Y   | N    |
| No-alloc verification          | Y      | P    | N   | N     | N   | N    |
| **Ecosystem & Community**      |        |      |     |       |     |      |
| Official package manager       | Y      | Y    | P   | N     | Y   | P    |
| Metrics dashboard              | Y      | N    | N   | N     | N   | N    |
| License compliance             | Y      | 3rd  | N   | N     | 3rd | N    |
| Dead code analysis             | Y      | 3rd  | N   | N     | N   | N    |

**Legend:**
  • Y = Built-in first-class feature (Yes)
  • 3rd = Available through third-party tools
  • P = Partial support or limited implementation
  • N = Not available or not applicable (No)
  • N/A = Concept doesn't apply (no ownership system)

**Unique Features (8):** REPL with ownership viz, energy profiling, performance 
lockfile, call-graph blame, contracts, formal semantics (comprehensive), 
community dashboard, internationalized errors (comprehensive)

**Best-in-Class (5):** Memory safety, supply-chain security, cost transparency, 
compiler diagnostics, binary size tools

**Result:** 8 distinctive features + 5 best-in-class capabilities + Pythonic syntax 
= comprehensive differentiation strategy

1.12 Getting Started: Developer Journey
--------------------------------------------------------------------------------

To illustrate how all these features work together, here's the typical developer 
journey from first install to production deployment.

Day 1: Installation and First Program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Install Pyrite (single command)
    $ curl --sSf https://raw.githubusercontent.com/WulfHouse/Quarry/main/scripts/setup/install.sh | sh
    
    # Write first program (hello.pyrite)
    fn main():
        print("Hello, Pyrite!")
    
    # Run immediately (script mode, zero config)
    $ pyrite run hello.pyrite
    Hello, Pyrite!
    
    # Or use REPL for exploration
    $ pyrite repl
    >>> let x = 5 + 3
    8
    >>> let data = List[int]([1, 2, 3])
    [Heap] [Move] Stack: 24B, Heap: 12B

Week 1: Learning Ownership Interactively
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Start interactive learning
    $ quarry learn ownership
    
    Exercise: Fix the ownership error...
    [Work through 12 exercises with progressive hints]
    
    # Practice in REPL
    $ pyrite repl --explain
    >>> let data = List[int]([1, 2, 3])
    >>> process(data)
    >>> data.length()  # See instant ownership error with visualization

Week 2: First Real Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Create project
    $ quarry new my-cli-tool
    $ cd my-cli-tool
    
    # Write code, hit ownership error
    $ quarry build
    error[P0234]: cannot use moved value 'config'
    
    # Interactive fix
    $ quarry fix --interactive
    Select a fix:
      1. Pass a reference (recommended)
      2. Clone the value
      3. Restructure to return ownership
    Choice: 1
    
    ✓ Fixed! Run 'quarry build' to verify.

Week 3: Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Profile the code
    $ quarry cost
    Warning: List allocated in loop (1000 times)
    
    $ quarry perf
    Hot spot: parse_data (34% of runtime)
    
    $ quarry tune
    Suggestions:
      1. Pre-allocate list with_capacity(1000) → 15% speedup
    [Apply] ✓ Applied
    
    $ quarry perf --check
    ✓ 15.3% faster than baseline

Month 2: Production Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Add dependencies
    $ quarry add http-server json
    
    # Write server with observability
    import std::http
    import std::log
    
    fn main():
        log::info("server_starting", {"port": 8080})
        let server = HttpServer::new("0.0.0.0:8080", handler)
        server.run()
    
    # Security audit
    $ quarry audit
    ✓ No vulnerabilities
    
    # Build for production
    $ quarry build --release --lto --pgo=bench
    
    # Generate SBOM for compliance
    $ quarry sbom --format=spdx
    
    # Deploy!

Month 6: Embedded Project
~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Target embedded device
    $ quarry new --embedded stm32-firmware
    $ cd stm32-firmware
    
    # Build with no-alloc verification
    $ quarry build --target=thumbv7em-none-eabi --no-alloc
    
    # Check binary size
    $ quarry bloat
    Total: 47 KB (73% of 64 KB flash)
    
    # Optimize
    $ quarry build --optimize=size --strip-all
    Total: 32 KB (50% of flash) ✓
    
    # Flash to device
    $ quarry flash --target=stm32f4

Year 1: Contributing to Ecosystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Publish your library
    $ quarry publish my-awesome-lib
    
    # Track adoption on dashboard
    <!-- Aspirational: does not exist yet -->
    https://quarry.dev/packages/my-awesome-lib
    Downloads: 1,247 this month
    
    # See your impact on metrics
    <!-- Aspirational: does not exist yet -->
    https://quarry.dev/metrics
    Ecosystem: 15,247 packages (+1 yours!)

This Journey Demonstrates
~~~~~~~~~~~~~~~~~~~~~~~~~~

  • **Day 1 productivity:** Write and run code immediately (script mode + REPL)
  • **Week 1 learning:** Interactive tools teach ownership organically
  • **Week 2 building:** Auto-fix removes friction, quarry just works
  • **Week 3 optimizing:** Profiling + tuning make performance systematic
  • **Month 2 production:** All production features built-in (observability, 
    security, compliance)
  • **Month 6 embedded:** Same language, different constraints, still safe
  • **Year 1 ecosystem:** Contribute back, see impact, feel part of community

Every stage is supported by first-class tooling. No external dependencies, no 
complex configuration requirements, no need to piece together solutions from 
multiple sources. This approach focuses on removing every friction point from 
beginner to expert to contributor.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Next**: [Compiler Diagnostics and Error Messages](02-diagnostics.md)
