"""LLVM code generation for Pyrite.

This module generates LLVM IR from a type-checked AST. It handles all aspects
of code generation including function generation, expression evaluation, and
memory management.

Main Components:
    LLVMCodeGen: Main code generator class
    generate_llvm(): Convenience function to generate LLVM IR
    compile_to_executable(): Compile to native executable
    CodeGenError: Exception raised on code generation errors

See Also:
    type_checker: Type checks AST before code generation
    linker: Links generated code with standard library
    monomorphization: Instantiates generic functions
"""

from typing import Dict, Optional, List
from llvmlite import ir, binding
from .. import ast
from ..types import (
    Type, IntType, FloatType, BoolType, CharType, StringType, VoidType, NoneType,
    ReferenceType, PointerType, ArrayType, SliceType, StructType, EnumType,
    GenericType, FunctionType, TupleType, UnknownType, TypeVariable, SelfType,
    TraitType, OpaqueType
)
from ..frontend.tokens import Span
from ..passes.closure_inlining import ClosureInliner


# LLVM initialization is now automatic in newer versions
try:
    binding.initialize()
    binding.initialize_native_target()
    binding.initialize_native_asmprinter()
except RuntimeError:
    # Already initialized or deprecated - that's fine
    pass


class CodeGenError(Exception):
    """Code generation error"""
    def __init__(self, message: str, span: Optional[Span] = None):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}" if span else message)


class LLVMCodeGen:
    """LLVM IR code generator"""
    
    def __init__(self, deterministic: bool = False):
        self.module = ir.Module(name="pyrite_module")
        self.module.triple = binding.get_default_triple()
        
        self.builder: Optional[ir.IRBuilder] = None
        self.function: Optional[ir.Function] = None
        self.variables: Dict[str, ir.Value] = {}  # Variable name -> LLVM value
        self.variable_types: Dict[str, Type] = {}  # Variable name -> Pyrite type
        self.struct_types: Dict[str, ir.Type] = {}  # Struct name -> LLVM type
        self.enum_types: Dict[str, ir.Type] = {}  # Enum name -> LLVM type (for enums with fields)
        self.functions: Dict[str, ir.Function] = {}  # Function name -> LLVM function
        self.function_defs: Dict[str, ast.FunctionDef] = {}  # Function name -> AST node
        self.type_checker = None  # Will be set externally
        self.deterministic = deterministic  # Enable deterministic output (sort symbol tables, etc.)
        
        # Defer statement support - scope-based tracking
        self.defer_stack: List[ast.Block] = []  # Stack of defer blocks (LIFO execution)
        self.defer_scope_stack: List[int] = []  # Track defer stack size at each scope entry
        
        # Parameter closure inlining
        self.closure_inliner = ClosureInliner()
        
        # Runtime functions
        self.printf: Optional[ir.Function] = None
        self.assert_func: Optional[ir.Function] = None
        self.fail_func: Optional[ir.Function] = None
        self.malloc: Optional[ir.Function] = None
        self.free: Optional[ir.Function] = None
        
        # Runtime closure tracking
        self.closure_environments: Dict[str, ir.Type] = {}  # Closure name -> environment struct type
        self.closure_environment_types: Dict[str, Dict[str, Type]] = {}  # Closure name -> {var_name: type}
        
        # Loop control flow tracking (for break/continue with defer)
        self.break_targets: List[ir.Block] = []  # Stack of break target blocks
        self.continue_targets: List[ir.Block] = []  # Stack of continue target blocks
        
        # Cost analysis tracking
        self.track_costs: bool = False  # Enable cost tracking
        self.warn_costs: bool = False  # Enable cost warnings
        self.allocation_sites: List[Dict] = []  # List of allocation sites: {function, line, type, bytes, description}
        self.copy_sites: List[Dict] = []  # List of copy sites: {function, line, type, bytes}
        self.cost_warnings: List[Dict] = []  # List of cost warnings: {span, message, help_hint}
    
    def get_cost_report(self) -> Dict:
        """Get cost analysis report from codegen
        
        Returns:
            Dictionary with allocation_sites and copy_sites
        """
        total_allocations = len(self.allocation_sites)
        total_allocation_bytes = sum(site.get("bytes", 0) for site in self.allocation_sites)
        total_copies = len(self.copy_sites)
        total_copy_bytes = sum(site.get("bytes", 0) for site in self.copy_sites)
        
        return {
            "allocations": self.allocation_sites,
            "copies": self.copy_sites,
            "summary": {
                "total_allocations": total_allocations,
                "total_allocation_bytes": total_allocation_bytes,
                "total_copies": total_copies,
                "total_copy_bytes": total_copy_bytes
            }
        }
    
    def type_to_llvm(self, typ: Type) -> ir.Type:
        """Convert Pyrite type to LLVM type"""
        # Debug: Check if we're getting the right type
        # If typ is a GenericType wrapping an EnumType, unwrap it
        if hasattr(typ, 'base_type') and typ.base_type and isinstance(typ.base_type, EnumType):
            typ = typ.base_type
        
        if isinstance(typ, IntType):
            return ir.IntType(typ.width)
        
        elif isinstance(typ, FloatType):
            if typ.width == 32:
                return ir.FloatType()
            else:
                return ir.DoubleType()
        
        elif isinstance(typ, BoolType):
            return ir.IntType(1)
        
        elif isinstance(typ, CharType):
            return ir.IntType(32)  # Unicode code point
        
        elif isinstance(typ, StringType):
            # String: { i8*, i64 } (pointer, length)
            return ir.LiteralStructType([
                ir.IntType(8).as_pointer(),
                ir.IntType(64)
            ])
        
        elif isinstance(typ, VoidType) or isinstance(typ, NoneType):
            return ir.VoidType()
        
        elif isinstance(typ, ReferenceType):
            # Reference is a pointer
            inner = self.type_to_llvm(typ.inner)
            return inner.as_pointer()
        
        elif isinstance(typ, PointerType):
            inner = self.type_to_llvm(typ.inner)
            return inner.as_pointer()
        
        elif isinstance(typ, ArrayType):
            elem = self.type_to_llvm(typ.element)
            return ir.ArrayType(elem, typ.size)
        
        elif isinstance(typ, SliceType):
            # Slice: { T*, i64 } (pointer, length)
            elem = self.type_to_llvm(typ.element)
            return ir.LiteralStructType([
                elem.as_pointer(),
                ir.IntType(64)
            ])
        
        elif isinstance(typ, StructType):
            if typ.name in self.struct_types:
                return self.struct_types[typ.name]
            # Create struct type
            # Sort field names for deterministic order (must match gen_struct_literal)
            field_names = sorted(typ.fields.keys()) if self.deterministic else list(typ.fields.keys())
            field_types = [self.type_to_llvm(typ.fields[name]) for name in field_names]
            struct_ty = ir.LiteralStructType(field_types)
            self.struct_types[typ.name] = struct_ty
            return struct_ty
        
        elif isinstance(typ, GenericType):
            # Handle stdlib generic types
            if typ.name == "List":
                # List[T]: { T*, i64, i64 }
                elem = self.type_to_llvm(typ.type_args[0])
                return ir.LiteralStructType([
                    elem.as_pointer(),
                    ir.IntType(64),
                    ir.IntType(64)
                ])
            elif typ.name == "Map":
                # Map[K, V]: { buckets: *void, len: i64, cap: i64, key_size: i64, value_size: i64 }
                return ir.LiteralStructType([
                    ir.IntType(8).as_pointer(),  # buckets
                    ir.IntType(64),              # len
                    ir.IntType(64),              # cap
                    ir.IntType(64),              # key_size
                    ir.IntType(64)               # value_size
                ])
            # If GenericType wraps an EnumType (e.g., Type enum), use the base_type
            elif typ.base_type and isinstance(typ.base_type, EnumType):
                return self.type_to_llvm(typ.base_type)
            # Add more as needed
        
        elif isinstance(typ, FunctionType):
            # Function pointer type: fn(T1, T2) -> R
            param_types = [self.type_to_llvm(pt) for pt in typ.param_types]
            return_type = self.type_to_llvm(typ.return_type) if typ.return_type else ir.VoidType()
            func_ty = ir.FunctionType(return_type, param_types)
            return func_ty.as_pointer()  # Function pointers are pointers to functions
        
        elif isinstance(typ, EnumType):
            # Check if enum has any variants with fields
            has_fields = any(fields is not None and len(fields) > 0 
                           for fields in typ.variants.values())
            
            if not has_fields:
                # Simple enum without fields - use i32 tag
                return ir.IntType(32)
            
            # Enum with fields - create struct type: { i32 tag, ...fields }
            # For MVP, we need a consistent struct type for all variants
            # Strategy: find the variant with the most fields, use that as the struct layout
            # For variants with fewer fields, we'll pad with unused values
            if typ.name in self.enum_types:
                return self.enum_types[typ.name]
            
            # Find maximum field count across all variants
            max_fields = 0
            for fields in typ.variants.values():
                if fields:
                    max_fields = max(max_fields, len(fields))
            
            if max_fields == 0:
                # Should not happen (has_fields check above), but handle it
                enum_struct = ir.LiteralStructType([ir.IntType(32)])
            else:
                # Create struct: { i32 tag, i64 field0, i64 field1, ... }
                # Use individual i64 fields instead of array to avoid LLVM constant issues
                # Limit to 8 fields max for MVP (covers most enum variants)
                # Note: This is a simplification - proper tagged union would be better
                max_fields_limited = min(max_fields, 8)
                i64_type = ir.IntType(64)
                struct_fields = [ir.IntType(32)]  # tag
                # Add individual i64 fields (avoid creating list with * operator that might cause issues)
                for _ in range(max_fields_limited):
                    struct_fields.append(i64_type)
                enum_struct = ir.LiteralStructType(struct_fields)
            
            self.enum_types[typ.name] = enum_struct
            return enum_struct
        
        elif isinstance(typ, TupleType):
            # Tuple: { T1, T2, ... }
            elem_types = [self.type_to_llvm(t) for t in typ.elements]
            return ir.LiteralStructType(elem_types)
        
        elif isinstance(typ, OpaqueType):
            # Opaque type: generate as void* (opaque pointer)
            return ir.IntType(8).as_pointer()  # void* in LLVM is i8*
        
        # Default: i64
        return ir.IntType(64)
    
    def _create_zero_constant(self, ty: ir.Type) -> ir.Value:
        """Create a zero-initialized constant for any LLVM type.
        
        Handles:
        - Primitive types (int, float): returns ir.Constant(ty, 0)
        - Struct types: creates list of zero constants for each field
        - Array types: creates list of zero constants for each element
        - Pointer types: returns null pointer (ir.Constant(ty, None))
        - Void: raises error (shouldn't be called for void)
        """
        if isinstance(ty, ir.VoidType):
            raise CodeGenError("Cannot create zero constant for void type", None)
        
        # Primitive integer types
        if isinstance(ty, ir.IntType):
            return ir.Constant(ty, 0)
        
        # Primitive float types
        if isinstance(ty, ir.FloatType) or isinstance(ty, ir.DoubleType):
            return ir.Constant(ty, 0.0)
        
        # Pointer types - return null pointer
        if isinstance(ty, ir.PointerType):
            return ir.Constant(ty, None)
        
        # Array types - create list of zero constants for each element
        if isinstance(ty, ir.ArrayType):
            elem_type = ty.element
            zero_elem = self._create_zero_constant(elem_type)
            # Create list of zero constants for all elements
            zero_list = [zero_elem] * ty.count
            return ir.Constant(ty, zero_list)
        
        # Struct types - create list of zero constants for each field
        if isinstance(ty, ir.LiteralStructType):
            field_values = [self._create_zero_constant(elem) for elem in ty.elements]
            return ir.Constant(ty, field_values)
        
        # Unknown type - try default zero
        return ir.Constant(ty, 0)
    
    def _get_type_size(self, ty: ir.Type) -> int:
        """Get the size in bytes of an LLVM type (approximation for Map FFI).
        
        This is used to pass key_size and value_size to map_new().
        For MVP, we use simple size approximations.
        """
        if isinstance(ty, ir.IntType):
            return ty.width // 8  # Bits to bytes
        elif isinstance(ty, ir.FloatType):
            return 4
        elif isinstance(ty, ir.DoubleType):
            return 8
        elif isinstance(ty, ir.PointerType):
            return 8  # 64-bit pointer
        elif isinstance(ty, ir.ArrayType):
            elem_size = self._get_type_size(ty.element)
            return elem_size * ty.count
        elif isinstance(ty, ir.LiteralStructType):
            # Sum of all field sizes
            return sum(self._get_type_size(elem) for elem in ty.elements)
        else:
            # Default: assume 8 bytes (i64)
            return 8
    
    def declare_runtime_functions(self):
        """Declare C runtime functions"""
        # printf
        printf_ty = ir.FunctionType(
            ir.IntType(32),
            [ir.IntType(8).as_pointer()],
            var_arg=True
        )
        self.printf = ir.Function(self.module, printf_ty, name="printf")
        
        # malloc
        malloc_ty = ir.FunctionType(
            ir.IntType(8).as_pointer(),
            [ir.IntType(64)]
        )
        self.malloc = ir.Function(self.module, malloc_ty, name="malloc")
        
        # free
        free_ty = ir.FunctionType(
            ir.VoidType(),
            [ir.IntType(8).as_pointer()]
        )
        self.free = ir.Function(self.module, free_ty, name="free")
        
        # Pyrite builtins
        # pyrite_print_int
        print_int_ty = ir.FunctionType(ir.VoidType(), [ir.IntType(32)])
        self.print_int = ir.Function(self.module, print_int_ty, name="pyrite_print_int")
        
        # pyrite_panic
        panic_ty = ir.FunctionType(ir.VoidType(), [ir.IntType(8).as_pointer()])
        self.panic = ir.Function(self.module, panic_ty, name="pyrite_panic")
        
        # pyrite_check_bounds
        check_bounds_ty = ir.FunctionType(ir.VoidType(), [ir.IntType(64), ir.IntType(64)])
        self.check_bounds = ir.Function(self.module, check_bounds_ty, name="pyrite_check_bounds")
        
        # pyrite_assert - for tests: assert(condition: bool, message: Option[String])
        assert_ty = ir.FunctionType(ir.VoidType(), [ir.IntType(8), ir.IntType(8).as_pointer()])
        self.assert_func = ir.Function(self.module, assert_ty, name="pyrite_assert")
        
        # pyrite_fail - for tests: fail(message: String)
        fail_ty = ir.FunctionType(ir.VoidType(), [ir.IntType(8).as_pointer()])
        self.fail_func = ir.Function(self.module, fail_ty, name="pyrite_fail")
        
        # Map FFI functions
        # Map struct type: { buckets: *void, len: i64, cap: i64, key_size: i64, value_size: i64 }
        map_struct_ty = ir.LiteralStructType([
            ir.IntType(8).as_pointer(),  # buckets
            ir.IntType(64),              # len
            ir.IntType(64),              # cap
            ir.IntType(64),              # key_size
            ir.IntType(64)               # value_size
        ])
        # map_new(key_size: i64, value_size: i64) -> Map
        map_new_ty = ir.FunctionType(
            map_struct_ty,
            [ir.IntType(64), ir.IntType(64)]
        )
        self.map_new = ir.Function(self.module, map_new_ty, name="map_new")
        
        # map_insert(map: *mut Map, key: *const void, value: *const void) -> void
        map_insert_ty = ir.FunctionType(
            ir.VoidType(),
            [map_struct_ty.as_pointer(), ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer()]
        )
        self.map_insert = ir.Function(self.module, map_insert_ty, name="map_insert")
        
        # map_get(map: *const Map, key: *const void) -> *const void
        map_get_ty = ir.FunctionType(
            ir.IntType(8).as_pointer(),
            [map_struct_ty.as_pointer(), ir.IntType(8).as_pointer()]
        )
        self.map_get = ir.Function(self.module, map_get_ty, name="map_get")
        
        # map_contains(map: *const Map, key: *const void) -> i8
        map_contains_ty = ir.FunctionType(
            ir.IntType(8),
            [map_struct_ty.as_pointer(), ir.IntType(8).as_pointer()]
        )
        self.map_contains = ir.Function(self.module, map_contains_ty, name="map_contains")
        
        # map_length(map: *const Map) -> i64
        map_length_ty = ir.FunctionType(
            ir.IntType(64),
            [map_struct_ty.as_pointer()]
        )
        self.map_length = ir.Function(self.module, map_length_ty, name="map_length")
        
        # List FFI functions
        # List struct type: { data: *void, len: i64, cap: i64 }
        list_struct_ty = ir.LiteralStructType([
            ir.IntType(8).as_pointer(),  # data
            ir.IntType(64),              # len
            ir.IntType(64)               # cap
        ])
        
        # list_new(elem_size: i64) -> List
        list_new_ty = ir.FunctionType(list_struct_ty, [ir.IntType(64)])
        self.list_new = ir.Function(self.module, list_new_ty, name="list_new")

        # list_with_capacity(elem_size: i64, capacity: i64) -> List
        list_with_capacity_ty = ir.FunctionType(list_struct_ty, [ir.IntType(64), ir.IntType(64)])
        self.list_with_capacity = ir.Function(self.module, list_with_capacity_ty, name="list_with_capacity")
        
        # list_push(list: *mut List, elem: *const void, elem_size: i64) -> void
        list_push_ty = ir.FunctionType(ir.VoidType(), [list_struct_ty.as_pointer(), ir.IntType(8).as_pointer(), ir.IntType(64)])
        self.list_push = ir.Function(self.module, list_push_ty, name="list_push")
        
        # list_get(list: *const List, index: i64, elem_size: i64) -> *const void
        list_get_ty = ir.FunctionType(ir.IntType(8).as_pointer(), [list_struct_ty.as_pointer(), ir.IntType(64), ir.IntType(64)])
        self.list_get = ir.Function(self.module, list_get_ty, name="list_get")
        
        # list_length(list: *const List) -> i64
        list_length_ty = ir.FunctionType(ir.IntType(64), [list_struct_ty.as_pointer()])
        self.list_length = ir.Function(self.module, list_length_ty, name="list_length")

        # Set FFI functions
        # Set struct type: { buckets: *void, len: i64, cap: i64, elem_size: i64 }
        set_struct_ty = ir.LiteralStructType([
            ir.IntType(8).as_pointer(),  # buckets
            ir.IntType(64),              # len
            ir.IntType(64),              # cap
            ir.IntType(64)               # elem_size
        ])
        
        # set_new(elem_size: i64) -> Set
        set_new_ty = ir.FunctionType(set_struct_ty, [ir.IntType(64)])
        self.set_new = ir.Function(self.module, set_new_ty, name="set_new")
        
        # set_insert(set: *mut Set, elem: *const void) -> void
        set_insert_ty = ir.FunctionType(ir.VoidType(), [set_struct_ty.as_pointer(), ir.IntType(8).as_pointer()])
        self.set_insert = ir.Function(self.module, set_insert_ty, name="set_insert")
        
        # set_contains(set: *const Set, elem: *const void) -> i8
        set_contains_ty = ir.FunctionType(ir.IntType(8), [set_struct_ty.as_pointer(), ir.IntType(8).as_pointer()])
        self.set_contains = ir.Function(self.module, set_contains_ty, name="set_contains")
        
        # set_length(set: *const Set) -> i64
        set_length_ty = ir.FunctionType(ir.IntType(64), [set_struct_ty.as_pointer()])
        self.set_length = ir.Function(self.module, set_length_ty, name="set_length")
    
    def compile_program(self, program: ast.Program) -> ir.Module:
        """Generate LLVM IR for entire program"""
        # Declare runtime functions
        self.declare_runtime_functions()
        
        # Declare imported module symbols as extern
        if hasattr(self, 'imported_modules') and self.imported_modules:
            for module in self.imported_modules:
                self.declare_module_symbols(module.ast)
        
        # Sort items for deterministic order if enabled
        items = program.items
        if self.deterministic:
            # Sort by type and name for deterministic order
            def sort_key(item):
                if isinstance(item, ast.FunctionDef):
                    return (0, item.name)  # Functions first
                elif isinstance(item, ast.StructDef):
                    return (1, item.name)  # Structs second
                elif isinstance(item, ast.ImplBlock):
                    return (2, item.type_name)  # Impl blocks third
                else:
                    return (3, str(type(item)))  # Other items last
            items = sorted(items, key=sort_key)
        
        # First pass: declare all functions and types
        for item in items:
            if isinstance(item, ast.FunctionDef):
                self.declare_function(item)
            elif isinstance(item, ast.StructDef):
                self.declare_struct(item)
        
        # Second pass: declare impl methods (trait and inherent)
        for item in items:
            if isinstance(item, ast.ImplBlock):
                self.declare_impl_methods(item)
        
        # Third pass: generate function bodies
        for item in items:
            if isinstance(item, ast.FunctionDef):
                self.gen_function(item)
            elif isinstance(item, ast.ImplBlock):
                self.gen_impl_methods(item)
        
        return self.module
    
    def declare_module_symbols(self, module_ast: ast.Program):
        """Declare functions and methods from an imported module as extern"""
        for item in module_ast.items:
            if isinstance(item, ast.FunctionDef):
                self.declare_function(item)
            elif isinstance(item, ast.ImplBlock):
                self.declare_impl_methods(item)

    def declare_struct(self, struct_def: ast.StructDef):
        """Declare a struct type"""
        # For now, just register it (will be created on first use)
        pass
    
    def declare_impl_methods(self, impl: ast.ImplBlock):
        """Declare methods from an impl block (for trait or inherent impl)"""
        type_name = impl.type_name
        
        for method in impl.methods:
            # Generate method name: Type_Trait_method or Type_method
            if impl.trait_name:
                method_name = f"{type_name}_{impl.trait_name}_{method.name}"
            else:
                method_name = f"{type_name}_{method.name}"
            
            # Declare function signature
            param_types = []
            for param in method.params:
                # Special handling for 'self' parameter
                if param.name == 'self':
                    # Get the struct type for this impl
                    struct_type = None
                    if self.type_checker:
                        struct_type = self.type_checker.resolver.lookup_type(type_name)
                    if struct_type:
                        # Create LLVM struct type if needed
                        if type_name not in self.struct_types:
                            if isinstance(struct_type, StructType):
                                field_types = [self.type_to_llvm(ft) for ft in struct_type.fields.values()]
                                llvm_struct = ir.LiteralStructType(field_types)
                                self.struct_types[type_name] = llvm_struct
                        # self is always a pointer to the struct
                        if type_name in self.struct_types:
                            param_types.append(self.struct_types[type_name].as_pointer())
                        else:
                            # Fallback: use i64* (pointer-sized)
                            param_types.append(ir.IntType(64).as_pointer())
                    else:
                        # Fallback: use i64* (pointer-sized)
                        param_types.append(ir.IntType(64).as_pointer())
                elif param.type_annotation and self.type_checker:
                    pyrite_type = self.type_checker.resolve_type(param.type_annotation)
                    llvm_type = self.type_to_llvm(pyrite_type)
                    # Check if this is a reference type (&T, &mut T)
                    if hasattr(param.type_annotation, 'is_reference') and param.type_annotation.is_reference:
                        # Make it a pointer type
                        if not isinstance(llvm_type, ir.PointerType):
                            llvm_type = llvm_type.as_pointer()
                    param_types.append(llvm_type)
                else:
                    param_types.append(ir.IntType(32))
            
            # Return type
            if method.return_type:
                if self.type_checker:
                    pyrite_type = self.type_checker.resolve_type(method.return_type)
                    return_type = self.type_to_llvm(pyrite_type)
                else:
                    return_type = ir.IntType(32)
            else:
                return_type = ir.VoidType()
            
            # Create function type
            fnty = ir.FunctionType(return_type, param_types)
            
            # Create function
            func = ir.Function(self.module, fnty, name=method_name)
            self.functions[method_name] = func
            self.function_defs[method_name] = method
    
    def gen_impl_methods(self, impl: ast.ImplBlock):
        """Generate code for methods in an impl block"""
        type_name = impl.type_name
        
        # Sort methods for deterministic order if enabled
        methods = impl.methods
        if self.deterministic:
            methods = sorted(methods, key=lambda m: m.name)
        
        for method in methods:
            # Generate method name
            if impl.trait_name:
                method_name = f"{type_name}_{impl.trait_name}_{method.name}"
            else:
                method_name = f"{type_name}_{method.name}"
            
            if method_name not in self.functions:
                continue  # Skip if not declared
            
            func = self.functions[method_name]
            
            # Create entry block
            block = func.append_basic_block(name="entry")
            self.builder = ir.IRBuilder(block)
            self.function = func
            self.variables = {}
            self.variable_types = {}
            self.defer_stack = []
            self.defer_scope_stack = []
            self.break_targets = []
            self.continue_targets = []
            
            # Map parameters
            for param_def, llvm_arg in zip(method.params, func.args):
                llvm_arg.name = param_def.name
                self.variables[param_def.name] = llvm_arg
                
                if param_def.type_annotation and self.type_checker:
                    param_type = self.type_checker.resolve_type(param_def.type_annotation)
                    self.variable_types[param_def.name] = param_type
            
            # Generate body
            self.gen_block(method.body)
            
            # Add implicit return if needed
            if not self.builder.block.is_terminated:
                self.execute_defers(scope_start=0)
                if isinstance(func.ftype.return_type, ir.VoidType):
                    self.builder.ret_void()
                else:
                    self.builder.ret(self._create_zero_constant(func.ftype.return_type))
    
    def declare_function(self, func_def: ast.FunctionDef):
        """Declare a function (signature only)"""
        if func_def.name in self.functions:
            return
        
        # Check if already declared in module (e.g. by declare_runtime_functions)
        if func_def.name in self.module.globals:
            # Reuse existing declaration
            self.functions[func_def.name] = self.module.globals[func_def.name]
            return
        
        # Store function def for later (we'll need type info)
        self.function_defs = getattr(self, 'function_defs', {})
        self.function_defs[func_def.name] = func_def
        
        # Get parameter types - need proper type resolution
        param_types = []
        for param in func_def.params:
            # Use actual type from annotation
            if hasattr(self, 'type_checker') and self.type_checker and param.type_annotation:
                pyrite_type = self.type_checker.resolve_type(param.type_annotation)
                param_types.append(self.type_to_llvm(pyrite_type))
            else:
                param_types.append(ir.IntType(32))
        
        # Get return type
        if func_def.return_type:
            if hasattr(self, 'type_checker') and self.type_checker:
                pyrite_type = self.type_checker.resolve_type(func_def.return_type)
                return_type = self.type_to_llvm(pyrite_type)
            else:
                return_type = ir.IntType(32)
        else:
            # Special case: main() should return int for C compatibility
            if func_def.name == "main":
                return_type = ir.IntType(32)
            else:
                return_type = ir.VoidType()
        
        # Create function type
        fnty = ir.FunctionType(return_type, param_types)
        
        # Create function
        func = ir.Function(self.module, fnty, name=func_def.name)
        self.functions[func_def.name] = func
    
    def gen_function(self, func_def: ast.FunctionDef):
        """Generate code for a function"""
        # Skip extern declarations (functions without a body)
        if func_def.is_extern and (func_def.body is None or not func_def.body.statements):
            return
        
        func = self.functions[func_def.name]
        
        # Create entry block
        block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.function = func
        self.variables = {}
        self.variable_types = {}  # Reset for this function
        self.defer_stack = []  # Reset defer stack for this function
        self.defer_scope_stack = []  # Reset scope tracking
        self.break_targets = []  # Reset break targets for this function
        self.continue_targets = []  # Reset continue targets for this function
        
        # Map parameters with their types
        for param_def, llvm_arg in zip(func_def.params, func.args):
            llvm_arg.name = param_def.name
            self.variables[param_def.name] = llvm_arg
            
            # Store parameter type
            if param_def.type_annotation and self.type_checker:
                param_type = self.type_checker.resolve_type(param_def.type_annotation)
                self.variable_types[param_def.name] = param_type
        
        # Generate body
        self.gen_block(func_def.body)
        
        # Add implicit return if needed
        if not self.builder.block.is_terminated:
            # Execute any remaining defers before implicit return (all defers from function scope)
            self.execute_defers(scope_start=0)
            
            if isinstance(func.ftype.return_type, ir.VoidType):
                self.builder.ret_void()
            else:
                # Return zero as default
                # This is normal for main() which should return 0 on success
                self.builder.ret(self._create_zero_constant(func.ftype.return_type))
    
    def gen_block(self, block: ast.Block):
        """Generate code for a block"""
        # Enter new scope - track current defer stack size
        scope_start_size = len(self.defer_stack)
        self.defer_scope_stack.append(scope_start_size)
        
        for stmt in block.statements:
            if self.builder.block.is_terminated:
                break  # Already returned/branched (early return/break handled there)
            self.gen_statement(stmt)
        
        # Normal block exit - execute defers added in this scope
        # (Early returns/breaks execute defers themselves, so this only runs on normal exit)
        if not self.builder.block.is_terminated:
            scope_end_size = len(self.defer_stack)
            if scope_end_size > scope_start_size:
                # Execute defers added in this scope in reverse order
                defers_in_scope = self.defer_stack[scope_start_size:]
                for defer_block in reversed(defers_in_scope):
                    self.gen_block(defer_block)
                # Remove defers from this scope
                self.defer_stack = self.defer_stack[:scope_start_size]
        
        # Pop scope tracking
        if self.defer_scope_stack:
            self.defer_scope_stack.pop()
    
    def gen_statement(self, stmt: ast.Statement):
        """Generate code for a statement"""
        if isinstance(stmt, ast.VarDecl):
            self.gen_var_decl(stmt)
        elif isinstance(stmt, ast.Assignment):
            self.gen_assignment(stmt)
        elif isinstance(stmt, ast.ExpressionStmt):
            self.gen_expression(stmt.expression)
        elif isinstance(stmt, ast.ReturnStmt):
            self.gen_return(stmt)
        elif isinstance(stmt, ast.IfStmt):
            self.gen_if(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self.gen_while(stmt)
        elif isinstance(stmt, ast.ForStmt):
            self.gen_for(stmt)
        elif isinstance(stmt, ast.MatchStmt):
            self.gen_match(stmt)
        elif isinstance(stmt, ast.DeferStmt):
            self.gen_defer(stmt)
        elif isinstance(stmt, ast.WithStmt):
            self.gen_with(stmt)
        elif isinstance(stmt, ast.BreakStmt):
            self.gen_break(stmt)
        elif isinstance(stmt, ast.ContinueStmt):
            self.gen_continue(stmt)
        elif isinstance(stmt, ast.PassStmt):
            pass  # Nothing to generate
    
    def gen_var_decl(self, decl: ast.VarDecl):
        """Generate code for variable declaration"""
        # Generate initializer
        value = self.gen_expression(decl.initializer)
        
        # Bind pattern
        self.gen_pattern_binding(decl.pattern, value, decl.mutable)
        
        # Track variable types for field access and method calls (legacy support)
        # Note: This only tracks the first identifier in a tuple or the identifier itself
        # In a full implementation, we'd track types for all bindings
        if hasattr(self, 'type_checker') and self.type_checker:
            if decl.type_annotation:
                var_type = self.type_checker.resolve_type(decl.type_annotation)
            else:
                var_type = self.type_checker.check_expression(decl.initializer)
            self.variable_types = getattr(self, 'variable_types', {})
            # Use property access to avoid issues with different AST versions
            if isinstance(decl.pattern, ast.IdentifierPattern):
                self.variable_types[decl.pattern.name] = var_type
            elif isinstance(decl.pattern, ast.TuplePattern):
                # For tuples, we'd ideally track types for each element
                # For now, just track the first one for legacy compatibility if it exists
                if decl.pattern.elements and isinstance(decl.pattern.elements[0], ast.IdentifierPattern):
                    if isinstance(var_type, TupleType) and var_type.elements:
                        self.variable_types[decl.pattern.elements[0].name] = var_type.elements[0]

    def gen_pattern_binding(self, pattern: ast.Pattern, value: ir.Value, mutable: bool = False):
        """Generate code for binding a value to a pattern"""
        if isinstance(pattern, ast.IdentifierPattern):
            if mutable:
                # For mutable variables, use alloca
                alloca = self.builder.alloca(value.type, name=pattern.name)
                self.builder.store(value, alloca)
                self.variables[pattern.name] = alloca
            else:
                # For immutable variables, use SSA register
                self.variables[pattern.name] = value
        elif isinstance(pattern, ast.TuplePattern):
            for i, sub_pat in enumerate(pattern.elements):
                elem_val = self.builder.extract_value(value, i)
                self.gen_pattern_binding(sub_pat, elem_val, mutable)
        elif isinstance(pattern, ast.WildcardPattern):
            pass
        elif isinstance(pattern, ast.OrPattern):
            # Or patterns in let are not fully supported yet, but for now just bind to the first one
            if pattern.patterns:
                self.gen_pattern_binding(pattern.patterns[0], value, mutable)
        elif isinstance(pattern, ast.EnumPattern):
            # Enum patterns in let are not supported yet (they should be refutable)
            pass
    
    def gen_assignment(self, assign: ast.Assignment):
        """Generate code for assignment"""
        value = self.gen_expression(assign.value)
        
        if isinstance(assign.target, ast.Identifier):
            # Normal variable assignment
            target_name = assign.target.name
            if target_name in self.variables:
                target_val = self.variables[target_name]
                if isinstance(target_val.type, ir.PointerType):
                    # It's an alloca, use store
                    self.builder.store(value, target_val)
                    return
            # Otherwise, update the binding (SSA style)
            self.variables[target_name] = value
        elif isinstance(assign.target, ast.FieldAccess):
            # Field assignment: obj.field = value
            self.gen_field_assignment(assign.target, value)
        elif isinstance(assign.target, ast.IndexAccess):
            # Index assignment: obj[index] = value
            self.gen_index_assignment(assign.target, value)
        else:
            raise CodeGenError(f"Assignment target not supported: {type(assign.target)}", assign.span)

    def gen_field_assignment(self, access: ast.FieldAccess, value: ir.Value):
        """Generate code for assigning to a struct field"""
        # 1. Get the base object
        obj = self.gen_expression(access.object)
        
        # 2. Get field index
        field_index = -1
        
        # Check if it's a known variable with type info
        obj_type_pyrite = None
        if isinstance(access.object, ast.Identifier) and hasattr(self, 'variable_types') and access.object.name in self.variable_types:
            obj_type_pyrite = self.variable_types[access.object.name]
        
        # If we couldn't find it directly, try to get it from the expression result if possible
        # (For nested field access, we'd need to track types through expressions better)
        
        if obj_type_pyrite:
            # If it's a reference, unwrap it to get the struct type
            if isinstance(obj_type_pyrite, ReferenceType):
                obj_type_pyrite = obj_type_pyrite.inner
            
            if isinstance(obj_type_pyrite, StructType):
                field_names = sorted(obj_type_pyrite.fields.keys()) if getattr(self, 'deterministic', False) else list(obj_type_pyrite.fields.keys())
                if access.field in field_names:
                    field_index = field_names.index(access.field)
        
        if field_index == -1:
            # Try to infer from LLVM type if it's a literal struct or pointer to one
            llvm_type = obj.type
            if isinstance(llvm_type, ir.PointerType):
                llvm_type = llvm_type.pointee
            
            if isinstance(llvm_type, ir.LiteralStructType):
                # We still need the field names to find the index.
                # If we don't have pyrite type info, we're stuck for now.
                # In a full implementation, we'd have a mapping from struct name to field names.
                pass

        if field_index == -1:
            raise CodeGenError(f"Could not determine field index for '{access.field}' on type {obj.type}", access.span)
            
        # 3. Handle assignment based on whether obj is a value or a pointer
        if isinstance(obj.type, ir.PointerType):
            # Object is a pointer (e.g. &mut struct)
            # Use GEP to get field pointer and store
            zero = ir.Constant(ir.IntType(32), 0)
            idx = ir.Constant(ir.IntType(32), field_index)
            field_ptr = self.builder.gep(obj, [zero, idx], inbounds=True)
            self.builder.store(value, field_ptr)
        elif isinstance(obj.type, ir.LiteralStructType):
            # Object is a value (SSA register)
            # Create new struct value with updated field
            new_obj = self.builder.insert_value(obj, value, field_index)
            
            # Assign the new struct value back to the target
            if isinstance(access.object, ast.Identifier):
                self.variables[access.object.name] = new_obj
            else:
                # Recursive assignment for nested fields/indices
                if isinstance(access.object, (ast.FieldAccess, ast.IndexAccess)):
                    self.gen_assignment(ast.Assignment(target=access.object, value=new_obj, span=access.span))
                else:
                    raise CodeGenError("Complex field assignment not yet supported", access.span)
        else:
            raise CodeGenError(f"Field assignment only supported for structs or struct pointers, found {obj.type}", access.span)

    def gen_index_assignment(self, access: ast.IndexAccess, value: ir.Value):
        """Generate code for assigning to an array/list index"""
        obj = self.gen_expression(access.object)
        index = self.gen_expression(access.index)
        
        # Normalize index to i64 for consistency
        if index.type.width < 64:
            index = self.builder.sext(index, ir.IntType(64))
        elif index.type.width > 64:
            index = self.builder.trunc(index, ir.IntType(64))

        # 1. Handle pointer to array (e.g. &mut [int; 3])
        if isinstance(obj.type, ir.PointerType) and isinstance(obj.type.pointee, ir.ArrayType):
            zero = ir.Constant(ir.IntType(32), 0)
            # GEP requires i32 indices for the array level
            idx_i32 = self.builder.trunc(index, ir.IntType(32))
            elem_ptr = self.builder.gep(obj, [zero, idx_i32], inbounds=True)
            self.builder.store(value, elem_ptr)
            return

        # 2. Handle List[T] which is { T*, i64, i64 }
        if isinstance(obj.type, ir.LiteralStructType) and len(obj.type.elements) == 3:
            # Assume it's a List { T*, length, capacity }
            ptr = self.builder.extract_value(obj, 0)
            elem_ptr = self.builder.gep(ptr, [index], inbounds=True)
            self.builder.store(value, elem_ptr)
            return

        # 3. Handle Slice [T] which is { T*, i64 }
        if isinstance(obj.type, ir.LiteralStructType) and len(obj.type.elements) == 2:
            # Assume it's a Slice { T*, length }
            ptr = self.builder.extract_value(obj, 0)
            elem_ptr = self.builder.gep(ptr, [index], inbounds=True)
            self.builder.store(value, elem_ptr)
            return

        # 4. Handle Array value (SSA register)
        if isinstance(obj.type, ir.ArrayType):
            # For array values, we use a temporary alloca + GEP + store
            alloca = self.builder.alloca(obj.type)
            self.builder.store(obj, alloca)
            
            zero = ir.Constant(ir.IntType(32), 0)
            idx_i32 = self.builder.trunc(index, ir.IntType(32))
            ptr = self.builder.gep(alloca, [zero, idx_i32], inbounds=True)
            self.builder.store(value, ptr)
            
            new_obj = self.builder.load(alloca)
            
            if isinstance(access.object, ast.Identifier):
                self.variables[access.object.name] = new_obj
            else:
                # Recursive assignment for nested access
                if isinstance(access.object, (ast.FieldAccess, ast.IndexAccess)):
                    self.gen_assignment(ast.Assignment(target=access.object, value=new_obj, span=access.span))
                else:
                    raise CodeGenError("Complex index assignment not yet supported", access.span)
        else:
            raise CodeGenError(f"Index assignment only supported for arrays and lists, found {obj.type}", access.span)
    
    def gen_return(self, ret: ast.ReturnStmt):
        """Generate code for return statement"""
        # Execute all deferred blocks in reverse order before returning
        # This executes all defers from function scope (scope_start=0 means all defers)
        # (defers are stored in LIFO order, so reversed iteration gives correct execution order)
        self.execute_defers(scope_start=0)
        
        if ret.value:
            value = self.gen_expression(ret.value)
            self.builder.ret(value)
        else:
            self.builder.ret_void()
    
    def gen_break(self, break_stmt: ast.BreakStmt):
        """Generate code for break statement"""
        if not self.break_targets:
            raise CodeGenError("break statement outside of loop", break_stmt.span)
        
        # Execute defers in current scope before breaking
        # Get the current scope's defers
        if self.defer_scope_stack:
            scope_start = self.defer_scope_stack[-1]
            scope_end = len(self.defer_stack)
            if scope_end > scope_start:
                # Execute defers added in this scope in reverse order
                defers_in_scope = self.defer_stack[scope_start:]
                for defer_block in reversed(defers_in_scope):
                    self.gen_block(defer_block)
        
        # Jump to break target (end of loop)
        break_target = self.break_targets[-1]
        self.builder.branch(break_target)
    
    def gen_continue(self, continue_stmt: ast.ContinueStmt):
        """Generate code for continue statement"""
        if not self.continue_targets:
            raise CodeGenError("continue statement outside of loop", continue_stmt.span)
        
        # Execute defers in current scope before continuing
        # Get the current scope's defers
        if self.defer_scope_stack:
            scope_start = self.defer_scope_stack[-1]
            scope_end = len(self.defer_stack)
            if scope_end > scope_start:
                # Execute defers added in this scope in reverse order
                defers_in_scope = self.defer_stack[scope_start:]
                for defer_block in reversed(defers_in_scope):
                    self.gen_block(defer_block)
        
        # Jump to continue target (loop condition or increment)
        continue_target = self.continue_targets[-1]
        self.builder.branch(continue_target)
    
    def gen_defer(self, defer_stmt: ast.DeferStmt):
        """Generate code for defer statement"""
        # Don't execute now - just add to the defer stack for later execution
        # Defers execute in LIFO (last in, first out) order
        self.defer_stack.append(defer_stmt.body)
    
    def execute_defers(self, scope_start: Optional[int] = None):
        """Execute deferred blocks in reverse order (LIFO)
        
        Args:
            scope_start: Index in defer_stack to start executing from.
                        If None, uses current scope from defer_scope_stack.
                        If 0, executes all defers (function scope).
        """
        if scope_start is None:
            # Use current scope
            if self.defer_scope_stack:
                scope_start = self.defer_scope_stack[-1]
            else:
                scope_start = 0
        
        # Execute defers from scope_start to end in reverse order
        scope_end = len(self.defer_stack)
        if scope_end > scope_start:
            defers_in_scope = self.defer_stack[scope_start:]
            for defer_block in reversed(defers_in_scope):
                self.gen_block(defer_block)
    
    def gen_panic_with_defers(self, message: str):
        """Generate code to panic after executing all defers
        
        This is best-effort: executes all function-level defers before calling
        pyrite_panic. Since panic terminates the process, this ensures cleanup
        code runs before program exit.
        
        Args:
            message: Panic message string
        """
        # Execute all defers from function scope (scope_start=0 means all defers)
        # This ensures cleanup happens before panic terminates the process
        self.execute_defers(scope_start=0)
        
        # Create string constant for panic message
        msg_ptr = self.create_string_constant(message)
        
        # Call pyrite_panic (which will print and exit)
        self.builder.call(self.panic, [msg_ptr])
        
        # Mark as unreachable (panic never returns)
        self.builder.unreachable()
    
    def gen_with(self, with_stmt: ast.WithStmt):
        """Generate code for with statement"""
        # With statement is syntactic sugar for:
        #   let variable = value
        #   defer: variable.close()
        #   <body>
        
        # Enter with scope - track defers for this with block
        with_scope_start = len(self.defer_stack)
        self.defer_scope_stack.append(with_scope_start)
        
        # Generate variable initialization
        value = self.gen_expression(with_stmt.value)
        self.variables[with_stmt.variable] = value
        
        # Create a defer block that calls .close() on the variable
        # For now, we'll assume the variable has a close method
        # In a full implementation, we'd verify the Closeable trait
        close_call = ast.MethodCall(
            object=ast.Identifier(name=with_stmt.variable, span=with_stmt.span),
            method="close",
            arguments=[],
            span=with_stmt.span
        )
        defer_body = ast.Block(
            statements=[ast.ExpressionStmt(expression=close_call, span=with_stmt.span)],
            span=with_stmt.span
        )
        # Add defer to with scope (will execute when with body exits)
        self.defer_stack.append(defer_body)
        
        # Generate the with body (creates its own nested scope)
        self.gen_block(with_stmt.body)
        
        # Execute defers from with scope (including the close defer)
        # This happens after the with body exits
        with_scope_end = len(self.defer_stack)
        if with_scope_end > with_scope_start:
            defers_in_with_scope = self.defer_stack[with_scope_start:]
            for defer_block in reversed(defers_in_with_scope):
                self.gen_block(defer_block)
            self.defer_stack = self.defer_stack[:with_scope_start]
        
        # Pop with scope tracking
        if self.defer_scope_stack:
            self.defer_scope_stack.pop()
    
    def gen_if(self, if_stmt: ast.IfStmt):
        """Generate code for if statement"""
        # Generate condition
        cond = self.gen_expression(if_stmt.condition)
        
        # Create blocks
        then_block = self.function.append_basic_block(name="if.then")
        else_block = self.function.append_basic_block(name="if.else")
        merge_block = self.function.append_basic_block(name="if.end")
        
        # Branch on condition
        self.builder.cbranch(cond, then_block, else_block)
        
        # Generate then block (gen_block handles defer execution automatically)
        self.builder.position_at_end(then_block)
        self.gen_block(if_stmt.then_block)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        
        # Generate else block (gen_block handles defer execution automatically)
        self.builder.position_at_end(else_block)
        if if_stmt.else_block:
            self.gen_block(if_stmt.else_block)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        
        # Continue at merge block
        self.builder.position_at_end(merge_block)
    
    def gen_while(self, while_stmt: ast.WhileStmt):
        """Generate code for while loop"""
        # Create blocks
        cond_block = self.function.append_basic_block(name="while.cond")
        body_block = self.function.append_basic_block(name="while.body")
        end_block = self.function.append_basic_block(name="while.end")
        
        # Track break/continue targets for defer execution
        self.break_targets.append(end_block)
        self.continue_targets.append(cond_block)
        
        # Branch to condition
        self.builder.branch(cond_block)
        
        # Generate condition block
        self.builder.position_at_end(cond_block)
        cond = self.gen_expression(while_stmt.condition)
        self.builder.cbranch(cond, body_block, end_block)
        
        # Generate body (gen_block handles defer execution per iteration)
        self.builder.position_at_end(body_block)
        self.gen_block(while_stmt.body)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        # Continue at end block
        self.builder.position_at_end(end_block)
        
        # Pop break/continue targets
        if self.break_targets:
            self.break_targets.pop()
        if self.continue_targets:
            self.continue_targets.pop()
    
    def gen_for(self, for_stmt: ast.ForStmt):
        """Generate code for for loop (simplified)"""
        # For MVP, handle simple range loops: for i in 0..10
        # TODO: Implement proper iterator protocol
        
        if isinstance(for_stmt.iterable, ast.BinOp) and for_stmt.iterable.op == '..':
            # Range loop
            start = self.gen_expression(for_stmt.iterable.left)
            end = self.gen_expression(for_stmt.iterable.right)
            
            # Allocate loop variable
            loop_var = self.builder.alloca(ir.IntType(32), name=for_stmt.variable)
            self.builder.store(start, loop_var)
            
            # Create blocks
            cond_block = self.function.append_basic_block(name="for.cond")
            body_block = self.function.append_basic_block(name="for.body")
            inc_block = self.function.append_basic_block(name="for.inc")
            end_block = self.function.append_basic_block(name="for.end")
            
            # Track break/continue targets for defer execution
            self.break_targets.append(end_block)
            self.continue_targets.append(inc_block)  # continue goes to increment
            
            # Branch to condition
            self.builder.branch(cond_block)
            
            # Condition: i < end
            self.builder.position_at_end(cond_block)
            i_val = self.builder.load(loop_var)
            cond = self.builder.icmp_signed('<', i_val, end)
            self.builder.cbranch(cond, body_block, end_block)
            
            # Body
            self.builder.position_at_end(body_block)
            self.variables[for_stmt.variable] = i_val
            self.gen_block(for_stmt.body)
            if not self.builder.block.is_terminated:
                self.builder.branch(inc_block)
            
            # Increment
            self.builder.position_at_end(inc_block)
            i_val = self.builder.load(loop_var)
            inc = self.builder.add(i_val, ir.Constant(ir.IntType(32), 1))
            self.builder.store(inc, loop_var)
            self.builder.branch(cond_block)
            
            # End
            self.builder.position_at_end(end_block)
            
            # Pop break/continue targets
            if self.break_targets:
                self.break_targets.pop()
            if self.continue_targets:
                self.continue_targets.pop()
    
    def gen_match(self, match_stmt: ast.MatchStmt):
        """Generate code for match statement"""
        # Evaluate scrutinee
        scrutinee = self.gen_expression(match_stmt.scrutinee)
        
        # Create final merge block
        merge_block = self.function.append_basic_block(name="match.end")
        
        # current_test_block will be updated in each iteration
        current_test_block = self.function.append_basic_block(name="match.test0")
        self.builder.branch(current_test_block)
        
        for i, arm in enumerate(match_stmt.arms):
            self.builder.position_at_end(current_test_block)
            
            # Create arm block
            arm_block = self.function.append_basic_block(name=f"match.arm{i}")
            
            # Create next test block (or jump to merge block if this is the last arm)
            if i + 1 < len(match_stmt.arms):
                next_test_block = self.function.append_basic_block(name=f"match.test{i+1}")
            else:
                next_test_block = merge_block
            
            # Generate matching logic
            if isinstance(arm.pattern, ast.LiteralPattern):
                literal_val = self.gen_expression(arm.pattern.literal)
                cond = self.builder.icmp_signed('==', scrutinee, literal_val)
                self.builder.cbranch(cond, arm_block, next_test_block)
            
            elif isinstance(arm.pattern, ast.EnumPattern):
                # Check if enum is a struct or just an i32 tag
                if isinstance(scrutinee.type, ir.IntType):
                    # Simple enum without fields - scrutinee is the tag
                    tag = scrutinee
                else:
                    # Enum with fields - extract tag from field 0
                    tag = self.builder.extract_value(scrutinee, 0)
                
                # Get expected tag value
                expected_tag_value = -1
                if self.type_checker:
                    scrutinee_type = self.type_checker.check_expression(match_stmt.scrutinee)
                    if isinstance(scrutinee_type, GenericType):
                        scrutinee_type = scrutinee_type.base_type
                    
                    if isinstance(scrutinee_type, EnumType):
                        if arm.pattern.variant_name in scrutinee_type.variants:
                            expected_tag_value = list(scrutinee_type.variants.keys()).index(arm.pattern.variant_name)
                
                if expected_tag_value == -1:
                    raise CodeGenError(f"Could not determine tag for variant {arm.pattern.variant_name}", arm.pattern.span)
                
                expected_tag = ir.Constant(ir.IntType(32), expected_tag_value)
                cond = self.builder.icmp_signed('==', tag, expected_tag)
                self.builder.cbranch(cond, arm_block, next_test_block)
                
            elif isinstance(arm.pattern, ast.TuplePattern):
                # Always matches
                self.builder.branch(arm_block)
                # Any following arms are unreachable (type checker should have warned)
                next_test_block = merge_block
                
            elif isinstance(arm.pattern, ast.WildcardPattern) or isinstance(arm.pattern, ast.IdentifierPattern):
                # Always matches
                self.builder.branch(arm_block)
                # Any following arms are unreachable
                next_test_block = merge_block
            
            else:
                # Fallback matching logic (should not happen if all handled)
                self.builder.branch(arm_block)

            # Generate arm body
            self.builder.position_at_end(arm_block)
            
            # Bind pattern variables
            if isinstance(arm.pattern, ast.IdentifierPattern):
                self.variables[arm.pattern.name] = scrutinee
            elif isinstance(arm.pattern, ast.EnumPattern) and arm.pattern.fields:
                for j, field_pat in enumerate(arm.pattern.fields):
                    field_val_raw = self.builder.extract_value(scrutinee, j + 1)
                    # Cast payload to correct type if possible
                    self.gen_pattern_binding(field_pat, field_val_raw)
            elif isinstance(arm.pattern, ast.TuplePattern):
                for j, elem_pat in enumerate(arm.pattern.elements):
                    elem_val = self.builder.extract_value(scrutinee, j)
                    self.gen_pattern_binding(elem_pat, elem_val)
            
            # Match guards
            if arm.guard:
                # TODO: Implement guards (needs another level of branching)
                pass
                
            self.gen_block(arm.body)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)
            
            # Move to next test block
            current_test_block = next_test_block
            if current_test_block == merge_block:
                break
        
        # Continue at merge block
        self.builder.position_at_end(merge_block)
    
    def gen_expression(self, expr: ast.Expression) -> ir.Value:
        """Generate code for an expression"""
        if isinstance(expr, ast.IntLiteral):
            return ir.Constant(ir.IntType(32), expr.value)
        
        elif isinstance(expr, ast.FloatLiteral):
            return ir.Constant(ir.DoubleType(), expr.value)
        
        elif isinstance(expr, ast.BoolLiteral):
            return ir.Constant(ir.IntType(1), 1 if expr.value else 0)
        
        elif isinstance(expr, ast.StringLiteral):
            # Create global string constant
            string_const = self.create_string_constant(expr.value)
            # Store type information for method calls
            if hasattr(self, 'type_checker') and self.type_checker:
                # String literals are String type
                from ..types import StringType
                # Store in a temporary variable name for type tracking
                # (This is a workaround - ideally we'd track types per expression)
            return string_const
        
        elif isinstance(expr, ast.Identifier):
            if expr.name in self.variables:
                val = self.variables[expr.name]
                # If it's a pointer (alloca), load it (unless it's a reference type)
                if isinstance(val.type, ir.PointerType):
                    # Check Pyrite type to see if it's a reference
                    py_type = self.variable_types.get(expr.name)
                    if not isinstance(py_type, ReferenceType):
                        return self.builder.load(val)
                return val
            else:
                raise CodeGenError(f"Undefined variable: {expr.name}", expr.span)
        
        elif isinstance(expr, ast.BinOp):
            return self.gen_binop(expr)
        
        elif isinstance(expr, ast.UnaryOp):
            return self.gen_unaryop(expr)
        
        elif isinstance(expr, ast.FunctionCall):
            return self.gen_function_call(expr)
        
        elif isinstance(expr, ast.MethodCall):
            return self.gen_method_call(expr)
        
        elif isinstance(expr, ast.ParameterClosure):
            return self.gen_parameter_closure(expr)
        
        elif isinstance(expr, ast.RuntimeClosure):
            return self.gen_runtime_closure(expr)
        
        elif isinstance(expr, ast.FieldAccess):
            return self.gen_field_access(expr)
        
        elif isinstance(expr, ast.StructLiteral):
            return self.gen_struct_literal(expr)
        
        elif isinstance(expr, ast.ListLiteral):
            return self.gen_list_literal(expr)
        
        elif isinstance(expr, ast.TupleLiteral):
            return self.gen_tuple_literal(expr)
        
        elif isinstance(expr, ast.IndexAccess):
            return self.gen_index_access(expr)
        
        elif isinstance(expr, ast.TryExpr):
            return self.gen_try_expr(expr)
        
        elif isinstance(expr, ast.TernaryExpr):
            return self.gen_ternary_expr(expr)
        
        else:
            raise CodeGenError(f"Expression type not implemented: {type(expr)}", expr.span)
    
    def gen_ternary_expr(self, ternary: ast.TernaryExpr) -> ir.Value:
        """Generate code for ternary expression: true_expr if condition else false_expr"""
        # Generate condition
        cond = self.gen_expression(ternary.condition)
        
        # Generate true and false expressions
        true_val = self.gen_expression(ternary.true_expr)
        false_val = self.gen_expression(ternary.false_expr)
        
        # Ensure both branches have the same type
        if true_val.type != false_val.type:
            # Type checker should have ensured this, but handle mismatch
            raise CodeGenError(
                f"Ternary branches have different types: {true_val.type} vs {false_val.type}",
                ternary.span
            )
        
        # Create basic blocks
        true_block = self.function.append_basic_block(name="ternary.true")
        false_block = self.function.append_basic_block(name="ternary.false")
        merge_block = self.function.append_basic_block(name="ternary.merge")
        
        # Branch on condition
        # Condition should be i1 (bool)
        if not isinstance(cond.type, ir.IntType) or cond.type.width != 1:
            # Convert to bool if needed
            zero = ir.Constant(cond.type, 0)
            cond = self.builder.icmp_signed('!=', cond, zero)
        
        self.builder.cbranch(cond, true_block, false_block)
        
        # Generate true branch
        self.builder.position_at_end(true_block)
        self.builder.branch(merge_block)
        
        # Generate false branch
        self.builder.position_at_end(false_block)
        self.builder.branch(merge_block)
        
        # Merge block
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(true_val.type, name="ternary.result")
        phi.add_incoming(true_val, true_block)
        phi.add_incoming(false_val, false_block)
        
        return phi
    
    def gen_try_expr(self, try_expr: ast.TryExpr) -> ir.Value:
        """Generate code for try expression (error propagation)
        
        try expr requires expr to be Result[T, E] and returns T.
        Desugars to early return on Err.
        """
        # 1. Generate the Result[T, E] expression
        result_val = self.gen_expression(try_expr.expression)
        
        # 2. Extract the tag (Result is an enum, layout is { i32 tag, ...fields })
        tag = self.builder.extract_value(result_val, 0)
        
        # 3. Check if it's Err (tag != 0)
        # Assuming tag 0 is Ok and tag 1 is Err
        zero = ir.Constant(ir.IntType(32), 0)
        is_err = self.builder.icmp_signed('!=', tag, zero)
        
        # 4. Create blocks for branching
        ok_block = self.function.append_basic_block(name="try.ok")
        err_block = self.function.append_basic_block(name="try.err")
        
        self.builder.cbranch(is_err, err_block, ok_block)
        
        # 5. Handle Err block: execute defers and return the error
        self.builder.position_at_end(err_block)
        self.execute_defers(scope_start=0)
        # Return the original result value (which is already an Err)
        # We might need to convert it to the function's return type if they differ,
        # but Result propagation usually requires matching error types.
        self.builder.ret(result_val)
        
        # 6. Handle Ok block: extract and return payload
        self.builder.position_at_end(ok_block)
        # Payload is in field 1 (first field after tag)
        payload_raw = self.builder.extract_value(result_val, 1)
        
        # The payload is stored as i64 in the enum struct, we need to cast it back
        # to the actual type T.
        if self.type_checker:
            res_type = self.type_checker.check_expression(try_expr.expression)
            if isinstance(res_type, GenericType) and res_type.name == "Result":
                t_type = res_type.type_args[0]
                target_llvm_type = self.type_to_llvm(t_type)
                
                # Use bitcast or inttoptr/ptrtoint if needed
                if isinstance(target_llvm_type, ir.PointerType):
                    return self.builder.inttoptr(payload_raw, target_llvm_type)
                elif isinstance(target_llvm_type, ir.IntType):
                    if target_llvm_type.width < 64:
                        return self.builder.trunc(payload_raw, target_llvm_type)
                    elif target_llvm_type.width > 64:
                        return self.builder.zext(payload_raw, target_llvm_type)
                    return payload_raw
                elif isinstance(target_llvm_type, (ir.FloatType, ir.DoubleType)):
                    return self.builder.bitcast(payload_raw, target_llvm_type)
                else:
                    # For complex types (structs), they might not fit in i64.
                    # Pyrite's current enum implementation pads with i64 fields.
                    # This is a simplification.
                    return self.builder.bitcast(payload_raw, target_llvm_type)
        
        return payload_raw
    
    def gen_list_literal(self, literal: ast.ListLiteral) -> ir.Value:
        """Generate code for list literal
        List[T] is { T*, i64, i64 } (pointer, length, capacity)
        """
        # Get element type from first element
        if not literal.elements:
            # Empty list - create List struct with null pointer, 0 length, 0 capacity
            # Need to determine element type from context - for MVP, use i64 as placeholder
            # TODO: Get element type from type checker
            elem_type = ir.IntType(64)
        else:
            first_elem = self.gen_expression(literal.elements[0])
            elem_type = first_elem.type
        
        # List type: { T*, i64, i64 }
        list_struct_ty = ir.LiteralStructType([
            elem_type.as_pointer(),
            ir.IntType(64),  # length
            ir.IntType(64)   # capacity
        ])
        
        if not literal.elements:
            # Empty list
            null_ptr = ir.Constant(elem_type.as_pointer(), None)
            zero = ir.Constant(ir.IntType(64), 0)
            list_val = ir.Constant(list_struct_ty, ir.Undefined)
            list_val = self.builder.insert_value(list_val, null_ptr, 0)
            list_val = self.builder.insert_value(list_val, zero, 1)
            list_val = self.builder.insert_value(list_val, zero, 2)
            
            # Track allocation for cost analysis (empty list still allocates struct)
            if self.track_costs and self.function:
                func_name = self.function.name if self.function else "unknown"
                line = literal.span.start_line if literal.span else 0
                elem_size = self._get_type_size(elem_type)
                estimated_bytes = 24  # List struct size (3 * i64)
                self.allocation_sites.append({
                    "function": func_name,
                    "line": line,
                    "type": "List",
                    "bytes": estimated_bytes,
                    "description": f"List (empty)"
                })
            
            # Emit cost warning if enabled (even empty lists allocate)
            if self.warn_costs and literal.span:
                self.cost_warnings.append({
                    "span": literal.span,
                    "message": "Heap allocation: List (empty)",
                    "help_hint": "Empty lists still allocate memory. Consider using Option[List] if the list may not be needed."
                })
            
            return list_val
        
        # For non-empty lists, allocate memory and store elements
        # Allocate array for elements
        array_type = ir.ArrayType(elem_type, len(literal.elements))
        alloca = self.builder.alloca(array_type, name="list_data")
        
        # Store each element
        for i, elem_expr in enumerate(literal.elements):
            elem_val = self.gen_expression(elem_expr)
            # Get pointer to element i
            elem_ptr = self.builder.gep(alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)])
            self.builder.store(elem_val, elem_ptr)
        
        # Get pointer to first element
        first_elem_ptr = self.builder.gep(alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
        data_ptr = self.builder.bitcast(first_elem_ptr, elem_type.as_pointer())
        
        # Create List struct
        length = ir.Constant(ir.IntType(64), len(literal.elements))
        capacity = ir.Constant(ir.IntType(64), len(literal.elements))
        list_val = ir.Constant(list_struct_ty, ir.Undefined)
        list_val = self.builder.insert_value(list_val, data_ptr, 0)
        list_val = self.builder.insert_value(list_val, length, 1)
        list_val = self.builder.insert_value(list_val, capacity, 2)
        
        # Track allocation for cost analysis (list literal allocates array)
        if self.track_costs and self.function:
            func_name = self.function.name if self.function else "unknown"
            line = literal.span.start_line if literal.span else 0
            elem_size = self._get_type_size(elem_type)
            estimated_bytes = 24 + (elem_size * len(literal.elements))  # List struct + elements
            self.allocation_sites.append({
                "function": func_name,
                "line": line,
                "type": "List",
                "bytes": estimated_bytes,
                "description": f"List with {len(literal.elements)} element(s)"
            })
        
        # Emit cost warning if enabled (for non-empty lists)
        if self.warn_costs and literal.span and literal.elements:
            self.cost_warnings.append({
                "span": literal.span,
                "message": f"Heap allocation: List with {len(literal.elements)} element(s)",
                "help_hint": "List literals allocate memory. Consider using arrays for fixed-size data."
            })
        
        return list_val

    def gen_tuple_literal(self, expr: ast.TupleLiteral) -> ir.Value:
        """Generate code for tuple literal: (1, "a")"""
        elements = [self.gen_expression(elem) for elem in expr.elements]
        # Create a struct value for the tuple
        pyrite_type = self.type_checker.check_expression(expr)
        llvm_type = self.type_to_llvm(pyrite_type)
        
        tuple_val = self._create_zero_constant(llvm_type)
        for i, val in enumerate(elements):
            tuple_val = self.builder.insert_value(tuple_val, val, i)
        return tuple_val

    def gen_index_access(self, access: ast.IndexAccess) -> ir.Value:
        """Generate code for array/list indexing"""
        obj = self.gen_expression(access.object)
        index = self.gen_expression(access.index)
        
        # Handle List[T] which is { T*, i64, i64 }
        if isinstance(obj.type, ir.LiteralStructType) and len(obj.type.elements) == 3:
            # Assume it's a List { T*, length, capacity }
            # 1. Extract the pointer to data
            ptr = self.builder.extract_value(obj, 0)
            
            # 2. Index into the pointer and load
            elem_ptr = self.builder.gep(ptr, [index], inbounds=True)
            return self.builder.load(elem_ptr)

        # For arrays, use GEP with bounds checking
        if isinstance(obj.type, ir.ArrayType):
            # Add bounds check in debug mode
            array_size = ir.Constant(ir.IntType(32), obj.type.count)
            
            # Check: index >= 0 && index < size
            zero = ir.Constant(ir.IntType(32), 0)
            in_bounds = self.builder.icmp_signed('>=', index, zero)
            in_bounds2 = self.builder.icmp_signed('<', index, array_size)
            valid = self.builder.and_(in_bounds, in_bounds2)
            
            # Branch to panic on out-of-bounds (with defer execution)
            ok_block = self.function.append_basic_block(name="bounds.ok")
            panic_block = self.function.append_basic_block(name="bounds.panic")
            
            self.builder.cbranch(valid, ok_block, panic_block)
            
            # Generate panic block (executes defers before panicking)
            self.builder.position_at_end(panic_block)
            self.gen_panic_with_defers("index out of bounds")
            
            # Continue with normal execution in ok block
            self.builder.position_at_end(ok_block)
            
            # Get pointer to element
            elem_ptr = self.builder.gep(obj, [zero, index], inbounds=True)
            return self.builder.load(elem_ptr)
        
        # For other types, return placeholder
        return obj
    
    def gen_binop(self, binop: ast.BinOp) -> ir.Value:
        """Generate code for binary operation"""
        left = self.gen_expression(binop.left)
        right = self.gen_expression(binop.right)
        
        # Arithmetic operations
        if binop.op == '+':
            if isinstance(left.type, ir.IntType):
                return self.builder.add(left, right)
            else:
                return self.builder.fadd(left, right)
        
        elif binop.op == '-':
            if isinstance(left.type, ir.IntType):
                return self.builder.sub(left, right)
            else:
                return self.builder.fsub(left, right)
        
        elif binop.op == '*':
            if isinstance(left.type, ir.IntType):
                return self.builder.mul(left, right)
            else:
                return self.builder.fmul(left, right)
        
        elif binop.op == '/':
            if isinstance(left.type, ir.IntType):
                return self.builder.sdiv(left, right)  # Signed division
            else:
                return self.builder.fdiv(left, right)
        
        elif binop.op == '%':
            if isinstance(left.type, ir.IntType):
                return self.builder.srem(left, right)
            else:
                return self.builder.frem(left, right)
        
        # Comparison operations
        elif binop.op == '==':
            if isinstance(left.type, ir.IntType):
                return self.builder.icmp_signed('==', left, right)
            elif isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('==', left, right)
            elif isinstance(left.type, ir.LiteralStructType):
                # For struct types (e.g., String), compare field by field
                # For String { i8*, i64 }, compare pointer and length
                if len(left.type.elements) == 2:
                    # Assume String-like struct: compare both fields
                    left_ptr = self.builder.extract_value(left, 0)
                    right_ptr = self.builder.extract_value(right, 0)
                    left_len = self.builder.extract_value(left, 1)
                    right_len = self.builder.extract_value(right, 1)
                    ptr_eq = self.builder.icmp_unsigned('==', left_ptr, right_ptr)
                    len_eq = self.builder.icmp_signed('==', left_len, right_len)
                    return self.builder.and_(ptr_eq, len_eq)
                else:
                    raise CodeGenError(f"Comparison of struct type with {len(left.type.elements)} fields not implemented", binop.span)
            else:
                return self.builder.fcmp_ordered('==', left, right)
        
        elif binop.op == '!=':
            if isinstance(left.type, ir.IntType):
                return self.builder.icmp_signed('!=', left, right)
            elif isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('!=', left, right)
            elif isinstance(left.type, ir.LiteralStructType):
                # For struct types, use == and negate
                if len(left.type.elements) == 2:
                    # Assume String-like struct: compare both fields
                    left_ptr = self.builder.extract_value(left, 0)
                    right_ptr = self.builder.extract_value(right, 0)
                    left_len = self.builder.extract_value(left, 1)
                    right_len = self.builder.extract_value(right, 1)
                    ptr_eq = self.builder.icmp_unsigned('==', left_ptr, right_ptr)
                    len_eq = self.builder.icmp_signed('==', left_len, right_len)
                    eq_result = self.builder.and_(ptr_eq, len_eq)
                    return self.builder.not_(eq_result)
                else:
                    raise CodeGenError(f"Comparison of struct type with {len(left.type.elements)} fields not implemented", binop.span)
            else:
                return self.builder.fcmp_ordered('!=', left, right)
        
        elif binop.op == '<':
            if isinstance(left.type, ir.IntType):
                return self.builder.icmp_signed('<', left, right)
            elif isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('<', left, right)
            else:
                raise CodeGenError(f"Comparison operator '<' not supported for type {left.type}", binop.span)
        
        elif binop.op == '<=':
            if isinstance(left.type, ir.IntType):
                return self.builder.icmp_signed('<=', left, right)
            elif isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('<=', left, right)
            else:
                raise CodeGenError(f"Comparison operator '<=' not supported for type {left.type}", binop.span)
        
        elif binop.op == '>':
            if isinstance(left.type, ir.IntType):
                return self.builder.icmp_signed('>', left, right)
            elif isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('>', left, right)
            else:
                raise CodeGenError(f"Comparison operator '>' not supported for type {left.type}", binop.span)
        
        elif binop.op == '>=':
            if isinstance(left.type, ir.IntType):
                return self.builder.icmp_signed('>=', left, right)
            elif isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
                return self.builder.fcmp_ordered('>=', left, right)
            else:
                raise CodeGenError(f"Comparison operator '>=' not supported for type {left.type}", binop.span)
        
        # Logical operations
        elif binop.op == 'and':
            return self.builder.and_(left, right)
        
        elif binop.op == 'or':
            return self.builder.or_(left, right)
        
        else:
            raise CodeGenError(f"Binary operator not implemented: {binop.op}", binop.span)
    
    def gen_unaryop(self, unaryop: ast.UnaryOp) -> ir.Value:
        """Generate code for unary operation"""
        if unaryop.op == '-':
            operand = self.gen_expression(unaryop.operand)
            if isinstance(operand.type, ir.IntType):
                return self.builder.neg(operand)
            else:
                return self.builder.fneg(operand)
        
        elif unaryop.op == 'not':
            operand = self.gen_expression(unaryop.operand)
            return self.builder.not_(operand)
        
        elif unaryop.op == '&' or unaryop.op == '&mut':
            # Create reference (address-of)
            if isinstance(unaryop.operand, ast.Identifier):
                var_name = unaryop.operand.name
                if var_name in self.variables:
                    var_val = self.variables[var_name]
                    # If it's already a pointer (either an alloca or a reference), return it
                    if isinstance(var_val.type, ir.PointerType):
                        return var_val
                    # Otherwise, need to create a temporary pointer (copying the value)
                    # Note: This only happens for immutable let bindings.
                    # In a full implementation, we'd maybe error if trying to take &mut of an immutable.
                    alloca = self.builder.alloca(var_val.type, name=f"{var_name}_ref")
                    self.builder.store(var_val, alloca)
                    return alloca
                else:
                    raise CodeGenError(f"Unknown variable: {var_name}", unaryop.span)
            else:
                raise CodeGenError("Can only take reference of variables for MVP", unaryop.span)
        
        elif unaryop.op == '*':
            # Dereference
            operand = self.gen_expression(unaryop.operand)
            if isinstance(operand.type, ir.PointerType):
                return self.builder.load(operand)
            return operand
        
        else:
            raise CodeGenError(f"Unary operator not implemented: {unaryop.op}", unaryop.span)
    
    def gen_enum_constructor(self, enum_type: EnumType, variant_name: str, arguments: List[ast.Expression]) -> ir.Value:
        """Generate code for an enum variant constructor call"""
        # 1. Get LLVM type for the enum
        llvm_type = self.type_to_llvm(enum_type)
        
        # 2. Get the tag for this variant
        tag_value = list(enum_type.variants.keys()).index(variant_name)
        tag = ir.Constant(ir.IntType(32), tag_value)
        
        # 3. Create initial enum struct with tag
        enum_val = self._create_zero_constant(llvm_type)
        enum_val = self.builder.insert_value(enum_val, tag, 0)
        
        # 4. Add payloads (if any)
        if arguments:
            for i, arg_expr in enumerate(arguments):
                arg_val = self.gen_expression(arg_expr)
                # In Pyrite's current enum layout, payloads start at field index 1
                # They are stored as i64, so we might need to cast
                payload_field_idx = i + 1
                if payload_field_idx < len(llvm_type.elements):
                    # Cast payload to i64 if needed
                    payload_val = arg_val
                    target_type = llvm_type.elements[payload_field_idx]
                    
                    if payload_val.type != target_type:
                        if isinstance(payload_val.type, ir.PointerType):
                            payload_val = self.builder.ptrtoint(payload_val, target_type)
                        elif isinstance(payload_val.type, ir.IntType):
                            if payload_val.type.width < target_type.width:
                                payload_val = self.builder.zext(payload_val, target_type)
                            else:
                                payload_val = self.builder.trunc(payload_val, target_type)
                        elif isinstance(payload_val.type, (ir.FloatType, ir.DoubleType)):
                            payload_val = self.builder.bitcast(payload_val, target_type)
                    
                    enum_val = self.builder.insert_value(enum_val, payload_val, payload_field_idx)
        
        return enum_val

    def gen_call_arguments(self, func: ir.Function, arguments: List[ast.Expression], offset: int = 0) -> List[ir.Value]:
        """Generate and cast arguments for a function call"""
        args = []
        for i, arg_expr in enumerate(arguments):
            arg_val = self.gen_expression(arg_expr)
            if i + offset < len(func.args):
                llvm_param = func.args[i + offset]
                param_type = llvm_param.type
                
                # Handle type mismatch
                if arg_val.type != param_type:
                    # 1. Integer widening/truncation
                    if isinstance(arg_val.type, ir.IntType) and isinstance(param_type, ir.IntType):
                        if arg_val.type.width < param_type.width:
                            arg_val = self.builder.sext(arg_val, param_type)
                        elif arg_val.type.width > param_type.width:
                            arg_val = self.builder.trunc(arg_val, param_type)
                    
                    # 2. Pointer bitcasts (e.g., *mut T to *const T or *u8 to *T)
                    elif isinstance(arg_val.type, ir.PointerType) and isinstance(param_type, ir.PointerType):
                        arg_val = self.builder.bitcast(arg_val, param_type)
            
            args.append(arg_val)
        return args

    def gen_function_call(self, call: ast.FunctionCall) -> ir.Value:
        """Generate code for function call"""
        # Special handling for enum constructors
        if isinstance(call.function, ast.FieldAccess):
            # Check if it's a type access like Enum::Variant
            if isinstance(call.function.object, ast.Identifier):
                type_name = call.function.object.name
                if hasattr(self, 'type_checker') and self.type_checker:
                    obj_type = self.type_checker.resolver.lookup_type(type_name)
                    if isinstance(obj_type, EnumType):
                        # It's an enum constructor call
                        return self.gen_enum_constructor(obj_type, call.function.field, call.arguments)
            
            # Otherwise, it might be an instance method call or field containing a closure
            # (handled by the general logic below)
            pass

        # Special handling for builtin functions
        if isinstance(call.function, ast.Identifier):
            if call.function.name == "print":
                return self.gen_print_call(call)
            elif call.function.name == "assert":
                return self.gen_assert_call(call)
            elif call.function.name == "fail":
                return self.gen_fail_call(call)
        
        # Check if any arguments are parameter closures
        # Parameter closures should be inlined, not passed as values
        # For MVP, we'll handle simple cases where parameter closures
        # are passed directly (full integration requires type information)
        has_parameter_closure = any(
            isinstance(arg, ast.ParameterClosure) for arg in call.arguments
        )
        
        if has_parameter_closure:
            # For now, parameter closures in function calls are not fully supported
            # Full integration requires:
            # 1. Type information to identify parameter closure parameters
            # 2. AST transformation to inline closures at call sites
            # This is a placeholder for future implementation
            pass
        
        # Check if this is a closure call first (before generating function expression)
        is_closure_call = False
        closure_func_ptr = None
        closure_env_ptr = None
        func = None
        
        # Check if function is an identifier (variable or function name)
        if isinstance(call.function, ast.Identifier):
            func_name = call.function.name
            # First check if it's a regular function (highest priority)
            if func_name in self.functions:
                func = self.functions[func_name]
            # Then check if it's a variable containing a closure
            elif func_name in self.variables:
                var_value = self.variables[func_name]
                # Check if variable is a closure struct (has 2 fields: function_ptr, env_ptr)
                if isinstance(var_value.type, ir.LiteralStructType) and len(var_value.type.elements) == 2:
                    # Check if both fields are pointers (function pointer and env pointer)
                    if (isinstance(var_value.type.elements[0], ir.PointerType) and
                        isinstance(var_value.type.elements[1], ir.PointerType)):
                        # Extract function pointer from closure struct
                        # extract_value returns the value directly, which is a function pointer
                        func_ptr_ptr = self.builder.extract_value(var_value, 0)
                        closure_env_ptr = self.builder.extract_value(var_value, 1)
                        # The extracted value is a pointer to function, we need to load it
                        # But wait - if it's already a function pointer (not a pointer to pointer), we can use it directly
                        # Check the type: if it's a pointer to pointer, load it
                        if isinstance(func_ptr_ptr.type, ir.PointerType) and isinstance(func_ptr_ptr.type.pointee, ir.PointerType):
                            # It's a pointer to pointer, load it to get the function pointer
                            closure_func_ptr = self.builder.load(func_ptr_ptr)
                        else:
                            # It's already a function pointer
                            closure_func_ptr = func_ptr_ptr
                        is_closure_call = True
                # Check if variable is a function pointer (closure with no captures)
                elif isinstance(var_value.type, ir.PointerType):
                    # Could be a function pointer (closure with no captures)
                    # For now, try to use it as a function
                    closure_func_ptr = var_value
                    is_closure_call = True
                    closure_env_ptr = None
        
        # If not a regular function or closure variable, try generating expression
        if func is None and not is_closure_call:
            func_expr = self.gen_expression(call.function)
            
            # Check if function expression is a closure struct
            struct_type = None
            struct_value = func_expr
            
            if isinstance(func_expr.type, ir.PointerType):
                # It's a pointer to struct
                struct_type = func_expr.type.pointee
                struct_value = func_expr
            elif isinstance(func_expr.type, ir.LiteralStructType):
                # It's a struct value - need to get a pointer to it
                struct_type = func_expr.type
                # Allocate temporary storage and store the struct
                temp_alloca = self.builder.alloca(struct_type)
                self.builder.store(func_expr, temp_alloca)
                struct_value = temp_alloca
            
            # Check if it's a closure struct (has 2 fields: function_ptr, env_ptr)
            if struct_type and isinstance(struct_type, ir.LiteralStructType) and len(struct_type.elements) == 2:
                # Check if both fields are pointers (function pointer and env pointer)
                if (isinstance(struct_type.elements[0], ir.PointerType) and
                    isinstance(struct_type.elements[1], ir.PointerType)):
                    # Extract function pointer
                    func_ptr_field = self.builder.gep(struct_type, struct_value, [
                        ir.Constant(ir.IntType(32), 0),
                        ir.Constant(ir.IntType(32), 0)
                    ], inbounds=True)
                    closure_func_ptr = self.builder.load(struct_type.elements[0], func_ptr_field)
                    
                    # Extract environment pointer
                    env_ptr_field = self.builder.gep(struct_type, struct_value, [
                        ir.Constant(ir.IntType(32), 0),
                        ir.Constant(ir.IntType(32), 1)
                    ], inbounds=True)
                    closure_env_ptr = self.builder.load(struct_type.elements[1], env_ptr_field)
                    
                    is_closure_call = True
        
        # Get function (either direct call or closure)
        if is_closure_call:
            # Use closure function pointer
            func = closure_func_ptr
        elif func is None:
            # If we still don't have a function, it's an error
            if isinstance(call.function, ast.Identifier):
                raise CodeGenError(f"Unknown function: {call.function.name}", call.span)
            else:
                raise CodeGenError("Complex function calls not yet supported", call.span)
        
        # Generate arguments with proper casting
        if isinstance(func, ir.Function):
            args = self.gen_call_arguments(func, call.arguments)
        else:
            # For closure pointers, etc.
            args = [self.gen_expression(arg) for arg in call.arguments]
        
        # Check if this is an FFI function call and convert references to pointers
        if isinstance(call.function, ast.Identifier):
            func_name = call.function.name
            if self._is_ffi_function(func_name) and func_name in self.functions:
                # Convert &T to *const T and &mut T to *mut T for FFI arguments
                # Get expected LLVM types from function signature
                func_llvm = self.functions[func_name]
                expected_types = list(func_llvm.ftype.args)
                args = self._convert_refs_to_ptrs_for_ffi(args, func_name, expected_types)
        
        # If closure call, prepend environment pointer
        if is_closure_call and closure_env_ptr:
            args.insert(0, closure_env_ptr)
        
        # Call function
        return self.builder.call(func, args)
    
    def _is_ffi_function(self, func_name: str) -> bool:
        """Check if a function is an FFI (extern "C") function"""
        if func_name in self.function_defs:
            func_def = self.function_defs[func_name]
            return func_def.is_extern
        return False
    
    def _convert_refs_to_ptrs_for_ffi(self, args: List[ir.Value], func_name: str, expected_types: List[ir.Type]) -> List[ir.Value]:
        """Convert reference arguments to pointers for FFI function calls
        
        Args:
            args: List of LLVM values (arguments)
            func_name: Name of the FFI function being called
            expected_types: List of expected LLVM types for each parameter
            
        Returns:
            List of converted arguments (references converted to pointers)
        """
        converted_args = []
        
        for i, (arg, expected_type) in enumerate(zip(args, expected_types)):
            # Check if types match
            if arg.type == expected_type:
                # Types match - use as-is
                converted_args.append(arg)
            elif isinstance(arg.type, ir.PointerType) and isinstance(expected_type, ir.PointerType):
                # Both are pointers - check if pointee types match
                if arg.type.pointee == expected_type.pointee:
                    # Pointee types match - use as-is (reference is already a pointer)
                    converted_args.append(arg)
                else:
                    # Pointee types don't match - try to bitcast
                    # This handles cases where the types are compatible but not identical
                    converted_args.append(self.builder.bitcast(arg, expected_type))
            elif not isinstance(arg.type, ir.PointerType) and isinstance(expected_type, ir.PointerType):
                # Argument is not a pointer but parameter expects one
                # Allocate temporary and get pointer
                temp_alloca = self.builder.alloca(arg.type)
                self.builder.store(arg, temp_alloca)
                converted_args.append(temp_alloca)
            else:
                # Types don't match and can't convert - use as-is (will fail at LLVM level if wrong)
                converted_args.append(arg)
        
        return converted_args
    
    def gen_print_call(self, call: ast.FunctionCall) -> ir.Value:
        """Generate code for print() builtin"""
        if not call.arguments:
            return ir.Constant(ir.IntType(32), 0)
        
        # Print each argument
        for arg_expr in call.arguments:
            arg = self.gen_expression(arg_expr)
            
            if isinstance(arg.type, ir.IntType) and arg.type.width == 32:
                # Use pyrite_print_int
                self.builder.call(self.print_int, [arg])
            elif isinstance(arg.type, ir.IntType):
                # Cast to i32 first
                arg_i32 = self.builder.trunc(arg, ir.IntType(32)) if arg.type.width > 32 else self.builder.sext(arg, ir.IntType(32))
                self.builder.call(self.print_int, [arg_i32])
            elif isinstance(arg.type, ir.DoubleType):
                # Use printf for floats
                fmt_struct = self.create_string_constant("%f\n")
                fmt = self.builder.extract_value(fmt_struct, 0)  # Extract i8* from {i8*, i64}
                self.builder.call(self.printf, [fmt, arg])
            elif isinstance(arg.type, ir.PointerType) and isinstance(arg.type.pointee, ir.IntType) and arg.type.pointee.width == 8:
                # String (i8*) - use printf with %s
                fmt_struct = self.create_string_constant("%s\n")
                fmt = self.builder.extract_value(fmt_struct, 0)  # Extract i8* from {i8*, i64}
                self.builder.call(self.printf, [fmt, arg])
            elif isinstance(arg.type, ir.LiteralStructType) and len(arg.type.elements) == 2 and isinstance(arg.type.elements[0], ir.PointerType):
                # Pyrite String struct { i8*, i64 }
                ptr = self.builder.extract_value(arg, 0)
                fmt_struct = self.create_string_constant("%s\n")
                fmt = self.builder.extract_value(fmt_struct, 0)
                self.builder.call(self.printf, [fmt, ptr])
            else:
                # For other types, use printf with placeholder
                fmt_struct = self.create_string_constant("<value>\n")
                fmt = self.builder.extract_value(fmt_struct, 0)  # Extract i8* from {i8*, i64}
                self.builder.call(self.printf, [fmt])
        
        return ir.Constant(ir.IntType(32), 0)
    
    def gen_method_call(self, call: ast.MethodCall) -> ir.Value:
        """Generate code for method call: object.method(args)
        
        For trait methods, uses static dispatch:
        1. Determine the type of the object
        2. Find the trait implementation for that type
        3. Call the concrete method directly (zero-cost abstraction)
        """
        # Get object type from type checker first (before generating expression)
        obj_type = None
        is_static_call = False
        obj = None
        
        # Handle string literals - they are String type
        if isinstance(call.object, ast.StringLiteral):
            from ..types import StringType
            obj_type = StringType()
        
        # Handle FieldAccess for enum constructors (e.g., Option.Some)
        if self.type_checker and isinstance(call.object, ast.FieldAccess):
            if isinstance(call.object.object, ast.Identifier):
                # Check if the object is a type name (e.g., Option)
                type_obj = self.type_checker.resolver.lookup_type(call.object.object.name)
                if type_obj:
                    from ..types import UNKNOWN
                    if type_obj != UNKNOWN:
                        # This is a static call on a type (e.g., Option.Some)
                        # For generic enums like Option[T], we need to handle the base enum type
                        # Check if it's a GenericType wrapping an EnumType
                        if hasattr(type_obj, 'base_type') and isinstance(type_obj.base_type, EnumType):
                            obj_type = type_obj.base_type
                        elif isinstance(type_obj, EnumType):
                            obj_type = type_obj
                        else:
                            obj_type = type_obj
                        is_static_call = True
                        obj = None
                        # The method name should be the field name from the FieldAccess
                        # But call.method might already be set correctly
                        # For enum constructors like Option.Some(42), the method is "Some"
        
        if self.type_checker and isinstance(call.object, ast.Identifier):
            # First, try to get type from current variable types (codegen's tracking)
            if call.object.name in self.variable_types:
                obj_type = self.variable_types[call.object.name]
            # Also try to get from type checker's resolver (for variables)
            elif hasattr(self.type_checker, 'resolver'):
                # Try as a variable first
                symbol = self.type_checker.resolver.lookup_variable(call.object.name)
                if symbol and hasattr(symbol, 'type'):
                    obj_type = symbol.type
                # If not a variable, try lookup_type (for static method calls on types)
                else:
                    type_obj = self.type_checker.resolver.lookup_type(call.object.name)
                    if type_obj:
                        obj_type = type_obj
                        is_static_call = True  # This is a static method call
        elif self.type_checker and isinstance(call.object, ast.GenericType):
            # Static call on generic type: Map[int, int].new()
            obj_type = self.type_checker.resolve_type(call.object)
            is_static_call = True
            obj = None
        
        # Generate object expression (for string literals, generate it here)
        if isinstance(call.object, ast.StringLiteral):
            obj = self.gen_expression(call.object)
        elif not is_static_call:
            try:
                obj = self.gen_expression(call.object)
            except CodeGenError as e:
                # If we can't generate the object (e.g., "Undefined variable: Point"),
                # it might be a static call on a type name
                if self.type_checker and isinstance(call.object, ast.Identifier):
                    type_obj = self.type_checker.resolver.lookup_type(call.object.name)
                    if type_obj:
                        obj_type = type_obj
                        is_static_call = True
                        obj = None  # No object for static calls
                    else:
                        raise  # Re-raise if it's not a type either
                else:
                    raise
            except Exception as e:
                # For other exceptions, check if it's a type name
                if self.type_checker and isinstance(call.object, ast.Identifier):
                    type_obj = self.type_checker.resolver.lookup_type(call.object.name)
                    if type_obj:
                        obj_type = type_obj
                        is_static_call = True
                        obj = None
                    else:
                        raise
                else:
                    raise
        
        # For MVP, try to find method in impl blocks
        # Method name format: Type_method_name
        method_name = call.method
        
        # Special handling for enum variant constructors
        # If this is a static call on an EnumType and the method matches a variant name,
        # generate the enum value directly
        # Handle both EnumType directly and GenericType wrapping EnumType
        # Also handle case where obj_type might be None but we detected it's a static call
        enum_type_for_check = obj_type
        if obj_type and hasattr(obj_type, 'base_type') and isinstance(obj_type.base_type, EnumType):
            enum_type_for_check = obj_type.base_type
        
        # If obj_type is still None but we have a FieldAccess, try to get the type again
        if obj_type is None and is_static_call and isinstance(call.object, ast.FieldAccess):
            if isinstance(call.object.object, ast.Identifier) and self.type_checker:
                type_obj = self.type_checker.resolver.lookup_type(call.object.object.name)
                if type_obj:
                    if hasattr(type_obj, 'base_type') and isinstance(type_obj.base_type, EnumType):
                        enum_type_for_check = type_obj.base_type
                    elif isinstance(type_obj, EnumType):
                        enum_type_for_check = type_obj
                    obj_type = enum_type_for_check
        
        if is_static_call and enum_type_for_check and isinstance(enum_type_for_check, EnumType):
            if method_name in enum_type_for_check.variants:
                # Use the enum type for variant lookup
                obj_type = enum_type_for_check
                variant_field_types = obj_type.variants[method_name]
                # Check argument count matches variant fields
                if variant_field_types is None:
                    # Variant with no fields - create enum value with tag only
                    # But if the enum type has any variants with fields, we need to return the struct
                    variant_names = list(obj_type.variants.keys())
                    variant_index = variant_names.index(method_name)
                    
                    # Check if enum has any variants with fields
                    has_any_fields = any(fields is not None and len(fields) > 0 
                                       for fields in obj_type.variants.values())
                    
                    if not has_any_fields:
                        # Simple enum without any fields - return i32 tag
                        tag_type = ir.IntType(32)
                        tag_value = ir.Constant(tag_type, variant_index)
                        return tag_value
                    else:
                        # Enum has some variants with fields, so return type is struct
                        # Create struct with tag + zero-filled array
                        enum_llvm_type = self.type_to_llvm(obj_type)
                        tag_type = ir.IntType(32)
                        tag_value = ir.Constant(tag_type, variant_index)
                        
                        if isinstance(enum_llvm_type, ir.LiteralStructType) and len(enum_llvm_type.elements) == 2:
                            # Create zero-filled array
                            array_type = enum_llvm_type.elements[1]
                            max_fields = array_type.count
                            i64_type = ir.IntType(64)
                            zero_i64 = ir.Constant(i64_type, 0)
                            
                            # Build array with zeros using alloca+store+insert_value
                            temp_alloca = self.builder.alloca(array_type)
                            # Initialize all elements with zeros
                            for i in range(max_fields):
                                elem_ptr = self.builder.gep(temp_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)])
                                self.builder.store(zero_i64, elem_ptr)
                            array_val = self.builder.load(temp_alloca)
                            
                            # Create struct: { tag, array } - build entirely at runtime
                            # Allocate struct, store fields directly using gep+store (no constants)
                            struct_alloca = self.builder.alloca(enum_llvm_type)
                            # Store tag at field 0
                            tag_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                            self.builder.store(tag_value, tag_gep)
                            # Store array at field 1 - need to store the array value
                            # First, store array into a temporary alloca, then copy to struct
                            array_temp = self.builder.alloca(array_type)
                            self.builder.store(array_val, array_temp)
                            array_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 1)])
                            # Copy array by loading from temp and storing to struct field
                            array_to_store = self.builder.load(array_temp)
                            self.builder.store(array_to_store, array_gep)
                            # Load the complete struct
                            struct_val = self.builder.load(struct_alloca)
                            
                            return struct_val
                        else:
                            # Fallback: should not happen for enums with fields
                            return tag_value
                else:
                    # Variant with fields - validate argument count
                    if len(call.arguments) != len(variant_field_types):
                        raise CodeGenError(
                            f"Enum variant {obj_type.name}.{method_name} expects {len(variant_field_types)} arguments, got {len(call.arguments)}",
                            call.span
                        )
                    
                    # Generate enum value with fields
                    # Get the enum struct type (ensures it's created)
                    enum_llvm_type = self.type_to_llvm(obj_type)
                    
                    # Get variant index
                    variant_names = list(obj_type.variants.keys())
                    variant_index = variant_names.index(method_name)
                    
                    # Generate field values and convert to i64 for storage
                    # The enum struct is { i32 tag, [max_fields x i64] data }
                    field_values_i64 = []
                    for arg_expr, field_type in zip(call.arguments, variant_field_types):
                        field_val = self.gen_expression(arg_expr)
                        # Convert field value to i64 for storage in the array
                        i64_type = ir.IntType(64)
                        if isinstance(field_val.type, ir.IntType):
                            if field_val.type.width < 64:
                                # Zero-extend to i64
                                field_val_i64 = self.builder.zext(field_val, i64_type)
                            elif field_val.type.width > 64:
                                # Truncate to i64 (may lose data, but MVP)
                                field_val_i64 = self.builder.trunc(field_val, i64_type)
                            else:
                                field_val_i64 = field_val
                        elif isinstance(field_val.type, ir.FloatType):
                            # Convert float to i64 via bitcast
                            field_val_i64 = self.builder.bitcast(field_val, i64_type)
                        elif isinstance(field_val.type, ir.DoubleType):
                            # Convert double to i64 via bitcast
                            field_val_i64 = self.builder.bitcast(field_val, i64_type)
                        elif field_val.type.is_pointer:
                            # Convert pointer to i64
                            field_val_i64 = self.builder.ptrtoint(field_val, i64_type)
                        elif isinstance(field_val.type, ir.LiteralStructType):
                            # For struct types (including enum structs), we can't bitcast directly
                            # Store as pointer: allocate on stack, store struct, then convert pointer to i64
                            # For MVP, we'll use alloca to get a pointer, store the struct, then ptrtoint
                            alloca = self.builder.alloca(field_val.type)
                            self.builder.store(field_val, alloca)
                            field_val_i64 = self.builder.ptrtoint(alloca, i64_type)
                        else:
                            # For other types, try bitcast to i64 (but this may fail for structs)
                            # If bitcast fails, we should handle it, but for now try it
                            try:
                                field_val_i64 = self.builder.bitcast(field_val, i64_type)
                            except:
                                # Fallback: treat as pointer
                                alloca = self.builder.alloca(field_val.type)
                                self.builder.store(field_val, alloca)
                                field_val_i64 = self.builder.ptrtoint(alloca, i64_type)
                        field_values_i64.append(field_val_i64)
                    
                    # Create struct value: { i32 tag, [max_fields x i64] data }
                    tag_type = ir.IntType(32)
                    tag_value = ir.Constant(tag_type, variant_index)
                    
                    # Get the struct type (should be { i32, i64, i64, ... })
                    if isinstance(enum_llvm_type, ir.LiteralStructType) and len(enum_llvm_type.elements) > 1:
                        # Struct has tag + individual i64 fields
                        # Create struct using alloca and store fields directly
                        struct_alloca = self.builder.alloca(enum_llvm_type)
                        # Store tag at field 0
                        tag_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                        self.builder.store(tag_value, tag_gep)
                        
                        # Store field values in individual struct fields (field 1, 2, 3, ...)
                        i64_type = ir.IntType(64)
                        zero_i64 = ir.Constant(i64_type, 0)
                        num_data_fields = len(enum_llvm_type.elements) - 1  # Exclude tag field
                        for i, field_val in enumerate(field_values_i64):
                            if i < num_data_fields:
                                field_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i + 1)])
                                self.builder.store(field_val, field_gep)
                        # Pad remaining fields with zeros
                        for i in range(len(field_values_i64), num_data_fields):
                            field_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i + 1)])
                            self.builder.store(zero_i64, field_gep)
                        
                        # Load struct
                        struct_val = self.builder.load(struct_alloca)
                        
                        return struct_val
                    else:
                        # Fallback: should not happen for enums with fields
                        return tag_value
        
        # Special handling for Map method calls
        if obj_type and isinstance(obj_type, GenericType) and obj_type.name == "Map":
            # Handle Map[K, V] method calls
            if is_static_call and method_name == "new":
                # Map.new() - static constructor
                # Need key_size and value_size from type_args
                if len(obj_type.type_args) < 2:
                    raise CodeGenError("Map.new() requires Map[K, V] with two type arguments", call.span)
                key_type = obj_type.type_args[0]
                value_type = obj_type.type_args[1]
                key_llvm = self.type_to_llvm(key_type)
                value_llvm = self.type_to_llvm(value_type)
                # Get sizes (for now, use sizeof approximation)
                key_size = self._get_type_size(key_llvm)
                value_size = self._get_type_size(value_llvm)
                # Call map_new
                key_size_const = ir.Constant(ir.IntType(64), key_size)
                value_size_const = ir.Constant(ir.IntType(64), value_size)
                map_val = self.builder.call(self.map_new, [key_size_const, value_size_const])
                
                # Track allocation for cost analysis
                if self.track_costs and self.function:
                    func_name = self.function.name if self.function else "unknown"
                    line = call.span.start_line if call.span else 0
                    # Estimate Map allocation size (hash table overhead + initial capacity)
                    estimated_bytes = 64 + (key_size + value_size) * 8  # Rough estimate
                    self.allocation_sites.append({
                        "function": func_name,
                        "line": line,
                        "type": "Map",
                        "bytes": estimated_bytes,
                        "description": f"Map[{obj_type.type_args[0]}, {obj_type.type_args[1]}]"
                    })
                
                # Emit cost warning if enabled
                if self.warn_costs and call.span:
                    self.cost_warnings.append({
                        "span": call.span,
                        "message": f"Heap allocation: Map[{obj_type.type_args[0]}, {obj_type.type_args[1]}]",
                        "help_hint": "Consider using a reference (&Map) or pre-allocating with known size if possible"
                    })
                
                return map_val
            elif not is_static_call and obj:
                # Instance method calls on Map
                # Get pointer to Map struct
                if not isinstance(obj.type, ir.PointerType):
                    # Allocate and store Map struct
                    map_alloca = self.builder.alloca(obj.type, name="map_ptr")
                    self.builder.store(obj, map_alloca)
                    map_ptr = map_alloca
                else:
                    map_ptr = obj
                
                if method_name == "get" or method_name == "set" or method_name == "insert":
                    # map.get(key) or map.set(key, value) or map.insert(key, value)
                    if len(call.arguments) < 1:
                        raise CodeGenError(f"Map.{method_name}() requires at least one argument", call.span)
                    key_expr = call.arguments[0]
                    key_val = self.gen_expression(key_expr)
                    # Convert key to pointer
                    if not isinstance(key_val.type, ir.PointerType):
                        key_alloca = self.builder.alloca(key_val.type, name="key_ptr")
                        self.builder.store(key_val, key_alloca)
                        key_ptr = self.builder.bitcast(key_alloca, ir.IntType(8).as_pointer())
                    else:
                        key_ptr = self.builder.bitcast(key_val, ir.IntType(8).as_pointer())
                    
                    if method_name == "get":
                        # map.get(key) -> Option[&V] (for now, return pointer or null)
                        result_ptr = self.builder.call(self.map_get, [map_ptr, key_ptr])
                        return result_ptr
                    elif method_name == "set" or method_name == "insert":
                        # map.set(key, value) or map.insert(key, value)
                        if len(call.arguments) < 2:
                            raise CodeGenError(f"Map.{method_name}() requires two arguments (key, value)", call.span)
                        value_expr = call.arguments[1]
                        value_val = self.gen_expression(value_expr)
                        # Convert value to pointer
                        if not isinstance(value_val.type, ir.PointerType):
                            value_alloca = self.builder.alloca(value_val.type, name="value_ptr")
                            self.builder.store(value_val, value_alloca)
                            value_ptr = self.builder.bitcast(value_alloca, ir.IntType(8).as_pointer())
                        else:
                            value_ptr = self.builder.bitcast(value_val, ir.IntType(8).as_pointer())
                        # Call map_insert
                        self.builder.call(self.map_insert, [map_ptr, key_ptr, value_ptr])
                        return ir.Constant(ir.IntType(32), 0)  # Return void (0 for now)
                elif method_name == "contains":
                    # map.contains(key) -> bool
                    if len(call.arguments) < 1:
                        raise CodeGenError("Map.contains() requires one argument", call.span)
                    key_expr = call.arguments[0]
                    key_val = self.gen_expression(key_expr)
                    # Convert key to pointer
                    if not isinstance(key_val.type, ir.PointerType):
                        key_alloca = self.builder.alloca(key_val.type, name="key_ptr")
                        self.builder.store(key_val, key_alloca)
                        key_ptr = self.builder.bitcast(key_alloca, ir.IntType(8).as_pointer())
                    else:
                        key_ptr = self.builder.bitcast(key_val, ir.IntType(8).as_pointer())
                    # Call map_contains
                    result = self.builder.call(self.map_contains, [map_ptr, key_ptr])
                    # Convert i8 to i1 (bool)
                    return self.builder.trunc(result, ir.IntType(1))
                elif method_name == "length":
                    # map.length() -> int
                    result = self.builder.call(self.map_length, [map_ptr])
                    return result
        
        # Special handling for List method calls
        if obj_type and isinstance(obj_type, GenericType) and obj_type.name == "List":
            # Handle List[T] method calls
            if is_static_call and (method_name == "new" or method_name == "with_capacity"):
                # List.new() or List.with_capacity(cap)
                elem_type = obj_type.type_args[0]
                elem_llvm = self.type_to_llvm(elem_type)
                elem_size = self._get_type_size(elem_llvm)
                elem_size_const = ir.Constant(ir.IntType(64), elem_size)
                
                if method_name == "new":
                    return self.builder.call(self.list_new, [elem_size_const])
                else: # with_capacity
                    if len(call.arguments) < 1:
                        raise CodeGenError("List.with_capacity() requires one argument", call.span)
                    cap_val = self.gen_expression(call.arguments[0])
                    return self.builder.call(self.list_with_capacity, [elem_size_const, cap_val])
            
            elif not is_static_call and obj:
                # Instance method calls on List
                # Get pointer to List struct
                if not isinstance(obj.type, ir.PointerType):
                    list_alloca = self.builder.alloca(obj.type, name="list_ptr")
                    self.builder.store(obj, list_alloca)
                    list_ptr = list_alloca
                else:
                    list_ptr = obj
                
                elem_type = obj_type.type_args[0]
                elem_llvm = self.type_to_llvm(elem_type)
                elem_size = self._get_type_size(elem_llvm)
                elem_size_const = ir.Constant(ir.IntType(64), elem_size)

                if method_name == "push":
                    if len(call.arguments) < 1:
                        raise CodeGenError("List.push() requires one argument", call.span)
                    elem_val = self.gen_expression(call.arguments[0])
                    # Convert elem to pointer
                    if not isinstance(elem_val.type, ir.PointerType):
                        elem_alloca = self.builder.alloca(elem_val.type, name="elem_ptr")
                        self.builder.store(elem_val, elem_alloca)
                        elem_ptr = self.builder.bitcast(elem_alloca, ir.IntType(8).as_pointer())
                    else:
                        elem_ptr = self.builder.bitcast(elem_val, ir.IntType(8).as_pointer())
                    # Call list_push
                    self.builder.call(self.list_push, [list_ptr, elem_ptr, elem_size_const])
                    return ir.Constant(ir.IntType(32), 0)
                
                elif method_name == "get":
                    if len(call.arguments) < 1:
                        raise CodeGenError("List.get() requires one argument", call.span)
                    index_val = self.gen_expression(call.arguments[0])
                    # Call list_get
                    result_ptr = self.builder.call(self.list_get, [list_ptr, index_val, elem_size_const])
                    # Bitcast and load result
                    typed_ptr = self.builder.bitcast(result_ptr, elem_llvm.as_pointer())
                    return self.builder.load(typed_ptr)
                
                elif method_name == "length":
                    return self.builder.call(self.list_length, [list_ptr])

        # Special handling for Set method calls
        if obj_type and isinstance(obj_type, GenericType) and obj_type.name == "Set":
            # Handle Set[T] method calls
            if is_static_call and method_name == "new":
                elem_type = obj_type.type_args[0]
                elem_llvm = self.type_to_llvm(elem_type)
                elem_size = self._get_type_size(elem_llvm)
                elem_size_const = ir.Constant(ir.IntType(64), elem_size)
                return self.builder.call(self.set_new, [elem_size_const])
            
            elif not is_static_call and obj:
                # Instance method calls on Set
                if not isinstance(obj.type, ir.PointerType):
                    set_alloca = self.builder.alloca(obj.type, name="set_ptr")
                    self.builder.store(obj, set_alloca)
                    set_ptr = set_alloca
                else:
                    set_ptr = obj
                
                if method_name == "insert" or method_name == "contains":
                    if len(call.arguments) < 1:
                        raise CodeGenError(f"Set.{method_name}() requires one argument", call.span)
                    elem_val = self.gen_expression(call.arguments[0])
                    # Convert elem to pointer
                    if not isinstance(elem_val.type, ir.PointerType):
                        elem_alloca = self.builder.alloca(elem_val.type, name="elem_ptr")
                        self.builder.store(elem_val, elem_alloca)
                        elem_ptr = self.builder.bitcast(elem_alloca, ir.IntType(8).as_pointer())
                    else:
                        elem_ptr = self.builder.bitcast(elem_val, ir.IntType(8).as_pointer())
                    
                    if method_name == "insert":
                        self.builder.call(self.set_insert, [set_ptr, elem_ptr])
                        return ir.Constant(ir.IntType(32), 0)
                    else: # contains
                        result = self.builder.call(self.set_contains, [set_ptr, elem_ptr])
                        return self.builder.trunc(result, ir.IntType(1))
                
                elif method_name == "length":
                    return self.builder.call(self.set_length, [set_ptr])

        # Try to find method function
        # First, try inherent method: Type_method
        if obj_type:
            type_name = str(obj_type)
            # For struct types, use the name directly
            if hasattr(obj_type, 'name'):
                type_name = obj_type.name
            
            inherent_method_name = f"{type_name}_{method_name}"
            if inherent_method_name in self.functions:
                func = self.functions[inherent_method_name]
                
                # For instance methods, prepend self (object) as first argument
                if not is_static_call:
                    # Ensure obj is a pointer if the method expects one
                    if func.ftype.args and isinstance(func.ftype.args[0], ir.PointerType):
                        if not isinstance(obj.type, ir.PointerType):
                            # Allocate space for struct and store it
                            alloca = self.builder.alloca(obj.type, name="self_ptr")
                            self.builder.store(obj, alloca)
                            obj = alloca
                    
                    args = [obj] + self.gen_call_arguments(func, call.arguments, offset=1)
                else:
                    # Static method
                    args = self.gen_call_arguments(func, call.arguments)
                
                return self.builder.call(func, args)
        
        # Try trait method dispatch
        if obj_type and self.type_checker:
            # Look for trait implementations for this type
            # Try both the type name string and the type object
            type_name_str = str(obj_type)
            # Also try getting the base type name (for struct types)
            if hasattr(obj_type, 'name'):
                type_name_str = obj_type.name
            elif isinstance(obj_type, str):
                type_name_str = obj_type
            
            trait_impls = self.type_checker.trait_implementations.get(type_name_str, {})
            
            # Search through trait implementations to find the method
            # Sort for deterministic order if in deterministic mode
            items_to_iterate = trait_impls.items()
            if self.deterministic:
                items_to_iterate = sorted(items_to_iterate, key=lambda x: x[0])
            
            for trait_name, impl_block in items_to_iterate:
                # Check if this impl has the method
                for method in impl_block.methods:
                    if method.name == method_name:
                        # Found the method! Generate static dispatch call
                        # Method name format: Type_Trait_method
                        trait_method_name = f"{type_name_str}_{trait_name}_{method_name}"
                        
                        if trait_method_name in self.functions:
                            func = self.functions[trait_method_name]
                            # Handle self (object) as first argument
                            # If method expects a pointer, create one
                            if func.function_type.args and isinstance(func.function_type.args[0], ir.PointerType):
                                # Need to allocate and store the struct, then pass pointer
                                if not isinstance(obj.type, ir.PointerType):
                                    # Allocate space for struct
                                    alloca = self.builder.alloca(obj.type, name="self_ptr")
                                    self.builder.store(obj, alloca)
                                    self_arg = alloca
                                else:
                                    self_arg = obj
                            else:
                                self_arg = obj
                            
                            args = [self_arg] + self.gen_call_arguments(func, call.arguments, offset=1)
                            return self.builder.call(func, args)
        
        # Fallback: try direct method name (for builtin methods)
        if method_name in self.functions:
            func = self.functions[method_name]
            args = [obj] + self.gen_call_arguments(func, call.arguments, offset=1)
            return self.builder.call(func, args)
        
        # Error: method not found
        # Debug info
        if isinstance(call.object, ast.StringLiteral):
            available = [f for f in self.functions.keys() if f.startswith("String_")]
            raise CodeGenError(
                f"Method '{method_name}' not found for String literal. obj_type={obj_type}, available: {available}",
                call.span
            )
        raise CodeGenError(
            f"Method '{method_name}' not found for type '{obj_type}'",
            call.span
        )
    
    def gen_field_access(self, access: ast.FieldAccess) -> ir.Value:
        """Generate code for field access"""
        # Check if this is a static field access on a type (e.g., Type.BoolType, Option.Some)
        obj_type = None
        is_static_access = False
        if isinstance(access.object, ast.Identifier) and self.type_checker:
            # Check if it's a type name first (before trying as variable)
            if hasattr(self.type_checker, 'resolver'):
                # Try lookup_type first for static access
                type_obj = self.type_checker.resolver.lookup_type(access.object.name)
                if type_obj:
                    obj_type = type_obj
                    is_static_access = True
        
        # If not a static access, generate object expression
        if not is_static_access:
            obj = self.gen_expression(access.object)
        else:
            obj = None
        
        # Handle static field access on enum types (e.g., Type.BoolType)
        if is_static_access and obj_type and isinstance(obj_type, EnumType):
            if access.field in obj_type.variants:
                variant_field_types = obj_type.variants[access.field]
                if variant_field_types is None:
                    # Variant with no fields - return tag value or struct depending on enum type
                    variant_names = list(obj_type.variants.keys())
                    variant_index = variant_names.index(access.field)
                    
                    # Check if enum has any variants with fields
                    has_any_fields = any(fields is not None and len(fields) > 0 
                                       for fields in obj_type.variants.values())
                    
                    if not has_any_fields:
                        # Simple enum - return i32 tag
                        tag_type = ir.IntType(32)
                        return ir.Constant(tag_type, variant_index)
                    else:
                        # Enum has variants with fields - return struct with tag + zero array
                        enum_llvm_type = self.type_to_llvm(obj_type)
                        tag_type = ir.IntType(32)
                        tag_value = ir.Constant(tag_type, variant_index)
                        
                        if isinstance(enum_llvm_type, ir.LiteralStructType) and len(enum_llvm_type.elements) > 1:
                            # Struct has tag + individual i64 fields
                            # Create struct using alloca and store fields directly
                            struct_alloca = self.builder.alloca(enum_llvm_type)
                            # Store tag at field 0
                            tag_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])
                            self.builder.store(tag_value, tag_gep)
                            
                            # Store zeros in all data fields (variant has no fields, so all zeros)
                            i64_type = ir.IntType(64)
                            zero_i64 = ir.Constant(i64_type, 0)
                            num_data_fields = len(enum_llvm_type.elements) - 1  # Exclude tag field
                            for i in range(num_data_fields):
                                field_gep = self.builder.gep(struct_alloca, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i + 1)])
                                self.builder.store(zero_i64, field_gep)
                            
                            # Load struct
                            struct_val = self.builder.load(struct_alloca)
                            
                            return struct_val
                        else:
                            # Fallback: should not happen for enums with fields
                            return tag_value
                else:
                    # Variant with fields - this should be a constructor call, not field access
                    raise CodeGenError(
                        f"Enum variant {obj_type.name}.{access.field} has fields and must be called as a constructor",
                        access.span
                    )
        
        # Get the struct type info from type checker
        if hasattr(self, 'type_checker') and self.type_checker:
            # Get object type
            if isinstance(access.object, ast.Identifier):
                var_name = access.object.name
                if hasattr(self, 'variable_types') and var_name in self.variable_types:
                    obj_type = self.variable_types.get(var_name)
                    
                    if isinstance(obj_type, StructType):
                        # Get field index
                        # Sort field names for deterministic order
                        field_names = sorted(obj_type.fields.keys()) if self.deterministic else list(obj_type.fields.keys())
                        if access.field in field_names:
                            field_index = field_names.index(access.field)
                            
                            # If obj is a struct value, extract field
                            if isinstance(obj.type, ir.LiteralStructType):
                                # Extract field from struct
                                return self.builder.extract_value(obj, field_index)
        
        # Fallback: return the object itself (or raise error if static access failed)
        if is_static_access:
            raise CodeGenError(
                f"Static field access '{access.object.name}.{access.field}' not supported",
                access.span
            )
        return obj
    
    def gen_parameter_closure(self, closure: ast.ParameterClosure) -> ir.Value:
        """
        Generate code for parameter closure (fn[...])
        
        Parameter closures should be inlined at call sites, not generated as values.
        If we encounter one here, it means it's being used incorrectly (stored/returned).
        
        For now, we'll generate a placeholder that will be inlined later.
        """
        # Parameter closures don't have a runtime representation
        # They should only appear as arguments to functions that inline them
        # For now, return a null pointer as placeholder
        # TODO: Add error checking to prevent storing parameter closures
        return ir.Constant(ir.IntType(8).as_pointer(), None)
    
    def gen_runtime_closure(self, closure: ast.RuntimeClosure) -> ir.Value:
        """
        Generate code for runtime closure (fn(...))
        
        Runtime closures are first-class values with structure:
        - function_ptr: Pointer to closure function
        - env_ptr: Pointer to captured environment (or null if no captures)
        
        If captures exist:
        1. Create environment struct type
        2. Allocate environment on heap
        3. Copy captured variables into environment
        4. Create closure object (function_ptr, env_ptr)
        5. Closure function accepts env_ptr as hidden first parameter
        """
        # Generate a unique name for the closure function
        closure_name = f"__closure_{id(closure)}"
        
        # Get captured variables and their types
        captured_vars = closure.captures if closure.captures else []
        
        # Create function type (with environment pointer if captures exist)
        param_types = []
        env_type = None
        
        if captured_vars:
            # Create environment struct type
            env_fields = []
            env_field_types = {}
            
            for var_name in captured_vars:
                # Get variable type from current scope
                if var_name in self.variable_types:
                    var_type = self.variable_types[var_name]
                    llvm_type = self.type_to_llvm(var_type)
                    env_fields.append(llvm_type)
                    env_field_types[var_name] = var_type
                else:
                    # Default to i32 if type not found
                    env_fields.append(ir.IntType(32))
                    env_field_types[var_name] = IntType(32)
            
            # Create environment struct type
            env_type = ir.LiteralStructType(env_fields)
            self.closure_environments[closure_name] = env_type
            self.closure_environment_types[closure_name] = env_field_types
            
            # Environment pointer is first parameter
            param_types.append(env_type.as_pointer())
        
        # Add closure parameters
        param_types.extend([self.llvm_type_from_pyrite_type(param.type_annotation) for param in closure.params])
        
        # Determine return type
        if closure.return_type:
            return_type = self.llvm_type_from_pyrite_type(closure.return_type)
        else:
            # Infer from body
            if closure.body.statements:
                return_stmt = closure.body.statements[0]
                if isinstance(return_stmt, ast.ReturnStmt) and return_stmt.value:
                    # Type check the return expression
                    # For now, default to i32
                    return_type = ir.IntType(32)
                else:
                    return_type = ir.VoidType()
            else:
                return_type = ir.VoidType()
        
        # Create closure function
        func_type = ir.FunctionType(return_type, param_types)
        closure_func = ir.Function(self.module, func_type, name=closure_name)
        
        # Save current builder and function
        saved_builder = self.builder
        saved_function = self.function
        saved_variables = self.variables.copy()
        saved_variable_types = self.variable_types.copy()
        
        # Create entry block for closure
        block = closure_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.function = closure_func
        
        # Load captured variables from environment if they exist
        env_param_idx = 0
        if captured_vars:
            env_ptr = closure_func.args[0]
            env_ptr.name = "__env"
            
            # Load each captured variable from environment
            for i, var_name in enumerate(captured_vars):
                # Get pointer to field in environment
                # GEP: getelementptr env_type, env_ptr, [0, i]
                field_ptr = self.builder.gep(env_ptr, [
                    ir.Constant(ir.IntType(32), 0),  # Base pointer
                    ir.Constant(ir.IntType(32), i)   # Field index
                ], inbounds=True)
                
                # Load the value
                var_value = self.builder.load(field_ptr)
                var_value.name = var_name
                
                # Add to closure's variable scope
                self.variables[var_name] = var_value
                if var_name in env_field_types:
                    self.variable_types[var_name] = env_field_types[var_name]
            
            env_param_idx = 1
        
        # Add closure parameters to scope
        for i, param in enumerate(closure.params):
            param_value = closure_func.args[env_param_idx + i]
            param_value.name = param.name
            self.variables[param.name] = param_value
        
        # Generate closure body
        self.gen_block(closure.body)
        
        # Ensure function returns
        if not self.builder.block.is_terminated:
            if isinstance(return_type, ir.VoidType):
                self.builder.ret_void()
            else:
                # Return zero/null as default
                self.builder.ret(self._create_zero_constant(return_type))
        
        # Restore builder and function
        self.builder = saved_builder
        self.function = saved_function
        self.variables = saved_variables
        self.variable_types = saved_variable_types
        
        # If no captures, return function pointer directly
        if not captured_vars:
            return closure_func
        
        # Allocate environment on heap
        # Calculate size manually (sum of field sizes)
        # For MVP, use a simple calculation
        env_size_bytes = 0
        for field_type in env_type.elements:
            if isinstance(field_type, ir.IntType):
                env_size_bytes += field_type.width // 8
            elif isinstance(field_type, ir.FloatType):
                env_size_bytes += 4 if field_type.width == 32 else 8
            elif isinstance(field_type, ir.PointerType):
                env_size_bytes += 8  # 64-bit pointer
            else:
                env_size_bytes += 8  # Default
        
        env_size = ir.Constant(ir.IntType(64), env_size_bytes)
        
        # Get or declare malloc
        if not self.malloc:
            malloc_type = ir.FunctionType(
                ir.IntType(8).as_pointer(),
                [ir.IntType(64)]
            )
            self.malloc = ir.Function(self.module, malloc_type, name="malloc")
        
        # Allocate environment
        env_raw_ptr = self.builder.call(self.malloc, [env_size])
        env_ptr = self.builder.bitcast(env_raw_ptr, env_type.as_pointer())
        
        # Copy captured variables into environment
        for i, var_name in enumerate(captured_vars):
            if var_name in saved_variables:
                # Get source value
                src_value = saved_variables[var_name]
                
                # Get pointer to field in environment
                # GEP: getelementptr env_ptr, [0, i]
                field_ptr = self.builder.gep(env_ptr, [
                    ir.Constant(ir.IntType(32), 0),  # Base pointer
                    ir.Constant(ir.IntType(32), i)   # Field index
                ], inbounds=True)
                
                # Store value into environment
                self.builder.store(src_value, field_ptr)
        
        # Create closure object struct: { function_ptr, env_ptr }
        closure_struct_type = ir.LiteralStructType([
            closure_func.type.as_pointer(),  # function pointer
            env_type.as_pointer()            # environment pointer
        ])
        
        # Create closure object struct value
        # We'll use insertvalue to build the struct
        closure_obj = ir.Constant(closure_struct_type, ir.Undefined)
        
        # Insert function pointer (cast to generic function pointer type)
        func_ptr_const = ir.Constant(closure_func.type.as_pointer(), closure_func)
        closure_obj = self.builder.insert_value(closure_obj, func_ptr_const, 0)
        
        # Insert environment pointer
        closure_obj = self.builder.insert_value(closure_obj, env_ptr, 1)
        
        # Return closure object as struct value
        return closure_obj
    
    def llvm_type_from_pyrite_type(self, type_node: ast.Type) -> ir.Type:
        """Convert Pyrite type annotation to LLVM type"""
        if isinstance(type_node, ast.PrimitiveType):
            if type_node.name == "int":
                return ir.IntType(32)
            elif type_node.name == "i64":
                return ir.IntType(64)
            elif type_node.name == "bool":
                return ir.IntType(1)
            elif type_node.name == "f32":
                return ir.FloatType()
            elif type_node.name == "f64":
                return ir.DoubleType()
            elif type_node.name == "void":
                return ir.VoidType()
            else:
                return ir.IntType(32)  # Default
        elif isinstance(type_node, ast.ReferenceType):
            # References are pointers
            inner_type = self.llvm_type_from_pyrite_type(type_node.inner_type)
            return inner_type.as_pointer()
        else:
            # Default to i32
            return ir.IntType(32)
    
    def gen_struct_literal(self, literal: ast.StructLiteral) -> ir.Value:
        """Generate code for struct literal"""
        # Get struct type from type checker
        if hasattr(self, 'type_checker') and self.type_checker:
            struct_type_obj = self.type_checker.resolver.lookup_type(literal.struct_name)
            
            if isinstance(struct_type_obj, StructType):
                # Create LLVM struct type if not already created
                if literal.struct_name not in self.struct_types:
                    field_types = []
                    # Sort field names for deterministic order
                    field_iter = sorted(struct_type_obj.fields.keys()) if self.deterministic else struct_type_obj.fields.keys()
                    for field_name in field_iter:
                        field_type = struct_type_obj.fields[field_name]
                        field_types.append(self.type_to_llvm(field_type))
                    llvm_struct = ir.LiteralStructType(field_types)
                    self.struct_types[literal.struct_name] = llvm_struct
                
                struct_ty = self.struct_types[literal.struct_name]
                
                # Generate field values in correct order
                # Sort field names for deterministic order
                field_names = sorted(struct_type_obj.fields.keys()) if self.deterministic else list(struct_type_obj.fields.keys())
                field_values = [None] * len(field_names)
                
                for field_name, field_expr in literal.fields:
                    if field_name in field_names:
                        index = field_names.index(field_name)
                        field_values[index] = self.gen_expression(field_expr)
                
                # Create struct value by inserting fields
                struct_val = ir.Constant(struct_ty, ir.Undefined)
                for i, field_val in enumerate(field_values):
                    if field_val is not None:
                        struct_val = self.builder.insert_value(struct_val, field_val, i)
                
                # Store type info for later field access
                self.variable_types = getattr(self, 'variable_types', {})
                
                return struct_val
        
        # Fallback
        return ir.Constant(ir.IntType(32), 0)
    
    def create_string_constant(self, value: str) -> ir.Value:
        """Create a global string constant and return as String struct {i8*, i64}"""
        # Add null terminator
        string_bytes = bytearray((value + '\0').encode('utf-8'))
        
        # Create constant
        string_ty = ir.ArrayType(ir.IntType(8), len(string_bytes))
        string_const = ir.Constant(string_ty, string_bytes)
        
        # Create global variable
        global_str = ir.GlobalVariable(self.module, string_ty, name=self.module.get_unique_name("str"))
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = string_const
        
        # Get pointer to first element
        ptr = self.builder.bitcast(global_str, ir.IntType(8).as_pointer())
        
        # String type is {i8*, i64} - wrap in struct
        string_struct_ty = ir.LiteralStructType([
            ir.IntType(8).as_pointer(),
            ir.IntType(64)
        ])
        # Create struct with pointer and length (excluding null terminator for length)
        length = len(value.encode('utf-8'))
        length_val = ir.Constant(ir.IntType(64), length)
        struct_val = ir.Constant(string_struct_ty, ir.Undefined)
        struct_val = self.builder.insert_value(struct_val, ptr, 0)
        struct_val = self.builder.insert_value(struct_val, length_val, 1)
        return struct_val


def generate_llvm(program: ast.Program, deterministic: bool = False, type_checker=None) -> str:
    """Generate LLVM IR from program"""
    codegen = LLVMCodeGen(deterministic=deterministic)
    if type_checker:
        codegen.type_checker = type_checker
    module = codegen.compile_program(program)
    return str(module)


def compile_to_executable(program: ast.Program, output_path: str, deterministic: bool = False):
    """Compile program to executable"""
    codegen = LLVMCodeGen(deterministic=deterministic)
    module = codegen.compile_program(program)
    
    # Create execution engine
    llvm_ir = str(module)
    
    # Parse and verify
    llvm_module = binding.parse_assembly(llvm_ir)
    llvm_module.verify()
    
    # Optimize (optional)
    pmb = binding.PassManagerBuilder()
    pmb.opt_level = 0  # No optimization for debug
    pm = binding.ModulePassManager()
    pmb.populate(pm)
    pm.run(llvm_module)
    
    # Create target machine
    target = binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    
    # Generate object file
    with open(output_path + ".o", "wb") as f:
        f.write(target_machine.emit_object(llvm_module))
    
    return output_path + ".o"

