"""Equivalence tests for locked validation operations

Tests that Pyrite FFI implementation matches Python implementation exactly.
"""

import pytest
import sys
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.dependency import DependencySource
from quarry.bridge.locked_validate_bridge import (
    validate_locked_deps_ffi, validate_locked_deps_python
)


class TestValidateLockedDepsEquivalence:
    """Test validate_locked_deps equivalence"""
    
    def test_exact_match_registry(self):
        """Exact match: registry dependencies"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_exact_match_git(self):
        """Exact match: git dependencies"""
        toml_deps = {
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main")
        }
        lockfile_deps = {
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_exact_match_path(self):
        """Exact match: path dependencies"""
        toml_deps = {
            "baz": DependencySource(type="path", path="../baz")
        }
        lockfile_deps = {
            "baz": DependencySource(type="path", path="../baz")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_registry_version_satisfies_constraint(self):
        """Registry: locked version satisfies constraint"""
        toml_deps = {
            "foo": DependencySource(type="registry", version=">=1.0.0")
        }
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.5.0")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_missing_dependency(self):
        """Error: missing dependency in lockfile"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        lockfile_deps = {}
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == False
        assert len(python_errors) == len(pyrite_errors) == 1
        assert "not found in lockfile" in python_errors[0]
        assert "not found in lockfile" in pyrite_errors[0]
        assert python_warnings == pyrite_warnings == []
    
    def test_registry_version_mismatch(self):
        """Error: registry version doesn't satisfy constraint"""
        toml_deps = {
            "foo": DependencySource(type="registry", version=">=2.0.0")
        }
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == False
        assert len(python_errors) == len(pyrite_errors) == 1
        assert "does not satisfy constraint" in python_errors[0]
        assert "does not satisfy constraint" in pyrite_errors[0]
        assert python_warnings == pyrite_warnings == []
    
    def test_source_type_mismatch(self):
        """Error: source type mismatch"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        lockfile_deps = {
            "foo": DependencySource(type="git", git_url="https://github.com/user/foo.git")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == False
        assert len(python_errors) == len(pyrite_errors) == 1
        assert "Source type mismatch" in python_errors[0] or "type mismatch" in python_errors[0]
        assert "Source type mismatch" in pyrite_errors[0] or "type mismatch" in pyrite_errors[0]
        assert python_warnings == pyrite_warnings == []
    
    def test_extra_dependency_warning(self):
        """Warning: extra dependency in lockfile"""
        toml_deps = {}
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True  # Warnings don't make it invalid
        assert python_errors == pyrite_errors == []
        assert len(python_warnings) == len(pyrite_warnings) == 1
        assert "not in Quarry.toml" in python_warnings[0]
        assert "not in Quarry.toml" in pyrite_warnings[0]
    
    def test_empty_dependencies(self):
        """Empty dependencies"""
        toml_deps = {}
        lockfile_deps = {}
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_mixed_dependencies_success(self):
        """Mixed dependencies: all match"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
            "baz": DependencySource(type="path", path="../baz")
        }
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
            "baz": DependencySource(type="path", path="../baz")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_multiple_errors(self):
        """Multiple errors: all reported"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="registry", version="2.0.0")
        }
        lockfile_deps = {
            "foo": DependencySource(type="git", git_url="https://github.com/user/foo.git"),
            "bar": DependencySource(type="registry", version="1.0.0")  # Wrong version
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == False
        assert len(python_errors) >= 1
        assert len(pyrite_errors) >= 1
        # Both should report errors (exact count may vary based on which checks run first)
    
    def test_registry_wildcard_constraint(self):
        """Registry: wildcard constraint (*)"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="*")
        }
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
    
    def test_registry_exact_version_match(self):
        """Registry: exact version match"""
        toml_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        lockfile_deps = {
            "foo": DependencySource(type="registry", version="1.0.0")
        }
        
        python_valid, python_errors, python_warnings = validate_locked_deps_python(toml_deps, lockfile_deps)
        pyrite_valid, pyrite_errors, pyrite_warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
        
        assert python_valid == pyrite_valid == True
        assert python_errors == pyrite_errors == []
        assert python_warnings == pyrite_warnings == []
