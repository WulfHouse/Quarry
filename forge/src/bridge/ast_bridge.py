"""FFI bridge for ast.pyrite

This module provides a Python interface to the Pyrite AST implementation.
Currently, this is a placeholder that re-exports from the Python implementation.
Once ast.pyrite is fully compiled and linked, this will provide FFI bindings.

TODO: Implement actual FFI bindings when compilation infrastructure is ready.
"""

# For now, re-export from Python implementation to maintain compatibility
from ..ast import (
    ASTNode, Program, ImportStmt, FunctionDef, GenericParam,
    CompileTimeIntParam, CompileTimeBoolParam, CompileTimeFunctionParam,
    Param, StructDef, Attribute, Field, EnumDef, Variant, TraitDef,
    TraitMethod, AssociatedType, ImplBlock, ConstDecl, OpaqueTypeDecl,
    VarDecl, Assignment, ExpressionStmt, ReturnStmt, BreakStmt,
    ContinueStmt, IfStmt, WhileStmt, ForStmt, MatchStmt, MatchArm,
    DeferStmt, WithStmt, UnsafeBlock, Block,
    IntLiteral, FloatLiteral, StringLiteral, CharLiteral, BoolLiteral,
    NoneLiteral, Identifier, BinOp, UnaryOp, TernaryExpr, FunctionCall,
    MethodCall, FieldAccess, IndexAccess, SliceAccess, StructLiteral,
    ListLiteral, TryExpr, ParameterClosure, RuntimeClosure,
    LiteralPattern, IdentifierPattern, WildcardPattern, EnumPattern,
    OrPattern, PrimitiveType, ReferenceType, PointerType, ArrayType,
    SliceType, GenericType, FunctionType, TupleType, AssociatedTypeRef,
    Item, Statement, Expression, Pattern, Type
)

__all__ = [
    "ASTNode", "Program", "ImportStmt", "FunctionDef", "GenericParam",
    "CompileTimeIntParam", "CompileTimeBoolParam", "CompileTimeFunctionParam",
    "Param", "StructDef", "Attribute", "Field", "EnumDef", "Variant", "TraitDef",
    "TraitMethod", "AssociatedType", "ImplBlock", "ConstDecl", "OpaqueTypeDecl",
    "VarDecl", "Assignment", "ExpressionStmt", "ReturnStmt", "BreakStmt",
    "ContinueStmt", "IfStmt", "WhileStmt", "ForStmt", "MatchStmt", "MatchArm",
    "DeferStmt", "WithStmt", "UnsafeBlock", "Block",
    "IntLiteral", "FloatLiteral", "StringLiteral", "CharLiteral", "BoolLiteral",
    "NoneLiteral", "Identifier", "BinOp", "UnaryOp", "TernaryExpr", "FunctionCall",
    "MethodCall", "FieldAccess", "IndexAccess", "SliceAccess", "StructLiteral",
    "ListLiteral", "TryExpr", "ParameterClosure", "RuntimeClosure",
    "LiteralPattern", "IdentifierPattern", "WildcardPattern", "EnumPattern",
    "OrPattern", "PrimitiveType", "ReferenceType", "PointerType", "ArrayType",
    "SliceType", "GenericType", "FunctionType", "TupleType", "AssociatedTypeRef",
    "Item", "Statement", "Expression", "Pattern", "Type"
]
