"""Type system for Pyrite"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


class Type:
    """Base class for all types"""
    def __eq__(self, other):
        return type(self) == type(other)
    
    def __hash__(self):
        return hash(str(self))
    
    def __str__(self):
        return self.__class__.__name__


@dataclass
class IntType(Type):
    """Integer type: int, i8, i16, i32, i64, u8, u16, u32, u64"""
    width: int = 32  # Bit width
    signed: bool = True
    
    def __eq__(self, other):
        return isinstance(other, IntType) and self.width == other.width and self.signed == other.signed
    
    def __hash__(self):
        return hash(("int", self.width, self.signed))
    
    def __str__(self):
        if self.width == 32 and self.signed:
            return "int"
        prefix = "i" if self.signed else "u"
        return f"{prefix}{self.width}"


@dataclass
class FloatType(Type):
    """Float type: f32, f64"""
    width: int = 64  # 32 or 64
    
    def __eq__(self, other):
        return isinstance(other, FloatType) and self.width == other.width
    
    def __hash__(self):
        return hash(("float", self.width))
    
    def __str__(self):
        return f"f{self.width}"


class BoolType(Type):
    """Boolean type"""
    def __str__(self):
        return "bool"


class CharType(Type):
    """Character type (Unicode code point)"""
    def __str__(self):
        return "char"


class StringType(Type):
    """String type (immutable UTF-8)"""
    def __str__(self):
        return "String"


class VoidType(Type):
    """Void/unit type"""
    def __str__(self):
        return "void"


class NoneType(Type):
    """None type"""
    def __str__(self):
        return "None"


@dataclass
class ReferenceType(Type):
    """Reference type: &T or &mut T"""
    inner: Type
    mutable: bool = False
    
    def __eq__(self, other):
        return (isinstance(other, ReferenceType) and 
                self.inner == other.inner and 
                self.mutable == other.mutable)
    
    def __hash__(self):
        return hash(("ref", self.inner, self.mutable))
    
    def __str__(self):
        mut = "mut " if self.mutable else ""
        return f"&{mut}{self.inner}"


@dataclass
class PointerType(Type):
    """Raw pointer type: *T or *mut T"""
    inner: Type
    mutable: bool = False
    
    def __eq__(self, other):
        return (isinstance(other, PointerType) and 
                self.inner == other.inner and 
                self.mutable == other.mutable)
    
    def __hash__(self):
        return hash(("ptr", self.inner, self.mutable))
    
    def __str__(self):
        mut = "mut " if self.mutable else ""
        return f"*{mut}{self.inner}"


@dataclass
class ArrayType(Type):
    """Array type: [T; N]"""
    element: Type
    size: int
    
    def __eq__(self, other):
        return (isinstance(other, ArrayType) and 
                self.element == other.element and 
                self.size == other.size)
    
    def __hash__(self):
        return hash(("array", self.element, self.size))
    
    def __str__(self):
        return f"[{self.element}; {self.size}]"


@dataclass
class SliceType(Type):
    """Slice type: &[T]"""
    element: Type
    
    def __eq__(self, other):
        return isinstance(other, SliceType) and self.element == other.element
    
    def __hash__(self):
        return hash(("slice", self.element))
    
    def __str__(self):
        return f"&[{self.element}]"


@dataclass
class StructType(Type):
    """Struct type with fields"""
    name: str
    fields: Dict[str, Type]
    generic_params: List[str] = None
    
    def __post_init__(self):
        if self.generic_params is None:
            self.generic_params = []
    
    def __eq__(self, other):
        return isinstance(other, StructType) and self.name == other.name
    
    def __hash__(self):
        return hash(("struct", self.name))
    
    def __str__(self):
        if self.generic_params:
            params = ", ".join(self.generic_params)
            return f"{self.name}[{params}]"
        return self.name


@dataclass
@dataclass
class EnumType(Type):
    """Enum type with variants"""
    name: str
    variants: Dict[str, Optional[List[Type]]]  # variant_name -> field_types
    generic_params: List[str] = None
    
    def __post_init__(self):
        if self.generic_params is None:
            self.generic_params = []
    
    def __eq__(self, other):
        return isinstance(other, EnumType) and self.name == other.name
    
    def __hash__(self):
        return hash(("enum", self.name))
    
    def __str__(self):
        if self.generic_params:
            params = ", ".join(self.generic_params)
            return f"{self.name}[{params}]"
        return self.name


@dataclass
class GenericType(Type):
    """Generic type: List[T], Map[K, V]"""
    name: str
    base_type: Optional[Type]  # The struct/enum it's instantiated from
    type_args: List[Type]
    
    def __eq__(self, other):
        return (isinstance(other, GenericType) and 
                self.name == other.name and 
                self.type_args == other.type_args)
    
    def __hash__(self):
        return hash(("generic", self.name, tuple(self.type_args)))
    
    def __str__(self):
        args = ", ".join(str(t) for t in self.type_args)
        return f"{self.name}[{args}]"


@dataclass
class FunctionType(Type):
    """Function type: fn(T1, T2) -> R"""
    param_types: List[Type]
    return_type: Optional[Type]
    
    def __eq__(self, other):
        return (isinstance(other, FunctionType) and 
                self.param_types == other.param_types and 
                self.return_type == other.return_type)
    
    def __hash__(self):
        return hash(("fn", tuple(self.param_types), self.return_type))
    
    def __str__(self):
        params = ", ".join(str(t) for t in self.param_types)
        ret = f" -> {self.return_type}" if self.return_type else ""
        return f"fn({params}){ret}"


@dataclass
class TupleType(Type):
    """Tuple type: (T1, T2, ...)"""
    elements: List[Type]
    
    def __eq__(self, other):
        return isinstance(other, TupleType) and self.elements == other.elements
    
    def __hash__(self):
        return hash(("tuple", tuple(self.elements)))
    
    def __str__(self):
        elems = ", ".join(str(t) for t in self.elements)
        return f"({elems})"


class UnknownType(Type):
    """Unknown type (for error recovery)"""
    def __str__(self):
        return "?"


class TypeVariable(Type):
    """Type variable for generics"""
    def __init__(self, name: str):
        self.name = name
    
    def __eq__(self, other):
        return isinstance(other, TypeVariable) and self.name == other.name
    
    def __hash__(self):
        return hash(("typevar", self.name))
    
    def __str__(self):
        return self.name


class SelfType(Type):
    """Self type (refers to implementing type in traits)"""
    def __eq__(self, other):
        return isinstance(other, SelfType)
    
    def __hash__(self):
        return hash("Self")
    
    def __str__(self):
        return "Self"


@dataclass
class OpaqueType(Type):
    """Opaque type for FFI (non-dereferenceable pointer)"""
    name: str
    
    def __eq__(self, other):
        return isinstance(other, OpaqueType) and self.name == other.name
    
    def __hash__(self):
        return hash(("opaque", self.name))
    
    def __str__(self):
        return self.name


@dataclass
class TraitType(Type):
    """Trait type"""
    name: str
    methods: Dict[str, FunctionType]  # method_name -> method_type
    generic_params: List[str] = None
    associated_types: List[str] = None
    
    def __post_init__(self):
        if self.generic_params is None:
            self.generic_params = []
        if self.associated_types is None:
            self.associated_types = []
    
    def __eq__(self, other):
        return isinstance(other, TraitType) and self.name == other.name
    
    def __hash__(self):
        return hash(("trait", self.name))
    
    def __str__(self):
        if self.generic_params:
            params = ", ".join(self.generic_params)
            return f"{self.name}[{params}]"
        return self.name


# Built-in type instances
INT = IntType(32, True)
I8 = IntType(8, True)
I16 = IntType(16, True)
I32 = IntType(32, True)
I64 = IntType(64, True)
U8 = IntType(8, False)
U16 = IntType(16, False)
U32 = IntType(32, False)
U64 = IntType(64, False)
F32 = FloatType(32)
F64 = FloatType(64)
BOOL = BoolType()
CHAR = CharType()
STRING = StringType()
VOID = VoidType()
NONE = NoneType()
UNKNOWN = UnknownType()
SELF = SelfType()


def primitive_type_from_name(name: str) -> Optional[Type]:
    """Get primitive type from name"""
    type_map = {
        "int": INT,
        "i8": I8,
        "i16": I16,
        "i32": I32,
        "i64": I64,
        "u8": U8,
        "u16": U16,
        "u32": U32,
        "u64": U64,
        "float": F64,  # Alias for f64
        "f32": F32,
        "f64": F64,
        "bool": BOOL,
        "char": CHAR,
        "String": STRING,
        "void": VOID,
        "Self": SELF,
    }
    return type_map.get(name)


def is_copy_type(typ: Type) -> bool:
    """Check if a type is Copy (doesn't move on assignment)"""
    # Only primitive types and references are Copy
    # Structs, Enums, Arrays, Slices, Strings are Move types
    return isinstance(typ, (IntType, FloatType, BoolType, CharType, ReferenceType, PointerType))


def is_numeric_type(typ: Type) -> bool:
    """Check if type is numeric (int or float)"""
    return isinstance(typ, (IntType, FloatType))


def types_compatible(t1: Type, t2: Type) -> bool:
    """Check if two types are compatible for assignment/comparison"""
    if t1 == t2:
        return True
    
    # Allow implicit conversion between numeric types of same category
    if isinstance(t1, IntType) and isinstance(t2, IntType):
        # For now, require exact match
        return t1 == t2
    
    if isinstance(t1, FloatType) and isinstance(t2, FloatType):
        return t1 == t2
    
    # Unknown matches anything
    if isinstance(t1, UnknownType) or isinstance(t2, UnknownType):
        return True

    # Handle TypeVariables - they match any type (for generic parameters)
    if isinstance(t1, TypeVariable) or isinstance(t2, TypeVariable):
        return True

    # Handle GenericType compatibility
    if isinstance(t1, GenericType) and isinstance(t2, GenericType):
        if t1.name != t2.name:
            return False
        if len(t1.type_args) != len(t2.type_args):
            return False
        return all(types_compatible(a1, a2) for a1, a2 in zip(t1.type_args, t2.type_args))
    
    # Unknown matches anything
    if isinstance(t1, UnknownType) or isinstance(t2, UnknownType):
        return True
    
    # Handle generic enum constructor return types
    # When we have Result.Ok(42), it returns EnumType("Result", ...)
    # But the function expects GenericType("Result", base_type, [int, String])
    # They should be compatible if the names match and base_type is the EnumType
    if isinstance(t1, EnumType) and isinstance(t2, GenericType):
        if t1.name == t2.name and t2.base_type == t1:
            return True
    
    # Also handle the reverse case (GenericType to EnumType)
    if isinstance(t1, GenericType) and isinstance(t2, EnumType):
        if t1.name == t2.name and t1.base_type == t2:
            return True
    
    # Handle List to Array compatibility (for literals)
    if isinstance(t1, ArrayType) and isinstance(t2, GenericType) and t2.name == "List":
        return types_compatible(t1.element, t2.type_args[0])
    
    if isinstance(t1, GenericType) and t1.name == "List" and isinstance(t2, ArrayType):
        return types_compatible(t1.type_args[0], t2.element)

    return False


def common_numeric_type(t1: Type, t2: Type) -> Optional[Type]:
    """Get common numeric type for binary operations"""
    if not (is_numeric_type(t1) and is_numeric_type(t2)):
        return None
    
    # If either is float, result is float
    if isinstance(t1, FloatType) or isinstance(t2, FloatType):
        # Return the larger float type
        if isinstance(t1, FloatType) and isinstance(t2, FloatType):
            return F64 if t1.width == 64 or t2.width == 64 else F32
        elif isinstance(t1, FloatType):
            return t1
        else:
            return t2
    
    # Both are integers - return the larger type
    if isinstance(t1, IntType) and isinstance(t2, IntType):
        # For MVP, just return int for simplicity
        return INT
    
    return None

