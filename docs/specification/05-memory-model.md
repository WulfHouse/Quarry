---
title: "Memory Management and Ownership"
section: 5
order: 5
---

# Memory Management and Ownership

One of Pyrite's cornerstone features is its approach to memory management: 
memory-safe by default with the ability to manually manage memory when necessary, 
all achieved without a garbage collector or runtime penalty. This section details 
Pyrite's ownership model, how allocation and deallocation work, and how we 
achieve safety without runtime overhead.

## 5.1 Ownership Model and RAII

Pyrite uses a system of ownership and lifetimes reminiscent of Rust's borrow 
checker to ensure memory safety at compile time. However, the aim is to present 
it in a simplified, more Pythonic way to make it easier for newcomers to grasp. 

The key idea is that every value in Pyrite is owned by some variable (or 
temporary), or is borrowed from one. There is always a clear owner responsible 
for freeing the value when it's no longer needed.

### Resource Ownership

When we say a variable owns an object, it means that variable is responsible for 
the object's lifetime. For stack-allocated values (those without an explicit heap 
allocation), ownership is simple: the value lives until the variable goes out of 
scope (end of the block or function), at which point it is automatically cleaned 
up (like a stack frame being popped). For heap-allocated resources, ownership 
means the owner variable is responsible for freeing that memory when it goes out 
of scope. 

In Pyrite, when an owner goes out of scope, the language will invoke code to 
release any resources it owned (memory, file handles, etc.). This is analogous to 
RAII in C++ and is how Rust's ownership model works as well. In practical terms, 
the Pyrite compiler will automatically insert calls to destructors or free 
functions at the end of scope for owned objects.

### Moves and Scope-Based Destruction

As mentioned in the type system, when an owning variable goes out of scope, 
Pyrite ensures the resource it owns is freed exactly once. For example, consider:

    {
        let data = Vector[int]([1,2,3])
        # ... use data ...
    }  # scope ends here
    # data is automatically freed here (memory reclaimed)

Inside the block, data owns a dynamic array allocated on the heap. When the block 
exits, because data is going out of scope, the compiler generates code to free 
the array's memory. This happens deterministically at the end of the scope, not 
at some unpredictable time in the future (there is no garbage collector pausing 
the program). 

The compile-time ownership analysis guarantees that in safe code, every 
allocation has a matching free at the right time: no leaks (each allocated 
resource has an owner that eventually frees it) and no double frees (because 
ownership prevents two owners of the same resource). If a resource needs to live 
longer than the scope in which it's created, you must explicitly move it to an 
outer scope (e.g. by returning it from a function or assigning it to a variable 
in an enclosing scope).

### Transfer of Ownership (Move semantics)

Ownership can be transferred by moving values between variables or across 
function calls. In Pyrite, assigning an object to a new variable or passing it as 
an argument will move it by default, unless the type is marked Copy. 

For instance:

    fn process_vector(lst: Vector[int]):
        print("Length:", lst.length())
        # lst goes out of scope here, so it will be freed automatically
    
    var myvec = Vector[int]([10,20,30])
    process_vector(myvec)  # moves ownership of myvec into the function
    # after this call, myvec is invalid (cannot be used) unless it was returned back

Here, process_vector takes a `Vector[int]` by value, meaning it will own the 
vector while in the function. When we call `process_vector(myvec)`, we move the 
vector into the function. The local variable `myvec` in the caller loses ownership - 
essentially, it's emptied. If we try to use `myvec` after that call, the compiler 
will give an error, because `myvec` no longer owns the vector (it was moved). 

Inside process_vector, `lst` is a new owner of the vector. When process_vector 
returns, `lst` goes out of scope, and thus the vector is freed at that point. This 
ensures the memory is freed exactly once overall. If we did want to use `myvec` 
again, process_vector would have to return it (transfer it back), or we would pass 
a reference instead of moving (see borrowing below). These move semantics prevent 
having two owners to the same heap allocation at the same time (which would cause 
double-free) and also prevent use-after-free: once a value is moved, any attempt 
to use the old handle is a compile-time error, so you can't accidentally use an 
object after it's been freed.

### Borrowing (References)

Often, you don't want to transfer ownership but merely lend access to some data 
to a function or another part of code. This is where borrowing comes in. Instead 
of passing objects by value, you can pass them by reference. In Pyrite, borrowing 
is achieved by using reference types (&T or &mut T). When you pass a reference, 
you are not giving up ownership; you are lending the object for a certain scope. 

There are two kinds of references:

  • Immutable references: &T - allow the borrower to read (but not modify) the 
    value.
  • Mutable references: &mut T - allow the borrower to modify the value, but you 
    can only have one active mutable borrow at a time.

The borrowing rules are: 
  1. You may have multiple immutable (&T) references to the same object at the 
     same time (read-only sharing is OK). 
  2. You may have at most one mutable (&mut T) reference to an object at a time, 
     and only if no immutable references exist to that object at that time 
     (exclusive write access).

These rules are enforced by the compiler and ensure there are no data races or 
conflicting accesses: you can't have two things trying to write to the same data 
simultaneously, and you can't read stale data while someone else is writing, etc. 
It's essentially Rust's borrowing rules enforced in Pyrite's context. 

For example:

    fn sum(numbers: &Vector[int]) -> int:
        var total = 0
        for n in numbers:  # iterate (read-only) through the vector
            total += n
        return total
    
    let nums = Vector[int]([5,6,7,8])
    let total = sum(&nums)  # pass an immutable reference to nums
    print(nums[0])  # nums can still be used here since only an immutable borrow was taken

In this code, sum takes `&Vector[int]`, meaning it borrows a read-only reference 
to a vector of ints. We call `sum(&nums)`, lending it our `nums` vector. Inside 
sum, it can read through the vector but not modify it. After sum returns, we still 
own `nums` in the caller, and we can continue using it. 

If sum tried to keep a reference to nums and return it or store it globally, the 
compiler would reject it because that could lead to a reference outliving its 
owner. Indeed, Pyrite's compiler internally tracks the lifetimes of references to 
ensure you don't end up with dangling pointers: a reference cannot outlive the 
variable it refers to. If you attempt something unsafe like returning a reference 
to a local variable, the compiler will give an error (e.g. "returning reference 
to local variable which will be dropped"). This way, dangling pointers are 
prevented at compile time - either you have ownership (and after scope end you 
can't use it), or you have a borrow (and the compiler ensures it doesn't outlast 
the owned value).

A mutable borrow &mut T works similarly but with the exclusivity rule. If you 
have passed &mut nums to a function, you cannot use nums in the caller during 
that time (the compiler treats nums as temporarily moved/locked for that scope). 
This prevents concurrent mutation issues. Data races (unsynchronized concurrent 
writes) are eliminated in safe Pyrite because you simply can't alias mutable 
references.

### Lifetimes (under the hood)

Pyrite's compiler uses a concept of lifetimes (much like Rust) to reason about 
how long references are valid. However, the goal is to keep this implicit for 
most users. In straightforward code, the compiler can infer lifetimes without any 
annotations - e.g. a reference passed into a function is valid until that 
function returns, etc., following simple rules. 

Only in advanced scenarios (like complex self-referential structures or writing 
low-level data structures) might the programmer need to help the compiler with 
lifetime annotations or tricks. The idea is that beginners can use references in 
the obvious ways without needing to know the theoretical details; if they violate 
the rules, they'll just get a compiler error that says something like "error: 
borrowed value does not live long enough" and perhaps an explanation, which guides 
them to adjust their code. Over time, this teaches the concept of lifetimes 
gently.

In essence, the ownership and borrowing system ensures memory safety: no 
use-after-free, no double free, no null dereference (in safe code). Each resource 
is owned by exactly one entity at a time, and the compiler checks any aliasing 
through references to ensure it's safe. This allows Pyrite to be memory-safe by 
default without needing a garbage collector. 

The cost is entirely at compile time (the compiler does the analysis); at 
runtime, you pay nothing for these safety guarantees. Developers coming from 
manual memory management will find that Pyrite provides the same control (you can 
decide exactly when something is freed by controlling its scope or explicitly 
freeing in unsafe code), while eliminating the most common errors through 
compile-time enforcement.

## 5.2 Manual Memory Management (Unsafe)

While the default ownership model covers most needs safely, Pyrite recognizes 
that systems programming sometimes requires manual control over memory 
allocation and layout, or interfacing with code that doesn't conform to Pyrite's 
safety rules. For those cases, Pyrite provides unsafe features that allow the 
programmer to step outside the compile-time guarantees. These must be used with 
care and are not intended for everyday programming - they are escape hatches for 
special scenarios. 

Crucially, unsafe operations are explicitly marked and isolated so that the 
boundaries between safe and unsafe code are clear. Safe code cannot be 
compromised by unsafe code unless you explicitly opt into it.

### Unsafe Blocks

To perform an operation that the compiler cannot verify as safe, you must enclose 
it in an unsafe block (or be inside an unsafe fn). This signals to the compiler 
(and to readers of the code) that "here be dragons" - the normal guarantees are 
suspended and the programmer takes responsibility for upholding safety manually. 

For example:

    unsafe:
        let p = malloc(100) as *mut u8
        # allocate 100 bytes on heap, returns a raw pointer
        if p == null:
            abort("Out of memory")
        p[0] = 123  # write to the allocated memory
        free(p)     # free the memory

In this code, we explicitly called a malloc function (from, say, the C standard 
library or Pyrite's std) to allocate raw memory, which returns a *mut u8 (raw 
pointer to byte). We then check for null and use p by writing to it and finally 
freeing it. All of this must be in unsafe because raw pointer manipulation and 
manual memory free are not checked by the compiler - it's up to us to ensure 
correctness. 

Inside an unsafe block, you can do things that are normally forbidden, such as 
dereferencing raw pointers, performing pointer arithmetic, casting between 
incompatible pointer types, or calling foreign functions that the compiler cannot 
guarantee to be safe. Essentially, the compiler "trusts" you within an unsafe 
block.

However, note that even in an unsafe context, not everything is allowed: the 
basic language rules still apply (you can't magically treat an int as a float 
without a cast, for example, and you can't violate the fundamentals of the type 
system). The borrow checker also still works for references - if you use normal 
&T references inside unsafe, the compiler will enforce borrowing rules unless you 
intentionally convert them to raw pointers to circumvent the rules. The unsafe 
keyword does not turn off all checks; it only permits the specific dangerous 
operations that are otherwise disallowed (like raw pointer dereference or calling 
an unsafe function). This means even inside unsafe, you get as much help from the 
compiler as possible.

### Explicit Allocation/Free

Pyrite's standard library will likely include functions analogous to C's malloc, 
free, and realloc for raw memory management (or it will allow you to call C's 
versions easily via FFI). These are considered unsafe to use because they deal 
with raw pointers and unstructured memory. A programmer who wants to manually 
manage a memory region might use these to allocate a buffer and then manipulate 
it. 

Typically, one would encapsulate such allocations in a safe abstraction. For 
example, you might implement a custom data structure by using malloc to get a 
buffer and then constructing elements in place. Pyrite encourages isolating this 
kind of code: write the low-level memory manipulation inside a module, mark it 
unsafe, thoroughly test it, and then expose a safe API (much like how one would 
write portions of a Rust library in unsafe internally but present a safe 
interface). This way the majority of the codebase remains safe Pyrite, and only a 
tiny core is unsafe.

### Unsafe Data Structures and Type Punning

In some low-level scenarios, you may need to reinterpret bits of memory in a 
different type (type punning), or use a union to overlay different 
representations. Pyrite allows these in unsafe code. For instance, you could cast 
a *u8 to a *MyStruct after ensuring the memory is aligned and sized correctly. Or 
use a union as defined earlier: reading from a union field is only safe if you 
know that field is the one last written. If you misuse it, that's a bug the 
compiler can't catch in unsafe code. 

Pyrite's philosophy is that any trick you can do in C to optimize or interface 
with hardware, you can do in Pyrite as well - but you must opt into unsafe and 
thus you accept the responsibility. The set of operations that are considered 
undefined behavior (and thus must be kept within unsafe and done correctly) 
include things like dereferencing invalid pointers, misaligning data, creating 
data races, etc., similar to Rust's model of what's not allowed even in unsafe.

### Opting Out of the Borrow Checker

There are cases where you might need to circumvent the borrowing rules. For 
example, you might have an API that requires two mutable pointers to the same 
data (maybe for some algorithm that treats the data in chunks). In safe Pyrite 
this is impossible, but in unsafe you could do it. 

For instance:

    fn give_two_aliases(x: &mut int):
        unsafe:
            let p1 = x as *mut int
            let p2 = x as *mut int
            # Now p1 and p2 are two mutable aliases to the same integer
            *p1 = 5
            *p2 = 6  # this is undefined behavior if used concurrently

Here we took a mutable reference x (which we got in a safe way from the function 
parameter) and cast it to raw pointers p1 and p2. We thereby created two aliases 
to the same data and used them. This is not allowed in safe code (the borrow 
checker would have prevented it), which is why we had to be in unsafe.

If this code runs in a single-threaded context sequentially, it will simply set 
the integer to 6. But if one tried to do such things concurrently, it could cause 
a data race - the compiler won't help you here because you turned off the checks. 
This example is contrived, but it illustrates that unsafe can be used to 
temporarily opt out of the strict rules. Any invariants you break in unsafe code, 
you as the programmer must ensure they don't violate overall program safety 
(perhaps through other means like synchronization).

In summary, unsafe is a tool of last resort. Pyrite provides it so that you can 
do things like manual memory allocation, low-level fiddling, interfacing with 
hardware or foreign libraries, etc., which are indispensable for systems 
programming. But all unsafe actions must be explicitly marked, and safe and 
unsafe code are kept separated as much as possible. This design mirrors Rust's 
approach to unsafe: you contain the "unsafe mess" in small, well-audited 
portions. By doing so, you get the benefit that the bulk of your program is 
verified by the compiler to be free of memory errors, and you only have to reason 
deeply about the unsafe parts.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Types and Type System](04-type-system.md)

**Next**: [Control Flow](06-control-flow.md)
