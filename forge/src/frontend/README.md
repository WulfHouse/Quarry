# Frontend

The frontend module handles lexical analysis and parsing of Pyrite source code.

## Components

- **`lexer.py`** - Tokenizes Pyrite source code into a stream of tokens
- **`parser.py`** - Parses tokens into an Abstract Syntax Tree (AST)
- **`tokens.py`** - Token definitions and utilities

## Pipeline

```
Source Code → lexer.py → Tokens → parser.py → AST
```

## Usage

```python
from src.frontend import lex, parse, LexerError, ParseError

# Tokenize source code
tokens = lex(source_code)

# Parse tokens into AST
ast = parse(tokens)
```

## See Also

- `src/middle/` - Type checking and analysis
- `src/backend/` - Code generation
- `src/README.md` - Compiler pipeline overview
