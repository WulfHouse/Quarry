"""Test quarry search and info commands"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.main import cmd_search, cmd_info
from quarry.registry import (
    set_registry_path, ensure_registry, store_package_metadata,
    add_to_index
)


def test_search_finds_packages():
    """Test that quarry search finds packages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Store packages
            store_package_metadata("test-pkg", "1.0.0", {
                "name": "test-pkg",
                "version": "1.0.0"
            })
            store_package_metadata("another-pkg", "2.0.0", {
                "name": "another-pkg",
                "version": "2.0.0"
            })
            add_to_index("test-pkg", "1.0.0")
            add_to_index("another-pkg", "2.0.0")
            
            # Search should find test-pkg
            result = cmd_search("test")
            assert result == 0
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_search_no_results():
    """Test that quarry search handles no results"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Search for non-existent package
            result = cmd_search("nonexistent")
            assert result == 0  # Should succeed but find nothing
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_info_shows_package_details():
    """Test that quarry info shows package details"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Store package with metadata
            metadata = {
                "name": "test-pkg",
                "version": "1.0.0",
                "description": "Test package",
                "license": "MIT",
                "authors": ["test@example.com"],
                "dependencies": {}
            }
            store_package_metadata("test-pkg", "1.0.0", metadata)
            add_to_index("test-pkg", "1.0.0")
            
            # Info should show package details
            result = cmd_info("test-pkg")
            assert result == 0
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)


def test_info_package_not_found():
    """Test that quarry info handles missing package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Use isolated registry path
            registry_path = Path(tmpdir) / "test_registry"
            set_registry_path(registry_path)
            ensure_registry()
            
            # Info for non-existent package should fail
            result = cmd_info("nonexistent")
            assert result == 1
        finally:
            set_registry_path(None)
            os.chdir(old_cwd)
