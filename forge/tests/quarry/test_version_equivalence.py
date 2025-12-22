"""Equivalence tests for version comparison functions

Tests that the Pyrite/C implementation (via version_bridge) produces
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

from quarry.bridge.version_bridge import _compare_versions, _version_satisfies_constraint, _latest_version, _select_version, _is_semver, _is_valid_package_name, _normalize_string


class TestCompareVersions:
    """Test compare_versions function"""
    
    def test_equal_versions(self):
        """Test that equal versions return 0"""
        assert _compare_versions("1.0.0", "1.0.0") == 0
        assert _compare_versions("2.5.3", "2.5.3") == 0
    
    def test_v1_less_than_v2(self):
        """Test that v1 < v2 returns -1"""
        assert _compare_versions("1.0.0", "2.0.0") == -1
        assert _compare_versions("1.2.3", "1.2.4") == -1
        assert _compare_versions("0.9.0", "1.0.0") == -1
    
    def test_v1_greater_than_v2(self):
        """Test that v1 > v2 returns 1"""
        assert _compare_versions("2.0.0", "1.0.0") == 1
        assert _compare_versions("1.2.4", "1.2.3") == 1
        assert _compare_versions("1.10.0", "1.2.0") == 1  # 10 > 2, not string comparison
    
    def test_different_length_versions(self):
        """Test versions with different numbers of parts"""
        assert _compare_versions("1.0", "1.0.0") == 0
        assert _compare_versions("1.0.0", "1.0") == 0
        assert _compare_versions("1.0", "1.0.1") == -1
        assert _compare_versions("1.0.1", "1.0") == 1


class TestVersionSatisfiesConstraint:
    """Test version_satisfies_constraint function"""
    
    def test_wildcard(self):
        """Test that '*' matches any version"""
        assert _version_satisfies_constraint("1.0.0", "*") == True
        assert _version_satisfies_constraint("2.5.3", "*") == True
        assert _version_satisfies_constraint("0.1.0", "*") == True
    
    def test_exact_match(self):
        """Test exact version matching"""
        assert _version_satisfies_constraint("1.0.0", "1.0.0") == True
        assert _version_satisfies_constraint("2.0.0", "1.0.0") == False
        assert _version_satisfies_constraint("1.5.0", "1.0.0") == False
    
    def test_greater_or_equal(self):
        """Test '>=' constraint"""
        assert _version_satisfies_constraint("2.0.0", ">=1.0.0") == True
        assert _version_satisfies_constraint("1.0.0", ">=1.0.0") == True
        assert _version_satisfies_constraint("1.5.0", ">=1.0.0") == True
        assert _version_satisfies_constraint("0.9.0", ">=1.0.0") == False
    
    def test_greater_or_equal_with_whitespace(self):
        """Test '>=' constraint with whitespace"""
        assert _version_satisfies_constraint("2.0.0", ">= 1.0.0") == True
        assert _version_satisfies_constraint("1.0.0", ">=  1.0.0") == True
    
    def test_pessimistic_constraint(self):
        """Test '~>' pessimistic constraint"""
        assert _version_satisfies_constraint("1.5.0", "~>1.0") == True
        assert _version_satisfies_constraint("1.0.0", "~>1.0") == True
        assert _version_satisfies_constraint("1.9.9", "~>1.0") == True
        assert _version_satisfies_constraint("2.0.0", "~>1.0") == False
        assert _version_satisfies_constraint("0.9.0", "~>1.0") == False
    
    def test_pessimistic_constraint_with_whitespace(self):
        """Test '~>' constraint with whitespace"""
        assert _version_satisfies_constraint("1.5.0", "~> 1.0") == True


class TestLatestVersion:
    """Test latest_version function"""
    
    def test_single_version(self):
        """Test with single version"""
        assert _latest_version(["1.0.0"]) == "1.0.0"
    
    def test_multiple_versions(self):
        """Test with multiple versions"""
        assert _latest_version(["1.0.0", "2.0.0", "1.5.0"]) == "2.0.0"
        assert _latest_version(["1.0.0", "1.5.0", "2.0.0"]) == "2.0.0"
        assert _latest_version(["2.0.0", "1.0.0", "1.5.0"]) == "2.0.0"
    
    def test_empty_list(self):
        """Test with empty list"""
        assert _latest_version([]) is None
    
    def test_same_versions(self):
        """Test with all same versions"""
        assert _latest_version(["1.0.0", "1.0.0", "1.0.0"]) == "1.0.0"
    
    def test_complex_versions(self):
        """Test with complex version numbers"""
        assert _latest_version(["1.0.0", "1.10.0", "1.2.0"]) == "1.10.0"  # 10 > 2


class TestSelectVersion:
    """Test select_version function"""
    
    def test_wildcard_constraint_multiple_versions(self):
        """Test '*' constraint selects latest version"""
        assert _select_version("*", ["1.0.0", "2.0.0", "1.5.0"]) == "2.0.0"
        assert _select_version("*", ["0.9.0", "1.0.0", "1.1.0"]) == "1.1.0"
    
    def test_wildcard_constraint_single_version(self):
        """Test '*' constraint with single version"""
        assert _select_version("*", ["1.0.0"]) == "1.0.0"
    
    def test_wildcard_constraint_empty_list(self):
        """Test '*' constraint with empty list returns None"""
        assert _select_version("*", []) is None
    
    def test_greater_or_equal_basic(self):
        """Test '>=' constraint basic case"""
        assert _select_version(">=1.0.0", ["0.9.0", "1.0.0", "1.1.0", "2.0.0"]) == "2.0.0"
        assert _select_version(">=1.0.0", ["1.0.0", "1.5.0", "2.0.0"]) == "2.0.0"
    
    def test_greater_or_equal_no_matching_versions(self):
        """Test '>=' constraint with no matching versions returns None"""
        assert _select_version(">=2.0.0", ["0.9.0", "1.0.0", "1.1.0"]) is None
    
    def test_greater_or_equal_multiple_matching_versions(self):
        """Test '>=' constraint selects latest from matching versions"""
        assert _select_version(">=1.0.0", ["1.0.0", "1.1.0", "1.2.0", "0.9.0"]) == "1.2.0"
    
    def test_greater_or_equal_exact_match_included(self):
        """Test '>=' constraint includes exact match"""
        assert _select_version(">=1.0.0", ["1.0.0", "1.5.0"]) == "1.5.0"
        assert _select_version(">=1.5.0", ["1.5.0", "2.0.0"]) == "2.0.0"
    
    def test_greater_or_equal_all_versions_match(self):
        """Test '>=' constraint when all versions match"""
        assert _select_version(">=0.1.0", ["1.0.0", "2.0.0", "1.5.0"]) == "2.0.0"
    
    def test_pessimistic_constraint_basic(self):
        """Test '~>' constraint basic case"""
        # ~>1.0 matches versions starting with "1.0" (Python uses startswith)
        assert _select_version("~>1.0", ["0.9.0", "1.0.0", "1.0.1", "1.1.0", "2.0.0"]) == "1.0.1"
        assert _select_version("~>1.0", ["1.0.0", "1.0.5", "1.0.9"]) == "1.0.9"
    
    def test_pessimistic_constraint_no_matching_versions(self):
        """Test '~>' constraint with no matching versions returns None"""
        assert _select_version("~>2.0", ["0.9.0", "1.0.0", "1.1.0"]) is None
        assert _select_version("~>1.0", ["2.0.0", "2.1.0"]) is None
    
    def test_pessimistic_constraint_multiple_matching_versions(self):
        """Test '~>' constraint selects latest from matching versions"""
        # Only versions starting with "1.0" match
        assert _select_version("~>1.0", ["1.0.0", "1.0.1", "1.0.2", "2.0.0"]) == "1.0.2"
    
    def test_pessimistic_constraint_different_major_excluded(self):
        """Test '~>' constraint excludes different major versions"""
        # Only versions starting with "1.0" match (not "1.5" or "2.0")
        assert _select_version("~>1.0", ["1.0.0", "1.0.5", "2.0.0", "2.1.0"]) == "1.0.5"
    
    def test_pessimistic_constraint_different_minor_excluded(self):
        """Test '~>' constraint excludes different minor versions"""
        # Python code uses startswith("1.0"), so only 1.0.x matches (not 1.5.x)
        assert _select_version("~>1.0", ["1.0.0", "1.0.5", "1.5.0"]) == "1.0.5"
    
    def test_exact_version_match_exists(self):
        """Test exact version match when version exists"""
        assert _select_version("1.0.0", ["1.0.0", "1.1.0"]) == "1.0.0"
        assert _select_version("2.0.0", ["1.0.0", "2.0.0", "1.5.0"]) == "2.0.0"
    
    def test_exact_version_match_not_exists(self):
        """Test exact version match when version doesn't exist returns None"""
        assert _select_version("1.5.0", ["1.0.0", "1.1.0", "2.0.0"]) is None
    
    def test_exact_version_match_case_sensitive(self):
        """Test exact version match is case sensitive"""
        # Versions are typically numeric, but test edge case
        assert _select_version("1.0.0", ["1.0.0"]) == "1.0.0"
        # If we had "1.0.0" vs "1.0.0" (different case), they should be different
        # But semantic versions don't typically have case differences
    
    def test_empty_constraint_string(self):
        """Test empty constraint string (should try exact match, return None if not found)"""
        assert _select_version("", ["1.0.0", "2.0.0"]) is None
        assert _select_version("", []) is None
    
    def test_whitespace_in_constraint(self):
        """Test constraint with whitespace (should be stripped)"""
        assert _select_version(">= 1.0.0", ["1.0.0", "2.0.0"]) == "2.0.0"
        # ~>1.0 matches versions starting with "1.0" (not "1.5")
        assert _select_version("~> 1.0", ["1.0.0", "1.0.5"]) == "1.0.5"
    
    def test_invalid_constraint_format(self):
        """Test invalid constraint format (graceful degradation - tries exact match)"""
        assert _select_version("invalid", ["1.0.0", "2.0.0"]) is None
        assert _select_version("<>1.0.0", ["1.0.0", "2.0.0"]) is None


class TestIsSemver:
    """Test is_semver function"""
    
    def test_valid_basic_semver(self):
        """Test valid basic semver formats"""
        assert _is_semver("1.0.0") == True
        assert _is_semver("0.1.0") == True
        assert _is_semver("10.20.30") == True
        assert _is_semver("999.999.999") == True
    
    def test_valid_semver_with_prerelease(self):
        """Test valid semver with pre-release suffix"""
        assert _is_semver("1.0.0-alpha") == True
        assert _is_semver("1.0.0-beta.1") == True
        assert _is_semver("1.0.0-rc.2") == True
        assert _is_semver("1.0.0-alpha.1") == True
        assert _is_semver("1.0.0-0.3.7") == True
        assert _is_semver("1.0.0-x.7.z.92") == True
    
    def test_valid_edge_cases(self):
        """Test edge cases that are valid"""
        assert _is_semver("0.0.0") == True
        assert _is_semver("0.0.1") == True
    
    def test_invalid_missing_parts(self):
        """Test invalid semver with missing parts"""
        assert _is_semver("1.0") == False
        assert _is_semver("1") == False
        assert _is_semver("") == False
    
    def test_invalid_too_many_parts(self):
        """Test invalid semver with too many parts"""
        assert _is_semver("1.0.0.0") == False
        assert _is_semver("1.0.0.0.0") == False
    
    def test_invalid_non_numeric(self):
        """Test invalid semver with non-numeric parts"""
        assert _is_semver("1.0.a") == False
        assert _is_semver("a.b.c") == False
        # Note: Python regex [a-zA-Z0-9.-]+ allows trailing hyphen, so this is actually valid
        assert _is_semver("1.0.0-alpha-") == True  # Python regex allows this
    
    def test_invalid_prefixes(self):
        """Test invalid semver with prefixes"""
        assert _is_semver("v1.0.0") == False
        assert _is_semver("version1.0.0") == False
        assert _is_semver("V1.0.0") == False
    
    def test_invalid_whitespace(self):
        """Test invalid semver with whitespace"""
        assert _is_semver(" 1.0.0") == False
        assert _is_semver("1.0.0 ") == False
        # Note: Python regex $ matches before newline, so this is actually valid
        assert _is_semver("1.0.0\n") == True  # Python regex allows this
        assert _is_semver("1. 0.0") == False
    
    def test_invalid_special_characters(self):
        """Test invalid semver with special characters"""
        assert _is_semver("1.0.0+metadata") == False  # Build metadata not supported in this pattern
        assert _is_semver("1.0.0_alpha") == False  # Underscore not allowed
        assert _is_semver("1.0.0@alpha") == False  # @ not allowed
    
    def test_invalid_empty_prerelease(self):
        """Test invalid semver with empty pre-release"""
        assert _is_semver("1.0.0-") == False  # Must have content after hyphen
    
    def test_valid_prerelease_with_dots_and_hyphens(self):
        """Test valid pre-release identifiers with dots and hyphens"""
        assert _is_semver("1.0.0-alpha.1") == True
        assert _is_semver("1.0.0-alpha-1") == True
        assert _is_semver("1.0.0-alpha.1.2") == True
        assert _is_semver("1.0.0-0.3.7") == True


class TestIsValidPackageName:
    """Test is_valid_package_name function"""
    
    def test_valid_simple_names(self):
        """Test valid simple package names"""
        assert _is_valid_package_name("foo") == True
        assert _is_valid_package_name("bar") == True
        assert _is_valid_package_name("baz") == True
        assert _is_valid_package_name("package") == True
    
    def test_valid_with_hyphens(self):
        """Test valid package names with hyphens"""
        assert _is_valid_package_name("foo-bar") == True
        assert _is_valid_package_name("my-package") == True
        assert _is_valid_package_name("foo-bar-baz") == True
    
    def test_valid_with_underscores(self):
        """Test valid package names with underscores"""
        assert _is_valid_package_name("foo_bar") == True
        assert _is_valid_package_name("my_package") == True
        assert _is_valid_package_name("foo_bar_baz") == True
    
    def test_valid_alphanumeric(self):
        """Test valid alphanumeric package names"""
        assert _is_valid_package_name("foo123") == True
        assert _is_valid_package_name("package1") == True
        assert _is_valid_package_name("123package") == True
    
    def test_valid_mixed(self):
        """Test valid mixed package names"""
        assert _is_valid_package_name("foo-bar_123") == True
        assert _is_valid_package_name("my-package_name") == True
        assert _is_valid_package_name("package_1-2") == True
    
    def test_invalid_empty(self):
        """Test invalid empty package name"""
        assert _is_valid_package_name("") == False
    
    def test_invalid_special_characters(self):
        """Test invalid package names with special characters"""
        assert _is_valid_package_name("foo@bar") == False
        assert _is_valid_package_name("foo.bar") == False
        assert _is_valid_package_name("foo/bar") == False
        assert _is_valid_package_name("foo bar") == False
        assert _is_valid_package_name("foo+bar") == False
    
    def test_invalid_starts_with_hyphen(self):
        """Test invalid package names starting with hyphen"""
        assert _is_valid_package_name("-foo") == False
        assert _is_valid_package_name("-my-package") == False
    
    def test_invalid_ends_with_hyphen(self):
        """Test invalid package names ending with hyphen"""
        assert _is_valid_package_name("foo-") == False
        assert _is_valid_package_name("my-package-") == False
    
    def test_invalid_starts_with_underscore(self):
        """Test invalid package names starting with underscore"""
        assert _is_valid_package_name("_foo") == False
        assert _is_valid_package_name("_my-package") == False
    
    def test_invalid_ends_with_underscore(self):
        """Test invalid package names ending with underscore"""
        assert _is_valid_package_name("foo_") == False
        assert _is_valid_package_name("my-package_") == False
    
    def test_invalid_whitespace(self):
        """Test invalid package names with whitespace"""
        assert _is_valid_package_name("foo bar") == False
        assert _is_valid_package_name(" foo") == False
        assert _is_valid_package_name("foo ") == False
        # Note: Python regex $ matches before newline, so this is actually valid per Python behavior
        assert _is_valid_package_name("foo\n") == True  # Python regex allows this
    
    def test_invalid_only_special_chars(self):
        """Test invalid package names with only special characters"""
        assert _is_valid_package_name("@#$") == False
        assert _is_valid_package_name("---") == False
        assert _is_valid_package_name("___") == False
    
    def test_edge_cases_single_char(self):
        """Test edge cases with single characters"""
        assert _is_valid_package_name("a") == True
        assert _is_valid_package_name("1") == True
        assert _is_valid_package_name("-") == False
        assert _is_valid_package_name("_") == False


class TestNormalizeString:
    """Test normalize_string function"""
    
    def test_basic_normalization(self):
        """Test basic string normalization"""
        assert _normalize_string("  Foo  ") == "foo"
        assert _normalize_string("FOO") == "foo"
        assert _normalize_string("foo") == "foo"
        assert _normalize_string("  Bar  ") == "bar"
    
    def test_empty_strings(self):
        """Test empty string handling"""
        assert _normalize_string("") == ""
        assert _normalize_string("   ") == ""
        assert _normalize_string("  \n\t  ") == ""
    
    def test_mixed_case(self):
        """Test mixed case normalization"""
        assert _normalize_string("MixedCase") == "mixedcase"
        assert _normalize_string("  Mixed_Case  ") == "mixed_case"
        assert _normalize_string("A-B-C") == "a-b-c"
    
    def test_with_special_chars(self):
        """Test normalization with special characters"""
        assert _normalize_string("  Foo-Bar_123  ") == "foo-bar_123"
        assert _normalize_string("  Package-Name_1  ") == "package-name_1"
    
    def test_whitespace_variants(self):
        """Test different whitespace characters"""
        assert _normalize_string("\tFoo\n") == "foo"
        assert _normalize_string("  \r\n  Bar  \r\n  ") == "bar"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
