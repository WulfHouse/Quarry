"""Test quarry publish command"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_publish
from quarry import registry as registry_module
from quarry.registry import set_registry_path, ensure_registry, get_package_metadata, read_index
from quarry.publisher import validate_for_publish


def test_publish_publishes_package():
    """Test that quarry publish publishes package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Create valid project
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
license = "MIT"
""")
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.pyrite").write_text("fn main():\n    print(42)\n")
            
            os.chdir(project_dir)
            
            # Publish (with --no-test to skip test validation)
            result = cmd_publish(dry_run=False, no_test=True)
            assert result == 0
            
            # Check package is in registry
            metadata = get_package_metadata("test-pkg", "1.0.0")
            assert metadata is not None
            assert metadata["name"] == "test-pkg"
            assert metadata["version"] == "1.0.0"
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_publish_dry_run():
    """Test that --dry-run validates and packages without publishing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Create valid project
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
license = "MIT"
""")
            
            os.chdir(project_dir)
            
            # Ensure registry path is set
            registry_module.set_registry_path(registry_path)
            
            # Dry run should succeed
            result = cmd_publish(dry_run=True, no_test=True)
            assert result == 0
            
            # But package should not be in registry (dry run doesn't publish)
            # Verify registry directory is empty or package not there
            package_dir = registry_path / "test-pkg" / "1.0.0"
            # Package directory should not exist (dry run doesn't publish)
            if package_dir.exists():
                # If it exists, metadata should not be there
                metadata = registry_module.get_package_metadata("test-pkg", "1.0.0")
                assert metadata is None
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_publish_validation_errors_prevent_publishing():
    """Test that validation errors prevent publishing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Create invalid project (missing license)
            project_dir = Path(tmpdir) / "test_project"
            project_dir.mkdir()
            (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
""")
            
            os.chdir(project_dir)
            
            # Publish should fail
            result = cmd_publish(dry_run=False, no_test=True)
            assert result == 1
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)
