# Middle-End

The middle-end module handles type checking, ownership analysis, and symbol resolution.

## Components

- **`type_checker.py`** - Type checking and inference
- **`ownership.py`** - Ownership analysis
- **`borrow_checker.py`** - Borrow checking
- **`symbol_table.py`** - Symbol resolution and scoping
- **`module_system.py`** - Module resolution and imports

## Pipeline

```
AST → type_checker.py → Typed AST → ownership.py → Borrow Checker → Analyzed AST
```

## Usage

```python
from src.middle import type_check, analyze_ownership, check_borrows, resolve_modules

# Type check AST
type_checker = type_check(ast)

# Analyze ownership
analyze_ownership(ast, type_checker)

# Check borrows
check_borrows(ast, type_checker)

# Resolve modules
resolve_modules(ast)
```

## See Also

- `src/frontend/` - Lexical analysis and parsing
- `src/backend/` - Code generation
- `src/README.md` - Compiler pipeline overview
