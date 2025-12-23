---
title: "Syntax Overview"
section: 3
order: 3
---

# Syntax Overview

Pyrite's syntax is designed to be familiar to Python users while operating in a 
compiled, statically-typed setting. This section describes the basic lexical 
structure and grammar of Pyrite code.

## 3.1 Lexical Elements and Formatting

### Whitespace and Indentation

Pyrite uses indentation-based block structure, similar to Python. Blocks of code 
(such as the body of a function, loop, or conditional) are defined by their 
indent level rather than explicit braces. Consistent indentation is required; a 
mix of tab and spaces or inconsistent indent widths will be a compile-time error. 

This design ensures that the visual layout of the code always matches its logical 
structure - a feature proven by Python to reduce bugs and improve clarity. 

For example: 

    if x > 0:
        print("Positive")
    elif x < 0:
        print("Negative")
    else:
        print("Zero")

In this snippet, the bodies of the if and else branches are determined by 
indentation. The layout makes the flow obvious. (If the indentation were 
misaligned, the compiler would reject it.) This contributes to code that is easy 
to read and reason about.

### End-of-Line Termination

Statements are terminated by newline characters. Pyrite does not require a 
semicolon at the end of each statement. You typically put one statement per line. 
(An optional semicolon may be allowed if multiple statements are written on a 
single line or to explicitly terminate a statement, but this is rarely needed in 
practice.) 

This follows Python's convention and avoids cluttering code with unnecessary 
punctuation. Long expressions can be continued across lines either by using a 
backslash or (more commonly) by open parentheses/brackets, similar to Python.

### Comments

Pyrite supports both single-line and multi-line comments. Single-line comments 
start with # and continue to the end of the line (just like Python). 

For example: 

    x = 5  # this is a single-line comment

Multi-line (block) comments can be written by enclosing the text in triple quotes 
""" ... """ (again, similar to Python's docstring style). Alternatively, C-style 
/* ... */ block comments may be supported for convenience with certain tools, but 
the idiomatic way is to use """ for multi-line documentation comments. 

By convention, a triple-quoted string literal that is not assigned to any 
variable (placed standalone in code) can serve as a documentation comment for the 
following code element.

### Identifiers

Identifiers (names for variables, functions, types, etc.) may consist of letters 
(including Unicode letters), digits, and underscores, but must not begin with a 
digit. Pyrite is case-sensitive, so for example foo, Foo, and FOO are distinct 
identifiers. 

By convention, snake_case is used for variable and function names (following 
Python's style), and CamelCase is used for type names (e.g. struct or enum names, 
similar to Rust and Zig naming conventions). Identifiers cannot clash with 
reserved keywords (the compiler will error if you try to name a variable if or 
while, for instance).

### Keywords

Pyrite reserves certain keywords for language constructs. Many keywords are 
borrowed from Python for familiarity. For example: fn (for function definition), 
let and var (for variable binding, see mutability below), if, elif, else, for, 
while, break, continue, return, struct, enum, union, true, false, None, unsafe, 
etc. 

Note that we use `fn` to define functions (similar to Rust's `fn` or Swift's `func`) 
instead of Python's `def`. This design choice serves several important purposes:

**Rationale for `fn` vs `def`:**
- **Distinction from Python**: `fn` clearly signals that this is a compiled, 
  statically-typed language, not interpreted Python code
- **Rust familiarity**: Rust developers will immediately recognize `fn` and feel 
  at home with Pyrite's syntax
- **Compiled language identity**: Makes Pyrite feel like a systems programming 
  language from the first line of code
- **Brevity**: Shorter than "function" keyword while being more distinctive than "def"
- **Teaching value**: Helps beginners understand that Pyrite functions are different 
  from Python functions (compiled, typed, zero-cost)

Overall, the goal is a light syntax reminiscent of Python, but with some tweaks to 
suit a compiled language. The `fn` keyword is one of those intentional distinctions 
that helps set expectations about Pyrite's nature as a systems programming language.

### Literals

Pyrite supports various literal forms:

• Integer literals can be written in decimal (e.g. 123), hexadecimal (prefix 0x, 
  e.g. 0x7B), binary (prefix 0b), or octal (prefix 0o). You can include 
  underscores in numeric literals for readability (e.g. 1_000_000 for one 
  million). By default, an unsuffixed integer literal is inferred to an 
  appropriate integer type based on context (or defaults to the type int if 
  there's no context). Pyrite does not implicitly widen or narrow integers without 
  a cast - arithmetic on mixed integer types either requires an explicit cast or 
  will use an automatic promotion to a larger type when well-defined (similar to 
  C's usual arithmetic conversions but simpler, since Pyrite discourages implicit 
  narrowing). Integer overflow is handled by the build mode: in debug builds, 
  arithmetic overflow is checked and will raise an error or panic if it occurs, 
  whereas in optimized release builds it will wrap around using two's complement 
  arithmetic by default (with an option to enable checked arithmetic if desired). 
  This follows Rust and Zig's approach of having overflow checks in debug mode 
  but zero overhead in release unless explicitly requested for safety.

• Floating-point literals use standard decimal or scientific notation (e.g. 3.14, 
  1e-9). By default a floating literal like 3.0 is inferred as a double-precision 
  64-bit float (f64) for precision, unless a context or suffix indicates 
  otherwise. A suffix (like 1.2f32) can denote a specific type. No implicit 
  conversion between floats and ints occurs - an explicit cast is required to 
  convert between numeric types, to avoid accidental loss of data.

• Boolean literals are written as true and false. Only booleans can be used in 
  conditional contexts (if, while, etc.); there is no automatic truthiness 
  conversion from other types (e.g. an integer 0 vs non-zero) - this prevents 
  certain classes of bugs (like writing if (x = 0) in C when == was meant). 
  Instead, you must explicitly compare or convert to bool if needed. Logical 
  operations use the keywords and, or, not (in place of C's &&, ||, !) for 
  readability, with short-circuit evaluation semantics identical to Python (e.g. 
  A and B evaluates B only if A was true).

• Character and string literals: A char in Pyrite represents a single Unicode 
  code point (likely a 32-bit value, like Rust's char). Character literals are 
  written with single quotes, e.g. 'A'. Text strings are handled by an immutable 
  string type (e.g. String), with string literals written in double quotes, e.g. 
  "Hello, world". Standard escape sequences are supported within strings (\n, \t, 
  \", etc.). Strings in Pyrite are sequences of Unicode characters and are 
  immutable (their content cannot be changed once created). To modify text, one 
  would use a separate mutable buffer type or convert a string to a mutable array 
  of chars. Concatenating string literals at compile time is allowed (adjacent 
  string literals are merged, or a special operator can be evaluated at compile 
  time), but runtime string concatenation will allocate new memory. Pyrite avoids 
  hidden heap allocations by default, so using + to concatenate two strings will 
  likely allocate behind the scenes - the language encourages using an explicit 
  string builder or formatting utility for efficiency when building strings in a 
  loop, for example. (In fact, Pyrite may only allow string + in a context where 
  it can be evaluated at compile time, to avoid misleading performance costs.)

• The None literal: None represents a null or absent value. This is similar to 
  Python's None or to the concept of null/nullptr in other languages, but in 
  Pyrite it is used in a controlled way: primarily as the value of an optional 
  type or sentinel. Pyrite does not have null pointers by default; None is 
  actually an instance of an `Option[T]` type (see composite types below). You 
  cannot assign None to an arbitrary variable unless that variable's type permits 
  it (e.g. `Option[T]`). This design prevents null-pointer dereferences in safe 
  code - you can only get a "null" if you explicitly use an optional, and you 
  must check for None before using the value.

## 3.2 Code Structure

### Modules and Imports

Pyrite source code is organized into modules, typically one module per file. 
Every source file is a module, and modules can import other modules. The syntax 
for importing is Python-like: the `import` keyword is used.

**Import Syntax:**

    # Basic import
    import math
    
    # Qualified import (package hierarchy)
    import graphics.image
    
    # Selective import (if supported)
    import math::{sin, cos, tan}
    
    # Import with alias
    import graphics.image as img
    
    # Re-export (make imported items available to consumers)
    pub import std::collections
    
    # Wildcard import (if supported, with warnings - use sparingly)
    import std::io::*  # Imports all items from std::io

Imported module names act as namespaces, so names defined in `math` would be 
accessed with a `math.` prefix (e.g. `math.sin(x)`). 

Pyrite supports a simple package system that allows grouping modules into package 
hierarchies using dot notation (for example, `import graphics.image` would import 
the `image` sub-module of the `graphics` package, assuming a directory structure to 
match). The exact details of module lookup (how the compiler finds 
`graphics/image.pyrite` or similar) are defined by the compiler and build system, 
but cyclic imports are either disallowed or handled gracefully (the compiler will 
detect circular dependencies and produce an error or resolution order). Module 
imports are resolved at compile time; there is no dynamic importing at runtime by 
default.

**Note**: The exact set of supported import forms (selective imports, aliases, 
re-exports, wildcards) will be finalized during implementation. The syntax shown 
above represents the intended design.

### Entry Point

Like C (and Rust), Pyrite programs start execution from a special main function. 
A Pyrite program must have exactly one function defined as fn main(): ... which 
serves as the entry point. The main function takes no arguments (or, 
alternatively, it may take an array of strings as an argument to represent 
command-line arguments, similar to argv in C, depending on the final design) and 
returns an integer as an exit code (conventionally 0 for success). 

For example, a minimal program might be:

    fn main():
        print("Hello from Pyrite!")
        return 0

If no explicit return is given in main, reaching the end of the function 
implicitly returns 0. Pyrite's build system will produce an executable that 
begins at main. There is no requirement for a runtime library to start up (unlike 
languages that need a VM initialization); Pyrite's startup is as minimal as C's - 
  it just calls main.

### File Extension and Compilation Units

(By convention, assume Pyrite source files use a .pyrite extension, though 
this is not a language rule per se.) Each file can be compiled as part of a 
project. The compiler and package manager handle how multiple modules are linked 
together into an application or library. A package in Pyrite might consist of 
many modules, with a manifest for dependencies (similar to Rust's Cargo or Zig's 
build system). 

However, the specifics of the build and package system are part of the ecosystem 
rather than the core language syntax, so they are not detailed here. The language 
ensures that separate modules have explicit imports for any names they use from 
other modules (no implicit global scope), which aids clarity and compiler 
optimization.

---

**Part of**: [Pyrite Language Specification](../SSOT.md)

**Previous**: [Compiler Diagnostics and Error Messages](02-diagnostics.md)

**Next**: [Types and Type System](04-type-system.md)
