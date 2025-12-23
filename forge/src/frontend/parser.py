"""Parser for Pyrite programming language.

This module provides syntax parsing for Pyrite. It converts a stream of tokens
into an Abstract Syntax Tree (AST) representing the program structure.

Main Components:
    Parser: Main parser class that builds AST from tokens
    parse(): Convenience function to parse tokens into AST
    ParseError: Exception raised on parsing errors

See Also:
    lexer: Tokenizes source code into tokens
    ast: AST node definitions
    type_checker: Type checks the parsed AST
"""

from typing import Any, List, Optional
from .tokens import Token, TokenType, Span
from .. import ast


class ParseError(Exception):
    """Parse error exception"""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


class Parser:
    """Recursive descent parser for Pyrite"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
    
    def current(self) -> Token:
        """Get current token"""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[self.pos]
    
    def peek(self, offset: int = 0) -> Token:
        """Peek ahead at token"""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]
    
    def is_eof(self) -> bool:
        """Check if at end of file"""
        return self.current().type == TokenType.EOF
    
    def advance(self) -> Token:
        """Consume and return current token"""
        token = self.current()
        if not self.is_eof():
            self.pos += 1
        return token
    
    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type"""
        token = self.current()
        if token.type != token_type:
            raise ParseError(
                f"Expected {token_type.name}, got {token.type.name}",
                token.span
            )
        return self.advance()
    
    def match_token(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types"""
        return self.current().type in token_types
    
    def skip_newlines(self):
        """Skip NEWLINE tokens"""
        while self.match_token(TokenType.NEWLINE):
            self.advance()
    
    def parse_program(self) -> ast.Program:
        """Parse a complete program"""
        start_span = self.current().span
        
        imports = []
        items = []
        
        self.skip_newlines()
        
        # Parse imports
        while self.match_token(TokenType.IMPORT):
            imports.append(self.parse_import())
            self.skip_newlines()
        
        # Parse items (functions, structs, enums, etc.)
        while not self.is_eof():
            self.skip_newlines()
            if self.is_eof():
                break
            items.append(self.parse_item())
            self.skip_newlines()
        
        return ast.Program(
            imports=imports,
            items=items,
            span=self.make_span(start_span)
        )
    
    def parse_import(self) -> ast.ImportStmt:
        """Parse import statement"""
        start_span = self.current().span
        self.expect(TokenType.IMPORT)
        
        # Parse module path: std::collections or graphics.image
        path = []
        path.append(self.expect(TokenType.IDENTIFIER).value)
        
        # Support both :: and . for qualified imports
        while self.match_token(TokenType.DOUBLE_COLON, TokenType.DOT):
            self.advance()
            path.append(self.expect(TokenType.IDENTIFIER).value)
        
        # Parse optional alias
        alias = None
        if self.match_token(TokenType.AS):
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value
        
        self.expect(TokenType.NEWLINE)
        
        return ast.ImportStmt(
            path=path,
            alias=alias,
            span=self.make_span(start_span)
        )
    
    def parse_item(self) -> ast.Item:
        """Parse a top-level item"""
        # Parse attributes before the item
        attributes = self.parse_attributes()
        
        if self.match_token(TokenType.EXTERN):
            item = self.parse_extern()
        elif self.match_token(TokenType.FN, TokenType.UNSAFE):
            item = self.parse_function()
        elif self.match_token(TokenType.STRUCT):
            item = self.parse_struct()
        elif self.match_token(TokenType.ENUM):
            item = self.parse_enum()
        elif self.match_token(TokenType.TRAIT):
            item = self.parse_trait()
        elif self.match_token(TokenType.IMPL):
            item = self.parse_impl()
        elif self.match_token(TokenType.CONST):
            item = self.parse_const()
        elif self.match_token(TokenType.TYPE):
            item = self.parse_type_alias()
        elif self.current().value == "opaque" and self.match_token(TokenType.IDENTIFIER):
            item = self.parse_opaque_type()
        else:
            raise ParseError(
                f"Expected item (fn, struct, enum, impl, const, type, opaque type), got {self.current().type.name}",
                self.current().span
            )
        
        # Attach attributes to the item if it supports them
        if hasattr(item, 'attributes'):
            item.attributes = attributes
        elif attributes:
            # For items that don't support attributes yet, just ignore them
            # This allows parsing to succeed even if we don't store attributes
            pass
        
        return item
    
    def parse_extern(self) -> ast.FunctionDef:
        """Parse extern function declaration: extern "C" fn name(...)"""
        start_span = self.current().span
        self.expect(TokenType.EXTERN)
        
        # Parse ABI string: "C", "Rust", etc.
        abi = "C"  # Default
        if self.match_token(TokenType.STRING):
            abi = self.advance().value
        
        # Parse function signature (no body)
        self.expect(TokenType.FN)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic and compile-time parameters
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        # Parameters
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list()
        self.expect(TokenType.RPAREN)
        
        # Return type
        return_type = None
        if self.match_token(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type()
        
        # No body for extern functions - just a declaration
        self.expect(TokenType.NEWLINE)
        
        # Create empty body (extern functions have no implementation)
        body = ast.Block(statements=[], span=self.current().span)
        
        return ast.FunctionDef(
            name=name,
            generic_params=generic_params,
            compile_time_params=compile_time_params,
            params=params,
            return_type=return_type,
            body=body,
            is_unsafe=False,  # extern is implicitly unsafe
            is_extern=True,
            extern_abi=abi,
            attributes=[],  # Attributes are attached in parse_item
            span=self.make_span(start_span)
        )
    
    def parse_function(self) -> ast.FunctionDef:
        """Parse function definition"""
        start_span = self.current().span
        
        # Optional unsafe keyword
        is_unsafe = False
        if self.match_token(TokenType.UNSAFE):
            is_unsafe = True
            self.advance()
        
        self.expect(TokenType.FN)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic and compile-time parameters
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        # Parameters
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list()
        self.expect(TokenType.RPAREN)
        
        # Return type
        return_type = None
        if self.match_token(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type()
        
        # Optional where clause
        where_clause = []
        if self.current().value == "where" and self.match_token(TokenType.IDENTIFIER):
            where_clause = self.parse_where_clause()
        
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        
        # Body
        body = self.parse_block()
        
        return ast.FunctionDef(
            name=name,
            generic_params=generic_params,
            compile_time_params=compile_time_params,
            params=params,
            return_type=return_type,
            body=body,
            is_unsafe=is_unsafe,
            is_extern=False,
            extern_abi=None,
            where_clause=where_clause,
            span=self.make_span(start_span)
        )
    
    def parse_generic_params(self) -> tuple[List[ast.GenericParam], List[Any]]:
        """
        Parse generic parameters: [T, U: Trait, N: int, Flag: bool]
        Returns (type_params, compile_time_params)
        """
        self.expect(TokenType.LBRACKET)
        type_params = []
        compile_time_params = []
        
        while not self.match_token(TokenType.RBRACKET):
            start_span = self.current().span
            name = self.expect(TokenType.IDENTIFIER).value
            
            if self.match_token(TokenType.COLON):
                self.advance()
                # Check if it's a compile-time parameter
                # First check for function type: fn[...]
                if self.match_token(TokenType.FN):
                    # Compile-time function parameter: Body: fn[int] -> int
                    self.advance()
                    self.expect(TokenType.LBRACKET)
                    
                    # Parse parameter types
                    param_types = []
                    while not self.match_token(TokenType.RBRACKET):
                        param_types.append(self.parse_type())
                        if not self.match_token(TokenType.RBRACKET):
                            self.expect(TokenType.COMMA)
                    
                    self.expect(TokenType.RBRACKET)
                    
                    # Optional return type
                    return_type = None
                    if self.match_token(TokenType.ARROW):
                        self.advance()
                        return_type = self.parse_type()
                    
                    compile_time_params.append(ast.CompileTimeFunctionParam(
                        name=name,
                        param_types=param_types,
                        return_type=return_type,
                        span=self.make_span(start_span)
                    ))
                else:
                    # Check if it's int or bool
                    param_type_name = self.current().value if self.match_token(TokenType.IDENTIFIER) else None
                    
                    if param_type_name in ('int', 'bool'):
                        # Compile-time parameter: N: int or Flag: bool
                        self.advance()
                        if param_type_name == 'int':
                            compile_time_params.append(ast.CompileTimeIntParam(
                                name=name,
                                span=self.make_span(start_span)
                            ))
                        else:  # bool
                            compile_time_params.append(ast.CompileTimeBoolParam(
                                name=name,
                                span=self.make_span(start_span)
                            ))
                    else:
                        # Type parameter with trait bounds: T: Trait
                        trait_bounds = []
                        if param_type_name:
                            trait_bounds.append(param_type_name)
                            self.advance()
                            
                            while self.match_token(TokenType.PLUS):
                                self.advance()
                                trait_bounds.append(self.expect(TokenType.IDENTIFIER).value)
                        
                        type_params.append(ast.GenericParam(
                            name=name,
                            trait_bounds=trait_bounds,
                            span=self.make_span(start_span)
                        ))
            else:
                # Type parameter without bounds: T
                type_params.append(ast.GenericParam(
                    name=name,
                    trait_bounds=[],
                    span=self.make_span(start_span)
                ))
            
            if not self.match_token(TokenType.RBRACKET):
                self.expect(TokenType.COMMA)
        
        self.expect(TokenType.RBRACKET)
        return (type_params, compile_time_params)
    
    def parse_param_list(self) -> List[ast.Param]:
        """Parse function parameters"""
        params = []
        
        # Skip newlines after opening parenthesis
        self.skip_newlines()
        
        # Check for indented parameter list (multi-line)
        has_indent = False
        if self.match_token(TokenType.INDENT):
            has_indent = True
            self.advance()
        
        while True:
            # Skip newlines before parameter
            self.skip_newlines()
            
            # Check for closing paren or DEDENT (end of indented block)
            if self.match_token(TokenType.RPAREN):
                break
            if has_indent and self.match_token(TokenType.DEDENT):
                # Consume DEDENT and check for RPAREN
                self.advance()
                if self.match_token(TokenType.RPAREN):
                    break
            
            start_span = self.current().span
            
            # Check for &self or &mut self (method receiver) - shorthand syntax
            if self.match_token(TokenType.AMPERSAND):
                self.advance()
                is_mut = False
                if self.current().value == "mut" and self.match_token(TokenType.IDENTIFIER):
                    is_mut = True
                    self.advance()
                
                # Expect 'self'
                if self.current().value == "self" and self.match_token(TokenType.IDENTIFIER):
                    self.advance()
                    # Create a reference type for self
                    self_type = ast.ReferenceType(
                        mutable=is_mut,
                        inner=ast.PrimitiveType(name="Self", span=start_span),
                        span=self.make_span(start_span)
                    )
                    params.append(ast.Param(
                        name="self",
                        type_annotation=self_type,
                        span=self.make_span(start_span)
                    ))
                else:
                    raise ParseError("Expected 'self' after '&'", self.current().span)
            else:
                # Check for bare 'self' parameter (without & or &mut)
                if self.current().value == "self" and self.match_token(TokenType.IDENTIFIER):
                    self.advance()
                    # Check for explicit type annotation: self: &Type or self: &mut Type
                    if self.match_token(TokenType.COLON):
                        self.advance()
                        # Check for reference type
                        is_mut = False
                        if self.match_token(TokenType.AMPERSAND):
                            self.advance()
                            if self.current().value == "mut" and self.match_token(TokenType.IDENTIFIER):
                                is_mut = True
                                self.advance()
                            type_annotation = self.parse_type()
                            self_type = ast.ReferenceType(
                                mutable=is_mut,
                                inner=type_annotation,
                                span=self.make_span(start_span)
                            )
                        else:
                            # Bare self with explicit type (moved)
                            self_type = self.parse_type()
                        params.append(ast.Param(
                            name="self",
                            type_annotation=self_type,
                            span=self.make_span(start_span)
                        ))
                    else:
                        # Bare self parameter (moved, not borrowed) - implicit Self type
                        self_type = ast.PrimitiveType(name="Self", span=start_span)
                        params.append(ast.Param(
                            name="self",
                            type_annotation=self_type,
                            span=self.make_span(start_span)
                        ))
                else:
                    # Regular parameter: name: Type
                    name = self.expect(TokenType.IDENTIFIER).value
                    self.expect(TokenType.COLON)
                    type_annotation = self.parse_type()
                    
                    params.append(ast.Param(
                        name=name,
                        type_annotation=type_annotation,
                        span=self.make_span(start_span)
                    ))
            
            # Skip newlines after parameter
            self.skip_newlines()
            
            # Check for closing paren or DEDENT
            if self.match_token(TokenType.RPAREN):
                break
            if has_indent and self.match_token(TokenType.DEDENT):
                self.advance()
                if self.match_token(TokenType.RPAREN):
                    break
            
            # Expect comma if not at end
            self.expect(TokenType.COMMA)
            self.skip_newlines()
        
        return params
    
    def parse_struct(self) -> ast.StructDef:
        """Parse struct definition"""
        start_span = self.current().span
        self.expect(TokenType.STRUCT)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic and compile-time parameters
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        # Optional where clause
        where_clause = []
        if self.current().value == "where" and self.match_token(TokenType.IDENTIFIER):
            where_clause = self.parse_where_clause()
        
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        
        # Parse fields
        fields = []
        while not self.match_token(TokenType.DEDENT):
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                break
            
            field_start = self.current().span
            field_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COLON)
            field_type = self.parse_type()
            self.expect(TokenType.NEWLINE)
            
            fields.append(ast.Field(
                name=field_name,
                type_annotation=field_type,
                span=self.make_span(field_start)
            ))
        
        self.expect(TokenType.DEDENT)
        
        return ast.StructDef(
            name=name,
            generic_params=generic_params,
            compile_time_params=compile_time_params,
            fields=fields,
            where_clause=where_clause,
            span=self.make_span(start_span)
        )
    
    def parse_enum(self) -> ast.EnumDef:
        """Parse enum definition"""
        start_span = self.current().span
        self.expect(TokenType.ENUM)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic and compile-time parameters
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        
        # Parse variants
        variants = []
        while not self.match_token(TokenType.DEDENT):
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                break
            
            variant_start = self.current().span
            # Variant names can be identifiers or None keyword
            if self.match_token(TokenType.IDENTIFIER):
                variant_name = self.advance().value
            elif self.match_token(TokenType.NONE):
                self.advance()
                variant_name = "None"
            else:
                raise ParseError(f"Expected variant name, got {self.current().type.name}", self.current().span)
            
            # Optional fields
            fields = None
            if self.match_token(TokenType.LPAREN):
                self.advance()
                fields = []
                
                while not self.match_token(TokenType.RPAREN):
                    field_start = self.current().span
                    field_name = self.expect(TokenType.IDENTIFIER).value
                    self.expect(TokenType.COLON)
                    field_type = self.parse_type()
                    
                    fields.append(ast.Field(
                        name=field_name,
                        type_annotation=field_type,
                        span=self.make_span(field_start)
                    ))
                    
                    if not self.match_token(TokenType.RPAREN):
                        self.expect(TokenType.COMMA)
                
                self.expect(TokenType.RPAREN)
            
            self.expect(TokenType.NEWLINE)
            
            variants.append(ast.Variant(
                name=variant_name,
                fields=fields,
                span=self.make_span(variant_start)
            ))
        
        self.expect(TokenType.DEDENT)
        
        return ast.EnumDef(
            name=name,
            generic_params=generic_params,
            compile_time_params=compile_time_params,
            variants=variants,
            span=self.make_span(start_span)
        )
    
    def parse_trait(self) -> ast.TraitDef:
        """Parse trait definition"""
        start_span = self.current().span
        self.expect(TokenType.TRAIT)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic parameters
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        # Optional where clause
        where_clause = []
        if self.current().value == "where" and self.match_token(TokenType.IDENTIFIER):
            where_clause = self.parse_where_clause()
        
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        
        # Parse trait methods
        methods = []
        associated_types = []
        
        while not self.match_token(TokenType.DEDENT):
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                break
            
            # Check if it's an associated type or method
            if self.match_token(TokenType.TYPE):
                # Associated type: type Item
                self.advance()  # Skip 'type'
                assoc_name = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.NEWLINE)
                
                associated_types.append(ast.AssociatedType(
                    name=assoc_name,
                    bounds=[],
                    span=self.current().span
                ))
            else:
                # Trait method (with or without default implementation)
                method = self.parse_trait_method()
                methods.append(method)
        
        self.expect(TokenType.DEDENT)
        
        return ast.TraitDef(
            name=name,
            generic_params=generic_params,
            methods=methods,
            associated_types=associated_types,
            where_clause=where_clause,
            span=self.make_span(start_span)
        )
    
    def parse_trait_method(self) -> ast.TraitMethod:
        """Parse a method in a trait definition"""
        start_span = self.current().span
        self.expect(TokenType.FN)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic and compile-time parameters
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        # Parameters
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list()
        self.expect(TokenType.RPAREN)
        
        # Return type
        return_type = None
        if self.match_token(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type()
        
        # Check for default implementation
        default_body = None
        if self.match_token(TokenType.COLON):
            self.advance()
            self.expect(TokenType.NEWLINE)
            default_body = self.parse_block()
        else:
            # No default implementation - just a signature
            self.expect(TokenType.NEWLINE)
        
        return ast.TraitMethod(
            name=name,
            generic_params=generic_params,
            compile_time_params=compile_time_params,
            params=params,
            return_type=return_type,
            default_body=default_body,
            span=self.make_span(start_span)
        )
    
    def parse_impl(self) -> ast.ImplBlock:
        """Parse impl block: impl Type: or impl Trait for Type:"""
        start_span = self.current().span
        self.expect(TokenType.IMPL)
        
        # Generic parameters for the impl
        generic_params = []
        compile_time_params = []
        if self.match_token(TokenType.LBRACKET):
            generic_params, compile_time_params = self.parse_generic_params()
        
        # Parse first identifier (could be trait name or type name)
        first_name = self.expect(TokenType.IDENTIFIER).value
        
        # Check if this is "impl Trait for Type" or "impl Type"
        trait_name = None
        type_name = first_name
        
        if self.match_token(TokenType.FOR):
            # impl Trait for Type
            trait_name = first_name
            self.advance()  # Skip 'for'
            type_name = self.expect(TokenType.IDENTIFIER).value
            
            # Handle generic type arguments: List[T]
            if self.match_token(TokenType.LBRACKET):
                # For now, just skip the generic args
                # Full implementation would parse and store them
                bracket_depth = 1
                self.advance()
                while bracket_depth > 0:
                    if self.match_token(TokenType.LBRACKET):
                        bracket_depth += 1
                        self.advance()
                    elif self.match_token(TokenType.RBRACKET):
                        bracket_depth -= 1
                        self.advance()
                    else:
                        self.advance()
        else:
            # impl Type[T] - handle generic type arguments on the type itself
            if self.match_token(TokenType.LBRACKET):
                # For now, just skip the generic args
                # Full implementation would parse and store them
                bracket_depth = 1
                self.advance()
                while bracket_depth > 0:
                    if self.match_token(TokenType.LBRACKET):
                        bracket_depth += 1
                        self.advance()
                    elif self.match_token(TokenType.RBRACKET):
                        bracket_depth -= 1
                        self.advance()
                    else:
                        self.advance()
        
        # Optional where clause
        where_clause = []
        if self.current().value == "where" and self.match_token(TokenType.IDENTIFIER):
            where_clause = self.parse_where_clause()
        
        self.expect(TokenType.COLON)
        
        # Check for alternative syntax: impl Type: Trait: (instead of impl Trait for Type:)
        if self.match_token(TokenType.IDENTIFIER):
            # This is impl Type: Trait: syntax - swap trait_name and type_name
            alt_trait_name = self.advance().value
            # The first_name was the type, alt_trait_name is the trait
            trait_name = alt_trait_name
            # type_name is already set correctly from first_name
            # Now expect the second colon
            self.expect(TokenType.COLON)
        
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        
        methods = []
        associated_type_impls = []
        
        while not self.match_token(TokenType.DEDENT):
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                break
            
            # Check for associated type implementation
            if self.match_token(TokenType.TYPE):
                # type Item = ConcreteType
                self.advance()  # Skip 'type'
                assoc_name = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.ASSIGN)
                assoc_type = self.parse_type()
                self.expect(TokenType.NEWLINE)
                associated_type_impls.append((assoc_name, assoc_type))
            else:
                methods.append(self.parse_function())
        
        self.expect(TokenType.DEDENT)
        
        return ast.ImplBlock(
            trait_name=trait_name,
            type_name=type_name,
            generic_params=generic_params,
            where_clause=where_clause,
            methods=methods,
            associated_type_impls=associated_type_impls,
            span=self.make_span(start_span)
        )
    
    def parse_where_clause(self) -> List[tuple[str, List[str]]]:
        """Parse where clause: where T: Trait1 + Trait2, U: Trait3"""
        self.advance()  # Skip 'where'
        clauses = []
        
        while True:
            # Type parameter name
            type_param = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COLON)
            
            # Trait bounds
            bounds = [self.expect(TokenType.IDENTIFIER).value]
            while self.match_token(TokenType.PLUS):
                self.advance()
                bounds.append(self.expect(TokenType.IDENTIFIER).value)
            
            clauses.append((type_param, bounds))
            
            # Check for more clauses
            if not self.match_token(TokenType.COMMA):
                break
            self.advance()
        
        return clauses
    
    def parse_const(self) -> ast.ConstDecl:
        """Parse constant declaration"""
        start_span = self.current().span
        self.expect(TokenType.CONST)
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Optional type annotation
        type_annotation = None
        if self.match_token(TokenType.COLON):
            self.advance()
            type_annotation = self.parse_type()
        
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect(TokenType.NEWLINE)
        
        return ast.ConstDecl(
            name=name,
            type_annotation=type_annotation,
            value=value,
            span=self.make_span(start_span)
        )
    
    def parse_opaque_type(self) -> ast.OpaqueTypeDecl:
        """Parse opaque type declaration: opaque type OpaqueHandle;"""
        start_span = self.current().span
        # Current token is "opaque" (already matched)
        self.advance()  # Skip "opaque"
        # Next should be "type" (now a keyword)
        if not self.match_token(TokenType.TYPE):
            raise ParseError("Expected 'type' after 'opaque'", self.current().span)
        self.advance()  # Skip "type"
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.SEMICOLON)
        self.expect(TokenType.NEWLINE)
        
        return ast.OpaqueTypeDecl(
            name=name,
            span=self.make_span(start_span)
        )
    
    def parse_attributes(self) -> List[ast.Attribute]:
        """Parse attributes: @attribute or #[attribute]"""
        attributes = []
        
        while True:
            attr = None
            
            # Parse @attribute
            if self.match_token(TokenType.AT_SIGN):
                start_span = self.current().span
                self.advance()
                name = self.expect(TokenType.IDENTIFIER).value
                
                # Parse optional arguments: @attr(args) or @attr(key=value, ...)
                args = []
                if self.match_token(TokenType.LPAREN):
                    self.advance()
                    # Parse arguments (key=value or just value)
                    while not self.match_token(TokenType.RPAREN):
                        # Check for key=value syntax
                        if self.match_token(TokenType.IDENTIFIER):
                            key = self.advance().value
                            if self.match_token(TokenType.ASSIGN):
                                self.advance()
                                # Parse value
                                if self.match_token(TokenType.IDENTIFIER):
                                    value = self.advance().value
                                    args.append(f"{key}={value}")
                                elif self.match_token(TokenType.INTEGER):
                                    value = str(self.advance().value)
                                    args.append(f"{key}={value}")
                                elif self.match_token(TokenType.STRING):
                                    value = self.advance().value
                                    args.append(f"{key}={value}")
                                else:
                                    args.append(f"{key}=")
                            else:
                                # Just an identifier, no =value
                                args.append(key)
                        elif self.match_token(TokenType.STRING):
                            args.append(self.advance().value)
                        elif self.match_token(TokenType.INTEGER):
                            args.append(str(self.advance().value))
                        else:
                            break
                        if not self.match_token(TokenType.RPAREN):
                            self.expect(TokenType.COMMA)
                    self.expect(TokenType.RPAREN)
                
                attr = ast.Attribute(
                    name=name,
                    args=args,
                    span=self.make_span(start_span)
                )
                self.expect(TokenType.NEWLINE)
            
            # Parse #[attribute]
            elif self.match_token(TokenType.HASH):
                start_span = self.current().span
                self.advance()
                self.expect(TokenType.LBRACKET)
                name = self.expect(TokenType.IDENTIFIER).value
                
                # Parse optional arguments: #[attr(args)] or #[attr(key=value, ...)]
                args = []
                if self.match_token(TokenType.LPAREN):
                    self.advance()
                    # Parse arguments (key=value or just value)
                    while not self.match_token(TokenType.RPAREN):
                        # Check for key=value syntax
                        if self.match_token(TokenType.IDENTIFIER):
                            key = self.advance().value
                            if self.match_token(TokenType.ASSIGN):
                                self.advance()
                                # Parse value
                                if self.match_token(TokenType.IDENTIFIER):
                                    value = self.advance().value
                                    args.append(f"{key}={value}")
                                elif self.match_token(TokenType.INTEGER):
                                    value = str(self.advance().value)
                                    args.append(f"{key}={value}")
                                elif self.match_token(TokenType.STRING):
                                    value = self.advance().value
                                    args.append(f"{key}={value}")
                                else:
                                    args.append(f"{key}=")
                            else:
                                # Just an identifier, no =value
                                args.append(key)
                        elif self.match_token(TokenType.STRING):
                            args.append(self.advance().value)
                        elif self.match_token(TokenType.INTEGER):
                            args.append(str(self.advance().value))
                        else:
                            break
                        if not self.match_token(TokenType.RPAREN):
                            self.expect(TokenType.COMMA)
                    self.expect(TokenType.RPAREN)
                
                self.expect(TokenType.RBRACKET)
                attr = ast.Attribute(
                    name=name,
                    args=args,
                    span=self.make_span(start_span)
                )
                self.expect(TokenType.NEWLINE)
            else:
                break
            
            if attr:
                attributes.append(attr)
        
        return attributes
    
    def parse_type_alias(self) -> ast.TypeAlias:
        """Parse type alias: type Optional[T] = Option[T]"""
        start_span = self.current().span
        self.expect(TokenType.TYPE)
        
        # Parse alias name
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Parse optional generic parameters: [T, E]
        generic_params = []
        if self.match_token(TokenType.LBRACKET):
            self.advance()
            if not self.match_token(TokenType.RBRACKET):
                # Parse first generic param
                param_name = self.expect(TokenType.IDENTIFIER).value
                generic_params.append(ast.GenericParam(
                    name=param_name,
                    trait_bounds=[],
                    span=self.current().span
                ))
                
                # Parse additional params
                while self.match_token(TokenType.COMMA):
                    self.advance()
                    param_name = self.expect(TokenType.IDENTIFIER).value
                    generic_params.append(ast.GenericParam(
                        name=param_name,
                        trait_bounds=[],
                        span=self.current().span
                    ))
            
            self.expect(TokenType.RBRACKET)
        
        # Parse = sign
        self.expect(TokenType.ASSIGN)
        
        # Parse target type
        target_type = self.parse_type()
        
        # Expect newline
        self.expect(TokenType.NEWLINE)
        
        return ast.TypeAlias(
            name=name,
            generic_params=generic_params,
            target_type=target_type,
            span=self.make_span(start_span)
        )
    
    def parse_block(self) -> ast.Block:
        """Parse a block of statements"""
        start_span = self.current().span
        
        # Allow function bodies to start with comments
        # If we see a NEWLINE instead of INDENT, it means the first line is a comment
        # Skip NEWLINEs until we find the INDENT token (which comes with the first actual statement)
        # The lexer doesn't produce INDENT tokens for comment-only lines, so we need to skip
        # NEWLINE tokens until we find the INDENT that comes with the first statement
        while self.match_token(TokenType.NEWLINE):
            self.advance()
            # After skipping NEWLINE, the next token should be either:
            # - INDENT (from the first statement line)
            # - Another NEWLINE (from another comment line)
            # - DEDENT (if the block is empty)
            if self.match_token(TokenType.INDENT):
                break
            if self.match_token(TokenType.DEDENT):
                # Empty block (only comments)
                self.expect(TokenType.DEDENT)
                return ast.Block(statements=[], span=self.make_span(start_span))
        
        self.expect(TokenType.INDENT)
        
        statements = []
        while not self.match_token(TokenType.DEDENT):
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                break
            
            # Skip additional NEWLINE tokens that may come from comment-only lines
            # Comments are filtered by the lexer, but comment-only lines still produce NEWLINE tokens
            while self.match_token(TokenType.NEWLINE):
                self.advance()
                self.skip_newlines()
                if self.match_token(TokenType.DEDENT):
                    break
            
            if self.match_token(TokenType.DEDENT):
                break
            
            # Workaround for missing DEDENT: if we see a top-level item token after newlines,
            # it means we've exited the block but the lexer didn't produce DEDENT
            # This can happen if the function body ends and the next item starts at column 0
            # Check for top-level item tokens that should not appear in statements
            current = self.current()
            # Check for function declaration: fn identifier (not fn[...] or fn(...))
            if current.type == TokenType.FN:
                peek_token = self.peek(1)  # Next token (offset 1 means current+1)
                if peek_token.type == TokenType.IDENTIFIER:
                    # This is a function declaration, not a closure - we've exited the block
                    break
            # Check for other top-level items
            elif current.type in (TokenType.STRUCT, TokenType.ENUM, TokenType.IMPL, TokenType.TRAIT, TokenType.CONST, TokenType.EXTERN):
                # Other top-level items - we've exited the block
                break
            
            statements.append(self.parse_statement())
        
        # Try to consume DEDENT, but if it's missing and we detected a top-level item above, continue
        if self.match_token(TokenType.DEDENT):
            self.expect(TokenType.DEDENT)
        # Note: If DEDENT is missing but we broke out of the loop due to detecting a top-level item,
        # we continue without consuming DEDENT (workaround for lexer issue)
        
        return ast.Block(
            statements=statements,
            span=self.make_span(start_span)
        )
    
    def parse_statement(self) -> ast.Statement:
        """Parse a statement"""
        # Check for top-level item tokens - these should not appear in statements
        # This is a safety check for parser bugs where we're in the wrong context
        if self.match_token(TokenType.FN) and self.peek().type == TokenType.IDENTIFIER:
            # This looks like a function declaration, not a closure
            # If we're here, the parser is in the wrong context (should be in parse_item, not parse_statement)
            raise ParseError(
                f"Unexpected function declaration in statement context. This may indicate a missing DEDENT token or parser state issue.",
                self.current().span
            )
        
        if self.match_token(TokenType.LET, TokenType.VAR):
            return self.parse_var_decl()
        elif self.match_token(TokenType.RETURN):
            return self.parse_return()
        elif self.match_token(TokenType.BREAK):
            return self.parse_break()
        elif self.match_token(TokenType.CONTINUE):
            return self.parse_continue()
        elif self.match_token(TokenType.IF):
            return self.parse_if()
        elif self.match_token(TokenType.WHILE):
            return self.parse_while()
        elif self.match_token(TokenType.FOR):
            return self.parse_for()
        elif self.match_token(TokenType.MATCH):
            return self.parse_match()
        elif self.match_token(TokenType.DEFER):
            return self.parse_defer()
        elif self.match_token(TokenType.WITH):
            return self.parse_with()
        elif self.match_token(TokenType.UNSAFE):
            return self.parse_unsafe_block()
        elif self.match_token(TokenType.PASS):
            return self.parse_pass()
        else:
            # Try to parse as assignment or expression statement
            return self.parse_assignment_or_expression()
    
    def parse_var_decl(self) -> ast.VarDecl:
        """Parse variable declaration: let name = value or let (a, b) = value"""
        start_span = self.current().span
        
        mutable = self.match_token(TokenType.VAR)
        self.advance()  # consume let or var
        
        # Parse pattern (identifier or tuple)
        pattern = self.parse_pattern()
        
        # Optional type annotation
        type_annotation = None
        if self.match_token(TokenType.COLON):
            self.advance()
            type_annotation = self.parse_type()
        
        self.expect(TokenType.ASSIGN)
        initializer = self.parse_expression()
        
        # Expect NEWLINE after variable declaration
        # Check for DEDENT first (end of block - newline was consumed)
        if self.match_token(TokenType.DEDENT):
            # At end of indented block - newline was consumed by DEDENT
            pass
        elif self.match_token(TokenType.NEWLINE):
            # Consume the NEWLINE
            self.advance()
            # Skip any additional newlines (blank lines)
            self.skip_newlines()
        else:
            # Must have NEWLINE after variable declaration
            # But if we're at a statement keyword, the newline might have been consumed
            # by a multi-line expression (like if-expr). Check for this case.
            if (self.match_token(TokenType.RETURN) or
                self.match_token(TokenType.IF) or
                self.match_token(TokenType.WHILE) or
                self.match_token(TokenType.FOR) or
                self.match_token(TokenType.LET) or
                self.match_token(TokenType.VAR)):
                # Next statement - newline was consumed by multi-line expression
                pass
            else:
                # Must have NEWLINE
                self.expect(TokenType.NEWLINE)
        
        return ast.VarDecl(
            pattern=pattern,
            mutable=mutable,
            type_annotation=type_annotation,
            initializer=initializer,
            span=self.make_span(start_span)
        )
    
    def parse_return(self) -> ast.ReturnStmt:
        """Parse return statement"""
        start_span = self.current().span
        self.expect(TokenType.RETURN)
        
        value = None
        if not self.match_token(TokenType.NEWLINE):
            value = self.parse_expression()
        
        self.expect(TokenType.NEWLINE)
        
        return ast.ReturnStmt(
            value=value,
            span=self.make_span(start_span)
        )
    
    def parse_break(self) -> ast.BreakStmt:
        """Parse break statement"""
        start_span = self.current().span
        self.expect(TokenType.BREAK)
        self.expect(TokenType.NEWLINE)
        return ast.BreakStmt(span=self.make_span(start_span))
    
    def parse_continue(self) -> ast.ContinueStmt:
        """Parse continue statement"""
        start_span = self.current().span
        self.expect(TokenType.CONTINUE)
        self.expect(TokenType.NEWLINE)
        return ast.ContinueStmt(span=self.make_span(start_span))
    
    def parse_pass(self) -> ast.PassStmt:
        """Parse pass statement"""
        start_span = self.current().span
        self.expect(TokenType.PASS)
        # Pass can be followed by NEWLINE or DEDENT
        if self.match_token(TokenType.NEWLINE):
            self.advance()
        return ast.PassStmt(span=self.make_span(start_span))
    
    def parse_if_expression(self) -> ast.Expression:
        """Parse if expression: if cond: expr elif cond: expr else: expr"""
        start_span = self.current().span
        self.expect(TokenType.IF)
        
        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        
        # Parse expression - skip newlines before and after
        self.skip_newlines()
        then_expr = self.parse_expression()
        self.skip_newlines()
        
        # DEDENT should come after the expression
        # Skip newlines first, then check for DEDENT
        self.skip_newlines()
        if self.match_token(TokenType.DEDENT):
            self.advance()  # consume DEDENT
        # If no DEDENT, check if we're at elif/else (expression might have ended)
        # or if we're at the next statement (expression is complete)
        
        elif_clauses = []
        while self.match_token(TokenType.ELIF):
            self.advance()
            elif_condition = self.parse_expression()
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            self.expect(TokenType.INDENT)
            self.skip_newlines()
            elif_expr = self.parse_expression()
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                self.advance()
            elif_clauses.append((elif_condition, elif_expr))
        
        else_expr = None
        if self.match_token(TokenType.ELSE):
            self.advance()
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            self.expect(TokenType.INDENT)
            self.skip_newlines()
            else_expr = self.parse_expression()
            self.skip_newlines()
            # Always expect DEDENT after else expression
            if self.match_token(TokenType.DEDENT):
                self.advance()
            else:
                # If no DEDENT, we might be at the end - but this shouldn't happen
                # The expression should have consumed everything up to DEDENT
                pass
        
        # After parsing if expression, we should be back at the original indentation level
        # The DEDENT after else clause has been consumed, and any trailing newlines should be skipped
        # But we need to leave the parser in a state where the next statement can be parsed
        # So we skip newlines here, but don't consume any DEDENT (that was already done)
        self.skip_newlines()
        
        # Convert if expression to nested ternary expressions
        # if cond1: expr1 elif cond2: expr2 else: expr3
        # becomes: expr1 if cond1 else (expr2 if cond2 else expr3)
        result = else_expr if else_expr else ast.NoneLiteral(span=start_span)
        for elif_cond, elif_expr in reversed(elif_clauses):
            result = ast.TernaryExpr(
                true_expr=elif_expr,
                condition=elif_cond,
                false_expr=result,
                span=self.make_span(start_span)
            )
        result = ast.TernaryExpr(
            true_expr=then_expr,
            condition=condition,
            false_expr=result,
            span=self.make_span(start_span)
        )
        return result
    
    def parse_if(self) -> ast.IfStmt:
        """Parse if statement"""
        start_span = self.current().span
        self.expect(TokenType.IF)
        
        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        then_block = self.parse_block()
        
        # Parse elif clauses
        elif_clauses = []
        while self.match_token(TokenType.ELIF):
            self.advance()
            elif_condition = self.parse_expression()
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            elif_block = self.parse_block()
            elif_clauses.append((elif_condition, elif_block))
        
        # Parse else clause
        else_block = None
        if self.match_token(TokenType.ELSE):
            self.advance()
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            else_block = self.parse_block()
        
        return ast.IfStmt(
            condition=condition,
            then_block=then_block,
            elif_clauses=elif_clauses,
            else_block=else_block,
            span=self.make_span(start_span)
        )
    
    def parse_while(self) -> ast.WhileStmt:
        """Parse while statement"""
        start_span = self.current().span
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = self.parse_block()
        
        return ast.WhileStmt(
            condition=condition,
            body=body,
            span=self.make_span(start_span)
        )
    
    def parse_for(self) -> ast.ForStmt:
        """Parse for statement"""
        start_span = self.current().span
        self.expect(TokenType.FOR)
        variable = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        # Parse iterable expression (which includes ranges like 0..10)
        iterable = self.parse_range_or_expression()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = self.parse_block()
        
        return ast.ForStmt(
            variable=variable,
            iterable=iterable,
            body=body,
            span=self.make_span(start_span)
        )
    
    def parse_range_or_expression(self) -> ast.Expression:
        """Parse expression that might be a range (0..10)"""
        expr = self.parse_comparison()
        
        # Check for range operator
        if self.match_token(TokenType.DOUBLE_DOT):
            self.advance()
            end = self.parse_comparison()
            # Represent range as a binary operation
            return ast.BinOp(
                left=expr,
                op="..",
                right=end,
                span=self.make_span(expr.span)
            )
        
        return expr
    
    def parse_match(self) -> ast.MatchStmt:
        """Parse match statement"""
        start_span = self.current().span
        self.expect(TokenType.MATCH)
        scrutinee = self.parse_expression()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        
        arms = []
        while not self.match_token(TokenType.DEDENT):
            self.skip_newlines()
            if self.match_token(TokenType.DEDENT):
                break
            
            arm_start = self.current().span
            self.expect(TokenType.CASE)
            pattern = self.parse_pattern()
            
            # Optional guard
            guard = None
            if self.match_token(TokenType.IF):
                self.advance()
                guard = self.parse_expression()
            
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            body = self.parse_block()
            
            arms.append(ast.MatchArm(
                pattern=pattern,
                guard=guard,
                body=body,
                span=self.make_span(arm_start)
            ))
        
        self.expect(TokenType.DEDENT)
        
        return ast.MatchStmt(
            scrutinee=scrutinee,
            arms=arms,
            span=self.make_span(start_span)
        )
    
    def parse_defer(self) -> ast.DeferStmt:
        """Parse defer statement"""
        start_span = self.current().span
        self.expect(TokenType.DEFER)
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = self.parse_block()
        
        return ast.DeferStmt(
            body=body,
            span=self.make_span(start_span)
        )
    
    def parse_with(self) -> ast.WithStmt:
        """Parse with statement: with variable = try expression:"""
        start_span = self.current().span
        self.expect(TokenType.WITH)
        variable = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        
        # Require try keyword for error handling
        if not self.match_token(TokenType.TRY):
            raise ParseError(
                f"with statement requires 'try' keyword (syntax: with {variable} = try expression:)",
                self.current().span
            )
        self.expect(TokenType.TRY)
        
        value = self.parse_expression()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = self.parse_block()
        
        return ast.WithStmt(
            variable=variable,
            value=value,
            body=body,
            span=self.make_span(start_span)
        )
    
    def parse_unsafe_block(self) -> ast.UnsafeBlock:
        """Parse unsafe block"""
        start_span = self.current().span
        self.expect(TokenType.UNSAFE)
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        body = self.parse_block()
        
        return ast.UnsafeBlock(
            body=body,
            span=self.make_span(start_span)
        )
    
    def parse_assignment_or_expression(self) -> ast.Statement:
        """Parse assignment or expression statement"""
        start_span = self.current().span
        expr = self.parse_expression()
        
        # Check if it's an assignment
        if self.match_token(TokenType.ASSIGN):
            self.advance()
            value = self.parse_expression()
            self.expect(TokenType.NEWLINE)
            
            return ast.Assignment(
                target=expr,
                value=value,
                span=self.make_span(start_span)
            )
        else:
            self.expect(TokenType.NEWLINE)
            return ast.ExpressionStmt(
                expression=expr,
                span=self.make_span(start_span)
            )
    
    def parse_pattern(self) -> ast.Pattern:
        """Parse a pattern for match arms or variable declarations"""
        start_span = self.current().span
        
        # Tuple pattern: (a, b)
        if self.match_token(TokenType.LPAREN):
            self.advance()
            elements = []
            while not self.match_token(TokenType.RPAREN):
                elements.append(self.parse_pattern())
                if not self.match_token(TokenType.RPAREN):
                    self.expect(TokenType.COMMA)
            self.expect(TokenType.RPAREN)
            return ast.TuplePattern(elements=elements, span=self.make_span(start_span))

        # Wildcard pattern
        if self.match_token(TokenType.IDENTIFIER) and self.current().value == "_":
            self.advance()
            return ast.WildcardPattern(span=self.make_span(start_span))
        
        # Literal or identifier pattern
        if self.match_token(TokenType.INTEGER, TokenType.FLOAT, TokenType.STRING,
                          TokenType.CHAR, TokenType.TRUE, TokenType.FALSE, TokenType.NONE):
            literal = self.parse_primary()
            
            # Check for OR pattern
            if self.match_token(TokenType.PIPE):
                patterns = [ast.LiteralPattern(literal=literal, span=self.make_span(start_span))]
                
                while self.match_token(TokenType.PIPE):
                    self.advance()
                    pat_lit = self.parse_primary()
                    patterns.append(ast.LiteralPattern(literal=pat_lit, span=self.make_span(start_span)))
                
                return ast.OrPattern(patterns=patterns, span=self.make_span(start_span))
            
            return ast.LiteralPattern(literal=literal, span=self.make_span(start_span))
        
        # Identifier pattern (binds variable) or enum pattern
        if self.match_token(TokenType.IDENTIFIER):
            name = self.advance().value
            
            # Check for enum pattern with double colon: Enum::Variant(...)
            if self.match_token(TokenType.DOUBLE_COLON):
                self.advance()
                if self.match_token(TokenType.IDENTIFIER):
                    variant = self.advance().value
                elif self.match_token(TokenType.NONE):
                    self.advance()
                    variant = "None"
                else:
                    raise ParseError(f"Expected variant name after '::', got {self.current().type.name}", self.current().span)
                
                # Optional fields
                fields = None
                if self.match_token(TokenType.LPAREN):
                    self.advance()
                    fields = []
                    while not self.match_token(TokenType.RPAREN):
                        fields.append(self.parse_pattern())
                        if not self.match_token(TokenType.RPAREN):
                            self.expect(TokenType.COMMA)
                    self.expect(TokenType.RPAREN)
                
                return ast.EnumPattern(
                    enum_name=name,
                    variant_name=variant,
                    fields=fields,
                    span=self.make_span(start_span)
                )
            
            # Check for direct enum variant pattern: Variant(...) or Variant(_)
            if self.match_token(TokenType.LPAREN):
                self.advance()
                fields = []
                while not self.match_token(TokenType.RPAREN):
                    fields.append(self.parse_pattern())
                    if not self.match_token(TokenType.RPAREN):
                        self.expect(TokenType.COMMA)
                self.expect(TokenType.RPAREN)
                
                return ast.EnumPattern(
                    enum_name=None,  # Direct variant, enum name inferred from context
                    variant_name=name,
                    fields=fields,
                    span=self.make_span(start_span)
                )
            
            return ast.IdentifierPattern(name=name, span=self.make_span(start_span))
        
        raise ParseError(f"Expected pattern, got {self.current().type.name}", self.current().span)
    
    def parse_expression(self) -> ast.Expression:
        """Parse an expression"""
        return self.parse_ternary()
    
    def parse_ternary(self) -> ast.Expression:
        """Parse ternary expression: a if cond else b"""
        expr = self.parse_logical_or()
        
        if self.match_token(TokenType.IF):
            start_span = expr.span
            self.advance()
            condition = self.parse_logical_or()
            self.expect(TokenType.ELSE)
            false_expr = self.parse_ternary()
            
            return ast.TernaryExpr(
                true_expr=expr,
                condition=condition,
                false_expr=false_expr,
                span=self.make_span(start_span)
            )
        
        return expr
    
    def parse_logical_or(self) -> ast.Expression:
        """Parse logical OR expression"""
        left = self.parse_logical_and()
        
        while self.match_token(TokenType.OR):
            op_token = self.advance()
            right = self.parse_logical_and()
            left = ast.BinOp(
                left=left,
                op="or",
                right=right,
                span=self.make_span(left.span)
            )
        
        return left
    
    def parse_logical_and(self) -> ast.Expression:
        """Parse logical AND expression"""
        left = self.parse_comparison()
        
        while self.match_token(TokenType.AND):
            op_token = self.advance()
            right = self.parse_comparison()
            left = ast.BinOp(
                left=left,
                op="and",
                right=right,
                span=self.make_span(left.span)
            )
        
        return left
    
    def parse_comparison(self) -> ast.Expression:
        """Parse comparison expression"""
        left = self.parse_additive()
        
        if self.match_token(TokenType.EQ, TokenType.NE, TokenType.LT,
                           TokenType.LE, TokenType.GT, TokenType.GE):
            op_token = self.advance()
            op_map = {
                TokenType.EQ: "==",
                TokenType.NE: "!=",
                TokenType.LT: "<",
                TokenType.LE: "<=",
                TokenType.GT: ">",
                TokenType.GE: ">=",
            }
            right = self.parse_additive()
            left = ast.BinOp(
                left=left,
                op=op_map[op_token.type],
                right=right,
                span=self.make_span(left.span)
            )
        
        return left
    
    def parse_additive(self) -> ast.Expression:
        """Parse additive expression (+ -)"""
        left = self.parse_multiplicative()
        
        while self.match_token(TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            op = "+" if op_token.type == TokenType.PLUS else "-"
            right = self.parse_multiplicative()
            left = ast.BinOp(
                left=left,
                op=op,
                right=right,
                span=self.make_span(left.span)
            )
        
        return left
    
    def parse_multiplicative(self) -> ast.Expression:
        """Parse multiplicative expression (* / % @)"""
        left = self.parse_unary()
        
        while self.match_token(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT, TokenType.AT_SIGN):
            op_token = self.advance()
            op_map = {
                TokenType.STAR: "*",
                TokenType.SLASH: "/",
                TokenType.PERCENT: "%",
                TokenType.AT_SIGN: "@",
            }
            right = self.parse_unary()
            left = ast.BinOp(
                left=left,
                op=op_map[op_token.type],
                right=right,
                span=self.make_span(left.span)
            )
        
        return left
    
    def parse_unary(self) -> ast.Expression:
        """Parse unary expression"""
        start_span = self.current().span
        
        if self.match_token(TokenType.NOT):
            self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(
                op="not",
                operand=operand,
                span=self.make_span(start_span)
            )
        
        if self.match_token(TokenType.MINUS):
            self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(
                op="-",
                operand=operand,
                span=self.make_span(start_span)
            )
        
        if self.match_token(TokenType.AMPERSAND):
            self.advance()
            # Check for &mut
            is_mut = False
            if self.match_token(TokenType.IDENTIFIER) and self.current().value == "mut":
                is_mut = True
                self.advance()
            
            operand = self.parse_unary()
            op = "&mut" if is_mut else "&"
            return ast.UnaryOp(
                op=op,
                operand=operand,
                span=self.make_span(start_span)
            )
        
        if self.match_token(TokenType.STAR):
            self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(
                op="*",
                operand=operand,
                span=self.make_span(start_span)
            )
        
        return self.parse_cast()
    
    def parse_cast(self) -> ast.Expression:
        """Parse cast expression (expr as Type)"""
        expr = self.parse_postfix()
        
        while self.match_token(TokenType.AS):
            self.advance()
            target_type = self.parse_type()
            expr = ast.AsExpression(
                expression=expr,
                target_type=target_type,
                span=self.make_span(expr.span)
            )
            
        return expr
    
    def parse_postfix(self) -> ast.Expression:
        """Parse postfix expression (calls, field access, indexing)"""
        expr = self.parse_primary()
        
        while True:
            if self.match_token(TokenType.DOT):
                self.advance()
                # Allow IDENTIFIER or NONE (for enum variants like Option.None)
                if self.match_token(TokenType.IDENTIFIER):
                    field = self.advance().value
                elif self.match_token(TokenType.NONE):
                    self.advance()
                    field = "None"
                else:
                    raise ParseError(
                        f"Expected IDENTIFIER or NONE after '.', got {self.current().type.name}",
                        self.current().span
                    )
                
                # Check if it's a method call
                if self.match_token(TokenType.LPAREN):
                    self.advance()
                    args = self.parse_argument_list()
                    self.expect(TokenType.RPAREN)
                    
                    expr = ast.MethodCall(
                        object=expr,
                        method=field,
                        arguments=args,
                        span=self.make_span(expr.span)
                    )
                else:
                    expr = ast.FieldAccess(
                        object=expr,
                        field=field,
                        span=self.make_span(expr.span)
                    )
            
            elif self.match_token(TokenType.LBRACKET):
                # Could be: array index, slice, or compile-time args
                self.advance()
                
                # Check for slice first (simpler case)
                if self.match_token(TokenType.DOUBLE_DOT):
                    # Slice: expr[..end]
                    self.advance()
                    end = None if self.match_token(TokenType.RBRACKET) else self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    
                    expr = ast.SliceAccess(
                        object=expr,
                        start=None,
                        end=end,
                        span=self.make_span(expr.span)
                    )
                else:
                    # Parse first expression (could be index, slice start, or compile-time arg)
                    first_expr = self.parse_expression()
                    
                    if self.match_token(TokenType.DOUBLE_DOT):
                        # Slice with start: expr[start..end]
                        self.advance()
                        end = None if self.match_token(TokenType.RBRACKET) else self.parse_expression()
                        self.expect(TokenType.RBRACKET)
                        
                        expr = ast.SliceAccess(
                            object=expr,
                            start=first_expr,
                            end=end,
                            span=self.make_span(expr.span)
                        )
                    elif self.match_token(TokenType.COMMA):
                        # Multiple args - must be compile-time args: func[256, true](...)
                        compile_time_args = [first_expr]
                        while self.match_token(TokenType.COMMA):
                            self.advance()
                            compile_time_args.append(self.parse_expression())
                        self.expect(TokenType.RBRACKET)
                        
                        # Must be followed by LPAREN for function call
                        self.expect(TokenType.LPAREN)
                        args = self.parse_argument_list()
                        self.expect(TokenType.RPAREN)
                        
                        expr = ast.FunctionCall(
                            function=expr,
                            compile_time_args=compile_time_args,
                            arguments=args,
                            span=self.make_span(expr.span)
                        )
                    elif self.match_token(TokenType.RBRACKET):
                        # Single arg in brackets
                        self.advance()
                        
                        # Check if followed by LPAREN (compile-time call)
                        if self.match_token(TokenType.LPAREN):
                            # Compile-time function call: func[256](args)
                            self.advance()
                            args = self.parse_argument_list()
                            self.expect(TokenType.RPAREN)
                            
                            expr = ast.FunctionCall(
                                function=expr,
                                compile_time_args=[first_expr],
                                arguments=args,
                                span=self.make_span(expr.span)
                            )
                        else:
                            # Regular index access: arr[0]
                            expr = ast.IndexAccess(
                                object=expr,
                                index=first_expr,
                                span=self.make_span(expr.span)
                            )
                    else:
                        # Unexpected token
                        raise ParseError(f"Expected ']', '..', or ',' after index expression")
            
            elif self.match_token(TokenType.LPAREN):
                # Regular function call (no compile-time args)
                self.advance()
                args = self.parse_argument_list()
                self.expect(TokenType.RPAREN)
                
                expr = ast.FunctionCall(
                    function=expr,
                    compile_time_args=[],  # No compile-time args
                    arguments=args,
                    span=self.make_span(expr.span)
                )
            
            elif self.match_token(TokenType.DOUBLE_COLON):
                # Enum variant access
                start_span = expr.span
                self.advance()
                variant = self.expect(TokenType.IDENTIFIER).value
                
                # For now, treat as a field access (will be resolved in semantic analysis)
                expr = ast.FieldAccess(
                    object=expr,
                    field=variant,
                    span=self.make_span(start_span)
                )
            
            elif self.match_token(TokenType.QUESTION_MARK):
                # Try operator: expr?
                self.advance()
                expr = ast.TryExpr(
                    expression=expr,
                    span=self.make_span(expr.span)
                )
            
            else:
                break
        
        return expr
    
    def parse_argument_list(self) -> List[ast.Expression]:
        """Parse function argument list"""
        args = []
        
        while not self.match_token(TokenType.RPAREN):
            args.append(self.parse_expression())
            if not self.match_token(TokenType.RPAREN):
                self.expect(TokenType.COMMA)
        
        return args
    
    def parse_primary(self) -> ast.Expression:
        """Parse primary expression"""
        start_span = self.current().span
        
        # Integer literal
        if self.match_token(TokenType.INTEGER):
            value = self.advance().value
            return ast.IntLiteral(value=value, span=self.make_span(start_span))
        
        # Float literal
        if self.match_token(TokenType.FLOAT):
            value = self.advance().value
            return ast.FloatLiteral(value=value, span=self.make_span(start_span))
        
        # String literal
        if self.match_token(TokenType.STRING):
            value = self.advance().value
            return ast.StringLiteral(value=value, span=self.make_span(start_span))
        
        # Character literal
        if self.match_token(TokenType.CHAR):
            value = self.advance().value
            return ast.CharLiteral(value=value, span=self.make_span(start_span))
        
        # Boolean literals
        if self.match_token(TokenType.TRUE):
            self.advance()
            return ast.BoolLiteral(value=True, span=self.make_span(start_span))
        
        if self.match_token(TokenType.FALSE):
            self.advance()
            return ast.BoolLiteral(value=False, span=self.make_span(start_span))
        
        # None literal
        if self.match_token(TokenType.NONE):
            self.advance()
            return ast.NoneLiteral(span=self.make_span(start_span))
        
        # Try expression - must parse the full expression, not just primary
        # try get_value() should parse as TryExpr(expression=FunctionCall(...))
        if self.match_token(TokenType.TRY):
            self.advance()
            # Parse the full expression (which may include function calls)
            # We need to parse at the postfix level to handle function calls correctly
            expr = self.parse_postfix()
            return ast.TryExpr(expression=expr, span=self.make_span(start_span))
        
        # If expression: if cond: expr elif cond: expr else: expr
        if self.match_token(TokenType.IF):
            return self.parse_if_expression()
        
        # Closure expression: move fn[...] or fn(...) or move fn(...)
        is_move = False
        if self.match_token(TokenType.MOVE):
            is_move = True
            self.advance()
            self.expect(TokenType.FN)
            return self.parse_closure(is_move=True)
        
        if self.match_token(TokenType.FN):
            return self.parse_closure()
        
        # Parenthesized expression or tuple literal
        if self.match_token(TokenType.LPAREN):
            self.advance()
            # Check if it's a tuple: (expr, expr, ...) or just (expr)
            first_expr = self.parse_expression()
            
            # Check for comma - if present, it's a tuple
            if self.match_token(TokenType.COMMA):
                self.advance()
                elements = [first_expr]
                
                # Parse remaining elements
                while not self.match_token(TokenType.RPAREN):
                    elements.append(self.parse_expression())
                    if not self.match_token(TokenType.RPAREN):
                        self.expect(TokenType.COMMA)
                
                self.expect(TokenType.RPAREN)
                # Return as a tuple literal
                return ast.TupleLiteral(elements=elements, span=self.make_span(start_span))
            else:
                # Single parenthesized expression
                self.expect(TokenType.RPAREN)
                return first_expr
        
        # List literal
        if self.match_token(TokenType.LBRACKET):
            return self.parse_list_literal()
        
        # Identifier (might be struct literal or type expression)
        if self.match_token(TokenType.IDENTIFIER):
            name = self.advance().value
            
            # Check for struct literal
            if self.match_token(TokenType.LBRACE):
                return self.parse_struct_literal(name, start_span)
            
            # Check for generic type instantiation: Map[int, int].new()
            if self.match_token(TokenType.LBRACKET):
                # Peek ahead to see if it's followed by '.' after closing ']'
                # If so, it's a static method call on a generic type
                depth = 0
                look_pos = self.pos
                found_generic = False
                while look_pos < len(self.tokens):
                    tok = self.tokens[look_pos]
                    if tok.type == TokenType.LBRACKET:
                        depth += 1
                    elif tok.type == TokenType.RBRACKET:
                        depth -= 1
                        if depth == 0:
                            # Found matching closing ], check if next is '.'
                            if look_pos + 1 < len(self.tokens) and self.tokens[look_pos + 1].type == TokenType.DOT:
                                found_generic = True
                            break
                    look_pos += 1
                
                if found_generic:
                    self.advance() # consume [
                    type_args = []
                    while not self.match_token(TokenType.RBRACKET):
                        type_args.append(self.parse_type())
                        if not self.match_token(TokenType.RBRACKET):
                            self.expect(TokenType.COMMA)
                    self.expect(TokenType.RBRACKET)
                    
                    return ast.GenericType(
                        name=name,
                        type_args=type_args,
                        span=self.make_span(start_span)
                    )
            
            return ast.Identifier(name=name, span=self.make_span(start_span))
        
        raise ParseError(
            f"Expected expression, got {self.current().type.name}",
            self.current().span
        )
    
    def parse_closure(self, is_move: bool = False) -> ast.Expression:
        """
        Parse closure expression: fn[...] or fn(...)
        fn[...] = parameter closure (compile-time, zero-cost)
        fn(...) = runtime closure (first-class, may allocate)
        """
        start_span = self.current().span
        if not is_move:
            self.expect(TokenType.FN)
        
        # Check if it's a parameter closure or runtime closure
        if self.match_token(TokenType.LBRACKET):
            # Parameter closure: fn[i: int]: body
            return self.parse_parameter_closure(start_span, is_move=is_move)
        elif self.match_token(TokenType.LPAREN):
            # Runtime closure: fn(x: int) -> bool: body
            return self.parse_runtime_closure(start_span, is_move=is_move)
        elif self.match_token(TokenType.IDENTIFIER):
            # This looks like a function declaration (fn name(...)), not a closure
            # If we're here, the parser is in the wrong context (should be in parse_item, not parse_expression)
            # This typically indicates a missing DEDENT token or parser state issue
            raise ParseError(
                f"Unexpected function declaration in expression context. Expected closure syntax 'fn[...]' or 'fn(...)', but found 'fn {self.current().value}'. This may indicate a missing DEDENT token after the previous function body.",
                self.current().span
            )
        else:
            raise ParseError(
                f"Expected '[' or '(' after 'fn', got {self.current().type.name}",
                self.current().span
            )
    
    def parse_parameter_closure(self, start_span: Span, is_move: bool = False) -> ast.ParameterClosure:
        """Parse parameter closure: fn[i: int]: body"""
        self.expect(TokenType.LBRACKET)
        
        # Parse parameters
        params = []
        while not self.match_token(TokenType.RBRACKET):
            param_start = self.current().span
            param_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COLON)
            param_type = self.parse_type()
            
            params.append(ast.Param(
                name=param_name,
                type_annotation=param_type,
                span=self.make_span(param_start)
            ))
            
            if not self.match_token(TokenType.RBRACKET):
                self.expect(TokenType.COMMA)
        
        self.expect(TokenType.RBRACKET)
        
        # Optional return type
        return_type = None
        if self.match_token(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type()
        
        # Body - single expression only for closures (no block syntax yet)
        self.expect(TokenType.COLON)
        
        # Parse single expression body
        expr = self.parse_expression()
        
        # Wrap in a block with return statement
        body = ast.Block(
            statements=[ast.ReturnStmt(value=expr, span=expr.span)],
            span=expr.span
        )
        
        return ast.ParameterClosure(
            params=params,
            return_type=return_type,
            body=body,
            is_move=is_move,
            span=self.make_span(start_span)
        )
    
    def parse_runtime_closure(self, start_span: Span, is_move: bool = False) -> ast.RuntimeClosure:
        """Parse runtime closure: fn(x: int) -> bool: body"""
        # Check for 'move' keyword
        # (is_move already set from caller)
        
        self.expect(TokenType.LPAREN)
        
        # Parse parameters
        params = self.parse_param_list()
        self.expect(TokenType.RPAREN)
        
        # Optional return type
        return_type = None
        if self.match_token(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type()
        
        # Body - single expression only for closures (no block syntax yet)
        self.expect(TokenType.COLON)
        
        # Parse single expression body
        expr = self.parse_expression()
        
        # Wrap in a block with return statement
        body = ast.Block(
            statements=[ast.ReturnStmt(value=expr, span=expr.span)],
            span=expr.span
        )
        
        return ast.RuntimeClosure(
            params=params,
            return_type=return_type,
            body=body,
            is_move=is_move,
            span=self.make_span(start_span)
        )
    
    def parse_list_literal(self) -> ast.ListLiteral:
        """Parse list literal: [1, 2, 3] or [value; count] or [\n  1,\n  2\n]"""
        start_span = self.current().span
        self.expect(TokenType.LBRACKET)
        
        # Skip newlines after opening bracket
        self.skip_newlines()
        
        # Check for indented block (multi-line list literal)
        has_indent = False
        if self.match_token(TokenType.INDENT):
            has_indent = True
            self.advance()
        
        # Check for repeat syntax: [value; count]
        # Skip newlines before first element
        self.skip_newlines()
        
        # Check if empty list
        if self.match_token(TokenType.RBRACKET):
            self.expect(TokenType.RBRACKET)
            return ast.ListLiteral(
                elements=[],
                span=self.make_span(start_span)
            )
        
        # Parse first element
        first_element = self.parse_expression()
        
        # Check for repeat syntax: [value; count]
        if self.match_token(TokenType.SEMICOLON):
            self.advance()
            self.skip_newlines()
            count_expr = self.parse_expression()
            self.expect(TokenType.RBRACKET)
            
            # For repeat syntax, create a list with the value repeated
            # Note: Actual repetition will be handled in codegen/type checking
            # For now, we'll create a special marker or handle it in type checking
            # For simplicity, return a ListLiteral with a single element and mark it
            # The type checker/codegen will need to handle the repetition
            return ast.ListLiteral(
                elements=[first_element],  # Store value once, repetition handled later
                span=self.make_span(start_span)
            )
        
        # Regular list literal syntax: [elem1, elem2, ...]
        elements = [first_element]
        
        while True:
            # Skip newlines after element
            self.skip_newlines()
            
            # Check for closing bracket or DEDENT
            if self.match_token(TokenType.RBRACKET):
                break
            if has_indent and self.match_token(TokenType.DEDENT):
                self.advance()
                if self.match_token(TokenType.RBRACKET):
                    break
            
            # Expect comma if not at end
            self.expect(TokenType.COMMA)
            self.skip_newlines()
            
            # Skip newlines before next element
            self.skip_newlines()
            
            # Check for closing bracket or DEDENT
            if self.match_token(TokenType.RBRACKET):
                break
            if has_indent and self.match_token(TokenType.DEDENT):
                # Consume DEDENT and check for RBRACKET
                self.advance()
                if self.match_token(TokenType.RBRACKET):
                    break
            
            elements.append(self.parse_expression())
        
        self.expect(TokenType.RBRACKET)
        
        return ast.ListLiteral(
            elements=elements,
            span=self.make_span(start_span)
        )
    
    def parse_struct_literal(self, name: str, start_span: Span) -> ast.StructLiteral:
        """Parse struct literal: Point { x: 1, y: 2 } or Point { x: 1,\n  y: 2 }"""
        self.expect(TokenType.LBRACE)
        
        # Skip newlines after opening brace
        self.skip_newlines()
        
        # Check for indented block (multi-line struct literal)
        has_indent = False
        if self.match_token(TokenType.INDENT):
            has_indent = True
            self.advance()
        
        fields = []
        while True:
            # Skip newlines before field
            self.skip_newlines()
            
            # Check for closing brace or DEDENT (end of indented block)
            if self.match_token(TokenType.RBRACE):
                break
            if has_indent and self.match_token(TokenType.DEDENT):
                # Consume DEDENT and check for RBRACE
                self.advance()
                if self.match_token(TokenType.RBRACE):
                    break
                # If not RBRACE, continue parsing (shouldn't happen normally)
            
            field_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.COLON)
            field_value = self.parse_expression()
            fields.append((field_name, field_value))
            
            # Skip newlines after field value
            self.skip_newlines()
            
            # Check for closing brace or DEDENT
            if self.match_token(TokenType.RBRACE):
                break
            if has_indent and self.match_token(TokenType.DEDENT):
                # Consume DEDENT and check for RBRACE
                self.advance()
                if self.match_token(TokenType.RBRACE):
                    break
            
            # Expect comma if not at end
            self.expect(TokenType.COMMA)
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        
        return ast.StructLiteral(
            struct_name=name,
            fields=fields,
            span=self.make_span(start_span)
        )
    
    def parse_type(self) -> ast.Type:
        """Parse a type annotation"""
        start_span = self.current().span
        
        # Reference type
        if self.match_token(TokenType.AMPERSAND):
            self.advance()
            is_mut = False
            if self.match_token(TokenType.IDENTIFIER) and self.current().value == "mut":
                is_mut = True
                self.advance()
            
            inner = self.parse_type()
            return ast.ReferenceType(
                mutable=is_mut,
                inner=inner,
                span=self.make_span(start_span)
            )
        
        # Pointer type
        if self.match_token(TokenType.STAR):
            self.advance()
            is_mut = False
            # Check for 'const' or 'mut' keyword
            if self.match_token(TokenType.CONST):
                # *const T (immutable pointer)
                self.advance()
                is_mut = False
            elif self.match_token(TokenType.IDENTIFIER) and self.current().value == "mut":
                # *mut T (mutable pointer)
                is_mut = True
                self.advance()
            
            inner = self.parse_type()
            return ast.PointerType(
                mutable=is_mut,
                inner=inner,
                span=self.make_span(start_span)
            )
        
        # Array or slice type
        if self.match_token(TokenType.LBRACKET):
            self.advance()
            element_type = self.parse_type()
            
            if self.match_token(TokenType.SEMICOLON):
                # Array type: [T; N]
                self.advance()
                size = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                return ast.ArrayType(
                    element_type=element_type,
                    size=size,
                    span=self.make_span(start_span)
                )
            else:
                # Slice type: [T]
                self.expect(TokenType.RBRACKET)
                return ast.SliceType(
                    element_type=element_type,
                    span=self.make_span(start_span)
                )
        
        # Function type
        if self.match_token(TokenType.FN):
            return self.parse_function_type()
        
        # Tuple type or unit type: (T, U) or ()
        if self.match_token(TokenType.LPAREN):
            self.advance()
            # Check for unit type: ()
            if self.match_token(TokenType.RPAREN):
                self.advance()
                return ast.TupleType(
                    element_types=[],
                    span=self.make_span(start_span)
                )
            
            # Parse tuple elements
            element_types = []
            element_types.append(self.parse_type())
            
            while self.match_token(TokenType.COMMA):
                self.advance()
                # Check for trailing comma: (T, U,)
                if self.match_token(TokenType.RPAREN):
                    break
                element_types.append(self.parse_type())
            
            self.expect(TokenType.RPAREN)
            
            return ast.TupleType(
                element_types=element_types,
                span=self.make_span(start_span)
            )
        
        # Named type (primitive, generic, or associated type)
        if self.match_token(TokenType.IDENTIFIER):
            name = self.advance().value
            
            # Check for associated type: Trait::Item or Self::Item
            if self.match_token(TokenType.DOUBLE_COLON):
                self.advance()
                assoc_type_name = self.expect(TokenType.IDENTIFIER).value
                return ast.AssociatedTypeRef(
                    trait_name=name,
                    associated_type_name=assoc_type_name,
                    span=self.make_span(start_span)
                )
            
            # Check for generic type
            if self.match_token(TokenType.LBRACKET):
                self.advance()
                type_args = []
                
                while not self.match_token(TokenType.RBRACKET):
                    type_args.append(self.parse_type())
                    if not self.match_token(TokenType.RBRACKET):
                        self.expect(TokenType.COMMA)
                
                self.expect(TokenType.RBRACKET)
                
                return ast.GenericType(
                    name=name,
                    type_args=type_args,
                    span=self.make_span(start_span)
                )
            
            return ast.PrimitiveType(name=name, span=self.make_span(start_span))
        
        raise ParseError(f"Expected type, got {self.current().type.name}", self.current().span)
    
    def parse_function_type(self) -> ast.FunctionType:
        """Parse function type: fn(int, int) -> int"""
        start_span = self.current().span
        self.expect(TokenType.FN)
        self.expect(TokenType.LPAREN)
        
        param_types = []
        while not self.match_token(TokenType.RPAREN):
            param_types.append(self.parse_type())
            if not self.match_token(TokenType.RPAREN):
                self.expect(TokenType.COMMA)
        
        self.expect(TokenType.RPAREN)
        
        return_type = None
        if self.match_token(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type()
        
        return ast.FunctionType(
            param_types=param_types,
            return_type=return_type,
            span=self.make_span(start_span)
        )
    
    def make_span(self, start_span: Span) -> Span:
        """Create a span from start to current position"""
        current = self.peek(-1).span if self.pos > 0 else self.current().span
        return Span(
            filename=start_span.filename,
            start_line=start_span.start_line,
            start_column=start_span.start_column,
            end_line=current.end_line,
            end_column=current.end_column
        )


def parse(tokens: List[Token]) -> ast.Program:
    """Convenience function to parse a token stream"""
    parser = Parser(tokens)
    return parser.parse_program()

