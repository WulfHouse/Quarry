"""Enhanced error diagnostics for Pyrite"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from ..frontend.tokens import Span
from colorama import init, Fore, Style

# Initialize colorama for Windows color support
init()


@dataclass
class FixSuggestion:
    """A suggested fix for an error"""
    description: str
    code_change: str  # Description of the code change (e.g., "Pass &data instead of data")
    confidence: str = "medium"  # "high", "medium", "low"
    explanation: str = ""  # Why this fix works


class Diagnostic:
    """A compiler diagnostic (error or warning)"""
    
    def __init__(self, 
                 code: str,
                 message: str,
                 span: Span,
                 level: str = "error",
                 notes: List[str] = None,
                 help_messages: List[str] = None,
                 related_spans: List[Tuple[str, Span]] = None,
                 var_name: str = None):
        self.code = code
        self.message = message
        self.span = span
        self.level = level
        self.notes = notes or []
        self.help_messages = help_messages or []
        self.related_spans = related_spans or []
        self.var_name = var_name  # Variable name for ownership errors
    
    def format(self, source: str) -> str:
        """Format diagnostic with source context"""
        lines = []
        
        # Header
        if self.level == "error":
            color = Fore.RED
            level_str = "error"
        elif self.level == "warning":
            color = Fore.YELLOW
            level_str = "warning"
        else:
            color = ""
            level_str = self.level
        
        lines.append(f"\n{color}{level_str}[{self.code}]: {self.message}{Style.RESET_ALL}")
        
        # Location
        lines.append(f"  --> {self.span}")
        lines.append("   |")
        
        # Source context
        source_lines = source.split('\n')
        start_line = max(0, self.span.start_line - 2)
        end_line = min(len(source_lines), self.span.end_line + 2)
        
        for i in range(start_line, end_line):
            line_num = i + 1
            line_content = source_lines[i] if i < len(source_lines) else ""
            lines.append(f"{line_num:4} | {line_content}")
            
            # Highlight error location
            if line_num == self.span.start_line:
                spaces = " " * (self.span.start_column - 1)
                carets = "^" * max(1, self.span.end_column - self.span.start_column)
                lines.append(f"     | {spaces}{color}{carets}{Style.RESET_ALL}")
        
        lines.append("   |")
        
        # Related spans
        for note, related_span in self.related_spans:
            lines.append(f"   = note: {note}")
            lines.append(f"     --> {related_span}")
        
        # Notes
        for note in self.notes:
            lines.append(f"   = note: {note}")
        
        # Help messages
        for help_msg in self.help_messages:
            lines.append(f"   = {Fore.CYAN}help{Style.RESET_ALL}: {help_msg}")
        
        # Fix suggestions
        fix_suggestions = self.suggest_fixes()
        if fix_suggestions:
            for i, fix in enumerate(fix_suggestions, 1):
                lines.append(f"   = {Fore.CYAN}help{Style.RESET_ALL}: Fix {i}: {fix.description}")
                if fix.code_change:
                    lines.append(f"      {fix.code_change}")
                if fix.explanation:
                    lines.append(f"      {fix.explanation}")
        
        # Explanation hint
        lines.append(f"   = For more information, run: pyrite --explain {self.code}")
        
        return '\n'.join(lines)
    
    def suggest_fixes(self) -> List[FixSuggestion]:
        """Generate fix suggestions for this diagnostic"""
        suggestions = []
        
        # P0234: cannot use moved value
        if self.code == "P0234":
            if self.var_name:
                suggestions.append(FixSuggestion(
                    description=f"Pass a reference to '{self.var_name}' instead",
                    code_change=f"Change function call to use &{self.var_name} instead of {self.var_name}",
                    confidence="high",
                    explanation=f"'{self.var_name}' will remain usable after the call, but function can only read (not mutate) unless it takes &mut."
                ))
                suggestions.append(FixSuggestion(
                    description=f"Clone '{self.var_name}' before moving",
                    code_change=f"Change function call to use {self.var_name}.clone() instead of {self.var_name}",
                    confidence="medium",
                    explanation=f"Creates a copy of '{self.var_name}' before passing it. '{self.var_name}' remains usable, but this allocates memory."
                ))
                suggestions.append(FixSuggestion(
                    description=f"Restructure code to avoid using '{self.var_name}' after move",
                    code_change="Move the usage of the variable before the function call",
                    confidence="low",
                    explanation="Sometimes the best fix is to restructure the code flow."
                ))
        
        # P0502: cannot borrow as mutable while borrowed as immutable
        elif self.code == "P0502":
            if self.var_name:
                suggestions.append(FixSuggestion(
                    description=f"Clone '{self.var_name}' to avoid borrow conflict",
                    code_change=f"Use {self.var_name}.clone() for one of the borrows",
                    confidence="medium",
                    explanation="Creates a new copy, avoiding the borrow conflict. Resolves the conflict but allocates memory."
                ))
                suggestions.append(FixSuggestion(
                    description=f"Limit borrow scope for '{self.var_name}'",
                    code_change="Wrap the conflicting borrows in a block to limit their lifetime",
                    confidence="high",
                    explanation="No memory overhead, but requires restructuring code. Use when you can separate the borrows into different scopes."
                ))
                suggestions.append(FixSuggestion(
                    description=f"Use '{self.var_name}' in separate scopes",
                    code_change="Restructure code so immutable and mutable borrows don't overlap",
                    confidence="medium",
                    explanation="Ensure the immutable borrow ends before the mutable borrow begins."
                ))
        
        # P0308: type mismatch
        elif self.code == "P0308":
            # Extract type information from message if possible
            if "expected" in self.message.lower() and "found" in self.message.lower():
                suggestions.append(FixSuggestion(
                    description="Add explicit type cast",
                    code_change="Use 'as TypeName' to cast the value to the expected type",
                    confidence="medium",
                    explanation="May lose precision or fail at runtime if cast is invalid. Use when you're certain the value can be safely cast."
                ))
                suggestions.append(FixSuggestion(
                    description="Change the variable type",
                    code_change="Update the type annotation to match the actual value type",
                    confidence="high",
                    explanation="If the value type is correct, update the expected type instead."
                ))
                suggestions.append(FixSuggestion(
                    description="Fix the initialization",
                    code_change="Ensure the value being assigned matches the expected type",
                    confidence="high",
                    explanation="The most common fix: use the correct value type from the start."
                ))
        
        # P0382: borrow of moved value
        elif self.code == "P0382":
            if self.var_name:
                suggestions.append(FixSuggestion(
                    description=f"Borrow '{self.var_name}' before moving it",
                    code_change=f"Create the borrow (&{self.var_name}) before the move operation",
                    confidence="high",
                    explanation="Once a value is moved, you cannot borrow it. Borrow it first, then move."
                ))
        
        # P0499: cannot borrow as mutable more than once
        elif self.code == "P0499":
            if self.var_name:
                suggestions.append(FixSuggestion(
                    description=f"Use '{self.var_name}' in separate scopes",
                    code_change="Ensure the first mutable borrow ends before creating the second",
                    confidence="high",
                    explanation="Only one mutable borrow can exist at a time. Separate them with scopes."
                ))
                suggestions.append(FixSuggestion(
                    description=f"Clone '{self.var_name}' for one of the borrows",
                    code_change=f"Use {self.var_name}.clone() to create a copy for one borrow",
                    confidence="medium",
                    explanation="Resolves the conflict but allocates memory. Use when the value is small enough."
                ))
        
        # P0505: borrowed value does not live long enough
        elif self.code == "P0505":
            suggestions.append(FixSuggestion(
                description="Return owned value instead of reference",
                code_change="Change function return type from &T to T and return the owned value",
                confidence="high",
                explanation="References cannot outlive the value they point to. Returning an owned value avoids this issue."
            ))
            suggestions.append(FixSuggestion(
                description="Pass reference as parameter instead of returning it",
                code_change="Take a reference parameter and return that reference instead of creating a new one",
                confidence="medium",
                explanation="If the reference comes from a parameter, it can be returned safely."
            ))
        
        return suggestions


# Common error codes
ERROR_CODES = {
    # Ownership errors
    "P0234": "cannot use moved value",
    "P0382": "borrow of moved value",
    "P0499": "cannot borrow as mutable more than once",
    "P0502": "cannot borrow as mutable while borrowed as immutable",
    "P0503": "cannot borrow as immutable while borrowed as mutable",
    "P0505": "borrowed value does not live long enough",
    
    # Type errors
    "P0308": "type mismatch",
    "P0425": "cannot compare types",
    "P0277": "trait bound not satisfied",
    
    # Name resolution
    "P0425": "cannot find value in this scope",
    "P0412": "cannot find type in this scope",
    
    # Pattern matching
    "P0004": "non-exhaustive patterns",
}


def create_ownership_error(var_name: str, moved_to: str, use_span: Span, move_span: Span, alloc_span: Span) -> Diagnostic:
    """Create a use-after-move error diagnostic"""
    return Diagnostic(
        code="P0234",
        message=f"cannot use moved value '{var_name}'",
        span=use_span,
        var_name=var_name,
        level="error",
        notes=[
            f"value moved to '{moved_to}' here"
        ],
        help_messages=[
            "Consider:",
            f"  1. Pass a reference: &{var_name}",
            f"  2. Clone the value: {var_name}.clone()",
            "  3. Restructure your code to avoid the move"
        ],
        related_spans=[
            ("value allocated here", alloc_span),
            ("value moved here", move_span)
        ]
    )


def create_borrow_conflict_error(var_name: str, new_borrow_span: Span, 
                                 existing_borrow_span: Span, 
                                 new_is_mut: bool, existing_is_mut: bool) -> Diagnostic:
    """Create a borrow conflict error"""
    if new_is_mut and existing_is_mut:
        message = f"cannot borrow '{var_name}' as mutable more than once at a time"
        code = "P0499"
    elif new_is_mut:
        message = f"cannot borrow '{var_name}' as mutable because it is also borrowed as immutable"
        code = "P0502"
    else:
        message = f"cannot borrow '{var_name}' as immutable because it is also borrowed as mutable"
        code = "P0503"
    
    return Diagnostic(
        code=code,
        message=message,
        span=new_borrow_span,
        level="error",
        related_spans=[
            ("first borrow occurs here", existing_borrow_span)
        ],
        help_messages=[
            "Consider:",
            "  1. Reduce the scope of the first borrow",
            "  2. Use the borrows sequentially instead of simultaneously"
        ]
    )


def create_type_mismatch_error(expected: str, got: str, span: Span) -> Diagnostic:
    """Create a type mismatch error"""
    return Diagnostic(
        code="P0308",
        message=f"mismatched types",
        span=span,
        level="error",
        notes=[
            f"expected type: {expected}",
            f"   found type: {got}"
        ],
        help_messages=[
            f"Consider converting {got} to {expected}",
            "Or change the expected type to match"
        ]
    )

