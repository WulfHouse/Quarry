# Proven Features

This document lists language features, compiler capabilities, and toolchain features with their proven status.

## Legend

- ✅ **Supported**: Feature is fully implemented and proven to work
- ⚠️ **Partial**: Feature is partially implemented (documented limitations apply)
- ❌ **Not Supported**: Feature is explicitly absent or marked as TODO in repository

## Language Features

### Core Syntax

| Feature | Status | Evidence |
|---------|--------|----------|
| Function definitions | ✅ | `test_parse_simple_function()`, `forge/examples/basic/hello.pyrite` |
| Function parameters | ✅ | `test_parse_function_with_params()`, examples |
| Function return types | ✅ | `test_parse_function_with_params()`, examples |
| Generic functions | ✅ | `forge/examples/basic/generics.pyrite` |
| Immutable variables (`let`) | ✅ | `test_parse_let_statement()`, `forge/examples/basic/simple.pyrite` |
| Mutable variables (`var`) | ✅ | `test_parse_var_statement()` |
| Struct definitions | ✅ | `test_parse_struct()`, `forge/examples/basic/structs.pyrite` |
| Struct literals | ✅ | `test_parse_struct_literal()`, examples |
| Enum definitions | ✅ | `test_parse_enum()`, `forge/examples/basic/enums.pyrite` |
| Trait definitions | ✅ | Parser: `parse_trait()` in `forge/src/frontend/parser.py:597` |
| Implementation blocks | ✅ | Parser: `parse_impl()` in `forge/src/frontend/parser.py:690` |
| Opaque types | ✅ | `test_parse_opaque_type()` |
| Const declarations | ✅ | Parser: `parse_const()` in `forge/src/frontend/parser.py:823` |
| Import statements | ✅ | `test_parse_import()`, `test_parse_import_with_alias()` |

### Control Flow

| Feature | Status | Evidence |
|---------|--------|----------|
| If statements | ✅ | `test_parse_if_statement()`, examples |
| If expressions | ✅ | `test_parse_if_expression()` |
| While loops | ✅ | `test_parse_while_loop()`, `tests/acceptance/test9_loops.pyrite` |
| For loops | ✅ | `test_parse_for_loop()`, `tests/acceptance/test9_loops.pyrite` |
| Match statements | ✅ | `test_parse_match_statement()`, `tests/acceptance/test5_match.pyrite` |
| Match with or patterns | ✅ | `test_parse_match_with_or_pattern()` |
| Match with enum patterns | ✅ | `test_parse_match_with_enum_pattern()` |
| Match with wildcard | ✅ | `test_parse_match_with_wildcard_pattern()` |
| Break statements | ✅ | `test_parse_break_statement()` |
| Continue statements | ✅ | `test_parse_continue_statement()` |
| Return statements | ✅ | `test_parse_return_with_value()`, `test_parse_return_without_value()` |
| Defer statements | ✅ | `test_parse_defer_statement()`, `tests/acceptance/test_defer.pyrite` |
| With statements | ✅ | `test_parse_with_statement()` |
| Unsafe blocks | ✅ | `test_parse_unsafe_block()` |
| Try expressions | ✅ | `test_parse_try_expression()` |

### Types

| Feature | Status | Evidence |
|---------|--------|----------|
| Primitive types (`int`, `bool`, `String`) | ✅ | Used throughout tests and examples |
| Reference types (`&T`, `&mut T`) | ✅ | `test_parse_reference_type()`, `forge/examples/basic/borrowing.pyrite` |
| Pointer types (`*T`, `*mut T`, `*const T`) | ✅ | `test_parse_pointer_type()`, `test_parse_mutable_pointer_type()`, `test_parse_const_pointer_type()` |
| Array types (`[T; N]`) | ✅ | `test_parse_array_type()` |
| Slice types (`[T]`) | ✅ | `test_parse_slice_type()` |
| Generic types (`List[T]`, `Map[K, V]`) | ✅ | `test_parse_generic_type()`, `test_parse_nested_generic_type()` |
| Tuple types (`(T, U)`) | ✅ | `test_parse_tuple_type()` |
| Function types (`fn(T) -> U`) | ✅ | `test_parse_function_type()` |
| Associated type references | ✅ | `test_parse_associated_type_ref()` |

### Expressions

| Feature | Status | Evidence |
|---------|--------|----------|
| Integer literals | ✅ | Used throughout tests and examples |
| Boolean literals | ✅ | Used throughout tests and examples |
| String literals | ✅ | Used throughout tests and examples |
| List literals | ✅ | `test_parse_list_literal()`, `tests/acceptance/test8_arrays.pyrite` |
| Binary operations | ✅ | `test_parse_binary_op()`, `tests/acceptance/test6_arithmetic.pyrite` |
| Function calls | ✅ | `test_parse_function_call()`, examples |
| Method calls | ✅ | `test_parse_method_call()` |
| Field access | ✅ | `test_parse_field_access()`, `forge/examples/basic/structs.pyrite` |
| Index access | ✅ | `test_parse_index_access()`, `tests/acceptance/test8_arrays.pyrite` |
| Index access with range | ✅ | `test_parse_index_access_with_range()` |
| Parameter closures (compile-time) | ✅ | `test_parse_parameter_closure()`, `forge/examples/basic/closures.pyrite` |
| Runtime closures | ✅ | `test_parse_runtime_closure()`, `forge/examples/basic/closures.pyrite` |

### Ownership and Borrowing

| Feature | Status | Evidence |
|---------|--------|----------|
| Ownership analysis | ✅ | `tests/acceptance/test2_ownership_error.pyrite`, `forge/examples/basic/ownership.pyrite` |
| Immutable borrowing (`&T`) | ✅ | `forge/examples/basic/borrowing.pyrite`, `tests/acceptance/test3_borrowing.pyrite` |
| Mutable borrowing (`&mut T`) | ✅ | `forge/examples/basic/borrowing.pyrite`, `tests/acceptance/test3_borrowing.pyrite` |
| Borrow checker | ✅ | Code: `forge/src/middle/borrow_checker.py` |

### Not Supported / Partial

| Feature | Status | Evidence |
|---------|--------|----------|
| Tuple literals `(1, 2, 3)` | ❌ | `LIMITATIONS.md`: Not implemented, `src/frontend/parser.py:1833` |
| Tuple destructuring | ❌ | `LIMITATIONS.md`: Not fully implemented, `src/frontend/parser.py:991` |
| Enum variant field binding (ownership) | ⚠️ | `LIMITATIONS.md`: Partial, `src/middle/ownership.py:478` |
| Iterator protocol | ⚠️ | `LIMITATIONS.md`: Partial, `src/middle/type_checker.py:783`, `src/backend/codegen.py:951` |
| Result error propagation | ⚠️ | `LIMITATIONS.md`: Partial, `src/backend/codegen.py:1202` |
| Compile-time parameters in type annotations | ❌ | `LIMITATIONS.md`: Not implemented, `src/backend/monomorphization.py:269` |
| Field assignment | ❌ | `LIMITATIONS.md`: Not implemented, `src/backend/codegen.py:732` |
| Index assignment | ❌ | `LIMITATIONS.md`: Not implemented, `src/backend/codegen.py:732` |

## Compiler Features

### Compilation Pipeline

| Feature | Status | Evidence |
|---------|--------|----------|
| Lexical analysis | ✅ | `forge/src/frontend/lexer.py`, tests |
| Parsing | ✅ | `forge/src/frontend/parser.py`, tests |
| Type checking | ✅ | `forge/src/middle/type_checker.py`, tests |
| Ownership analysis | ✅ | `forge/src/middle/ownership.py`, tests |
| Borrow checking | ✅ | `forge/src/middle/borrow_checker.py`, tests |
| LLVM IR generation | ✅ | `forge/src/backend/codegen.py`, examples compile |
| Linking | ✅ | `forge/src/backend/linker.py` |
| Monomorphization | ✅ | `forge/src/backend/monomorphization.py`, `tests/acceptance/test_monomorphization.pyrite` |

### Compiler Passes

| Feature | Status | Evidence |
|---------|--------|----------|
| Closure inlining | ⚠️ | `forge/src/passes/closure_inline_pass.py`, `LIMITATIONS.md`: Partial |
| With desugaring | ✅ | `forge/src/passes/with_desugar_pass.py` |

### Compiler Options

| Feature | Status | Evidence |
|---------|--------|----------|
| Emit LLVM IR (`--emit-llvm`) | ✅ | `forge/src/compiler.py:395-397` |
| Deterministic builds (`--deterministic`) | ✅ | `forge/src/compiler.py:398-400` |
| Ownership visualizations (`--visual`) | ✅ | `forge/src/compiler.py:401-403` |
| Cost warnings (`--warn-cost`) | ✅ | `forge/src/compiler.py:404-406` |
| Incremental compilation | ✅ | `forge/src/compiler.py:407-412`, `forge/src/utils/incremental.py` |
| Error explanations (`--explain`) | ✅ | `forge/src/compiler.py:413-421` |

## Quarry Build System Features

### Project Management

| Feature | Status | Evidence |
|---------|--------|----------|
| Create new project (`new`) | ✅ | `forge/quarry/main.py:cmd_new()`, registered |
| Build project (`build`) | ✅ | `forge/quarry/main.py:cmd_build()`, registered |
| Run project (`run`) | ✅ | `forge/quarry/main.py:cmd_run()`, registered |
| Clean artifacts (`clean`) | ✅ | `forge/quarry/main.py:cmd_clean()`, registered |
| Run tests (`test`) | ✅ | `forge/quarry/main.py:cmd_test()`, registered |

### Code Quality

| Feature | Status | Evidence |
|---------|--------|----------|
| Format code (`fmt`) | ✅ | `forge/quarry/main.py:cmd_fmt()`, registered |
| Auto-fix errors (`fix`) | ✅ | `forge/quarry/main.py:cmd_fix()`, registered |

### Performance Analysis

| Feature | Status | Evidence |
|---------|--------|----------|
| Cost analysis (`cost`) | ✅ | `forge/quarry/main.py:cmd_cost()`, registered |
| Binary size analysis (`bloat`) | ✅ | `forge/quarry/main.py:cmd_bloat()`, registered |
| Performance profiling (`perf`) | ✅ | `forge/quarry/main.py:cmd_perf()`, registered |

### Dependency Management

| Feature | Status | Evidence |
|---------|--------|----------|
| Resolve dependencies (`resolve`) | ✅ | `forge/quarry/main.py:cmd_resolve()`, registered |
| Update dependencies (`update`) | ✅ | `forge/quarry/main.py:cmd_update()`, registered |
| Install dependencies (`install`) | ✅ | `forge/quarry/main.py:cmd_install()`, registered |
| Search packages (`search`) | ✅ | `forge/quarry/main.py:cmd_search()`, registered |
| Package info (`info`) | ✅ | `forge/quarry/main.py:cmd_info()`, registered |
| Publish package (`publish`) | ✅ | `forge/quarry/main.py:cmd_publish()`, registered |

## Experimental Features

(No experimental features currently tracked)

## Validation

To validate feature claims:

1. Check test files: `python tools/testing/pytest_fast.py`
2. Check examples: `python tools/runtime/pyrite.py forge/examples/basic/<example>.pyrite`
3. Check acceptance tests: `python tools/testing/pytest.py tests/acceptance/`
4. Check limitations: `LIMITATIONS.md`
5. Check code: Search for implementation in `forge/src/`
