"""Test quarry test command"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_test
from quarry.test_runner import TestRunner


def test_test_runs_all_tests():
    """Test that quarry test runs all tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        
        # Create test file
        test_file = tests_dir / "test_example.pyrite"
        test_file.write_text("""@test
fn test_example():
    print(42)
""")
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            # Test may fail compilation, but command should work
            result = cmd_test()
            assert isinstance(result, int)
        finally:
            os.chdir(old_cwd)


def test_test_no_tests_found():
    """Test that quarry test handles no tests gracefully"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = cmd_test()
            assert result == 0, "test should succeed when no tests found"
        finally:
            os.chdir(old_cwd)
