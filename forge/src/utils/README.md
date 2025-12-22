# Utilities

Utility modules for diagnostics, error handling, and incremental compilation.

## Components

- **`diagnostics.py`** - Error diagnostics and error codes
- **`error_formatter.py`** - Error message formatting with source context
- **`error_explanations.py`** - Detailed error explanations
- **`incremental.py`** - Incremental compilation support
- **`drops.py`** - Drop analysis for resource cleanup

## Usage

```python
from src.utils import ErrorFormatter, ErrorCode, get_explanation

# Format errors
formatter = ErrorFormatter()
message = formatter.format_error(
    error_type="Type Error",
    message="Expected int, found string",
    span=span,
    source_lines=source_lines
)

# Get error explanation
explanation = get_explanation("E001")
```

## See Also

- `src/README.md` - Compiler pipeline overview
- `docs/specification/02-diagnostics.md` - Diagnostic system specification
