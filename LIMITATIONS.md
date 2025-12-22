# Known Limitations (Alpha v1.0)

> **⚠️ ALPHA v1.0 STATUS**
> 
> This project is currently in **Alpha v1.0**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0.

This document lists known limitations and incomplete features in **Forge** (the Pyrite compiler) as of Alpha v1.0. These are tracked as TODO comments in the codebase and will be addressed in future releases.

## Language Features

### Tuple Destructuring
**Status:** Not fully implemented
**Location:** `src/frontend/parser.py:991`
**Description:** Proper tuple destructuring in variable declarations is not yet supported. The AST node structure exists but needs full implementation.

### Tuple Literals
**Status:** Not implemented
**Location:** `src/frontend/parser.py:1833`
**Description:** Tuple literal syntax (e.g., `(1, 2, 3)`) is not yet supported. A proper `TupleLiteral` AST node needs to be added.

### Enum Variant Field Binding
**Status:** Partial implementation
**Location:** `src/middle/ownership.py:478`
**Description:** Ownership analysis for enum variant fields is not fully implemented. This may affect memory safety guarantees for complex enum patterns.

### Iterator Protocol
**Status:** Partial implementation
**Location:** 
- `src/middle/type_checker.py:783` - Iterator trait checking
- `src/backend/codegen.py:951` - Iterator protocol codegen
**Description:** The iterator trait and protocol are partially implemented. Some iterator operations may not work correctly.

### Result Type Error Propagation
**Status:** Partial implementation
**Location:** `src/backend/codegen.py:1202`
**Description:** Full `Result` type unwrapping with automatic error propagation is not yet implemented. Manual error handling is required.

## Type System

### Mutability Checking
**Status:** Basic implementation
**Location:** `src/middle/type_checker.py:690`
**Description:** Mutability checking exists but could be more sophisticated. Some edge cases may not be caught.

### Enum Variant Type Matching
**Status:** Partial implementation
**Location:** `src/middle/type_checker.py:890`
**Description:** Type checking for enum variants may not fully verify that variant types match expected types in all cases.

### Compile-Time Parameters in Type Annotations
**Status:** Not implemented
**Location:** `src/backend/monomorphization.py:269`
**Description:** Using compile-time parameters in type annotations is not yet supported.

## Code Generation

### Field and Index Assignment
**Status:** Not implemented
**Location:** `src/backend/codegen.py:732`
**Description:** Assignment to struct fields and array indices is not yet fully implemented in code generation.

### Element Type Inference
**Status:** Partial implementation
**Location:** `src/backend/codegen.py:1217`
**Description:** Some array operations may not correctly infer element types from the type checker.

### Parameter Closure Storage
**Status:** Missing error checking
**Location:** `src/backend/codegen.py:2269`
**Description:** Error checking to prevent storing parameter closures is not yet implemented. This may lead to incorrect code generation in some cases.

### Method Calls and Field Access in Monomorphization
**Status:** Not implemented
**Location:** `src/backend/monomorphization.py:496`
**Description:** Method calls and field access in generic contexts may not be fully handled during monomorphization.

## Compiler Passes

### Closure Inlining - Statement Sequences
**Status:** Partial implementation
**Location:** `src/passes/closure_inline_pass.py:212`
**Description:** Closure inlining may not handle statement sequences properly, requiring block-level transformation.

### Closure Inlining - Error Reporting
**Status:** Basic implementation
**Location:** `src/passes/closure_inline_pass.py:223`
**Description:** Error reporting for closure inlining could be more detailed.

## FFI and Bridges

### AST Bridge FFI Bindings
**Status:** Placeholder implementation
**Location:** `src/bridge/ast_bridge.py:7`
**Description:** Actual FFI bindings for AST bridge are not yet implemented. Placeholder code exists.

### Tokens Bridge FFI Bindings
**Status:** Placeholder implementation
**Location:** `src/bridge/tokens_bridge.py:10,39,46`
**Description:** FFI bindings for token-related functions (`get_keyword_type()`, `is_keyword()`) are not yet implemented. Python fallbacks are used.

## Experimental Features

(No experimental features currently tracked)

## Workarounds

For features that are not yet implemented:

1. **Tuple Destructuring:** Use individual variable assignments instead
2. **Tuple Literals:** Use arrays or structs as alternatives
3. **Iterator Protocol:** Use explicit loops instead of iterator-based operations
4. **Result Error Propagation:** Use explicit error handling with `match` or `try` expressions
5. **Field/Index Assignment:** Use temporary variables and reassignment

## Reporting Issues

If you encounter issues related to these limitations, please:
1. Check if the issue is listed here
2. If not, report it as a bug
3. If it is listed, note that it's a known limitation

## Future Releases

These limitations are tracked in the codebase as TODO comments and will be addressed in future releases based on priority and user feedback.
