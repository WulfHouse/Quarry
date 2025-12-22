---
title: "Pyrite Playground and Learning Experience"
section: 10
order: 10
---

# Pyrite Playground and Learning Experience

================================================================================

The Pyrite Playground is a first-class component of the ecosystem, designed to 
lower the barrier to entry and enable frictionless sharing of code examples.

10.1 Browser-Based Playground
--------------------------------------------------------------------------------

Features
~~~~~~~~

The Playground (play.pyrite-lang.org) provides:

  • Zero-installation experimentation: Write and run Pyrite in the browser
  • Real compiler: Uses WebAssembly-compiled pyritec for authentic experience
  • Instant feedback: Compiler errors displayed inline as you type
  • Example library: Curated examples for common patterns and language features
  • Shareable links: Every playground session has a unique URL
  • Embedded mode: Playground can be embedded in documentation and tutorials
  • Output capture: Console output, compiler warnings, execution time

Example Workflow
~~~~~~~~~~~~~~~~

1. Visit play.pyrite-lang.org
2. Write code:

   fn main():
       let numbers = List[int]([1, 2, 3, 4, 5])
       let sum = numbers.iter().fold(0, fn(acc, x): acc + x)
       print("Sum:", sum)

3. Click "Run" → See output immediately
4. Click "Share" → Get link: play.pyrite-lang.org/abc123
5. Paste link in forum post, documentation, or chat

10.2 Integration with Documentation
--------------------------------------------------------------------------------

Every code example in official documentation is a live Playground link:

    ```pyrite
    fn factorial(n: int) -> int:
        if n <= 1:
            return 1
        return n * factorial(n - 1)
    
    fn main():
        print(factorial(5))  # Output: 120
    ```
    
    [▶ Run this example] → Opens in Playground

Readers can modify examples and see results instantly, dramatically improving 
the learning experience.

10.3 Compiler Error Teaching
--------------------------------------------------------------------------------

The Playground is optimized for teaching through errors:

  • Error messages use the full diagnostic format (section 2)
  • Hover over error codes for inline explanations
  • "Explain" button opens detailed error documentation
  • "Suggest fix" applies automatic corrections when available
  • Multi-error display with prioritization (show blocking errors first)

Example error in Playground:

    let data = List[int]([1, 2, 3])
    process(data)
    print(data[0])  # ← Error highlighted here

    [!] error[P0234]: cannot use moved value 'data'
    
    'data' was moved on line 2 when passed to 'process'
    
    [Explain P0234] [Suggest fix] [Share this error]

10.4 Why Playground Matters for Adoption
--------------------------------------------------------------------------------

Learning Curve Reduction
~~~~~~~~~~~~~~~~~~~~~~~~

Playground eliminates friction for newcomers:

  • No installation required (toolchain setup often blocks beginners)
  • Instant gratification (see results in seconds)
  • Low stakes (experiment without breaking local environment)
  • Social proof (easily share working examples)

Advocacy Amplification
~~~~~~~~~~~~~~~~~~~~~~

When developers discover something cool in Pyrite, they share it:

  • Twitter/Reddit post with Playground link → Readers can try immediately
  • Stack Overflow answer with Playground example → Questioner runs it in-browser
  • Tutorial with embedded Playground → Readers learn by doing

This creates a flywheel: better playground → more sharing → more discovery → 
more adoption.

Community Support
~~~~~~~~~~~~~~~~~

Playground links are invaluable for support forums:

  • Bug reports include reproducible case (playground link)
  • Help requests show actual code context
  • Teaching examples are interactive, not passive screenshots

Rust Playground (play.rust-lang.org) is consistently cited as one of Rust's best 
features. Pyrite Playground delivers similar experience from day one.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Standard Library and Ecosystem](09-standard-library.md)

**Next**: [Foreign Function Interface (FFI) and Interoperability](11-ffi.md)
