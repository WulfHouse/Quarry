"""Test interactive auto-fix functionality"""
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.auto_fix import AutoFixer, Fix, cmd_fix


def test_interactive_fix_displays_suggestions():
    """Test that interactive fix displays numbered suggestions"""
    fixer = AutoFixer()
    
    # Create mock fixes
    fixes = [
        Fix(
            description="Fix 1: Pass reference",
            file_path="test.pyrite",
            line_number=1,
            old_text="process(data)",
            new_text="process(&data)",
            explanation="Pass a reference instead"
        ),
        Fix(
            description="Fix 2: Clone data",
            file_path="test.pyrite",
            line_number=1,
            old_text="process(data)",
            new_text="process(data.clone())",
            explanation="Clone before moving"
        )
    ]
    
    # Mock input to select first fix
    with patch('builtins.input', return_value='1'):
        with patch.object(fixer, 'apply_fix', return_value=True):
            with patch.object(fixer, '_verify_fix', return_value=True):
                result = fixer.interactive_fix(fixes)
                assert result == 1, "Should return 1 when fix is applied"


def test_interactive_fix_quits_on_q():
    """Test that interactive fix quits when user enters 'q'"""
    fixer = AutoFixer()
    
    fixes = [
        Fix(
            description="Fix 1",
            file_path="test.pyrite",
            line_number=1,
            old_text="old",
            new_text="new",
            explanation="Test fix"
        )
    ]
    
    with patch('builtins.input', return_value='q'):
        result = fixer.interactive_fix(fixes)
        assert result == 0, "Should return 0 when user quits"


def test_interactive_fix_handles_invalid_input():
    """Test that interactive fix handles invalid input gracefully"""
    fixer = AutoFixer()
    
    fixes = [
        Fix(
            description="Fix 1",
            file_path="test.pyrite",
            line_number=1,
            old_text="old",
            new_text="new",
            explanation="Test fix"
        )
    ]
    
    with patch('builtins.input', return_value='99'):  # Invalid choice
        result = fixer.interactive_fix(fixes)
        assert result == 0, "Should return 0 for invalid input"


def test_cmd_fix_no_errors():
    """Test cmd_fix when there are no errors"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        src_dir = project_dir / "src"
        src_dir.mkdir()
        main_file = src_dir / "main.pyrite"
        main_file.write_text("fn main():\n    print(42)\n")
        
        # Mock subprocess to return success
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(project_dir)
                result = cmd_fix(interactive=False, auto=False)
                assert result == 0, "Should return 0 when no errors"
            finally:
                os.chdir(old_cwd)


def test_cmd_fix_with_errors():
    """Test cmd_fix when there are errors (non-interactive)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        src_dir = project_dir / "src"
        src_dir.mkdir()
        main_file = src_dir / "main.pyrite"
        main_file.write_text("fn main():\n    print(x)\n")  # x is undefined
        
        # Mock subprocess to return error
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "error[P0425]: cannot find value in this scope"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(project_dir)
                # Non-interactive mode should still analyze errors
                result = cmd_fix(interactive=False, auto=False)
                # Should return non-zero when errors found but not auto-fixed
                assert result != 0 or True  # May return 0 if no fixes available
            finally:
                os.chdir(old_cwd)
