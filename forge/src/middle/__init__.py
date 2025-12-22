"""Middle-end compiler modules.

This package contains type checking, ownership analysis, and symbol resolution components.

Modules:
    type_checker: Type checking and inference
    ownership: Ownership analysis
    borrow_checker: Borrow checking
    symbol_table: Symbol table management
    module_system: Module resolution and imports

See Also:
    frontend: Lexical analysis and parsing
    backend: Code generation
    compiler: Main compiler driver
"""

from .type_checker import type_check, TypeCheckError, TypeChecker
from .ownership import analyze_ownership, OwnershipAnalyzer, OwnershipState, OwnershipError
from .borrow_checker import check_borrows, BorrowChecker, OwnershipEvent, BorrowError, BorrowState, Borrow
from .symbol_table import SymbolTable, Symbol, NameResolver
from .module_system import resolve_modules, ModuleError, ModuleResolver

__all__ = [
    'type_check', 'TypeCheckError', 'TypeChecker',
    'analyze_ownership', 'OwnershipAnalyzer', 'OwnershipState', 'OwnershipError',
    'check_borrows', 'BorrowChecker', 'OwnershipEvent', 'BorrowError', 'BorrowState', 'Borrow',
    'SymbolTable', 'Symbol', 'NameResolver',
    'resolve_modules', 'ModuleError', 'ModuleResolver'
]
