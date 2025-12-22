"""Equivalence tests for dependency normalization and fingerprinting

Tests that Python and Pyrite implementations produce identical results.
"""

import pytest
import json
import hashlib
from pathlib import Path
import sys

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.dependency import DependencySource
from quarry.bridge.dep_fingerprint_bridge import (
    normalize_dependency_source_ffi,
    normalize_dependency_source_python,
    normalize_dependency_set_ffi,
    normalize_dependency_set_python,
    compute_resolution_fingerprint_ffi,
    compute_resolution_fingerprint_python,
)


class TestNormalizeDependencySource:
    """Test normalize_dependency_source function"""
    
    def test_registry_normalization(self):
        """Test normalization of registry dependency"""
        source = DependencySource(type="REGISTRY", version="1.0.0", checksum="sha256:ABC123")
        
        # Python implementation
        python_result = normalize_dependency_source_python(source)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_source_ffi(source)
        
        assert python_result.type == pyrite_result.type == "registry"
        assert python_result.version == pyrite_result.version == "1.0.0"
        assert python_result.checksum == pyrite_result.checksum == "sha256:abc123"
    
    def test_git_normalization(self):
        """Test normalization of git dependency"""
        source = DependencySource(type="GIT", git_url="https://github.com/user/repo.git", git_branch="main")
        
        # Python implementation
        python_result = normalize_dependency_source_python(source)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_source_ffi(source)
        
        assert python_result.type == pyrite_result.type == "git"
        assert python_result.git_url == pyrite_result.git_url == "https://github.com/user/repo.git"
        assert python_result.git_branch == pyrite_result.git_branch == "main"
    
    def test_path_normalization(self):
        """Test normalization of path dependency"""
        source = DependencySource(type="PATH", path="../dep", hash="sha256:XYZ789")
        
        # Python implementation
        python_result = normalize_dependency_source_python(source)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_source_ffi(source)
        
        assert python_result.type == pyrite_result.type == "path"
        assert python_result.path == pyrite_result.path == "../dep"
        assert python_result.hash == pyrite_result.hash == "sha256:xyz789"
    
    def test_empty_optional_fields(self):
        """Test normalization with empty optional fields"""
        source = DependencySource(type="registry", version="1.0.0")
        
        # Python implementation
        python_result = normalize_dependency_source_python(source)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_source_ffi(source)
        
        assert python_result.type == pyrite_result.type == "registry"
        assert python_result.version == pyrite_result.version == "1.0.0"
        assert python_result.checksum == pyrite_result.checksum is None


class TestNormalizeDependencySet:
    """Test normalize_dependency_set function"""
    
    def test_sorting_by_name(self):
        """Test that dependencies are sorted by name"""
        deps = {
            "zebra": DependencySource(type="registry", version="1.0.0"),
            "alpha": DependencySource(type="registry", version="2.0.0"),
            "beta": DependencySource(type="registry", version="3.0.0"),
        }
        
        # Python implementation
        python_result = normalize_dependency_set_python(deps)
        python_names = list(python_result.keys())
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_set_ffi(deps)
        pyrite_names = list(pyrite_result.keys())
        
        assert python_names == pyrite_names == ["alpha", "beta", "zebra"]
    
    def test_mixed_dependencies(self):
        """Test normalization of mixed dependency types"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:ABC123"),
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
            "baz": DependencySource(type="path", path="../baz", hash="sha256:XYZ789"),
        }
        
        # Python implementation
        python_result = normalize_dependency_set_python(deps)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_set_ffi(deps)
        
        # Check sorting
        assert list(python_result.keys()) == list(pyrite_result.keys()) == ["bar", "baz", "foo"]
        
        # Check normalization
        assert python_result["foo"].type == pyrite_result["foo"].type == "registry"
        assert python_result["foo"].checksum == pyrite_result["foo"].checksum == "sha256:abc123"
        assert python_result["bar"].type == pyrite_result["bar"].type == "git"
        assert python_result["baz"].type == pyrite_result["baz"].type == "path"
    
    def test_empty_set(self):
        """Test normalization of empty dependency set"""
        deps = {}
        
        # Python implementation
        python_result = normalize_dependency_set_python(deps)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_set_ffi(deps)
        
        assert python_result == pyrite_result == {}
    
    def test_single_dependency(self):
        """Test normalization of single dependency"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
        }
        
        # Python implementation
        python_result = normalize_dependency_set_python(deps)
        
        # Pyrite implementation
        pyrite_result = normalize_dependency_set_ffi(deps)
        
        assert python_result == pyrite_result
        assert list(python_result.keys()) == ["foo"]


class TestComputeResolutionFingerprint:
    """Test compute_resolution_fingerprint function"""
    
    def test_empty_set_fingerprint(self):
        """Test fingerprint of empty dependency set"""
        deps = {}
        
        # Python implementation
        python_fp = compute_resolution_fingerprint_python(deps)
        
        # Pyrite implementation
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        assert python_fp == pyrite_fp
        assert len(python_fp) == 64  # SHA-256 produces 64 hex characters
        
        # Empty JSON object should produce known hash
        empty_json = json.dumps({}, sort_keys=True, separators=(',', ':')).encode('utf-8')
        expected_hash = hashlib.sha256(empty_json).hexdigest()
        assert python_fp == expected_hash
    
    def test_single_registry_fingerprint(self):
        """Test fingerprint of single registry dependency"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123"),
        }
        
        # Python implementation
        python_fp = compute_resolution_fingerprint_python(deps)
        
        # Pyrite implementation
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        assert python_fp == pyrite_fp
        assert len(python_fp) == 64
    
    def test_single_git_fingerprint(self):
        """Test fingerprint of single git dependency"""
        deps = {
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
        }
        
        # Python implementation
        python_fp = compute_resolution_fingerprint_python(deps)
        
        # Pyrite implementation
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        assert python_fp == pyrite_fp
        assert len(python_fp) == 64
    
    def test_single_path_fingerprint(self):
        """Test fingerprint of single path dependency"""
        deps = {
            "baz": DependencySource(type="path", path="../baz", hash="sha256:xyz789"),
        }
        
        # Python implementation
        python_fp = compute_resolution_fingerprint_python(deps)
        
        # Pyrite implementation
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        assert python_fp == pyrite_fp
        assert len(python_fp) == 64
    
    def test_mixed_fingerprint(self):
        """Test fingerprint of mixed dependencies"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123"),
            "bar": DependencySource(type="git", git_url="https://github.com/user/bar.git", git_branch="main"),
            "baz": DependencySource(type="path", path="../baz", hash="sha256:xyz789"),
        }
        
        # Python implementation
        python_fp = compute_resolution_fingerprint_python(deps)
        
        # Pyrite implementation
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        assert python_fp == pyrite_fp
        assert len(python_fp) == 64
    
    def test_order_independence(self):
        """Test that fingerprint is order-independent"""
        deps1 = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="registry", version="2.0.0"),
        }
        deps2 = {
            "bar": DependencySource(type="registry", version="2.0.0"),
            "foo": DependencySource(type="registry", version="1.0.0"),
        }
        
        # Python implementation
        python_fp1 = compute_resolution_fingerprint_python(deps1)
        python_fp2 = compute_resolution_fingerprint_python(deps2)
        
        # Pyrite implementation
        pyrite_fp1 = compute_resolution_fingerprint_ffi(deps1)
        pyrite_fp2 = compute_resolution_fingerprint_ffi(deps2)
        
        # Same dependencies in different order should produce same fingerprint
        assert python_fp1 == python_fp2
        assert pyrite_fp1 == pyrite_fp2
        assert python_fp1 == pyrite_fp1
    
    def test_field_order_independence(self):
        """Test that fingerprint is independent of field order in JSON"""
        # This is tested implicitly by using deterministic JSON serialization
        # (sort_keys=True ensures field order is consistent)
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123"),
        }
        
        # Python implementation
        python_fp = compute_resolution_fingerprint_python(deps)
        
        # Pyrite implementation
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        assert python_fp == pyrite_fp
    
    def test_checksum_case_normalization(self):
        """Test that checksum case is normalized"""
        deps1 = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:ABC123"),
        }
        deps2 = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123"),
        }
        
        # Python implementation
        python_fp1 = compute_resolution_fingerprint_python(deps1)
        python_fp2 = compute_resolution_fingerprint_python(deps2)
        
        # Pyrite implementation
        pyrite_fp1 = compute_resolution_fingerprint_ffi(deps1)
        pyrite_fp2 = compute_resolution_fingerprint_ffi(deps2)
        
        # Same checksum (different case) should produce same fingerprint
        assert python_fp1 == python_fp2
        assert pyrite_fp1 == pyrite_fp2
        assert python_fp1 == pyrite_fp1
    
    def test_type_case_normalization(self):
        """Test that type case is normalized"""
        deps1 = {
            "foo": DependencySource(type="REGISTRY", version="1.0.0"),
        }
        deps2 = {
            "foo": DependencySource(type="registry", version="1.0.0"),
        }
        
        # Python implementation
        python_fp1 = compute_resolution_fingerprint_python(deps1)
        python_fp2 = compute_resolution_fingerprint_python(deps2)
        
        # Pyrite implementation
        pyrite_fp1 = compute_resolution_fingerprint_ffi(deps1)
        pyrite_fp2 = compute_resolution_fingerprint_ffi(deps2)
        
        # Same type (different case) should produce same fingerprint
        assert python_fp1 == python_fp2
        assert pyrite_fp1 == pyrite_fp2
        assert python_fp1 == pyrite_fp1


class TestGoldenFingerprints:
    """Test golden fingerprints (known good values)"""
    
    def test_empty_set_golden(self):
        """Test golden fingerprint for empty set"""
        deps = {}
        
        # Compute fingerprint
        fp = compute_resolution_fingerprint_python(deps)
        
        # Verify against expected (empty JSON object)
        empty_json = json.dumps({}, sort_keys=True, separators=(',', ':')).encode('utf-8')
        expected = hashlib.sha256(empty_json).hexdigest()
        
        assert fp == expected
    
    def test_registry_golden(self):
        """Test golden fingerprint for registry dependency"""
        deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123"),
        }
        
        # Compute fingerprint
        python_fp = compute_resolution_fingerprint_python(deps)
        pyrite_fp = compute_resolution_fingerprint_ffi(deps)
        
        # Both should match
        assert python_fp == pyrite_fp
        
        # Verify manually computed
        canonical = {"foo": {"type": "registry", "version": "1.0.0", "checksum": "sha256:abc123"}}
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode('utf-8')
        expected = hashlib.sha256(canonical_json).hexdigest()
        
        assert python_fp == expected
