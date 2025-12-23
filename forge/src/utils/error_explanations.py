"""Error code explanations for Pyrite"""

ERROR_EXPLANATIONS = {
    "P0234": {
        "title": "cannot use moved value",
        "description": """
This error occurs when you try to use a value after ownership has been
transferred (moved) to another variable or function.

In Pyrite, when you pass a non-Copy value to a function or assign it to
another variable, ownership is transferred. The original variable can no
longer be used because it no longer owns the value.
        """,
        "examples": {
            "wrong": """
fn main():
    let data = List[int]([1, 2, 3])
    process(data)        # data is moved here
    print(data.length()) # ERROR: can't use data anymore
            """,
            "correct1": """
fn main():
    let data = List[int]([1, 2, 3])
    process(&data)       # Pass a reference instead
    print(data.length()) # OK: data is still owned here
            """,
            "correct2": """
fn main():
    let data = List[int]([1, 2, 3])
    process(data.clone()) # Clone the data
    print(data.length())  # OK: original data still owned
            """,
            "correct3": """
fn main():
    let data = List[int]([1, 2, 3])
    process(data)         # Move is OK
    # Don't use data after this point
            """
        },
        "notes": """
Why does Pyrite do this?

Ownership tracking prevents common memory bugs:
- Use-after-free: Can't use memory after it's been freed
- Double-free: Can't free the same memory twice  
- Memory leaks: Values are automatically dropped when ownership ends

Types like int, bool, f64 are Copy, so they don't move.
Types like List, Map, String are Move, so they transfer ownership.
        """
    },
    
    "P0502": {
        "title": "cannot borrow as mutable while borrowed as immutable",
        "description": """
This error occurs when you try to create a mutable borrow while an immutable
borrow is still active.

Pyrite's borrowing rules:
1. You can have multiple immutable borrows (&T) at the same time
2. You can have ONE mutable borrow (&mut T) at a time
3. You cannot have mutable AND immutable borrows at the same time
        """,
        "examples": {
            "wrong": """
fn main():
    var data = List[int]([1, 2, 3])
    let ref1 = &data        # Immutable borrow
    let ref2 = &mut data    # ERROR: can't mutably borrow while immutably borrowed
    print(ref1.length())    # ref1 is still in use here
            """,
            "correct": """
fn main():
    var data = List[int]([1, 2, 3])
    let ref1 = &data        # Immutable borrow
    print(ref1.length())    # Use ref1
    # ref1 is no longer used
    let ref2 = &mut data    # OK: immutable borrow is done
    ref2.push(4)
            """
        },
        "notes": """
Why these rules?

These rules prevent data races at compile time:
- Multiple readers OR one writer (never both)
- Prevents reading data while it's being modified
- Prevents modifying data while it's being read

This is Rust's innovation: memory safety WITHOUT garbage collection!
        """
    },
    
    "P0503": {
        "title": "borrowed value does not live long enough",
        "description": """
This error occurs when a reference outlives the value it points to.

A reference cannot outlive the value it references. If it could, you'd have
a dangling pointer - a reference to freed memory.
        """,
        "examples": {
            "wrong": """
fn get_data() -> &List[int]:
    let data = List[int]([1, 2, 3])
    return &data  # ERROR: data is freed when function returns
            """,
            "correct": """
fn get_data() -> List[int]:
    let data = List[int]([1, 2, 3])
    return data  # OK: return owned value
            """
        },
        "notes": """
Lifetimes ensure references are always valid.

The compiler tracks how long values live and ensures references
don't outlive them. This prevents dangling pointers at compile time!
        """
    },
    
    "P0308": {
        "title": "type mismatch",
        "description": """
This error occurs when the type of an expression doesn't match what's expected.

Pyrite is statically typed - types must match at compile time.
        """,
        "examples": {
            "wrong": """
fn main():
    let x: int = "hello"  # ERROR: expected int, found str
            """,
            "correct": """
fn main():
    let x: int = 42       # OK: int matches int
    let y: str = "hello"  # OK: str matches str
            """
        },
        "notes": """
Pyrite has type inference, so you often don't need type annotations:

    let x = 42        # Type inferred as int
    let y = "hello"   # Type inferred as str

But sometimes you need to be explicit:

    fn process(x: int) -> int:  # Types required in signatures
        return x * 2
        """
    },
    
    "P0382": {
        "title": "borrow of moved value",
        "description": """
This error occurs when you try to borrow a value that has already been moved.

Once a value is moved (ownership transferred), you cannot borrow it because
the original variable no longer owns it.
        """,
        "examples": {
            "wrong": """
fn main():
    let data = List[int]([1, 2, 3])
    process(data)      # data is moved here
    let ref = &data    # ERROR: can't borrow moved value
            """,
            "correct": """
fn main():
    let data = List[int]([1, 2, 3])
    let ref = &data    # OK: borrow before moving
    process(data)      # Move is OK (ref is no longer used)
            """
        },
        "notes": """
This is similar to P0234 (cannot use moved value), but specifically about
trying to borrow a moved value.

Remember: Move happens when you pass a non-Copy value to a function or
assign it to another variable. After a move, the original variable is
no longer valid.
        """
    },
    
    "P0499": {
        "title": "cannot borrow as mutable more than once",
        "description": """
This error occurs when you try to create multiple mutable borrows of the same value.

Pyrite's borrowing rules:
- You can have multiple immutable borrows (&T) at the same time
- You can have ONE mutable borrow (&mut T) at a time
- You cannot have multiple mutable borrows at the same time
        """,
        "examples": {
            "wrong": """
fn main():
    var data = List[int]([1, 2, 3])
    let ref1 = &mut data  # First mutable borrow
    let ref2 = &mut data  # ERROR: can't have two mutable borrows
    ref1.push(4)
    ref2.push(5)
            """,
            "correct": """
fn main():
    var data = List[int]([1, 2, 3])
    let ref1 = &mut data  # First mutable borrow
    ref1.push(4)          # Use ref1
    # ref1 is no longer used
    let ref2 = &mut data  # OK: first borrow is done
    ref2.push(5)
            """
        },
        "notes": """
Why only one mutable borrow?

Multiple mutable borrows would allow data races:
- Two functions could modify the same data simultaneously
- This could lead to inconsistent state or crashes

By allowing only one mutable borrow at a time, Pyrite prevents data races
at compile time - no runtime overhead!
        """
    },
    
    "P0505": {
        "title": "borrowed value does not live long enough",
        "description": """
This error occurs when a reference outlives the value it points to.

A reference cannot outlive the value it references. If it could, you'd have
a dangling pointer - a reference to freed memory.
        """,
        "examples": {
            "wrong": """
fn get_ref() -> &List[int]:
    let data = List[int]([1, 2, 3])
    return &data  # ERROR: data is freed when function returns
            """,
            "correct1": """
fn get_ref() -> List[int]:
    let data = List[int]([1, 2, 3])
    return data  # OK: return owned value
            """,
            "correct2": """
fn get_ref(data: &List[int]) -> &List[int]:
    return data  # OK: return reference to parameter (lives long enough)
            """
        },
        "notes": """
Lifetimes ensure references are always valid.

The compiler tracks how long values live and ensures references
don't outlive them. This prevents dangling pointers at compile time!

This is similar to P0503, but P0505 specifically refers to lifetime
issues where the borrowed value's lifetime is too short.
        """
    },
    
    "P0425": {
        "title": "cannot find value in this scope",
        "description": """
This error occurs when you try to use a variable or function that doesn't exist
in the current scope.

The name might be:
- Misspelled
- Not imported
- Defined in a different scope
- Not yet defined (forward reference issue)
        """,
        "examples": {
            "wrong": """
fn main():
    print(x)  # ERROR: x is not defined
            """,
            "correct1": """
fn main():
    let x = 42
    print(x)  # OK: x is defined
            """,
            "correct2": """
fn main():
    let x = 42
    if true:
        print(x)  # OK: x is in outer scope
            """
        },
        "notes": """
Pyrite uses lexical scoping:
- Variables are visible in the scope where they're defined
- Inner scopes can access outer scope variables
- Outer scopes cannot access inner scope variables

If you need a value from another module, use `import`.
        """
    },
    
    "P0412": {
        "title": "cannot find type in this scope",
        "description": """
This error occurs when you try to use a type that doesn't exist in the current scope.

The type might be:
- Misspelled
- Not imported
- Not yet defined
- Defined in a different module
        """,
        "examples": {
            "wrong": """
fn main():
    let x: MyType = ...  # ERROR: MyType is not defined
            """,
            "correct1": """
struct MyType:
    field: int

fn main():
    let x: MyType = MyType { field: 42 }  # OK: MyType is defined
            """,
            "correct2": """
# In module types.pyrite
struct MyType:
    field: int

# In main.pyrite
import types

fn main():
    let x: types.MyType = types.MyType { field: 42 }  # OK: imported
            """
        },
        "notes": """
Types must be defined before use (or imported).

Common fixes:
- Check spelling
- Import the type: `import module_name`
- Define the type before using it
- Check if the type is in a different module
        """
    },
    
    "P0277": {
        "title": "trait bound not satisfied",
        "description": """
This error occurs when a type doesn't implement a required trait.

Traits define behavior that types must implement. If you use a trait method
or require a trait bound, the type must implement that trait.
        """,
        "examples": {
            "wrong": """
trait Display:
    fn display(self) -> str

struct MyType:
    field: int

fn print_value<T: Display>(x: T):
    print(x.display())

fn main():
    let x = MyType { field: 42 }
    print_value(x)  # ERROR: MyType doesn't implement Display
            """,
            "correct": """
trait Display:
    fn display(self) -> str

struct MyType:
    field: int

impl Display for MyType:
    fn display(self) -> str:
        return f"{self.field}"

fn print_value<T: Display>(x: T):
    print(x.display())

fn main():
    let x = MyType { field: 42 }
    print_value(x)  # OK: MyType implements Display
            """
        },
        "notes": """
Traits enable polymorphism in Pyrite.

To fix this error:
1. Implement the required trait for your type
2. Or use a different type that implements the trait
3. Or remove the trait bound if it's not needed

Traits are similar to interfaces in other languages, but more powerful
because they can have default implementations.
        """
    },
    
    "P0004": {
        "title": "non-exhaustive patterns",
        "description": """
This error occurs when a pattern match doesn't cover all possible cases.

Pattern matching must be exhaustive - every possible value must be handled.
        """,
        "examples": {
            "wrong": """
fn process(x: Option[int]):
    match x:
        case Option.Some(value):
            print(value)
        # ERROR: missing case for Option.None
            """,
            "correct": """
fn process(x: Option[int]):
    match x:
        case Option.Some(value):
            print(value)
        case Option.None:
            print("No value")
            """
        },
        "notes": """
Exhaustive pattern matching ensures all cases are handled.

This prevents bugs where you forget to handle a case. The compiler
forces you to think about all possibilities.

For enums, you must match all variants. For Option, you must match
both Some and None. For Result, you must match both Ok and Err.
        """
    }
}


def get_explanation(error_code: str) -> str:
    """Get formatted explanation for an error code"""
    if error_code not in ERROR_EXPLANATIONS:
        return f"Error code {error_code} not found. Available codes: {', '.join(ERROR_EXPLANATIONS.keys())}"
    
    exp = ERROR_EXPLANATIONS[error_code]
    
    parts = []
    parts.append(f"error[{error_code}]: {exp['title']}")
    parts.append("=" * 70)
    parts.append("")
    parts.append(exp['description'].strip())
    parts.append("")
    
    if 'examples' in exp:
        parts.append("Examples:")
        parts.append("-" * 70)
        
        if 'wrong' in exp['examples']:
            parts.append("")
            parts.append("[X] INCORRECT:")
            parts.append(exp['examples']['wrong'].strip())
            parts.append("")
        
        for key in ['correct', 'correct1', 'correct2', 'correct3']:
            if key in exp['examples']:
                parts.append("[OK] CORRECT:")
                parts.append(exp['examples'][key].strip())
                parts.append("")
    
    if 'notes' in exp:
        parts.append("Additional Information:")
        parts.append("-" * 70)
        parts.append(exp['notes'].strip())
        parts.append("")
    
    parts.append("=" * 70)
    parts.append("For more information, see the Pyrite documentation:")
    parts.append("https://github.com/WulfHouse/Quarry/tree/main/docs/errors")
    
    return '\n'.join(parts)


def list_error_codes() -> str:
    """List all available error codes"""
    parts = []
    parts.append("Available Error Codes:")
    parts.append("=" * 70)
    parts.append("")
    
    for code, exp in sorted(ERROR_EXPLANATIONS.items()):
        parts.append(f"  {code}: {exp['title']}")
    
    parts.append("")
    parts.append("Use 'pyritec --explain CODE' to see detailed explanation")
    
    return '\n'.join(parts)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print(list_error_codes())
    else:
        code = sys.argv[1]
        print(get_explanation(code))

