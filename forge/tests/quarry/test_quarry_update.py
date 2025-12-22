"""Test quarry update command"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_update
from quarry.dependency import read_lockfile, parse_quarry_toml


def test_update_updates_lockfile():
    """Test that quarry update updates lockfile"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = ">=1.0.0"
""")
        
        # Create old lockfile
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
foo = "1.0.0"
""")
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_update()
            assert result == 0, "update should succeed"
            
            # Check lockfile was updated
            assert lockfile.exists()
            updated_deps = read_lockfile(str(lockfile))
            assert "foo" in updated_deps
        finally:
            os.chdir(old_cwd)


def test_update_specific_package():
    """Test that --package flag updates only specific package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml with multiple deps
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = ">=1.0.0"
bar = "2.0.0"
""")
        
        # Create lockfile
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
foo = "1.0.0"
bar = "2.0.0"
""")
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            # Update only foo
            result = cmd_update(package_name="foo")
            assert result == 0, "update should succeed"
            
            # Check lockfile
            updated_deps = read_lockfile(str(lockfile))
            assert "foo" in updated_deps
            assert "bar" in updated_deps
            # bar should remain unchanged
            assert updated_deps["bar"].version == "2.0.0"
        finally:
            os.chdir(old_cwd)


def test_update_no_changes():
    """Test that update reports when no changes are needed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = "1.0.0"
""")
        
        # Create lockfile with same version
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
foo = "1.0.0"
""")
        
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            result = cmd_update()
            # Should succeed even if no changes
            assert result == 0
        finally:
            os.chdir(old_cwd)
