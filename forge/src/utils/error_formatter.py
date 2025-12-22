"""Enhanced error message formatting for Pyrite"""

import sys
from typing import Optional
from ..frontend.tokens import Span


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    
    @staticmethod
    def enabled():
        """Check if colors should be enabled"""
        # Disable colors if output is redirected or on Windows without ANSI support
        if not sys.stdout.isatty():
            return False
        # Enable colors on Windows 10+ (has ANSI support)
        if sys.platform == 'win32':
            try:
                import os
                os.system('')  # Enable ANSI escape sequences on Windows
                return True
            except:
                return False
        return True


class ErrorFormatter:
    """Format error messages with WHAT/WHY/HOW structure"""
    
    def __init__(self, use_colors: bool = None):
        if use_colors is None:
            use_colors = Colors.enabled()
        self.use_colors = use_colors
    
    def format_error(
        self,
        error_type: str,
        message: str,
        span: Optional[Span] = None,
        source_lines: Optional[list] = None,
        error_code: Optional[str] = None,
        notes: Optional[list] = None,
        help_text: Optional[str] = None
    ) -> str:
        """Format a complete error message"""
        parts = []
        
        # Error header
        if error_code:
            header = f"error[{error_code}]: {message}"
        else:
            header = f"error: {message}"
        
        if self.use_colors:
            header = f"{Colors.BOLD}{Colors.RED}{header}{Colors.RESET}"
        
        parts.append(header)
        
        # Location
        if span:
            location = f"  --> {span.filename}:{span.start_line}:{span.start_column}"
            if self.use_colors:
                location = f"{Colors.BLUE}{location}{Colors.RESET}"
            parts.append(location)
            
            # Show source code context
            if source_lines:
                parts.append(self._format_source_context(span, source_lines))
        
        # Additional notes
        if notes:
            for note in notes:
                note_text = f"  = note: {note}"
                if self.use_colors:
                    note_text = f"{Colors.CYAN}  = note:{Colors.RESET} {note}"
                parts.append(note_text)
        
        # Help text
        if help_text:
            help_line = f"  = help: {help_text}"
            if self.use_colors:
                help_line = f"{Colors.CYAN}  = help:{Colors.RESET} {help_text}"
            parts.append(help_line)
        
        # Explanation hint
        if error_code:
            explain = f"  = explain: Run 'pyritec --explain {error_code}' for more details"
            if self.use_colors:
                explain = f"{Colors.GRAY}{explain}{Colors.RESET}"
            parts.append(explain)
        
        return '\n'.join(parts)
    
    def _format_source_context(self, span: Span, source_lines: list) -> str:
        """Format source code context with line numbers and highlighting"""
        parts = []
        
        # Show 2 lines before and after for context
        start_line = max(0, span.start_line - 3)
        end_line = min(len(source_lines), span.start_line + 2)
        
        # Calculate line number width for alignment
        line_num_width = len(str(end_line))
        
        parts.append("   |")
        
        for i in range(start_line, end_line):
            line_num = i + 1
            line_text = source_lines[i].rstrip()
            
            # Format line number
            if line_num == span.start_line:
                # Error line
                num_str = f"{line_num:>{line_num_width}}"
                if self.use_colors:
                    num_str = f"{Colors.BLUE}{num_str}{Colors.RESET}"
                parts.append(f"{num_str} | {line_text}")
                
                # Add highlighting
                highlight = " " * (line_num_width + 3 + span.start_column - 1)
                highlight_len = span.end_column - span.start_column if span.end_line == span.start_line else len(line_text) - span.start_column + 1
                highlight += "^" * max(1, highlight_len)
                if self.use_colors:
                    highlight = f"{Colors.RED}{highlight}{Colors.RESET}"
                parts.append(highlight)
            else:
                # Context line
                num_str = f"{line_num:>{line_num_width}}"
                if self.use_colors:
                    num_str = f"{Colors.GRAY}{num_str}{Colors.RESET}"
                    line_text = f"{Colors.GRAY}{line_text}{Colors.RESET}"
                parts.append(f"{num_str} | {line_text}")
        
        parts.append("   |")
        
        return '\n'.join(parts)
    
    def format_ownership_error(
        self,
        variable: str,
        span: Span,
        source_lines: list,
        moved_to: str,
        moved_at: Optional[Span] = None,
        allocated_at: Optional[Span] = None
    ) -> str:
        """Format ownership error (use-after-move)"""
        message = f"cannot use moved value '{variable}'"
        
        notes = []
        if allocated_at:
            notes.append(f"value allocated at {allocated_at.filename}:{allocated_at.start_line}")
        if moved_at:
            notes.append(f"value moved to '{moved_to}' at {moved_at.filename}:{moved_at.start_line}")
        
        help_text = (
            "Consider:\n"
            f"           1. Pass a reference: {moved_to}(&{variable})\n"
            f"           2. Clone the value: {moved_to}({variable}.clone())\n"
            "           3. Restructure to avoid the move"
        )
        
        return self.format_error(
            "Ownership Error",
            message,
            span,
            source_lines,
            "P0234",
            notes,
            help_text
        )
    
    def format_borrow_error(
        self,
        variable: str,
        span: Span,
        source_lines: list,
        borrow_type: str = "mutable",
        conflict_with: str = "immutable",
        conflict_at: Optional[Span] = None
    ) -> str:
        """Format borrow checking error"""
        message = f"cannot borrow '{variable}' as {borrow_type} while borrowed as {conflict_with}"
        
        notes = []
        if conflict_at:
            notes.append(f"first {conflict_with} borrow occurs at {conflict_at.filename}:{conflict_at.start_line}")
        
        help_text = (
            "Borrowing rules:\n"
            "           - Multiple immutable borrows are allowed\n"
            "           - Only ONE mutable borrow at a time\n"
            "           - No mutable borrow while immutable borrows exist"
        )
        
        return self.format_error(
            "Borrow Checking Error",
            message,
            span,
            source_lines,
            "P0502",
            notes,
            help_text
        )
    
    def format_type_error(
        self,
        message: str,
        span: Span,
        source_lines: list,
        expected_type: Optional[str] = None,
        found_type: Optional[str] = None
    ) -> str:
        """Format type checking error"""
        notes = []
        if expected_type and found_type:
            notes.append(f"expected type: {expected_type}")
            notes.append(f"found type: {found_type}")
        
        return self.format_error(
            "Type Error",
            message,
            span,
            source_lines,
            "P0308",
            notes
        )


def format_error_message(
    error_type: str,
    message: str,
    span: Optional[Span] = None,
    source: Optional[str] = None,
    **kwargs
) -> str:
    """Quick helper to format an error message"""
    formatter = ErrorFormatter()
    
    source_lines = None
    if source:
        source_lines = source.split('\n')
    
    return formatter.format_error(error_type, message, span, source_lines, **kwargs)


# Example usage
if __name__ == "__main__":  # pragma: no cover
    # Test the formatter
    from ..frontend.tokens import Span
    
    source = """fn main():
    let data = List { length: 3 }
    process(data)
    print(data.length)  # ERROR: moved value
"""
    
    lines = source.split('\n')
    span = Span("test.pyrite", 4, 11, 4)
    
    formatter = ErrorFormatter()
    print(formatter.format_ownership_error(
        "data",
        span,
        lines,
        "process",
        Span("test.pyrite", 3, 13, 4),
        Span("test.pyrite", 2, 9, 4)
    ))

