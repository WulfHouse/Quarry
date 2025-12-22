"""Frontend compiler modules.

This package contains the lexical analysis and parsing components of the Pyrite compiler.

Modules:
    lexer: Tokenizes Pyrite source code into tokens
    parser: Parses tokens into an Abstract Syntax Tree (AST)
    tokens: Token definitions and utilities

See Also:
    middle: Type checking and analysis
    backend: Code generation
    compiler: Main compiler driver
"""

from .lexer import lex, LexerError, Lexer
from .parser import parse, ParseError
from .tokens import Token, TokenType, Span

__all__ = ['lex', 'LexerError', 'Lexer', 'parse', 'ParseError', 'Token', 'TokenType', 'Span']
