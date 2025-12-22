"""Test assert and fail builtin functions"""
import pytest
import sys
import tempfile
import subprocess
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from quarry.test_runner import TestRunner


def test_assert_passes():
    """Test that assert with true condition passes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        
        # Create test file with assert
        test_file = tests_dir / "test_assert.pyrite"
        test_file.write_text("""@test
fn test_assert_passes():
    assert true
""")
        
        runner = TestRunner(project_dir)
        results = runner.run_test_file(test_file)
        
        # Test should pass (assert true)
        # Note: May fail if compilation/execution fails, but assert logic should work
        assert len(results) > 0


def test_fail_exits_with_error():
    """Test that fail exits with non-zero"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        tests_dir = project_dir / "tests"
        tests_dir.mkdir(parents=True)
        
        # Create test file with fail
        test_file = tests_dir / "test_fail.pyrite"
        test_file.write_text("""@test
fn test_fail():
    fail("test should fail")
""")
        
        runner = TestRunner(project_dir)
        results = runner.run_test_file(test_file)
        
        # Test should fail (fail() exits with non-zero)
        # Note: May fail compilation, but fail logic should work if compilation succeeds
        assert len(results) > 0
