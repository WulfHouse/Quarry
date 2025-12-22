"""Test quarry resolve command"""
import pytest
import sys
import tempfile
from pathlib import Path
import subprocess

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_resolve
from quarry.dependency import read_lockfile


def test_resolve_creates_lockfile():
    """Test that quarry resolve creates Quarry.lock"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml with dependencies
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test_project"
version = "0.1.0"

[dependencies]
foo = ">=1.0.0"
bar = "2.0.0"
""")
        
        # Change to project directory and run resolve
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_resolve()
            assert result == 0, "resolve should succeed"
            
            # Check that lockfile was created
            lockfile = project_dir / "Quarry.lock"
            assert lockfile.exists(), "Quarry.lock should be created"
            
            # Check lockfile contents
            deps = read_lockfile(str(lockfile))
            assert "foo" in deps
            assert "bar" in deps
            assert deps["bar"].version == "2.0.0"
        finally:
            os.chdir(old_cwd)


def test_resolve_missing_toml():
    """Test that resolve errors when Quarry.toml is missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = cmd_resolve()
            assert result == 1, "resolve should fail when Quarry.toml is missing"
        finally:
            os.chdir(old_cwd)


def test_resolve_empty_dependencies():
    """Test that resolve works with empty dependencies"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml without dependencies
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test_project"
version = "0.1.0"
""")
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_resolve()
            assert result == 0, "resolve should succeed with no dependencies"
            
            # Lockfile should still be created (empty)
            lockfile = project_dir / "Quarry.lock"
            assert lockfile.exists(), "Quarry.lock should be created even with no deps"
            
            deps = read_lockfile(str(lockfile))
            assert deps == {}, "Lockfile should be empty"
        finally:
            os.chdir(old_cwd)


def test_resolve_resolution_failure():
    """Test that resolve handles resolution failures"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml with invalid dependency (not in mock registry)
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test_project"
version = "0.1.0"

[dependencies]
nonexistent_package = "999.0.0"
""")
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_resolve()
            assert result == 1, "resolve should fail when dependency cannot be resolved"
        finally:
            os.chdir(old_cwd)
