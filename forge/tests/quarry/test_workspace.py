"""Test workspace support"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.workspace import parse_workspace_toml, find_workspace_root, get_workspace_packages


def test_parse_workspace_toml():
    """Test parsing Workspace.toml"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_file = Path(tmpdir) / "Workspace.toml"
        workspace_file.write_text("""[workspace]
members = ["pkg1", "pkg2", "pkg3"]
""")
        
        members = parse_workspace_toml(str(workspace_file))
        assert len(members) == 3
        assert "pkg1" in members
        assert "pkg2" in members
        assert "pkg3" in members


def test_find_workspace_root():
    """Test finding workspace root"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_root = Path(tmpdir)
        (workspace_root / "Workspace.toml").write_text("""[workspace]
members = ["pkg1"]
""")
        
        # Create subdirectory
        subdir = workspace_root / "subdir"
        subdir.mkdir()
        
        found_root = find_workspace_root(subdir)
        assert found_root == workspace_root


def test_get_workspace_packages():
    """Test getting workspace packages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_root = Path(tmpdir)
        (workspace_root / "Workspace.toml").write_text("""[workspace]
members = ["pkg1", "pkg2"]
""")
        
        # Create package directories
        pkg1 = workspace_root / "pkg1"
        pkg1.mkdir()
        (pkg1 / "Quarry.toml").write_text("""[package]
name = "pkg1"
version = "0.1.0"
""")
        
        pkg2 = workspace_root / "pkg2"
        pkg2.mkdir()
        (pkg2 / "Quarry.toml").write_text("""[package]
name = "pkg2"
version = "0.1.0"
""")
        
        packages = get_workspace_packages(workspace_root)
        assert len(packages) == 2
        assert any(p.name == "pkg1" for p in packages)
        assert any(p.name == "pkg2" for p in packages)
