"""Type checker for Pyrite.

This module provides type checking and type inference for Pyrite programs.
It analyzes the AST and ensures type safety, performing type inference where needed.

Main Components:
    TypeChecker: Main type checker class
    type_check(): Convenience function to type check an AST
    TypeCheckError: Exception raised on type checking errors

See Also:
    parser: Produces AST to be type checked
    ownership: Ownership analysis (runs after type checking)
    borrow_checker: Borrow checking (runs after type checking)
    codegen: Code generation (runs after type checking)
"""

from typing import Optional, List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from .module_system import Module
from .. import ast
from ..types import *
from .symbol_table import NameResolver, Symbol
from ..frontend.tokens import Span


# Import TraitType
from ..types import TraitType


class TypeCheckError(Exception):
    """Type checking error"""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


class TypeChecker:
    """Type checker for Pyrite programs"""
    
    def __init__(self):
        self.resolver = NameResolver()
        self.errors: List[TypeCheckError] = []
        self.current_function_return_type: Optional[Type] = None
        self.current_impl_type: Optional[Type] = None  # Track current impl type for Self resolution
        # Track trait implementations: {type_name: {trait_name: ImplBlock}}
        self.trait_implementations: Dict[str, Dict[str, ast.ImplBlock]] = {}
        # Track impl blocks for types: {type_name: ImplBlock}
        self.type_impl_blocks: Dict[str, ast.ImplBlock] = {}
        # Track function definitions for FFI detection
        self.function_defs: Dict[str, ast.FunctionDef] = {}
        # Track type aliases: {alias_name: (generic_params, target_type)}
        self.type_aliases: Dict[str, tuple[List[ast.GenericParam], Type]] = {}
        # Track if we are inside an @ensures attribute for old() validation
        self.is_inside_ensures = False
        # Track constraints for compile-time contract verification (SPEC-LANG-0406)
        # Maps variable name to list of constraint expressions (BinOp with comparisons)
        self.variable_constraints: Dict[str, List[ast.Expression]] = {}
        self.register_builtins()
    
    def error(self, message: str, span: Span):
        """Record a type error"""
        self.errors.append(TypeCheckError(message, span))
    
    def has_errors(self) -> bool:
        """Check if any errors occurred"""
        return len(self.errors) > 0 or self.resolver.has_errors()
    
    def register_builtins(self):
        """Register builtin functions and types"""
        # print function - accepts any arguments, returns void
        # For MVP, simplified signature
        print_type = FunctionType([], VOID)  # Variadic in reality
        self.resolver.define_function("print", print_type)
        
        # assert function - for tests: assert(condition: bool, message: Option[String] = None)
        # For MVP: assert(condition: bool) - message optional
        assert_type = FunctionType([BOOL], VOID)
        self.resolver.define_function("assert", assert_type)
        
        # fail function - for tests: fail(message: String)
        fail_type = FunctionType([STRING], VOID)
        self.resolver.define_function("fail", fail_type)
        
        # Register builtin generic types (Result, Box)
        self.resolver.define_type("Result", UNKNOWN)
        self.resolver.define_type("Box", UNKNOWN)  # Box type for heap allocation
        self.resolver.define_type("String", STRING)  # String is a builtin type (not generic)
        
        # Register Option enum from stdlib - this is a real enum, not a placeholder
        # Load it from stdlib/core/option.pyrite
        self._register_option_enum()
    
    def _register_option_enum(self):
        """Register Option enum from stdlib"""
        import os
        from pathlib import Path
        from ..frontend import lex, parse
        
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        # Find stdlib option.pyrite
        # Path: forge/src/middle -> forge/src -> forge -> repo_root
        compiler_dir = Path(__file__).parent.parent
        repo_root = compiler_dir.parent.parent  # forge/src -> forge -> repo_root
        option_path = repo_root / 'pyrite' / 'core' / 'option.pyrite'
        
        if debug:
            print(f"[TRACE _register_option_enum] Looking for Option enum at: {option_path}")
            print(f"  Path exists: {option_path.exists()}")
        
        if not option_path.exists():
            # Fallback: register as UNKNOWN if stdlib not found
            if debug:
                print(f"  [WARN] Option enum file not found, registering as UNKNOWN")
            self.resolver.define_type("Option", UNKNOWN)
            return
        
        try:
            # Try to parse Option enum from file
            source = option_path.read_text(encoding='utf-8')
            tokens = lex(source, str(option_path))
            program_ast = parse(tokens)
            
            if debug:
                print(f"  Parsed {len(program_ast.items)} items from option.pyrite")
            
            # Find Option enum definition
            for item in program_ast.items:
                if isinstance(item, ast.EnumDef) and item.name == "Option":
                    if debug:
                        print(f"  Found Option enum, registering...")
                    # Register the Option enum
                    self.register_enum(item)
                    if debug:
                        option_type = self.resolver.global_scope.types.get('Option', 'NOT_FOUND')
                        if option_type != 'NOT_FOUND':
                            print(f"  After registration, types[Option] = {type(option_type).__name__}")
                        else:
                            print(f"  [ERROR] Option not found in types after registration")
                    return
            
            # If Option enum not found, register as UNKNOWN
            if debug:
                print(f"  [WARN] Option enum not found in parsed items, registering as UNKNOWN")
            self.resolver.define_type("Option", UNKNOWN)
        except Exception as e:
            # Parse failed - manually construct Option enum type
            # This is more robust than parsing the file
            if debug:
                print(f"  [WARN] Parse failed ({e}), manually constructing Option enum")
            
            # Manually create Option enum: enum Option[T]: Some(value: T), None
            # Create a TypeVariable for the generic parameter T
            from ..types import TypeVariable
            t_var = TypeVariable("T")
            
            # Option enum has two variants:
            # - Some(value: T) - takes one parameter of type T
            # - None - takes no parameters
            option_variants = {
                "Some": [t_var],  # Some takes one field of type T
                "None": None      # None takes no fields
            }
            
            # Create EnumType for Option[T]
            option_enum = EnumType("Option", option_variants, ["T"])
            
            # Register it
            self.resolver.define_type("Option", option_enum)
            
            if debug:
                print(f"  Manually registered Option enum: {type(option_enum).__name__}")
                print(f"  Variants: {list(option_enum.variants.keys())}")
                option_type = self.resolver.global_scope.types.get('Option', 'NOT_FOUND')
                if option_type != 'NOT_FOUND':
                    print(f"  Verified: types[Option] = {type(option_type).__name__}")
                else:
                    print(f"  [ERROR] Option not found in types after manual registration")
    
    def import_module_symbols(self, module_ast: ast.Program):
        """Import public symbols from an imported module into the global scope
        
        For MVP, all top-level items (structs, enums, functions) are considered public.
        """
        for item in module_ast.items:
            if isinstance(item, ast.StructDef):
                # Register struct type properly using register_struct
                # This creates the proper StructType
                self.register_struct(item)
            elif isinstance(item, ast.EnumDef):
                # Register enum - need to process it to create EnumType
                self.register_enum(item)
            elif isinstance(item, ast.FunctionDef):
                # Register function signature properly using register_function
                # This ensures the function is callable and handles FFI detection
                self.register_function(item)
            elif isinstance(item, ast.ImplBlock):
                # Register impl blocks so methods can be resolved
                self.register_impl(item)
    
    def check_program(self, program: ast.Program):
        """Type check an entire program"""
        # First pass: register all top-level items
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                self.register_function(item)
            elif isinstance(item, ast.StructDef):
                self.register_struct(item)
            elif isinstance(item, ast.EnumDef):
                self.register_enum(item)
            elif isinstance(item, ast.TraitDef):
                self.register_trait(item)
            elif isinstance(item, ast.ImplBlock):
                self.register_impl(item)
            elif isinstance(item, ast.ConstDecl):
                self.register_const(item)
            elif isinstance(item, ast.OpaqueTypeDecl):
                self.register_opaque_type(item)
        
        # Register type aliases (after types are registered)
        for item in program.items:
            if isinstance(item, ast.TypeAlias):
                self.register_type_alias(item)
        
        # Second pass: type check function bodies and implementations
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                self.check_function(item)
            elif isinstance(item, ast.ImplBlock):
                self.check_impl(item)
            elif isinstance(item, ast.ConstDecl):
                self.check_const(item)
    
    def validate_where_clause(self, where_clause: List[tuple[str, List[str]]], generic_params: List[ast.GenericParam], span: Span):
        """Validate where clause bounds"""
        if not where_clause:
            return
        
        # Get generic parameter names
        generic_param_names = {p.name for p in generic_params}
        
        # Validate each where clause constraint
        for type_param, trait_bounds in where_clause:
            # Check that type parameter exists
            if type_param not in generic_param_names:
                self.error(
                    f"Type parameter '{type_param}' in where clause is not a generic parameter",
                    span
                )
                continue
            
            # Check that all trait bounds exist
            for trait_name in trait_bounds:
                trait_type = self.resolver.lookup_type(trait_name)
                if not trait_type or not isinstance(trait_type, TraitType):
                    self.error(
                        f"Trait '{trait_name}' in where clause not found",
                        span
                    )
    
    def apply_lifetime_elision(self, param_types: List[Type], return_type: Optional[Type]):
        """Apply basic lifetime elision rules (SPEC-LANG-0205)"""
        # Find all input references
        input_refs = []
        for t in param_types:
            if isinstance(t, ReferenceType):
                input_refs.append(t)
        
        # Rule 1: If there is exactly one input reference, 
        # its lifetime is assigned to all output references.
        if len(input_refs) == 1:
            in_ref = input_refs[0]
            if not in_ref.lifetime:
                in_ref.lifetime = "a"
            
            # Apply to return type
            if isinstance(return_type, ReferenceType):
                if not return_type.lifetime:
                    return_type.lifetime = in_ref.lifetime

    def register_function(self, func: ast.FunctionDef):
        # Store function definition for FFI detection
        self.function_defs[func.name] = func
        """Register a function in the symbol table"""
        # Note: Compile-time parameters are handled during monomorphization
        # For now, we register the generic function signature
        
        # Validate where clause
        self.validate_where_clause(func.where_clause, func.generic_params, func.span)
        
        # Enter a temporary function scope to register compile-time parameters
        # This allows parameter types to reference compile-time parameters
        self.resolver.enter_scope()
        
        # Register compile-time parameters FIRST (before resolving parameter types)
        # These are treated as compile-time constants during type checking
        for ct_param in func.compile_time_params:
            if isinstance(ct_param, ast.CompileTimeIntParam):
                # Register as int constant (value unknown at type-check time)
                self.resolver.define_variable(ct_param.name, INT, False, ct_param.span)
            elif isinstance(ct_param, ast.CompileTimeBoolParam):
                # Register as bool constant
                self.resolver.define_variable(ct_param.name, BOOL, False, ct_param.span)
            elif isinstance(ct_param, ast.CompileTimeFunctionParam):
                # Register as function type constant
                # Resolve parameter types and return type
                param_types = [self.resolve_type(pt) for pt in ct_param.param_types]
                return_type = self.resolve_type(ct_param.return_type) if ct_param.return_type else None
                func_type = FunctionType(param_types=param_types, return_type=return_type)
                self.resolver.define_variable(ct_param.name, func_type, False, ct_param.span)
        
        # Now resolve parameter types (which can reference compile-time parameters)
        param_types = []
        for param in func.params:
            param_type = self.resolve_type(param.type_annotation)
            param_types.append(param_type)
        
        # Resolve return type
        return_type = None
        if func.return_type:
            return_type = self.resolve_type(func.return_type)
        else:
            return_type = VOID
        
        # Exit the temporary scope
        self.resolver.exit_scope()
        
        # Apply lifetime elision (SPEC-LANG-0205)
        self.apply_lifetime_elision(param_types, return_type)
        
        func_type = FunctionType(param_types, return_type)
        self.resolver.define_function(func.name, func_type, func.span, is_extern=func.is_extern)
    
    def register_struct(self, struct: ast.StructDef):
        """Register a struct type"""
        # Validate where clause
        self.validate_where_clause(struct.where_clause, struct.generic_params, struct.span)
        
        # First, register generic type parameters
        generic_param_names = [p.name for p in struct.generic_params]
        
        # Temporarily register type variables for generic parameters
        type_vars = {}
        for param_name in generic_param_names:
            type_var = TypeVariable(param_name)
            type_vars[param_name] = type_var
            self.resolver.define_type(param_name, type_var)
        
        fields = {}
        for field in struct.fields:
            field_type = self.resolve_type(field.type_annotation)
            fields[field.name] = field_type
        
        struct_type = StructType(struct.name, fields, generic_param_names)
        self.resolver.define_type(struct.name, struct_type, struct.span)
        
        # Check attributes (@invariant)
        if struct.attributes:
            for attr in struct.attributes:
                if attr.name == "invariant":
                    self.resolver.enter_scope()
                    # For struct invariants, 'self' refers to the struct instance
                    self.resolver.define_variable("self", ReferenceType(False, struct_type), False, attr.span)
                    for expr in attr.args:
                        if isinstance(expr, ast.Expression):
                            self.check_expression(expr, expected_type=BOOL)
                    self.resolver.exit_scope()
    
    def register_enum(self, enum: ast.EnumDef):
        """Register an enum type"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        if debug:
            print(f"[TRACE register_enum] Registering enum: {enum.name}")
            print(f"  global_scope id: {id(self.resolver.global_scope)}")
            print(f"  global_scope.types id: {id(self.resolver.global_scope.types)}")
            if enum.name in self.resolver.global_scope.types:
                existing = self.resolver.global_scope.types[enum.name]
                print(f"  Existing type before registration: {type(existing).__name__} = {existing}")
            else:
                print(f"  No existing type for {enum.name}")
        
        # First, register generic type parameters
        generic_param_names = [p.name for p in enum.generic_params]
        
        # Temporarily register type variables for generic parameters
        type_vars = {}
        for param_name in generic_param_names:
            type_var = TypeVariable(param_name)
            type_vars[param_name] = type_var
            self.resolver.define_type(param_name, type_var)
        
        # Register the enum type name early (before processing variants) to support forward references
        # Create a temporary EnumType with empty variants - we'll replace it with the full one later
        # This allows forward references like Box[ASTNode] to resolve correctly
        temp_enum_type = EnumType(enum.name, {}, generic_param_names)
        # Remove any existing UNKNOWN placeholder
        if enum.name in self.resolver.global_scope.types:
            existing = self.resolver.global_scope.types[enum.name]
            if existing is UNKNOWN or (hasattr(existing, '__class__') and existing.__class__.__name__ == 'UnknownType'):
                del self.resolver.global_scope.types[enum.name]
        # Register temporary enum type for forward references
        self.resolver.global_scope.types[enum.name] = temp_enum_type
        
        variants = {}
        for variant in enum.variants:
            if variant.fields:
                # During registration, allow forward references (UNKNOWN types)
                # These will be resolved properly during type checking phase
                field_types = []
                for f in variant.fields:
                    field_type = self.resolve_type(f.type_annotation)
                    # If we got UNKNOWN but the type name matches the enum name, it's a forward reference
                    # This is valid - we'll resolve it properly later
                    # UNKNOWN is imported via "from .types import *" at the top
                    if field_type is UNKNOWN or (hasattr(field_type, '__class__') and field_type.__class__.__name__ == 'UnknownType'):
                        if f.type_annotation.name == enum.name:
                            # Forward reference to self - use a placeholder that will be resolved later
                            field_type = TypeVariable(f"__{enum.name}__forward_ref")
                    field_types.append(field_type)
                variants[variant.name] = field_types
            else:
                variants[variant.name] = None
        
        enum_type = EnumType(enum.name, variants, generic_param_names)
        # Replace the temporary enum type with the full one (with variants)
        # The temporary one was registered early to support forward references
        self.resolver.global_scope.types[enum.name] = enum_type
        
        if debug:
            print(f"  Registered enum_type: {type(enum_type).__name__} = {enum_type}")
            print(f"  After registration, types[{enum.name}] = {type(self.resolver.global_scope.types[enum.name]).__name__}")
            print(f"  isinstance check: {isinstance(self.resolver.global_scope.types[enum.name], EnumType)}")
            print(f"  Variants: {list(enum_type.variants.keys())}")
    
    def register_const(self, const: ast.ConstDecl):
        """Register a constant"""
        const_type = UNKNOWN
        if const.type_annotation:
            const_type = self.resolve_type(const.type_annotation)
        
        self.resolver.define_variable(const.name, const_type, False, const.span)
    
    def register_type_alias(self, alias: ast.TypeAlias):
        """Register a type alias: type Optional[T] = Option[T]"""
        # Resolve the target type
        # For generic aliases, the target type will be a GenericType with type variables
        # For example: type Optional[T] = Option[T] -> target is GenericType("Option", ..., [TypeVariable("T")])
        target_type = self.resolve_type(alias.target_type)
        
        # Store the alias definition with its generic parameters
        self.type_aliases[alias.name] = (alias.generic_params, target_type)
        
        # Also register in resolver for lookup (will be resolved during type resolution)
        self.resolver.define_type(alias.name, target_type, alias.span)
    
    def substitute_type_vars(self, typ: Type, subst_map: Dict[str, Type]) -> Type:
        """Substitute type variables in a type with actual types
        
        Args:
            typ: The type to substitute in
            subst_map: Mapping from type variable names to actual types
            
        Returns:
            Type with type variables substituted
        """
        from ..types import TypeVariable
        
        if isinstance(typ, TypeVariable):
            # Substitute if in map, otherwise keep the variable
            return subst_map.get(typ.name, typ)
        elif isinstance(typ, GenericType):
            # Substitute in type arguments
            substituted_args = [self.substitute_type_vars(arg, subst_map) for arg in typ.type_args]
            return GenericType(typ.name, typ.base_type, substituted_args)
        elif isinstance(typ, ReferenceType):
            inner = self.substitute_type_vars(typ.inner, subst_map)
            return ReferenceType(inner, typ.mutable)
        elif isinstance(typ, PointerType):
            inner = self.substitute_type_vars(typ.inner, subst_map)
            return PointerType(inner, typ.mutable)
        elif isinstance(typ, ArrayType):
            element = self.substitute_type_vars(typ.element_type, subst_map)
            return ArrayType(element, typ.size)
        elif isinstance(typ, SliceType):
            element = self.substitute_type_vars(typ.element_type, subst_map)
            return SliceType(element)
        elif isinstance(typ, FunctionType):
            param_types = [self.substitute_type_vars(pt, subst_map) for pt in typ.param_types]
            return_type = None
            if typ.return_type:
                return_type = self.substitute_type_vars(typ.return_type, subst_map)
            return FunctionType(param_types, return_type)
        elif isinstance(typ, TupleType):
            element_types = [self.substitute_type_vars(et, subst_map) for et in typ.element_types]
            return TupleType(element_types)
        else:
            # Primitive types, no substitution needed
            return typ
    
    def register_opaque_type(self, opaque: ast.OpaqueTypeDecl):
        """Register an opaque type"""
        from ..types import OpaqueType
        opaque_type = OpaqueType(opaque.name)
        self.resolver.define_type(opaque.name, opaque_type, opaque.span)
    
    def register_trait(self, trait: ast.TraitDef):
        """Register a trait in the symbol table"""
        # Validate where clause
        self.validate_where_clause(trait.where_clause, trait.generic_params, trait.span)
        
        # Register generic parameters as type variables
        generic_param_names = [p.name for p in trait.generic_params]
        
        # Temporarily register type variables for generic parameters
        for param_name in generic_param_names:
            type_var = TypeVariable(param_name)
            self.resolver.define_type(param_name, type_var)
        
        # Build method signatures
        methods = {}
        for method in trait.methods:
            # Resolve parameter types
            param_types = []
            for param in method.params:
                param_type = self.resolve_type(param.type_annotation)
                param_types.append(param_type)
            
            # Resolve return type
            return_type = VOID
            if method.return_type:
                return_type = self.resolve_type(method.return_type)
            
            method_type = FunctionType(param_types, return_type)
            methods[method.name] = method_type
        
        # Get associated type names
        assoc_types = [at.name for at in trait.associated_types]
        
        # Create trait type
        trait_type = TraitType(
            name=trait.name,
            methods=methods,
            generic_params=generic_param_names,
            associated_types=assoc_types
        )
        
        # Register trait as a type
        self.resolver.define_type(trait.name, trait_type, trait.span)
    
    def register_impl(self, impl: ast.ImplBlock):
        """Register an implementation block"""
        # Validate where clause
        self.validate_where_clause(impl.where_clause, impl.generic_params, impl.span)
        
        # Type being implemented for
        type_being_impl = self.resolver.lookup_type(impl.type_name)
        if not type_being_impl:
            self.error(f"Type '{impl.type_name}' not found", impl.span)
            return
        
        if impl.trait_name:
            # Trait implementation - track it
            trait_type = self.resolver.lookup_type(impl.trait_name)
            if not trait_type:
                self.error(f"Trait '{impl.trait_name}' not found", impl.span)
                return
            
            # Track this trait implementation
            if impl.type_name not in self.trait_implementations:
                self.trait_implementations[impl.type_name] = {}
            self.trait_implementations[impl.type_name][impl.trait_name] = impl
        else:
            # Regular impl block (not a trait impl) - track it for method resolution
            self.type_impl_blocks[impl.type_name] = impl
    
    def check_impl(self, impl: ast.ImplBlock):
        """Type check an implementation block"""
        if impl.trait_name:
            # Trait implementation - verify all required methods and associated types are implemented
            trait_type = self.resolver.lookup_type(impl.trait_name)
            if trait_type and isinstance(trait_type, TraitType):
                # Get required methods from trait (methods without default implementations)
                required_methods = set(trait_type.methods.keys())
                
                # Get implemented methods
                implemented_methods = {method.name for method in impl.methods}
                
                # Check for missing required methods
                missing_methods = required_methods - implemented_methods
                if missing_methods:
                    self.error(
                        f"Trait '{impl.trait_name}' requires implementation of: {', '.join(missing_methods)}",
                        impl.span
                    )
                
                # Check associated types
                required_assoc_types = set(trait_type.associated_types)
                implemented_assoc_types = {name for name, _ in impl.associated_type_impls}
                
                # Check for missing associated type implementations
                missing_assoc_types = required_assoc_types - implemented_assoc_types
                if missing_assoc_types:
                    self.error(
                        f"Trait '{impl.trait_name}' requires implementation of associated types: {', '.join(missing_assoc_types)}",
                        impl.span
                    )
                
                # Validate associated type implementations
                for assoc_name, assoc_type_ast in impl.associated_type_impls:
                    if assoc_name not in required_assoc_types:
                        self.error(
                            f"Associated type '{assoc_name}' is not declared in trait '{impl.trait_name}'",
                            impl.span
                        )
                    else:
                        # Resolve the concrete type
                        concrete_type = self.resolve_type(assoc_type_ast)
                        # Store for later resolution of Self::Item references
                        # For MVP, we just validate it resolves to a valid type
                        if concrete_type == UNKNOWN:
                            self.error(
                                f"Invalid type for associated type '{assoc_name}'",
                                impl.span
                            )
                
                # Verify method signatures match trait requirements
                for method in impl.methods:
                    if method.name in trait_type.methods:
                        # Check signature matches
                        trait_method_type = trait_type.methods[method.name]
                        # For MVP, we'll do basic checking - full signature matching can be enhanced later
                        pass
        
        # Resolve impl type for Self resolution
        impl_type = self.resolver.lookup_type(impl.type_name)
        if impl_type:
            self.current_impl_type = impl_type
        
        # Type check all methods
        for method in impl.methods:
            self.check_function(method)
        
        # Clear impl type
        self.current_impl_type = None
    
    def check_function(self, func: ast.FunctionDef):
        """Type check a function body"""
        # Enter function scope
        self.resolver.enter_scope()
        
        # Add compile-time parameters to scope FIRST (before resolving return/param types)
        # These are treated as compile-time constants during type checking
        for ct_param in func.compile_time_params:
            if isinstance(ct_param, ast.CompileTimeIntParam):
                # Register as int constant (value unknown at type-check time)
                self.resolver.define_variable(ct_param.name, INT, False, ct_param.span)
            elif isinstance(ct_param, ast.CompileTimeBoolParam):
                # Register as bool constant
                self.resolver.define_variable(ct_param.name, BOOL, False, ct_param.span)
            elif isinstance(ct_param, ast.CompileTimeFunctionParam):
                # Register as function type constant
                # Resolve parameter types and return type
                param_types = [self.resolve_type(pt) for pt in ct_param.param_types]
                return_type = self.resolve_type(ct_param.return_type) if ct_param.return_type else None
                func_type = FunctionType(param_types=param_types, return_type=return_type)
                self.resolver.define_variable(ct_param.name, func_type, False, ct_param.span)
        
        # Set current return type (after compile-time params are registered)
        if func.return_type:
            self.current_function_return_type = self.resolve_type(func.return_type)
            import os
            debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
            if debug:
                print(f"[TRACE check_function] Setting current_function_return_type for {func.name}: {type(self.current_function_return_type).__name__} = {self.current_function_return_type}")
        else:
            self.current_function_return_type = VOID
        
        # Add parameters to scope
        for param in func.params:
            param_type = self.resolve_type(param.type_annotation)
            self.resolver.define_variable(param.name, param_type, False, param.span)
        
        # Track constraints from @requires for compile-time verification (SPEC-LANG-0406)
        self.variable_constraints = {}
        
        # Check attributes (@requires, @ensures)
        for attr in func.attributes:
            if attr.name == "requires":
                for expr in attr.args:
                    if isinstance(expr, ast.Expression):
                        self.check_expression(expr, expected_type=BOOL)
                        # Compile-time verification (SPEC-LANG-0406)
                        val = self.evaluate_constant_bool(expr)
                        if val is False:
                            self.error(f"Precondition will always fail", expr.span)
                        elif val is True:
                            expr.is_proven = True
                        else:
                            # Track constraint for range analysis
                            self._track_constraint(expr)
            elif attr.name == "ensures":
                # For @ensures, 'result' refers to the return value
                self.resolver.enter_scope()
                # Use current_function_return_type (resolved above)
                ret_type = self.current_function_return_type if self.current_function_return_type else VOID
                self.resolver.define_variable("result", ret_type, False, attr.span)
                
                # Set flag for old() validation
                self.is_inside_ensures = True
                for expr in attr.args:
                    if isinstance(expr, ast.Expression):
                        self.check_expression(expr, expected_type=BOOL)
                        # Compile-time verification for postconditions (SPEC-LANG-0406)
                        val = self.evaluate_constant_bool(expr)
                        if val is False:
                            self.error(f"Postcondition will always fail", expr.span)
                        elif val is True:
                            expr.is_proven = True
                self.is_inside_ensures = False
                
                self.resolver.exit_scope()
        
        # Check function body
        self.check_block(func.body)
        
        # Exit function scope
        self.resolver.exit_scope()
        self.current_function_return_type = None
    
    def check_const(self, const: ast.ConstDecl):
        """Type check a constant declaration"""
        expr_type = self.check_expression(const.value)
        
        if const.type_annotation:
            expected_type = self.resolve_type(const.type_annotation)
            if not types_compatible(expr_type, expected_type):
                self.error(
                    f"Type mismatch: expected {expected_type}, got {expr_type}",
                    const.span
                )
    
    def check_block(self, block: ast.Block):
        """Type check a block of statements"""
        for stmt in block.statements:
            self.check_statement(stmt)
    
    def check_statement(self, stmt: ast.Statement):
        """Type check a statement"""
        if isinstance(stmt, ast.VarDecl):
            self.check_var_decl(stmt)
        elif isinstance(stmt, ast.Assignment):
            self.check_assignment(stmt)
        elif isinstance(stmt, ast.ExpressionStmt):
            self.check_expression(stmt.expression)
        elif isinstance(stmt, ast.ReturnStmt):
            self.check_return(stmt)
        elif isinstance(stmt, ast.IfStmt):
            self.check_if(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self.check_while(stmt)
        elif isinstance(stmt, ast.ForStmt):
            self.check_for(stmt)
        elif isinstance(stmt, ast.MatchStmt):
            self.check_match(stmt)
        elif isinstance(stmt, ast.WithStmt):
            self.check_with(stmt)
        elif isinstance(stmt, ast.BreakStmt) or isinstance(stmt, ast.ContinueStmt) or isinstance(stmt, ast.PassStmt):
            pass  # No type checking needed
        elif isinstance(stmt, ast.UnsafeBlock):
            self.check_block(stmt.body)
    
    def check_var_decl(self, decl: ast.VarDecl):
        """Type check a variable declaration"""
        # If type annotation provided, use it as expected type for bidirectional inference
        expected_type = None
        if decl.type_annotation:
            expected_type = self.resolve_type(decl.type_annotation)
        
        # Check initializer type with expected type for bidirectional inference
        init_type = self.check_expression(decl.initializer, expected_type=expected_type)
        
        # Check compatibility
        if decl.type_annotation:
            if not types_compatible(init_type, expected_type):
                self.error(
                    f"Type mismatch: cannot assign {init_type} to {expected_type}",
                    decl.span
                )
            var_type = expected_type
        else:
            # Infer type from initializer
            var_type = init_type
        
        # Bind variables in the pattern
        self.check_pattern(decl.pattern, var_type)
    
    def check_assignment(self, assign: ast.Assignment):
        """Type check an assignment"""
        target_type = self.check_expression(assign.target)
        value_type = self.check_expression(assign.value)
        
        if not types_compatible(target_type, value_type):
            self.error(
                f"Type mismatch: cannot assign {value_type} to {target_type}",
                assign.span
            )
        
        # Check if target is mutable (simplified for now)
        # TODO: More sophisticated mutability checking
    
    def check_return(self, ret: ast.ReturnStmt):
        """Type check a return statement"""
        if ret.value:
            # Use current function return type as expected type for bidirectional inference
            expected_type = self.current_function_return_type if self.current_function_return_type else None
            return_type = self.check_expression(ret.value, expected_type=expected_type)
        else:
            return_type = VOID
        
        if self.current_function_return_type:
            # Special handling for enum constructor calls
            # If return_type is a FunctionType (from FieldAccess like Option.None),
            # and it's an enum constructor with no parameters, automatically infer the generic type
            # from the expected return type
            if isinstance(return_type, FunctionType) and isinstance(return_type.return_type, EnumType):
                if (len(return_type.param_types) == 0 and  # No-arg constructor like Option.None
                    isinstance(self.current_function_return_type, GenericType) and
                    return_type.return_type.name == self.current_function_return_type.name):
                    # This is Option.None being used as a value - return the expected generic type
                    return_type = self.current_function_return_type
                elif (isinstance(self.current_function_return_type, EnumType) and
                      return_type.return_type.name == self.current_function_return_type.name):
                    # Non-generic enum constructor with no args - return the enum type directly
                    return_type = self.current_function_return_type
            
            # Special handling for enum constructor calls
            # If return_type is a generic EnumType and expected is a GenericType with same name,
            # they're compatible (the generic will be instantiated)
            if isinstance(return_type, EnumType) and isinstance(self.current_function_return_type, GenericType):
                if return_type.name == self.current_function_return_type.name:
                    # They're compatible - the enum constructor returns the generic enum type
                    return
            
            # Special handling for non-generic enum constructors
            # If return_type is an EnumType and expected is also an EnumType with same name,
            # they're compatible
            if isinstance(return_type, EnumType) and isinstance(self.current_function_return_type, EnumType):
                if return_type.name == self.current_function_return_type.name:
                    # They're compatible
                    return
            
            if not types_compatible(return_type, self.current_function_return_type):
                self.error(
                    f"Return type mismatch: expected {self.current_function_return_type}, got {return_type}",
                    ret.span
                )
    
    def check_if(self, if_stmt: ast.IfStmt):
        """Type check an if statement"""
        # Check condition is boolean
        cond_type = self.check_expression(if_stmt.condition)
        if not isinstance(cond_type, BoolType):
            self.error(f"If condition must be bool, got {cond_type}", if_stmt.span)
        
        # Check then block
        self.resolver.enter_scope()
        self.check_block(if_stmt.then_block)
        self.resolver.exit_scope()
        
        # Check elif clauses
        for elif_cond, elif_block in if_stmt.elif_clauses:
            elif_type = self.check_expression(elif_cond)
            if not isinstance(elif_type, BoolType):
                self.error(f"Elif condition must be bool, got {elif_type}", if_stmt.span)
            
            self.resolver.enter_scope()
            self.check_block(elif_block)
            self.resolver.exit_scope()
        
        # Check else block
        if if_stmt.else_block:
            self.resolver.enter_scope()
            self.check_block(if_stmt.else_block)
            self.resolver.exit_scope()
    
    def check_while(self, while_stmt: ast.WhileStmt):
        """Type check a while loop"""
        cond_type = self.check_expression(while_stmt.condition)
        if not isinstance(cond_type, BoolType):
            self.error(f"While condition must be bool, got {cond_type}", while_stmt.span)
        
        # Check loop invariants
        if while_stmt.attributes:
            for attr in while_stmt.attributes:
                if attr.name == "invariant":
                    for expr in attr.args:
                        if isinstance(expr, ast.Expression):
                            self.check_expression(expr, expected_type=BOOL)
                            # Compile-time verification
                            val = self.evaluate_constant_bool(expr)
                            if val is False:
                                self.error(f"Loop invariant will always fail", expr.span)
                            elif val is True:
                                expr.is_proven = True
        
        self.resolver.enter_scope()
        self.check_block(while_stmt.body)
        self.resolver.exit_scope()
    
    def check_for(self, for_stmt: ast.ForStmt):
        """Type check a for loop"""
        # Check iterable (simplified - just check it has a type)
        iterable_type = self.check_expression(for_stmt.iterable)
        
        # Check loop invariants
        if for_stmt.attributes:
            for attr in for_stmt.attributes:
                if attr.name == "invariant":
                    for expr in attr.args:
                        if isinstance(expr, ast.Expression):
                            self.check_expression(expr, expected_type=BOOL)
                            # Compile-time verification
                            val = self.evaluate_constant_bool(expr)
                            if val is False:
                                self.error(f"Loop invariant will always fail", expr.span)
                            elif val is True:
                                expr.is_proven = True
        
        # For MVP, assume loop variable is int
        loop_var_type = INT
        
        self.resolver.enter_scope()
        self.resolver.define_variable(for_stmt.variable, loop_var_type, False, for_stmt.span)
        self.check_block(for_stmt.body)
        self.resolver.exit_scope()
    
    def check_match(self, match_stmt: ast.MatchStmt):
        """Type check a match statement"""
        scrutinee_type = self.check_expression(match_stmt.scrutinee)
        
        for arm in match_stmt.arms:
            self.resolver.enter_scope()
            
            # Check pattern and bind variables
            self.check_pattern(arm.pattern, scrutinee_type)
            
            # Check guard if present
            if arm.guard:
                guard_type = self.check_expression(arm.guard)
                if not isinstance(guard_type, BoolType):
                    self.error(f"Match guard must be bool, got {guard_type}", arm.span)
            
            # Check arm body
            self.check_block(arm.body)
            
            self.resolver.exit_scope()
    
    def type_implements_trait(self, type_name: str, trait_name: str) -> bool:
        """Check if a type implements a trait"""
        if type_name not in self.trait_implementations:
            return False
        return trait_name in self.trait_implementations[type_name]
    
    def check_with(self, with_stmt: ast.WithStmt):
        """Type check a with statement"""
        # Check the value expression
        value_type = self.check_expression(with_stmt.value)
        
        # Check if Closeable trait exists
        closeable_trait = self.resolver.lookup_type("Closeable")
        if not closeable_trait:
            # Closeable trait not defined - warn but don't error (allows gradual adoption)
            # In full implementation, we'd require Closeable to be defined
            pass
        elif not isinstance(closeable_trait, TraitType):
            self.error(
                f"Closeable is not a trait (found {type(closeable_trait)})",
                with_stmt.span
            )
        else:
            # Verify that the value type implements Closeable
            # Extract type name from value_type
            type_name = self._get_type_name(value_type)
            if type_name and not self.type_implements_trait(type_name, "Closeable"):
                self.error(
                    f"Type '{type_name}' does not implement Closeable trait. "
                    f"Implement Closeable for {type_name} to use it with 'with' statement.",
                    with_stmt.span
                )
        
        # Add variable to scope for body checking
        # The variable type is the value type (unwrapped if it's a Result)
        # For MVP, we'll use the value type directly
        # In full implementation, we'd unwrap Result types
        resource_type = value_type
        
        # Add to symbol table for body checking
        self.resolver.enter_scope()
        self.resolver.define_variable(with_stmt.variable, resource_type, False, with_stmt.span)
        
        # Check the body with the resource in scope
        self.check_block(with_stmt.body)
        
        # Exit scope after with block
        self.resolver.exit_scope()
    
    def _get_type_name(self, typ: Type) -> Optional[str]:
        """Extract type name from a Type object"""
        from ..types import StructType, EnumType, TraitType
        
        if isinstance(typ, StructType):
            return typ.name
        elif isinstance(typ, EnumType):
            return typ.name
        elif isinstance(typ, TraitType):
            return typ.name
        # For other types (primitives, references, etc.), return None
        # Closeable validation only applies to named types (structs, enums)
        return None
    
    def check_pattern(self, pattern: ast.Pattern, expected_type: Type):
        """Type check a pattern and bind variables"""
        if isinstance(pattern, ast.LiteralPattern):
            literal_type = self.check_expression(pattern.literal)
            if not types_compatible(literal_type, expected_type):
                self.error(
                    f"Pattern type mismatch: expected {expected_type}, got {literal_type}",
                    pattern.span
                )
        elif isinstance(pattern, ast.IdentifierPattern):
            # Bind the variable
            self.resolver.define_variable(pattern.name, expected_type, False, pattern.span)
        elif isinstance(pattern, ast.TuplePattern):
            if not isinstance(expected_type, TupleType):
                self.error(f"Cannot destructure non-tuple type {expected_type} as tuple", pattern.span)
                return
            
            if len(pattern.elements) != len(expected_type.elements):
                self.error(f"Tuple arity mismatch: pattern has {len(pattern.elements)}, type has {len(expected_type.elements)}", pattern.span)
                return
            
            for sub_pat, elem_type in zip(pattern.elements, expected_type.elements):
                self.check_pattern(sub_pat, elem_type)
        elif isinstance(pattern, ast.WildcardPattern):
            pass  # Matches anything
        elif isinstance(pattern, ast.EnumPattern):
            # Check enum variant matches expected type
            actual_enum_type = expected_type
            if isinstance(actual_enum_type, GenericType):
                actual_enum_type = actual_enum_type.base_type
            
            if not isinstance(actual_enum_type, EnumType):
                self.error(f"Cannot match non-enum type {expected_type} against enum pattern", pattern.span)
                return
            
            if pattern.variant_name not in actual_enum_type.variants:
                self.error(f"Enum {actual_enum_type.name} has no variant '{pattern.variant_name}'", pattern.span)
                return
            
            variant_field_types = actual_enum_type.variants[pattern.variant_name]
            
            # If variant has fields, check arity and bind them
            if variant_field_types:
                if not pattern.fields:
                    self.error(f"Enum variant {actual_enum_type.name}::{pattern.variant_name} expects fields", pattern.span)
                    return
                
                if len(pattern.fields) != len(variant_field_types):
                    self.error(f"Enum variant {actual_enum_type.name}::{pattern.variant_name} expects {len(variant_field_types)} fields, got {len(pattern.fields)}", pattern.span)
                    return
                
                # If expected_type is GenericType, instantiate field types
                if isinstance(expected_type, GenericType):
                    # Simplified instantiation for Option[T]
                    if expected_type.name == "Option" and len(expected_type.type_args) == 1:
                        field_types = [expected_type.type_args[0]]
                    else:
                        field_types = variant_field_types
                else:
                    field_types = variant_field_types

                for sub_pat, field_type in zip(pattern.fields, field_types):
                    self.check_pattern(sub_pat, field_type)
            elif pattern.fields:
                self.error(f"Enum variant {actual_enum_type.name}::{pattern.variant_name} expects no fields", pattern.span)
        elif isinstance(pattern, ast.OrPattern):
            for sub_pattern in pattern.patterns:
                self.check_pattern(sub_pattern, expected_type)
    
    def check_expression(self, expr: ast.Expression, expected_type: Optional[Type] = None) -> Type:
        """Type check an expression and return its type
        
        Args:
            expr: The expression to check
            expected_type: Optional expected type for bidirectional type inference
        """
        import os
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        if debug and isinstance(expr, ast.FieldAccess):
            print(f"[TRACE check_expression] FieldAccess: {type(expr.object).__name__}.{expr.field}")
            if isinstance(expr.object, ast.Identifier):
                print(f"  Identifier name: {expr.object.name}")
        
        if isinstance(expr, ast.IntLiteral):
            # Bidirectional inference: if expected type is i64, infer i64 instead of int
            if expected_type is not None and expected_type == I64:
                return I64
            return INT
        elif isinstance(expr, ast.FloatLiteral):
            return F64
        elif isinstance(expr, ast.StringLiteral):
            return STRING
        elif isinstance(expr, ast.CharLiteral):
            return CHAR
        elif isinstance(expr, ast.BoolLiteral):
            return BOOL
        elif isinstance(expr, ast.NoneLiteral):
            return NONE
        elif isinstance(expr, ast.Identifier):
            return self.check_identifier(expr)
        elif isinstance(expr, ast.BinOp):
            return self.check_binop(expr)
        elif isinstance(expr, ast.UnaryOp):
            return self.check_unaryop(expr)
        elif isinstance(expr, ast.TernaryExpr):
            return self.check_ternary(expr)
        elif isinstance(expr, ast.FunctionCall):
            return self.check_function_call(expr, expected_type=expected_type)
        elif isinstance(expr, ast.MethodCall):
            return self.check_method_call(expr, expected_type=expected_type)
        elif isinstance(expr, ast.FieldAccess):
            return self.check_field_access(expr)
        elif isinstance(expr, ast.IndexAccess):
            return self.check_index_access(expr)
        elif isinstance(expr, ast.AsExpression):
            return self.check_as_expression(expr)
        elif isinstance(expr, ast.StructLiteral):
            return self.check_struct_literal(expr)
        elif isinstance(expr, ast.ListLiteral):
            return self.check_list_literal(expr)
        elif isinstance(expr, ast.GenericType):
            return self.resolve_type(expr)
        elif isinstance(expr, ast.TupleLiteral):
            element_types = [self.check_expression(elem) for elem in expr.elements]
            return TupleType(element_types)
        elif isinstance(expr, ast.TryExpr):
            return self.check_try_expr(expr)
        elif isinstance(expr, ast.OldExpr):
            return self.check_old_expr(expr)
        elif isinstance(expr, ast.QuantifiedExpr):
            return self.check_quantified_expr(expr)
        elif isinstance(expr, ast.ParameterClosure):
            return self.check_parameter_closure(expr)
        elif isinstance(expr, ast.RuntimeClosure):
            return self.check_runtime_closure(expr)
        else:
            self.error(f"Unknown expression type: {type(expr)}", expr.span)
            return UNKNOWN
    
    def check_identifier(self, ident: ast.Identifier) -> Type:
        """Check identifier and return its type"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_VLOOKUP') == '1'
        if debug:
            print(f"[VLOOKUP] Looking up identifier '{ident.name}' at {ident.span}")
            print(f"[VLOOKUP] Current scope: {id(self.resolver.current_scope)}")
            # Print scope chain
            scope = self.resolver.current_scope
            depth = 0
            while scope:
                print(f"[VLOOKUP]   Scope depth {depth}: symbols={list(scope.symbols.keys())}")
                scope = scope.parent
                depth += 1
        symbol = self.resolver.lookup_variable(ident.name, ident.span)
        if symbol:
            if debug:
                print(f"[VLOOKUP] Found symbol: {symbol.name} -> {symbol.type}")
            return symbol.type
        if debug:
            print(f"[VLOOKUP] Symbol not found, returning UNKNOWN")
        return UNKNOWN
    
    def check_binop(self, binop: ast.BinOp) -> Type:
        """Check binary operation"""
        left_type = self.check_expression(binop.left)
        right_type = self.check_expression(binop.right)
        
        # Arithmetic operators
        if binop.op in ['+', '-', '*', '/', '%']:
            if is_numeric_type(left_type) and is_numeric_type(right_type):
                return common_numeric_type(left_type, right_type) or INT
            else:
                self.error(
                    f"Arithmetic operator {binop.op} requires numeric types, got {left_type} and {right_type}",
                    binop.span
                )
                return UNKNOWN
        
        # Comparison operators
        elif binop.op in ['==', '!=', '<', '<=', '>', '>=']:
            if not types_compatible(left_type, right_type):
                self.error(
                    f"Cannot compare {left_type} with {right_type}",
                    binop.span
                )
            return BOOL
        
        # Logical operators
        elif binop.op in ['and', 'or']:
            if not isinstance(left_type, BoolType):
                self.error(f"Left operand of {binop.op} must be bool, got {left_type}", binop.span)
            if not isinstance(right_type, BoolType):
                self.error(f"Right operand of {binop.op} must be bool, got {right_type}", binop.span)
            return BOOL
        
        # Range operator (for now, just return a generic type)
        elif binop.op == '..':
            if not isinstance(left_type, IntType):
                self.error(f"Left operand of .. must be integer, got {left_type}", binop.span)
            if not isinstance(right_type, IntType):
                self.error(f"Right operand of .. must be integer, got {right_type}", binop.span)
            return INT  # Simplified - should be Range[int]
        
        else:
            self.error(f"Unknown binary operator: {binop.op}", binop.span)
            return UNKNOWN
    
    def check_unaryop(self, unaryop: ast.UnaryOp) -> Type:
        """Check unary operation"""
        operand_type = self.check_expression(unaryop.operand)
        
        if unaryop.op == '-':
            if not is_numeric_type(operand_type):
                self.error(f"Unary minus requires numeric type, got {operand_type}", unaryop.span)
                return UNKNOWN
            return operand_type
        
        elif unaryop.op == 'not':
            if not isinstance(operand_type, BoolType):
                self.error(f"Logical not requires bool, got {operand_type}", unaryop.span)
                return UNKNOWN
            return BOOL
        
        elif unaryop.op == '&':
            # Immutable reference
            return ReferenceType(operand_type, False)
        
        elif unaryop.op == '&mut':
            # Mutable reference
            return ReferenceType(operand_type, True)
        
        elif unaryop.op == '*':
            # Dereference
            if isinstance(operand_type, (ReferenceType, PointerType)):
                return operand_type.inner
            else:
                self.error(f"Cannot dereference non-pointer type {operand_type}", unaryop.span)
                return UNKNOWN
        
        else:
            self.error(f"Unknown unary operator: {unaryop.op}", unaryop.span)
            return UNKNOWN
    
    def check_ternary(self, ternary: ast.TernaryExpr) -> Type:
        """Check ternary expression"""
        cond_type = self.check_expression(ternary.condition)
        if not isinstance(cond_type, BoolType):
            self.error(f"Ternary condition must be bool, got {cond_type}", ternary.span)
        
        true_type = self.check_expression(ternary.true_expr)
        false_type = self.check_expression(ternary.false_expr)
        
        if not types_compatible(true_type, false_type):
            self.error(
                f"Ternary branches have incompatible types: {true_type} and {false_type}",
                ternary.span
            )
            return UNKNOWN
        
        return true_type
    
    def check_function_call(self, call: ast.FunctionCall, expected_type: Optional[Type] = None) -> Type:
        """Check function call"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        if debug:
            print(f"[TRACE check_function_call] ENTRY: function={type(call.function).__name__}")
            if isinstance(call.function, ast.FieldAccess):
                print(f"  FieldAccess: {type(call.function.object).__name__}.{call.function.field}")
                if isinstance(call.function.object, ast.Identifier):
                    print(f"    Identifier name: {call.function.object.name}")
            elif isinstance(call.function, ast.TryExpr):
                print(f"  ERROR: TryExpr should not be a function - this is a parser bug!")
                return UNKNOWN
        
        # Get function type
        if isinstance(call.function, ast.Identifier):
            func_name = call.function.name
            
            # Special handling for variadic builtins
            if func_name == "print":
                # print accepts any number of arguments
                for arg in call.arguments:
                    self.check_expression(arg)
                return VOID
            
            symbol = self.resolver.lookup_function(func_name, call.span)
            if not symbol:
                return UNKNOWN
            
            if not isinstance(symbol.type, FunctionType):
                self.error(f"'{func_name}' is not a function", call.span)
                return UNKNOWN
            
            func_type = symbol.type
            
            # If this is a call with compile-time arguments, we need to check against
            # the original function definition to see if parameters with compile-time
            # parameter types should be automatically provided
            # For now, we'll check if compile-time args match compile-time params
            # and adjust expected argument count accordingly
            if call.compile_time_args:
                # Find the original function definition to check compile-time params
                # This is a simplified check - full implementation would use monomorphization
                # For type checking, we need to account for parameters whose types are
                # compile-time parameters that are being provided
                # For MVP, we'll skip the argument count check if compile-time args are provided
                # The monomorphization pass will handle the actual specialization
                pass
        else:
            # Could be a function pointer or method - simplified for MVP
            func_type_result = self.check_expression(call.function)
            if not isinstance(func_type_result, FunctionType):
                self.error("Expression is not callable", call.span)
                return UNKNOWN
            func_type = func_type_result
            
            # Special handling for enum constructors: if the return type is an EnumType
            # and we're in a context expecting a GenericType with the same name,
            # instantiate the enum with the generic type parameters
            if (isinstance(func_type.return_type, EnumType) and 
                self.current_function_return_type and
                isinstance(self.current_function_return_type, GenericType) and
                func_type.return_type.name == self.current_function_return_type.name):
                # This is an enum constructor call in a return statement
                # Return the expected generic type instead of the base enum type
                # But first check the arguments match
                if len(call.arguments) == len(func_type.param_types):
                    return self.current_function_return_type
        
        # Check argument count
        # Note: For functions with compile-time parameters, the argument count check
        # is deferred until after monomorphization, as compile-time arguments may
        # affect the specialized function signature. When compile-time args are provided,
        # the monomorphization pass will create a specialized function with the correct
        # parameter signature, so we skip strict argument count checking here.
        if len(call.arguments) != len(func_type.param_types):
            if not call.compile_time_args:
                # Only error if no compile-time args (normal function call)
                self.error(
                    f"Function expects {len(func_type.param_types)} arguments, got {len(call.arguments)}",
                    call.span
                )
                return func_type.return_type or VOID
            # If compile-time args are provided, skip strict checking
            # The monomorphization pass will handle creating the correct specialized signature
        
        # Check if this is an FFI function call (for reference-to-pointer coercion)
        is_ffi_call = False
        if isinstance(call.function, ast.Identifier):
            func_name = call.function.name
            # Check if function is extern "C" using function_defs
            if func_name in self.function_defs:
                is_ffi_call = self.function_defs[func_name].is_extern
        
        # Check argument types and collect type variable mappings for generic inference
        type_var_map = {}  # Maps type variable name to inferred type
        for i, (arg, param_type) in enumerate(zip(call.arguments, func_type.param_types)):
            # Pass expected type for bidirectional inference (e.g., int literal → i64 when param expects i64)
            arg_type = self.check_expression(arg, expected_type=param_type)
            
            # Special handling: if arg_type is a FunctionType with no parameters (no-arg enum constructor),
            # use the return type instead, as the constructor is being used as a value
            if isinstance(arg_type, FunctionType) and len(arg_type.param_types) == 0:
                if isinstance(arg_type.return_type, EnumType):
                    arg_type = arg_type.return_type
            
            # Allow int→i64 coercion in function arguments (widening only)
            # This handles cases where bidirectional inference didn't apply (e.g., int variable passed to i64 param)
            if isinstance(arg_type, IntType) and isinstance(param_type, IntType):
                if arg_type == INT and param_type == I64:
                    # int → i64 widening is allowed in function arguments
                    arg_type = I64  # Promote to i64 for compatibility check
                elif arg_type == INT:
                    # Check if expected_type is u8 (U8 from types)
                    from ..types import U8 as U8_TYPE
                    if param_type == U8_TYPE:
                        # int → u8 coercion for small literals (0-255) in function arguments
                        if isinstance(arg, ast.IntLiteral) and 0 <= arg.value <= 255:
                            arg_type = U8_TYPE
            
            # FFI coercion: &T -> *const T, &mut T -> *mut T
            if is_ffi_call and isinstance(arg_type, ReferenceType) and isinstance(param_type, PointerType):
                # Resolve Self type if needed
                from ..types import SelfType
                ref_inner = arg_type.inner
                if isinstance(ref_inner, SelfType):
                    # Self needs to be resolved to concrete type
                    # For impl blocks, Self is the type being implemented
                    if self.current_impl_type:
                        ref_inner = self.current_impl_type
                    else:
                        # Can't resolve Self - skip coercion (will fail with clearer error)
                        ref_inner = None
                
                # Check if reference inner type matches pointer inner type
                if ref_inner and ref_inner == param_type.inner:
                    # Coercion allowed: &T to *const T or &mut T to *mut T
                    # For mutable references, ensure pointer is also mutable
                    if arg_type.mutable and not param_type.mutable:
                        # &mut T cannot be coerced to *const T (safety)
                        self.error(
                            f"Argument {i+1}: cannot coerce &mut {arg_type.inner} to *const {param_type.inner} (use *mut)",
                            call.span
                        )
                    else:
                        # Coercion is valid - continue with param_type as the effective type
                        arg_type = param_type  # Treat as if argument matches parameter type
            
            # If param_type is a TypeVariable, map it to the argument type for generic inference
            if isinstance(param_type, TypeVariable):
                type_var_map[param_type.name] = arg_type
            
            if not types_compatible(arg_type, param_type):
                self.error(
                    f"Argument {i+1}: expected {param_type}, got {arg_type}",
                    call.span
                )
        
        # Special handling for enum constructors: infer generic type parameters
        # If the return type is an EnumType with generic parameters, and we have type variable mappings,
        # create a GenericType with the inferred type arguments
        if isinstance(func_type.return_type, EnumType) and func_type.return_type.generic_params:
            # Check if we can infer all generic parameters from the arguments
            inferred_type_args = []
            for param_name in func_type.return_type.generic_params:
                if param_name in type_var_map:
                    inferred_type_args.append(type_var_map[param_name])
                else:
                    # Can't infer this parameter - use the base enum type
                    # This shouldn't happen for proper enum constructor calls
                    break
            
            # If we inferred all parameters, create a GenericType
            if len(inferred_type_args) == len(func_type.return_type.generic_params):
                # GenericType is already imported via "from .types import *"
                return GenericType(
                    name=func_type.return_type.name,
                    base_type=func_type.return_type,
                    type_args=inferred_type_args
                )
        
        # Special handling for enum constructors in return context
        # If we're returning an enum constructor and the expected return type is a GenericType
        # with the same name, return the generic type instead of the base enum type
        if (isinstance(func_type.return_type, EnumType) and 
            self.current_function_return_type and
            isinstance(self.current_function_return_type, GenericType) and
            func_type.return_type.name == self.current_function_return_type.name):
            return self.current_function_return_type
        
        # Use expected type for generic type inference if available
        return_type = func_type.return_type or VOID
        
        # If return type is UNKNOWN and we have an expected type, try to use it
        if (return_type == UNKNOWN or isinstance(return_type, UnknownType)) and expected_type:
            # Check if expected type is a GenericType
            if isinstance(expected_type, GenericType):
                # If the function return type annotation matches the generic type name,
                # use the expected type
                # For now, we'll use the expected type if it's a generic type
                return expected_type
        
        # If return type is a generic type placeholder and we have an expected GenericType,
        # use the expected type
        if isinstance(return_type, GenericType) and isinstance(expected_type, GenericType):
            if return_type.name == expected_type.name:
                # Same generic type - use expected type with inferred parameters
                return expected_type
        
        return return_type
    
    def check_method_call(self, call: ast.MethodCall, expected_type: Optional[Type] = None) -> Type:
        """Check method call (simplified for MVP)"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        if debug:
            print(f"[TRACE check_method_call] ENTRY: object={type(call.object).__name__}, method={call.method}")
            if isinstance(call.object, ast.Identifier):
                print(f"  Identifier name: {call.object.name}")
        
        # Try to get object type
        object_type = None
        
        # For method calls, the object might be a type name (static method call)
        # or a variable (instance method call)
        if isinstance(call.object, ast.Identifier):
            # First, try as a type name (for static method calls like Point.new())
            # Use global_scope.lookup_type directly to avoid error reporting
            type_name = call.object.name
            if debug:
                print(f"  Looking up type: {type_name}")
                print(f"  type_name in global_scope.types: {type_name in self.resolver.global_scope.types}")
                if type_name in self.resolver.global_scope.types:
                    print(f"  types[{type_name}] = {type(self.resolver.global_scope.types[type_name]).__name__}")
            
            type_obj = self.resolver.global_scope.lookup_type(call.object.name)
            if debug:
                print(f"  lookup_type result: {type(type_obj).__name__} = {type_obj}")
            if type_obj:
                object_type = type_obj
                if debug:
                    print(f"  Using type_obj as object_type: {type(object_type).__name__}")
            else:
                # Not a type, try as a variable/expression
                object_type = self.check_expression(call.object)
        else:
            # Complex expression - check normally
            object_type = self.check_expression(call.object)
        
        # Check if this is an enum constructor call: EnumName.VariantName(args)
        # The object_type should be an EnumType if we found it as a type name
        if isinstance(object_type, EnumType):
            if debug:
                print(f"  object_type is EnumType: {object_type.name}")
                print(f"  Checking for variant: {call.method}")
                print(f"  Available variants: {list(object_type.variants.keys())}")
            
            if call.method in object_type.variants:
                variant_field_types = object_type.variants[call.method]
                if debug:
                    print(f"  Found variant {call.method} with field types: {variant_field_types}")
                
                # Check argument count and types
                if variant_field_types is None:
                    # Variant with no fields
                    if len(call.arguments) != 0:
                        self.error(
                            f"Enum variant {object_type.name}.{call.method} takes no arguments, got {len(call.arguments)}",
                            call.span
                        )
                        return UNKNOWN
                    # Return the enum type, but convert to GenericType if we're in a return context
                    if (self.current_function_return_type and
                        isinstance(self.current_function_return_type, GenericType) and
                        object_type.name == self.current_function_return_type.name):
                        if debug:
                            print(f"  Converting EnumType to GenericType for return context: {self.current_function_return_type}")
                        return self.current_function_return_type
                    return object_type
                else:
                    # Variant with fields - check argument count
                    if len(call.arguments) != len(variant_field_types):
                        self.error(
                            f"Enum variant {object_type.name}.{call.method} expects {len(variant_field_types)} arguments, got {len(call.arguments)}",
                            call.span
                        )
                        return UNKNOWN
                    
                    # Check argument types and collect type variable mappings for generic inference
                    type_var_map = {}  # Maps type variable name to inferred type
                    for i, (arg, expected_type) in enumerate(zip(call.arguments, variant_field_types)):
                        # Pass expected type for bidirectional inference
                        arg_type = self.check_expression(arg, expected_type=expected_type)
                        
                        # Special handling: if arg_type is a FunctionType with no parameters (no-arg enum constructor),
                        # use the return type instead, as the constructor is being used as a value
                        if isinstance(arg_type, FunctionType) and len(arg_type.param_types) == 0:
                            if isinstance(arg_type.return_type, EnumType):
                                arg_type = arg_type.return_type
                        
                        # Allow int→i64 coercion (widening only)
                        if isinstance(arg_type, IntType) and isinstance(expected_type, IntType):
                            if arg_type == INT and expected_type == I64:
                                arg_type = I64
                            elif arg_type == INT and expected_type == U8:
                                # int → u8 coercion for small literals (0-255)
                                if isinstance(arg, ast.IntLiteral) and 0 <= arg.value <= 255:
                                    arg_type = U8
                        
                        # If expected_type is a TypeVariable, map it to the argument type for generic inference
                        if isinstance(expected_type, TypeVariable):
                            type_var_map[expected_type.name] = arg_type
                        
                        if not types_compatible(arg_type, expected_type):
                            self.error(
                                f"Argument {i+1} to {object_type.name}.{call.method}: expected {expected_type}, got {arg_type}",
                                call.span
                            )
                    
                    # Special handling for generic enum constructors: infer generic type parameters
                    # If the enum has generic parameters, and we have type variable mappings,
                    # create a GenericType with the inferred type arguments
                    if object_type.generic_params:
                        inferred_type_args = []
                        for param_name in object_type.generic_params:
                            if param_name in type_var_map:
                                inferred_type_args.append(type_var_map[param_name])
                            else:
                                # Can't infer this parameter - use the base enum type
                                break
                        
                        # If we inferred all parameters, create a GenericType
                        if len(inferred_type_args) == len(object_type.generic_params):
                            return GenericType(
                                name=object_type.name,
                                base_type=object_type,
                                type_args=inferred_type_args
                            )
                    
                    # Return the enum type, but convert to GenericType if we're in a return context
                    # and the expected return type is a GenericType with the same name
                    if (self.current_function_return_type and
                        isinstance(self.current_function_return_type, GenericType) and
                        object_type.name == self.current_function_return_type.name):
                        if debug:
                            print(f"  Converting EnumType to GenericType for return context: {self.current_function_return_type}")
                        return self.current_function_return_type
                    return object_type
            else:
                if debug:
                    print(f"  Variant {call.method} not found in enum {object_type.name}")
                self.error(
                    f"Enum {object_type.name} has no variant '{call.method}'",
                    call.span
                )
                return UNKNOWN
        
        # Check arguments
        for arg in call.arguments:
            self.check_expression(arg)
        
        # If object_type is a type (not a variable), try to find the method in impl blocks
        if object_type and isinstance(call.object, ast.Identifier):
            # This is a static method call on a type (e.g., List.new(), StringBuilder.new())
            type_name = call.object.name
            
            # Look up impl block for this type
            if type_name in self.type_impl_blocks:
                impl_block = self.type_impl_blocks[type_name]
                
                # Find the method in the impl block
                for method in impl_block.methods:
                    if method.name == call.method:
                        # Found the method - check argument count
                        if len(call.arguments) != len(method.params):
                            self.error(
                                f"Method {type_name}.{call.method} expects {len(method.params)} arguments, got {len(call.arguments)}",
                                call.span
                            )
                            return UNKNOWN
                        
                        # Check argument types
                        for i, (arg, param) in enumerate(zip(call.arguments, method.params)):
                            if param.type_annotation:
                                expected_type = self.resolve_type(param.type_annotation)
                                # Pass expected type for bidirectional inference
                                arg_type = self.check_expression(arg, expected_type=expected_type)
                                
                                # Allow int→i64 coercion (widening only)
                                if isinstance(arg_type, IntType) and isinstance(expected_type, IntType):
                                    if arg_type == INT and expected_type == I64:
                                        arg_type = I64
                                    elif arg_type == INT:
                                        # Check if expected_type is u8 (U8 from types)
                                        from ..types import U8 as U8_TYPE
                                        if expected_type == U8_TYPE:
                                            # int → u8 coercion for small literals (0-255)
                                            if isinstance(arg, ast.IntLiteral) and 0 <= arg.value <= 255:
                                                arg_type = U8_TYPE
                                
                                if not types_compatible(arg_type, expected_type):
                                    self.error(
                                        f"Argument {i+1} to {type_name}.{call.method}: expected {expected_type}, got {arg_type}",
                                        call.span
                                    )
                        
                        # Return the method's return type
                        if method.return_type:
                            return_type = self.resolve_type(method.return_type)
                            # If return type is UNKNOWN and the type name matches, check if it's a struct type
                            if return_type == UNKNOWN or isinstance(return_type, UnknownType):
                                # Check if the return type annotation is the same as the type name
                                if isinstance(method.return_type, ast.PrimitiveType) and method.return_type.name == type_name:
                                    # First, try to look up the struct type directly
                                    struct_type = self.resolver.global_scope.lookup_type(type_name)
                                    if isinstance(struct_type, StructType) and struct_type.name == type_name:
                                        # This is a struct constructor (e.g., Path.new() -> Path)
                                        return struct_type
                                    # Otherwise, it's likely a generic type constructor (e.g., List.new() -> List)
                                    # Try to infer type parameters from expected type
                                    if expected_type and isinstance(expected_type, GenericType) and expected_type.name == type_name:
                                        # Expected type is List[String], so return List[String]
                                        return expected_type
                                    # Otherwise, return a GenericType with unknown type parameters
                                    # Type inference will fill in the parameters later
                                    type_decl = self.resolver.global_scope.lookup_type(type_name)
                                    if isinstance(type_decl, StructType) and type_decl.generic_params:
                                        num_params = len(type_decl.generic_params)
                                        return GenericType(name=type_name, base_type=type_decl, type_args=[UNKNOWN] * num_params)
                                    return GenericType(name=type_name, base_type=None, type_args=[UNKNOWN])
                            # If return type is a StructType with the same name, return it
                            elif isinstance(return_type, StructType) and return_type.name == type_name:
                                return return_type
                            return return_type
                        else:
                            return VOID
                
                # Method not found in impl block
                # Special case: String.new() calls extern function string_new()
                if type_name == "String" and call.method == "new":
                    # Check argument count (should be 1: cstr: *const u8)
                    if len(call.arguments) != 1:
                        self.error(
                            f"String.new() expects 1 argument, got {len(call.arguments)}",
                            call.span
                        )
                        return UNKNOWN
                    # Check argument type
                    arg_type = self.check_expression(call.arguments[0])
                    # For MVP, we'll be lenient with argument types
                    # Return String type
                    return STRING
                
                self.error(
                    f"Type '{type_name}' has no method '{call.method}'",
                    call.span
                )
                return UNKNOWN
        
        # Handle instance method calls (object is a variable/expression, not a type name)
        if object_type:
            # Look up the type name from the object type
            type_name = None
            if isinstance(object_type, StructType):
                type_name = object_type.name
            elif isinstance(object_type, GenericType):
                type_name = object_type.name
            elif object_type == STRING:
                type_name = "String"
            elif isinstance(object_type, EnumType):
                type_name = object_type.name
            
            # If type_name is None, the object type doesn't support methods
            if type_name is None:
                self.error(
                    f"Cannot call method '{call.method}' on type {object_type}",
                    call.span
                )
                return UNKNOWN
            
            # Look up impl block for this type
            if type_name in self.type_impl_blocks:
                impl_block = self.type_impl_blocks[type_name]
                
                # Find the method in the impl block
                for method in impl_block.methods:
                    if method.name == call.method:
                        # Found the method - check argument count
                        # Skip 'self' parameter for instance methods
                        expected_param_count = len(method.params)
                        # Check if first param is self (instance method)
                        # Instance methods have first param named "self" (with or without type annotation)
                        is_instance_method = False
                        if expected_param_count > 0:
                            first_param = method.params[0]
                            # If parameter name is "self", it's an instance method
                            if first_param.name == "self":
                                is_instance_method = True
                        
                        if is_instance_method:
                            expected_param_count -= 1  # Don't count 'self'
                        
                        if len(call.arguments) != expected_param_count:
                            self.error(
                                f"Method {type_name}.{call.method} expects {expected_param_count} arguments, got {len(call.arguments)}",
                                call.span
                            )
                            return UNKNOWN
                        
                        # Check argument types (skip self parameter)
                        method_params = method.params[1:] if is_instance_method else method.params
                        for i, (arg, param) in enumerate(zip(call.arguments, method_params)):
                            if param.type_annotation:
                                expected_type = self.resolve_type(param.type_annotation)
                                # Pass expected type for bidirectional inference
                                arg_type = self.check_expression(arg, expected_type=expected_type)
                                
                                # Allow int→i64 coercion (widening only)
                                if isinstance(arg_type, IntType) and isinstance(expected_type, IntType):
                                    if arg_type == INT and expected_type == I64:
                                        arg_type = I64
                                    elif arg_type == INT:
                                        # Check if expected_type is u8 (U8 from types)
                                        from ..types import U8 as U8_TYPE
                                        if expected_type == U8_TYPE:
                                            # int → u8 coercion for small literals (0-255)
                                            if isinstance(arg, ast.IntLiteral) and 0 <= arg.value <= 255:
                                                arg_type = U8_TYPE
                                
                                if not types_compatible(arg_type, expected_type):
                                    self.error(
                                        f"Argument {i+1} to {type_name}.{call.method}: expected {expected_type}, got {arg_type}",
                                        call.span
                                    )
                        
                        # Return the method's return type
                        if method.return_type:
                            return_type = self.resolve_type(method.return_type)
                            # If return type is UNKNOWN and we have an expected type, try to use it
                            if (return_type == UNKNOWN or isinstance(return_type, UnknownType)) and expected_type:
                                # Check if expected type matches the generic type name
                                if isinstance(expected_type, GenericType):
                                    # Check if method return type annotation matches
                                    if isinstance(method.return_type, ast.PrimitiveType) and method.return_type.name == expected_type.name:
                                        return expected_type
                            return return_type
                        else:
                            return VOID
                
                # Method not found in impl block
                self.error(
                    f"Type '{type_name}' has no method '{call.method}'",
                    call.span
                )
                return UNKNOWN
        
        # For MVP, if we can't resolve the method, return unknown
        return UNKNOWN
    
    def check_field_access(self, access: ast.FieldAccess) -> Type:
        """Check field access"""
        import os
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        if debug:
            print(f"[TRACE check_field_access] ENTRY: object={type(access.object).__name__}, field={access.field}")
            if isinstance(access.object, ast.Identifier):
                print(f"  Identifier name: {access.object.name}")
            elif isinstance(access.object, ast.GenericType):
                print(f"  GenericType name: {access.object.name}")
        
        # First, check if this is a type name access (e.g., Result.Ok)
        if isinstance(access.object, ast.Identifier):
            # Check directly in the types dictionary FIRST to avoid lookup issues
            # This ensures we get the actual registered enum, not a builtin placeholder
            enum_type = None
            type_name = access.object.name
            field_name = access.field
            
            import os
            debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
            
            if debug:
                print(f"[TRACE check_field_access] Accessing {type_name}.{field_name}")
                print(f"  global_scope id: {id(self.resolver.global_scope)}")
                print(f"  global_scope.types id: {id(self.resolver.global_scope.types)}")
                print(f"  type_name in types: {type_name in self.resolver.global_scope.types}")
            
            # Check types dictionary directly
            if type_name in self.resolver.global_scope.types:
                direct_type = self.resolver.global_scope.types[type_name]
                if debug:
                    print(f"  direct_type: {type(direct_type).__name__} = {direct_type}")
                    print(f"  isinstance(direct_type, EnumType): {isinstance(direct_type, EnumType)}")
                    print(f"  direct_type is UNKNOWN: {direct_type is UNKNOWN}")
                
                # Check if it's an EnumType - use both isinstance and type check for safety
                if isinstance(direct_type, EnumType) or (hasattr(direct_type, '__class__') and direct_type.__class__.__name__ == 'EnumType'):
                    enum_type = direct_type
                    if debug:
                        print(f"  Found EnumType in types dict: {enum_type.name}")
                # If it's UNKNOWN, that means the enum wasn't registered (shouldn't happen)
                elif direct_type is not UNKNOWN:
                    # Some other type - not what we're looking for
                    if debug:
                        print(f"  Found non-EnumType in types dict: {type(direct_type).__name__}")
                    pass
                else:
                    if debug:
                        print(f"  Found UNKNOWN in types dict (enum not registered?)")
            
            # If not found in types dict, try lookup_type as fallback (shouldn't happen for registered enums)
            if enum_type is None:
                if debug:
                    print(f"  Trying lookup_type fallback...")
                looked_up = self.resolver.global_scope.lookup_type(type_name)
                if debug:
                    print(f"  lookup_type result: {type(looked_up).__name__} = {looked_up}")
                if isinstance(looked_up, EnumType):
                    enum_type = looked_up
                    if debug:
                        print(f"  Found EnumType via lookup_type: {enum_type.name}")
            
            # Check if it's an EnumType (not UNKNOWN placeholder or None)
            if enum_type is not None and isinstance(enum_type, EnumType):
                if debug:
                    print(f"  enum_type is valid EnumType: {enum_type.name}")
                    print(f"  Checking for field '{access.field}' in variants: {list(enum_type.variants.keys())}")
                if access.field in enum_type.variants:
                    variant_field_types = enum_type.variants[access.field]
                    if variant_field_types is None:
                        # Variant with no fields - return function that takes no args and returns enum
                        return FunctionType(param_types=[], return_type=enum_type)
                    else:
                        # Variant with fields - return function that takes field types and returns enum
                        # Create a copy of variant_field_types to avoid mutating the original
                        # The types might be TypeVariables (for generic enums) which is fine
                        # TypeVariables will be resolved during type checking when arguments are provided
                        return FunctionType(param_types=list(variant_field_types), return_type=enum_type)
                else:
                    self.error(f"Enum {enum_type.name} has no variant '{access.field}'", access.span)
                    return UNKNOWN
            
            # If enum_type is still None, check if the type name exists in types dict but wasn't recognized
            # This is a fallback in case isinstance fails for some reason
            if enum_type is None:
                # Try checking types dict again with structure check
                if type_name in self.resolver.global_scope.types:
                    direct_type = self.resolver.global_scope.types[type_name]
                    # Check if it has the structure of an EnumType (has variants and name attributes)
                    if (hasattr(direct_type, 'variants') and hasattr(direct_type, 'name') and 
                        isinstance(direct_type.variants, dict)):
                        # This looks like an enum - use it
                        if access.field in direct_type.variants:
                            variant_field_types = direct_type.variants[access.field]
                            if variant_field_types is None:
                                return FunctionType(param_types=[], return_type=direct_type)
                            else:
                                return FunctionType(param_types=list(variant_field_types), return_type=direct_type)
            
            # If enum_type is UNKNOWN or None, check if it's actually a type name that failed
            # If the identifier is in the types dict but not an enum, it's a struct/other type access
            # Otherwise, fall through to check as variable field access
            if enum_type is None:
                # Check if identifier name exists in types dict as a non-enum type
                if type_name in self.resolver.global_scope.types:
                    # It's a type name but not an enum - this is invalid (can't do Point.field)
                    # But we should still check if it's a variable first
                    # Fall through to normal field access check below
                    pass
                else:
                    # Not a type name at all - definitely a variable, fall through to normal field access
                    pass
        
        # Check as normal field access (variable.field or struct.field if type name was found but not enum)
        import os
        debug = os.environ.get('PYRITE_DEBUG_VLOOKUP') == '1'
        if debug:
            print(f"[VLOOKUP] Field access: checking object {access.object} (type: {type(access.object).__name__})")
            if isinstance(access.object, ast.Identifier):
                print(f"[VLOOKUP] Field access object is Identifier: {access.object.name}")
        object_type = self.check_expression(access.object)
        if debug:
            print(f"[VLOOKUP] Field access: {access.object} -> {object_type}, field: {access.field}")
        
        # If object_type is UNKNOWN, we can't proceed with field access
        if object_type == UNKNOWN or isinstance(object_type, UnknownType):
            if debug:
                print(f"[VLOOKUP] Field access on UNKNOWN type, returning UNKNOWN")
            # Try to infer from context - if field is "data" or "len", it might be String
            # But for now, return UNKNOWN and let the error propagate
            return UNKNOWN
        
        # Dereference if it's a reference
        if isinstance(object_type, ReferenceType):
            object_type = object_type.inner
        
        # Special handling for StringType (String has data: *u8 and len: i64 fields)
        # Check both isinstance and equality since StringType might be a singleton
        is_string_type = (isinstance(object_type, StringType) or 
                         object_type == STRING or
                         (hasattr(object_type, '__class__') and object_type.__class__.__name__ == 'StringType'))
        
        if is_string_type:
            if access.field == "data":
                from ..types import PointerType, U8
                return PointerType(U8, False)  # *u8
            elif access.field == "len":
                from ..types import I64
                return I64
            else:
                self.error(f"String has no field '{access.field}'", access.span)
                return UNKNOWN
        
        if isinstance(object_type, StructType):
            if access.field in object_type.fields:
                return object_type.fields[access.field]
            else:
                self.error(f"Struct {object_type.name} has no field '{access.field}'", access.span)
                return UNKNOWN
        elif isinstance(object_type, EnumType):
            # Enum variant access (e.g., Result.Ok)
            if access.field in object_type.variants:
                variant_field_types = object_type.variants[access.field]
                # Return a FunctionType representing the constructor
                # For now, we'll use the enum type itself as the return type
                # In a full implementation, we'd need to handle generic enums properly
                if variant_field_types is None:
                    # Variant with no fields (e.g., Option.None)
                    return FunctionType(param_types=[], return_type=object_type)
                else:
                    # Variant with fields (e.g., Result.Ok(value: T))
                    return FunctionType(param_types=variant_field_types, return_type=object_type)
            else:
                self.error(f"Enum {object_type.name} has no variant '{access.field}'", access.span)
                return UNKNOWN
        
        # For MVP, allow field access on other types (will be resolved later)
        return UNKNOWN
    
    def check_index_access(self, access: ast.IndexAccess) -> Type:
        """Check index access"""
        object_type = self.check_expression(access.object)
        index_type = self.check_expression(access.index)
        
        # Check index is integer
        if not isinstance(index_type, IntType):
            self.error(f"Index must be integer, got {index_type}", access.span)
        
        # Determine element type
        if isinstance(object_type, ArrayType):
            return object_type.element
        elif isinstance(object_type, SliceType):
            return object_type.element
        elif isinstance(object_type, GenericType) and object_type.name == "List":
            if object_type.type_args:
                return object_type.type_args[0]
            return UNKNOWN
        elif isinstance(object_type, PointerType):
            return object_type.inner
        else:
            # Type is not indexable
            self.error(f"Cannot index type {object_type}", access.span)
            return UNKNOWN
    
    def check_as_expression(self, cast: ast.AsExpression) -> Type:
        """Check cast expression"""
        expr_type = self.check_expression(cast.expression)
        target_type = self.resolve_type(cast.target_type)
        
        # In unsafe mode, allow more casts
        # For now, allow any pointer cast
        if isinstance(expr_type, (PointerType, ReferenceType)) and isinstance(target_type, (PointerType, ReferenceType)):
            return target_type
        
        # Allow casting String to *u8 in unsafe mode (extract data pointer)
        if isinstance(expr_type, StringType) and isinstance(target_type, PointerType) and isinstance(target_type.inner, IntType) and target_type.inner.width == 8:
            return target_type

        # Default compatibility check
        if types_compatible(expr_type, target_type):
            return target_type
            
        self.error(f"Cannot cast {expr_type} to {target_type}", cast.span)
        return target_type
    
    def check_struct_literal(self, literal: ast.StructLiteral) -> Type:
        """Check struct literal"""
        struct_type = self.resolver.lookup_type(literal.struct_name, literal.span)
        
        if not struct_type or not isinstance(struct_type, StructType):
            self.error(f"Unknown struct type: {literal.struct_name}", literal.span)
            return UNKNOWN
        
        # Check all fields are provided
        provided_fields = {name for name, _ in literal.fields}
        expected_fields = set(struct_type.fields.keys())
        
        missing = expected_fields - provided_fields
        if missing:
            self.error(f"Missing fields in struct literal: {', '.join(missing)}", literal.span)
        
        extra = provided_fields - expected_fields
        if extra:
            self.error(f"Unknown fields in struct literal: {', '.join(extra)}", literal.span)
        
        # Check field types
        for field_name, field_value in literal.fields:
            if field_name in struct_type.fields:
                expected_type = struct_type.fields[field_name]
                actual_type = self.check_expression(field_value)
                if not types_compatible(actual_type, expected_type):
                    self.error(
                        f"Field '{field_name}': expected {expected_type}, got {actual_type}",
                        literal.span
                    )
        
        return struct_type
    
    def check_list_literal(self, literal: ast.ListLiteral) -> Type:
        """Check list literal"""
        if not literal.elements:
            # Empty list - for MVP, return unknown
            return UNKNOWN
        
        # Check all elements have same type
        first_type = self.check_expression(literal.elements[0])
        for elem in literal.elements[1:]:
            elem_type = self.check_expression(elem)
            if not types_compatible(elem_type, first_type):
                self.error(f"List elements must have same type", literal.span)
                break
        
        # Return generic List type (simplified)
        return GenericType("List", None, [first_type])
    
    def check_try_expr(self, try_expr: ast.TryExpr) -> Type:
        """Check try expression
        
        try expr requires expr to be Result[T, E] and returns T.
        If expr is not a Result type, this is a type error.
        """
        import os
        debug = os.environ.get('PYRITE_DEBUG_TYPE_RESOLUTION') == '1'
        
        if debug:
            print(f"[TRACE check_try_expr] ENTRY: expression={type(try_expr.expression).__name__}")
            if isinstance(try_expr.expression, ast.FunctionCall):
                if isinstance(try_expr.expression.function, ast.Identifier):
                    print(f"  Function name: {try_expr.expression.function.name}")
        
        expr_type = self.check_expression(try_expr.expression)
        
        if debug:
            print(f"[TRACE check_try_expr] Expression type: {type(expr_type).__name__} = {expr_type}")
            if isinstance(expr_type, GenericType):
                print(f"  GenericType name: {expr_type.name}")
                print(f"  GenericType type_args: {expr_type.type_args}")
        
        # Check if expression type is Result[T, E]
        if isinstance(expr_type, GenericType) and expr_type.name == "Result":
            if len(expr_type.type_args) == 2:
                # Return the Ok type (first type argument)
                return expr_type.type_args[0]
            else:
                self.error(
                    f"Result type must have exactly 2 type arguments, got {len(expr_type.type_args)}",
                    try_expr.span
                )
                return UNKNOWN
        else:
            # Expression is not a Result type
            self.error(
                f"try operator can only be used on Result types, got {expr_type}",
                try_expr.span
            )
            return UNKNOWN

    def check_old_expr(self, old_expr: ast.OldExpr) -> Type:
        """Type check old() expression for DbC"""
        if not self.is_inside_ensures:
            self.error("old() can only be used within @ensures postconditions", old_expr.span)
        
        # Type of old(expr) is the same as type of expr
        return self.check_expression(old_expr.expression)
    
    def check_quantified_expr(self, quantified: ast.QuantifiedExpr) -> Type:
        """Type check quantified expression (forall/exists) (SPEC-LANG-0405)"""
        # Check collection type - must be iterable (List, Array, Slice, etc.)
        collection_type = self.check_expression(quantified.collection)
        
        # For now, check if it's a List, Array, or Slice
        element_type = None
        if isinstance(collection_type, ArrayType):
            element_type = collection_type.element_type
        elif isinstance(collection_type, SliceType):
            element_type = collection_type.element_type
        elif isinstance(collection_type, GenericType) and collection_type.name == "List":
            if collection_type.type_args:
                element_type = collection_type.type_args[0]
        
        if element_type is None:
            self.error(f"Quantified expression requires an iterable collection (List, Array, or Slice), got {collection_type}", quantified.collection.span)
            return BOOL  # Return bool as fallback
        
        # Enter scope for bound variable
        self.resolver.enter_scope()
        self.resolver.define_variable(quantified.variable, element_type, False, quantified.span)
        
        # Check predicate - must be boolean
        predicate_type = self.check_expression(quantified.predicate)
        if predicate_type != BOOL:
            self.error(f"Predicate in quantified expression must be boolean, got {predicate_type}", quantified.predicate.span)
        
        # Exit scope
        self.resolver.exit_scope()
        
        # Quantified expressions always return bool
        return BOOL
    
    def _track_constraint(self, expr: ast.Expression):
        """Track a constraint from @requires for range analysis (SPEC-LANG-0406)"""
        # Track simple comparisons: x > 0, x >= 0, x < 10, etc.
        if isinstance(expr, ast.BinOp) and expr.op in ('>', '>=', '<', '<=', '==', '!='):
            # Check if left side is a variable and right side is a constant
            if isinstance(expr.left, ast.Identifier):
                var_name = expr.left.name
                if var_name not in self.variable_constraints:
                    self.variable_constraints[var_name] = []
                self.variable_constraints[var_name].append(expr)
            # Also check if right side is a variable and left side is a constant
            elif isinstance(expr.right, ast.Identifier):
                var_name = expr.right.name
                if var_name not in self.variable_constraints:
                    self.variable_constraints[var_name] = []
                # Reverse the comparison for tracking
                reversed_op = {'>': '<', '>=': '<=', '<': '>', '<=': '>=', '==': '==', '!=': '!='}[expr.op]
                reversed_expr = ast.BinOp(expr.right, reversed_op, expr.left, expr.span)
                self.variable_constraints[var_name].append(reversed_expr)
    
    def _prove_from_constraints(self, expr: ast.Expression) -> Optional[bool]:
        """Try to prove an expression using tracked constraints (SPEC-LANG-0406)"""
        # Handle simple comparisons using constraints
        if isinstance(expr, ast.BinOp) and expr.op in ('>', '>=', '<', '<=', '==', '!='):
            # Check if we can prove this from constraints
            if isinstance(expr.left, ast.Identifier):
                var_name = expr.left.name
                constraints = self.variable_constraints.get(var_name, [])
                right_const = self.evaluate_constant_int(expr.right)
                
                if right_const is not None:
                    # Check each constraint
                    for constraint in constraints:
                        if isinstance(constraint, ast.BinOp) and isinstance(constraint.right, (ast.IntLiteral, ast.FloatLiteral)):
                            constraint_const = self.evaluate_constant_int(constraint.right)
                            if constraint_const is not None:
                                # Try to prove the expression
                                if constraint.op == '>' and expr.op == '>=':
                                    # If we know x > 5, then x >= 4 is true
                                    if constraint_const >= right_const:
                                        return True
                                elif constraint.op == '>=' and expr.op == '>=':
                                    # If we know x >= 5, then x >= 4 is true
                                    if constraint_const >= right_const:
                                        return True
                                elif constraint.op == '>' and expr.op == '>':
                                    # If we know x > 5, then x > 4 is true
                                    if constraint_const >= right_const:
                                        return True
                                elif constraint.op == '<' and expr.op == '<=':
                                    # If we know x < 5, then x <= 6 is true
                                    if constraint_const <= right_const:
                                        return True
                                elif constraint.op == '<=' and expr.op == '<=':
                                    # If we know x <= 5, then x <= 6 is true
                                    if constraint_const <= right_const:
                                        return True
                                elif constraint.op == '<' and expr.op == '<':
                                    # If we know x < 5, then x < 6 is true
                                    if constraint_const <= right_const:
                                        return True
                                elif constraint.op == '==' and expr.op == '==':
                                    # If we know x == 5, then x == 5 is true
                                    if constraint_const == right_const:
                                        return True
                                elif constraint.op == '==' and expr.op == '!=':
                                    # If we know x == 5, then x != 4 is true
                                    if constraint_const != right_const:
                                        return True
                                elif constraint.op == '>' and expr.op == '<':
                                    # If we know x > 5, then x < 4 is false
                                    if constraint_const >= right_const:
                                        return False
                                elif constraint.op == '<' and expr.op == '>':
                                    # If we know x < 5, then x > 6 is false
                                    if constraint_const <= right_const:
                                        return False
        
        return None
    
    def evaluate_constant_int(self, expr: ast.Expression) -> Optional[int]:
        """Evaluate a constant integer expression (SPEC-LANG-0216)"""
        if isinstance(expr, ast.IntLiteral):
            return expr.value
        elif isinstance(expr, ast.BinOp):
            left = self.evaluate_constant_int(expr.left)
            right = self.evaluate_constant_int(expr.right)
            
            if left is not None and right is not None:
                if expr.op == "+": return left + right
                if expr.op == "-": return left - right
                if expr.op == "*": return left * right
                if expr.op == "/":
                    if right == 0:
                        self.error("Division by zero in constant expression", expr.span)
                        return None
                    return left // right
                if expr.op == "%":
                    if right == 0:
                        self.error("Modulo by zero in constant expression", expr.span)
                        return None
                    return left % right
        elif isinstance(expr, ast.UnaryOp):
            operand = self.evaluate_constant_int(expr.operand)
            if operand is not None:
                if expr.op == "-": return -operand
                if expr.op == "+": return operand
        
        return None

    def evaluate_constant_bool(self, expr: ast.Expression) -> Optional[bool]:
        """Evaluate a constant boolean expression with range analysis (SPEC-LANG-0406)"""
        # First try to prove from constraints
        proven = self._prove_from_constraints(expr)
        if proven is not None:
            return proven
        
        # Fall back to constant evaluation
        if isinstance(expr, ast.BoolLiteral):
            return expr.value
        elif isinstance(expr, ast.BinOp):
            if expr.op == '==':
                left = self.evaluate_constant_int(expr.left)
                right = self.evaluate_constant_int(expr.right)
                if left is not None and right is not None:
                    return left == right
                
                # Also handle bool comparison
                left_b = self.evaluate_constant_bool(expr.left)
                right_b = self.evaluate_constant_bool(expr.right)
                if left_b is not None and right_b is not None:
                    return left_b == right_b
            elif expr.op == '!=':
                val = self.evaluate_constant_bool(ast.BinOp(expr.left, '==', expr.right, expr.span))
                return not val if val is not None else None
            elif expr.op == '>':
                left = self.evaluate_constant_int(expr.left)
                right = self.evaluate_constant_int(expr.right)
                if left is not None and right is not None:
                    return left > right
            elif expr.op == '<':
                left = self.evaluate_constant_int(expr.left)
                right = self.evaluate_constant_int(expr.right)
                if left is not None and right is not None:
                    return left < right
            elif expr.op == '>=':
                left = self.evaluate_constant_int(expr.left)
                right = self.evaluate_constant_int(expr.right)
                if left is not None and right is not None:
                    return left >= right
            elif expr.op == '<=':
                left = self.evaluate_constant_int(expr.left)
                right = self.evaluate_constant_int(expr.right)
                if left is not None and right is not None:
                    return left <= right
            elif expr.op == 'and':
                left = self.evaluate_constant_bool(expr.left)
                right = self.evaluate_constant_bool(expr.right)
                if left is not None and right is not None:
                    return left and right
            elif expr.op == 'or':
                left = self.evaluate_constant_bool(expr.left)
                right = self.evaluate_constant_bool(expr.right)
                if left is not None and right is not None:
                    return left or right
        elif isinstance(expr, ast.UnaryOp):
            if expr.op == 'not':
                val = self.evaluate_constant_bool(expr.operand)
                return not val if val is not None else None
        return None

    def resolve_type(self, type_annotation: ast.Type) -> Type:
        """Resolve a type annotation to a Type"""
        if isinstance(type_annotation, ast.PrimitiveType):
            prim = primitive_type_from_name(type_annotation.name)
            if prim:
                return prim
            
            # Check if it's a compile-time parameter (registered as variable)
            # Use lookup directly to avoid triggering error
            symbol = self.resolver.current_scope.lookup(type_annotation.name)
            if symbol:
                # If it's a compile-time parameter, return its type
                return symbol.type
            
            # Check if it's a user-defined type (but don't trigger error if not found)
            # We'll handle the error ourselves
            # Use global_scope.lookup_type directly to avoid error() call in NameResolver.lookup_type
            user_type = self.resolver.global_scope.lookup_type(type_annotation.name)
            if user_type:
                # If it's UNKNOWN, it might be a forward reference (e.g., enum referencing itself)
                # Allow it during registration phase - this is valid for recursive types
                if user_type == UNKNOWN:
                    return user_type  # Allow UNKNOWN as a placeholder for forward references
                
                # Check if it's a type alias (non-generic)
                # If the resolved type is different from what we'd expect for the name,
                # it might be an alias. For now, just return the resolved type.
                # Generic aliases are handled in GenericType resolution above.
                return user_type
            
            # Only error if we're not in registration phase (i.e., during function body checking)
            # During registration, forward references are allowed
            # We can detect this by checking if we're currently registering a type
            # For now, we'll be lenient and allow UNKNOWN types
            # The error will be caught later if the type is never properly defined
            self.error(f"Unknown type: {type_annotation.name}", type_annotation.span)
            return UNKNOWN
        
        elif isinstance(type_annotation, ast.ReferenceType):
            inner = self.resolve_type(type_annotation.inner)
            return ReferenceType(inner, type_annotation.mutable)
        
        elif isinstance(type_annotation, ast.PointerType):
            inner = self.resolve_type(type_annotation.inner)
            return PointerType(inner, type_annotation.mutable)
        
        elif isinstance(type_annotation, ast.ArrayType):
            element = self.resolve_type(type_annotation.element_type)
            # Evaluate constant expression for size (SPEC-LANG-0216)
            size = self.evaluate_constant_int(type_annotation.size)
            if size is not None:
                if size < 0:
                    self.error("Array size cannot be negative", type_annotation.span)
                    return ArrayType(element, 0)
                return ArrayType(element, size)
            else:
                self.error("Array size must be constant integer", type_annotation.span)
                return ArrayType(element, 0)
        
        elif isinstance(type_annotation, ast.SliceType):
            element = self.resolve_type(type_annotation.element_type)
            return SliceType(element)
        
        elif isinstance(type_annotation, ast.GenericType):
            type_args = [self.resolve_type(t) for t in type_annotation.type_args]
            # Look up the base type - use global_scope directly to avoid error on forward refs
            base_type = self.resolver.global_scope.lookup_type(type_annotation.name)
            
            # Check if this is a type alias
            if type_annotation.name in self.type_aliases:
                alias_params, alias_target = self.type_aliases[type_annotation.name]
                
                # Build substitution map: alias param -> actual type arg
                subst_map = {}
                if len(alias_params) == len(type_args):
                    for param, arg in zip(alias_params, type_args):
                        subst_map[param.name] = arg
                    
                    # Substitute type variables in the target type
                    resolved_target = self.substitute_type_vars(alias_target, subst_map)
                    return resolved_target
            
            # Check if base_type is itself a GenericType (type alias to generic type)
            # For example: type Optional[T] = Option[T]
            # When we see Optional[int], we need to resolve it to Option[int]
            if isinstance(base_type, GenericType) and base_type.type_args:
                # This is a generic type alias - substitute type variables
                # For now, simple substitution: if the alias has one param and target has one param
                # TODO: Handle more complex cases with multiple type parameters
                if len(type_annotation.type_args) == len(base_type.type_args):
                    # Create new GenericType with substituted type arguments
                    return GenericType(
                        base_type.name,
                        base_type.base_type,
                        type_args  # Use the type args from the alias usage
                    )
            
            # If not found, use UNKNOWN (might be forward reference)
            if not base_type:
                base_type = UNKNOWN
            return GenericType(type_annotation.name, base_type, type_args)
        
        elif isinstance(type_annotation, ast.FunctionType):
            param_types = [self.resolve_type(t) for t in type_annotation.param_types]
            return_type = None
            if type_annotation.return_type:
                return_type = self.resolve_type(type_annotation.return_type)
            return FunctionType(param_types, return_type)
        
        elif isinstance(type_annotation, ast.TupleType):
            element_types = [self.resolve_type(t) for t in type_annotation.element_types]
            # Empty tuple () is the unit type, equivalent to void
            if len(element_types) == 0:
                return VOID
            return TupleType(element_types)
        
        elif isinstance(type_annotation, ast.AssociatedTypeRef):
            # Resolve associated type: Trait::Item or Self::Item
            trait_name = type_annotation.trait_name
            assoc_type_name = type_annotation.associated_type_name
            
            # Look up the trait
            trait_type = self.resolver.lookup_type(trait_name)
            if not trait_type or not isinstance(trait_type, TraitType):
                if trait_name == "Self":
                    # Self::Item - need to find current impl context
                    # For MVP, return UNKNOWN (will be resolved during impl checking)
                    return UNKNOWN
                else:
                    self.error(f"Trait '{trait_name}' not found", type_annotation.span)
                    return UNKNOWN
            
            # Check if trait has this associated type
            if assoc_type_name not in trait_type.associated_types:
                self.error(
                    f"Trait '{trait_name}' does not have associated type '{assoc_type_name}'",
                    type_annotation.span
                )
                return UNKNOWN
            
            # For MVP, return UNKNOWN - will be resolved to concrete type during impl checking
            # In full implementation, we'd track the current impl context and resolve to concrete type
            return UNKNOWN
        
        else:
            self.error(f"Unknown type annotation: {type(type_annotation)}", type_annotation.span)
            return UNKNOWN
    
    def check_parameter_closure(self, closure: ast.ParameterClosure) -> Type:
        """
        Type check a parameter closure (fn[...])
        
        Parameter closures are compile-time only and must:
        - Be inlinable (no recursion, reasonable size)
        - Not allocate (no heap operations)
        - Not escape (grammar already enforces this)
        """
        # Enter closure scope
        self.resolver.enter_scope()
        
        # Add parameters to scope
        param_types = []
        for param in closure.params:
            param_type = self.resolve_type(param.type_annotation)
            param_types.append(param_type)
            self.resolver.define_variable(param.name, param_type, False, param.span)
        
        # Determine return type
        if closure.return_type:
            return_type = self.resolve_type(closure.return_type)
        else:
            # Infer from body (single expression)
            if closure.body.statements:
                return_stmt = closure.body.statements[0]
                if isinstance(return_stmt, ast.ReturnStmt) and return_stmt.value:
                    return_type = self.check_expression(return_stmt.value)
                else:
                    return_type = VOID
            else:
                return_type = VOID
        
        # Save current function return type and set closure's return type
        saved_return_type = self.current_function_return_type
        self.current_function_return_type = return_type
        
        # Check body
        self.check_block(closure.body)
        
        # Restore function return type
        self.current_function_return_type = saved_return_type
        
        # Exit closure scope
        self.resolver.exit_scope()
        
        # Mark as zero-cost (compiler guarantees)
        closure.can_inline = True
        closure.allocates = False
        closure.escapes = False
        
        # Return function type
        return FunctionType(param_types, return_type)
    
    def check_runtime_closure(self, closure: ast.RuntimeClosure) -> Type:
        """
        Type check a runtime closure (fn(...))
        
        Runtime closures are first-class values that:
        - Can be stored, returned, passed anywhere
        - May allocate (environment on heap if captures exist)
        - Can escape scope
        """
        # Collect variables from outer scope before entering closure scope
        outer_scope_vars = self._collect_outer_scope_variables()
        
        # Enter closure scope
        self.resolver.enter_scope()
        
        # Add parameters to scope
        param_types = []
        for param in closure.params:
            param_type = self.resolve_type(param.type_annotation)
            param_types.append(param_type)
            self.resolver.define_variable(param.name, param_type, False, param.span)
        
        # Determine return type
        if closure.return_type:
            return_type = self.resolve_type(closure.return_type)
        else:
            # Infer from body (single expression)
            if closure.body.statements:
                return_stmt = closure.body.statements[0]
                if isinstance(return_stmt, ast.ReturnStmt) and return_stmt.value:
                    return_type = self.check_expression(return_stmt.value)
                else:
                    return_type = VOID
            else:
                return_type = VOID
        
        # Save current function return type and set closure's return type
        saved_return_type = self.current_function_return_type
        self.current_function_return_type = return_type
        
        # Check body
        self.check_block(closure.body)
        
        # Restore function return type
        self.current_function_return_type = saved_return_type
        
        # Analyze captured variables (exclude closure parameters)
        param_names = [param.name for param in closure.params]
        captured_vars = self._find_captured_variables(closure.body, outer_scope_vars, param_names)
        closure.captures = captured_vars
        
        # Calculate environment size (sum of captured variable sizes)
        env_size = 0
        for var_name in captured_vars:
            var_type = outer_scope_vars.get(var_name)
            if var_type:
                # For now, assume pointer-sized capture (8 bytes)
                # In full implementation, calculate actual type size
                env_size += 8
        
        closure.environment_size = env_size
        
        # Exit closure scope
        self.resolver.exit_scope()
        
        # Return function type
        return FunctionType(param_types, return_type)
    
    def _collect_outer_scope_variables(self) -> dict:
        """Collect all variables visible from current scope"""
        # Use the SymbolTable's get_all_symbols() method
        all_symbols = self.resolver.current_scope.get_all_symbols()
        
        # Convert to dict of name -> type
        outer_vars = {}
        for var_name, symbol in all_symbols.items():
            outer_vars[var_name] = symbol.type
        
        return outer_vars
    
    def _find_captured_variables(self, body: ast.Block, outer_scope_vars: dict, param_names: list = None) -> list:
        """Find variables captured by closure from outer scope"""
        if param_names is None:
            param_names = []
        
        captured = []
        used_vars = set()
        
        # Collect all variable references in closure body
        self._collect_variable_uses(body, used_vars)
        
        # Filter to only variables from outer scope (excluding closure parameters)
        for var_name in used_vars:
            if var_name in outer_scope_vars and var_name not in param_names:
                captured.append(var_name)
        
        return captured
    
    def _collect_variable_uses(self, node: ast.ASTNode, used_vars: set):
        """Recursively collect all variable references in an AST node"""
        if isinstance(node, ast.Identifier):
            used_vars.add(node.name)
        elif isinstance(node, ast.Block):
            for stmt in node.statements:
                self._collect_variable_uses(stmt, used_vars)
        elif isinstance(node, ast.ExpressionStmt):
            self._collect_variable_uses(node.expression, used_vars)
        elif isinstance(node, ast.ReturnStmt):
            if node.value:
                self._collect_variable_uses(node.value, used_vars)
        elif isinstance(node, ast.IfStmt):
            self._collect_variable_uses(node.condition, used_vars)
            self._collect_variable_uses(node.then_block, used_vars)
            if node.else_block:
                self._collect_variable_uses(node.else_block, used_vars)
        elif isinstance(node, ast.BinOp):
            self._collect_variable_uses(node.left, used_vars)
            self._collect_variable_uses(node.right, used_vars)
        elif isinstance(node, ast.UnaryOp):
            self._collect_variable_uses(node.operand, used_vars)
        elif isinstance(node, ast.FunctionCall):
            for arg in node.arguments:
                self._collect_variable_uses(arg, used_vars)
        elif isinstance(node, ast.FieldAccess):
            self._collect_variable_uses(node.object, used_vars)
        elif isinstance(node, ast.IndexAccess):
            self._collect_variable_uses(node.object, used_vars)
            self._collect_variable_uses(node.index, used_vars)
        elif isinstance(node, ast.VarDecl):
            # Don't traverse initializer (handled separately)
            pass
        # Add more node types as needed


def type_check(program: ast.Program, imported_modules: Optional[List['Module']] = None) -> TypeChecker:
    """Convenience function to type check a program
    
    Args:
        program: Main program AST
        imported_modules: List of Module objects from module_system (optional)
    """
    checker = TypeChecker()
    
    # Import symbols from imported modules before checking main program
    if imported_modules:
        for module in imported_modules:
            checker.import_module_symbols(module.ast)
    
    checker.check_program(program)
    return checker

