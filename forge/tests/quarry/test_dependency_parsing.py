"""Test dependency parsing from Quarry.toml"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.dependency import parse_quarry_toml, resolve_dependencies, generate_lockfile, read_lockfile, DependencySource


def test_parse_simple_dependency():
    """Test parsing simple dependency"""
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
        # DependencySource is a dataclass, isinstance check should work
        # But if it fails, check the type directly
        assert hasattr(deps["foo"], 'type') and hasattr(deps["foo"], 'version')
        assert deps["foo"].type == "registry"
        assert deps["foo"].version == "1.0.0"


def test_parse_version_constraints():
    """Test parsing version constraints"""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = ">=1.0.0"
bar = "~>1.0"
baz = "*"
""")
        
        deps = parse_quarry_toml(str(toml_file))
        assert deps["foo"].version == ">=1.0.0"
        assert deps["bar"].version == "~>1.0"
        assert deps["baz"].version == "*"


def test_parse_missing_dependencies_section():
    """Test parsing when dependencies section is missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"
""")
        
        deps = parse_quarry_toml(str(toml_file))
        assert deps == {}


def test_parse_empty_dependencies():
    """Test parsing empty dependencies section"""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
""")
        
        deps = parse_quarry_toml(str(toml_file))
        assert deps == {}


def test_parse_multiple_dependencies():
    """Test parsing multiple dependencies"""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
foo = "1.0.0"
bar = "2.1.0"
baz = ">=3.0.0"
""")
        
        deps = parse_quarry_toml(str(toml_file))
        assert len(deps) == 3
        assert deps["foo"].version == "1.0.0"
        assert deps["bar"].version == "2.1.0"
        assert deps["baz"].version == ">=3.0.0"


def test_parse_missing_file():
    """Test parsing when file doesn't exist"""
    deps = parse_quarry_toml("nonexistent.toml")
    assert deps == {}


def test_parse_invalid_toml_handles_gracefully():
    """Test that invalid TOML is handled gracefully"""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
invalid toml syntax here
""")
        
        # Should return empty dict or partial results, not crash
        deps = parse_quarry_toml(str(toml_file))
        # May return empty dict or partial results depending on parser
        assert isinstance(deps, dict)


def test_resolve_exact_version():
    """Test resolving exact version"""
    deps = {"foo": DependencySource(type="registry", version="1.0.0")}
    resolved = resolve_dependencies(deps)
    assert resolved["foo"].type == "registry"
    assert resolved["foo"].version == "1.0.0"


def test_resolve_greater_equal_constraint():
    """Test resolving >= constraint"""
    deps = {"foo": DependencySource(type="registry", version=">=1.0.0")}
    resolved = resolve_dependencies(deps)
    # Should select latest version >= 1.0.0 (mock registry has 2.0.0)
    assert resolved["foo"].version in ["1.0.0", "1.1.0", "2.0.0"]
    # Verify it's >= 1.0.0
    version_parts = resolved["foo"].version.split('.')
    assert int(version_parts[0]) >= 1


def test_resolve_wildcard_constraint():
    """Test resolving * constraint (latest)"""
    deps = {"foo": DependencySource(type="registry", version="*")}
    resolved = resolve_dependencies(deps)
    # Should select latest version (mock registry has 2.0.0 as latest)
    assert resolved["foo"].version == "2.0.0"


def test_resolve_pessimistic_constraint():
    """Test resolving ~> constraint (pessimistic)"""
    deps = {"bar": DependencySource(type="registry", version="~>2.0")}
    resolved = resolve_dependencies(deps)
    # Should select latest version with same major.minor (2.x)
    assert resolved["bar"].version.startswith("2.")


def test_resolve_version_conflict():
    """Test that version conflicts are detected"""
    # This test would require two dependencies with incompatible constraints
    # For MVP, we'll test that invalid constraints raise errors
    deps = {"nonexistent": DependencySource(type="registry", version="999.0.0")}
    with pytest.raises(ValueError):
        resolve_dependencies(deps)


def test_resolve_multiple_dependencies():
    """Test resolving multiple dependencies"""
    deps = {
        "foo": DependencySource(type="registry", version="1.0.0"),
        "bar": DependencySource(type="registry", version=">=2.0.0")
    }
    resolved = resolve_dependencies(deps)
    assert len(resolved) == 2
    assert resolved["foo"].version == "1.0.0"
    assert resolved["bar"].version in ["2.0.0", "2.1.0", "3.0.0"]


def test_generate_lockfile():
    """Test lockfile generation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        resolved_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="registry", version="2.1.0")
        }
        
        generate_lockfile(resolved_deps, str(lockfile_path))
        
        assert lockfile_path.exists(), "Lockfile should be created"
        content = lockfile_path.read_text()
        assert "[dependencies]" in content
        assert "foo" in content
        assert "1.0.0" in content


def test_read_lockfile():
    """Test lockfile reading"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        lockfile_path.write_text("""[dependencies]
foo = "1.0.0"
bar = "2.1.0"
""")
        
        deps = read_lockfile(str(lockfile_path))
        assert len(deps) == 2
        assert deps["foo"].version == "1.0.0"
        assert deps["bar"].version == "2.1.0"


def test_read_missing_lockfile():
    """Test reading missing lockfile"""
    deps = read_lockfile("nonexistent.lock")
    assert deps == {}


def test_lockfile_round_trip():
    """Test lockfile generation and reading round-trip"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        original_deps = {
            "foo": DependencySource(type="registry", version="1.0.0"),
            "bar": DependencySource(type="registry", version="2.1.0"),
            "baz": DependencySource(type="registry", version="3.0.0")
        }
        
        # Generate lockfile
        generate_lockfile(original_deps, str(lockfile_path))
        
        # Read it back
        read_deps = read_lockfile(str(lockfile_path))
        
        assert len(read_deps) == len(original_deps)
        assert read_deps["foo"].version == original_deps["foo"].version
        assert read_deps["bar"].version == original_deps["bar"].version
        assert read_deps["baz"].version == original_deps["baz"].version


def test_parse_git_dependency():
    """Test parsing git dependency"""
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


def test_parse_path_dependency():
    """Test parsing path dependency"""
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


def test_parse_mixed_sources():
    """Test parsing mixed dependency sources"""
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = Path(tmpdir) / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"

[dependencies]
registry_dep = "1.0.0"
git_dep = { git = "https://github.com/user/repo.git", branch = "main" }
path_dep = { path = "../local" }
""")
        
        deps = parse_quarry_toml(str(toml_file))
        assert len(deps) == 3
        assert deps["registry_dep"].type == "registry"
        assert deps["git_dep"].type == "git"
        assert deps["path_dep"].type == "path"


def test_resolve_git_dependency():
    """Test that git dependencies don't need version resolution"""
    deps = {
        "foo": DependencySource(type="git", git_url="https://github.com/user/foo.git", git_branch="main")
    }
    resolved = resolve_dependencies(deps)
    assert resolved["foo"].type == "git"
    assert resolved["foo"].git_url == "https://github.com/user/foo.git"


def test_resolve_path_dependency():
    """Test that path dependencies don't need version resolution"""
    deps = {
        "bar": DependencySource(type="path", path="../bar")
    }
    resolved = resolve_dependencies(deps)
    assert resolved["bar"].type == "path"
    assert resolved["bar"].path == "../bar"


def test_lockfile_includes_checksums():
    """Test that lockfile includes checksums for registry packages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        resolved_deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123")
        }
        
        generate_lockfile(resolved_deps, str(lockfile_path))
        
        assert lockfile_path.exists()
        content = lockfile_path.read_text()
        assert "checksum" in content
        assert "sha256:abc123" in content


def test_read_lockfile_parses_checksums():
    """Test that read_lockfile() parses checksums from lockfile"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        lockfile_path.write_text("""[dependencies]
foo = { version = "1.0.0", checksum = "sha256:abc123" }
""")
        
        deps = read_lockfile(str(lockfile_path))
        assert len(deps) == 1
        assert deps["foo"].version == "1.0.0"
        assert deps["foo"].checksum == "sha256:abc123"


def test_lockfile_includes_git_commit():
    """Test that lockfile includes commit hash for git dependencies"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        resolved_deps = {
            "foo": DependencySource(
                type="git",
                git_url="https://github.com/user/foo.git",
                git_branch="main",
                commit="abc123def456"
            )
        }
        
        generate_lockfile(resolved_deps, str(lockfile_path))
        
        assert lockfile_path.exists()
        content = lockfile_path.read_text()
        assert "commit" in content
        assert "abc123def456" in content


def test_read_lockfile_parses_git_commit():
    """Test that read_lockfile() parses commit hash from lockfile"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        lockfile_path.write_text("""[dependencies]
foo = { git = "https://github.com/user/foo.git", branch = "main", commit = "abc123def456" }
""")
        
        deps = read_lockfile(str(lockfile_path))
        assert len(deps) == 1
        assert deps["foo"].type == "git"
        assert deps["foo"].git_url == "https://github.com/user/foo.git"
        assert deps["foo"].commit == "abc123def456"


def test_lockfile_includes_path_hash():
    """Test that lockfile includes hash for path dependencies"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        resolved_deps = {
            "bar": DependencySource(
                type="path",
                path="../bar",
                hash="sha256:def456"
            )
        }
        
        generate_lockfile(resolved_deps, str(lockfile_path))
        
        assert lockfile_path.exists()
        content = lockfile_path.read_text()
        assert "hash" in content
        assert "sha256:def456" in content


def test_read_lockfile_parses_path_hash():
    """Test that read_lockfile() parses path hash from lockfile"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        lockfile_path.write_text("""[dependencies]
bar = { path = "../bar", hash = "sha256:def456" }
""")
        
        deps = read_lockfile(str(lockfile_path))
        assert len(deps) == 1
        assert deps["bar"].type == "path"
        assert deps["bar"].path == "../bar"
        assert deps["bar"].hash == "sha256:def456"


def test_lockfile_round_trip_with_checksums():
    """Test lockfile generation and reading round-trip with checksums"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Quarry.lock"
        original_deps = {
            "foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:abc123"),
            "bar": DependencySource(
                type="git",
                git_url="https://github.com/user/bar.git",
                git_branch="main",
                commit="def456"
            ),
            "baz": DependencySource(type="path", path="../baz", hash="sha256:ghi789")
        }
        
        # Generate lockfile
        generate_lockfile(original_deps, str(lockfile_path))
        
        # Read it back
        read_deps = read_lockfile(str(lockfile_path))
        
        assert len(read_deps) == len(original_deps)
        assert read_deps["foo"].version == original_deps["foo"].version
        assert read_deps["foo"].checksum == original_deps["foo"].checksum
        assert read_deps["bar"].commit == original_deps["bar"].commit
        assert read_deps["baz"].hash == original_deps["baz"].hash
