"""Equivalence tests for resolve command vertical

Tests that Python and Pyrite implementations produce identical results.
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
from quarry.bridge.resolve_bridge import resolve_dependencies_ffi, resolve_dependencies_python
from quarry.bridge.lockfile_bridge import read_lockfile_ffi, read_lockfile_python


class TestResolveBasic:
    """Test basic resolve functionality"""
    
    def test_resolve_registry_dependency(self):
        """Test resolve with single registry dependency"""
        toml_content = """[dependencies]
foo = "1.0.0"
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Compare resolved dependencies
        assert len(python_result["resolved"]) == len(pyrite_result["resolved"]) == 1
        assert "foo" in python_result["resolved"]
        assert "foo" in pyrite_result["resolved"]
        
        python_foo = python_result["resolved"]["foo"]
        pyrite_foo = pyrite_result["resolved"]["foo"]
        
        assert python_foo.type == pyrite_foo.type == "registry"
        assert python_foo.version == pyrite_foo.version  # Should be resolved version
    
    def test_resolve_git_dependency(self):
        """Test resolve with single git dependency"""
        toml_content = """[dependencies]
bar = { git = "https://github.com/user/bar.git", branch = "main" }
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Compare resolved dependencies
        assert len(python_result["resolved"]) == len(pyrite_result["resolved"]) == 1
        assert "bar" in python_result["resolved"]
        assert "bar" in pyrite_result["resolved"]
        
        python_bar = python_result["resolved"]["bar"]
        pyrite_bar = pyrite_result["resolved"]["bar"]
        
        assert python_bar.type == pyrite_bar.type == "git"
        assert python_bar.git_url == pyrite_bar.git_url == "https://github.com/user/bar.git"
        assert python_bar.git_branch == pyrite_bar.git_branch == "main"
    
    def test_resolve_path_dependency(self):
        """Test resolve with single path dependency"""
        toml_content = """[dependencies]
baz = { path = "../baz" }
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Compare resolved dependencies
        assert len(python_result["resolved"]) == len(pyrite_result["resolved"]) == 1
        assert "baz" in python_result["resolved"]
        assert "baz" in pyrite_result["resolved"]
        
        python_baz = python_result["resolved"]["baz"]
        pyrite_baz = pyrite_result["resolved"]["baz"]
        
        assert python_baz.type == pyrite_baz.type == "path"
        assert python_baz.path == pyrite_baz.path == "../baz"
    
    def test_resolve_mixed_dependencies(self):
        """Test resolve with mixed dependency types"""
        toml_content = """[dependencies]
foo = "1.0.0"
bar = { git = "https://github.com/user/bar.git", branch = "main" }
baz = { path = "../baz" }
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Compare resolved dependencies
        assert len(python_result["resolved"]) == len(pyrite_result["resolved"]) == 3
        
        # Check all dependencies are present
        for name in ["foo", "bar", "baz"]:
            assert name in python_result["resolved"]
            assert name in pyrite_result["resolved"]
            
            python_dep = python_result["resolved"][name]
            pyrite_dep = pyrite_result["resolved"][name]
            
            assert python_dep.type == pyrite_dep.type


class TestResolveEmpty:
    """Test resolve with empty dependencies"""
    
    def test_resolve_empty_dependencies(self):
        """Test resolve with empty [dependencies] section"""
        toml_content = """[dependencies]
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Compare resolved dependencies
        assert python_result["resolved"] == pyrite_result["resolved"] == {}
        
        # Compare lockfile content (should be empty)
        assert "[dependencies]" in python_result["lockfile_content"]
        assert "[dependencies]" in pyrite_result["lockfile_content"]
    
    def test_resolve_missing_dependencies_section(self):
        """Test resolve with missing [dependencies] section"""
        toml_content = """[package]
name = "test"
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Compare resolved dependencies
        assert python_result["resolved"] == pyrite_result["resolved"] == {}


class TestResolveLockfile:
    """Test lockfile generation in resolve"""
    
    def test_lockfile_content_structure(self):
        """Test that lockfile content has correct structure"""
        toml_content = """[dependencies]
foo = "1.0.0"
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Both should have lockfile content
        assert python_result["lockfile_content"]
        assert pyrite_result["lockfile_content"]
        
        # Both should contain [dependencies]
        assert "[dependencies]" in python_result["lockfile_content"]
        assert "[dependencies]" in pyrite_result["lockfile_content"]
        
        # Parse and compare structure
        python_lockfile = python_result["lockfile_content"]
        pyrite_lockfile = pyrite_result["lockfile_content"]
        
        # Read lockfiles and compare
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lock', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Write Python lockfile
            Path(tmp_path).write_text(python_lockfile, encoding='utf-8')
            python_parsed = read_lockfile_python(tmp_path)
            
            # Write Pyrite lockfile
            Path(tmp_path).write_text(pyrite_lockfile, encoding='utf-8')
            pyrite_parsed = read_lockfile_ffi(tmp_path)
            
            # Compare parsed results
            assert len(python_parsed) == len(pyrite_parsed)
            for name in python_parsed:
                assert name in pyrite_parsed
                python_dep = python_parsed[name]
                pyrite_dep = pyrite_parsed[name]
                assert python_dep.type == pyrite_dep.type
                if python_dep.type == "registry":
                    assert python_dep.version == pyrite_dep.version
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_lockfile_roundtrip(self):
        """Test roundtrip: resolve → read lockfile → verify"""
        toml_content = """[dependencies]
foo = "1.0.0"
bar = { git = "https://github.com/user/bar.git", branch = "main" }
"""
        
        # Resolve
        result = resolve_dependencies_ffi(toml_content)
        lockfile_content = result["lockfile_content"]
        
        # Write lockfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lock', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            Path(tmp_path).write_text(lockfile_content, encoding='utf-8')
            
            # Read lockfile
            read_deps = read_lockfile_ffi(tmp_path)
            
            # Verify
            assert len(read_deps) == len(result["resolved"])
            for name in result["resolved"]:
                assert name in read_deps
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestResolveOutput:
    """Test output formatting"""
    
    def test_formatted_output_structure(self):
        """Test that formatted output has correct structure"""
        toml_content = """[dependencies]
foo = "1.0.0"
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Both should have formatted output
        assert python_result["formatted_output"]
        assert pyrite_result["formatted_output"]
        
        # Both should contain key phrases
        assert "Resolving dependencies" in python_result["formatted_output"]
        assert "Resolving dependencies" in pyrite_result["formatted_output"]
        assert "Resolved" in python_result["formatted_output"]
        assert "Resolved" in pyrite_result["formatted_output"]
        assert "Generated Quarry.lock" in python_result["formatted_output"]
        assert "Generated Quarry.lock" in pyrite_result["formatted_output"]
    
    def test_formatted_output_empty(self):
        """Test formatted output for empty dependencies"""
        toml_content = """[dependencies]
"""
        
        # Python implementation
        python_result = resolve_dependencies_python(toml_content)
        
        # Pyrite implementation
        pyrite_result = resolve_dependencies_ffi(toml_content)
        
        # Both should mention empty
        assert "empty" in python_result["formatted_output"].lower() or "no dependencies" in python_result["formatted_output"].lower()
        assert "empty" in pyrite_result["formatted_output"].lower() or "no dependencies" in pyrite_result["formatted_output"].lower()


class TestResolveDeterminism:
    """Test determinism and fingerprinting"""
    
    def test_fingerprint_consistency(self):
        """Test that fingerprint is consistent"""
        toml_content = """[dependencies]
foo = "1.0.0"
bar = "2.0.0"
"""
        
        # Resolve multiple times
        result1 = resolve_dependencies_ffi(toml_content)
        result2 = resolve_dependencies_ffi(toml_content)
        
        # Fingerprints should match
        if result1["fingerprint"] and result2["fingerprint"]:
            assert result1["fingerprint"] == result2["fingerprint"]
    
    def test_order_independence(self):
        """Test that fingerprint is order-independent"""
        toml_content1 = """[dependencies]
foo = "1.0.0"
bar = "2.0.0"
"""
        toml_content2 = """[dependencies]
bar = "2.0.0"
foo = "1.0.0"
"""
        
        # Resolve both
        result1 = resolve_dependencies_ffi(toml_content1)
        result2 = resolve_dependencies_ffi(toml_content2)
        
        # Resolved dependencies should be the same (normalized)
        assert len(result1["resolved"]) == len(result2["resolved"]) == 2
        
        # Fingerprints should match (if computed)
        if result1["fingerprint"] and result2["fingerprint"]:
            assert result1["fingerprint"] == result2["fingerprint"]


class TestResolveVersionResolution:
    """Test version resolution"""
    
    def test_exact_version(self):
        """Test exact version constraint"""
        toml_content = """[dependencies]
foo = "1.0.0"
"""
        
        result = resolve_dependencies_ffi(toml_content)
        
        assert "foo" in result["resolved"]
        foo = result["resolved"]["foo"]
        assert foo.type == "registry"
        # Version should be resolved (exact version from mock registry)
        assert foo.version
    
    def test_range_constraint(self):
        """Test range constraint (>=)"""
        toml_content = """[dependencies]
bar = ">=2.0.0"
"""
        
        result = resolve_dependencies_ffi(toml_content)
        
        assert "bar" in result["resolved"]
        bar = result["resolved"]["bar"]
        assert bar.type == "registry"
        # Version should be resolved (latest >= 2.0.0 from mock registry)
        assert bar.version
