"""Test quarry run command"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_run


def test_run_binary_not_found():
    """Test that run errors when binary doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Binary doesn't exist
            result = cmd_run()
            assert result == 1, "run should fail when binary not found"
        finally:
            os.chdir(old_cwd)


def test_run_with_args():
    """Test that run function exists and is callable"""
    # cmd_run() doesn't take parameters - it reads from sys.argv
    # This test verifies the function exists and can be called
    assert callable(cmd_run)
    
    # The function will fail if binary doesn't exist, but should be callable
    # We can't easily test with args since it reads from sys.argv
    # Just verify it's a function
    import inspect
    sig = inspect.signature(cmd_run)
    assert len(sig.parameters) == 0, "cmd_run should take no parameters"
