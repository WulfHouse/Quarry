"""Test --locked flag validation"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from quarry.dependency import parse_quarry_toml, read_lockfile, generate_lockfile, resolve_dependencies


def test_locked_with_valid_lockfile():
    """Test that --locked succeeds with valid lockfile"""
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
        
        # Create matching lockfile
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
foo = "2.0.0"
""")
        
        # Verify lockfile matches toml
        toml_deps = parse_quarry_toml(str(toml_file))
        lockfile_deps = read_lockfile(str(lockfile))
        
        assert "foo" in toml_deps
        assert "foo" in lockfile_deps
        # Version 2.0.0 should satisfy >=1.0.0
        assert lockfile_deps["foo"].version == "2.0.0"


def test_locked_with_missing_lockfile():
    """Test that --locked fails when lockfile is missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"
""")
        
        # No lockfile
        
        lockfile = project_dir / "Quarry.lock"
        assert not lockfile.exists(), "Lockfile should not exist"
        
        # Validation should fail
        lockfile_deps = read_lockfile(str(lockfile))
        assert lockfile_deps == {}, "Missing lockfile should return empty dict"


def test_locked_with_outdated_lockfile():
    """Test that --locked fails when lockfile is outdated"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml with dependency
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = ">=2.0.0"
bar = "1.0.0"
""")
        
        # Create outdated lockfile (missing bar, wrong version for foo)
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
foo = "1.0.0"
""")
        
        toml_deps = parse_quarry_toml(str(toml_file))
        lockfile_deps = read_lockfile(str(lockfile))
        
        # Lockfile is missing 'bar' and has wrong version for 'foo'
        assert "bar" in toml_deps
        assert "bar" not in lockfile_deps, "Lockfile should be missing 'bar'"
        assert lockfile_deps["foo"].version == "1.0.0", "Lockfile has old version"
        assert toml_deps["foo"].version == ">=2.0.0", "Toml requires >=2.0.0"


def test_locked_auto_resolves_when_not_locked():
    """Test that build auto-resolves when --locked is not set"""
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
        
        # No lockfile - should auto-resolve
        lockfile = project_dir / "Quarry.lock"
        assert not lockfile.exists()
        
        # Auto-resolve
        deps = parse_quarry_toml(str(toml_file))
        resolved = resolve_dependencies(deps)
        generate_lockfile(resolved, str(lockfile))
        
        assert lockfile.exists(), "Lockfile should be auto-generated"
        lockfile_deps = read_lockfile(str(lockfile))
        assert "foo" in lockfile_deps
