"""Pyrite code formatter"""

import sys
from pathlib import Path
from typing import List


class Formatter:
    """Format Pyrite source code"""
    
    def __init__(self):
        self.indent_size = 4
        self.max_line_length = 100
    
    def format_file(self, filepath: Path) -> str:
        """Format a Pyrite file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        return self.format_source(source)
    
    def format_source(self, source: str) -> str:
        """Format Pyrite source code"""
        lines = source.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                formatted_lines.append('')
                continue
            
            # Handle dedent (closing braces, dedent keywords)
            if self._is_dedent(stripped):
                indent_level = max(0, indent_level - 1)
            
            # Format the line with proper indentation
            indent = ' ' * (indent_level * self.indent_size)
            formatted_line = indent + self._format_line(stripped)
            formatted_lines.append(formatted_line)
            
            # Handle indent (opening braces, function defs, etc.)
            if self._is_indent(stripped):
                indent_level += 1
        
        return '\n'.join(formatted_lines)
    
    def _is_indent(self, line: str) -> bool:
        """Check if line should increase indent"""
        # Lines ending with : increase indent
        return line.rstrip().endswith(':')
    
    def _is_dedent(self, line: str) -> bool:
        """Check if line should decrease indent"""
        # For now, no explicit dedent keywords
        # Indentation is handled by the absence of content
        return False
    
    def _format_line(self, line: str) -> str:
        """Format a single line"""
        # Add spaces around operators
        line = self._add_operator_spacing(line)
        
        # Format function definitions
        if line.startswith('fn '):
            line = self._format_function_def(line)
        
        # Format struct definitions
        if line.startswith('struct '):
            line = self._format_struct_def(line)
        
        return line
    
    def _add_operator_spacing(self, line: str) -> str:
        """Add proper spacing around operators"""
        # This is a simplified version
        # In a real formatter, we'd use the AST
        
        # Skip if line is a comment or string
        if line.strip().startswith('#'):
            return line
        
        # Add spaces around = (but not ==)
        parts = []
        i = 0
        while i < len(line):
            if line[i] == '=' and i + 1 < len(line) and line[i+1] != '=':
                # Assignment operator
                parts.append(' = ')
                i += 1
            elif line[i:i+2] == '==':
                parts.append(' == ')
                i += 2
            elif line[i:i+2] == '!=':
                parts.append(' != ')
                i += 2
            elif line[i:i+2] == '<=':
                parts.append(' <= ')
                i += 2
            elif line[i:i+2] == '>=':
                parts.append(' >= ')
                i += 2
            elif line[i] in '<>':
                parts.append(f' {line[i]} ')
                i += 1
            elif line[i] in '+-*/%' and (i == 0 or line[i-1] not in '=<>!'):
                parts.append(f' {line[i]} ')
                i += 1
            else:
                parts.append(line[i])
                i += 1
        
        result = ''.join(parts)
        # Clean up multiple spaces
        while '  ' in result:
            result = result.replace('  ', ' ')
        
        return result.strip()
    
    def _format_function_def(self, line: str) -> str:
        """Format function definition"""
        # Ensure proper spacing: fn name(params) -> return_type:
        return line  # Simplified for now
    
    def _format_struct_def(self, line: str) -> str:
        """Format struct definition"""
        return line  # Simplified for now


def format_file(filepath: str, check_only: bool = False) -> bool:
    """Format a Pyrite file"""
    path = Path(filepath)
    
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        return False
    
    formatter = Formatter()
    
    try:
        original = path.read_text(encoding='utf-8')
        formatted = formatter.format_source(original)
        
        if check_only:
            if original != formatted:
                print(f"File would be reformatted: {filepath}")
                return False
            else:
                print(f"File is already formatted: {filepath}")
                return True
        else:
            if original != formatted:
                path.write_text(formatted, encoding='utf-8')
                print(f"Formatted: {filepath}")
            else:
                print(f"Already formatted: {filepath}")
            return True
    
    except Exception as e:
        print(f"Error formatting {filepath}: {e}")
        return False


def format_directory(directory: str, check_only: bool = False) -> bool:
    """Format all .pyrite files in a directory"""
    path = Path(directory)
    
    if not path.exists():
        print(f"Error: Directory not found: {directory}")
        return False
    
    pyrite_files = list(path.rglob("*.pyrite"))
    
    if not pyrite_files:
        print(f"No .pyrite files found in {directory}")
        return True
    
    all_ok = True
    for file in pyrite_files:
        if not format_file(str(file), check_only):
            all_ok = False
    
    return all_ok


def main():
    """Main entry point for formatter"""
    if len(sys.argv) < 2:
        print("Usage: python -m quarry.formatter <file_or_dir> [--check]")
        return 1
    
    target = sys.argv[1]
    check_only = '--check' in sys.argv
    
    path = Path(target)
    
    if path.is_file():
        success = format_file(target, check_only)
    elif path.is_dir():
        success = format_directory(target, check_only)
    else:
        print(f"Error: Not a file or directory: {target}")
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

