# Known Limitations (Alpha v1.1)

> **⚠️ ALPHA v1.1 STATUS**
> 
> This project is currently in **Alpha v1.1**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0.

This document lists known limitations and incomplete features in **Forge** (the Pyrite compiler) as of Alpha v1.1. These will be addressed in future releases.

## Language Features

### Field and Index Assignment

**Status:** ✅ Implemented

**Location:** `forge/src/backend/codegen.py:876, 879, 885, 951`

**Description:** Assignment to struct fields (`obj.field = value`) and array/list indices (`obj[index] = value`) is now supported.

### Tuple Destructuring

**Status:** ✅ Implemented

**Location:** `forge/src/frontend/parser.py:1152`, `forge/src/middle/type_checker.py:952`, `forge/src/backend/codegen.py:733`

**Description:** Tuple destructuring in variable declarations is supported. You can use `let (a, b) = tuple_value` to destructure tuples.

### Tuple Literals

**Status:** ✅ Implemented

**Location:** `forge/src/frontend/parser.py:2006`, `forge/src/backend/codegen.py:1573`

**Description:** Tuple literal syntax (e.g., `(1, 2, 3)`) is supported.

### Enum Variant Field Binding

**Status:** Partial implementation

**Location:** `forge/src/middle/ownership.py:478`

**Description:** Ownership analysis for enum variant fields is not fully implemented. This may affect memory safety guarantees for complex enum patterns.

### Iterator Protocol

**Status:** Partial implementation

**Location:** 
- `forge/src/middle/type_checker.py:783` - Iterator trait checking
- `forge/src/backend/codegen.py:951` - Iterator protocol codegen

**Description:** The iterator trait and protocol are partially implemented. Some iterator operations may not work correctly.

### Result Type Error Propagation

**Status:** Partial implementation

**Location:** `forge/src/backend/codegen.py:1202`

**Description:** Full `Result` type unwrapping with automatic error propagation is not yet implemented. Manual error handling is required.

## Type System

### Mutability Checking

**Status:** Basic implementation

**Location:** `forge/src/middle/type_checker.py:690`

**Description:** Mutability checking exists but could be more sophisticated. Some edge cases may not be caught.

### Enum Variant Type Matching


**Location:** `forge/src/middle/type_checker.py:890`

**Description:** Type checking for enum variants may not fully verify that variant types match expected types in all cases.

### Compile-Time Parameters in Type Annotations

**Status:** Not implemented

**Location:** `forge/src/backend/monomorphization.py:269`

**Description:** Using compile-time parameters in type annotations is not yet supported.

## Code Generation

### Element Type Inference

**Status:** Partial implementation

**Location:** `forge/src/backend/codegen.py:1217`

**Description:** Some array operations may not correctly infer element types from the type checker.

### Parameter Closure Storage

**Status:** Missing error checking

**Location:** `forge/src/backend/codegen.py:2269`

**Description:** Error checking to prevent storing parameter closures is not yet implemented. This may lead to incorrect code generation in some cases.

### Method Calls and Field Access in Monomorphization

**Status:** Not implemented

**Location:** `forge/src/backend/monomorphization.py:496`

**Description:** Method calls and field access in generic contexts may not be fully handled during monomorphization.

## Compiler Passes

### Closure Inlining - Statement Sequences

**Status:** Partial implementation

**Location:** `forge/src/passes/closure_inline_pass.py:212`

**Description:** Closure inlining may not handle statement sequences properly, requiring block-level transformation.

### Closure Inlining - Error Reporting

**Status:** Basic implementation

**Location:** `forge/src/passes/closure_inline_pass.py:223`

**Description:** Error reporting for closure inlining could be more detailed.

## FFI and Bridges

### AST Bridge FFI Bindings

**Status:** Placeholder implementation

**Location:** `forge/src/bridge/ast_bridge.py:7`

**Description:** Actual FFI bindings for AST bridge are not yet implemented. Placeholder code exists.

### Tokens Bridge FFI Bindings

**Status:** Placeholder implementation

**Location:** `forge/src/bridge/tokens_bridge.py:10,39,46`

**Description:** FFI bindings for token-related functions (`get_keyword_type()`, `is_keyword()`) are not yet implemented. Python fallbacks are used.

## Experimental Features

(No experimental features currently tracked)

## Workarounds

For features that are not yet implemented:

1. **Iterator Protocol:** Use explicit loops instead of iterator-based operations

2. **Result Error Propagation:** Use explicit error handling with `match` or `try` expressions

3. **Compile-time Parameters:** Use concrete types or generic functions where possible

4. **Enum Variant Ownership:** Avoid complex ownership-heavy data in enums if safety is critical

## Reporting Issues

If you encounter issues related to these limitations, please:

1. Check if the issue is listed here

2. If not, report it as a bug

3. If it is listed, note that it's a known limitation

## Future Releases

These limitations will be addressed in future releases based on priority and user feedback.
