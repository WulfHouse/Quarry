"""Equivalence tests for TOML parsing functions

Tests that the Pyrite/C implementation (via toml_bridge) produces
identical results to the Python implementation.
"""

import pytest
import sys
from pathlib import Path

pytestmark = pytest.mark.fast  # All tests in this file are fast unit tests

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.bridge.toml_bridge import _parse_dependencies_simple, _parse_workspace_simple


class TestParseDependenciesSimple:
    """Test _parse_dependencies_simple function"""
    
    def test_basic_dependencies(self):
        """Test basic dependencies section"""
        toml_text = """[dependencies]
pyrite-compiler = "1.0.0"
quarry = "2.1.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"pyrite-compiler": "1.0.0", "quarry": "2.1.0"}
    
    def test_single_dependency(self):
        """Test with single dependency"""
        toml_text = """[dependencies]
utils = "1.0.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"utils": "1.0.0"}
    
    def test_empty_dependencies(self):
        """Test empty dependencies section"""
        toml_text = """[dependencies]
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {}
    
    def test_no_dependencies_section(self):
        """Test TOML without dependencies section"""
        toml_text = """[package]
name = "test"
version = "0.1.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {}
    
    def test_stops_at_next_section(self):
        """Test that parsing stops at next section"""
        toml_text = """[dependencies]
foo = "1.0.0"
bar = "2.0.0"

[dev-dependencies]
baz = "3.0.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"foo": "1.0.0", "bar": "2.0.0"}
        assert "baz" not in result
    
    def test_single_quotes(self):
        """Test with single quotes"""
        toml_text = """[dependencies]
foo = '1.0.0'
bar = '2.0.0'
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"foo": "1.0.0", "bar": "2.0.0"}
    
    def test_whitespace_variations(self):
        """Test with various whitespace"""
        toml_text = """[dependencies]
  foo  =  "1.0.0"
bar="2.0.0"
  baz = "3.0.0"  
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"foo": "1.0.0", "bar": "2.0.0", "baz": "3.0.0"}
    
    def test_with_package_section(self):
        """Test with package section before dependencies"""
        toml_text = """[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = "1.0.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"foo": "1.0.0"}
    
    def test_blank_lines(self):
        """Test with blank lines"""
        toml_text = """[dependencies]

foo = "1.0.0"

bar = "2.0.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"foo": "1.0.0", "bar": "2.0.0"}
    
    def test_complex_version_strings(self):
        """Test with complex version strings"""
        toml_text = """[dependencies]
foo = "1.2.3-alpha.1"
bar = ">=1.0.0"
"""
        result = _parse_dependencies_simple(toml_text)
        assert result == {"foo": "1.2.3-alpha.1", "bar": ">=1.0.0"}


class TestParseWorkspaceSimple:
    """Test _parse_workspace_simple function"""
    
    def test_basic_workspace(self):
        """Test basic workspace members"""
        workspace_text = """[workspace]
members = ["processor", "utils"]
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["processor", "utils"]
    
    def test_single_member(self):
        """Test with single member"""
        workspace_text = """[workspace]
members = ["pkg1"]
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["pkg1"]
    
    def test_empty_members(self):
        """Test empty members array"""
        workspace_text = """[workspace]
members = []
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == []
    
    def test_no_workspace_section(self):
        """Test TOML without workspace section"""
        workspace_text = """[package]
name = "test"
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == []
    
    def test_stops_at_next_section(self):
        """Test that parsing stops at next section"""
        workspace_text = """[workspace]
members = ["pkg1", "pkg2"]

[package]
name = "test"
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["pkg1", "pkg2"]
    
    def test_whitespace_variations(self):
        """Test with various whitespace"""
        workspace_text = """[workspace]
members = [ "pkg1" , "pkg2" , "pkg3" ]
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["pkg1", "pkg2", "pkg3"]
    
    def test_trailing_comma(self):
        """Test with trailing comma (if supported)"""
        workspace_text = """[workspace]
members = ["pkg1", "pkg2",]
"""
        result = _parse_workspace_simple(workspace_text)
        # Should handle trailing comma gracefully
        assert "pkg1" in result
        assert "pkg2" in result
    
    def test_multiple_members(self):
        """Test with multiple members"""
        workspace_text = """[workspace]
members = ["pkg1", "pkg2", "pkg3", "pkg4"]
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["pkg1", "pkg2", "pkg3", "pkg4"]
    
    def test_blank_lines(self):
        """Test with blank lines"""
        workspace_text = """[workspace]

members = ["pkg1", "pkg2"]
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["pkg1", "pkg2"]
    
    def test_members_on_same_line(self):
        """Test members array on same line as key"""
        workspace_text = """[workspace]
members = ["pkg1", "pkg2"]
"""
        result = _parse_workspace_simple(workspace_text)
        assert result == ["pkg1", "pkg2"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
