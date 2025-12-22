"""Test registry operations"""
import pytest
import sys
import tempfile
import json
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.registry import (
    get_registry_path, ensure_registry, list_packages,
    get_package_versions, get_package_metadata, get_package_path,
    store_package_metadata, remove_package, set_registry_path,
    read_index, update_index, add_to_index, remove_from_index
)


def test_get_registry_path():
    """Test that registry path is returned"""
    path = get_registry_path()
    assert isinstance(path, Path)


def test_ensure_registry():
    """Test that registry directory is created"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            registry_path = ensure_registry()
            assert registry_path.exists()
            assert registry_path.is_dir()
        finally:
            os.chdir(old_cwd)


def test_list_packages_empty():
    """Test list_packages() on empty registry"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            # Create empty registry
            registry_path.mkdir(parents=True, exist_ok=True)
            packages = list_packages()
            assert packages == []
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_get_package_versions_nonexistent():
    """Test get_package_versions() for non-existent package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            versions = get_package_versions("nonexistent")
            assert versions == []
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_store_and_get_metadata():
    """Test storing and retrieving package metadata"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            metadata = {
                "name": "test-pkg",
                "version": "1.0.0",
                "dependencies": {},
                "checksum": "sha256:abc123",
                "license": "MIT",
                "authors": ["test@example.com"]
            }
            
            success = store_package_metadata("test-pkg", "1.0.0", metadata)
            assert success
            
            retrieved = get_package_metadata("test-pkg", "1.0.0")
            assert retrieved is not None
            assert retrieved["name"] == "test-pkg"
            assert retrieved["version"] == "1.0.0"
            assert retrieved["checksum"] == "sha256:abc123"
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_list_packages_with_data():
    """Test list_packages() with packages in registry"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Store metadata for a package
            metadata = {"name": "test-pkg", "version": "1.0.0"}
            store_package_metadata("test-pkg", "1.0.0", metadata)
            
            packages = list_packages()
            assert "test-pkg" in packages
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_get_package_versions():
    """Test get_package_versions() with multiple versions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Store multiple versions
            store_package_metadata("test-pkg", "1.0.0", {"name": "test-pkg", "version": "1.0.0"})
            store_package_metadata("test-pkg", "1.1.0", {"name": "test-pkg", "version": "1.1.0"})
            store_package_metadata("test-pkg", "2.0.0", {"name": "test-pkg", "version": "2.0.0"})
            
            versions = get_package_versions("test-pkg")
            assert "1.0.0" in versions
            assert "1.1.0" in versions
            assert "2.0.0" in versions
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_update_index():
    """Test that update_index() creates index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Store some packages
            store_package_metadata("pkg1", "1.0.0", {"name": "pkg1", "version": "1.0.0"})
            store_package_metadata("pkg2", "2.0.0", {"name": "pkg2", "version": "2.0.0"})
            
            # Update index
            success = update_index()
            assert success
            
            # Read index
            index = read_index()
            assert "pkg1" in index
            assert "pkg2" in index
            assert "1.0.0" in index["pkg1"]
            assert "2.0.0" in index["pkg2"]
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_read_index_empty():
    """Test that read_index() returns empty dict for missing index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Read index (should be empty)
            index = read_index()
            assert index == {}
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_add_to_index():
    """Test that add_to_index() updates index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path for this test
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Add to index
            success = add_to_index("test-pkg", "1.0.0")
            assert success
            
            # Read index
            index = read_index()
            assert "test-pkg" in index
            assert "1.0.0" in index["test-pkg"]
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)
