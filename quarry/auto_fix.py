"""Auto-fix system for common Pyrite errors"""

import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Import Diagnostic for fix suggestions
try:
    import sys as _sys
    from pathlib import Path as _Path
    _repo_root = _Path(__file__).parent.parent
    _forge_path = _repo_root / "forge"
    if str(_forge_path) not in _sys.path:
        _sys.path.insert(0, str(_forge_path))
    from src.utils.diagnostics import Diagnostic, FixSuggestion
    from src.frontend.tokens import Span
    HAS_DIAGNOSTIC = True
except ImportError:
    HAS_DIAGNOSTIC = False


@dataclass
class Fix:
    """Represents a code fix"""
    description: str
    file_path: str
    line_number: int
    old_text: str
    new_text: str
    explanation: str
    trade_off: str = ""  # Trade-off explanation
    when_to_use: str = ""  # When to use this fix
    cost: str = ""  # Cost annotation ("allocates", "copies", "zero-cost", etc.)


class AutoFixer:
    """Automatically fix common Pyrite errors"""
    
    def __init__(self):
        self.fixes: List[Fix] = []
    
    def analyze_error(self, error_message: str, source_file: str) -> List[Fix]:
        """Analyze compiler error and generate fixes"""
        fixes = []
        
        # Parse error message
        if "cannot use moved value" in error_message or "already moved" in error_message:
            move_fixes = self._fix_use_after_move(error_message, source_file)
            fixes.extend(move_fixes)
        
        elif "cannot borrow" in error_message:
            borrow_fixes = self._fix_borrow_conflict(error_message, source_file)
            fixes.extend(borrow_fixes)
        
        elif "type mismatch" in error_message or "expected" in error_message:
            type_fixes = self._fix_type_mismatch(error_message, source_file)
            fixes.extend(type_fixes)
        
        elif "undefined" in error_message or "not found" in error_message:
            undefined_fixes = self._fix_undefined_variable(error_message, source_file)
            fixes.extend(undefined_fixes)
        
        return fixes
    
    def _extract_line_number(self, error_message: str) -> Optional[int]:
        """Extract line number from error message"""
        # Look for patterns like "line 5" or ":5:"
        match = re.search(r'line\s+(\d+)', error_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        match = re.search(r':(\d+):', error_message)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_variable_name(self, error_message: str) -> Optional[str]:
        """Extract variable name from error message"""
        # Look for patterns like 'data' or "data"
        match = re.search(r"['\"](\w+)['\"]", error_message)
        if match:
            return match.group(1)
        return None
    
    def _fix_use_after_move(self, error_message: str, source_file: str) -> List[Fix]:
        """Generate fixes for use-after-move error (multiple options)"""
        line_num = self._extract_line_number(error_message)
        var_name = self._extract_variable_name(error_message)
        
        if not line_num or not var_name:
            return []
        
        fixes = []
        
        # Read source file
        try:
            with open(source_file, 'r') as f:
                lines = f.readlines()
            
            if line_num <= 0 or line_num > len(lines):
                return []
            
            # Find the line with the move (usually a function call)
            # Search backwards from the error line, but skip the error line itself
            # The move happens on a line BEFORE the error line
            move_line = None
            # Start from line_num - 2 (one line before the error line, 0-indexed)
            # This ensures we skip the error line itself
            # line_num is 1-indexed, so line_num - 2 gives us the line before the error (0-indexed)
            start_line = max(0, line_num - 2)  # Ensure we don't go negative
            for i in range(start_line, -1, -1):
                line_content = lines[i].strip()
                # Look for function call pattern: function_name(var_name) or function_name(..., var_name, ...)
                # Must have '(' and the variable name, and should be a function call (not just print/assignment)
                if var_name in line_content and '(' in line_content:
                    # Additional check: make sure it's not just the variable declaration
                    # Skip if it's a 'let' statement (variable declaration)
                    if not line_content.startswith('let ') and not line_content.startswith('fn '):
                        move_line = i
                        break
            
            if move_line is None:
                return []
            
            old_text = lines[move_line].rstrip()
            
            # Fix 1: Pass reference (borrow) instead of move
            new_text_ref = old_text.replace(f"({var_name}", f"(&{var_name}")
            new_text_ref = new_text_ref.replace(f", {var_name}", f", &{var_name}")
            if new_text_ref != old_text:  # Only add if change was made
                fixes.append(Fix(
                    description=f"Pass a reference to '{var_name}' instead",
                    file_path=source_file,
                    line_number=move_line + 1,
                    old_text=old_text,
                    new_text=new_text_ref,
                    explanation=f"Changes the function call to borrow '{var_name}' instead of taking ownership.",
                    trade_off=f"'{var_name}' remains usable after the call, but function can only read (not mutate) unless it takes &mut.",
                    when_to_use="Use when the function only needs to read the value, or when you need to use the variable after the call.",
                    cost="zero-cost (no allocation or copy)"
                ))
            
            # Fix 2: Clone before moving
            new_text_clone = old_text.replace(f"({var_name}", f"({var_name}.clone()")
            new_text_clone = new_text_clone.replace(f", {var_name}", f", {var_name}.clone()")
            if new_text_clone != old_text:  # Only add if change was made
                fixes.append(Fix(
                    description=f"Clone '{var_name}' before moving",
                    file_path=source_file,
                    line_number=move_line + 1,
                    old_text=old_text,
                    new_text=new_text_clone,
                    explanation=f"Creates a copy of '{var_name}' before passing it to the function.",
                    trade_off=f"'{var_name}' remains usable, but this allocates memory and copies data.",
                    when_to_use="Use when you need both the original and a copy, or when the function needs ownership but you also need the value.",
                    cost="allocates and copies (memory overhead)"
                ))
        
        except Exception:
            return []
        
        return fixes
    
    def _fix_borrow_conflict(self, error_message: str, source_file: str) -> List[Fix]:
        """Generate fixes for borrow conflict (multiple options)"""
        line_num = self._extract_line_number(error_message)
        var_name = self._extract_variable_name(error_message)
        
        if not line_num or not var_name:
            return []
        
        fixes = []
        
        # Fix 1: Clone to avoid conflict
        fixes.append(Fix(
            description=f"Clone '{var_name}' to avoid borrow conflict",
            file_path=source_file,
            line_number=line_num,
            old_text=var_name,
            new_text=f"{var_name}.clone()",
            explanation="Creates a new copy, avoiding the borrow conflict.",
            trade_off="Resolves the conflict but allocates memory and copies data.",
            when_to_use="Use when you need both mutable borrows, or when the value is small enough that copying is acceptable.",
            cost="allocates and copies"
        ))
        
        # Fix 2: Use scope to limit borrow lifetime
        # This is harder to implement automatically, but we can suggest it
        fixes.append(Fix(
            description=f"Limit borrow scope for '{var_name}'",
            file_path=source_file,
            line_number=line_num,
            old_text="",  # Manual fix
            new_text="",  # Manual fix
            explanation="Wrap the conflicting borrows in a block to limit their lifetime.",
            trade_off="No memory overhead, but requires restructuring code.",
            when_to_use="Use when you can separate the borrows into different scopes.",
            cost="zero-cost (no allocation)"
        ))
        
        return fixes
    
    def _fix_type_mismatch(self, error_message: str, source_file: str) -> List[Fix]:
        """Generate fixes for type mismatch"""
        line_num = self._extract_line_number(error_message)
        
        if not line_num:
            return []
        
        fixes = []
        
        # Extract expected and actual types
        expected_match = re.search(r'expected\s+`?(\w+)`?', error_message, re.IGNORECASE)
        actual_match = re.search(r'(?:found|got|actual)\s+`?(\w+)`?', error_message, re.IGNORECASE)
        
        if expected_match and actual_match:
            expected = expected_match.group(1)
            actual = actual_match.group(1)
            
            fixes.append(Fix(
                description=f"Add type cast from {actual} to {expected}",
                file_path=source_file,
                line_number=line_num,
                old_text="",  # Will be filled in by apply_fix
                new_text=f" as {expected}",
                explanation=f"Explicitly cast the value to the expected type {expected}.",
                trade_off="May lose precision or fail at runtime if cast is invalid.",
                when_to_use="Use when you're certain the value can be safely cast to the target type.",
                cost="zero-cost (compile-time cast)"
            ))
        
        return fixes
    
    def _fix_undefined_variable(self, error_message: str, source_file: str) -> List[Fix]:
        """Generate fixes for undefined variable"""
        var_name = self._extract_variable_name(error_message)
        line_num = self._extract_line_number(error_message)
        
        if not var_name:
            return []
        
        fixes = []
        
        fixes.append(Fix(
            description=f"Define variable '{var_name}'",
            file_path=source_file,
            line_number=line_num or 1,
            old_text="",
            new_text=f"let {var_name} = ",
            explanation=f"Add a declaration for '{var_name}' before using it.",
            trade_off="Variable will be available, but you need to provide an initial value.",
            when_to_use="Use when the variable should be declared at this point in the code.",
            cost="zero-cost (no allocation)"
        ))
        
        return fixes
    
    def apply_fix(self, fix: Fix) -> bool:
        """Apply a fix to the source file"""
        try:
            with open(fix.file_path, 'r') as f:
                lines = f.readlines()
            
            if fix.line_number <= 0 or fix.line_number > len(lines):
                return False
            
            # Apply the fix
            line_idx = fix.line_number - 1
            old_line = lines[line_idx]
            
            if fix.old_text:
                # Replace old_text with new_text
                new_line = old_line.replace(fix.old_text, fix.new_text)
            else:
                # Append new_text
                new_line = old_line.rstrip() + fix.new_text + '\n'
            
            lines[line_idx] = new_line
            
            # Write back
            with open(fix.file_path, 'w') as f:
                f.writelines(lines)
            
            return True
        
        except Exception as e:
            print(f"Error applying fix: {e}")
            return False
    
    def interactive_fix(self, fixes: List[Fix]) -> int:
        """Interactively apply fixes with numbered options"""
        if not fixes:
            print("No fixes available")
            return 0
        
        # Group fixes by error (for now, show all fixes together)
        print("\n" + "=" * 60)
        print("Select a fix:")
        print("=" * 60)
        
        for i, fix in enumerate(fixes, 1):
            print(f"\n  {i}. {fix.description}")
            if fix.trade_off:
                print(f"     - Effect: {fix.trade_off}")
            if fix.when_to_use:
                print(f"     - When to use: {fix.when_to_use}")
            if fix.cost:
                print(f"     - Cost: {fix.cost}")
            print(f"     - File: {fix.file_path}:{fix.line_number}")
            if fix.old_text and fix.new_text:
                print(f"     - Change: {fix.old_text} -> {fix.new_text}")
            elif fix.old_text:
                print(f"     - Remove: {fix.old_text}")
            elif fix.new_text:
                print(f"     - Add: {fix.new_text}")
            if fix.explanation:
                print(f"     - {fix.explanation}")
        
        print(f"\nChoice (1-{len(fixes)}, or 'q' to quit): ", end="")
        
        try:
            choice = input().strip()
            
            if choice.lower() == 'q':
                print("Cancelled")
                return 0
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(fixes):
                selected_fix = fixes[choice_num - 1]
                
                # Check if this is a manual fix (empty old_text and new_text)
                if not selected_fix.old_text and not selected_fix.new_text:
                    print("\n[WARNING] This fix requires manual code changes:")
                    print(f"   {selected_fix.explanation}")
                    print(f"   {selected_fix.trade_off}")
                    return 0
                
                if self.apply_fix(selected_fix):
                    print(f"\n[OK] Fix applied: {selected_fix.description}")
                    
                    # Recompile and verify
                    if self._verify_fix(selected_fix.file_path):
                        print("[OK] Code compiles successfully after fix")
                        return 1
                    else:
                        print("[WARNING] Fix applied but code still has errors")
                        return 1
                else:
                    print("✗ Failed to apply fix")
                    return 0
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(fixes)}")
                return 0
        except ValueError:
            print("Invalid input. Please enter a number or 'q'")
            return 0
        except KeyboardInterrupt:
            print("\nCancelled")
            return 0
    
    def _verify_fix(self, file_path: str) -> bool:
        """Recompile and verify the fix worked"""
        try:
            import subprocess
            compiler_root = Path(__file__).parent.parent
            
            result = subprocess.run([
                sys.executable, "-m", "src.compiler",
                file_path,
                "-o", "target/debug/test_fix",
                "--emit-llvm"
            ], cwd=compiler_root, capture_output=True, text=True)
            
            return result.returncode == 0
        except Exception:
            return False


def cmd_fix(interactive: bool = True, auto: bool = False):
    """Run auto-fix on current project
    
    Args:
        interactive: Show interactive prompt (default: True)
        auto: Apply all fixes automatically (default: False)
    """
    # Get current working directory (project directory)
    project_dir = Path.cwd()
    main_file = project_dir / "src" / "main.pyrite"
    
    if not main_file.exists():
        print("Error: src/main.pyrite not found")
        return 1
    
    print("Analyzing code for fixable errors...")
    
    # Compile to get errors
    import subprocess
    compiler_root = Path(__file__).parent.parent
    # Use absolute path for source file
    result = subprocess.run([
        sys.executable, "-m", "src.compiler",
        str(main_file),
        "-o", str(project_dir / "target" / "debug" / "main"),
        "--emit-llvm"
    ], cwd=compiler_root, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("No errors found!")
        return 0
    
    # Parse errors and generate fixes
    fixer = AutoFixer()
    error_output = result.stdout + result.stderr
    
    # Try to extract Diagnostic information from error output
    # Look for error codes like P0234, P0502, etc.
    fixes = []
    error_lines = error_output.split('\n')
    current_error_lines = []
    current_error_code = None
    current_var_name = None
    
    for line in error_lines:
        # Check for error code pattern: error[P0234] or error[P0502]
        error_code_match = re.search(r'error\[(P\d{4})\]', line, re.IGNORECASE)
        if error_code_match:
            current_error_code = error_code_match.group(1)
        
        # Extract variable name from error message
        var_match = re.search(r"['\"](\w+)['\"]", line)
        if var_match:
            current_var_name = var_match.group(1)
        
        # Check if this line starts a new error
        if any(keyword in line.lower() for keyword in ["error", "cannot", "expected", "undefined"]):
            # Process previous error if any
            if current_error_lines:
                error_message = '\n'.join(current_error_lines)
                error_fixes = fixer.analyze_error(error_message, str(main_file))
                fixes.extend(error_fixes)
                
                # Also try to use Diagnostic.suggest_fixes() if we have error code
                if HAS_DIAGNOSTIC and current_error_code:
                    try:
                        # Create a Diagnostic object to get suggestions
                        span = Span(
                            filename=str(main_file),
                            start_line=1,
                            start_column=1,
                            end_line=1,
                            end_column=10
                        )
                        diag = Diagnostic(
                            code=current_error_code,
                            message=error_message.split('\n')[0] if error_message else "Error",
                            span=span,
                            var_name=current_var_name
                        )
                        suggestions = diag.suggest_fixes()
                        
                        # Convert FixSuggestion to Fix for compatibility
                        for i, suggestion in enumerate(suggestions):
                            # Try to extract line number from error message
                            line_num = fixer._extract_line_number(error_message) or 1
                            fixes.append(Fix(
                                description=suggestion.description,
                                file_path=str(main_file),
                                line_number=line_num,
                                old_text="",  # Will be filled by apply_fix if needed
                                new_text=suggestion.code_change,
                                explanation=suggestion.explanation,
                                trade_off="",
                                when_to_use="",
                                cost=""
                            ))
                    except Exception:
                        # Fall back to AutoFixer if Diagnostic fails
                        pass
            
            # Start new error
            current_error_lines = [line]
            current_error_code = None
            current_var_name = None
        elif current_error_lines:
            # Continue collecting current error
            current_error_lines.append(line)
    
    # Process last error
    if current_error_lines:
        error_message = '\n'.join(current_error_lines)
        error_fixes = fixer.analyze_error(error_message, str(main_file))
        fixes.extend(error_fixes)
        
        # Also try Diagnostic.suggest_fixes() for last error
        if HAS_DIAGNOSTIC and current_error_code:
            try:
                span = Span(
                    filename=str(main_file),
                    start_line=1,
                    start_column=1,
                    end_line=1,
                    end_column=10
                )
                diag = Diagnostic(
                    code=current_error_code,
                    message=error_message.split('\n')[0] if error_message else "Error",
                    span=span,
                    var_name=current_var_name
                )
                suggestions = diag.suggest_fixes()
                line_num = fixer._extract_line_number(error_message) or 1
                for suggestion in suggestions:
                    fixes.append(Fix(
                        description=suggestion.description,
                        file_path=str(main_file),
                        line_number=line_num,
                        old_text="",
                        new_text=suggestion.code_change,
                        explanation=suggestion.explanation,
                        trade_off="",
                        when_to_use="",
                        cost=""
                    ))
            except Exception:
                pass
    
    if not fixes:
        print("No automatic fixes available for these errors")
        print("\nErrors:")
        print(error_output)
        return 1
    
    print(f"Found {len(fixes)} fix option(s)")
    
    if auto:
        # Batch mode: apply first fix for each error
        applied = 0
        seen_errors = set()
        
        for fix in fixes:
            # Only apply first fix per error location
            error_key = f"{fix.file_path}:{fix.line_number}"
            if error_key not in seen_errors:
                if fix.old_text or fix.new_text:  # Skip manual fixes
                    if fixer.apply_fix(fix):
                        print(f"  [OK] {fix.description}")
                        applied += 1
                        seen_errors.add(error_key)
        
        if applied > 0:
            # Verify compilation
            verify_result = subprocess.run([
                sys.executable, "-m", "src.compiler",
                str(main_file),
                "-o", str(project_dir / "target" / "debug" / "main"),
                "--emit-llvm"
            ], cwd=compiler_root, capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                print(f"\n[OK] Applied {applied} fix(es) - code compiles successfully")
            else:
                print(f"\n[WARNING] Applied {applied} fix(es) but code still has errors")
        
        return 0 if applied > 0 else 1
    
    elif interactive:
        applied = fixer.interactive_fix(fixes)
        return 0 if applied > 0 else 1
    
    return 0


if __name__ == '__main__':
    import subprocess
    cmd_fix(interactive=True)

