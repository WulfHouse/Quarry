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
        
        # Deserialize each field in order
        # This is a simplified implementation that deserializes fields sequentially
        # A full implementation would match field names from a map structure
        field_vars = []
        for field in struct.fields:
            # Generate: let field_name_val = FieldType::deserialize(deserializer)?
            # Since we don't have full type information in the AST at this stage,
            # we'll generate code that assumes the field type implements Deserialize
            # and can be deserialized via a static method or trait method
            
            field_var_name = f"{field.name}_val"
            
            # For each field, call deserialize on the field type
            # This assumes: FieldType::deserialize(deserializer) or field_type.deserialize(deserializer)
            # Since we don't have the field type in the AST, we'll use a pattern that
            # assumes the deserializer can handle the field type directly
            
            # Simplified: assume deserializer has methods for common types
            # In a full implementation, we'd inspect field.type_annotation and generate
            # appropriate deserialization calls (deserialize_str, deserialize_i64, etc.)
            
            # For MVP, generate code that calls deserialize_str (most common case)
            # This can be extended to handle other types based on field.type_annotation
            deserialize_field = ast.TryExpr(
                expression=ast.MethodCall(
                    object=ast.Identifier(name="deserializer", span=span),
                    method="deserialize_str",  # Simplified - full impl would check field type
                    arguments=[],
                    span=span
                ),
                span=span
            )
            
            # let field_name_val = deserializer.deserialize_str()?
            field_var = ast.LetStmt(
                name=field_var_name,
                type_annotation=None,  # Type inference
                value=deserialize_field,
                span=span
            )
            statements.append(field_var)
            field_vars.append((field.name, field_var_name))
        
        # Build struct literal with deserialized fields
        # return Ok(StructName { field1: field1_val, field2: field2_val, ... })
        struct_fields = []
        for field_name, var_name in field_vars:
            struct_fields.append(ast.StructField(
                name=field_name,
                value=ast.Identifier(name=var_name, span=span),
                span=span
            ))
        
        struct_literal = ast.StructLiteral(
            type_name=struct.name,
            fields=struct_fields,
            span=span
        )
        
        ok_result = ast.FunctionCall(
            function=ast.Identifier(name="Ok", span=span),
            compile_time_args=[],
            arguments=[struct_literal],
            span=span
        )
        statements.append(ast.ReturnStmt(value=ok_result, span=span))
        
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

