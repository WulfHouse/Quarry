"""Test quarry install command"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_install
from quarry.dependency import DependencySource, generate_lockfile


def test_install_creates_deps_directory():
    """Test that install creates deps directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.lock with dependencies
        lockfile = project_dir / "Quarry.lock"
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        generate_lockfile(deps, str(lockfile))
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_install()
            # Should fail because package not in cache, but deps dir should be created
            deps_dir = project_dir / "deps"
            assert deps_dir.exists(), "deps directory should be created"
            # Command should fail (package not in cache)
            assert result == 1, "install should fail when package not in cache"
        finally:
            os.chdir(old_cwd)


def test_install_missing_lockfile():
    """Test that install errors when lockfile is missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = cmd_install()
            assert result == 1, "install should fail when lockfile is missing"
        finally:
            os.chdir(old_cwd)


def test_install_empty_lockfile():
    """Test that install works with empty lockfile"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create empty lockfile
        lockfile = project_dir / "Quarry.lock"
        generate_lockfile({}, str(lockfile))
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_install()
            assert result == 0, "install should succeed with empty lockfile"
        finally:
            os.chdir(old_cwd)
