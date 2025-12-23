# Proven Language Syntax

This document lists only syntax elements that are **proven** to be accepted by the parser and compiler, based on passing tests and working examples.

## Evidence Methodology

Each syntax element listed here is backed by:

- Passing parser tests in `forge/tests/frontend/test_parser.py`

- Working examples in `forge/examples/basic/`

- Acceptance tests in `tests/acceptance/`

## Functions

### Function Definition

```pyrite
fn function_name():
    pass

fn function_with_params(a: int, b: int) -> int:
    return a + b
```

**Evidence:**

- Test: `test_parse_simple_function()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_function_with_params()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/hello.pyrite`

### Function with Self Parameter

```pyrite
fn method(&self):
    pass

fn mutable_method(&mut self):
    pass
```

**Evidence:**

- Test: `test_parse_function_with_self_parameter()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_function_with_mutable_self()` in `forge/tests/frontend/test_parser.py`

### Generic Functions

```pyrite
fn max[T](a: T, b: T) -> T:
    if a > b:
        return a
    return b
```

**Evidence:**

- Example: `forge/examples/basic/generics.pyrite`

- Test: `test_parse_generic_type()` in `forge/tests/frontend/test_parser.py`

### Extern Functions

```pyrite
extern fn external_function(x: int) -> int
```

**Evidence:**

- Parser method: `parse_extern()` in `forge/src/frontend/parser.py:160`

## Variables

### Immutable Variable Declaration

```pyrite
let x = 42
let name: String = "Pyrite"
```

**Evidence:**

- Test: `test_parse_let_statement()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/simple.pyrite`

### Mutable Variable Declaration

```pyrite
var x = 42
var counter: int = 0
```

**Evidence:**

- Test: `test_parse_var_statement()` in `forge/tests/frontend/test_parser.py`

## Control Flow

### If Statement

```pyrite
if condition:
    do_something()
else:
    do_something_else()
```

**Evidence:**

- Test: `test_parse_if_statement()` in `forge/tests/frontend/test_parser.py`

### If Expression

```pyrite
let result = x if condition else y
```

**Evidence:**

- Test: `test_parse_if_expression()` in `forge/tests/frontend/test_parser.py`

### While Loop

```pyrite
while condition:
    do_something()
```

**Evidence:**

- Test: `test_parse_while_loop()` in `forge/tests/frontend/test_parser.py`

### For Loop

```pyrite
for i in 0..10:
    print(i)
```

**Evidence:**

- Test: `test_parse_for_loop()` in `forge/tests/frontend/test_parser.py`

### Match Statement

```pyrite
match value:
    0:
        print("zero")
    1 | 2:
        print("one or two")
    _:
        print("other")
```

**Evidence:**

- Test: `test_parse_match_statement()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_match_with_or_pattern()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_match_with_enum_pattern()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_match_with_wildcard_pattern()` in `forge/tests/frontend/test_parser.py`

- Example: `tests/acceptance/test5_match.pyrite`

### Break Statement

```pyrite
while True:
    if condition:
        break
```

**Evidence:**

- Test: `test_parse_break_statement()` in `forge/tests/frontend/test_parser.py`

### Continue Statement

```pyrite
while True:
    if condition:
        continue
```

**Evidence:**

- Test: `test_parse_continue_statement()` in `forge/tests/frontend/test_parser.py`

### Return Statement

```pyrite
return
return value
```

**Evidence:**

- Test: `test_parse_return_with_value()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_return_without_value()` in `forge/tests/frontend/test_parser.py`

### Defer Statement

```pyrite
defer:
    cleanup()
```

**Evidence:**

- Test: `test_parse_defer_statement()` in `forge/tests/frontend/test_parser.py`

- Example: `tests/acceptance/test_defer.pyrite`

### With Statement

```pyrite
with resource:
    use_resource()
```

**Evidence:**

- Test: `test_parse_with_statement()` in `forge/tests/frontend/test_parser.py`

### Unsafe Block

```pyrite
unsafe:
    unsafe_operation()
```

**Evidence:**

- Test: `test_parse_unsafe_block()` in `forge/tests/frontend/test_parser.py`

### Try Expression

```pyrite
let result = try operation()
```

**Evidence:**

- Test: `test_parse_try_expression()` in `forge/tests/frontend/test_parser.py`

## Types

### Primitive Types

```pyrite
let x: int = 42
let y: bool = true
let z: String = "hello"
```

**Evidence:**

- Used throughout parser tests and examples

### Reference Types

```pyrite
fn read(x: &int):
    pass

fn modify(x: &mut int):
    pass
```

**Evidence:**

- Test: `test_parse_reference_type()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_mutable_reference_type()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/borrowing.pyrite`

### Pointer Types

```pyrite
let p: *int = ...
let mp: *mut int = ...
let cp: *const int = ...
```

**Evidence:**
- Test: `test_parse_pointer_type()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_mutable_pointer_type()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_const_pointer_type()` in `forge/tests/frontend/test_parser.py`

### Array Types

```pyrite
let arr: [int; 10] = ...
```

**Evidence:**

- Test: `test_parse_array_type()` in `forge/tests/frontend/test_parser.py`

### Slice Types

```pyrite
let slice: [int] = ...
```

**Evidence:**

- Test: `test_parse_slice_type()` in `forge/tests/frontend/test_parser.py`

### Generic Types

```pyrite
let list: List[int] = ...
let nested: Map[String, List[int]] = ...
```

**Evidence:**

- Test: `test_parse_generic_type()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_nested_generic_type()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/generics.pyrite`

### Tuple Types

```pyrite
let pair: (int, String) = ...
```

**Evidence:**

- Test: `test_parse_tuple_type()` in `forge/tests/frontend/test_parser.py`

### Tuple Literals

```pyrite
let tuple = (1, 2, 3)
let pair = ("hello", 42)
```

**Evidence:**

- Parser method: `parse_primary()` in `forge/src/frontend/parser.py:2006`

- Codegen method: `gen_tuple_literal()` in `forge/src/backend/codegen.py:1573`

### Tuple Patterns in Variable Declarations

```pyrite
let (a, b) = (1, 2)
let (x, y, z) = get_tuple()
```

**Evidence:**

- Parser method: `parse_var_decl()` in `forge/src/frontend/parser.py:1152`

- Type checker: `check_pattern()` in `forge/src/middle/type_checker.py:952`

- Codegen: `gen_pattern_binding()` in `forge/src/backend/codegen.py:733`

### Function Types

```pyrite
let callback: fn(int) -> int = ...
```

**Evidence:**

- Test: `test_parse_function_type()` in `forge/tests/frontend/test_parser.py`

## Data Structures

### Struct Definition

```pyrite
struct Point:
    x: int
    y: int
```

**Evidence:**

- Test: `test_parse_struct()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/structs.pyrite`

### Struct Literal

```pyrite
let point = Point { x: 1, y: 2 }
```

**Evidence:**

- Test: `test_parse_struct_literal()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/structs.pyrite`

### Enum Definition

```pyrite
enum Option[T]:
    Some(value: T)
    None
```

**Evidence:**

- Test: `test_parse_enum()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_enum_variant_with_none()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/enums.pyrite`

### Trait Definition

```pyrite
trait Display:
    fn display(&self) -> String
```

**Evidence:**

- Parser method: `parse_trait()` in `forge/src/frontend/parser.py:597`

### Implementation Block

```pyrite
impl Display for Point:
    fn display(&self) -> String:
        return "Point"
```

**Evidence:**

- Parser method: `parse_impl()` in `forge/src/frontend/parser.py:690`

- Test: `test_parse_function_after_impl()` in `forge/tests/frontend/test_parser.py`

### Opaque Type

```pyrite
opaque type Handle;
```

**Evidence:**

- Test: `test_parse_opaque_type()` in `forge/tests/frontend/test_parser.py`

- Parser method: `parse_opaque_type()` in `forge/src/frontend/parser.py:846`

### Const Declaration

```pyrite
const MAX_SIZE: int = 100
```

**Evidence:**

- Parser method: `parse_const()` in `forge/src/frontend/parser.py:823`

## Expressions

### Literals

```pyrite
let int_lit = 42
let bool_lit = true
let string_lit = "hello"
let list_lit = [1, 2, 3]
```

**Evidence:**

- Test: `test_parse_list_literal()` in `forge/tests/frontend/test_parser.py`

- Used throughout examples

### Binary Operations

```pyrite
let sum = a + b
let product = a * b
let comparison = a > b
```

**Evidence:**

- Test: `test_parse_binary_op()` in `forge/tests/frontend/test_parser.py`

- Example: `tests/acceptance/test6_arithmetic.pyrite`

### Function Calls

```pyrite
print("hello", "world")
```

**Evidence:**

- Test: `test_parse_function_call()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/hello.pyrite`

### Method Calls

```pyrite
list.push(42)
```

**Evidence:**

- Test: `test_parse_method_call()` in `forge/tests/frontend/test_parser.py`

### Field Access

```pyrite
let x = point.x
```

**Evidence:**

- Test: `test_parse_field_access()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/structs.pyrite`

### Index Access

```pyrite
let item = list[0]
let slice = array[0..10]
```

**Evidence:**

- Test: `test_parse_index_access()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_index_access_with_range()` in `forge/tests/frontend/test_parser.py`

- Example: `tests/acceptance/test8_arrays.pyrite`

### Field and Index Assignment

```pyrite
point.x = 42
list[0] = 100
```

**Evidence:**

- Codegen: `gen_field_assignment()` in `forge/src/backend/codegen.py:885`

- Codegen: `gen_index_assignment()` in `forge/src/backend/codegen.py:951`

- Test: `tests/m9_map_local.pyrite` (exercises field/index access)

## Closures

### Parameter Closures (Compile-Time)

```pyrite
let closure = fn[x: int] -> int: x * 2
```

**Evidence:**

- Test: `test_parse_parameter_closure()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/closures.pyrite`

### Runtime Closures

```pyrite
let closure = fn(x: int) -> int: x * 2
```

**Evidence:**

- Test: `test_parse_runtime_closure()` in `forge/tests/frontend/test_parser.py`

- Example: `forge/examples/basic/closures.pyrite`

## Modules

### Import Statement

```pyrite
import std::io
import std::collections as coll
```

**Evidence:**

- Test: `test_parse_import()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_import_with_alias()` in `forge/tests/frontend/test_parser.py`

- Test: `test_parse_program_with_only_imports()` in `forge/tests/frontend/test_parser.py`

## Known Limitations

The following syntax elements are **not** fully implemented (see `LIMITATIONS.md`):

- ⚠️ Enum variant field binding in ownership analysis - Partial implementation

## Validation

To validate syntax claims:

1. Run parser tests: `python tools/testing/pytest_fast.py forge/tests/frontend/test_parser.py`

2. Try examples: `python tools/runtime/pyrite.py forge/examples/basic/<example>.pyrite`

3. Check acceptance tests: `python tools/testing/pytest.py tests/acceptance/`
