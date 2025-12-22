"""Tests for types.py"""

import pytest

pytestmark = pytest.mark.fast  # Type tests are fast unit tests
from src.types import (
    Type, IntType, FloatType, BoolType, CharType, StringType, VoidType, NoneType,
    ReferenceType, PointerType, ArrayType, SliceType, StructType, EnumType,
    GenericType, FunctionType, TupleType, UnknownType, TypeVariable, SelfType,
    OpaqueType, TraitType,
    INT, I8, I16, I32, I64, U8, U16, U32, U64, F32, F64, BOOL, CHAR, STRING,
    VOID, NONE, UNKNOWN, SELF,
    primitive_type_from_name, is_copy_type, is_numeric_type, types_compatible,
    common_numeric_type
)


def test_int_type_default():
    """Test IntType with default values"""
    int_type = IntType()
    assert int_type.width == 32
    assert int_type.signed == True
    assert str(int_type) == "int"


def test_int_type_custom():
    """Test IntType with custom width and signed"""
    int_type = IntType(64, False)
    assert int_type.width == 64
    assert int_type.signed == False
    assert str(int_type) == "u64"


def test_int_type_equality():
    """Test IntType equality"""
    assert IntType(32, True) == IntType(32, True)
    assert IntType(32, True) != IntType(64, True)
    assert IntType(32, True) != IntType(32, False)


def test_int_type_hash():
    """Test IntType hashing"""
    assert hash(IntType(32, True)) == hash(IntType(32, True))
    assert hash(IntType(32, True)) != hash(IntType(64, True))


def test_float_type_default():
    """Test FloatType with default values"""
    float_type = FloatType()
    assert float_type.width == 64
    assert str(float_type) == "f64"


def test_float_type_custom():
    """Test FloatType with custom width"""
    float_type = FloatType(32)
    assert float_type.width == 32
    assert str(float_type) == "f32"


def test_float_type_equality():
    """Test FloatType equality"""
    assert FloatType(32) == FloatType(32)
    assert FloatType(32) != FloatType(64)


def test_bool_type():
    """Test BoolType"""
    bool_type = BoolType()
    assert str(bool_type) == "bool"
    assert isinstance(bool_type, Type)


def test_char_type():
    """Test CharType"""
    char_type = CharType()
    assert str(char_type) == "char"
    assert isinstance(char_type, Type)


def test_string_type():
    """Test StringType"""
    string_type = StringType()
    assert str(string_type) == "String"
    assert isinstance(string_type, Type)


def test_void_type():
    """Test VoidType"""
    void_type = VoidType()
    assert str(void_type) == "void"
    assert isinstance(void_type, Type)


def test_none_type():
    """Test NoneType"""
    none_type = NoneType()
    assert str(none_type) == "None"
    assert isinstance(none_type, Type)


def test_reference_type_immutable():
    """Test ReferenceType with immutable reference"""
    ref_type = ReferenceType(INT, False)
    assert ref_type.inner == INT
    assert ref_type.mutable == False
    assert str(ref_type) == "&int"


def test_reference_type_mutable():
    """Test ReferenceType with mutable reference"""
    ref_type = ReferenceType(INT, True)
    assert ref_type.inner == INT
    assert ref_type.mutable == True
    assert str(ref_type) == "&mut int"


def test_reference_type_equality():
    """Test ReferenceType equality"""
    assert ReferenceType(INT, False) == ReferenceType(INT, False)
    assert ReferenceType(INT, False) != ReferenceType(INT, True)
    assert ReferenceType(INT, False) != ReferenceType(STRING, False)


def test_pointer_type():
    """Test PointerType"""
    ptr_type = PointerType(INT, False)
    assert ptr_type.inner == INT
    assert ptr_type.mutable == False
    assert str(ptr_type) == "*int"


def test_pointer_type_mutable():
    """Test PointerType with mutable pointer"""
    ptr_type = PointerType(INT, True)
    assert ptr_type.mutable == True
    assert str(ptr_type) == "*mut int"


def test_pointer_type_equality():
    """Test PointerType equality"""
    assert PointerType(INT, False) == PointerType(INT, False)
    assert PointerType(INT, False) != PointerType(INT, True)


def test_array_type():
    """Test ArrayType"""
    array_type = ArrayType(INT, 10)
    assert array_type.element == INT
    assert array_type.size == 10
    assert str(array_type) == "[int; 10]"


def test_array_type_equality():
    """Test ArrayType equality"""
    assert ArrayType(INT, 10) == ArrayType(INT, 10)
    assert ArrayType(INT, 10) != ArrayType(STRING, 10)
    assert ArrayType(INT, 10) != ArrayType(INT, 20)


def test_slice_type():
    """Test SliceType"""
    slice_type = SliceType(INT)
    assert slice_type.element == INT
    assert str(slice_type) == "&[int]"


def test_slice_type_equality():
    """Test SliceType equality"""
    assert SliceType(INT) == SliceType(INT)
    assert SliceType(INT) != SliceType(STRING)


def test_struct_type():
    """Test StructType"""
    struct_type = StructType("Point", {"x": INT, "y": INT})
    assert struct_type.name == "Point"
    assert struct_type.fields == {"x": INT, "y": INT}
    assert str(struct_type) == "Point"


def test_struct_type_with_generics():
    """Test StructType with generic parameters"""
    struct_type = StructType("List", {}, ["T"])
    assert struct_type.generic_params == ["T"]
    assert str(struct_type) == "List[T]"


def test_struct_type_str_empty_generics():
    """Test StructType.__str__() with empty generic_params (covers line 175)"""
    struct_type = StructType("Point", {}, [])  # Empty list
    assert str(struct_type) == "Point"  # Should return name, not "Point[]"


def test_struct_type_equality():
    """Test StructType equality (by name only)"""
    assert StructType("Point", {}) == StructType("Point", {"x": INT})
    assert StructType("Point", {}) != StructType("Line", {})


def test_enum_type():
    """Test EnumType"""
    enum_type = EnumType("Option", {"Some": [INT], "None": None})
    assert enum_type.name == "Option"
    assert enum_type.variants == {"Some": [INT], "None": None}
    assert str(enum_type) == "Option"


def test_enum_type_with_generics():
    """Test EnumType with generic parameters"""
    enum_type = EnumType("Result", {"Ok": [INT], "Err": [STRING]}, ["T", "E"])
    assert enum_type.generic_params == ["T", "E"]
    assert str(enum_type) == "Result[T, E]"


def test_enum_type_str_empty_generics():
    """Test EnumType.__str__() with empty generic_params (covers line 199)"""
    enum_type = EnumType("Option", {}, [])  # Empty list
    assert str(enum_type) == "Option"  # Should return name, not "Option[]"


def test_enum_type_equality():
    """Test EnumType equality (by name only)"""
    assert EnumType("Option", {}) == EnumType("Option", {"Some": [INT]})
    assert EnumType("Option", {}) != EnumType("Result", {})


def test_generic_type():
    """Test GenericType"""
    base = StructType("List", {})
    generic_type = GenericType("List", base, [INT])
    assert generic_type.name == "List"
    assert generic_type.base_type == base
    assert generic_type.type_args == [INT]
    assert str(generic_type) == "List[int]"


def test_generic_type_multiple_args():
    """Test GenericType with multiple type arguments"""
    base = EnumType("Result", {})
    generic_type = GenericType("Result", base, [INT, STRING])
    assert str(generic_type) == "Result[int, String]"


def test_generic_type_equality():
    """Test GenericType equality"""
    base = StructType("List", {})
    assert GenericType("List", base, [INT]) == GenericType("List", base, [INT])
    assert GenericType("List", base, [INT]) != GenericType("List", base, [STRING])


def test_function_type():
    """Test FunctionType"""
    func_type = FunctionType([INT, STRING], BOOL)
    assert func_type.param_types == [INT, STRING]
    assert func_type.return_type == BOOL
    assert str(func_type) == "fn(int, String) -> bool"


def test_function_type_no_return():
    """Test FunctionType with no return type"""
    func_type = FunctionType([INT], None)
    assert func_type.return_type is None
    assert str(func_type) == "fn(int)"


def test_function_type_equality():
    """Test FunctionType equality"""
    assert FunctionType([INT], BOOL) == FunctionType([INT], BOOL)
    assert FunctionType([INT], BOOL) != FunctionType([STRING], BOOL)
    assert FunctionType([INT], BOOL) != FunctionType([INT], STRING)


def test_tuple_type():
    """Test TupleType"""
    tuple_type = TupleType([INT, STRING, BOOL])
    assert tuple_type.elements == [INT, STRING, BOOL]
    assert str(tuple_type) == "(int, String, bool)"


def test_tuple_type_equality():
    """Test TupleType equality"""
    assert TupleType([INT, STRING]) == TupleType([INT, STRING])
    assert TupleType([INT, STRING]) != TupleType([STRING, INT])


def test_unknown_type():
    """Test UnknownType"""
    unknown_type = UnknownType()
    assert str(unknown_type) == "?"
    assert isinstance(unknown_type, Type)


def test_type_variable():
    """Test TypeVariable"""
    type_var = TypeVariable("T")
    assert type_var.name == "T"
    assert str(type_var) == "T"


def test_type_variable_equality():
    """Test TypeVariable equality"""
    assert TypeVariable("T") == TypeVariable("T")
    assert TypeVariable("T") != TypeVariable("U")


def test_self_type():
    """Test SelfType"""
    self_type = SelfType()
    assert str(self_type) == "Self"
    assert isinstance(self_type, Type)


def test_self_type_equality():
    """Test SelfType equality"""
    assert SelfType() == SelfType()


def test_opaque_type():
    """Test OpaqueType"""
    opaque_type = OpaqueType("CFile")
    assert opaque_type.name == "CFile"
    assert str(opaque_type) == "CFile"


def test_opaque_type_equality():
    """Test OpaqueType equality"""
    assert OpaqueType("CFile") == OpaqueType("CFile")
    assert OpaqueType("CFile") != OpaqueType("CHandle")


def test_trait_type():
    """Test TraitType"""
    trait_type = TraitType("Iterator", {})
    assert trait_type.name == "Iterator"
    assert trait_type.methods == {}
    assert trait_type.generic_params == []
    assert trait_type.associated_types == []
    assert str(trait_type) == "Iterator"


def test_trait_type_with_generics():
    """Test TraitType with generic parameters"""
    trait_type = TraitType("Iterator", {}, ["Item"])
    assert trait_type.generic_params == ["Item"]
    assert str(trait_type) == "Iterator[Item]"


def test_trait_type_str_empty_generics():
    """Test TraitType.__str__() with empty generic_params (covers line 330)"""
    trait_type = TraitType("Clone", {}, [])  # Empty list
    assert str(trait_type) == "Clone"  # Should return name, not "Clone[]"


def test_trait_type_with_associated_types():
    """Test TraitType with associated types"""
    trait_type = TraitType("Iterator", {}, None, ["Item"])
    assert trait_type.associated_types == ["Item"]


def test_trait_type_equality():
    """Test TraitType equality (by name only)"""
    assert TraitType("Iterator", {}) == TraitType("Iterator", {"next": FunctionType([], INT)})
    assert TraitType("Iterator", {}) != TraitType("Clone", {})


def test_builtin_type_instances():
    """Test built-in type instances"""
    assert isinstance(INT, IntType)
    assert isinstance(F32, FloatType)
    assert isinstance(F64, FloatType)
    assert isinstance(BOOL, BoolType)
    assert isinstance(CHAR, CharType)
    assert isinstance(STRING, StringType)
    assert isinstance(VOID, VoidType)
    assert isinstance(NONE, NoneType)
    assert isinstance(UNKNOWN, UnknownType)
    assert isinstance(SELF, SelfType)


def test_primitive_type_from_name():
    """Test primitive_type_from_name()"""
    assert primitive_type_from_name("int") == INT
    assert primitive_type_from_name("i8") == I8
    assert primitive_type_from_name("i16") == I16
    assert primitive_type_from_name("i32") == I32
    assert primitive_type_from_name("i64") == I64
    assert primitive_type_from_name("u8") == U8
    assert primitive_type_from_name("u16") == U16
    assert primitive_type_from_name("u32") == U32
    assert primitive_type_from_name("u64") == U64
    assert primitive_type_from_name("f32") == F32
    assert primitive_type_from_name("f64") == F64
    assert primitive_type_from_name("bool") == BOOL
    assert primitive_type_from_name("char") == CHAR
    assert primitive_type_from_name("String") == STRING
    assert primitive_type_from_name("void") == VOID
    assert primitive_type_from_name("Self") == SELF
    assert primitive_type_from_name("unknown") is None


def test_is_copy_type():
    """Test is_copy_type()"""
    assert is_copy_type(INT) == True
    assert is_copy_type(F32) == True
    assert is_copy_type(BOOL) == True
    assert is_copy_type(CHAR) == True
    assert is_copy_type(ReferenceType(INT, False)) == True
    assert is_copy_type(PointerType(INT, False)) == True
    assert is_copy_type(STRING) == False
    assert is_copy_type(StructType("Point", {})) == False
    assert is_copy_type(ArrayType(INT, 10)) == False


def test_is_numeric_type():
    """Test is_numeric_type()"""
    assert is_numeric_type(INT) == True
    assert is_numeric_type(I8) == True
    assert is_numeric_type(F32) == True
    assert is_numeric_type(F64) == True
    assert is_numeric_type(BOOL) == False
    assert is_numeric_type(STRING) == False
    assert is_numeric_type(CHAR) == False


def test_types_compatible_same_type():
    """Test types_compatible() with same types"""
    assert types_compatible(INT, INT) == True
    assert types_compatible(STRING, STRING) == True
    assert types_compatible(BOOL, BOOL) == True


def test_types_compatible_different_int_types():
    """Test types_compatible() with different IntTypes"""
    assert types_compatible(INT, I64) == False  # Different widths
    assert types_compatible(INT, U32) == False  # Different signedness


def test_types_compatible_different_float_types():
    """Test types_compatible() with different FloatTypes"""
    assert types_compatible(F32, F64) == False  # Different widths


def test_types_compatible_type_variable():
    """Test types_compatible() with TypeVariable"""
    assert types_compatible(TypeVariable("T"), INT) == True
    assert types_compatible(INT, TypeVariable("T")) == True
    assert types_compatible(TypeVariable("T"), TypeVariable("U")) == True


def test_types_compatible_enum_to_generic():
    """Test types_compatible() with EnumType to GenericType"""
    enum_type = EnumType("Result", {"Ok": [INT], "Err": [STRING]})
    generic_type = GenericType("Result", enum_type, [INT, STRING])
    assert types_compatible(enum_type, generic_type) == True


def test_types_compatible_generic_to_enum():
    """Test types_compatible() with GenericType to EnumType"""
    enum_type = EnumType("Result", {"Ok": [INT], "Err": [STRING]})
    generic_type = GenericType("Result", enum_type, [INT, STRING])
    assert types_compatible(generic_type, enum_type) == True


def test_types_compatible_incompatible():
    """Test types_compatible() with incompatible types"""
    assert types_compatible(INT, STRING) == False
    assert types_compatible(BOOL, INT) == False


def test_common_numeric_type_both_int():
    """Test common_numeric_type() with both integers"""
    assert common_numeric_type(INT, I64) == INT  # Returns INT for MVP


def test_common_numeric_type_both_float():
    """Test common_numeric_type() with both floats"""
    assert common_numeric_type(F32, F32) == F32
    assert common_numeric_type(F32, F64) == F64  # Larger float
    assert common_numeric_type(F64, F32) == F64


def test_common_numeric_type_int_and_float():
    """Test common_numeric_type() with int and float"""
    assert common_numeric_type(INT, F32) == F32
    assert common_numeric_type(F64, INT) == F64


def test_common_numeric_type_non_numeric():
    """Test common_numeric_type() with non-numeric types"""
    assert common_numeric_type(INT, STRING) is None
    assert common_numeric_type(BOOL, INT) is None


def test_type_base_class():
    """Test Type base class methods"""
    # Test that Type.__eq__ works
    assert Type() != IntType()
    assert Type().__str__() == "Type"
    
    # Test that Type.__hash__ works
    assert hash(Type()) == hash(str(Type()))


def test_struct_type_post_init_none():
    """Test StructType.__post_init__() with None generic_params (covers line 162)"""
    struct_type = StructType("Test", {}, None)
    assert struct_type.generic_params == []


def test_enum_type_post_init_none():
    """Test EnumType.__post_init__() with None generic_params (covers line 186)"""
    enum_type = EnumType("Test", {}, None)
    assert enum_type.generic_params == []


def test_trait_type_post_init_none():
    """Test TraitType.__post_init__() with None generic_params and associated_types (covers lines 315-318)"""
    trait_type = TraitType("Test", {}, None, None)
    assert trait_type.generic_params == []
    assert trait_type.associated_types == []


def test_int_type_str_custom_widths():
    """Test IntType.__str__() with various custom widths (covers lines 34-35)"""
    assert str(IntType(8, True)) == "i8"
    assert str(IntType(16, True)) == "i16"
    assert str(IntType(64, True)) == "i64"
    assert str(IntType(8, False)) == "u8"
    assert str(IntType(16, False)) == "u16"
    assert str(IntType(32, False)) == "u32"
    assert str(IntType(64, False)) == "u64"


def test_common_numeric_type_float_widths():
    """Test common_numeric_type() with different float widths (covers lines 430-435)"""
    # Test F32 and F64 combinations
    assert common_numeric_type(F32, F32) == F32  # Both F32 -> F32 (else branch of line 431)
    assert common_numeric_type(F64, F64) == F64  # Both F64 -> F64
    assert common_numeric_type(F32, F64) == F64  # F32 and F64 -> F64 (t1.width == 64 or t2.width == 64)
    assert common_numeric_type(F64, F32) == F64  # F64 and F32 -> F64
    # Test when one is float and one is int (covers lines 432-435)
    assert common_numeric_type(F32, INT) == F32  # F32 and int -> F32 (line 433)
    assert common_numeric_type(INT, F64) == F64  # int and F64 -> F64 (line 435)


def test_float_type_hash():
    """Test FloatType.__hash__ (covers line 47)"""
    assert hash(FloatType(32)) == hash(FloatType(32))
    assert hash(FloatType(32)) != hash(FloatType(64))


def test_reference_type_hash():
    """Test ReferenceType.__hash__ (covers line 95)"""
    assert hash(ReferenceType(INT, False)) == hash(ReferenceType(INT, False))
    assert hash(ReferenceType(INT, False)) != hash(ReferenceType(INT, True))
    assert hash(ReferenceType(INT, False)) != hash(ReferenceType(STRING, False))


def test_pointer_type_hash():
    """Test PointerType.__hash__ (covers line 114)"""
    assert hash(PointerType(INT, False)) == hash(PointerType(INT, False))
    assert hash(PointerType(INT, False)) != hash(PointerType(INT, True))


def test_array_type_hash():
    """Test ArrayType.__hash__ (covers line 133)"""
    assert hash(ArrayType(INT, 10)) == hash(ArrayType(INT, 10))
    assert hash(ArrayType(INT, 10)) != hash(ArrayType(INT, 20))
    assert hash(ArrayType(INT, 10)) != hash(ArrayType(STRING, 10))


def test_slice_type_hash():
    """Test SliceType.__hash__ (covers line 148)"""
    assert hash(SliceType(INT)) == hash(SliceType(INT))
    assert hash(SliceType(INT)) != hash(SliceType(STRING))


def test_struct_type_hash():
    """Test StructType.__hash__ (covers line 169)"""
    assert hash(StructType("Point", {})) == hash(StructType("Point", {"x": INT}))
    assert hash(StructType("Point", {})) != hash(StructType("Line", {}))


def test_enum_type_hash():
    """Test EnumType.__hash__ (covers line 193)"""
    assert hash(EnumType("Option", {})) == hash(EnumType("Option", {"Some": [INT]}))
    assert hash(EnumType("Option", {})) != hash(EnumType("Result", {}))


def test_generic_type_hash():
    """Test GenericType.__hash__ (covers line 215)"""
    base = StructType("List", {})
    assert hash(GenericType("List", base, [INT])) == hash(GenericType("List", base, [INT]))
    assert hash(GenericType("List", base, [INT])) != hash(GenericType("List", base, [STRING]))


def test_function_type_hash():
    """Test FunctionType.__hash__ (covers line 234)"""
    assert hash(FunctionType([INT], BOOL)) == hash(FunctionType([INT], BOOL))
    assert hash(FunctionType([INT], BOOL)) != hash(FunctionType([STRING], BOOL))
    assert hash(FunctionType([INT], BOOL)) != hash(FunctionType([INT], STRING))


def test_tuple_type_hash():
    """Test TupleType.__hash__ (covers line 251)"""
    assert hash(TupleType([INT, STRING])) == hash(TupleType([INT, STRING]))
    assert hash(TupleType([INT, STRING])) != hash(TupleType([STRING, INT]))


def test_type_variable_hash():
    """Test TypeVariable.__hash__ (covers line 273)"""
    assert hash(TypeVariable("T")) == hash(TypeVariable("T"))
    assert hash(TypeVariable("T")) != hash(TypeVariable("U"))


def test_self_type_hash():
    """Test SelfType.__hash__ (covers line 285)"""
    assert hash(SelfType()) == hash(SelfType())


def test_opaque_type_hash():
    """Test OpaqueType.__hash__ (covers line 300)"""
    assert hash(OpaqueType("CFile")) == hash(OpaqueType("CFile"))
    assert hash(OpaqueType("CFile")) != hash(OpaqueType("CHandle"))


def test_trait_type_hash():
    """Test TraitType.__hash__ (covers line 324)"""
    assert hash(TraitType("Iterator", {})) == hash(TraitType("Iterator", {"next": FunctionType([], INT)}))
    assert hash(TraitType("Iterator", {})) != hash(TraitType("Clone", {}))


def test_common_numeric_type_both_int_return():
    """Test common_numeric_type() with both integers returns INT (covers line 442)"""
    assert common_numeric_type(INT, I64) == INT
    assert common_numeric_type(I8, I16) == INT
