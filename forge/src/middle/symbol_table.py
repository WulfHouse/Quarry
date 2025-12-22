"""Symbol table for name resolution"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from ..types import Type, FunctionType
from ..frontend.tokens import Span


@dataclass
class Symbol:
    """A symbol in the symbol table"""
    name: str
    type: Type
    mutable: bool = False
    definition_span: Optional[Span] = None
    is_extern: bool = False  # True for extern "C" functions


class SymbolTable:
    """Symbol table for tracking variable bindings"""
    
    def __init__(self, parent: Optional['SymbolTable'] = None):
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.functions: Dict[str, Symbol] = {}
        self.types: Dict[str, Type] = {}  # Struct and enum types
    
    def enter_scope(self) -> 'SymbolTable':
        """Create a child scope"""
        return SymbolTable(parent=self)
    
    def exit_scope(self) -> Optional['SymbolTable']:
        """Exit to parent scope"""
        return self.parent
    
    def define(self, name: str, symbol: Symbol):
        """Define a symbol in current scope"""
        if name in self.symbols:
            return False  # Already defined
        self.symbols[name] = symbol
        return True
    
    def define_function(self, name: str, symbol: Symbol):
        """Define a function (in separate namespace)"""
        if name in self.functions:
            return False
        self.functions[name] = symbol
        return True
    
    def define_type(self, name: str, typ: Type):
        """Define a type (struct or enum)"""
        if name in self.types:
            return False
        self.types[name] = typ
        return True
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol (searches parent scopes)"""
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent.lookup(name)
        return None
    
    def lookup_function(self, name: str) -> Optional[Symbol]:
        """Look up a function"""
        if name in self.functions:
            return self.functions[name]
        elif self.parent:
            return self.parent.lookup_function(name)
        return None
    
    def lookup_type(self, name: str) -> Optional[Type]:
        """Look up a type"""
        if name in self.types:
            return self.types[name]
        elif self.parent:
            return self.parent.lookup_type(name)
        return None
    
    def is_defined_in_current_scope(self, name: str) -> bool:
        """Check if name is defined in current scope (not parent)"""
        return name in self.symbols or name in self.functions
    
    def get_all_symbols(self) -> Dict[str, Symbol]:
        """Get all symbols including parent scopes"""
        result = {}
        if self.parent:
            result.update(self.parent.get_all_symbols())
        result.update(self.symbols)
        return result


class NameResolver:
    """Resolves names to their definitions"""
    
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.errors: List[str] = []
    
    def error(self, message: str, span: Optional[Span] = None):
        """Record an error"""
        if span:
            self.errors.append(f"{span}: {message}")
        else:
            self.errors.append(message)
    
    def enter_scope(self):
        """Enter a new scope"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_VLOOKUP') == '1'
        if debug:
            print(f"[VLOOKUP] Entering new scope from {id(self.current_scope)}")
        self.current_scope = self.current_scope.enter_scope()
        if debug:
            print(f"[VLOOKUP] New scope: {id(self.current_scope)}, parent: {id(self.current_scope.parent)}")
    
    def exit_scope(self):
        """Exit current scope"""
        parent = self.current_scope.exit_scope()
        if parent:
            self.current_scope = parent
    
    def define_variable(self, name: str, typ: Type, mutable: bool, span: Optional[Span] = None) -> bool:
        """Define a variable in current scope"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_VLOOKUP') == '1'
        if debug:
            print(f"[VLOOKUP] Defining variable '{name}' with type {typ} in scope {id(self.current_scope)}")
        if self.current_scope.is_defined_in_current_scope(name):
            self.error(f"Variable '{name}' is already defined", span)
            return False
        
        symbol = Symbol(name=name, type=typ, mutable=mutable, definition_span=span)
        result = self.current_scope.define(name, symbol)
        if debug:
            print(f"[VLOOKUP] Variable '{name}' defined: {result}, symbols now: {list(self.current_scope.symbols.keys())}")
        return result
    
    def define_function(self, name: str, func_type: FunctionType, span: Optional[Span] = None, is_extern: bool = False) -> bool:
        """Define a function
        
        Allows idempotent re-registration of extern functions with the same signature.
        """
        existing_symbol = self.global_scope.lookup_function(name)
        if existing_symbol:
            # Check if both are extern functions with the same signature
            if existing_symbol.is_extern and is_extern:
                # Compare function signatures
                if isinstance(existing_symbol.type, FunctionType) and isinstance(func_type, FunctionType):
                    if existing_symbol.type == func_type:
                        # Same extern function with same signature - idempotent, allow it
                        return True
                    else:
                        # Different signatures - conflict
                        self.error(f"Function '{name}' is already defined with different signature", span)
                        return False
                else:
                    # Type mismatch - conflict
                    self.error(f"Function '{name}' is already defined with different type", span)
                    return False
            else:
                # One is extern and other is not, or both are non-extern - conflict
                self.error(f"Function '{name}' is already defined", span)
                return False
        
        symbol = Symbol(name=name, type=func_type, definition_span=span, is_extern=is_extern)
        return self.global_scope.define_function(name, symbol)
    
    def define_type(self, name: str, typ: Type, span: Optional[Span] = None) -> bool:
        """Define a type (struct or enum)
        
        Allows idempotent re-registration of generic type parameters (TypeVariable)
        with the same name, enabling multiple type definitions to use the same
        generic parameter name (e.g., both Option[T] and Result[T] can use 'T').
        """
        existing_type = self.global_scope.lookup_type(name)
        if existing_type:
            # Allow redefinition if existing type is UNKNOWN (builtin placeholder)
            # This allows users to define their own types that shadow builtins
            from ..types import UNKNOWN, UnknownType, TypeVariable
            # Use isinstance check since UNKNOWN is a singleton UnknownType instance
            if existing_type is UNKNOWN or isinstance(existing_type, UnknownType):
                # Remove the placeholder and define the real type
                if name in self.global_scope.types:
                    del self.global_scope.types[name]
            elif isinstance(existing_type, TypeVariable) and isinstance(typ, TypeVariable):
                # Allow idempotent re-registration of generic type parameters
                # Multiple type definitions can use the same generic parameter name
                # (e.g., Option[T] and Result[T] both use 'T')
                # Since TypeVariable equality is based on name, they're equivalent
                return True  # Already defined with same name, idempotent
            else:
                self.error(f"Type '{name}' is already defined", span)
                return False
        
        return self.global_scope.define_type(name, typ)
    
    def lookup_variable(self, name: str, span: Optional[Span] = None) -> Optional[Symbol]:
        """Look up a variable"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_VLOOKUP') == '1'
        if debug:
            print(f"[VLOOKUP] lookup_variable('{name}') in scope {id(self.current_scope)}")
        symbol = self.current_scope.lookup(name)
        if debug:
            if symbol:
                print(f"[VLOOKUP] Found '{name}' -> {symbol.type} in scope {id(self.current_scope)}")
            else:
                print(f"[VLOOKUP] '{name}' not found in scope chain")
        if not symbol:
            self.error(f"Undefined variable '{name}'", span)
        return symbol
    
    def lookup_function(self, name: str, span: Optional[Span] = None) -> Optional[Symbol]:
        """Look up a function"""
        symbol = self.global_scope.lookup_function(name)
        if not symbol:
            # Also check if it's a variable (could be function pointer)
            return self.lookup_variable(name, span)
        return symbol
    
    def lookup_type(self, name: str, span: Optional[Span] = None) -> Optional[Type]:
        """Look up a type"""
        typ = self.global_scope.lookup_type(name)
        if not typ:
            self.error(f"Undefined type '{name}'", span)
        return typ
    
    def has_errors(self) -> bool:
        """Check if any errors were encountered"""
        return len(self.errors) > 0

