---
title: "Types and Type System"
section: 4
order: 4
---

# Types and Type System

================================================================================

Pyrite has a static, strong type system that enforces type safety at compile 
time (preventing type errors and many classes of runtime errors). However, the 
type system is designed to be as unobtrusive as possible for the programmer. 
Type inference is used extensively so that in many cases the programmer doesn't 
need to explicitly write types - the compiler can deduce them. 

This section describes Pyrite's types, including primitives, composite types, and 
how mutability and ownership affect types.

4.1 Primitive Types
--------------------------------------------------------------------------------

Integers
~~~~~~~~

Pyrite supports a range of integer types for low-level control, similar to C and 
Rust. This includes fixed-width signed and unsigned integers of various bit 
widths (e.g. i8, i16, i32, i64 for signed 8/16/32/64-bit, and u8, u16, etc. for 
unsigned). There is also a native-sized integer type int (and uint or perhaps 
usize) whose bit width matches the platform's word size (32-bit on a 32-bit 
target, 64-bit on a 64-bit target) - this is analogous to Zig's usize or Rust's 
isize/usize. 

The default integer type for inference is a comfortable size (likely 32-bit or 
64-bit depending on platform) when the context doesn't constrain it. Pyrite 
avoids surprising implicit casts: it will not automatically narrow an integer 
(e.g. from 64-bit to 32-bit) and will only widen in cases that are well-defined. 
Mixed-type integer arithmetic either selects a larger type or yields a compile 
error requiring an explicit cast. 

Integer operations that overflow will, by default, throw an error in debug mode, 
but in optimized builds they wrap (two's complement wraparound) for performance, 
unless explicit checked arithmetic is requested. This strategy ensures safety 
during development without penalizing release performance, following Rust and 
Zig's lead on integer overflow handling.

Floating-Point
~~~~~~~~~~~~~~

Pyrite provides standard IEEE-754 floating point types: f32 (32-bit single 
precision) and f64 (64-bit double precision). By default, a float literal like 
3.14 is inferred as f64 for precision, but you can suffix or contextually infer 
f32 if needed. Floating-point operations follow IEEE semantics (with support for 
special values like NaN and infinity). 

As with ints, no implicit conversion occurs between floats and integers - a 
conversion must be done with an explicit cast function or operator to avoid 
unintended truncation or rounding. If necessary, a generic float keyword may be 
an alias for the default float type (like Python's float meaning 64-bit).

Boolean
~~~~~~~

The bool type represents a boolean value (true or false). Booleans in Pyrite are 
not implicitly convertible to or from numeric types. This means conditional 
statements require a bool expression explicitly. (This design, also used in 
languages like Rust and Pascal, prevents common errors like using = instead of == 
in C, and makes the code's intent clearer.) 

Boolean operations use the English words and, or, not as mentioned, and they 
short-circuit. There is no separate boolean and bitwise type - & and | are 
available as bitwise operators for integers, while and/or are logical for bools.

Character and String
~~~~~~~~~~~~~~~~~~~~

Pyrite's char type is a Unicode code point (32-bit). It can represent any 
Unicode character by code point value. Strings in Pyrite are of type String 
(immutable sequence of characters). A String can be any length and is stored in a 
contiguous memory buffer (likely heap-allocated for nontrivial lengths). Strings 
support typical operations like concatenation, slicing, and iteration. 

However, strings are immutable; you cannot change a character in an existing 
String. To build or modify text, you would use a StringBuilder or work with a 
mutable char array. String literals (quoted text in the source) produce String 
instances at compile time, which may be interned or stored in read-only memory 
  (as an optimization - but that's an implementation detail).

Pyrite avoids hidden allocations, so operations like concatenating two strings at 
runtime will allocate a new string for the result (and this is documented 
behavior). Programmers are encouraged to handle large text concatenation through 
explicit means (e.g. using a builder or formatting library) rather than relying 
on + repeatedly. In some cases, constant string concatenation can be evaluated at 
compile time (if the operands are known at compile time).

Beginner-Friendly Type Aliases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To ease the learning curve for absolute beginners, Pyrite's standard library 
provides optional type aliases for common borrowed views:

    type Text = &str        # Borrowed string view (read-only text)
    type Bytes = &[u8]      # Borrowed byte slice (raw data)

These aliases make function signatures more readable for newcomers:

    # More beginner-friendly
    fn parse_config(content: Text) -> Result[Config, Error]
    
    # Equivalent to (both work)
    fn parse_config(content: &str) -> Result[Config, Error]

The underlying types (&str, &[u8]) remain the fundamental types and work 
everywhere. The Text/Bytes aliases are purely for readability in documentation 
and teaching materials. Experienced developers can use either form.

Note: These are type aliases, not new types - no runtime cost, no type system 
complexity. They exist solely to make "borrowed view of text" more intuitive 
for Python/JavaScript developers transitioning to systems programming.

Generic Reference Aliases
~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond Text and Bytes, the standard library provides generic aliases for common 
reference patterns:

    type Ref[T] = &T        # Immutable reference to T
    type Mut[T] = &mut T    # Mutable reference to T
    type View[T] = &[T]     # Slice view of T elements

These are available in the prelude but entirely optional. They allow tutorial 
code to use familiar terms before introducing the underlying syntax:

    # Beginner-facing tutorial might use:
    fn sum(numbers: View[int]) -> int:
        var total = 0
        for n in numbers:
            total += n
        return total
    
    # Experienced developer writes:
    fn sum(numbers: &[int]) -> int:
        var total = 0
        for n in numbers:
            total += n
        return total
    
    # Both are identical (Ref[T] is literally &T)

Teaching Path
~~~~~~~~~~~~~

The suggested learning progression for references:

1. **Week 1:** Use `Ref[T]`, `Mut[T]`, `View[T]` in tutorials
   - "Pass a Ref[Config] to read the config"
   - "Pass a Mut[Buffer] to modify the buffer"
   - "Pass a View[int] to iterate over numbers"

2. **Week 2-3:** Reveal the underlying syntax
   - "Ref[T] is actually &T in Pyrite syntax"
   - "You can use either form"
   - Show both in examples side-by-side

3. **Week 4+:** Use underlying syntax primarily
   - Documentation uses &T, &mut T, &[T]
   - Generic aliases become optional shorthand
   - Beginners have learned the real syntax organically

**Type Alias Strategy:**

This approach mirrors how humans learn natural languages:

  • Start with familiar vocabulary ("pass a reference")
  • Reveal native idioms gradually ("actually it's &T")
  • Achieve fluency through practice

The key insight: type aliases cost nothing at runtime and don't fragment the 
ecosystem. They're purely pedagogical sugar. Experienced developers never need 
to know they exist, but they smooth the first week for Python/JavaScript 
developers.

**Important:** Type aliases are for teaching, not production. Production code 
should use the real syntax (`&T`, `&mut T`, `&[T]`) for clarity and consistency. 
The standard library uses real syntax exclusively; community tutorials can choose 
their approach.

Alternatives considered and rejected:
  ✗ Teaching &T immediately: Too much syntax shock
  ✗ Hiding &T permanently: Creates two communities
  ✓ Gradual revelation: Best of both worlds

These aliases are opt-in for documentation authors. Core Pyrite docs use the 
real syntax; community tutorials can choose their approach.

Unit (Void)
~~~~~~~~~~~

For functions that do not return a meaningful value (procedures), Pyrite has a 
unit type, analogous to void in C or NoneType in Python. The unit type is 
primarily spelled as `()` (empty tuple), which matches Rust's convention and is 
consistent with tuple syntax. The unit type has exactly one possible value (no 
data); we can think of it like "nothing". 

A function with no return type specified is assumed to return `()`. The unit 
value can be ignored (not assigned to anything). This is mainly for type 
completeness - so that every function has some return type even if it's not useful.

For C familiarity, `void` is available as a type alias: `type void = ()`. However, 
the primary syntax is `()` to maintain consistency with tuple types.

Examples:
    fn no_return() -> ():  # Primary syntax
        pass
    
    fn print_hello() -> ():  # Explicit unit return
        print("Hello")
    
    # void available as alias for C familiarity
    type void = ()
    fn no_return() -> void:  # Also works, but () is preferred
        pass 

In Pyrite, the None literal is not of type void; instead None is typically a 
value of type Option[T] (see below). Unit/void is used for functions that just 
have side effects and don't produce a value.

**Note**: The unit type is primarily spelled as `()` (empty tuple), which matches 
Rust's convention and is consistent with tuple syntax. For C familiarity, `void` is 
available as a type alias: `type void = ()`. Functions that don't return a value 
should use `() -> ()` as the primary syntax.

4.2 Composite Types
--------------------------------------------------------------------------------

Arrays
~~~~~~

Pyrite supports two kinds of arrays with explicit syntax to differentiate them:

• Fixed-size arrays - These are like C arrays, allocated on the stack (or inline 
  in structs) and with a size known at compile time. The syntax is [T; N], where 
  T is the element type and N is the compile-time size constant (following Rust's 
  syntax). For example, [int; 100] is an array of 100 integers, and [u8; 1024] 
  is a 1KB byte buffer. The semicolon visually distinguishes arrays from slices 
  (see below) and signals "fixed size" to readers. Fixed arrays have value 
  semantics: assigning or passing them will (by default) copy the entire array, 
  unless the type is non-copyable. They are useful for embedded programming or 
  performance-critical code where you want a true stack allocation.
  
  Examples:
      # Fixed-size array with type annotation
      let buffer: [u8; 256] = [0; 256]  # 256-byte buffer on stack, initialized to zeros
      let matrix: [[f32; 4]; 4]         # 4×4 matrix (16 floats)
      
      # Array literal: size inferred from elements
      let arr: [int; 5] = [1, 2, 3, 4, 5]  # Type annotation provides size
      let arr = [1, 2, 3, 4, 5]            # Size inferred from elements (if unambiguous)
      
      # Repeat syntax: [value; count] creates array of repeated value
      let zeros: [int; 100] = [0; 100]     # 100 zeros
      let zeros = [0; 100]                  # Type inferred as [int; 100]
      
  **Array Literal Syntax Rules:**
  - `[elem1, elem2, ...]` = array literal with explicit elements
  - `[value; count]` = repeat syntax (creates array with `count` copies of `value`)
  - Type annotation `[T; N]` provides size when needed
  - Size can be inferred from element count when unambiguous

• Dynamic arrays (Vectors) - These are resizable arrays that manage a block of 
  memory on the heap. Pyrite's standard library provides a `Vector[T]` type to 
  represent a dynamic array. `Vector[T]` can grow or shrink, and internally it 
  allocates memory (using an allocator) to hold its elements. The distinction 
  between these two is explicit: a beginner will learn that `Vector[int]` (for 
  example) is a resizable array that uses the heap, whereas `[int; N]` (an array 
  type of length N) is a fixed-size array on the stack. This makes the memory 
  behavior intuitive at a glance.
  
  For Python familiarity, `List[T]` is available as a type alias: `type List[T] = Vector[T]`. 
  However, `Vector[T]` is the primary name as it unambiguously means "growable array" 
  (unlike "List" which could mean linked list). 

• Slices: Pyrite supports slices as borrowed views into arrays or lists. The 
  syntax is &[T] for an immutable slice and &mut [T] for a mutable slice. A slice 
  is essentially a fat pointer (pointer to first element + length). For instance, 
  a function can take a &[T] parameter to accept either a fixed array, a List, or 
  a portion of either. Slices allow safe access to array segments without copying, 
  and come with bounds-checking (with potential to opt-out in unsafe code).
  
  Examples:
      fn sum(numbers: &[int]) -> int    # Accepts any contiguous integers
      
      let arr: [int; 5] = [1, 2, 3, 4, 5]
      let slice = &arr[1..4]            # Slice of elements [2, 3, 4]
      
      let vec = Vector[int]([10, 20, 30])
      let vec_slice = &vec[..]          # Slice of entire vector
  
  The type hierarchy is clear and teachable:
    • [T; N]     - Fixed-size array (stack, compile-time size)
    • &[T]       - Borrowed slice (view into array/vector)
    • Vector[T]  - Growable vector (heap, runtime size)
    • List[T]    - Alias for Vector[T] (for Python familiarity)

Structs (Records)
~~~~~~~~~~~~~~~~~

A struct in Pyrite is a composite type that groups multiple named fields 
(possibly of different types) into one record, similar to a struct in C or a 
class with only data in many OOP languages. By default, Pyrite structs have value 
semantics (a struct value holds its own copy of fields, and copying the struct 
copies all its data). Structs are defined with the struct keyword. 

For example: 

    struct Point:
        x: int
        y: int

This defines a struct Point with two integer fields. You can create a Point with 
a literal syntax like Point { x: 3, y: 4 }. Structs can be nested (a struct can 
contain other structs or arrays, etc.). They do not have implicit constructors or 
destructors - any initialization beyond simple field assignment would be done via 
functions (or static methods, see advanced features). By default, all struct 
fields are public (exported) within the module unless a visibility modifier is 
introduced (the spec may introduce private or similar for encapsulation at module 
boundaries). 

Pyrite does not automatically generate "methods" or behaviors for structs; it 
keeps them simple. However, traits and implementation blocks (discussed later in 
advanced features) can be used to add methods or operator overloads in a 
controlled manner. 

Memory layout: The layout of struct fields in memory is deterministic (likely 
same as C layout for compatibility, with perhaps some padding rules for 
alignment). Pyrite aims to support repr(C) or similar annotations to guarantee 
binary layouts for FFI when needed.

Enumerations (Enums)
~~~~~~~~~~~~~~~~~~~~

Pyrite supports enumerated types and algebraic data types via the enum keyword. 
An enum in Pyrite can be a simple enumeration of named constants or a tagged 
union of variants with data (similar to Rust's enums or variants in functional 
languages). 

For example:

    enum Result[T, E]:
        Ok(value: T)
        Err(error: E)

This enum Result has two variants: Ok holding a value of type T, and Err holding 
an error of type E. Enums in Pyrite are tagged unions under the hood: they 
consist of a discriminator (tag) and a payload for the active variant. The 
compiler ensures that only the active variant's data is accessible at any time, 
and that all possible variants are handled in pattern matching (exhaustiveness 
checking). 

Enums allow naturally expressing optional values, error handling, and other 
variant-based logic safely. A simpler enum with no data for variants (like enum 
Color { Red, Green, Blue }) is also allowed, similar to a C/C++ enum but 
type-safe (it doesn't silently convert to int, though you can map to an int if 
needed). Enum variant names are namespaced under the enum type. You construct 
variants as Color.Red, Result.Ok(42), etc. and use pattern matching to extract 
values (see Control Flow for pattern matching).

**Generic Syntax:**

Pyrite uses square brackets `[T]` for generic type parameters, following a 
consistent pattern across all generic constructs:

    # Multiple type parameters: comma-separated
    enum Result[T, E]:
        Ok(value: T)
        Err(error: E)
    
    # Type constraints (when added - syntax subject to final design)
    # Example syntax (to be finalized):
    fn process[T: Clone + Debug](item: T) -> T:
        # T must implement Clone and Debug traits
        return item.clone()
    
    # Lifetime parameters (when needed, Rust-style)
    # Example syntax (to be finalized):
    fn longest['a](x: &'a str, y: &'a str) -> &'a str:
        # Lifetime 'a ensures references live long enough
        if x.len() > y.len():
            return x
        return y

All generic constructs (enums, structs, functions, traits) use the same `[T]` 
syntax for consistency and learnability.

Using enums eliminates many error-prone patterns (like using integer codes or 
sentinel values). For instance, Pyrite encourages use of an `Option[T]` 
(which is an enum with variants `Some(T)` and `None`) for values that may or 
may not be present, rather than using null pointers. This way, the compiler 
forces you to handle the "none" case explicitly.

Optionals
~~~~~~~~~

Defined as an enum under the hood, `Option[T]` is the type for "maybe a T". 
You can declare `var x: Option[int] = None` to represent an integer that might 
not have a value. To use it, you must check if it's `None` or `Some(val)` - 
otherwise the compiler will not let you treat it as a concrete `int`. This 
prevents null usage errors.

For Python familiarity, `Optional[T]` is available as a type alias: 
`type Optional[T] = Option[T]`. However, `Option[T]` is the primary name as it 
aligns with Rust's `Option<T>` and is more concise.

Examples:
    var x: Option[int] = None
    var y: Option[str] = Some("hello")
    
    # Optional[T] available as alias
    var z: Optional[int] = None  # Equivalent to Option[int]
    
    # Pattern matching on Option
    match x:
        Some(val):
            print("Value:", val)
        None:
            print("No value")

Unions
~~~~~~

Pyrite also allows a form of union type (an untagged union, similar to C's union) 
for low-level programming where you need to interpret the same memory in 
different ways. However, accessing a union's fields is an unsafe operation unless 
you manually track which field is active, because the compiler cannot enforce 
correctness (an untagged union can lead to type punning and unsafe aliasing if 
misused). 

For example, you might define union IntOrFloat { i: int, f: f32 } to reuse memory 
for an int or float, but it's on the programmer to remember which one is stored. 
Reading from a union field that wasn't most recently written is undefined behavior 
in safe terms. Thus, union usage in Pyrite would require an unsafe block or 
function. The presence of union types ensures that any trick possible in C (for 
bit-level manipulation, etc.) is possible in Pyrite when absolutely needed, but 
safe code would prefer enums (tagged unions) for variant data.

4.3 References and Pointers
--------------------------------------------------------------------------------

Because Pyrite is a systems programming language, it provides pointer types - but 
in a way that separates safe references from raw, unsafe pointers.

References (Borrowed Pointers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A reference is a pointer type that is managed by the compiler's borrow checker 
for safety. Syntax: &T denotes an immutable reference to a value of type T, and 
&mut T denotes a mutable reference. You can think of &T similar to a pointer to T 
that you promise not to modify (and through which you cannot mutate the value), 
while &mut T is a pointer that gives you exclusive mutable access. 

References must obey the borrowing rules (see Memory Management section) - 
essentially, you can have multiple &T to the same value (read-only aliasing is 
OK), but only one &mut T at a time to a given value (exclusive write access). 

References are always non-null (you cannot have a null &T in safe code; the 
compiler ensures a reference is valid). They also must not outlive the data they 
point to - the compiler's lifetime analysis ensures that a reference doesn't 
persist beyond the scope of the value it refers to, preventing dangling pointers. 

In summary, &T and &mut T provide the convenience of pointers but with 
compile-time guarantees: if your code compiles using only references (and no 
unsafe conversions), you won't have null-dereferences or use-after-free issues. 
References are the primary way to pass data around without copying in Pyrite's 
safe code.

Optional Argument Convention Aliases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For educators and teaching materials, Pyrite provides optional argument convention 
keywords that desugar to standard reference syntax. These aliases make intent 
explicit for beginners learning ownership concepts:

    # Standard Pyrite syntax (always works)
    fn process(data: &Config) -> Result[(), Error]:
        # Immutable borrow
    
    fn update(data: &mut Config):
        # Mutable borrow
    
    fn consume(data: Config):
        # Takes ownership (moves)

    # Optional teaching aliases (desugar to above)
    fn process(borrow data: Config) -> Result[(), Error]:
        # Desugars to: data: &Config
    
    fn update(inout data: Config):
        # Desugars to: data: &mut Config
    
    fn consume(take data: Config):
        # Explicit: data moved (semantically identical, but self-documenting)

The keywords:
  • `borrow` → desugars to `&T` (immutable reference)
  • `inout` → desugars to `&mut T` (mutable reference)  
  • `take` → semantic marker for ownership transfer (no desugaring, just documentation)

These are **pure syntax sugar** with zero runtime cost and no type system changes.

Design rationale:
  • Zero cost: Desugars during parsing, identical to &T
  • Optional: Never required, &T works everywhere
  • Teaching-focused: Makes intent crystal clear for newcomers
  • Self-limiting: Experienced developers naturally transition to &T

Example teaching progression:

    # Week 1 (Tutorial code with aliases)
    fn calculate_total(borrow items: Vector[Item]) -> f64:
        var sum = 0.0
        for item in items:
            sum += item.price
        return sum
    
    # Week 2 (Show equivalence)
    fn calculate_total(borrow items: Vector[Item]) -> f64:
        # Note: 'borrow' is sugar for &Vector[Item]
        # Both forms work identically
    
    # Week 3+ (Transition to standard syntax)
    fn calculate_total(items: &Vector[Item]) -> f64:
        # Standard Pyrite syntax
        # More compact, same meaning

When to use:
  • Teaching materials targeting absolute beginners
  • Introductory tutorials and workshops
  • Educational institutions with Python-first students
  • Code review where intent needs extra clarity

When NOT to use:
  • Production code (stdlib uses &T exclusively)
  • Advanced tutorials (learners should see real syntax)
  • Library APIs (ecosystem standardizes on &T)
  • After first 2-3 weeks of learning

Compiler support:
  • Parser recognizes keywords and desugars immediately
  • Error messages always show underlying &T syntax
  • quarry fmt can normalize to standard syntax (configurable)
  • No separate type checking (aliases resolved before analysis)

Configuration:

    # Quarry.toml - Teaching mode
    [learning]
    allow-argument-aliases = true
    
    # Quarry.toml - Production mode
    [learning]
    allow-argument-aliases = false         # Reject aliases, standardize on &T

Linter integration:

    # Suggest transitioning to standard syntax
    quarry lint --suggest-standard-syntax
    
    warning: Consider using standard syntax '&Config' instead of 'borrow Config'
      ----> tutorial.py:15:23
       |
    15 | fn process(borrow data: Config):
       |            ^^^^^^^^^^^^ teaching alias
       |
       = help: Standard syntax is more compact:
               fn process(data: &Config):
       = note: Teaching aliases are optional sugar for beginners
       = note: Use 'quarry fmt --normalize-syntax' to convert automatically

Why this approach works:
  • **Gentle onboarding:** borrow/inout/take read like English
  • **Zero fragmentation:** All code is valid Pyrite, just different syntax
  • **Natural graduation:** Learners see &T in errors, transition organically
  • **No ecosystem split:** Production code uses &T, tutorials can choose

This mirrors Pyrite's existing type alias strategy (Text = &str, Ref[T] = &T):
  • Provide familiar vocabulary for beginners
  • Reveal underlying syntax gradually
  • Enable fluency through practice
  • Keep ecosystem unified (aliases are optional)

Inspired by Mojo's argument conventions but implemented as **opt-in syntax sugar** 
rather than required syntax, maintaining Pyrite's "one obvious way" philosophy 
while accommodating teaching scenarios.

Implementation: Beta Release (low complexity, high teaching value)
Adoption: Optional (individual projects/educators decide)
Ecosystem impact: Zero (stdlib and community standardize on &T)

Raw Pointers
~~~~~~~~~~~~

For interoperability with C and for the cases where you truly need pointer 
arithmetic or want to opt out of the borrow rules, Pyrite has raw pointer types. 
A raw pointer is written as *T for a constant pointer or *mut T for a mutable 
pointer (similar to C's T* or Rust's *const T /*mut T). 

Raw pointers do not carry lifetime or nullability guarantees - you can cast an 
address to a *T, it might be null or dangling, and you are responsible for using 
it correctly. Raw pointers are unsafe to dereference; the compiler will only 
allow you to read or write through a *T inside an unsafe context (see Memory 
Management). 

Raw pointers support pointer arithmetic (e.g. you can do ptr + 1 to point to the 
next element if it's an array), whereas references do not allow arithmetic. Raw 
pointers are mainly used for low-level code, FFI calls (passing pointers to or 
from C), or implementing data structures where you need more control than the 
safe abstractions allow. In safe Pyrite code, you will rarely use raw pointers 
directly - they'll be encapsulated in libraries.

Pointer Conversions
~~~~~~~~~~~~~~~~~~~

You can obtain a raw pointer from a reference (for example, by casting &T to *T 
or using some standard library function) which essentially tells the compiler "I 
want to manage this pointer's rules manually." Going the other way (raw to 
reference) is unsafe because the compiler must assume you know that pointer is 
valid. Pyrite's design encourages you to use references whenever possible, and 
only use raw pointers in isolated low-level parts of your code, clearly marked as 
unsafe.

References and raw pointers give Pyrite the same expressive power as C for memory 
access, but by distinguishing the safe vs unsafe variants, Pyrite ensures that 
most of your code can be checked for memory errors at compile time. Only in the 
rare parts that truly need unchecked behavior do you have to drop down to raw 
pointers.

4.4 Mutability and Assignment
--------------------------------------------------------------------------------

Pyrite distinguishes between immutable and mutable variables at the language 
syntax level, taking inspiration from Rust's approach of making immutability the 
default. By default, a variable declared with let is immutable - once a value is 
bound to that name, it cannot be changed. If you need a variable's value to 
change (mutate), you use the var keyword to declare it as mutable. This design 
encourages using immutable values wherever possible, which can prevent a class of 
bugs and makes reasoning about code easier (especially in concurrency).

Example:

    let radius = 10     # immutable binding
    var counter = 0     # mutable binding
    counter = counter + 1  # OK, counter is mutable
    # radius = 5        # ERROR, radius is immutable

Immutability by default aligns with the idea that most data does not need to 
change after creation, and it helps catch unintended changes. Of course, you can 
opt into mutability with a clear var annotation.

Constants
~~~~~~~~~

For values that are known at compile time and never change, Pyrite provides a 
`const` declaration. 

Constants in Pyrite are inlined at compile time - they do not occupy memory at 
runtime. You can use them in any context that a literal would be allowed. 
Constants must be initialized with a compile-time evaluable expression. They are 
implicitly immutable (you don't write `var` or `let` for constants, just `const`). 
This is analogous to `#define` in C or `const` in languages like C++ and Rust, 
and is useful for configuration values, array lengths, etc.

**Syntax:**
    # Compile-time constants with explicit types
    const PI: f64 = 3.14159
    const SIZE: int = 1024 * 4
    
    # Type inference (when unambiguous)
    const PI = 3.14159  # Inferred as f64
    const COUNT = 100   # Inferred as int
    
    # Must be compile-time evaluable
    const INVALID = random()  # ERROR: not compile-time evaluable
    
    # Can use in type contexts
    let arr: [int; SIZE] = [0; SIZE]  # SIZE is const, can be used in type
    
    # Compile-time expressions allowed
    const MAX_SIZE: int = 1024 * 4
    const ARRAY_SIZE: int = MAX_SIZE / 4

**Rules:**
- Constants must be initialized with compile-time evaluable expressions
- Type can be explicitly specified or inferred
- Constants can be used in type contexts (e.g., array sizes)
- Constants are inlined at compile time (no runtime memory)

Assignment Semantics (Move vs Copy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Pyrite, assignment and passing variables to functions will either copy or move 
the value depending on its type. Types like primitive integers, floats, and other 
simple types implement a trait (interface) that marks them as Copy types - 
meaning a bitwise copy of the value is cheap and valid. For those types, 
assigning a = b makes a copy of b into a (and both are still usable). 

However, for types that manage resources (like a dynamic array, or any type with 
an owned heap allocation), Pyrite will treat them as Move-only by default. This 
means an assignment a = b will move the value from b to a, leaving b invalid (and 
it cannot be used unless reinitialized). This move semantics ensures that there 
is only ever one owner of each piece of resource, preventing double-free errors 
at compile time. If a type is move-only, you can still explicitly clone it if 
needed (if the type provides a clone operation). But by default, expensive or 
sensitive resources aren't implicitly duplicated.

For example, if `Vector[int]` is a dynamic array type and you do `let a = 
Vector[int]([1,2,3]); let b = a;`, this would transfer ownership of the vector 
from `a` to `b` (after the line, `a` would be considered invalid or "moved"). 
If you try to use `a` again, the compiler will error, because using a moved 
value is not allowed (to prevent use-after-free). 

In contrast, if you had let x = 5; let y = x;, both x and y are fine because int 
is a Copy type (cheap to copy and doesn't represent a resource that needs 
freeing). The Pyrite compiler handles this automatically based on type traits - 
the beginner programmer doesn't need to deeply understand it initially, beyond 
noticing that some values can be reused after assignment and others cannot. The 
compiler's error messages (e.g. "value moved here and cannot be used again") will 
guide the programmer, effectively teaching them about ownership as they go.

Destruction and RAII
~~~~~~~~~~~~~~~~~~~~

When a variable goes out of scope (for example, at the end of a function or the 
end of a block in which it's defined), Pyrite will automatically destroy (clean 
up) that variable if it owns a resource. This is similar to RAII (Resource 
Acquisition Is Initialization) in C++ and is tied into the ownership model 
detailed in the next section. For instance, if you have a File object that 
acquires a file handle, when it goes out of scope Pyrite will ensure its 
destructor closes the file.

Simple types like ints or floats don't need special cleanup (and the compiler 
typically treats their destruction as a no-op). Complex types might free memory 
or other resources in their destructor. Importantly, Pyrite does not have a 
garbage collector - resources are deterministically freed at scope end, and 
memory is either stack-allocated or explicitly allocated/freed on the heap. 

If a type needs custom cleanup, it will implement a drop/destructor method as 
part of a trait (e.g. a trait similar to Disposable or Rust's Drop). But unlike 
C++, that destructor is not "hidden" - Pyrite does not implicitly generate code 
with side effects beyond freeing memory unless you've opted into it. This keeps 
control flow clear (no unexpected lengthy destructors running at scope exit 
unless you know the type does that).

In summary, Pyrite's type system offers the low-level control of C's types, the 
safety and expressiveness of Rust's ownership and algebraic types, and the 
convenience of Python's readability. Types are inferred where possible, and the 
rules about moves vs copies and lifetimes work mostly behind the scenes to 
prevent errors, with the programmer learning them gradually through clear 
compiler feedback.

4.5 Cost Transparency Attributes
--------------------------------------------------------------------------------

Pyrite provides compiler-enforced attributes to make performance guarantees 
explicit and verifiable. These attributes transform the language philosophy of 
"no hidden costs" from documentation into hard contracts.

@noalloc - No Heap Allocations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The @noalloc attribute guarantees a function (or block) performs zero heap 
allocations:

    @noalloc
    fn calculate_checksum(data: &[u8]) -> u32:
        var sum: u32 = 0
        for byte in data:
            sum = sum ^ byte
        return sum

If this function attempts any heap allocation (creating a List, allocating a 
String, calling a function that allocates), compilation fails:

    error[P0601]: heap allocation in @noalloc function
      ----> crypto.py:156:13
       |
    155 | @noalloc
    156 | fn calculate_checksum(data: &[u8]) -> u32:
    157 |     let buffer = List[u8].new()  # ERROR
       |                  ^^^^^^^^^^^^^^ heap allocation not allowed
       |
       = note: function is marked @noalloc
       = help: Use stack allocation or pass a pre-allocated buffer

Use cases:
  - Real-time systems (deterministic performance)
  - Embedded systems (limited heap or no allocator)
  - Cryptographic functions (constant-time requirements)
  - Kernel code (allocation restrictions)

@nocopy - No Implicit Copies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The @nocopy attribute prevents large value copies:

    @nocopy
    fn process_image(img: &ImageData) -> Result[(), Error]:
        # Compiler ensures no copies of large values
        # All data passed by reference or move

    error[P0602]: implicit copy in @nocopy function
      ----> image.py:89:18
       |
    88 | @nocopy
    89 | fn process_image(img: &ImageData) -> Result[(), Error]:
    90 |     let backup = *img  # ERROR: copies large struct
       |                  ^^^^ implicit copy of 5 MB struct
       |
       = help: Use a reference instead: let backup = img

@nosyscall - No System Calls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The @nosyscall attribute forbids operations that invoke system calls:

    @nosyscall
    fn pure_computation(x: int, y: int) -> int:
        return x * x + y * y  # OK
        # File I/O, network, threading → compile error

Useful for:
  - Security-critical code (system call auditing)
  - Performance-critical paths (no kernel transitions)
  - Sandboxed execution

@bounds_checked / @no_bounds_check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Explicit control over array bounds checking:

    @bounds_checked  # Always check, even in release mode
    fn safe_access(arr: &[int], idx: int) -> Option[int]:
        if idx < arr.len():
            return Some(arr[idx])
        return None

    @no_bounds_check  # Requires unsafe block
    unsafe fn unchecked_access(arr: &[int], idx: int) -> int:
        return arr[idx]  # Caller guarantees idx is valid

@cost_budget - Performance Contracts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For real-time and safety-critical systems, Pyrite allows specifying performance 
budgets as compile-time contracts:

    @cost_budget(cycles=100, allocs=0)
    fn parse_packet(data: &[u8]) -> Result[Packet, Error]:
        # Compiler enforces budget
        # Errors if exceeded
        var packet = Packet::default()  # Stack allocation OK
        packet.parse(data)?
        return Ok(packet)

Compilation error example:

    error[P0650]: cost budget exceeded
      ----> network.py:156:13
       |
    155 | @cost_budget(cycles=100, allocs=0)
    156 | fn parse_packet(data: &[u8]) -> Result[Packet, Error]:
    157 |     let buffer = Vector[u8].new()  # ERROR
        |                  ^^^^^^^^^^^^^^ heap allocation not allowed
        |
        = note: function specifies allocs=0 budget
        = note: List::new() allocates on heap
        = help: Use fixed-size array: [u8; N] or pass pre-allocated buffer

Budget parameters:
  • cycles=N: Maximum estimated instruction count
  • allocs=N: Maximum heap allocations allowed
  • stack=N: Maximum stack space (bytes)
  • syscalls=N: Maximum system calls allowed

Benefits:
  • **Guarantees for real-time systems:** Provable bounds
  • **Safety-critical certification:** Performance as correctness
  • **Executable documentation:** Budget is enforced, not hoped for
  • **Regression detection:** CI fails if budget exceeded

Integration with profiling:
  • quarry cost estimates actual cost vs budget
  • quarry perf measures runtime cost vs budget
  • quarry tune suggests how to meet budget

Use cases:
  • Real-time audio/video processing
  • Flight control software
  • Medical device firmware
  • High-frequency trading
  • Kernel interrupt handlers

Example: Constant-time cryptography

    @cost_budget(cycles=5000, allocs=0, branches=0)
    fn verify_signature(sig: &[u8; 64], msg: &[u8], key: &PublicKey) -> bool:
        # Compiler ensures constant-time execution
        # No data-dependent branches allowed
        # No heap allocation allowed
        ...

This transforms "performance requirements" from documentation into compiler-
verified contracts. Beta Release feature.

Call-Graph Blame Tracking
~~~~~~~~~~~~~~~~~~~~~~~~~~

Performance contracts compose across function boundaries with blame tracking. When 
a contract violation occurs, the compiler shows the complete call chain and 
identifies which callee caused the violation:

    @cost_budget(allocs=0)
    fn process_data(input: &[u8]) -> Result[Data, Error]:
        let parsed = parse_input(input)?
        return Ok(transform(parsed))

Compilation error with blame chain:

    error[P0650]: @cost_budget violation: heap allocation
      ----> src/processor.py:45:22
       |
    43 | @cost_budget(allocs=0)
    44 | fn process_data(input: &[u8]) -> Result[Data, Error]:
    45 |     let parsed = parse_input(input)?
       |                  ^^^^^^^^^^^^^^^^^^^ allocation occurs in this call
       |
       = note: Allocation chain:
         1. process_data() [marked @cost_budget(allocs=0)]
            → calls parse_input()
         2. parse_input() 
            → calls tokenize()
         3. tokenize() at line 234
            → allocates Vector[Token].new() [VIOLATES BUDGET]
       
       = help: To fix, choose one approach:
         1. Pass pre-allocated buffer to parse_input:
            fn parse_input(input: &[u8], buffer: &mut List[Token])
         
         2. Mark parse_input as @may_alloc (documents allocation):
            @may_alloc
            fn parse_input(input: &[u8]) -> Result[Tokens, Error]
         
         3. Refactor tokenize() to use fixed-size array:
            const MAX_TOKENS: int = 100
            var tokens: [Token; MAX_TOKENS]
       
       = explain: Run 'pyritec --explain P0650' for performance contracts guide

Cross-Module Blame:

    error[P0601]: @noalloc violation in safe_compute()
      ----> src/main.py:67:15
       |
    65 | @noalloc
    66 | fn safe_compute(x: f64) -> f64:
    67 |     return math::advanced_sqrt(x)  # Calls external function
       |            ^^^^^^^^^^^^^^^^^^^^^^ heap allocation occurs here
       |
       = note: Allocation chain across modules:
         1. safe_compute() [your code, marked @noalloc]
            → calls math::advanced_sqrt() [external crate 'advanced_math']
         2. advanced_math::advanced_sqrt() at advanced_math-1.2.3/src/lib.py:89
            → allocates Vec[f64] for iterative approximation [VIOLATES @noalloc]
       
       = help: The external function 'advanced_sqrt' is not marked @noalloc.
               Options:
         1. Use standard library math::sqrt() instead (marked @noalloc)
         2. File issue with 'advanced_math' crate to add @noalloc variant
         3. Remove @noalloc from safe_compute() and document allocation

Benefits:
  • **Root cause analysis:** Know exactly which function violated the contract
  • **Transitive enforcement:** Contracts propagate through call graph
  • **Actionable fixes:** Compiler suggests specific solutions at each level
  • **Cross-crate tracking:** Works across dependency boundaries
  • **Refactoring confidence:** Change internals, contract violations caught

Why This Matters:

Call-graph blame transforms performance contracts from "catch violations" to 
"understand why." Instead of "allocation occurred somewhere," you get "allocation 
occurred in tokenize() at line 234, called from parse_input(), called from your 
@cost_budget function." This makes contracts practical for large codebases and 
external dependencies.

Beta Release flagship feature.

Cost Transparency Warnings
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Even without explicit attributes, the compiler warns about potentially expensive 
operations (configurable via lint levels). Note the distinction between compiler 
attributes (`@attribute`) and linter attributes (`[attribute]`):

    # Compiler-enforced attributes: @ prefix
    @noalloc
    fn calculate() -> int:
        pass
    
    # Linter hints: [ ] brackets (Rust-style)
    #[allow(heap_alloc)]  # Suppress linter warning
    fn my_function():
        let v = Vector[int].new()  # warning: heap allocation (unless suppressed)
    
    # Warn on copies > 1KB
    #[warn(large_copy, threshold=1024)]
    fn another_function():
        let big = large_struct  # warning if > 1KB
    
    # Warn on dynamic dispatch
    #[warn(dynamic_dispatch)]
    fn uses_trait_object(obj: &dyn Trait):
        obj.method()  # warning: indirect call via vtable

**Attribute Syntax Distinction:**
- `@attribute` = compiler-enforced (affects compilation, e.g., `@noalloc`, `@cost_budget`)
- `[attribute]` = linter hint (affects warnings only, e.g., `#[allow(...)]`, `#[warn(...)]`)

Integration with Linter
~~~~~~~~~~~~~~~~~~~~~~~~

Cost transparency is also enforced through quarry lint levels:

    quarry lint --level=performance

Reports:
  • All heap allocations with size estimates
  • All implicit copies with byte counts
  • Dynamic dispatch call sites
  • Potential reallocation points (e.g., List growth)
  • Lock contention points in concurrent code

Output format:

    performance: heap allocation (estimated 1024 bytes)
      ----> src/parser.py:234:9
      |
    234 |     let tokens = Vector[Token].new()
      |
      = help: Consider pre-allocating with with_capacity(estimated_size)
      = impact: May allocate multiple times as list grows

    performance: large copy (4096 bytes)
      ----> src/renderer.py:567:14
      |
    567 |     process_buffer(buffer)  # buffer is 4KB struct
      |
      = help: Pass by reference: process_buffer(&buffer)

Summary
~~~~~~~

Cost transparency attributes make Pyrite's "no hidden costs" philosophy 
enforceable:

  • Beginners learn performance intuition through warnings
  • Experts gain hard guarantees for critical code
  • Auditors can verify performance requirements
  • Documentation becomes executable contracts

No other systems language provides this level of provable cost control while 
maintaining high-level ergonomics.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Syntax Overview](03-syntax.md)

**Next**: [Memory Management and Ownership](05-memory-model.md)
