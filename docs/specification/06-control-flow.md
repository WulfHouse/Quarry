---
title: "Control Flow"
section: 6
order: 6
---

# Control Flow

================================================================================

Pyrite's control flow structures combine Python's simplicity with C's low-level 
capabilities. All the usual constructs are present (conditionals, loops, pattern 
matching, etc.) with a syntax leaning towards Python's readability. There are 
also some additions inspired by modern languages to handle errors and pattern 
matching in a safer way.

6.1 Conditionals
--------------------------------------------------------------------------------

The if statement in Pyrite is similar to Python's. For example:

    if condition:
        # block of code if condition is true
    elif other_condition:
        # block if the first condition is false, second is true
    else:
        # block if all above conditions are false

The elif and else clauses are optional (you can have just an if, or an if with 
multiple elifs, etc.). The condition in an if must be of type bool - there is no 
implicit conversion from integers or other types to boolean. For instance, if x: 
is not allowed if x is an integer; you must write if x != 0: or some explicit 
check. This avoids ambiguity and mistakes. 

As mentioned earlier, logical operators are the words and, or, not, which also 
helps readability (e.g. if x > 0 and not done:). Parentheses around the 
condition are optional (you can write if (x > 0): if you want, but it's not 
required).

Pyrite also offers a ternary conditional expression (similar to Python's): x if 
condition else y. This allows inline conditional logic. For example: max_val = a 
if a > b else b will set max_val to the greater of a or b. This is purely an 
expression and does not use a question-mark like C; it uses the Python-style 
syntax for familiarity.

6.2 Loops
--------------------------------------------------------------------------------

Pyrite provides both while loops and for loops.

While Loop
~~~~~~~~~~

The syntax is straightforward:

    while condition:
        # loop body
        # (use `break` to exit early, `continue` to skip to next iteration)

The loop evaluates the condition (which must be a boolean) at the start of each 
iteration; if true, it executes the body, then repeats. If false, it exits the 
loop. Inside the loop, you can use break to immediately exit the loop, or 
continue to skip to the next iteration (re-checking the condition). This works 
just like in C/Python.

For Loop
~~~~~~~~

Instead of C's traditional for (init; cond; step) loop, Pyrite adopts a 
high-level iteration loop similar to Python's for ... in .... The Pyrite for loop 
iterates over any iterator or range of values. 

For example:

    for item in collection:
        print(item)

This will iterate through each element of collection (which could be, say, a 
`Vector` or an `Array`). Under the hood, collection should be something that 
provides an iterator (likely by implementing a trait in the standard library), 
but the syntax is clean and abstracted. 

If you need a numeric loop, you could iterate over a range of numbers. Pyrite 
will likely have a range type or literal. For instance, for i in 0..10: might 
iterate i from 0 up to 9 (if using a Rust-like range syntax), or for i in 
range(0, 10): might be used (if adopting Python's range() function style). The 
exact syntax is to be determined, but the concept is that you don't manually 
write index increment logic; you express what set of values to iterate over, and 
the language handles the progression.

You can also loop directly over a fixed-size array or any iterable. If you need 
the index as well, typical solutions include an enumerate iterator in the 
library, or a C-style loop using while with an index. Pyrite chooses to 
prioritize clarity and safety (no off-by-one errors from manual indexing if you 
use the high-level loop). As with while, break can exit the loop early and 
continue goes to the next iteration.

Example:

    let nums = Vector[int]([10,20,30])
    for n in nums:
        print(n)

This would print each number in the vector. If nums was empty, the loop would 
simply not execute at all (0 iterations). The loop construct abstracts away the 
indexing and bounds-checking (the iterator will handle that safely).

6.3 Pattern Matching
--------------------------------------------------------------------------------

Borrowing a powerful feature from Rust (and many functional languages), Pyrite 
includes a match construct for pattern matching on values, particularly on enums 
and other algebraic data types. Pattern matching allows you to branch on the 
structure of a value in a concise way, and the compiler ensures you handle all 
possible cases.

Syntax:

    match value:
        pattern1:
            # code for when value matches pattern1
        pattern2 if guard:
            # code for pattern2 with an additional boolean guard condition
        _:
            # default case if no other pattern matches

Each pattern: is like a case arm. The special pattern _ is a wildcard that 
matches anything (and is used as a default or catch-all). The if guard after a 
pattern is optional and allows an extra boolean condition to refine the match.

For example, imagine an enum result type:

    match result:
        Ok(val):
            print("Success:", val)
        Err(err_code):
            print("Error:", err_code)

Here result is matched against two patterns: Ok(val) and Err(err_code), which 
correspond to the variants of a Result enum. If result is an Ok, the val inside 
will be bound to the variable val and the success case code runs; if it's an Err, 
the err_code is bound and the error case code runs. The compiler will insist that 
this match is exhaustive - if Result had another variant, or if we omitted the 
Err case, it would be a compile error to have a non-exhaustive match (unless we 
include a wildcard _ to cover "all other cases"). This exhaustiveness checking 
helps prevent logic errors by ensuring you've considered every possible variant of 
an enum.

Pattern matching isn't limited to enums. You can match on basic types (e.g., 
different specific integers or strings), on tuples, on struct destructuring, etc. 

**Comprehensive Pattern Matching Examples:**

Enum matching:
    match result:
        Ok(val):
            process(val)
        Err(e):
            handle_error(e)

Integer matching with multiple patterns:
    match x:
        0:
            print("x is zero")
        1 | 2:
            print("x is 1 or 2")
        3 | 4 | 5:
            print("x is 3, 4, or 5")
        _:
            print("x is something else")

Guard clauses (additional conditions):
    match x:
        n if n > 0:
            print("positive")
        n if n < 0:
            print("negative")
        _:
            print("zero")

Tuple destructuring:
    match point:
        (0, y):
            print("Point lies on the Y axis at", y)
        (x, 0):
            print("Point lies on the X axis at", x)
        (x, y):
            print("Point at", x, ",", y)

Struct destructuring:
    match user:
        User{name: "admin", role: Role::Admin}:
            grant_access()
        User{name, role: Role::User}:
            print("User:", name)
        User{name, role: Role::Guest}:
            deny_access()
        _:
            print("Unknown user type")

This allows very expressive checking of complex conditions in a declarative style. 
It often leads to clearer code than a sequence of if/elif especially when dealing 
with structured data. New users can initially ignore match and use if/else, but 
as they become more comfortable, match becomes a potent tool that can make code 
more readable and robust (since the compiler checks that all cases are handled).

**Exhaustiveness Checking:**

The compiler ensures that all possible patterns are handled. If you omit a case, 
you'll get a compile error:

    match result:
        Ok(val):
            process(val)
        # ERROR: missing Err case - match is not exhaustive

You can use `_` (wildcard) to handle all remaining cases:

    match value:
        1 | 2 | 3:
            print("small")
        _:
            print("other")

6.4 Function Calls and Operators
--------------------------------------------------------------------------------

Function Calls
~~~~~~~~~~~~~~

Functions are called using parentheses and a comma-separated list of arguments, 
just like in most languages. Example: result = foo(a, b). There's no quirk like 
Python's mandatory self parameter for methods - method calls are handled 
differently (see Advanced Features on methods), and regular function calls are 
straightforward. Pyrite supports positional arguments and may support keyword 
arguments for functions (to improve readability for some calls), though that's a 
design choice beyond the core syntax.

Expressions and Operators
~~~~~~~~~~~~~~~~~~~~~~~~~~

Pyrite supports the typical arithmetic and comparison operators: +, -, *, /, % 
for arithmetic; ==, !=, <, <=, >, >= for comparisons. Operator precedence is 
similar to C/Python (for example, * and / bind tighter than + and -). Parentheses 
can be used to override precedence or for clarity. 

One important design decision in Pyrite is that it does not allow user-defined 
operator overloading by default. That is, you cannot arbitrarily change what + 
does for your custom type in the language itself, to avoid the pitfalls of hidden 
control flow or surprising performance costs. For built-in numeric types, + is 
defined as usual addition. The language might also allow + for certain standard 
library types (like concatenating strings or adding two same-typed vectors) for 
convenience, but these are well-defined by the language/standard library. 

Beyond those cases, users should define ordinary functions or methods (e.g. use a 
method like .add() or a trait implementation, see advanced section) to implement 
custom operations. This way, seeing an operator in code is never misleading - a + 
b is either basic arithmetic or a documented library-defined overload (not an 
arbitrary function call). Future versions of Pyrite might introduce operator 
overloading via traits (similar to Rust's Add trait) in a controlled manner, but 
initially, to keep things simple, we assume no custom operator overloading. This 
ensures that, for example, a + b is always O(1) for fundamental types and won't 
secretly do something like allocate memory or call a complex routine without the 
programmer realizing it.

Order of Evaluation
~~~~~~~~~~~~~~~~~~~

Pyrite guarantees left-to-right evaluation order for all expressions and function 
arguments. This eliminates an entire class of undefined behavior present in C/C++ 
and makes code behavior predictable and debuggable.

For example:
    
    fn side_effect() -> int:
        print("Called!")
        return 5
    
    fn process(a: int, b: int, c: int):
        pass
    
    process(side_effect(), side_effect(), side_effect())
    # Guaranteed to print "Called!" three times in order
    # Arguments evaluated left-to-right: first, second, third

This deterministic evaluation order:
  • Makes debugging easier (predictable execution flow)
  • Prevents surprising behavior with side effects
  • Aligns with Python's predictability expectations
  • Costs nothing in performance (compilers already choose some order)
  • Removes cognitive load from developers

While it's still good practice to avoid complex expressions with multiple side 
effects, Pyrite ensures that when they occur, behavior is consistent and 
understandable.

6.5 Error Handling
--------------------------------------------------------------------------------

Rather than using exceptions for error handling, Pyrite opts for a more explicit, 
type-based approach that avoids hidden control flow and runtime overhead. There 
are no throw or try/catch statements in the traditional sense (as in Java or 
C++). Instead, Pyrite encourages the use of result types (like the `Result[T, E]` 
enum described earlier) and provides syntactic sugar to make handling them 
ergonomic. This approach is influenced by Rust and Zig.

Result Type
~~~~~~~~~~~

If a function can fail (for example, a function that reads a file might fail if 
the file is not found), the function's return type is a `Result[T, E]`. For 
example: `fn read_config(path: String) -> Result[Config, IOError]` would 
indicate that the function returns either a `Config` object on success or an 
`IOError` on failure.

The caller of such a function is forced by the type system to handle the 
possibility of error - either by checking which variant it is (via pattern 
matching or an if), or by propagating the error upward.

The ? Operator
~~~~~~~~~~~~~~

To avoid boilerplate when you have many fallible calls, Pyrite provides the `?` 
operator (similar to Rust's `?`). The `?` operator performs early return on 
error: if the `Result` is `Err(e)`, it returns that error from the current 
function; if it's `Ok(value)`, it unwraps the value and continues execution.

For example:

    fn parse_number(s: &str) -> Result[int, ParseError]:
        let num = s.parse()?  # Returns early if Err, unwraps if Ok
        return Ok(num * 2)
    
    fn load_config(path: String) -> Result[Config, IOError]:
        let file = File.open(path)?  # If open fails, propagate error up
        let data = file.read_all()?  # If read fails, propagate error
        return parse_config(data)    # parse_config returns Result[Config, IOError]

In this code, `File.open(path)?` means: call `File.open(path)` which returns a 
`Result[File, IOError]`. If it returns `Ok(file)`, then `file` is assigned and 
execution continues. If it returns `Err(e)`, then the `?` operator returns that 
error from the current function (`load_config`), effectively propagating the 
error to the caller. This happens without unwinding the stack or throwing an 
exception; it's a simple jump out of the function, which the compiler implements 
as needed (essentially equivalent to `match result: Ok(v) => v, Err(e) => return Err(e)`).

The `?` operator makes error propagation almost as concise as exceptions but with 
none of the hidden cost or control flow issues (you can statically see which 
functions may return errors by their type, and there's no unwinding at runtime - 
it's just code that checks and returns).

Explicit Error Handling with match
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a function wants to handle errors instead of propagating, it can use `match` 
to inspect the `Result`:

    fn process_file(path: String) -> Result[(), Error]:
        match File.open(path):
            Ok(file):
                process_file_contents(file)
                Ok(())
            Err(e):
                print("Could not open file:", e)
                Err(e)  # or handle it somehow and return Ok(())

Optional: try/catch Sugar
~~~~~~~~~~~~~~~~~~~~~~~~~~

For Python familiarity, Pyrite may provide `try`/`catch` syntax as sugar over 
`Result` types. This would be compile-time desugaring, not exception-based:

    # Optional syntax (if implemented)
    try:
        let file = File.open(path)?
        let data = file.read_all()?
        process_data(data)
    catch e: IOError:
        handle_error(e)
    
    # Desugars to:
    match File.open(path):
        Ok(file):
            match file.read_all():
                Ok(data):
                    process_data(data)
                Err(e):
                    handle_error(e)
        Err(e):
            handle_error(e)

**Note**: If `try`/`catch` syntax is provided, it is purely syntactic sugar over 
`Result` types. There are no true exceptions in Pyrite - all error handling is 
explicit and type-checked at compile time.

No Exceptions
~~~~~~~~~~~~~

By not having language-level exceptions, Pyrite avoids the pitfalls of hidden 
control flow (where any function call might throw and skip the rest of your code 
unless you catch it). This means when you read Pyrite code, you don't have to 
worry that foo() will suddenly jump out to some handler unless it's explicitly 
written to do so via the Result mechanism. This determinism is important for 
reasoning about performance and correctness (no surprise performance hits from 
unwinding stack frames, etc.). In performance-critical or safety-critical 
systems, unpredictable control flow is undesirable. 

Pyrite's error handling is therefore opt-in at each call site: you either 
explicitly propagate or handle the error. There is talk of possibly a catch 
expression that can wrap a whole block and turn any error into a result, but that 
would just be a convenience that expands to checking each result.

Defer Statement
~~~~~~~~~~~~~~~

For cases where you need to guarantee code runs at scope exit (regardless of 
error or return path), Pyrite provides a defer statement (inspired by Go and Zig). 
The defer statement schedules a block of code to execute when the enclosing scope 
exits, making cleanup patterns explicit and guaranteed.

Syntax:
    
    fn process_file(path: String) -> Result[(), Error]:
        let handle = open_resource(path)?
        defer:
            close_resource(handle)  # Always runs when function exits
        
        # ... work with handle ...
        # If any errors occur and propagate, defer block still runs
        return Ok(())

Multiple defer statements execute in reverse order (last-deferred runs first):

    fn nested_cleanup():
        defer:
            print("Third")
        defer:
            print("Second")
        defer:
            print("First")
        # Prints: First, Second, Third

When to use defer vs RAII:
  • RAII: Preferred for resource management (files, locks, memory)
    Types with destructors automatically clean up
  
  • defer: Used when RAII is inconvenient:
    - C FFI resources without Pyrite wrappers
    - Multiple cleanup steps that don't fit one destructor
    - Explicit sequencing of cleanup operations
    - Temporary debugging/logging at scope exit

Example with C interop:

    fn use_c_library() -> Result[(), Error]:
        let ptr = unsafe { c_malloc(1024) }
        defer:
            unsafe { c_free(ptr) }
        
        # Use ptr safely...
        # Guaranteed cleanup even if errors occur

Benefits:
  • Beginners love "cleanup always runs" guarantee
  • Explicit and visible (no hidden destructor behavior)
  • Complements RAII for procedural-style code
  • Zero runtime cost (expanded at compile time)

Note: defer is part of Core Pyrite - it's simple enough for beginners and powerful 
enough for systems programming. While RAII handles most cleanup, defer provides 
an escape hatch for cases where ownership-based cleanup is awkward.

With Statement
~~~~~~~~~~~~~~

To provide familiar resource management patterns for Python developers, Pyrite 
includes a with statement that desugars to try + defer at compile time. This is 
pure syntactic sugar with zero runtime cost.

Syntax:

    with file = File.open("config.txt")?:
        for line in file.lines():
            process(line)
    # file.close() called automatically via defer

The with statement combines three operations:
  1. Bind the resource (let file = ...)
  2. Unwrap the Result (? operator)
  3. Register cleanup (defer: file.close())

Equivalent desugaring:

    let file = File.open("config.txt")?
    defer:
        file.close()
    for line in file.lines():
        process(line)

Multiple resources:

    with conn = Database.connect(url)?:
        with tx = conn.begin_transaction()?:
            tx.execute(query)
            tx.commit()
    # tx.rollback() if not committed, conn.close() - in reverse order

Requirements for use with `with`:
  • Type must implement the Closeable trait (or provide a close() method)
  • Expression must return a Result[T, E] where T: Closeable

Benefits:
  • Familiar to Python developers (reduces friction)
  • Zero cost (desugars to defer)
  • Explicit (you see the try, you see the with)
  • Teaches ownership (compiler shows desugared form with --explain)

When to use:
  • Opening files, network connections, database transactions
  • Acquiring locks (Mutex, RwLock)
  • Any resource with a clear "acquire → use → release" pattern

Teaching path:
  1. Week 1: Use with for familiar file operations
  2. Week 2: Learn that with = try + defer (show desugaring)
  3. Week 3+: Use defer directly when more control needed

The with statement is part of Core Pyrite - it's the ergonomic entry point to 
resource management that later teaches the underlying mechanisms.

In summary, Pyrite's approach to errors is to use the type system to make them 
explicit. This results in more robust code because you can't accidentally ignore 
an error (the compiler will warn or error if you don't use a Result you 
received). And you avoid the runtime cost of exceptions. This aligns with the 
overall philosophy of explicitness and zero-cost abstractions: error handling in 
Pyrite is as efficient as simple conditional checks and jumps (no stack unwinding 
machinery). It's also predictable - you know which functions might fail (it's in 
their type) and you handle it in-line with your logic.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Memory Management and Ownership](05-memory-model.md)

**Next**: [Advanced Features (Traits, Generics, and More)](07-advanced-features.md)
