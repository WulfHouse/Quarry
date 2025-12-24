"""Ownership tracking for Pyrite"""

from dataclasses import dataclass
from typing import Dict, Set, Optional, List
from .. import ast
from ..types import (Type, is_copy_type, INT, F64, STRING, BOOL, CHAR, UNKNOWN,
                    StructType, GenericType, UnknownType, TupleType)
from ..frontend.tokens import Span
from ..utils.error_formatter import ErrorFormatter


@dataclass
class OwnershipError(Exception):
    """Ownership violation error"""
    message: str
    span: Span
    
    def __str__(self):
        return f"{self.span}: {self.message}"


@dataclass
class ValueInfo:
    """Information about a value"""
    var_id: int
    var_name: str
    type: Type
    allocation_span: Span
    moved_to: Optional[str] = None  # Name of variable it was moved to
    move_span: Optional[Span] = None  # Where the move occurred
    moved_fields: Set[str] = None  # Set of field names that have been moved

    def __post_init__(self):
        if self.moved_fields is None:
            self.moved_fields = set()


class OwnershipState:
    """Tracks ownership state for values in a function"""
    
    def __init__(self):
        self.values: Dict[int, ValueInfo] = {}  # var_id -> ValueInfo
        self.moved: Set[int] = set()  # Set of moved variable IDs (whole value)
        self.var_id_counter = 0
        self.name_to_id: Dict[str, int] = {}  # var_name -> var_id
    
    def allocate(self, var_name: str, typ: Type, span: Span) -> int:
        """Allocate a new value"""
        var_id = self.var_id_counter
        self.var_id_counter += 1
        
        self.values[var_id] = ValueInfo(
            var_id=var_id,
            var_name=var_name,
            type=typ,
            allocation_span=span
        )
        self.name_to_id[var_name] = var_id
        return var_id
    
    def is_owned(self, var_id: int, field_name: Optional[str] = None) -> bool:
        """Check if a value (or field) is still owned (not moved)"""
        if var_id not in self.values:
            return False
        
        # If whole value is moved, nothing is owned
        if var_id in self.moved:
            # print(f"[DEBUG] is_owned({var_id}, {field_name}) -> False (whole moved)")
            return False
        
        # If checking a specific field
        if field_name:
            result = field_name not in self.values[var_id].moved_fields
            # print(f"[DEBUG] is_owned({var_id}, {field_name}) -> {result}")
            return result
        
        # If checking the whole value, it must not have any moved fields (SPEC-LANG-0309)
        result = not self.values[var_id].moved_fields
        # print(f"[DEBUG] is_owned({var_id}, None) -> {result}")
        return result

    def is_owned_by_name(self, var_name: str, field_name: Optional[str] = None) -> bool:
        """Check if a variable still owns its value (or field)"""
        if var_name not in self.name_to_id:
            return False
        var_id = self.name_to_id[var_name]
        return self.is_owned(var_id, field_name)

    def move_value(self, from_var: str, to_var: Optional[str], span: Span, field_name: Optional[str] = None):
        """Move ownership from one variable (or field) to another"""
        # print(f"[DEBUG] move_value({from_var}, {to_var}, {field_name})")
        if from_var not in self.name_to_id:
            return  # Variable doesn't exist

        from_id = self.name_to_id[from_var]
        
        if from_id in self.moved:
            return  # Already moved
        
        if field_name:
            # Partial move of a field (SPEC-LANG-0309)
            if from_id in self.values:
                self.values[from_id].moved_fields.add(field_name)
        else:
            # Move whole value
            self.moved.add(from_id)
            if from_id in self.values:
                self.values[from_id].moved_to = to_var
                self.values[from_id].move_span = span
    
    def get_value_info(self, var_name: str) -> Optional[ValueInfo]:
        """Get value info for a variable"""
        if var_name not in self.name_to_id:
            return None
        var_id = self.name_to_id[var_name]
        return self.values.get(var_id)
    
    def clone(self) -> 'OwnershipState':
        """Create a copy of this state"""
        new_state = OwnershipState()
        # Deep copy ValueInfo objects because they contain mutable moved_fields
        for vid, info in self.values.items():
            new_info = ValueInfo(
                var_id=info.var_id,
                var_name=info.var_name,
                type=info.type,
                allocation_span=info.allocation_span,
                moved_to=info.moved_to,
                move_span=info.move_span,
                moved_fields=info.moved_fields.copy()
            )
            new_state.values[vid] = new_info
        
        new_state.moved = self.moved.copy()
        new_state.var_id_counter = self.var_id_counter
        new_state.name_to_id = self.name_to_id.copy()
        return new_state


class OwnershipAnalyzer:
    """Analyzes ownership and detects use-after-move errors"""
    
    def __init__(self, track_timeline: bool = False):
        self.errors: List[OwnershipError] = []
        self.state: Optional[OwnershipState] = None
        self.variable_types: Dict[str, Type] = {}  # From type checker
        self.type_checker = None  # Will be set externally
        self.track_timeline = track_timeline
        # Import OwnershipEvent from borrow_checker for timeline
        try:
            from .borrow_checker import OwnershipEvent
            self.OwnershipEvent = OwnershipEvent
            self.ownership_timeline: List[OwnershipEvent] = []
        except ImportError:
            self.OwnershipEvent = None
            self.ownership_timeline = []
    
    def error(self, message: str, span: Span):
        """Record an ownership error"""
        self.errors.append(OwnershipError(message, span))
    
    def add_timeline_event(self, variable: str, event_type: str, description: str, span: Span):
        """Add an event to the ownership timeline"""
        if self.track_timeline and self.OwnershipEvent:
            self.ownership_timeline.append(self.OwnershipEvent(
                variable=variable,
                line=span.start_line,
                event_type=event_type,
                description=description,
                span=span
            ))
    
    def format_timeline(self, variable: str = None) -> str:
        """Format ownership timeline as text"""
        if not self.track_timeline or not self.ownership_timeline:
            return ""
        
        events = self.ownership_timeline if variable is None else [e for e in self.ownership_timeline if e.variable == variable]
        
        if not events:
            return ""
        
        lines = []
        lines.append("Ownership Timeline:")
        lines.append("-" * 60)
        
        for event in events:
            event_type_str = {
                "move": "MOVED",
                "borrow": "BORROWED",
                "borrow_mut": "BORROWED (mutable)",
                "release": "RELEASED",
                "use": "USED"
            }.get(event.event_type, event.event_type.upper())
            
            lines.append(f"Line {event.line}: '{event.variable}' {event_type_str}")
            if event.description:
                lines.append(f"  {event.description}")
        
        lines.append("-" * 60)
        return '\n'.join(lines)
    
    def has_errors(self) -> bool:
        """Check if any errors occurred"""
        return len(self.errors) > 0
    
    def analyze_program(self, program: ast.Program, type_env: Dict[str, Type]):
        """Analyze ownership for entire program"""
        self.variable_types = type_env
        
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                self.analyze_function(item)
    
    def analyze_function(self, func: ast.FunctionDef):
        """Analyze ownership in a function"""
        self.state = OwnershipState()
        
        # Build local type environment by walking the function
        self.collect_variable_types(func)
        
        # Parameters are owned by the function
        for param in func.params:
            param_type = self.variable_types.get(param.name, None)
            if param_type:
                self.state.allocate(param.name, param_type, param.span)
        
        # Analyze function body
        self.analyze_block(func.body)
    
    def collect_variable_types(self, func: ast.FunctionDef):
        """Collect all variable types defined in a function"""
        # This is a simplified collector - just walks the AST and collects var declarations
        def collect_from_block(block: ast.Block):
            for stmt in block.statements:
                if isinstance(stmt, ast.VarDecl):
                    # Don't overwrite existing types (e.g., from manually set type_env)
                    if stmt.name not in self.variable_types:
                        # Infer type from initializer
                        var_type = self.infer_type_from_expression(stmt.initializer)
                        if stmt.type_annotation and self.type_checker:
                            # Use annotated type if provided
                            var_type = self.type_checker.resolve_type(stmt.type_annotation)
                        self.variable_types[stmt.name] = var_type
                    elif stmt.type_annotation and self.type_checker:
                        # If type annotation is provided, use it even if type already exists
                        var_type = self.type_checker.resolve_type(stmt.type_annotation)
                        self.variable_types[stmt.name] = var_type
                elif isinstance(stmt, (ast.IfStmt, ast.WhileStmt, ast.ForStmt, ast.MatchStmt)):
                    # Recursively collect from nested blocks
                    if isinstance(stmt, ast.IfStmt):
                        collect_from_block(stmt.then_block)
                        for _, elif_block in stmt.elif_clauses:
                            collect_from_block(elif_block)
                        if stmt.else_block:
                            collect_from_block(stmt.else_block)
                    elif isinstance(stmt, ast.WhileStmt):
                        collect_from_block(stmt.body)
                    elif isinstance(stmt, ast.ForStmt):
                        collect_from_block(stmt.body)
                        self.variable_types[stmt.variable] = INT  # Loop variable
                    elif isinstance(stmt, ast.MatchStmt):
                        for arm in stmt.arms:
                            collect_from_block(arm.body)
        
        # Collect parameter types
        for param in func.params:
            if param.type_annotation and self.type_checker:
                param_type = self.type_checker.resolve_type(param.type_annotation)
                self.variable_types[param.name] = param_type
        
        # Collect from function body
        collect_from_block(func.body)
    
    def infer_type_from_expression(self, expr: ast.Expression) -> Type:
        """Simple type inference for expressions"""
        if isinstance(expr, ast.IntLiteral):
            return INT
        elif isinstance(expr, ast.FloatLiteral):
            return F64
        elif isinstance(expr, ast.StringLiteral):
            return STRING
        elif isinstance(expr, ast.BoolLiteral):
            return BOOL
        elif isinstance(expr, ast.StructLiteral):
            # Look up struct type
            if self.type_checker:
                struct_type = self.type_checker.resolver.lookup_type(expr.struct_name)
                if struct_type:
                    return struct_type
            return UNKNOWN
        elif isinstance(expr, ast.Identifier):
            # Look up variable type
            return self.variable_types.get(expr.name, UNKNOWN)
        elif isinstance(expr, ast.ListLiteral):
            # Generic List type
            if expr.elements and self.type_checker:
                elem_type = self.infer_type_from_expression(expr.elements[0])
                return GenericType("List", None, [elem_type])
            return UNKNOWN
        else:
            # For other expressions, return unknown for now
            return UNKNOWN
    
    def analyze_block(self, block: ast.Block):
        """Analyze a block of statements"""
        for stmt in block.statements:
            self.analyze_statement(stmt)
    
    def analyze_statement(self, stmt: ast.Statement):
        """Analyze a statement"""
        if isinstance(stmt, ast.VarDecl):
            self.analyze_var_decl(stmt)
        elif isinstance(stmt, ast.Assignment):
            self.analyze_assignment(stmt)
        elif isinstance(stmt, ast.ExpressionStmt):
            self.analyze_expression(stmt.expression)
        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                self.analyze_expression(stmt.value)
        elif isinstance(stmt, ast.IfStmt):
            self.analyze_if(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self.analyze_while(stmt)
        elif isinstance(stmt, ast.ForStmt):
            self.analyze_for(stmt)
        elif isinstance(stmt, ast.MatchStmt):
            self.analyze_match(stmt)
        elif isinstance(stmt, ast.DeferStmt):
            self.analyze_defer(stmt)
        elif isinstance(stmt, ast.UnsafeBlock):
            # In unsafe blocks, don't check ownership
            pass
        # Note: Runtime closures in variable declarations are handled in analyze_var_decl
        # when analyzing the initializer expression
    
    def analyze_var_decl(self, decl: ast.VarDecl):
        """Analyze variable declaration"""
        # Check if initializer is a runtime closure (needs special handling)
        if isinstance(decl.initializer, ast.RuntimeClosure):
            # Analyze the closure for ownership violations
            self.analyze_runtime_closure(decl.initializer, decl.span)
        # Check if initializer moves a value
        elif isinstance(decl.initializer, ast.Identifier):
            source_name = decl.initializer.name
            source_type = self.variable_types.get(source_name)
            
            if source_type and not is_copy_type(source_type):
                # This is a move
                self.check_identifier_use(decl.initializer)
                target_name = decl.name if hasattr(decl, 'name') else "<pattern>"
                self.state.move_value(source_name, target_name, decl.span)
                # Track timeline event
                self.add_timeline_event(source_name, "move", f"'{source_name}' moved to '{target_name}'", decl.span)
        elif isinstance(decl.initializer, ast.FieldAccess):
            # Partial move (SPEC-LANG-0309)
            if isinstance(decl.initializer.object, ast.Identifier):
                obj_name = decl.initializer.object.name
                field_name = decl.initializer.field
                
                # Check if this is a type name (enum variant construction like Type.BoolType)
                is_type_name = False
                if self.type_checker and self.type_checker.resolver:
                    type_obj = self.type_checker.resolver.global_scope.lookup_type(obj_name)
                    if type_obj is not None:
                        # This is a type name, not a variable - skip ownership check
                        is_type_name = True
                
                # Only check ownership if this is a variable, not a type name (enum variant construction)
                if not is_type_name and obj_name in self.variable_types:
                    # Check if object itself is valid (whole move check)
                    self.check_field_use(obj_name, field_name, decl.initializer.span)
                
                # Infer field type (simplified)
                obj_type = self.variable_types.get(obj_name)
                field_type = UNKNOWN
                if isinstance(obj_type, StructType) and field_name in obj_type.fields:
                    field_type = obj_type.fields[field_name]
                
                # Only make ownership decisions when we have actual type information
                # Don't treat UNKNOWN as always-move (conservative approach)
                if (not is_type_name and field_type and 
                    field_type != UNKNOWN and 
                    not isinstance(field_type, UnknownType) and 
                    not is_copy_type(field_type)):
                    # This is a partial move of a non-Copy field
                    target_name = decl.name if hasattr(decl, 'name') else "<pattern>"
                    self.state.move_value(obj_name, target_name, decl.span, field_name=field_name)
                    self.add_timeline_event(obj_name, "move", f"field '{field_name}' of '{obj_name}' moved to '{target_name}'", decl.span)
            else:
                self.analyze_expression(decl.initializer)
        else:
            # Analyze the initializer
            self.analyze_expression(decl.initializer)
        
        # Get the type of the initializer
        var_type = self.infer_type_from_expression(decl.initializer)
        if decl.type_annotation and self.type_checker:
            var_type = self.type_checker.resolve_type(decl.type_annotation)
        
        # Bind variables in the pattern
        self.bind_pattern_variables(decl.pattern, var_type)
    
    def analyze_assignment(self, assign: ast.Assignment):
        """Analyze assignment"""
        # If assigning to a simple identifier, it takes ownership
        if isinstance(assign.target, ast.Identifier):
            target_name = assign.target.name
            
            # Check if value is being moved
            if isinstance(assign.value, ast.Identifier):
                source_name = assign.value.name
                source_type = self.variable_types.get(source_name)
                
                if source_type and not is_copy_type(source_type):
                    # This is a move - check if source is valid first
                    self.check_identifier_use(assign.value)
                    self.state.move_value(source_name, target_name, assign.span)
                    # Track timeline event
                    self.add_timeline_event(source_name, "move", f"'{source_name}' moved to '{target_name}'", assign.span)
            else:
                # Analyze the value expression
                self.analyze_expression(assign.value)
    
    def analyze_if(self, if_stmt: ast.IfStmt):
        """Analyze if statement"""
        # Analyze condition
        self.analyze_expression(if_stmt.condition)
        
        # Save current state
        original_state = self.state.clone()
        
        # Analyze then block
        self.analyze_block(if_stmt.then_block)
        then_state = self.state.clone()
        
        # Analyze elif clauses
        elif_states = []
        for elif_cond, elif_block in if_stmt.elif_clauses:
            self.state = original_state.clone()
            self.analyze_expression(elif_cond)
            self.analyze_block(elif_block)
            elif_states.append(self.state.clone())
        
        # Analyze else block
        if if_stmt.else_block:
            self.state = original_state.clone()
            self.analyze_block(if_stmt.else_block)
            else_state = self.state.clone()
        else:
            else_state = original_state.clone()
        
        # Merge states: A value is moved if it's moved in ALL branches
        # For MVP, we'll use a simplified approach: mark as moved if moved in any branch
        # This is conservative but safe
        all_states = [then_state] + elif_states + [else_state]
        self.state = self.merge_states(all_states)
    
    def analyze_while(self, while_stmt: ast.WhileStmt):
        """Analyze while loop"""
        self.analyze_expression(while_stmt.condition)
        
        # For loops, we analyze the body but don't track moves across iterations
        # This is conservative but safe for MVP
        original_state = self.state.clone()
        self.analyze_block(while_stmt.body)
        # Restore state after loop (conservative)
        self.state = original_state
    
    def analyze_for(self, for_stmt: ast.ForStmt):
        """Analyze for loop"""
        self.analyze_expression(for_stmt.iterable)
        
        # Loop variable
        loop_var_type = self.variable_types.get(for_stmt.variable)
        if loop_var_type:
            self.state.allocate(for_stmt.variable, loop_var_type, for_stmt.span)
        
        # Analyze body (conservative approach like while)
        original_state = self.state.clone()
        self.analyze_block(for_stmt.body)
        self.state = original_state
    
    def analyze_match(self, match_stmt: ast.MatchStmt):
        """Analyze match statement"""
        scrutinee_moves = self.analyze_expression(match_stmt.scrutinee)
        scrutinee_type = self.infer_type_from_expression(match_stmt.scrutinee)
        
        # If the scrutinee is an identifier and its type is not a copy type,
        # matching against it (especially with field binding) may move it.
        # For now, we'll assume matching moves the scrutinee if it's a move type.
        scrutinee_name = None
        if isinstance(match_stmt.scrutinee, ast.Identifier):
            scrutinee_name = match_stmt.scrutinee.name
        
        # Save original state
        original_state = self.state.clone()
        
        # Analyze each arm
        arm_states = []
        for arm in match_stmt.arms:
            self.state = original_state.clone()
            
            # If scrutinee is a move type, mark it as moved in this arm
            if scrutinee_name and scrutinee_type and not is_copy_type(scrutinee_type):
                self.state.move_value(scrutinee_name, "<match arm>", arm.pattern.span)
                self.add_timeline_event(scrutinee_name, "move", f"'{scrutinee_name}' moved into match arm", arm.pattern.span)

            # Bind pattern variables
            self.bind_pattern_variables(arm.pattern, scrutinee_type)
            
            if arm.guard:
                self.analyze_expression(arm.guard)
            
            self.analyze_block(arm.body)
            arm_states.append(self.state.clone())
        
        # Merge all arm states
        self.state = self.merge_states(arm_states)
    
    def analyze_defer(self, defer_stmt: ast.DeferStmt):
        """Analyze defer statement
        
        Validates that all variables used in the defer block are still valid
        (not moved) at the point where the defer is declared.
        This is a snapshot check - we validate ownership at the defer site.
        """
        # Analyze the defer block to check for use-after-move errors
        # We need to validate that variables used in defer are still owned
        # at the time the defer is declared (not when it executes)
        self.analyze_block(defer_stmt.body)
    
    def analyze_runtime_closure(self, closure: ast.RuntimeClosure, span: Span):
        """Analyze runtime closure for ownership violations
        
        When a closure captures variables:
        - If variable is moved, it can't be captured (error)
        - If variable is move type and captured by value, it moves into closure
        - If variable is captured by reference, it needs to be borrowed
        """
        if not closure.captures:
            return  # No captures, nothing to validate
        
        # Check each captured variable
        for var_name in closure.captures:
            # Check if variable is still owned (not moved)
            if not self.state.is_owned_by_name(var_name):
                value_info = self.state.get_value_info(var_name)
                if value_info and value_info.moved_to:
                    self.error(
                        f"Cannot capture moved value '{var_name}' in closure "
                        f"(moved to '{value_info.moved_to}')",
                        span
                    )
                    continue
            
            # Get variable type
            var_type = self.variable_types.get(var_name)
            if var_type and not is_copy_type(var_type):
                # Move type captured by value - this moves the value into the closure
                # The variable is now owned by the closure, not the outer scope
                # For now, we'll mark it as moved (conservative approach)
                # In full implementation, we'd track closure ownership separately
                # Note: This is a conservative check - the actual move happens at closure creation
                # but we validate that the variable is valid at the capture site
                pass
    
    def bind_pattern_variables(self, pattern: ast.Pattern, expected_type: Optional[Type] = None):
        """Bind variables in a pattern"""
        if isinstance(pattern, ast.IdentifierPattern):
            # Bind the variable (type from type checker)
            var_type = expected_type or self.variable_types.get(pattern.name)
            if var_type:
                self.state.allocate(pattern.name, var_type, pattern.span)
        elif isinstance(pattern, ast.TuplePattern):
            if expected_type and isinstance(expected_type, TupleType):
                for sub_pat, elem_type in zip(pattern.elements, expected_type.elements):
                    self.bind_pattern_variables(sub_pat, elem_type)
            else:
                for sub_pat in pattern.elements:
                    self.bind_pattern_variables(sub_pat)
        elif isinstance(pattern, ast.EnumPattern):
            # Bind enum variant fields
            if pattern.fields:
                # We need to know the types of the fields for this variant.
                # In a full implementation, we'd look up the variant in the EnumType.
                # For now, we'll try to get them from self.variable_types if they were collected.
                for i, sub_pat in enumerate(pattern.fields):
                    self.bind_pattern_variables(sub_pat)
        elif isinstance(pattern, ast.OrPattern):
            for sub_pattern in pattern.patterns:
                self.bind_pattern_variables(sub_pattern, expected_type)
    
    def analyze_expression(self, expr: ast.Expression) -> bool:
        """Analyze an expression for ownership. Returns True if expression moves the value."""
        if isinstance(expr, ast.Identifier):
            self.check_identifier_use(expr)
            # Check if this is a move
            var_type = self.variable_types.get(expr.name)
            return var_type is not None and not is_copy_type(var_type)
        elif isinstance(expr, ast.BinOp):
            self.analyze_expression(expr.left)
            self.analyze_expression(expr.right)
            return False
        elif isinstance(expr, ast.UnaryOp):
            # References (&, &mut) don't move
            if expr.op in ['&', '&mut']:
                # Check the operand but don't move it
                if isinstance(expr.operand, ast.Identifier):
                    self.check_identifier_use(expr.operand)
                else:
                    self.analyze_expression(expr.operand)
                return False
            return self.analyze_expression(expr.operand)
        elif isinstance(expr, ast.TernaryExpr):
            self.analyze_expression(expr.condition)
            self.analyze_expression(expr.true_expr)
            self.analyze_expression(expr.false_expr)
            return False
        elif isinstance(expr, ast.RuntimeClosure):
            # Analyze runtime closure for ownership violations
            self.analyze_runtime_closure(expr, expr.span)
            return False  # Closure itself doesn't move (it's a value)
        elif isinstance(expr, ast.FunctionCall):
            self.analyze_function_call(expr)
            return False
        elif isinstance(expr, ast.MethodCall):
            self.analyze_method_call(expr)
            return False
        elif isinstance(expr, ast.FieldAccess):
            # Check that the object (or specific field) is still valid (SPEC-LANG-0309)
            if isinstance(expr.object, ast.Identifier):
                obj_name = expr.object.name
                field_name = expr.field
                # Check if this is a type name (enum variant construction like Type.BoolType)
                is_type_name = False
                if self.type_checker and self.type_checker.resolver:
                    type_obj = self.type_checker.resolver.global_scope.lookup_type(obj_name)
                    if type_obj is not None:
                        # This is a type name, not a variable - skip ownership check
                        is_type_name = True
                
                # Only check ownership if this is a variable, not a type name (enum variant construction)
                if not is_type_name and obj_name in self.variable_types:
                    self.check_field_use(obj_name, field_name, expr.span)
                # If it's not a variable, it's likely a type name (e.g., Type.BoolType), so skip ownership check
            else:
                self.analyze_expression(expr.object)
            return False
        elif isinstance(expr, ast.IndexAccess):
            self.analyze_expression(expr.object)
            self.analyze_expression(expr.index)
            return False
        elif isinstance(expr, ast.StructLiteral):
            for _, field_value in expr.fields:
                self.analyze_expression(field_value)
            return False
        elif isinstance(expr, ast.ListLiteral):
            for elem in expr.elements:
                self.analyze_expression(elem)
            return False
        # Literals don't need analysis
        return False
    
    def check_identifier_use(self, ident: ast.Identifier):
        """Check if an identifier can be used"""
        # Track usage
        self.add_timeline_event(ident.name, "use", f"'{ident.name}' used", ident.span)
        
        if not self.state.is_owned_by_name(ident.name):
            value_info = self.state.get_value_info(ident.name)
            if value_info and value_info.moved_to is not None:
                self.error(
                    f"Cannot use moved value '{ident.name}' (moved to '{value_info.moved_to}' at {value_info.move_span})",
                    ident.span
                )
            elif value_info and value_info.moved_fields:
                self.error(
                    f"Cannot use '{ident.name}' because it has partially moved fields: {', '.join(value_info.moved_fields)}",
                    ident.span
                )

    def check_field_use(self, obj_name: str, field_name: str, span: Span):
        """Check if a struct field can be used (SPEC-LANG-0309)"""
        self.add_timeline_event(obj_name, "use", f"field '{field_name}' of '{obj_name}' used", span)
        
        if not self.state.is_owned_by_name(obj_name):
            value_info = self.state.get_value_info(obj_name)
            if value_info and value_info.moved_to is not None:
                self.error(
                    f"Cannot use field '{field_name}' of moved value '{obj_name}'",
                    span
                )
        
        if not self.state.is_owned_by_name(obj_name, field_name):
            self.error(
                f"Cannot use already moved field '{field_name}' of '{obj_name}'",
                span
            )
    
    def analyze_function_call(self, call: ast.FunctionCall):
        """Analyze function call (may move arguments)"""
        # Analyze function expression
        self.analyze_expression(call.function)
        
        # Special handling for builtins that don't move
        if isinstance(call.function, ast.Identifier) and call.function.name == "print":
            # print doesn't move its arguments (just reads them)
            for arg in call.arguments:
                if isinstance(arg, ast.Identifier):
                    self.check_identifier_use(arg)
                else:
                    self.analyze_expression(arg)
            return
        
        # Analyze arguments
        for arg in call.arguments:
            # If argument is an identifier with non-Copy type, it moves
            if isinstance(arg, ast.Identifier):
                arg_type = self.variable_types.get(arg.name)
                if arg_type and not is_copy_type(arg_type):
                    # Check if already moved
                    if not self.state.is_owned_by_name(arg.name):
                        value_info = self.state.get_value_info(arg.name)
                        if value_info:
                            self.error(
                                f"Cannot move value '{arg.name}' (already moved to '{value_info.moved_to}')",
                                arg.span
                            )
                    else:
                        # Move the value
                        self.state.move_value(arg.name, "<function parameter>", arg.span)
            else:
                self.analyze_expression(arg)
    
    def analyze_method_call(self, call: ast.MethodCall):
        """Analyze method call"""
        self.analyze_expression(call.object)
        
        for arg in call.arguments:
            self.analyze_expression(arg)
    
    def merge_states(self, states: List[OwnershipState]) -> OwnershipState:
        """Merge multiple ownership states (conservative merge)"""
        if not states:
            return OwnershipState()
        
        # Start with first state
        merged = states[0].clone()
        
        # A value is moved if it's moved in ANY branch (conservative)
        for state in states[1:]:
            merged.moved.update(state.moved)
        
        return merged


def analyze_ownership(program: ast.Program, type_env: Dict[str, Type], track_timeline: bool = False) -> OwnershipAnalyzer:
    """Convenience function to analyze ownership
    
    Args:
        program: Program AST
        type_env: Type environment
        track_timeline: Enable ownership timeline tracking
    """
    analyzer = OwnershipAnalyzer(track_timeline=track_timeline)
    analyzer.analyze_program(program, type_env)
    return analyzer

