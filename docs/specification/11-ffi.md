---
title: "Foreign Function Interface (FFI) and Interoperability"
section: 11
order: 11
---

# Foreign Function Interface (FFI) and Interoperability

================================================================================
11. FOREIGN FUNCTION INTERFACE (FFI) AND INTEROPERABILITY
--------------------------------------------------------------------------------

11.1 C Foreign Function Interface
--------------------------------------------------------------------------------

Pyrite is engineered to integrate seamlessly with existing C/C++ codebases. The 
FFI (foreign function interface) allows calling external C functions directly and 
vice versa (exporting Pyrite functions to C), since one of the goals is easy 
adoption and reuse of legacy code. 

For example:

    extern fn printf(fmt: *const u8, ...) -> int  # declare an external C function

You could declare extern functions in Pyrite that are defined in C libraries. 
Pyrite will ensure the calling convention matches (likely it uses the platform C 
ABI by default for extern). Similarly, Pyrite could mark functions to be exported 
with C ABI so that C code can call into Pyrite compiled code. Because Pyrite has 
no heavyweight runtime, calling into Pyrite from C is just like calling into any 
compiled library - you just need to initialize any needed Pyrite runtime (which 
might be minimal to nonexistent).

The build tooling for Pyrite will likely include: 
  - A package manager (like Cargo for Rust or Zig's build system) to manage 
    dependencies and building libraries/executables. This simplifies sharing code 
    and using third-party libraries. 
  - Cross-compilation support out of the box: being a systems language, Pyrite 
    aims to target many architectures and OSes easily (like Zig's mantra of 
    cross-compiling is easy). The build system can supply needed runtime stubs, 
    etc., for different targets.

In terms of ecosystem: 
  - Testing and documentation: The language and tooling will encourage writing 
    tests (possibly with an inline testing framework like Rust's #[test] 
    functions) and documentation (doc comments """ that can be extracted into 
    docs). The goal is a developer-friendly experience where writing correct code 
    is streamlined. 
  - Package registry: likely there will be an official repository for Pyrite 
    packages to easily add dependencies (similar to PyPI for Python or crates.io 
    for Rust).

All these ecosystem features make Pyrite not just a bare language, but a 
practical tool for real projects. Part of being "most loved" is having a smooth 
development experience, not just the language syntax and features.

11.2 Build System Integration
--------------------------------------------------------------------------------

The build tooling for Pyrite (Quarry) includes:

  • Package manager to manage dependencies and build libraries/executables
  • Cross-compilation support out of the box: target many architectures and OSes 
    easily (like Zig's cross-compilation philosophy)
  • Testing framework with inline tests
  • Documentation generation from doc comments
  • Official package registry for sharing code

See section 8 (Tooling: Quarry Build System) for comprehensive details.

11.3 Future: Automatic Binding Generation
--------------------------------------------------------------------------------

While the initial release focuses on manual FFI declarations, future versions 
will include quarry bindgen to automatically generate Pyrite bindings from C 
header files:

    quarry bindgen /usr/include/sqlite3.h --output=src/sqlite.pyrite

This eliminates tedious manual translation of large C APIs, similar to Rust's 
bindgen tool.

11.4 Python Interoperability (Future Release)
--------------------------------------------------------------------------------

After establishing Pyrite in embedded and server domains (Phases 1-3), Python 
interoperability becomes a strategic adoption wedge for numerical computing and 
data science applications. This is intentionally delayed to avoid complexity in 
early phases.

Why Python Interop Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python's ecosystem (NumPy, SciPy, Pandas, PyTorch, TensorFlow) represents decades 
of mature libraries and millions of existing projects. For Pyrite to compete in 
numerical/scientific computing (Stable Release), seamless Python integration provides:

  • **Adoption wedge:** Incremental migration from Python performance bottlenecks
  • **Ecosystem leverage:** Access to existing Python libraries until Pyrite equivalents mature
  • **Data science appeal:** Pyrite becomes "Python's performance layer"
  • **Teaching path:** Python developers try Pyrite for hot loops, expand usage gradually

Why Not Beta Release
~~~~~~~~~~~~~~~~~~

Python interop is intentionally delayed because:

1. **Wrong audience initially:**
   Beta Release targets embedded developers and systems programmers
   Neither needs Python FFI (embedded has no Python, systems devs avoid it)

2. **Adds significant complexity:**
   • GIL integration (Global Interpreter Lock)
   • Reference counting interop with Pyrite ownership
   • Type bridging (Python dynamic types ↔ Pyrite static types)
   • Exception handling across boundary
   • Requires Python runtime present (conflicts with no-runtime philosophy)

3. **Conflicts with embedded-first strategy:**
   Embedded firmware can't depend on Python runtime
   @noalloc mode incompatible with Python's malloc-heavy runtime
   Target hardware (microcontrollers) can't run Python

4. **Mojo already owns this space:**
   Mojo's entire value proposition is "Python interop + performance"
   Competing there dilutes Pyrite's embedded/systems differentiation

Future Release Design Approach
~~~~~~~~~~~~~~~~~~~~~~~~~

When Python interop is added, it must maintain Pyrite's core principles:

**Explicit, not hidden:**
  • Python calls are clearly bounded
  • No hidden GIL acquisition or reference counting
  • Cost transparency: quarry cost shows Python calls as expensive

**Optional and isolated:**
  • Requires explicit import of std::python module
  • Python runtime is optional dependency (not required for core Pyrite)
  • Code without Python imports compiles with zero Python dependencies

**Type-safe boundaries:**
  • Explicit type conversion at boundaries
  • Pyrite ownership rules enforced (no implicit borrowing of Python objects)
  • Python exceptions converted to Result types

Example API sketch (Future Release):

    import std::python as py
    
    fn process_with_numpy(data: &[f64]) -> Result[Vec[f64], Error]:
        # Explicit Python GIL acquisition
        with gil = py::GIL::acquire():
            # Import Python module
            let np = try gil.import("numpy")
            
            # Convert Pyrite slice to NumPy array (zero-copy where possible)
            let py_array = try gil.from_slice(data)
            
            # Call Python function
            let result = try np.call("fft", [py_array])
            
            # Convert back to Pyrite (allocates)
            let pyrite_vec = try gil.to_vec[f64](result)
            
            return Ok(pyrite_vec)
        # GIL released automatically via defer

Cost transparency:

    warning[P1350]: Python GIL acquisition
      ----> src/compute.py:45:9
       |
    45 |     with gil = py::GIL::acquire():
       |              ^^^^^^^^^^^^^^^^^^^^ expensive operation
       |
       = note: GIL acquisition may block if Python is active
       = note: Python calls within GIL are 10-100x slower than native code
       = performance: Consider:
         1. Minimize GIL-protected regions
         2. Pre-convert data to avoid repeated conversions
         3. Use Pyrite-native libraries where available

Python Extension Module Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the reverse direction (calling Pyrite from Python), provide tooling:

    quarry pyext                           # Generate Python extension module
    quarry pyext --name=fast_compute       # Custom module name

Generated extension exposes Pyrite functions to Python:

    # Pyrite code (src/compute.pyrite)
    @pyexport
    fn fast_matrix_multiply(a: &[f64], b: &[f64], rows: usize, cols: usize) -> Vec[f64]:
        # Pyrite implementation (fast, safe)
        ...
    
    # Generated Python module (build/fast_compute.so)
    # Python usage:
    import fast_compute
    
    result = fast_compute.fast_matrix_multiply(a, b, rows, cols)
    # Calls compiled Pyrite code (100x faster than Python)

Benefits for Python users:
  • Drop-in replacement for performance bottlenecks
  • Memory-safe (no segfaults from extension bugs)
  • Easy distribution (wheel packages)
  • Gradual migration path (replace hot functions one at a time)

Example migration path:

    # Week 1: Profile Python code, find bottleneck
    # Week 2: Rewrite bottleneck in Pyrite
    # Week 3: Generate extension module (quarry pyext)
    # Week 4: Import and use from Python (import my_fast_code)
    # Week 5-N: Migrate more hot paths incrementally

Type Bridging
~~~~~~~~~~~~~

Explicit type conversions at the boundary:

    # Pyrite → Python
    gil.from_slice(&data)        # &[f64] → numpy.ndarray (zero-copy)
    gil.from_vec(vec)            # Vec[T] → list (copies)
    gil.from_str(&text)          # &str → str (copies)
    
    # Python → Pyrite
    gil.to_vec[f64](py_obj)      # list → Vec[f64] (allocates, validates)
    gil.to_slice[f64](py_obj)    # ndarray → &[f64] (borrows Python memory)
    gil.to_string(py_obj)        # str → String (allocates)

All conversions are explicit and show their cost in quarry cost output.

Future Release Rationale
~~~~~~~~~~~~~~~~~~

By waiting until a future release, Python interop benefits from:
  • Mature ownership model (no surprises at boundaries)
  • Proven cost transparency (Python calls clearly expensive)
  • Strong stdlib (less need for Python deps)
  • Established identity (not "Python with performance," but "systems language that CAN interop")

Target use cases:
  • NumPy/SciPy bottleneck replacement
  • Data science pipeline acceleration
  • ML model inference (Pyrite replaces Python hot paths)
  • Scientific computing (leverage both ecosystems)

Not for:
  • Embedded (no Python runtime available)
  • Systems programming (Python runtime unwanted)
  • Real-time systems (GIL breaks determinism)

Timeline: Future Release (after numerical computing, tensor types, SIMD are stable)
Priority: Medium (valuable for market expansion, not critical for core identity)

This positions Python interop as: "Pyrite is systems language first, but can 
leverage Python ecosystem when needed" rather than "Pyrite is Python replacement."

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Pyrite Playground and Learning Experience](10-playground.md)

**Next**: [Marketing and Positioning](12-marketing.md)
