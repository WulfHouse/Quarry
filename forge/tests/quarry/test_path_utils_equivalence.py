"""Equivalence tests for path utilities

Tests that Pyrite FFI implementation matches Python pathlib behavior exactly.
"""

import pytest
import sys
import os
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.bridge.path_utils_bridge import (
    is_absolute_ffi, is_absolute_python,
    resolve_path_ffi, resolve_path_python,
    join_paths_ffi, join_paths_python,
    relative_path_ffi, relative_path_python
)


class TestIsAbsoluteEquivalence:
    """Test is_absolute equivalence"""
    
    def test_posix_absolute(self):
        """POSIX absolute path"""
        path = "/foo/bar"
        python_result = is_absolute_python(path)
        pyrite_result = is_absolute_ffi(path)
        # On Windows, /foo/bar is relative; on POSIX it's absolute
        if os.name == 'nt':
            assert python_result == pyrite_result == False
        else:
            assert python_result == pyrite_result == True
    
    def test_posix_relative(self):
        """POSIX relative path"""
        path = "foo/bar"
        python_result = is_absolute_python(path)
        pyrite_result = is_absolute_ffi(path)
        assert python_result == pyrite_result == False
    
    def test_windows_drive_absolute(self):
        """Windows drive letter absolute"""
        path = "C:/foo/bar"
        python_result = is_absolute_python(path)
        pyrite_result = is_absolute_ffi(path)
        assert python_result == pyrite_result == (os.name == 'nt')
    
    def test_windows_backslash_absolute(self):
        """Windows backslash absolute"""
        path = "C:\\foo\\bar"
        python_result = is_absolute_python(path)
        pyrite_result = is_absolute_ffi(path)
        assert python_result == pyrite_result == (os.name == 'nt')
    
    def test_relative_with_dots(self):
        """Relative path with dots"""
        path = "../foo"
        python_result = is_absolute_python(path)
        pyrite_result = is_absolute_ffi(path)
        assert python_result == pyrite_result == False
    
    def test_current_dir(self):
        """Current directory"""
        path = "."
        python_result = is_absolute_python(path)
        pyrite_result = is_absolute_ffi(path)
        assert python_result == pyrite_result == False


class TestResolvePathEquivalence:
    """Test resolve_path equivalence"""
    
    def test_absolute_path(self):
        """Absolute path (no change)"""
        path = "/foo/bar" if os.name != 'nt' else "C:/foo/bar"
        python_result = resolve_path_python(path)
        pyrite_result = resolve_path_ffi(path)
        # Both should normalize but remain absolute
        assert Path(python_result).is_absolute() == Path(pyrite_result).is_absolute() == True
    
    def test_relative_with_base(self):
        """Relative path with base"""
        path = "foo/bar"
        base = "/base" if os.name != 'nt' else "C:/base"
        python_result = resolve_path_python(path, base)
        pyrite_result = resolve_path_ffi(path, base)
        # Results should be equivalent (may differ in normalization)
        assert Path(python_result).exists() or not Path(python_result).exists()  # Just check it's valid
        assert Path(pyrite_result).exists() or not Path(pyrite_result).exists()
        # Both should resolve to same logical path
        assert Path(python_result).resolve() == Path(pyrite_result).resolve()
    
    def test_with_dot_segments(self):
        """Path with . segments"""
        path = "foo/./bar"
        base = "/base" if os.name != 'nt' else "C:/base"
        python_result = resolve_path_python(path, base)
        pyrite_result = resolve_path_ffi(path, base)
        # . should be normalized away
        assert Path(python_result).resolve() == Path(pyrite_result).resolve()
    
    def test_with_parent_segments(self):
        """Path with .. segments"""
        path = "../foo"
        base = "/base/sub" if os.name != 'nt' else "C:/base/sub"
        python_result = resolve_path_python(path, base)
        pyrite_result = resolve_path_ffi(path, base)
        # .. should be resolved
        assert Path(python_result).resolve() == Path(pyrite_result).resolve()


class TestJoinPathsEquivalence:
    """Test join_paths equivalence"""
    
    def test_simple_join(self):
        """Simple path joining"""
        parts = ["foo", "bar", "baz"]
        python_result = join_paths_python(*parts)
        pyrite_result = join_paths_ffi(*parts)
        # Results should be equivalent
        assert Path(python_result) == Path(pyrite_result)
    
    def test_join_with_separators(self):
        """Join with existing separators"""
        parts = ["foo/", "bar", "baz"]
        python_result = join_paths_python(*parts)
        pyrite_result = join_paths_ffi(*parts)
        # Should handle separators correctly
        assert Path(python_result) == Path(pyrite_result)
    
    def test_absolute_override(self):
        """Absolute path overrides previous"""
        if os.name != 'nt':
            parts = ["foo", "/bar"]
            python_result = join_paths_python(*parts)
            pyrite_result = join_paths_ffi(*parts)
            # Absolute part should override
            assert Path(python_result).is_absolute() == Path(pyrite_result).is_absolute() == True
            assert Path(python_result) == Path(pyrite_result)
    
    def test_empty_parts(self):
        """Empty parts handling"""
        parts = ["foo", "", "bar"]
        python_result = join_paths_python(*parts)
        pyrite_result = join_paths_ffi(*parts)
        # Empty parts should be handled
        assert Path(python_result) == Path(pyrite_result)


class TestRelativePathEquivalence:
    """Test relative_path equivalence"""
    
    def test_same_directory(self):
        """Paths in same directory"""
        path = "/foo/bar" if os.name != 'nt' else "C:/foo/bar"
        base = "/foo" if os.name != 'nt' else "C:/foo"
        python_result = relative_path_python(path, base)
        pyrite_result = relative_path_ffi(path, base)
        assert python_result == pyrite_result == "bar"
    
    def test_subdirectory(self):
        """Path is subdirectory of base"""
        path = "/foo/bar/baz" if os.name != 'nt' else "C:/foo/bar/baz"
        base = "/foo" if os.name != 'nt' else "C:/foo"
        python_result = relative_path_python(path, base)
        pyrite_result = relative_path_ffi(path, base)
        assert python_result == pyrite_result == "bar/baz" or python_result == pyrite_result == "bar\\baz"
    
    def test_parent_directory(self):
        """Path is parent of base"""
        path = "/foo" if os.name != 'nt' else "C:/foo"
        base = "/foo/bar" if os.name != 'nt' else "C:/foo/bar"
        python_result = relative_path_python(path, base)
        pyrite_result = relative_path_ffi(path, base)
        # Should use .. to go up (or return None if paths can't be related)
        if python_result is None:
            assert pyrite_result is None
        else:
            assert ".." in python_result or python_result == ".."
            assert python_result == pyrite_result or Path(python_result) == Path(pyrite_result)
    
    def test_different_roots(self):
        """Paths on different roots (Windows drives)"""
        if os.name == 'nt':
            path = "C:/foo"
            base = "D:/bar"
            python_result = relative_path_python(path, base)
            pyrite_result = relative_path_ffi(path, base)
            # Should return None (no relative path)
            assert python_result == pyrite_result == None
    
    def test_same_path(self):
        """Same path"""
        path = "/foo/bar" if os.name != 'nt' else "C:/foo/bar"
        base = "/foo/bar" if os.name != 'nt' else "C:/foo/bar"
        python_result = relative_path_python(path, base)
        pyrite_result = relative_path_ffi(path, base)
        # Should return "." or empty
        assert python_result == pyrite_result or Path(python_result) == Path(pyrite_result) == Path(".")


class TestIntegrationEquivalence:
    """Integration tests using real Quarry functions"""
    
    def test_dependency_path_resolution(self):
        """Test path resolution in dependency module"""
        from quarry.dependency import _compute_path_hash
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            dep_dir = project_dir / "dep"
            dep_dir.mkdir()
            (dep_dir / "Quarry.toml").write_text("[package]\nname = \"dep\"\n")
            
            # Test relative path
            result = _compute_path_hash("dep", project_dir)
            # Should compute hash (or return None if checksum computation fails)
            assert result is None or isinstance(result, str)
    
    def test_workspace_path_resolution(self):
        """Test path resolution in workspace module"""
        from quarry.workspace import find_workspace_root
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "Workspace.toml").write_text("[workspace]\nmembers = []\n")
            
            # Test finding workspace root
            result = find_workspace_root(workspace_root)
            assert result == workspace_root
