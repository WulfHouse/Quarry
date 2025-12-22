---
title: "Advanced Features (Traits, Generics, and More)"
section: 7
order: 7
---

# Advanced Features (Traits, Generics, and More)

================================================================================

While Pyrite's core is procedural and data-oriented (like C), it offers 
higher-level abstraction mechanisms inspired by Rust's traits and Python's 
duck-typing, aiming to achieve flexibility without sacrificing performance. These 
features are optional - a beginner can ignore them initially - but they enable 
writing expressive and reusable code as one's proficiency grows.

7.0 Type Introspection: quarry explain-type
--------------------------------------------------------------------------------

To support Pyrite's "Intuitive Memory Model for Learners" (section 1.5), the 
tooling provides a first-class type introspection command that makes memory 
layouts and properties visible:

Command Usage
~~~~~~~~~~~~~

    quarry explain-type TypeName
    quarry explain-type TypeName --verbose

This command displays standardized "type badges" and memory characteristics in 
plain language, making low-level concepts tangible for beginners.

Example Output: Primitive Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    $ quarry explain-type int
    
    Type: int
    ════════════════════════════════════════
    
    Properties: [Stack] [Copy] [ThreadSafe]
    
    Memory Layout:
      • Size: 4 bytes (32-bit) or 8 bytes (64-bit)
      • Alignment: Same as size
      • Location: Stack (inline in structs)
    
    Behavior:
      • Assignment copies the value (cheap)
      • Can be shared between threads safely
      • No cleanup needed (no destructor)
    
    Performance:
      • Copy cost: O(1) - single register copy
      • Pass by value: Efficient (fits in register)

Example Output: Collection Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    $ quarry explain-type List[int]
    
    Type: List[int]
    ════════════════════════════════════════
    
    Properties: [Heap] [Move] [MayAlloc] [ThreadSafe*]
    
    Memory Layout:
      • Stack size: 24 bytes (3 words: pointer, length, capacity)
      • Heap size: Varies (capacity × element size)
      • Total for empty list: 24 bytes stack + 0 bytes heap
      • Example: List with 10 ints: 24 bytes stack + 40 bytes heap
    
    Ownership:
      • Owns heap-allocated array of elements
      • Moving transfers ownership (original becomes invalid)
      • Borrowing: Use &List[int] to share read-only access
    
    Behavior:
      • Assignment moves (original cannot be used after)
      • Use .clone() to create a deep copy
      • Automatically frees heap memory when dropped
    
    Performance:
      • Drop cost: O(1) - single deallocation (elements are Copy)
      • Clone cost: O(n) - allocates and copies all elements
      • Push may reallocate: Use with_capacity() to avoid
    
    Thread Safety:
      • ThreadSafe*: Can be moved to other threads
      • Cannot be shared between threads without synchronization
      • Use Mutex<List[int]> for shared mutable access
    
    Common Patterns:
      • Pre-allocate: List[int].with_capacity(expected_size)
      • Borrow for reading: fn process(items: &List[int])
      • Take ownership: fn consume(items: List[int])

Example Output: Custom Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    $ quarry explain-type ImageBuffer
    
    Type: ImageBuffer
    ════════════════════════════════════════
    
    Properties: [Stack] [Move] [NotCopy]
    
    Memory Layout:
      • Size: 1,000,016 bytes (1 MB array + 16 bytes metadata)
      • Alignment: 1 byte
      • Location: Stack or inline (WARNING: Very large)
    
    Structure:
      struct ImageBuffer:
          width: u32           # 4 bytes
          height: u32          # 4 bytes
          data: [u8; 1000000] # 1 MB array
    
    Behavior:
      • Assignment moves (too large to copy implicitly)
      • Pass by reference to avoid 1 MB copy
      • Automatically dropped (no heap allocation to free)
    
    Performance:
      • Copy cost: O(n) - 1 MB memcpy (expensive!)
      • Pass by value: Copies 1 MB onto stack (slow)
      • Pass by reference: O(1) - copies only pointer
    
    Recommendations:
      ⚠️  This type is very large (1 MB) for stack allocation
      ✓  Pass by reference: fn process(img: &ImageBuffer)
      ✓  Use Box<ImageBuffer> to move to heap
      ✓  Consider redesign: separate data buffer from metadata

Type Badge Reference
~~~~~~~~~~~~~~~~~~~~

The type introspection system uses standardized badges:

Memory Location:
  [Stack]     - Stored on the stack (or inline in parent)
  [Heap]      - Owns heap-allocated memory
  [Inline]    - Always inline (no indirection)

Ownership:
  [Copy]      - Cheap bitwise copy (can reuse after assignment)
  [Move]      - Move-only (original invalidated after assignment)
  [NotCopy]   - Explicitly not copyable

Allocation:
  [MayAlloc]  - Operations may allocate (e.g., push, insert)
  [NoAlloc]   - Never allocates memory

Thread Safety:
  [ThreadSafe]   - Can be moved or shared across threads
  [ThreadSafe*]  - Can be moved (Send) but not shared (not Sync)
  [NotThreadSafe] - Cannot cross thread boundaries

Views:
  [BorrowedView] - Refers to data owned elsewhere (e.g., &str, &[T])
  [OwnedData]    - Owns its data

Integration with Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~

Type introspection serves multiple purposes:

1. **Beginner Learning:**
   - Run quarry explain-type on unfamiliar types
   - See memory layout visually ("24 bytes stack + 40 bytes heap")
   - Understand copy vs move behavior
   - Learn when to use & vs owned values

2. **Performance Debugging:**
   - Identify unexpectedly large types
   - See allocation behavior before profiling
   - Understand cache implications (size, alignment)

3. **API Documentation:**
   - Clearly communicate type costs
   - Show thread safety guarantees
   - Explain ownership semantics

4. **IDE Integration:**
   - Hover over type to see badges and summary
   - Quick-info shows size and properties
   - Inline hints for expensive types (>1KB)

Verbose Mode
~~~~~~~~~~~~

    $ quarry explain-type List[int] --verbose

Verbose mode adds:
  • Field-by-field layout with offsets
  • Padding and alignment explanation
  • Trait implementations (Debug, Clone, etc.)
  • Related types (Iterator, slices)
  • Example usage patterns with benchmarks

Why This Matters
~~~~~~~~~~~~~~~~~

This feature operationalizes section 1.5 ("Intuitive Memory Model for Learners"). 
Instead of reading documentation about stack vs heap, beginners can inspect any 
type and see:
  • WHERE it lives (stack, heap, inline)
  • HOW it behaves (copy, move, allocate)
  • WHAT it costs (size, copy cost, drop cost)

Every type becomes self-documenting. The explicit, beginner-friendly presentation 
teaches systems programming concepts through concrete examples rather than 
abstract theory.

Enhanced Layout and Aliasing Introspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Building on the core quarry explain-type functionality, additional commands 
provide deep visibility into memory layout and aliasing guarantees for 
performance-critical code:

quarry layout - Detailed Memory Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shows exact memory layout including padding, alignment, and field offsets:

    $ quarry layout ImageBuffer
    
    Memory Layout: ImageBuffer
    ══════════════════════════════════════
    
    Total Size: 1,000,016 bytes (1 MB + 16 bytes)
    Alignment: 4 bytes
    
    Field Layout (with padding):
    
    Offset │ Size   │ Align │ Field
    ───────┼────────┼───────┼─────────────────────
       0   │ 4 B    │ 4 B   │ width: u32
       4   │ 4 B    │ 4 B   │ height: u32
       8   │ 1 MB   │ 1 B   │ data: [u8; 1000000]
    
    Padding: 0 bytes (no padding needed)
    
    Recommendations:
      ⚠️  Very large stack allocation (1 MB)
      ✓  Consider heap allocation: Box<ImageBuffer>
      ✓  Or separate buffer: struct ImageBuffer { width, height, data: &[u8] }

With padding example:

    $ quarry layout NetworkPacket
    
    Memory Layout: NetworkPacket
    ══════════════════════════════════════
    
    Total Size: 24 bytes
    Alignment: 8 bytes
    
    Field Layout (with padding):
    
    Offset │ Size   │ Align │ Field
    ───────┼────────┼───────┼─────────────────────
       0   │ 1 B    │ 1 B   │ protocol: u8
       1   │ (3 B)  │ -     │ [PADDING]
       4   │ 4 B    │ 4 B   │ length: u32
       8   │ 8 B    │ 8 B   │ timestamp: u64
      16   │ 8 B    │ 8 B   │ checksum: u64
    
    Padding: 3 bytes (12.5% overhead)
    
    Optimization suggestion:
      Reorder fields to eliminate padding:
      
      struct NetworkPacket:
          timestamp: u64    # 8-byte aligned
          checksum: u64     # 8-byte aligned
          length: u32       # 4-byte aligned
          protocol: u8      # 1-byte aligned
      
      New size: 21 bytes (no padding needed)
      Savings: 3 bytes (12.5% reduction)

This teaches cache-line awareness and struct packing naturally through concrete 
examples.

Cache-Line Analysis
~~~~~~~~~~~~~~~~~~~

For performance-critical types, show cache implications:

    $ quarry layout ImageBuffer --cache-analysis
    
    Cache-Line Analysis
    ===================
    
    L1 Cache Line: 64 bytes
    
    ImageBuffer (1,000,016 bytes):
      • Spans: 15,626 cache lines
      • Sequential access: Optimal (contiguous)
      • Random access: 15,626 potential cache misses
    
    Hot Fields (frequently accessed together):
      • width + height: 8 bytes → Same cache line ✓
    
    Recommendations:
      For sequential processing: Current layout optimal
      For random access: Consider tiling (64×64 blocks = 16 KB per tile)

Aliasing Analysis
~~~~~~~~~~~~~~~~~

Understand when the compiler can assume non-aliasing:

    $ quarry explain-aliasing
    
    Aliasing Guarantees in Pyrite
    ══════════════════════════════
    
    The compiler assumes non-aliasing (noalias) when:
    
    1. Exclusive mutable borrow (&mut T):
       
       fn process(data: &mut [f32]):
           # Compiler guarantees: 'data' is the ONLY mutable access
           # Enables: Aggressive vectorization, load/store reordering
       
    2. Multiple immutable borrows with disjoint provenance:
       
       let slice_a = &arr[0..100]
       let slice_b = &arr[100..200]
       process(slice_a, slice_b)  # Compiler proves disjoint
       
    3. Explicit @noalias attribute (expert-level):
       
       @noalias
       fn kernel(a: &[f32], b: &[f32], c: &mut [f32]):
           # Programmer asserts: a, b, c don't overlap
           # Compiler trusts and optimizes aggressively

For specific functions, show aliasing assumptions:

    $ quarry explain-aliasing process_vectors
    
    Aliasing Analysis: process_vectors
    ===================================
    
    fn process_vectors(a: &mut [f32], b: &mut [f32]):
        for i in 0..a.len():
            a[i] += b[i]
    
    Aliasing Assumptions:
      • 'a' and 'b' MAY alias (conservative)
      • Compiler cannot prove disjointness
      • Optimization: Limited (must assume overlap)
    
    Performance Impact:
      • Vectorization: Possible but conservative
      • Load/store reordering: Disabled (aliasing concern)
      • Estimated slowdown: 12-18% vs proven-disjoint case
    
    Solutions:
    
      1. If inputs are ALWAYS disjoint, add @noalias:
         
         @noalias
         fn process_vectors(a: &mut [f32], b: &mut [f32]):
         
         ⚠️  Warning: Undefined behavior if inputs overlap
         ✓  Benefit: 12-18% speedup (enables aggressive opts)
      
      2. Split into separate functions if provable:
         
         fn process_vector_pair(data: &mut [[f32; 2]]):
             # Compiler proves disjoint (separate array elements)
      
      3. Accept the cost if rarely called

This makes aliasing - an invisible, expert-level concern - concrete and actionable.

Integration with quarry cost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    $ quarry cost --aliasing-analysis
    
    Functions Limited by Aliasing Assumptions
    ==========================================
    
    3 functions would benefit from @noalias:
    
      1. process_vectors (src/math.py:234)
         • Current: Conservative aliasing assumptions
         • Potential: 15% speedup with @noalias
         • Verified safe: Manual inspection needed
      
      2. kernel_compute (src/kernels.py:567)
         • Current: 4-wide SIMD (aliasing limits width)
         • Potential: 8-wide SIMD with @noalias = 2x speedup
         • Verified safe: Check callsites for overlap

Why This Matters
~~~~~~~~~~~~~~~~~

Enhanced layout and aliasing visibility completes the "intuitive memory model" 
story:

  • **Layout inspection teaches:**
    - Cache-line awareness (64-byte boundaries)
    - Struct padding and alignment rules
    - Memory access patterns and performance
  
  • **Aliasing inspection teaches:**
    - When compiler can optimize aggressively
    - Why &mut T enables vectorization
    - When @noalias provides benefit
  
  • **Integration with existing tools:**
    - quarry explain-type: WHAT the type is
    - quarry layout: HOW it's arranged in memory
    - quarry explain-aliasing: WHEN compiler can optimize
    - quarry cost: WHERE to apply @noalias

This trio makes performance optimization systematic:
  1. Profile with quarry perf (find hot function)
  2. Inspect with quarry layout (understand memory)
  3. Check with quarry explain-aliasing (identify optimization opportunities)
  4. Apply @noalias if provably safe
  5. Measure improvement

Implementation: Stable Release (after core quarry explain-type is stable)

7.1 Traits and Generics (Parametric Polymorphism)
--------------------------------------------------------------------------------

Traits (Interfaces)
~~~~~~~~~~~~~~~~~~~

A trait in Pyrite is a way to define a set of methods (function signatures) that a 
type can implement. Traits serve a purpose similar to interfaces in Java or 
abstract base classes in C++, and they are akin to Rust's traits. They enable 
ad-hoc polymorphism, meaning you can write functions that operate on any type 
that "implements" a certain trait, without caring about the concrete type. This 
is all done at compile time (zero runtime cost for the polymorphism, unless 
explicitly using dynamic dispatch).

For example, we might define a trait Comparable that requires a cmp method:

    trait Comparable:
        fn cmp(&self, other: &Self) -> int

This trait Comparable says any type that implements it must have a method cmp 
which compares it with another of the same type, returning an int (negative for 
less-than, 0 for equal, positive for greater-than, perhaps). This is similar to 
how many languages define a compare function, or Rust's Ord/PartialOrd traits.

To implement a trait for a type, Pyrite uses an implementation block:

    impl Comparable for int:
        fn cmp(&self, other: &int) -> int:
            return *self - *other

Here we implement Comparable for the built-in int type (assuming we allow that; 
primitive types could have trait implementations). We define cmp to subtract the 
two values, which works as a comparison (if result < 0, self < other; etc.).

For a custom struct:

    struct Person:
        name: String
        age: int
    
    impl Comparable for Person:
        fn cmp(&self, other: &Person) -> int:
            return self.age - other.age

Now Person implements Comparable by comparing ages. We can use this trait to 
write generic algorithms:

Generics
~~~~~~~~

Pyrite allows defining functions or data types with type parameters (like 
templates in C++ or generics in Rust/Java). For instance, a generic function to 
get the maximum element of a list could be written as:

    fn max_item[T: Comparable](list: &List[T]) -> Optional[T]:
        if list.is_empty():
            return None
        var max = list[0]
        for item in list[1..]:  # iterate from second element onward
            if item.cmp(&max) > 0:
                max = item
        return Some(max)

Here fn max_item[T: Comparable] means this function is generic over type T, but 
with a constraint: T must implement the Comparable trait. Inside the function, we 
can then call item.cmp(&max) because we know T has a cmp method from that trait. 

The compiler will monomorphize this function for each specific T that is used - 
in other words, if you call max_item on a List[int], it will generate an 
max_item_int version (using the int implementation of Comparable), and if you 
call it on a List[Person], it will generate a max_item_person, etc. This static 
dispatch means there's no vtable or runtime overhead for calling cmp - the call 
is resolved at compile time to the appropriate function. Thus, generics + traits 
provide flexibility (write one max_item that works for any comparable type) 
without cost relative to writing a specialized function manually.

If one truly needs runtime polymorphism (deciding at runtime which implementation 
to call, perhaps holding different types in the same collection), Pyrite can 
support trait objects or virtual dispatch as an opt-in. For example, a dyn 
Comparable type could be a trait object carrying a pointer to some object and a 
pointer to a vtable of its implementation. This incurs a runtime cost (an 
indirect function call and some extra pointer data) and would only be used if you 
explicitly use dyn. Most beginners won't need this; it's mainly for cases like 
heterogeneous collections or interfacing with OOP frameworks. By default, 
everything is static (zero-cost abstraction). This design (very much like Rust's) 
ensures you only pay for dynamic dispatch if you want it.

Traits can also be used to overload certain operators or behaviors in a 
controlled way. For example, the language might provide a standard trait like Add 
with a method fn add(&self, rhs: &Self) -> Self. If a type implements Add, the 
compiler could allow using + on that type, desugaring it to the add call. This is 
how Rust does operator overloading - it's explicit via traits, not built-in 
magic. Pyrite may or may not include a lot of these in the initial version to 
keep things simple, but it's a possible extension (e.g. an Add trait for numeric 
types, a Display trait for printing, etc.).

Duck Typing vs Traits
~~~~~~~~~~~~~~~~~~~~~~

Python uses duck-typing (if an object has the right methods, you just call them 
and it works). Pyrite's traits are like a compile-time checked version of that. 
They require you to declare the conformance, but then give you static safety and 
efficiency. For a beginner, traits might feel like an advanced topic, but they 
mirror patterns they might know in dynamic languages (like "if it quacks like a 
duck, treat it as a duck"). Pyrite just formalizes the "quack" into a trait.

7.2 Methods and Associated Functions
--------------------------------------------------------------------------------

Pyrite allows you to associate functions with types, which provides a sort of 
lightweight object-oriented feel without actual classes. These are methods 
(instance functions) and associated functions (like static functions) defined in 
impl blocks.

Methods
~~~~~~~

A method is essentially a function that has an implicit parameter for the 
instance (self). For example:

    impl Person:
        fn birthday(&mut self):
            self.age += 1

This defines a method birthday on Person that increments the person's age. The 
&mut self syntax indicates it takes a mutable reference to the instance (so it 
can modify it). We could call this method as person.birthday() on a var person = 
Person { name: "Alice", age: 29 }. After calling person.birthday(), her age 
becomes 30. Under the hood, the compiler translates that call into something like 
birthday(&mut person) - it's not doing anything magic beyond passing the instance 
as an argument - but for the user, it's convenient and clear ("do this action on 
this object").

Methods can be defined either: 
  - In a trait implementation (as seen, where we implement trait methods for a 
    type). 
  - As inherent methods on the type itself (like the birthday example, which is 
    not part of a trait, just a method for Person).

Pyrite does not support subclassing or inheritance between types (just like Rust 
and Go). You cannot say struct Employee: Person or something - instead, you'd 
compose types (an Employee could have a Person field) or use traits to achieve 
polymorphism. This avoids complexities like the diamond problem, slicing issues, 
etc., that come with class inheritance. It keeps the type system simpler and 
encourages composition (favoring "has-a" over "is-a" relationships for code 
reuse).

Associated Functions
~~~~~~~~~~~~~~~~~~~~

These are functions tied to a type but not to an instance. In many languages, 
these are called static methods or constructors. For example, we can add a 
constructor as an associated function:

    impl Person:
        fn new(name: String, age: int) -> Person:
            return Person{name: name, age: age}

Now we can create a Person by calling Person.new("Bob", 25). This is easier to 
read than having a free function. It's essentially namespacing the function under 
the type. Associated functions do not get a self parameter (since they aren't on 
an instance). They can be used for anything from constructors to utility 
functions related to that type.

The benefit of methods and associated functions is largely organizational and 
ergonomic: they let you group functionality with the data it operates on. 
Beginners might find it natural to think "an action that a Person can do, like 
have a birthday, should be part of Person's definition" - and indeed, Pyrite 
allows that, making code more intuitive. However, under the hood, they're just 
functions (no special access privileges beyond what the module's rules allow; 
Pyrite modules control visibility rather than types).

Encapsulation and Design
~~~~~~~~~~~~~~~~~~~~~~~~~

Methods allow a form of encapsulation. If you mark fields of a struct as private 
(to the module) and only expose methods, you can control how the type's state is 
manipulated. Pyrite likely will have a module-level privacy (things are either 
public or private to the module by default). Using methods, you can enforce 
invariants on the data (like never letting age be negative, etc.) by not exposing 
direct field mutation. This is similar to Python, except Python relies on 
convention (like prefix _ for private) whereas Pyrite as a compiled language will 
enforce it if specified.

Operator Methods
~~~~~~~~~~~~~~~~

As mentioned, direct operator overloading by users isn't part of the base 
language, but if included via traits, the implementations of those traits for a 
type would likely be done in an impl as well. For example, if Pyrite had an Add 
trait with method add, implementing that trait for Person could allow using + if 
semantically defined (though adding persons doesn't make sense; a better example 
is maybe a Vector3 type implementing Add to add vectors). This would all be done 
at compile time.

In summary, methods and associated functions give Pyrite a touch of OO flavor 
(methods with dot-call syntax) without the full complexity of class-based 
inheritance. It's a pragmatic middle ground: you can encapsulate behavior with 
data and invoke it in a nice way, and the language remains oriented around 
structs and functions under the hood.

7.3 Contract Programming: Design by Contract (Stable Release)
--------------------------------------------------------------------------------

Beyond memory safety (ownership) and performance guarantees (@cost_budget), 
Pyrite provides Design by Contract for logical correctness verification. 
Contracts are executable specifications that express preconditions, 
postconditions, and invariants, bridging the gap between "memory safe" and 
"logically correct."

Design Philosophy
~~~~~~~~~~~~~~~~~

Contracts in Pyrite are inspired by Eiffel and Ada/SPARK but designed for 
systems programming:
  • Compile-time verification when provable
  • Runtime checks in debug/test builds
  • Zero cost in release builds (optimized out)
  • Composable with performance contracts (@cost_budget)
  • First-class error messages with blame tracking

Basic Contract Syntax
~~~~~~~~~~~~~~~~~~~~~~

Preconditions (@requires) and postconditions (@ensures):

    @requires(n >= 0, "n must be non-negative")
    @requires(n <= 20, "factorial only defined up to 20")
    @ensures(result > 0, "factorial is always positive")
    @ensures(n <= 1 or result > n, "factorial grows")
    fn factorial(n: int) -> int:
        if n <= 1:
            return 1
        return n * factorial(n - 1)

When contracts are violated:

    error[P0901]: precondition violated
      ----> main.py:45:15
       |
    45 |     let result = factorial(-5)
       |                  ^^^^^^^^^^^^^ precondition 'n >= 0' violated
       |
       = contract: n must be non-negative
       = actual value: n = -5
       = help: Ensure input is non-negative before calling

Invariants for Types
~~~~~~~~~~~~~~~~~~~~

Struct and enum invariants ensure type correctness:

    struct BoundedBuffer:
        data: [u8; 1024]
        length: usize
        
        @invariant(self.length <= 1024, "length within bounds")
        @invariant(self.length >= 0, "length non-negative")
    
    impl BoundedBuffer:
        fn push(&mut self, byte: u8) -> Result[(), Error]:
            @requires(self.length < 1024, "buffer not full")
            @ensures(self.length == old(self.length) + 1, "length increased by 1")
            
            self.data[self.length] = byte
            self.length += 1
            Ok(())

The @invariant is checked:
  • After construction
  • After every method call (in debug builds)
  • Before destruction

Loop Invariants
~~~~~~~~~~~~~~~

For complex algorithms, express loop invariants:

    fn binary_search[T: Ord](arr: &[T], target: &T) -> Optional[usize]:
        @requires(is_sorted(arr), "array must be sorted")
        
        var low = 0
        var high = arr.len()
        
        while low < high:
            @invariant(low <= high, "search bounds valid")
            @invariant(high <= arr.len(), "high within array")
            @invariant(
                all(arr[0..low], fn(x): x < target),
                "all elements before low are less than target"
            )
            @invariant(
                all(arr[high..], fn(x): x >= target),
                "all elements after high are >= target"
            )
            
            let mid = low + (high - low) / 2
            match arr[mid].cmp(target):
                Less:
                    low = mid + 1
                Greater:
                    high = mid
                Equal:
                    return Some(mid)
        
        return None

Old-Value Syntax
~~~~~~~~~~~~~~~~

Reference previous state in postconditions:

    fn increment_counter(&mut self):
        @ensures(self.counter == old(self.counter) + 1, "counter incremented")
        
        self.counter += 1

The old() function captures value at function entry for comparison in 
postcondition.

Quantified Conditions
~~~~~~~~~~~~~~~~~~~~~

Express properties over collections:

    @ensures(forall(result, fn(x): x % 2 == 0), "all even")
    fn filter_even(input: &[int]) -> Vec[int]:
        return input.iter().filter(fn(x): x % 2 == 0).collect()
    
    @requires(exists(arr, fn(x): x > 0), "at least one positive")
    fn find_first_positive(arr: &[int]) -> Optional[int]:
        for x in arr:
            if x > 0:
                return Some(x)
        return None

Compile-Time Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~

When contracts can be proven at compile time, no runtime cost:

    fn process_small_array(arr: [int; 5]) -> int:
        @requires(arr.len() == 5, "array has 5 elements")
        # Compiler proves: arr.len() is 5 (compile-time constant)
        # No runtime check generated
        ...

Symbolic execution for simple contracts:

    fn divide(a: int, b: int) -> int:
        @requires(b != 0, "divisor must be non-zero")
        return a / b
    
    let x = divide(10, 5)  # OK: b is 5, provably != 0
    let y = divide(10, 0)  # ERROR: Compile-time contract violation

Call-Graph Contract Propagation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Contracts compose through function boundaries:

    @requires(index < arr.len(), "index in bounds")
    fn get_element(arr: &[int], index: usize) -> int:
        return arr[index]
    
    fn caller():
        let arr = [1, 2, 3, 4, 5]
        let val = get_element(&arr, 10)  # ERROR: Contract violated
    
    error[P0902]: precondition violated in call
      ----> main.py:67:15
       |
    67 |     let val = get_element(&arr, 10)
       |               ^^^^^^^^^^^^^^^^^^^^^ precondition 'index < arr.len()' not satisfied
       |
       = contract: index < arr.len()
       = actual: index = 10, arr.len() = 5
       = note: Call chain:
         1. caller() at main.py:67
            → calls get_element(&arr, 10)
         2. get_element() requires index < arr.len()
            → 10 < 5 is false [VIOLATION]
       |
       = help: Validate index before calling:
               if index < arr.len():
                   let val = get_element(&arr, index)

Integration with Cost Contracts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine logical and performance contracts:

    @requires(data.len() <= 1024, "input bounded")
    @ensures(result.len() == data.len(), "output same length")
    @cost_budget(allocs=0, cycles=10000)
    fn process_packet(data: &[u8]) -> Result[Vec[u8], Error]:
        # Both logical correctness AND performance enforced
        ...

Runtime Contract Checking
~~~~~~~~~~~~~~~~~~~~~~~~~~

In debug and test builds, contracts are checked:

    $ quarry test
    
    Running tests with contract checking enabled...
    
    test test_binary_search ... FAILED
    
    Contract violation: postcondition
      ----> src/search.py:89:5
       |
    89 | @ensures(result.is_some() implies arr[result.unwrap()] == target)
       |
       = note: Postcondition violated
       = result: Some(3)
       = arr[3]: 42
       = target: 41
       = note: Function returned index 3, but arr[3] != target
    
    This indicates a BUG in binary_search implementation.

Configuration
~~~~~~~~~~~~~

Control contract checking levels:

    # Quarry.toml
    [profile.debug]
    check-contracts = "all"          # Check all contracts
    
    [profile.test]
    check-contracts = "all"          # Check in tests
    
    [profile.release]
    check-contracts = "none"         # Optimize out (zero cost)
    
    [profile.certified]
    check-contracts = "critical"     # Check @safety-critical contracts only

Safety-Critical Contracts
~~~~~~~~~~~~~~~~~~~~~~~~~

Mark critical contracts that should be checked even in release:

    @safety_critical
    @requires(temperature >= -40 and temperature <= 85, "sensor within operating range")
    fn read_temperature_sensor() -> f32:
        # This contract checked in ALL builds (safety-critical)
        ...

Why Contracts Matter
~~~~~~~~~~~~~~~~~~~~

**Logical correctness:**
  • Ownership prevents memory bugs
  • Contracts prevent logic bugs
  • "Memory-safe but logically incorrect" is still wrong
  • Contracts close the correctness gap

**Safety certification:**
  • DO-178C: Formal methods improve certification level
  • IEC 62304: Design by Contract accepted for medical devices
  • Ada/SPARK: Contracts enable formal verification
  • Pyrite: Same benefits, more accessible syntax

**Documentation as code:**
  • Contracts are executable specifications
  • Clearer than comments (enforced, not ignored)
  • Self-documenting APIs ("requires X, ensures Y")
  • Impossible to drift from implementation (checked)

**Testing amplification:**
  • Contracts checked on every test run
  • Catch violations beyond explicit test cases
  • Fuzz testing with contracts = systematic bug finding
  • quarry fuzz + contracts = exhaustive edge case coverage

**Verification path:**
  • Beta Release: Runtime checking in debug/test
  • Stable Release: Compile-time verification for provable contracts
  • Future: Integration with formal verification tools (Z3, SMT solvers)

Use Cases
~~~~~~~~~

  • Safety-critical firmware (aerospace, medical devices)
  • Cryptographic implementations (constant-time contracts)
  • Protocol implementations (state machine invariants)
  • Parsers (input validation contracts)
  • Concurrent code (lock ordering invariants)

Teaching Path
~~~~~~~~~~~~~

  1. **Beginner:** See contracts in stdlib ("why APIs are safe")
  2. **Intermediate:** Add simple contracts (@requires non-negative)
  3. **Advanced:** Complex invariants, loop invariants
  4. **Expert:** Formal verification integration

Comparison to Other Languages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  • **Eiffel:** Flagship contracts, but niche language
  • **Ada/SPARK:** Formal verification, complex tooling
  • **Rust:** No built-in contracts (external crates only)
  • **D:** Has contracts, but not widely used
  • **Pyrite:** Contracts integrated with ownership, cost tracking, blame chains

Pyrite is the first **mainstream systems language** with first-class contract 
support that composes with ownership and performance contracts.

Implementation: Stable Release (after core compiler is stable)
Priority: High (correctness + certification + differentiation)
Complexity: High (SMT integration for verification, runtime checking)
Impact: High (enables safety certification, prevents logic bugs)

7.4 Noalias and Restrict Semantics (Stable Release, Expert Feature)
--------------------------------------------------------------------------------

For advanced performance optimization, Pyrite provides explicit non-aliasing 
assertions that enable aggressive compiler optimizations. This is an opt-in, 
expert-level feature for cases where exclusive &mut access isn't sufficient.

Design Philosophy
~~~~~~~~~~~~~~~~~

Pyrite's ownership system already handles most aliasing through exclusive &mut 
borrows. The @noalias attribute is for the remaining cases: asserting that 
multiple immutable references don't overlap, or that pointers from FFI don't 
alias.

The @noalias Attribute
~~~~~~~~~~~~~~~~~~~~~~

Marks parameters as non-aliasing, enabling optimizations:

    @noalias
    fn process(a: &mut [f32], b: &mut [f32]):
        # Compiler assumes a and b don't overlap
        # Enables vectorization and aggressive loop optimizations
        for i in 0..a.len():
            a[i] += b[i]

Without @noalias, the compiler must assume potential aliasing and generates 
conservative code. With @noalias, the compiler can:
  • Reorder memory accesses
  • Vectorize loops more aggressively
  • Eliminate redundant loads
  • Perform more loop transformations

When to Use
~~~~~~~~~~~

@noalias is useful for:

1. **Multiple immutable references where compiler can't prove disjointness:**

   @noalias
   fn sum_two_views(a: &[f32], b: &[f32]) -> f32:
       # Assert a and b don't overlap
       var sum = 0.0
       for i in 0..a.len():
           sum += a[i] + b[i]
       return sum

2. **FFI pointers from C (no ownership information):**

   @noalias
   extern fn memcpy(dest: *mut u8, src: *const u8, n: usize)

3. **Performance-critical kernels where exclusivity is verified manually:**

   @noalias
   fn kernel_compute(in1: &[f32], in2: &[f32], out: &mut [f32]):
       # Manual verification: in1, in2, out are disjoint
       # Parameter closure (fn[...]) is inlined, zero allocation
       algorithm.vectorize[width=8](out.len(), fn[i: int]:
           out[i] = in1[i] * in2[i]
       )

Safety and Verification
~~~~~~~~~~~~~~~~~~~~~~~

@noalias is checked at compile time when possible, runtime in debug builds:

    @noalias
    fn process(a: &mut [f32], b: &mut [f32]):
        # ...
    
    let mut data = vec![1.0; 100]
    process(&mut data[0..50], &mut data[50..100])  # OK: disjoint
    
    # Debug build:
    process(&mut data[0..50], &mut data[25..75])   # PANIC: overlap detected

Release builds trust the programmer (like unsafe). The @noalias contract is 
part of the function's safety requirements.

Compiler Diagnostics
~~~~~~~~~~~~~~~~~~~~

When aliasing occurs despite @noalias:

    warning[P1300]: potential aliasing in @noalias function
      ----> src/compute.py:45:5
       |
    43 | @noalias
    44 | fn process(a: &mut [f32], b: &mut [f32]):
    45 |     process(&mut data[0..50], &mut data[25..75])
       |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ potential overlap
       |
       = note: @noalias asserts that 'a' and 'b' are disjoint
       = help: Verify manually that slices don't overlap
       = suggestion: Run with --debug to detect aliasing at runtime

Integration with Ownership
~~~~~~~~~~~~~~~~~~~~~~~~~~~

@noalias complements, doesn't replace, ownership:

  • &mut T already provides exclusive access (single mutable reference)
  • @noalias is for multiple references where compiler can't prove disjointness
  • Most code doesn't need @noalias (ownership handles common cases)

Performance Impact
~~~~~~~~~~~~~~~~~~

Typical speedups from @noalias:
  • 5-15% for compute-heavy loops (vectorization)
  • 10-25% for memory-bound operations (eliminates redundant loads)
  • Depends heavily on specific code and compiler optimizations

Use quarry cost to see when @noalias helps:

    $ quarry cost --noalias-analysis
    
    Function: process(a: &mut [f32], b: &mut [f32])
      → Aliasing assumption prevents vectorization
      → Suggestion: Add @noalias if inputs are guaranteed disjoint
      → Estimated improvement: 12-18% (enables SIMD)

When NOT to Use
~~~~~~~~~~~~~~~

Don't use @noalias if:
  • Ownership rules already prove exclusivity (&mut handles this)
  • You're not certain inputs are disjoint (undefined behavior otherwise)
  • Performance profiling doesn't show a bottleneck
  • Code is not performance-critical

@noalias is an expert optimization, not a default tool.

Teaching Path
~~~~~~~~~~~~~

1. **Beginner-Intermediate:** Use ownership system (&, &mut)
2. **Advanced:** Understand when ownership proves disjointness
3. **Expert:** Profile, identify aliasing-limited optimizations
4. **Expert:** Apply @noalias with manual verification

Summary
~~~~~~~

@noalias fills a small but important gap: asserting non-aliasing when ownership 
can't prove it. It's explicit, checked when possible, and provides measurable 
performance gains for the right use cases.

Implementation: Stable Release (after core ownership and performance tooling are stable)

7.5 Two-Tier Closure Model: Parameter vs Runtime (Beta Release)
--------------------------------------------------------------------------------

Pyrite distinguishes between two fundamentally different kinds of closures, making 
the performance characteristics explicit and enabling zero-cost abstractions for 
algorithmic helpers. This distinction is inspired by Mojo's parameter closures 
and addresses the critical gap between "callable code" and "zero-overhead callable 
code."

Design Philosophy
~~~~~~~~~~~~~~~~~

The two-tier model makes cost explicit:
  • **Parameter closures** - Compile-time, always-inline, zero-allocation, used 
    for performance primitives (vectorize, parallelize, tile)
  • **Runtime closures** - Real values, can escape, can allocate/copy capture 
    state, used for callbacks and thread spawning

This distinction is the foundation for verifiable `--no-alloc` mode and makes 
`quarry cost` analysis precise.

Parameter Closures (Compile-Time)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parameter closures use square bracket syntax `fn[params]` and are evaluated at 
compile time:

    import std::algorithm
    
    fn scale_array(data: &mut [f32], factor: f32):
        # Parameter closure: fn[i: int] with square brackets
        algorithm.vectorize[width=auto](data.len(), fn[i: int]:
            data[i] = data[i] * factor
        )

Key properties:
  • **Zero allocation:** Never captured on heap, inlined directly
  • **Compile-time only:** Cannot escape function scope or be stored
  • **Always inlined:** Compiler guarantees inline expansion
  • **No vtable:** Static dispatch only
  • **Captures by reference:** Environment captured at compile time
  • **Verified by --no-alloc:** Safe to use in no-allocation contexts

Parameter closures are the backbone of algorithmic helpers:

    # All use parameter closures (zero-cost)
    algorithm.vectorize[width=8](n, fn[i: int]: data[i] *= 2.0)
    algorithm.parallelize(n, fn[i: int]: process(&work[i]))
    algorithm.tile[64](rows, cols, fn[r: int, c: int]: compute(r, c))
    compile.unroll[N](fn[i: int]: result[i] = a[i] + b[i])

Cost verification:

    @noalloc
    fn process_buffer(data: &mut [f32]):
        # OK: parameter closures don't allocate
        algorithm.vectorize[width=auto](data.len(), fn[i: int]:
            data[i] = data[i].sqrt()
        )
    
    # Compiles successfully with --no-alloc

Capture semantics:

    fn scale_all(arrays: &[&mut [f32]], factor: f32):
        for arr in arrays:
            # Parameter closure captures 'factor' by reference (compile-time)
            algorithm.vectorize[width=8](arr.len(), fn[i: int]:
                arr[i] *= factor  # OK: 'factor' captured, zero cost
            )

What you CANNOT do with parameter closures:

    fn broken_example():
        let closure = fn[i: int]: i * 2  # ERROR: cannot store parameter closure
        
        let list = List[fn[int] -> int].new()
        list.push(fn[i: int]: i * 2)  # ERROR: cannot store in collection
        
        return fn[i: int]: i * 2  # ERROR: cannot return parameter closure

Parameter closures exist only at compile time for inline expansion.

Runtime Closures (First-Class Values)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runtime closures use parenthesis syntax `fn(params)` and are first-class values:

    # Runtime closure: fn(x: int) with parentheses
    let filter_fn = fn(x: int) -> bool:
        return x > threshold
    
    # Can be stored
    let callbacks = List[fn(int) -> bool].new()
    callbacks.push(filter_fn)
    
    # Can be returned
    fn make_filter(threshold: int) -> fn(int) -> bool:
        return fn(x: int) -> bool:
            return x > threshold
    
    # Can escape scope
    Thread.spawn(fn():
        process_background()
    )

Key properties:
  • **Can allocate:** Capture environment may require heap allocation
  • **Can escape:** Store in variables, return from functions, pass to threads
  • **Dynamic dispatch possible:** Can be stored in trait objects
  • **Captured by value/move:** Ownership rules apply to captures
  • **Shows up in quarry cost:** Allocations visible and tracked
  • **Requires runtime representation:** Function pointer + environment data

Cost characteristics:

    fn create_handlers(config: &Config) -> List[fn() -> void]:
        var handlers = List[fn() -> void].new()
        
        # Runtime closure captures 'config' reference
        # Allocation: closure object on heap (environment data)
        handlers.push(fn():
            print(config.name)  # Captures 'config' by reference
        )
        
        return handlers
    
    # quarry cost shows:
    #   Allocation at line X: closure environment (24 bytes)

Capture modes:

    let x = 10
    let y = String.new("hello")
    
    # Capture by reference (no allocation if closure doesn't escape)
    let closure1 = fn() -> int:
        return x * 2  # Captures &x
    
    # Capture by move (transfers ownership)
    let closure2 = fn():
        print(y)  # Moves y into closure
    # y is now invalid in outer scope
    
    # Explicit move all
    let closure3 = move fn():
        print(x)  # Forces move even for Copy types

Thread spawning requires move semantics:

    let data = vec![1, 2, 3]
    
    # ERROR: data is borrowed, may not outlive thread
    Thread.spawn(fn():
        print(data)
    )
    
    # OK: explicit move into thread
    Thread.spawn(move fn():
        print(data)  # data moved into closure
    )
    # data invalid here

Syntax Summary
~~~~~~~~~~~~~~

Visual distinction makes cost explicit:

    # COMPILE-TIME (zero-cost, inline, no-alloc safe)
    algorithm.vectorize[width=8](n, fn[i: int]:
        data[i] *= 2.0
    )
    
    # RUNTIME (may allocate, can escape, shows in quarry cost)
    Thread.spawn(fn():
        process_background()
    )
    
    # Parameter closure for compile-time helpers
    compile.unroll[4](fn[i: int]:
        result[i] = input[i]
    )
    
    # Runtime closure for dynamic behavior
    let callbacks = vec![
        fn(): handler_one(),
        fn(): handler_two(),
    ]

Teaching Progression
~~~~~~~~~~~~~~~~~~~~

1. **Week 1-2 (Beginner):** Use algorithmic helpers without understanding closure 
   types
   
   algorithm.vectorize[width=auto](data.len(), fn[i: int]:
       data[i] = data[i] * 2.0
   )
   
   "Just write what to do per element, the compiler makes it fast"

2. **Week 3-4 (Intermediate):** Learn runtime closures for callbacks
   
   let filter = fn(x: int) -> bool:
       return x > 10
   numbers.iter().filter(filter)
   
   "Closures are values you can pass around"

3. **Week 5+ (Advanced):** Understand the distinction
   
   "fn[...] is compile-time (free), fn(...) is runtime (may allocate)"
   
   See difference in `quarry cost` output

4. **Expert:** Choose appropriate closure type for performance
   
   "Use parameter closures for hot paths, runtime closures for flexibility"

Integration with quarry cost
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The cost analyzer distinguishes closure types:

    $ quarry cost
    
    Closures: 3 parameter (zero-cost), 5 runtime (24 bytes each)
    
    Parameter closures (zero-cost, always inlined):
      ✓ Line 234: vectorize closure - INLINED
      ✓ Line 267: parallelize closure - INLINED  
      ✓ Line 289: tile closure - INLINED
    
    Runtime closures (heap-allocated environments):
      Line 156: Thread::spawn closure
        • Environment: 24 bytes (captures 2 references)
        • Lifetime: Thread duration
      
      Line 178: Stored in callback list
        • Environment: 32 bytes (captures String by move)
        • Allocation: One per closure

Integration with --no-alloc Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Parameter closures are safe in no-allocation contexts:

    quarry build --no-alloc
    
    @noalloc
    fn compute_kernel(data: &mut [f32]):
        # OK: parameter closure doesn't allocate
        algorithm.vectorize[width=8](data.len(), fn[i: int]:
            data[i] = data[i].sqrt()
        )
        
        # ERROR: runtime closure may allocate
        let callback = fn(): print("done")
        #              ^^^ heap allocation in no-alloc mode

This makes `--no-alloc` verification complete - no hidden allocation through 
closures.

Error Messages
~~~~~~~~~~~~~~

Clear diagnostics teach the distinction:

    error[P0801]: cannot store parameter closure as runtime value
      ----> src/compute.py:45:13
       |
    45 |     let f = fn[i: int]: i * 2
        |             ^^^^^^^^^^^^^^^^^ parameter closure (compile-time only)
       |
       = note: Parameter closures use square brackets fn[...] and exist only 
               at compile time for inline expansion
       = help: To store a closure, use runtime closure syntax:
               let f = fn(i: int) -> int: return i * 2
       = explain: Run 'pyritec --explain P0801' for closure types guide

    error[P0802]: runtime closure in no-allocation context
      ----> src/embedded.py:67:9
       |
    65 | @noalloc
    66 | fn process_data(input: &[u8]):
    67 |     let parser = fn(): parse(input)
        |                  ^^^^^^^^^^^^^^^^^^ runtime closure may allocate
       |
       = note: Runtime closures allocate environment for captured variables
       = help: Use parameter closure for no-alloc guarantee:
               algorithm.vectorize[width=auto](input.len(), fn[i: int]:
                   process_byte(input[i])
               )
       = explain: Run 'pyritec --explain P0802' for zero-cost closures

quarry explain-type Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Type introspection shows closure characteristics:

    $ quarry explain-type "fn[int]"
    
    Type: Parameter Closure (fn[int])
    ════════════════════════════════════════
    
    Properties: [CompileTime] [ZeroCost] [AlwaysInline]
    
    Memory Layout:
      • Size: 0 bytes at runtime (compile-time only)
      • Captures: Compile-time environment
      • Storage: Cannot be stored (exists only during compilation)
    
    Behavior:
      • Inlined at every call site (no function pointer)
      • Zero allocation (never captured on heap)
      • Zero indirection (direct code expansion)
    
    Use Cases:
      • algorithm.vectorize - SIMD loop bodies
      • algorithm.parallelize - Work distribution
      • algorithm.tile - Cache-blocking
      • compile.unroll - Loop unrolling
    
    Restrictions:
      ✗ Cannot be stored in variables
      ✗ Cannot be returned from functions
      ✗ Cannot be passed to runtime functions
      ✓ Can only be used with compile-time helpers

    $ quarry explain-type "fn(int) -> bool"
    
    Type: Runtime Closure (fn(int) -> bool)
    ════════════════════════════════════════
    
    Properties: [Runtime] [MayAlloc] [FirstClass]
    
    Memory Layout:
      • Size: 16 bytes (function pointer + environment pointer)
      • Environment: Varies (depends on captured variables)
      • Total: 16 bytes + sizeof(captures)
    
    Behavior:
      • Can be stored in variables and collections
      • Can be returned from functions
      • Can escape scope and be passed to threads
      • Environment may allocate on heap (if captures non-Copy types)
    
    Cost:
      • Allocation: Varies (0 if no captures, >0 if captures heap data)
      • Call overhead: Indirect call (function pointer, ~2-3 cycles)
      • Environment access: One pointer dereference per captured variable
    
    Use Cases:
      • Callbacks and event handlers
      • Thread::spawn arguments
      • Filter/map in iterators
      • Plugin systems
      • Dynamic dispatch scenarios

Why This Distinction Matters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The two-tier model unlocks multiple benefits:

1. **Zero-cost algorithmic abstractions:**
   
   Parameter closures make helpers like vectorize truly zero-cost - no allocation, 
   no indirection, no runtime overhead. The closure body is inlined directly into 
   the generated SIMD loop.

2. **Verifiable --no-alloc mode:**
   
   The compiler can guarantee no heap allocation through algorithmic helpers 
   because parameter closures have no runtime representation.

3. **Teaching clarity:**
   
   Beginners learn "square brackets = free, parentheses = may cost" as a simple 
   visual rule. Advanced developers understand the compile-time vs runtime 
   distinction.

4. **Performance transparency:**
   
   `quarry cost` can analyze runtime closures but shows parameter closures as 
   "zero-cost inline." No ambiguity about what's expensive.

5. **Composability:**
   
   Algorithmic helpers compose without allocation:
   
       algorithm.parallelize(chunks, fn[chunk: int]:
           algorithm.vectorize[width=8](chunk_size, fn[i: int]:
               # Both closures are parameter closures (zero-cost)
               data[chunk * chunk_size + i] = compute(i)
           )
       )

Comparison to Other Languages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  • **Mojo:** Direct inspiration - Mojo's parameter closures power `vectorize` and 
    `parallelize` with guaranteed zero cost
  • **C++ lambdas:** Can be inline or allocate, but distinction is implicit and 
    compiler-dependent (not explicit syntax)
  • **Rust closures:** All runtime closures, even when inlined (no compile-time 
    closure type)
  • **Zig comptime:** Related concept but different mechanism (comptime blocks vs 
    closure syntax)

Pyrite makes the distinction **explicit in syntax** rather than compiler-dependent, 
ensuring predictable cost regardless of optimization level.

API Design Guidelines
~~~~~~~~~~~~~~~~~~~~~

Standard library follows these patterns:

**Use parameter closures for:**
  • algorithm.vectorize - SIMD loop bodies
  • algorithm.parallelize - Work distribution (body runs per item)
  • algorithm.tile - Cache-blocking iteration
  • compile.unroll - Loop unrolling
  • compile.if_constexpr - Compile-time conditionals
  • Any compile-time code generation helper

**Use runtime closures for:**
  • Thread::spawn - Thread entry points (can capture and move data)
  • Iterator::filter, Iterator::map - Lazy iterator chains
  • Event handlers and callbacks
  • Sorted collections (comparison functions)
  • Defer blocks (scope-exit code)
  • Any closure that escapes or is stored dynamically

Example: Iterator Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~

Different iterator methods use appropriate closure types:

    let numbers = vec![1, 2, 3, 4, 5]
    
    # Runtime closure (filter may need to store for lazy evaluation)
    let filtered = numbers.iter()
        .filter(fn(x: &int) -> bool: *x > 2)
    
    # But forEach uses parameter closure (always eager)
    numbers.iter().for_each(fn[x: &int]:
        print(*x)  # Inlined into loop, zero allocation
    )

This flexibility allows both lazy (runtime closures) and eager (parameter closures) 
patterns with clear performance implications.

Type System Integration
~~~~~~~~~~~~~~~~~~~~~~~

Parameter and runtime closure types are distinct:

    # Parameter closure type (only appears in signatures)
    fn vectorize[T, Body: fn[int]](
        count: int,
        body: Body  # Body is a compile-time parameter
    ):
        # Body is inlined at compile time
    
    # Runtime closure type (regular type)
    type Predicate[T] = fn(T) -> bool
    
    fn filter[T](items: &[T], pred: Predicate[T]) -> Vec[T]:
        var result = Vec[T].new()
        for item in items:
            if pred(item):  # Indirect call through function pointer
                result.push(item)
        return result

Compiler Guarantees
~~~~~~~~~~~~~~~~~~~

The compiler enforces distinctions:

  • Parameter closures **must** be inlined (compilation fails if not possible)
  • Parameter closures **cannot** allocate (compilation fails if captures would 
    require heap)
  • Runtime closures **can** allocate (tracked by quarry cost)
  • Runtime closures **can** escape (ownership rules apply to captures)

This makes the cost model explicit and verifiable - no "depends on optimization 
level" ambiguity.

Migration from Existing Spec
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Current spec shows:

    algorithm.vectorize[width=auto](data.len(), fn(i: int):
        data[i] = data[i] * factor
    )

This is ambiguous - is `fn(i: int)` zero-cost or not?

Updated syntax makes it explicit:

    algorithm.vectorize[width=auto](data.len(), fn[i: int]:
        data[i] = data[i] * factor
    )

The square brackets `fn[i: int]` signal "compile-time, zero-cost, inline."

All algorithmic helpers (vectorize, parallelize, tile, unroll) updated to use 
parameter closures consistently.

Why This Is the Highest-Value Addition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The two-tier closure model:

1. Fills the biggest gap in current spec (closure cost ambiguity)
2. Enables `--no-alloc` verification for algorithmic helpers
3. Makes Pyrite's performance story bulletproof (zero-cost abstractions are 
   provably zero-cost)
4. Provides clear teaching model ("square brackets = free")
5. Aligns perfectly with existing compile-time parameterization (`[N: int]` 
   syntax)
6. Makes `quarry cost` analysis precise and complete

This is the foundation for Pyrite's "accessible high-performance" positioning -
ergonomic helpers (vectorize, parallelize) that are provably zero-cost, not 
"usually optimized away."

Implementation: Beta Release (after core ownership and algorithmic helpers exist)
Complexity: Moderate (new closure type, parameter tracking, inline verification)
Impact: High (unlocks verifiable zero-cost abstractions)

7.6 Compile-Time Code Execution and Metaprogramming
--------------------------------------------------------------------------------

Pyrite incorporates capabilities for executing code at compile time, inspired by 
Zig's comptime functions, Rust's const fn, Mojo's parameterization, and C++'s 
constexpr and template metaprogramming. The goal is to enable powerful 
optimizations and code generation without requiring an external macro language or 
heavy runtime reflection.

Const Functions
~~~~~~~~~~~~~~~

You can mark certain functions as const (meaning they can be evaluated at compile 
time if called with constant arguments). For example:

    const fn fib(n: int) -> int:
        if n < 2:
            return n
        else:
            return fib(n-1) + fib(n-2)
    
    const FIB_10 = fib(10)

In this code, fib is a function that calculates Fibonacci numbers, marked const. 
FIB_10 will be computed at compile time (the compiler will recursively evaluate 
fib(10) during compilation) and treated as a constant with that value. This is 
useful for precomputing lookup tables, math constants, etc., at compile time so 
that they incur no cost at runtime.

Compile-Time Parameterization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite supports compile-time parameterization inspired by Mojo's parameter system, 
enabling the compiler to generate specialized versions of functions and types for 
specific constant values. This provides performance benefits similar to C++ 
templates but with clearer semantics and better error messages.

Syntax and Semantics
~~~~~~~~~~~~~~~~~~~~~

Compile-time parameters are distinguished from runtime parameters using square 
brackets:

    fn process[N: int](data: [u8; N]) -> int:
        # N is known at compile time
        # Compiler generates specialized version for each unique N
        var sum = 0
        for i in 0..N:  # Loop unrolling possible
            sum += data[i]
        return sum
    
    # Usage:
    let buffer1: [u8; 16] = ...
    let result1 = process[16](buffer1)  # Specialized for N=16
    
    let buffer2: [u8; 256] = ...
    let result2 = process[256](buffer2)  # Different specialization for N=256

The key properties of compile-time parameters:
  • Known at compile time (constant values only)
  • Used for type-level computations and optimizations
  • Each unique parameter value generates a separate function/type instance
  • Zero runtime cost (constants can be inlined, loops unrolled)

Parameter Constraints
~~~~~~~~~~~~~~~~~~~~~

Compile-time parameters can be integers, booleans, or types:

    # Integer parameter (array size, loop bounds, capacity)
    fn create_buffer[Size: int]() -> [u8; Size]:
        return [0; Size]
    
    # Boolean parameter (feature flags, optimization modes)
    fn process[DebugMode: bool](data: &[u8]):
        if DebugMode:  # Evaluated at compile time
            # Debug code completely eliminated when DebugMode=false
            print("Processing {} bytes", data.len())
        # ... actual processing ...
    
    # Type parameter with compile-time size constraint
    fn optimize[T, Size: int](data: [T; Size]) -> int:
        # Both T and Size available at compile time
        const BYTES = Size * sizeof(T)  # Computed at compile time
        if BYTES < 64:  # Compile-time decision
            # Small buffer: inline processing
            return process_inline(data)
        else:
            # Large buffer: different strategy
            return process_chunked(data)

Standard Library Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The standard library provides compile-time helpers for common optimizations using 
parameter closures:

    import std.compile

    # Unroll loops at compile time
    fn vector_add[N: int](a: [f32; N], b: [f32; N]) -> [f32; N]:
        var result: [f32; N]
        # Parameter closure (fn[...]) inlined and unrolled at compile time
        compile.unroll[N](fn[i: int]:
            result[i] = a[i] + b[i]
        )
        return result

@unroll - Explicit Loop Unrolling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For performance-critical code where loop unrolling provides measurable benefit, 
Pyrite provides the @unroll attribute with explicit control and safety limits:

    @unroll(factor=4)
    fn process_array(data: &mut [f32]):
        for i in 0..data.len():
            data[i] = data[i] * 2.0 + 1.0
    
    # Compiler unrolls to process 4 elements per iteration:
    # for i in 0..data.len() step 4:
    #     data[i+0] = data[i+0] * 2.0 + 1.0
    #     data[i+1] = data[i+1] * 2.0 + 1.0
    #     data[i+2] = data[i+2] * 2.0 + 1.0
    #     data[i+3] = data[i+3] * 2.0 + 1.0
    #     # + remainder loop for data.len() % 4

Unroll factor options:
  • @unroll(factor=N) - Unroll by specific factor (2, 4, 8, 16, etc.)
  • @unroll(full) - Fully unroll (only if iteration count known at compile time)
  • @unroll(auto) - Compiler chooses optimal factor based on loop body size

Safety limits and warnings:

    @unroll(factor=128)
    fn process_small(data: &[f32; 4]):
        for i in 0..4:
            data[i] = compute(data[i])
    
    warning[P1200]: excessive unroll factor
      ----> src/compute.py:45:5
       |
    45 | @unroll(factor=128)
       | ^^^^^^^^^^^^^^^^^^^ unroll factor 128 too large for loop
       |
       = note: Loop has only 4 iterations
       = note: Unroll factor 128 would generate 512 instructions
       = help: Reduce factor or use @unroll(full) for complete unrolling
       = suggestion: @unroll(factor=4) or @unroll(full)

Compiler limits:
  • Maximum unroll factor: 64 (prevents code size explosion)
  • Maximum unrolled body size: 256 instructions per iteration
  • Full unroll: Only for loops with ≤ 128 iterations (compile-time known)

Integration with compile-time parameters:

    fn matrix_multiply[N: int](a: &Matrix[N], b: &Matrix[N]) -> Matrix[N]:
        var result = Matrix[N]::zero()
        
        @unroll(full)  # N known at compile time
        for i in 0..N:
            @unroll(full)
            for j in 0..N:
                for k in 0..N:
                    result[i][j] += a[i][k] * b[k][j]
        
        return result
    
    # For Matrix[4], compiler fully unrolls i and j loops
    # For Matrix[100], compiler warns and uses auto factor

Interaction with SIMD:

    @unroll(factor=4)
    @simd(width=8)
    fn process_large(data: &mut [f32]):
        # Combines loop unrolling with SIMD
        # Each unrolled iteration processes 8 elements (SIMD width)
        # Total: 32 elements per outer loop iteration

When to use @unroll:
  • Small, performance-critical loops (< 16 iterations)
  • Loops with compile-time known bounds
  • Inner loops in hot paths (profiling shows benefit)
  • Kernels that benefit from instruction-level parallelism

When NOT to use @unroll:
  • Large loops (code size explosion)
  • Loops with complex bodies (diminishing returns)
  • Loops with unpredictable branches (unrolling adds little value)
  • Without profiling data (premature optimization)

Cost transparency integration:

    quarry cost shows:
      @unroll(factor=8) at line 45:
        • Loop body: 12 instructions
        • Unrolled size: 96 instructions + 12 (remainder)
        • Code size increase: +84 bytes
        • Expected speedup: 1.5-2x (reduced branch overhead)

Teaching path:
  1. **Beginner:** Don't use @unroll, let compiler optimize
  2. **Intermediate:** Profile shows hot loop → try @unroll(factor=4)
  3. **Advanced:** Tune factor based on profiling results
  4. **Expert:** Combine @unroll with @simd and compile-time params

Beta Release feature that fills the gap between "compiler auto-optimization" and 
"manual assembly." Provides explicit control while maintaining safety through 
compiler warnings and hard limits.
    
    # Choose optimal SIMD width for current platform
    fn process_parallel(data: &[f32]):
        const WIDTH = compile.simd_width[f32]()  # 4, 8, or 16 depending on CPU
        # ... use WIDTH to process in optimal chunks ...
    
    # Compile-time assertions
    fn requires_power_of_two[N: int]():
        compile.assert(is_power_of_two(N), "N must be power of 2")
    
    const fn is_power_of_two(n: int) -> bool:
        return n > 0 and (n & (n - 1)) == 0

Practical Examples
~~~~~~~~~~~~~~~~~~

Example 1: Fixed-size matrix optimizations

    struct Matrix[Rows: int, Cols: int]:
        data: [f32; Rows * Cols]
    
    impl[R: int, C: int] Matrix[R, C]:
        fn multiply[K: int](&self, other: &Matrix[C, K]) -> Matrix[R, K]:
            var result = Matrix[R, K].zero()
            
            # Compiler knows all dimensions at compile time
            # Can unroll loops, optimize memory layout
            for i in 0..R:
                for j in 0..K:
                    for k in 0..C:
                        result.data[i*K + j] += 
                            self.data[i*C + k] * other.data[k*K + j]
            
            return result
    
    # Usage:
    let a = Matrix[4, 4].identity()
    let b = Matrix[4, 3].from_array(...)
    let c = a.multiply[3](&b)  # Result type: Matrix[4, 3]

Example 2: Buffer pre-allocation with known sizes

    fn parse_packet[MaxSize: int](data: &[u8]) -> Result[Packet, Error]:
        # Stack-allocated buffer, size known at compile time
        var fields: [Field; MaxSize]
        var count = 0
        
        # Compiler can optimize bounds checks away
        for byte in data:
            if count >= MaxSize:
                return Err(Error.TooManyFields)
            fields[count] = parse_field(byte)?
            count += 1
        
        return Ok(Packet { fields: fields[0..count] })
    
    # Different protocols use different specializations:
    let ip_packet = parse_packet[20](ip_data)?   # IPv4: max 20 fields
    let tcp_packet = parse_packet[40](tcp_data)? # TCP: max 40 fields

Example 3: Compile-time string processing

    const fn compute_hash(s: &str) -> u64:
        # Runs at compile time
        var hash: u64 = 0
        for c in s.bytes():
            hash = hash * 31 + c as u64
        return hash
    
    const API_KEY_HASH = compute_hash("MySecretAPIKey")  # Computed at compile time
    
    fn check_api_key(input: &str) -> bool:
        # Only the hash is in the binary, not the original key
        return compute_hash(input) == API_KEY_HASH

Performance Benefits
~~~~~~~~~~~~~~~~~~~~

Compile-time parameterization enables:

1. **Loop unrolling:** Fixed iteration counts can be fully unrolled
2. **Dead code elimination:** Compile-time conditionals remove unused branches
3. **SIMD optimization:** Generate vector instructions for known sizes
4. **Memory layout:** Optimal struct packing based on known sizes
5. **Constant propagation:** Intermediate computations folded away
6. **Specialization:** Different algorithms for different parameter values

All of this happens at compile time with zero runtime overhead. The generated 
code is as efficient as hand-written assembly for the specific parameters.

Integration with Teaching
~~~~~~~~~~~~~~~~~~~~~~~~~

For beginners, compile-time parameterization is introduced gradually:

1. **First exposure:** Fixed-size arrays `[T; N]` (N is a compile-time parameter)
2. **Basic usage:** Functions that take sized arrays
3. **Intermediate:** Writing parameterized functions for generic sizes
4. **Advanced:** Compile-time computation, conditional compilation, SIMD

The explainer system makes this concrete:

    $ pyritec --explain compile-time-param
    
    Compile-Time Parameters
    =======================
    
    Parameters in square brackets [N: int] are evaluated at compile time.
    The compiler creates a separate version of your function for each
    unique value of N that you use.
    
    Think of it like this:
      fn process[4](data) compiles to process_4(data)
      fn process[8](data) compiles to process_8(data)
    
    Each version can be optimized for its specific N value (loop unrolling,
    specialized algorithms, etc.).
    
    Cost: Zero runtime cost. Slight increase in binary size if many different
          values are used (each specialization adds code).

Comparison to Other Languages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  • **C++ templates:** Similar power, but clearer syntax and better errors
  • **Rust const generics:** Similar concept, extended with more parameter types
  • **Mojo parameters:** Direct inspiration, adapted to Pyrite's syntax
  • **Zig comptime:** Related but different (Pyrite uses explicit [N] syntax)

Pyrite's approach prioritizes readability (clear [] syntax) and teachability 
(explicit is better than implicit).

Comptime Execution
~~~~~~~~~~~~~~~~~~

Pyrite may introduce a keyword (like comptime or use const as above) to run 
arbitrary code at compile time. This can be more powerful than just const 
functions - it could allow conditional compilation logic in regular code. 

For instance, Zig allows things like:

    if(@import("builtin").os == .windows){
        // windows-specific code
    }else{
        // other OS code
    }

Pyrite might have a way to inspect compile-time configuration or types. For 
example, generating code based on type sizes or existence of implementations. 
This can eliminate the need for a separate preprocessor in many cases.

Generics vs Macros
~~~~~~~~~~~~~~~~~~

A lot of what one might use C++ templates or C preprocessor macros for can be 
handled by Pyrite's generics and const evaluation. However, there might still be 
scenarios where writing code that generates other code (metaprogramming) is 
useful. Pyrite could consider a hygienic macro system similar to Rust's (where 
you can write code that produces code in a controlled, compiler-integrated way). 
But this is advanced and can be tricky for beginners, so it might not be in the 
initial release. 

The philosophy is to try to achieve most metaprogramming needs via regular 
language constructs (like generics and const eval) before resorting to macros. If 
macros are introduced, they would likely be more like Rust's - i.e., part of the 
language's syntax and invoked in code, rather than a textual substitution like 
C's #define.

No Textual Preprocessor
~~~~~~~~~~~~~~~~~~~~~~~~

Unlike C, Pyrite doesn't rely on a textual preprocessor. This avoids a whole 
class of issues with macros and order of expansion and so on. Instead, features 
like conditional compilation, including other files, etc., are handled in more 
structured ways (via the module system or compile-time ifs). 

For example, Pyrite might have attributes or built-in conditionals for 
compilation target, so you could do @cfg(windows) to include some code only on 
Windows, akin to Rust's #[cfg(windows)]. The aim is to integrate these with the 
language grammar rather than as raw text substitution, making it safer and 
clearer.

Configuration Attributes (Feature Flags)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite provides comprehensive conditional compilation through @cfg attributes, 
enabling platform-specific code, optional features, and build configuration 
without textual preprocessing:

Platform Conditionals:

    @cfg(target_os = "windows")
    fn get_separator() -> char:
        return '\\'
    
    @cfg(target_os = "linux")
    fn get_separator() -> char:
        return '/'
    
    @cfg(target_os = "macos")
    fn get_separator() -> char:
        return '/'
    
    # Or combined:
    @cfg(any(target_os = "linux", target_os = "macos"))
    fn get_separator() -> char:
        return '/'

Architecture Conditionals:

    @cfg(target_arch = "x86_64")
    fn fast_crypto() -> Cipher:
        # Use AES-NI hardware instructions
        return AesNiCipher::new()
    
    @cfg(target_arch = "aarch64")
    fn fast_crypto() -> Cipher:
        # Use ARM crypto extensions
        return ArmCryptoChip::new()
    
    @cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))
    fn fast_crypto() -> Cipher:
        # Software fallback
        return SoftwareCipher::new()

Feature Flags:

    # Quarry.toml
    [features]
    default = ["json", "http", "observability"]
    json = ["serde"]
    http = ["http-client", "http-server"]
    observability = ["log", "trace", "metrics"]
    gpu = ["cuda"]
    minimal = []                     # No optional features
    
    # Code using features:
    @cfg(feature = "json")
    import json
    
    @cfg(feature = "gpu")
    import std::gpu
    
    @cfg(not(feature = "observability"))]
    fn log::info(msg: &str, fields: Map[String, Value]):
        # No-op when observability disabled (zero cost)
        pass

Build Configuration:

    @cfg(debug_assertions)
    fn expensive_check():
        # Only in debug builds
        validate_invariants()
    
    @cfg(release)
    fn expensive_check():
        # No-op in release builds
        pass

Combined Conditions:

    @cfg(all(target_os = "linux", target_arch = "x86_64", feature = "gpu"))]
    fn use_cuda():
        # Linux + x86_64 + GPU feature enabled
        ...
    
    @cfg(any(target_os = "windows", target_os = "macos"))]
    fn desktop_only():
        ...
    
    @cfg(not(target_pointer_width = "64"))]
    fn handle_32bit():
        ...

Available cfg Keys:

    target_os:            "windows", "linux", "macos", "ios", "android", "freebsd", "none" (bare-metal)
    target_arch:          "x86_64", "aarch64", "arm", "riscv64", "wasm32", etc.
    target_pointer_width: "32", "64"
    target_endian:        "little", "big"
    target_env:           "gnu", "msvc", "musl"
    feature:              User-defined feature flags
    debug_assertions:     true in debug builds
    test:                 true when running tests
    
Why Structured Conditionals Matter:

  • **Type-checked:** Conditions checked at compile time, not runtime
  • **No preprocessor pitfalls:** No macro expansion order issues
  • **IDE-friendly:** Grayed-out code for disabled configurations
  • **Explicit:** See exactly what code runs on what platforms
  • **Safe:** Can't create invalid combinations

This completes Pyrite's "no textual preprocessor" philosophy while providing all 
the power of conditional compilation in a type-safe, structured way.

Reflection and Code Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the future, Pyrite might allow limited compile-time reflection, such as 
iterating over the fields of a struct at compile time or generating trait 
implementations automatically (like deriving in Rust). This could be done via 
compile-time functions that use a reflection API, or via macro-like facilities. 
But again, this is advanced and can be added once the base language is solid.

By moving work to compile time, Pyrite enables optimizations and flexibility 
without hitting runtime performance. A classic example is building a big lookup 
table: you could compute it with a const loop at compile time rather than at 
program startup. Another example is complex computations for constants (like 
sin/cos tables, regex compilation to automata, etc.) done once at compile time. 
All of this follows the zero-cost ethos: if you can do it at compile time, you 
pay nothing at runtime except possibly a larger binary if data tables are 
generated.

Overall, compile-time execution and metaprogramming features in Pyrite are about 
empowering the programmer to let the compiler do more work (safely) so that the 
runtime work is less. But these features are optional and will typically be used 
by more advanced users or library authors; a beginner might not encounter them on 
day one.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Control Flow](06-control-flow.md)

**Next**: [Tooling: Quarry Build System](08-tooling.md)
