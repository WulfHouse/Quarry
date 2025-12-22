# Compiler Passes

Compiler passes perform AST transformations and optimizations.

## Components

- **`closure_inline_pass.py`** - Closure inlining optimization
- **`closure_inlining.py`** - Closure inlining utilities
- **`with_desugar_pass.py`** - `with` statement desugaring

## Pipeline Position

```
Typed AST → Passes → Transformed AST → Backend
```

## Usage

```python
from src.passes import ClosureInlinePass, WithDesugarPass

# Apply passes
with_pass = WithDesugarPass()
ast = with_pass.transform(ast)

closure_pass = ClosureInlinePass()
ast = closure_pass.transform(ast)
```

## See Also

- `src/middle/` - Type checking (runs before passes)
- `src/backend/` - Code generation (runs after passes)
- `src/README.md` - Compiler pipeline overview
