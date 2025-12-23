"""Abstract Syntax Tree node definitions for Pyrite"""

from dataclasses import dataclass
from typing import List, Optional, Any
from .frontend.tokens import Span


# Base classes
@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    span: Span


# Program structure
@dataclass
class Program(ASTNode):
    """Root of the AST"""
    imports: List['ImportStmt']
    items: List['Item']


@dataclass
class ImportStmt(ASTNode):
    """Import statement: import std::collections"""
    path: List[str]  # ["std", "collections"]
    alias: Optional[str] = None  # "as collections"


# Top-level items
@dataclass
class FunctionDef(ASTNode):
    """Function definition"""
    name: str
    generic_params: List['GenericParam']  # Type parameters: T, U
    compile_time_params: List[Any]  # Compile-time params: N: int, Flag: bool
    params: List['Param']
    return_type: Optional['Type']
    body: 'Block'
    is_unsafe: bool = False
    is_extern: bool = False  # True for extern "C" functions
    extern_abi: Optional[str] = None  # "C", "Rust", etc.
    where_clause: List[tuple[str, List[str]]] = None  # Where T: Trait1 + Trait2
    attributes: List['Attribute'] = None  # @noalloc, #[allow(...)], etc.
    
    def __post_init__(self):
        if self.where_clause is None:
            self.where_clause = []
        if self.attributes is None:
            self.attributes = []


@dataclass
class GenericParam(ASTNode):
    """Generic type parameter: T or T: Trait"""
    name: str
    trait_bounds: List[str]  # Trait names


@dataclass
class CompileTimeIntParam(ASTNode):
    """Compile-time integer parameter: N: int"""
    name: str


@dataclass
class CompileTimeBoolParam(ASTNode):
    """Compile-time boolean parameter: Flag: bool"""
    name: str


@dataclass
class CompileTimeFunctionParam(ASTNode):
    """Compile-time function parameter: Body: fn[int] -> int"""
    name: str
    param_types: List['Type']  # Parameter types: [int, int]
    return_type: Optional['Type']  # Return type: int or None


@dataclass
class Param(ASTNode):
    """Function parameter"""
    name: str
    type_annotation: 'Type'


@dataclass
class StructDef(ASTNode):
    """Struct definition"""
    name: str
    generic_params: List['GenericParam']  # Type parameters: T, U
    compile_time_params: List[Any]  # Compile-time params: N: int, Flag: bool
    fields: List['Field']
    attributes: List['Attribute'] = None  # #[repr(C)], etc.
    where_clause: List[tuple[str, List[str]]] = None  # Where T: Trait1 + Trait2
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = []
        if self.where_clause is None:
            self.where_clause = []
    
    def has_attribute(self, name: str) -> bool:
        """Check if struct has a specific attribute"""
        return any(attr.name == name for attr in self.attributes)
    
    def is_repr_c(self) -> bool:
        """Check if struct has #[repr(C)] attribute"""
        return self.has_attribute("repr") and any(
            attr.name == "repr" and attr.args and attr.args[0] == "C" 
            for attr in self.attributes
        )


@dataclass
class Attribute(ASTNode):
    """Attribute: #[name] or #[name(args)]"""
    name: str
    args: List[str] = None  # Arguments like "C" in #[repr(C)]
    
    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class Field(ASTNode):
    """Struct field"""
    name: str
    type_annotation: 'Type'


@dataclass
class EnumDef(ASTNode):
    """Enum definition"""
    name: str
    generic_params: List['GenericParam']  # Type parameters: T, U
    compile_time_params: List[Any]  # Compile-time params: N: int, Flag: bool
    variants: List['Variant']


@dataclass
class Variant(ASTNode):
    """Enum variant"""
    name: str
    fields: Optional[List['Field']]  # None for unit variant


@dataclass
class TraitDef(ASTNode):
    """Trait definition: trait TraitName:"""
    name: str
    generic_params: List['GenericParam']
    methods: List['TraitMethod']  # Method signatures with optional default implementations
    associated_types: List['AssociatedType']  # Associated type declarations
    where_clause: List[tuple[str, List[str]]] = None  # Where T: Trait1 + Trait2
    
    def __post_init__(self):
        if self.where_clause is None:
            self.where_clause = []


@dataclass
class TraitMethod(ASTNode):
    """Method in a trait definition"""
    name: str
    params: List['Param']
    return_type: Optional['Type']
    default_body: Optional['Block']  # None if no default implementation
    generic_params: List['GenericParam'] = None
    compile_time_params: List[Any] = None


@dataclass
class AssociatedType(ASTNode):
    """Associated type in a trait: type Item"""
    name: str
    bounds: List[str]  # Trait bounds on the associated type


@dataclass
class ImplBlock(ASTNode):
    """Implementation block: impl TypeName: or impl Trait for TypeName:"""
    trait_name: Optional[str]  # None for inherent impl, Some for trait impl
    type_name: str
    generic_params: List['GenericParam']  # For generic implementations
    where_clause: List[tuple[str, List[str]]]  # Where T: Trait1 + Trait2
    methods: List['FunctionDef']
    associated_type_impls: List[tuple[str, 'Type']]  # (name, concrete_type)


@dataclass
class ConstDecl(ASTNode):
    """Constant declaration"""
    name: str
    type_annotation: Optional['Type']
    value: 'Expression'


@dataclass
class OpaqueTypeDecl(ASTNode):
    """Opaque type declaration: opaque type OpaqueHandle;"""
    name: str


@dataclass
class TypeAlias(ASTNode):
    """Type alias declaration: type Optional[T] = Option[T]"""
    name: str
    generic_params: List['GenericParam']  # Type parameters: T, U
    target_type: 'Type'  # The type this alias refers to


# Statements
@dataclass
class VarDecl(ASTNode):
    """Variable declaration: let/var pattern = value"""
    pattern: 'Pattern'
    mutable: bool  # True for 'var', False for 'let'
    type_annotation: Optional['Type']
    initializer: 'Expression'

    def __init__(self, pattern: 'Pattern' = None, mutable: bool = False, 
                 type_annotation: Optional['Type'] = None, initializer: 'Expression' = None,
                 span: Span = None, name: str = None):
        super().__init__(span)
        if name is not None and pattern is None:
            self.pattern = IdentifierPattern(name=name, span=span)
        else:
            self.pattern = pattern
        self.mutable = mutable
        self.type_annotation = type_annotation
        self.initializer = initializer

    @property
    def name(self) -> str:
        """Legacy access for simple identifier patterns"""
        if isinstance(self.pattern, IdentifierPattern):
            return self.pattern.name
        elif isinstance(self.pattern, TuplePattern):
            # Return first element name if possible, for legacy code that expects a name
            if self.pattern.elements and isinstance(self.pattern.elements[0], IdentifierPattern):
                return self.pattern.elements[0].name
        return "_"


@dataclass
class Assignment(ASTNode):
    """Assignment: x = value"""
    target: 'Expression'  # Lvalue
    value: 'Expression'


@dataclass
class ExpressionStmt(ASTNode):
    """Expression statement"""
    expression: 'Expression'


@dataclass
class ReturnStmt(ASTNode):
    """Return statement"""
    value: Optional['Expression']


@dataclass
class BreakStmt(ASTNode):
    """Break statement"""
    pass


@dataclass
class ContinueStmt(ASTNode):
    """Continue statement"""
    pass


@dataclass
class PassStmt(ASTNode):
    """Pass statement"""
    pass


@dataclass
class IfStmt(ASTNode):
    """If statement with elif and else"""
    condition: 'Expression'
    then_block: 'Block'
    elif_clauses: List[tuple['Expression', 'Block']]
    else_block: Optional['Block']


@dataclass
class WhileStmt(ASTNode):
    """While loop"""
    condition: 'Expression'
    body: 'Block'


@dataclass
class ForStmt(ASTNode):
    """For loop: for x in iterable:"""
    variable: str
    iterable: 'Expression'
    body: 'Block'


@dataclass
class MatchStmt(ASTNode):
    """Match statement"""
    scrutinee: 'Expression'
    arms: List['MatchArm']


@dataclass
class MatchArm(ASTNode):
    """Match arm"""
    pattern: 'Pattern'
    guard: Optional['Expression']
    body: 'Block'


@dataclass
class DeferStmt(ASTNode):
    """Defer statement"""
    body: 'Block'


@dataclass
class WithStmt(ASTNode):
    """With statement"""
    variable: str
    value: 'Expression'
    body: 'Block'


@dataclass
class UnsafeBlock(ASTNode):
    """Unsafe block"""
    body: 'Block'


@dataclass
class Block(ASTNode):
    """Block of statements"""
    statements: List['Statement']


# Expressions
@dataclass
class IntLiteral(ASTNode):
    """Integer literal"""
    value: int


@dataclass
class FloatLiteral(ASTNode):
    """Float literal"""
    value: float


@dataclass
class StringLiteral(ASTNode):
    """String literal"""
    value: str


@dataclass
class CharLiteral(ASTNode):
    """Character literal"""
    value: str


@dataclass
class BoolLiteral(ASTNode):
    """Boolean literal"""
    value: bool


@dataclass
class NoneLiteral(ASTNode):
    """None literal"""
    pass


@dataclass
class Identifier(ASTNode):
    """Identifier"""
    name: str


@dataclass
class BinOp(ASTNode):
    """Binary operation"""
    left: 'Expression'
    op: str  # "+", "-", "*", "==", etc.
    right: 'Expression'


@dataclass
class UnaryOp(ASTNode):
    """Unary operation"""
    op: str  # "not", "-", "&", "&mut", "*"
    operand: 'Expression'


@dataclass
class TernaryExpr(ASTNode):
    """Ternary expression: true_expr if condition else false_expr"""
    true_expr: 'Expression'
    condition: 'Expression'
    false_expr: 'Expression'


@dataclass
class AsExpression(ASTNode):
    """Cast expression: x as Type"""
    expression: 'Expression'
    target_type: 'Type'


@dataclass
class FunctionCall(ASTNode):
    """Function call"""
    function: 'Expression'
    compile_time_args: List[Any]  # Compile-time arguments: [256], [true]
    arguments: List['Expression']  # Runtime arguments


@dataclass
class MethodCall(ASTNode):
    """Method call: object.method(args)"""
    object: 'Expression'
    method: str
    arguments: List['Expression']


@dataclass
class FieldAccess(ASTNode):
    """Field access: object.field"""
    object: 'Expression'
    field: str


@dataclass
class IndexAccess(ASTNode):
    """Index access: array[index]"""
    object: 'Expression'
    index: 'Expression'


@dataclass
class SliceAccess(ASTNode):
    """Slice access: array[start..end]"""
    object: 'Expression'
    start: Optional['Expression']
    end: Optional['Expression']


@dataclass
class StructLiteral(ASTNode):
    """Struct literal: Point { x: 1, y: 2 }"""
    struct_name: str
    fields: List[tuple[str, 'Expression']]  # (field_name, value)


@dataclass
class TupleLiteral(ASTNode):
    """Tuple literal: (1, "a")"""
    elements: List['Expression']


@dataclass
class ListLiteral(ASTNode):
    """List literal: [1, 2, 3]"""
    elements: List['Expression']


@dataclass
class TryExpr(ASTNode):
    """Try expression for error propagation"""
    expression: 'Expression'


@dataclass
class ParameterClosure(ASTNode):
    """
    Parameter closure: fn[params] -> Type
    Compile-time only, always inlined, zero allocation
    """
    params: List['Param']
    return_type: Optional['Type']
    body: 'Block'
    is_move: bool = False
    # Compiler guarantees (set during type checking)
    can_inline: bool = True  # Must be True
    allocates: bool = False  # Must be False
    escapes: bool = False    # Must be False


@dataclass
class RuntimeClosure(ASTNode):
    """
    Runtime closure: fn(params) -> Type
    First-class value, can escape, may allocate
    """
    params: List['Param']
    return_type: Optional['Type']
    body: 'Block'
    is_move: bool = False  # True if 'move fn(...)'
    # Runtime properties (calculated during type checking)
    environment_size: int = 0  # Bytes for captured variables
    captures: List[str] = None  # Names of captured variables
    
    def __post_init__(self):
        if self.captures is None:
            self.captures = []


# Patterns
@dataclass
class LiteralPattern(ASTNode):
    """Literal pattern in match"""
    literal: 'Expression'  # Only literals allowed


@dataclass
class IdentifierPattern(ASTNode):
    """Identifier pattern (binds variable)"""
    name: str


@dataclass
class TuplePattern(ASTNode):
    """Tuple pattern: (a, b)"""
    elements: List['Pattern']


@dataclass
class WildcardPattern(ASTNode):
    """Wildcard pattern: _"""
    pass


@dataclass
class EnumPattern(ASTNode):
    """Enum variant pattern: Some(x) or Option::Some(x)"""
    enum_name: Optional[str]  # None for direct variant patterns like Some(_)
    variant_name: str
    fields: Optional[List['Pattern']]


@dataclass
class OrPattern(ASTNode):
    """Or pattern: 1 | 2 | 3"""
    patterns: List['Pattern']


# Types
@dataclass
class PrimitiveType(ASTNode):
    """Primitive type: int, f64, bool, etc."""
    name: str


@dataclass
class ReferenceType(ASTNode):
    """Reference type: &T or &mut T"""
    mutable: bool
    inner: 'Type'


@dataclass
class PointerType(ASTNode):
    """Raw pointer type: *T or *mut T"""
    mutable: bool
    inner: 'Type'


@dataclass
class ArrayType(ASTNode):
    """Array type: [T; N]"""
    element_type: 'Type'
    size: 'Expression'  # Must be constant


@dataclass
class SliceType(ASTNode):
    """Slice type: [T]"""
    element_type: 'Type'


@dataclass
class GenericType(ASTNode):
    """Generic type: List[T] or Map[K, V]"""
    name: str
    type_args: List['Type']


@dataclass
class FunctionType(ASTNode):
    """Function type: fn(int, int) -> int"""
    param_types: List['Type']
    return_type: Optional['Type']


@dataclass
class TupleType(ASTNode):
    """Tuple type: (int, String)"""
    element_types: List['Type']


@dataclass
class AssociatedTypeRef(ASTNode):
    """Associated type reference: Trait::Item or Self::Item"""
    trait_name: str  # Trait name or "Self"
    associated_type_name: str  # Associated type name (e.g., "Item")


# Type aliases for unions
Item = FunctionDef | StructDef | EnumDef | ImplBlock | ConstDecl | OpaqueTypeDecl | TypeAlias
Statement = (VarDecl | Assignment | ExpressionStmt | ReturnStmt | 
             BreakStmt | ContinueStmt | IfStmt | WhileStmt | ForStmt |
             MatchStmt | DeferStmt | WithStmt | UnsafeBlock)
# Expression types - GenericType can be used as expression for type.method() syntax
Expression = (IntLiteral | FloatLiteral | StringLiteral | CharLiteral |
              BoolLiteral | NoneLiteral | Identifier | BinOp | UnaryOp |
              TernaryExpr | FunctionCall | MethodCall | FieldAccess |
              IndexAccess | SliceAccess | StructLiteral | ListLiteral | TupleLiteral | TryExpr |
              GenericType | AsExpression)  # Allow GenericType as expression for Type[Args].method() syntax
Pattern = (LiteralPattern | IdentifierPattern | TuplePattern | WildcardPattern |
           EnumPattern | OrPattern)
Type = (PrimitiveType | ReferenceType | PointerType | ArrayType |
        SliceType | GenericType | FunctionType | TupleType | AssociatedTypeRef)

