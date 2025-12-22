"""Borrow checker for Pyrite"""

from dataclasses import dataclass
from typing import Dict, Set, Optional, List, Tuple
from .. import ast
from ..types import Type, ReferenceType, is_copy_type
from ..frontend.tokens import Span


@dataclass
class BorrowError(Exception):
    """Borrow checking error"""
    message: str
    span: Span
    related_spans: List[Tuple[str, Span]] = None
    
    def __post_init__(self):
        if self.related_spans is None:
            self.related_spans = []
    
    def __str__(self):
        msg = f"{self.span}: {self.message}"
        for note, span in self.related_spans:
            msg += f"\n  note: {note} at {span}"
        return msg


@dataclass
class Borrow:
    """Represents an active borrow"""
    variable: str  # Variable being borrowed
    mutable: bool
    borrow_span: Span  # Where the borrow was created
    last_use_span: Span  # Where the borrow was last used


@dataclass
class OwnershipEvent:
    """Represents an ownership event in the timeline"""
    variable: str
    line: int
    event_type: str  # "move", "borrow", "borrow_mut", "release", "use"
    description: str
    span: Span


class BorrowState:
    """Tracks active borrows in current scope"""
    
    def __init__(self):
        self.active_borrows: List[Borrow] = []
        self.parent: Optional['BorrowState'] = None
    
    def add_borrow(self, variable: str, mutable: bool, span: Span) -> Borrow:
        """Add a new borrow"""
        borrow = Borrow(
            variable=variable,
            mutable=mutable,
            borrow_span=span,
            last_use_span=span
        )
        self.active_borrows.append(borrow)
        return borrow
    
    def get_active_borrows(self, variable: str) -> List[Borrow]:
        """Get all active borrows of a variable"""
        borrows = [b for b in self.active_borrows if b.variable == variable]
        if self.parent:
            borrows.extend(self.parent.get_active_borrows(variable))
        return borrows
    
    def check_borrow_conflict(self, variable: str, mutable: bool, span: Span) -> Optional[Borrow]:
        """Check if a new borrow would conflict with existing borrows"""
        existing = self.get_active_borrows(variable)
        
        for borrow in existing:
            # Conflict if:
            # 1. New borrow is mutable (exclusive access required)
            # 2. Existing borrow is mutable (already has exclusive access)
            if mutable or borrow.mutable:
                return borrow  # Conflict found
        
        return None  # No conflict
    
    def end_borrow(self, borrow: Borrow):
        """Mark a borrow as ended"""
        if borrow in self.active_borrows:
            self.active_borrows.remove(borrow)
    
    def clone(self) -> 'BorrowState':
        """Create a copy of this state"""
        new_state = BorrowState()
        new_state.active_borrows = self.active_borrows.copy()
        new_state.parent = self.parent
        return new_state
    
    def enter_scope(self) -> 'BorrowState':
        """Create child scope"""
        child = BorrowState()
        child.parent = self
        return child


class BorrowChecker:
    """Checks borrowing rules and lifetimes"""
    
    def __init__(self, track_timeline: bool = False):
        self.errors: List[BorrowError] = []
        self.state: Optional[BorrowState] = None
        self.variable_types: Dict[str, Type] = {}
        self.type_checker = None
        self.track_timeline = track_timeline
        self.ownership_timeline: List[OwnershipEvent] = []  # Timeline of ownership events
    
    def error(self, message: str, span: Span, related: List[Tuple[str, Span]] = None):
        """Record a borrow error"""
        if related is None:
            related = []
        self.errors.append(BorrowError(message, span, related))
    
    def add_timeline_event(self, variable: str, event_type: str, description: str, span: Span):
        """Add an event to the ownership timeline"""
        if self.track_timeline:
            self.ownership_timeline.append(OwnershipEvent(
                variable=variable,
                line=span.start_line,
                event_type=event_type,
                description=description,
                span=span
            ))
    
    def get_timeline_for_variable(self, variable: str) -> List[OwnershipEvent]:
        """Get timeline events for a specific variable"""
        return [e for e in self.ownership_timeline if e.variable == variable]
    
    def format_timeline(self, variable: str = None) -> str:
        """Format ownership timeline as text"""
        events = self.ownership_timeline if variable is None else self.get_timeline_for_variable(variable)
        
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
    
    def check_program(self, program: ast.Program, type_env: Dict[str, Type]):
        """Check borrowing for entire program"""
        self.variable_types = type_env
        
        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                self.check_function(item)
    
    def check_function(self, func: ast.FunctionDef):
        """Check borrowing in a function"""
        self.state = BorrowState()
        
        # Collect all variable types in function
        self.collect_variable_types(func)
        
        # Check function body
        self.check_block(func.body)
    
    def collect_variable_types(self, func: ast.FunctionDef):
        """Collect variable types (similar to ownership analyzer)"""
        def collect_from_block(block: ast.Block):
            for stmt in block.statements:
                if isinstance(stmt, ast.VarDecl):
                    var_type = self.infer_type(stmt.initializer)
                    if stmt.type_annotation and self.type_checker:
                        var_type = self.type_checker.resolve_type(stmt.type_annotation)
                    self.variable_types[stmt.name] = var_type
                elif isinstance(stmt, (ast.IfStmt, ast.WhileStmt, ast.ForStmt, ast.MatchStmt)):
                    if isinstance(stmt, ast.IfStmt):
                        collect_from_block(stmt.then_block)
                        for _, block in stmt.elif_clauses:
                            collect_from_block(block)
                        if stmt.else_block:
                            collect_from_block(stmt.else_block)
                    elif isinstance(stmt, ast.WhileStmt):
                        collect_from_block(stmt.body)
                    elif isinstance(stmt, ast.ForStmt):
                        collect_from_block(stmt.body)
                    elif isinstance(stmt, ast.MatchStmt):
                        for arm in stmt.arms:
                            collect_from_block(arm.body)
        
        for param in func.params:
            if param.type_annotation and self.type_checker:
                self.variable_types[param.name] = self.type_checker.resolve_type(param.type_annotation)
        
        collect_from_block(func.body)
    
    def infer_type(self, expr: ast.Expression) -> Type:
        """Simple type inference"""
        from ..types import INT, F64, STRING, BOOL, UNKNOWN, StructType, GenericType
        
        if isinstance(expr, ast.IntLiteral):
            return INT
        elif isinstance(expr, ast.FloatLiteral):
            return F64
        elif isinstance(expr, ast.StringLiteral):
            return STRING
        elif isinstance(expr, ast.BoolLiteral):
            return BOOL
        elif isinstance(expr, ast.StructLiteral):
            if self.type_checker:
                return self.type_checker.resolver.lookup_type(expr.struct_name) or UNKNOWN
            return UNKNOWN
        elif isinstance(expr, ast.Identifier):
            return self.variable_types.get(expr.name, UNKNOWN)
        return UNKNOWN
    
    def check_block(self, block: ast.Block):
        """Check a block of statements"""
        for stmt in block.statements:
            self.check_statement(stmt)
    
    def check_statement(self, stmt: ast.Statement):
        """Check a statement"""
        if isinstance(stmt, ast.VarDecl):
            self.check_var_decl(stmt)
        elif isinstance(stmt, ast.Assignment):
            self.check_assignment(stmt)
        elif isinstance(stmt, ast.ExpressionStmt):
            self.check_expression(stmt.expression)
        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value:
                self.check_expression(stmt.value)
        elif isinstance(stmt, ast.IfStmt):
            self.check_if(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self.check_while(stmt)
        elif isinstance(stmt, ast.ForStmt):
            self.check_for(stmt)
        elif isinstance(stmt, ast.MatchStmt):
            self.check_match(stmt)
    
    def check_var_decl(self, decl: ast.VarDecl):
        """Check variable declaration"""
        self.check_expression(decl.initializer)
    
    def check_assignment(self, assign: ast.Assignment):
        """Check assignment"""
        # Check if target is mutably borrowed
        if isinstance(assign.target, ast.Identifier):
            # Check if this variable is borrowed
            borrows = self.state.get_active_borrows(assign.target.name)
            if borrows:
                self.error(
                    f"Cannot assign to '{assign.target.name}' because it is borrowed",
                    assign.span,
                    [("borrowed here", b.borrow_span) for b in borrows]
                )
        
        self.check_expression(assign.value)
    
    def check_if(self, if_stmt: ast.IfStmt):
        """Check if statement"""
        self.check_expression(if_stmt.condition)
        
        # Save state
        original_state = self.state.clone()
        
        # Check then branch
        self.state = original_state.enter_scope()
        self.check_block(if_stmt.then_block)
        then_state = self.state
        self.state = original_state
        
        # Check elif clauses
        elif_states = []
        for elif_cond, elif_block in if_stmt.elif_clauses:
            self.state = original_state.enter_scope()
            self.check_expression(elif_cond)
            self.check_block(elif_block)
            elif_states.append(self.state)
            self.state = original_state
        
        # Check else branch
        if if_stmt.else_block:
            self.state = original_state.enter_scope()
            self.check_block(if_stmt.else_block)
            else_state = self.state
        else:
            else_state = original_state
        
        # Merge states - conservative approach
        self.state = original_state
    
    def check_while(self, while_stmt: ast.WhileStmt):
        """Check while loop"""
        self.check_expression(while_stmt.condition)
        
        # Analyze body in new scope
        original_state = self.state.clone()
        self.state = self.state.enter_scope()
        self.check_block(while_stmt.body)
        self.state = original_state
    
    def check_for(self, for_stmt: ast.ForStmt):
        """Check for loop"""
        self.check_expression(for_stmt.iterable)
        
        # Analyze body in new scope
        original_state = self.state.clone()
        self.state = self.state.enter_scope()
        self.check_block(for_stmt.body)
        self.state = original_state
    
    def check_match(self, match_stmt: ast.MatchStmt):
        """Check match statement"""
        self.check_expression(match_stmt.scrutinee)
        
        # Check each arm
        for arm in match_stmt.arms:
            original_state = self.state.clone()
            self.state = self.state.enter_scope()
            
            if arm.guard:
                self.check_expression(arm.guard)
            
            self.check_block(arm.body)
            self.state = original_state
    
    def check_expression(self, expr: ast.Expression):
        """Check an expression for borrow conflicts"""
        if isinstance(expr, ast.Identifier):
            # Using a variable - track usage
            var_name = expr.name
            self.add_timeline_event(var_name, "use", f"'{var_name}' used", expr.span)
            # Reading is always OK (borrow checker doesn't prevent reads)
        
        elif isinstance(expr, ast.UnaryOp):
            if expr.op == '&':
                # Immutable borrow
                self.check_immutable_borrow(expr.operand, expr.span)
            elif expr.op == '&mut':
                # Mutable borrow
                self.check_mutable_borrow(expr.operand, expr.span)
            else:
                self.check_expression(expr.operand)
        
        elif isinstance(expr, ast.BinOp):
            self.check_expression(expr.left)
            self.check_expression(expr.right)
        
        elif isinstance(expr, ast.TernaryExpr):
            self.check_expression(expr.condition)
            self.check_expression(expr.true_expr)
            self.check_expression(expr.false_expr)
        
        elif isinstance(expr, ast.FunctionCall):
            self.check_expression(expr.function)
            for arg in expr.arguments:
                self.check_expression(arg)
        
        elif isinstance(expr, ast.MethodCall):
            self.check_expression(expr.object)
            for arg in expr.arguments:
                self.check_expression(arg)
        
        elif isinstance(expr, ast.FieldAccess):
            self.check_expression(expr.object)
        
        elif isinstance(expr, ast.IndexAccess):
            self.check_expression(expr.object)
            self.check_expression(expr.index)
        
        elif isinstance(expr, ast.StructLiteral):
            for _, field_value in expr.fields:
                self.check_expression(field_value)
        
        elif isinstance(expr, ast.ListLiteral):
            for elem in expr.elements:
                self.check_expression(elem)
    
    def check_immutable_borrow(self, operand: ast.Expression, span: Span):
        """Check if immutable borrow is allowed"""
        if isinstance(operand, ast.Identifier):
            var_name = operand.name
            
            # Track timeline event
            self.add_timeline_event(var_name, "borrow", f"'{var_name}' borrowed as immutable", span)
            
            # Check for conflicting mutable borrow
            conflict = self.state.check_borrow_conflict(var_name, False, span)
            if conflict:
                self.error(
                    f"Cannot borrow '{var_name}' as immutable because it is also borrowed as mutable",
                    span,
                    [("mutable borrow occurs here", conflict.borrow_span)]
                )
                return
            
            # Add immutable borrow
            self.state.add_borrow(var_name, False, span)
    
    def check_mutable_borrow(self, operand: ast.Expression, span: Span):
        """Check if mutable borrow is allowed"""
        if isinstance(operand, ast.Identifier):
            var_name = operand.name
            
            # Track timeline event
            self.add_timeline_event(var_name, "borrow_mut", f"'{var_name}' borrowed as mutable", span)
            
            # Check for ANY conflicting borrow
            conflict = self.state.check_borrow_conflict(var_name, True, span)
            if conflict:
                if conflict.mutable:
                    self.error(
                        f"Cannot borrow '{var_name}' as mutable more than once at a time",
                        span,
                        [("first mutable borrow occurs here", conflict.borrow_span)]
                    )
                else:
                    self.error(
                        f"Cannot borrow '{var_name}' as mutable because it is also borrowed as immutable",
                        span,
                        [("immutable borrow occurs here", conflict.borrow_span)]
                    )
                return
            
            # Add mutable borrow
            self.state.add_borrow(var_name, True, span)


def check_borrows(program: ast.Program, type_env: Dict[str, Type], type_checker, track_timeline: bool = False) -> BorrowChecker:
    """Convenience function to check borrows
    
    Args:
        program: Program AST
        type_env: Type environment
        type_checker: Type checker instance
        track_timeline: Enable ownership timeline tracking
    """
    checker = BorrowChecker(track_timeline=track_timeline)
    checker.type_checker = type_checker
    checker.check_program(program, type_env)
    return checker

