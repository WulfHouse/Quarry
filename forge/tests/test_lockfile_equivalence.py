"""Equivalence tests for lockfile operations

Tests that Pyrite FFI implementation matches Python implementation exactly.
"""

import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.dependency import DependencySource
from quarry.bridge.lockfile_bridge import (
    generate_lockfile_ffi, generate_lockfile_python,
    read_lockfile_ffi, read_lockfile_python
)


class TestGenerateLockfileEquivalence:
    """Test generate_lockfile equivalence"""
    
    def test_empty_dependencies(self):
        """Empty dependencies"""
        deps = {}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Python implementation
            generate_lockfile_python(deps, str(lockfile_path))
            python_content = lockfile_path.read_text()
            
            # Pyrite implementation
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            pyrite_content = lockfile_path.read_text()
            
            # Both should produce valid lockfiles
            assert "[dependencies]" in python_content
            assert "[dependencies]" in pyrite_content
    
    def test_registry_dependency_simple(self):
        """Registry dependency without checksum"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Python implementation
            generate_lockfile_python(deps, str(lockfile_path))
            python_deps = read_lockfile_python(str(lockfile_path))
            
            # Pyrite implementation
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            # Compare parsed results
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["foo"].type == pyrite_deps["foo"].type == "registry"
            assert python_deps["foo"].version == pyrite_deps["foo"].version == "1.0.0"
    
    def test_registry_dependency_with_checksum(self):
        """Registry dependency with checksum"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Python implementation
            generate_lockfile_python(deps, str(lockfile_path))
            python_deps = read_lockfile_python(str(lockfile_path))
            
            # Pyrite implementation
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            # Compare parsed results
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["foo"].checksum == pyrite_deps["foo"].checksum == "sha256:abc123"
    
    def test_git_dependency(self):
        """Git dependency"""
        deps = {
            "bar": DependencySource(
                type="git",
                git_url="https://github.com/user/bar.git",
                git_branch="main",
                commit="def456"
            )
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Python implementation
            generate_lockfile_python(deps, str(lockfile_path))
            python_deps = read_lockfile_python(str(lockfile_path))
            
            # Pyrite implementation
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            # Compare parsed results
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["bar"].type == pyrite_deps["bar"].type == "git"
            assert python_deps["bar"].git_url == pyrite_deps["bar"].git_url
            assert python_deps["bar"].git_branch == pyrite_deps["bar"].git_branch == "main"
            assert python_deps["bar"].commit == pyrite_deps["bar"].commit == "def456"
    
    def test_path_dependency(self):
        """Path dependency"""
        deps = {
            "baz": DependencySource(
                type="path",
                path="../baz",
                hash="sha256:ghi789"
            )
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Python implementation
            generate_lockfile_python(deps, str(lockfile_path))
            python_deps = read_lockfile_python(str(lockfile_path))
            
            # Pyrite implementation
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            # Compare parsed results
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["baz"].type == pyrite_deps["baz"].type == "path"
            assert python_deps["baz"].path == pyrite_deps["baz"].path == "../baz"
            assert python_deps["baz"].hash == pyrite_deps["baz"].hash == "sha256:ghi789"
    
    def test_mixed_dependencies(self):
        """Mixed dependency types"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
            "baz": DependencySource(type="path", path="../baz")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Python implementation
            generate_lockfile_python(deps, str(lockfile_path))
            python_deps = read_lockfile_python(str(lockfile_path))
            
            # Pyrite implementation
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            # Compare parsed results
            assert len(python_deps) == len(pyrite_deps) == 3
            assert set(python_deps.keys()) == set(pyrite_deps.keys()) == {"foo", "bar", "baz"}
    
    def test_deterministic_ordering(self):
        """Test that dependencies are sorted by name"""
        deps = {
            "zebra": DependencySource(type="registry", version="1.0.0"),
            "alpha": DependencySource(type="registry", version="1.0.0"),
                "beta": DependencySource(type="registry", version="1.0.0")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Generate multiple times
            generate_lockfile_ffi(deps, str(lockfile_path))
            content1 = lockfile_path.read_text()
            
            lockfile_path.unlink()
            generate_lockfile_ffi(deps, str(lockfile_path))
            content2 = lockfile_path.read_text()
            
            # Should produce same output (deterministic)
            assert content1 == content2
            
            # Check ordering (alpha should come before beta, beta before zebra)
            alpha_pos = content1.find("alpha")
            beta_pos = content1.find("beta")
            zebra_pos = content1.find("zebra")
            assert alpha_pos < beta_pos < zebra_pos


class TestReadLockfileEquivalence:
    """Test read_lockfile equivalence"""
    
    def test_empty_lockfile(self):
        """Empty lockfile"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            lockfile_path.write_text("[dependencies]\n")
            
            python_deps = read_lockfile_python(str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            assert python_deps == pyrite_deps == {}
    
    def test_missing_lockfile(self):
        """Missing lockfile"""
        lockfile_path = "nonexistent.lock"
        
        python_deps = read_lockfile_python(lockfile_path)
        pyrite_deps = read_lockfile_ffi(lockfile_path)
        
        assert python_deps == pyrite_deps == {}
    
    def test_registry_dependency_parsing(self):
        """Parse registry dependency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            lockfile_path.write_text("""[dependencies]
foo = "1.0.0"
""")
            
            python_deps = read_lockfile_python(str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["foo"].type == pyrite_deps["foo"].type == "registry"
            assert python_deps["foo"].version == pyrite_deps["foo"].version == "1.0.0"
    
    def test_registry_with_checksum_parsing(self):
        """Parse registry dependency with checksum"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            lockfile_path.write_text("""[dependencies]
foo = { version = "1.0.0", checksum = "sha256:abc123" }
""")
            
            python_deps = read_lockfile_python(str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["foo"].checksum == pyrite_deps["foo"].checksum == "sha256:abc123"
    
    def test_git_dependency_parsing(self):
        """Parse git dependency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            lockfile_path.write_text("""[dependencies]
bar = { git = "https://github.com/user/bar.git", branch = "main", commit = "def456" }
""")
            
            python_deps = read_lockfile_python(str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["bar"].type == pyrite_deps["bar"].type == "git"
            assert python_deps["bar"].git_url == pyrite_deps["bar"].git_url
            assert python_deps["bar"].git_branch == pyrite_deps["bar"].git_branch == "main"
            assert python_deps["bar"].commit == pyrite_deps["bar"].commit == "def456"
    
    def test_path_dependency_parsing(self):
        """Parse path dependency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            lockfile_path.write_text("""[dependencies]
baz = { path = "../baz", hash = "sha256:ghi789" }
""")
            
            python_deps = read_lockfile_python(str(lockfile_path))
            pyrite_deps = read_lockfile_ffi(str(lockfile_path))
            
            assert len(python_deps) == len(pyrite_deps) == 1
            assert python_deps["baz"].type == pyrite_deps["baz"].type == "path"
            assert python_deps["baz"].path == pyrite_deps["baz"].path == "../baz"
            assert python_deps["baz"].hash == pyrite_deps["baz"].hash == "sha256:ghi789"


class TestRoundtripEquivalence:
    """Test roundtrip (generate → read) equivalence"""
    
    def test_roundtrip_registry(self):
        """Roundtrip: registry dependency"""
        original_deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Generate with Python, read with both
            generate_lockfile_python(original_deps, str(lockfile_path))
            python_read = read_lockfile_python(str(lockfile_path))
            pyrite_read = read_lockfile_ffi(str(lockfile_path))
            
            # Both should read same data
            assert len(python_read) == len(pyrite_read) == 1
            assert python_read["foo"].type == pyrite_read["foo"].type == "registry"
            assert python_read["foo"].version == pyrite_read["foo"].version == "1.0.0"
            assert python_read["foo"].checksum == pyrite_read["foo"].checksum == "sha256:abc123"
    
    def test_roundtrip_mixed(self):
        """Roundtrip: mixed dependencies"""
        original_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
            "baz": DependencySource(type="path", path="../baz", hash="sha256:ghi789")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Generate with Pyrite, read with both
            generate_lockfile_ffi(original_deps, str(lockfile_path))
            python_read = read_lockfile_python(str(lockfile_path))
            pyrite_read = read_lockfile_ffi(str(lockfile_path))
            
            # Both should read same data
            assert len(python_read) == len(pyrite_read) == 3
            assert set(python_read.keys()) == set(pyrite_read.keys()) == {"foo", "bar", "baz"}
    
    def test_roundtrip_idempotency(self):
        """Roundtrip: multiple roundtrips should be idempotent"""
        original_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="registry", version="2.0.0")
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile_path = Path(tmpdir) / "Quarry.lock"
            
            # Generate → Read → Generate → Read
            generate_lockfile_ffi(original_deps, str(lockfile_path))
            round1_read = read_lockfile_ffi(str(lockfile_path))
            generate_lockfile_ffi(round1_read, str(lockfile_path))
            round2_read = read_lockfile_ffi(str(lockfile_path))
            
            # Should be same after roundtrip
            assert len(round1_read) == len(round2_read) == 2
            assert round1_read["foo"].version == round2_read["foo"].version == "1.0.0"
            assert round1_read["bar"].version == round2_read["bar"].version == "2.0.0"


class TestIntegrationEquivalence:
    """Integration tests using real Quarry functions"""
    
    def test_cmd_resolve_integration(self):
        """Test cmd_resolve uses lockfile functions"""
        from quarry.dependency import parse_quarry_toml, resolve_dependencies, generate_lockfile, read_lockfile
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            toml_file = project_dir / "Quarry.toml"
            toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = "1.0.0"
""")
            
            # Parse and resolve
            deps = parse_quarry_toml(str(toml_file))
            resolved = resolve_dependencies(deps)
            
            # Generate lockfile
            lockfile_path = project_dir / "Quarry.lock"
            generate_lockfile(resolved, str(lockfile_path), project_dir)
            
            # Read lockfile
            locked_deps = read_lockfile(str(lockfile_path))
            
            assert len(locked_deps) == 1
            assert "foo" in locked_deps
            assert locked_deps["foo"].type == "registry"
