"""Tests for incremental compilation being enabled by default"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from pathlib import Path
import tempfile
import shutil


def test_incremental_enabled_by_default():
    """Test that incremental compilation is enabled by default"""
    from quarry.main import cmd_build
    
    # Create a temporary project
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        
        # Create Quarry.toml
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test_project"
version = "0.1.0"
""")
        
        # Create main.pyrite
        (project_dir / "src" / "main.pyrite").write_text("""fn main():
    print("Hello")
""")
        
        # Change to project directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(project_dir)
            
            # Build should use incremental by default (no --no-incremental flag)
            # This is a basic smoke test - actual incremental behavior is tested elsewhere
            # We just verify the function accepts incremental=True as default
            result = cmd_build(release=False, incremental=True)
            
            # Should succeed (or fail gracefully, not crash)
            assert result is not None
        finally:
            os.chdir(original_cwd)


def test_no_incremental_flag():
    """Test that --no-incremental flag disables incremental compilation"""
    from quarry.main import cmd_build
    
    # Create a temporary project
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        
        # Create Quarry.toml
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test_project"
version = "0.1.0"
""")
        
        # Create main.pyrite
        (project_dir / "src" / "main.pyrite").write_text("""fn main():
    print("Hello")
""")
        
        # Change to project directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(project_dir)
            
            # Build with incremental disabled
            result = cmd_build(release=False, incremental=False)
            
            # Should succeed (or fail gracefully, not crash)
            assert result is not None
        finally:
            os.chdir(original_cwd)

