"""AST pass for automatic derivation of traits (@derive)

This pass scans for @derive(Trait) attributes on structs and enums
and generates the corresponding impl blocks.
"""

from typing import List, Optional
from .. import ast
from ..frontend.tokens import Span

class DerivePass:
    """AST pass that generates impl blocks for @derive attributes"""
    
    def derive_program(self, program: ast.Program) -> ast.Program:
        """Process all items in a program and add derived impl blocks"""
        new_items = []
        for item in program.items:
            new_items.append(item)
            if isinstance(item, ast.StructDef):
                derived_impls = self._derive_struct(item)
                new_items.extend(derived_impls)
        
        return ast.Program(
            imports=program.imports,
            items=new_items,
            span=program.span
        )

    def _derive_struct(self, struct: ast.StructDef) -> List[ast.ImplBlock]:
        """Generate impl blocks for a struct based on @derive attributes"""
        impls = []
        for attr in struct.attributes:
            if attr.name == "derive":
                for trait_name in attr.args:
                    if trait_name == "Serialize":
                        impls.append(self._generate_serialize_struct(struct))
                    elif trait_name == "Deserialize":
                        impls.append(self._generate_deserialize_struct(struct))
        return impls

    def _generate_serialize_struct(self, struct: ast.StructDef) -> ast.ImplBlock:
        """Generate 'impl Serialize for StructName'"""
        # fn serialize[S: Serializer](&self, serializer: &mut S) -> Result[bool, String]
        
        statements = []
        span = struct.span
        
        # serializer.serialize_map_start(len(struct.fields))?
        serialize_map_start = ast.TryExpr(
            expression=ast.MethodCall(
                object=ast.Identifier(name="serializer", span=span),
                method="serialize_map_start",
                arguments=[ast.IntLiteral(value=len(struct.fields), span=span)],
                span=span
            ),
            span=span
        )
        statements.append(ast.ExpressionStmt(expression=serialize_map_start, span=span))
        
        for field in struct.fields:
            # serializer.serialize_str("field_name")?
            serialize_key = ast.TryExpr(
                expression=ast.MethodCall(
                    object=ast.Identifier(name="serializer", span=span),
                    method="serialize_str",
                    arguments=[ast.StringLiteral(value=field.name, span=span)],
                    span=span
                ),
                span=span
            )
            statements.append(ast.ExpressionStmt(expression=serialize_key, span=span))
            
            # self.field_name.serialize(serializer)?
            serialize_val = ast.TryExpr(
                expression=ast.MethodCall(
                    object=ast.FieldAccess(
                        object=ast.Identifier(name="self", span=span),
                        field=field.name,
                        span=span
                    ),
                    method="serialize",
                    arguments=[ast.Identifier(name="serializer", span=span)],
                    span=span
                ),
                span=span
            )
            statements.append(ast.ExpressionStmt(expression=serialize_val, span=span))
            
        # serializer.serialize_map_end()?
        serialize_map_end = ast.TryExpr(
            expression=ast.MethodCall(
                object=ast.Identifier(name="serializer", span=span),
                method="serialize_map_end",
                arguments=[],
                span=span
            ),
            span=span
        )
        statements.append(ast.ExpressionStmt(expression=serialize_map_end, span=span))
        
        # return Ok(true)
        ok_true = ast.FunctionCall(
            function=ast.Identifier(name="Ok", span=span),
            compile_time_args=[],
            arguments=[ast.BoolLiteral(value=True, span=span)],
            span=span
        )
        statements.append(ast.ReturnStmt(value=ok_true, span=span))
        
        # fn serialize[S: Serializer](&self, serializer: &mut S) -> Result[bool, String]
        serialize_method = ast.FunctionDef(
            name="serialize",
            generic_params=[ast.GenericParam(name="S", trait_bounds=["Serializer"], span=span)],
            compile_time_params=[],
            params=[
                ast.Param(name="self", type_annotation=ast.ReferenceType(mutable=False, inner=ast.PrimitiveType(name=struct.name, span=span), span=span), span=span),
                ast.Param(name="serializer", type_annotation=ast.ReferenceType(mutable=True, inner=ast.PrimitiveType(name="S", span=span), span=span), span=span)
            ],
            return_type=ast.GenericType(name="Result", type_args=[ast.PrimitiveType(name="bool", span=span), ast.PrimitiveType(name="String", span=span)], span=span),
            body=ast.Block(statements=statements, span=span),
            span=span
        )
        
        return ast.ImplBlock(
            trait_name="Serialize",
            type_name=struct.name,
            generic_params=[],
            where_clause=[],
            methods=[serialize_method],
            associated_type_impls=[],
            span=span
        )

    def _generate_deserialize_struct(self, struct: ast.StructDef) -> ast.ImplBlock:
        """Generate 'impl Deserialize for StructName'"""
        # fn deserialize[D: Deserializer](deserializer: &mut D) -> Result[Self, String]
        
        span = struct.span
        statements = []
        
        # Placeholder implementation for MVP
        error_msg = ast.StringLiteral(value=f"Deserialization for {struct.name} not yet implemented via @derive", span=span)
        err_call = ast.FunctionCall(
            function=ast.Identifier(name="Err", span=span),
            compile_time_args=[],
            arguments=[error_msg],
            span=span
        )
        statements.append(ast.ReturnStmt(value=err_call, span=span))
        
        deserialize_method = ast.FunctionDef(
            name="deserialize",
            generic_params=[ast.GenericParam(name="D", trait_bounds=["Deserializer"], span=span)],
            compile_time_params=[],
            params=[
                ast.Param(name="deserializer", type_annotation=ast.ReferenceType(mutable=True, inner=ast.PrimitiveType(name="D", span=span), span=span), span=span)
            ],
            return_type=ast.GenericType(name="Result", type_args=[ast.PrimitiveType(name=struct.name, span=span), ast.PrimitiveType(name="String", span=span)], span=span),
            body=ast.Block(statements=statements, span=span),
            span=span
        )
        
        return ast.ImplBlock(
            trait_name="Deserialize",
            type_name=struct.name,
            generic_params=[],
            where_clause=[],
            methods=[deserialize_method],
            associated_type_impls=[],
            span=span
        )

