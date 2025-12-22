# Backend

The backend module handles code generation, linking, and optimization.

## Components

- **`codegen.py`** - LLVM IR code generation
- **`linker.py`** - Linking with standard library
- **`monomorphization.py`** - Generic instantiation

## Pipeline

```
Analyzed AST → monomorphization.py → codegen.py → LLVM IR → linker.py → Executable
```

## Usage

```python
from src.backend import generate_llvm, link_with_stdlib, monomorphize_program

# Monomorphize generics
monomorphize_program(ast)

# Generate LLVM IR
llvm_ir = generate_llvm(ast)

# Link with standard library
link_with_stdlib(llvm_ir, output_path)
```

## See Also

- `src/middle/` - Type checking and analysis
- `src/passes/` - Compiler passes
- `src/README.md` - Compiler pipeline overview
