"""Equivalence tests for dependency source parsing

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
from quarry.bridge.dep_source_bridge import _parse_dependency_source_ffi, _parse_dependency_source_python


class TestRegistryStringEquivalence:
    """Test registry dependency (string) equivalence"""
    
    def test_simple_version(self):
        """Simple version string"""
        name = "foo"
        value = "1.0.0"
        expected = DependencySource(type="registry", version="1.0.0")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_version_constraint_greater_equal(self):
        """Version constraint >="""
        name = "foo"
        value = ">=1.0.0"
        expected = DependencySource(type="registry", version=">=1.0.0")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_version_constraint_pessimistic(self):
        """Version constraint ~>"""
        name = "foo"
        value = "~>1.0"
        expected = DependencySource(type="registry", version="~>1.0")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_version_constraint_wildcard(self):
        """Version constraint *"""
        name = "foo"
        value = "*"
        expected = DependencySource(type="registry", version="*")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_empty_string(self):
        """Empty version string"""
        name = "foo"
        value = ""
        expected = DependencySource(type="registry", version="")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash


class TestRegistryDictEquivalence:
    """Test registry dependency (dict with version) equivalence"""
    
    def test_version_only(self):
        """Dict with version only"""
        name = "foo"
        value = {"version": "1.0.0"}
        expected = DependencySource(type="registry", version="1.0.0")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_version_with_checksum(self):
        """Dict with version and checksum"""
        name = "foo"
        value = {"version": "1.0.0", "checksum": "sha256:abc123"}
        expected = DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash


class TestGitEquivalence:
    """Test git dependency equivalence"""
    
    def test_git_with_branch(self):
        """Git dependency with branch"""
        name = "foo"
        value = {"git": "https://github.com/user/foo.git", "branch": "main"}
        expected = DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="main")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_git_with_tag(self):
        """Git dependency with tag"""
        name = "foo"
        value = {"git": "https://github.com/user/foo.git", "tag": "v1.0.0"}
        expected = DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="v1.0.0")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_git_with_rev(self):
        """Git dependency with rev"""
        name = "foo"
        value = {"git": "https://github.com/user/foo.git", "rev": "abc123"}
        expected = DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="abc123")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_git_branch_priority(self):
        """Git dependency: branch takes priority over tag/rev"""
        name = "foo"
        value = {"git": "https://github.com/user/foo.git", "branch": "main", "tag": "v1.0.0", "rev": "abc123"}
        expected = DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="main")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_git_tag_priority(self):
        """Git dependency: tag takes priority over rev"""
        name = "foo"
        value = {"git": "https://github.com/user/foo.git", "tag": "v1.0.0", "rev": "abc123"}
        expected = DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="v1.0.0")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_git_with_commit(self):
        """Git dependency with commit"""
        name = "foo"
        value = {"git": "https://github.com/user/foo.git", "branch": "main", "commit": "def456"}
        expected = DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="main", commit="def456")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash


class TestPathEquivalence:
    """Test path dependency equivalence"""
    
    def test_path_only(self):
        """Path dependency without hash"""
        name = "foo"
        value = {"path": "../foo"}
        expected = DependencySource(type="path", path="../foo")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_path_with_hash(self):
        """Path dependency with hash"""
        name = "foo"
        value = {"path": "../foo", "hash": "sha256:abc123"}
        expected = DependencySource(type="path", path="../foo", hash="sha256:abc123")
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash


class TestInvalidInputEquivalence:
    """Test invalid input equivalence"""
    
    def test_none_value(self):
        """None value"""
        name = "foo"
        value = None
        expected = None
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_empty_dict(self):
        """Empty dict"""
        name = "foo"
        value = {}
        expected = None
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_dict_without_valid_keys(self):
        """Dict without git, path, or version"""
        name = "foo"
        value = {"invalid": "value"}
        expected = None
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_list_value(self):
        """List value (invalid)"""
        name = "foo"
        value = ["1.0.0"]
        expected = None
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash
    
    def test_int_value(self):
        """Integer value (invalid)"""
        name = "foo"
        value = 123
        expected = None
        
        python_result = _parse_dependency_source_python(name, value)
        pyrite_result = _parse_dependency_source_ffi(name, value)
        
        # Check that both match expected (compare by attributes since dataclass __eq__ might have issues)
        if expected is None:
            assert python_result is None, f"Python result should be None, got: {python_result}"
            assert pyrite_result is None, f"Pyrite result should be None, got: {pyrite_result}"
        else:
            assert python_result is not None, f"Python result should not be None"
            assert pyrite_result is not None, f"Pyrite result should not be None"
            assert python_result.type == expected.type == pyrite_result.type
            assert python_result.version == expected.version == pyrite_result.version
            assert python_result.git_url == expected.git_url == pyrite_result.git_url
            assert python_result.git_branch == expected.git_branch == pyrite_result.git_branch
            assert python_result.path == expected.path == pyrite_result.path
            assert python_result.checksum == expected.checksum == pyrite_result.checksum
            assert python_result.commit == expected.commit == pyrite_result.commit
            assert python_result.hash == expected.hash == pyrite_result.hash


class TestIntegrationEquivalence:
    """Integration tests using parse_quarry_toml"""
    
    def test_parse_quarry_toml_registry(self):
        """Test parse_quarry_toml with registry dependency"""
        from quarry.dependency import parse_quarry_toml
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_file = Path(tmpdir) / "Quarry.toml"
            toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = "1.0.0"
""")
            
            deps = parse_quarry_toml(str(toml_file))
            assert "foo" in deps
            assert deps["foo"].type == "registry"
            assert deps["foo"].version == "1.0.0"
    
    def test_parse_quarry_toml_git(self):
        """Test parse_quarry_toml with git dependency"""
        from quarry.dependency import parse_quarry_toml
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_file = Path(tmpdir) / "Quarry.toml"
            toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = { git = "https://github.com/user/foo.git", branch = "main" }
""")
            
            deps = parse_quarry_toml(str(toml_file))
            assert "foo" in deps
            assert deps["foo"].type == "git"
            assert deps["foo"].git_url == "https://github.com/user/foo.git"
            assert deps["foo"].git_branch == "main"
    
    def test_parse_quarry_toml_path(self):
        """Test parse_quarry_toml with path dependency"""
        from quarry.dependency import parse_quarry_toml
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            toml_file = Path(tmpdir) / "Quarry.toml"
            toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
local_dep = { path = "../local_dep" }
""")
            
            deps = parse_quarry_toml(str(toml_file))
            assert "local_dep" in deps
            assert deps["local_dep"].type == "path"
            assert deps["local_dep"].path == "../local_dep"
